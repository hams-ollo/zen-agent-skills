#!/usr/bin/env python3
"""Serve the observatory store as one page, on the loopback interface, with no build step.

    python scripts/observatory/serve.py [--store PATH] [--port N]

`ingest.py` fills the store and nothing reads it. This is the surface that reads it: a
`ThreadingHTTPServer` that renders `ui/index.html`, answers a small JSON API from the store,
and does nothing else. The page shell it serves is a deliverable in its own right, because the
four remaining reports (`feat-0055` to `feat-0058`) slot into it rather than each reinventing
layout, navigation, and the scope selector.

Three properties are load-bearing and are why this file is shaped the way it is.

**Loopback only.** `make_server` refuses any address that is not a loopback address, before it
binds rather than after. The contract forbids data leaving the machine (S-022), and a server on
all interfaces publishes one maintainer's whole session corpus to whatever network the machine
is on. Refusing is deliberate: a warning would be read once and a `--host 0.0.0.0` would go on
working.

**No third-party dependency and no external asset.** Standard library only, per the conventions
section of `AGENTS.md`. The page carries its own CSS and its own script inline and requests no
subresource at all, so it renders with the network unavailable and a chart is hand-rolled inline
SVG. A remote font or a chart library would also break the no-network property `S-022` sets.

**Reads only.** Every route is a GET. Nothing here writes to the store, and nothing here touches
anything the harness owns; `ingest.py` is the only writer and the corpus is opened by neither.
`S-019` and `S-020`, which fix what a session-directed action may do, are `feat-0060`'s and this
surface offers no such action at all. The fleet report names sessions and changes none of them.

**The live registry is read per request, not ingested.** `S-012` asks a question about now, so
an answer stored at the last ingest would be as old as that ingest. `live_sessions` reads the
harness's registry and checks each entry's process on every request, which is why the report is
correct as of when it was asked for and no more; keeping an open report current is `S-013`, and
that is `feat-0059`'s.

Exit codes, matching `run-checks.py` and `ingest.py`:

    0  the server ran and was stopped
    2  the server could not start (a non-loopback address, or a port already in use)

Contract: `docs/spec/agent-observatory.md`. Scenarios: S-001, S-002, S-012, S-018.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# `install` is imported for one thing only: where the skills live. S-002 needs a roster the
# corpus cannot supply, and writing that path here would be a second source of truth that
# disagrees with the installer the first time the tree moves.
from scripts import install                     # noqa: E402
from scripts.observatory import db, ingest      # noqa: E402

DEFAULT_STORE = ingest.DEFAULT_STORE
DEFAULT_CORPUS = ingest.DEFAULT_CORPUS
DEFAULT_REGISTRY = ingest.DEFAULT_REGISTRY

UI_DIR = Path(__file__).resolve().parent / "ui"
INDEX = UI_DIR / "index.html"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

# The five reports of the contract's Proposed Surface, in its order. This is the registry the
# page shell renders its navigation from, so a later task adds its report by adding an endpoint
# and a renderer rather than by editing the shell's markup. `owner` names the task that owns a
# report not built yet, so the page says who owes it instead of showing an empty panel.
REPORTS = (
    {"id": "fleet", "title": "Fleet",
     "question": "Which sessions exist, where, and which are running?",
     "scenarios": ["S-012", "S-018"], "endpoint": "/api/fleet", "owner": None},
    {"id": "skills", "title": "Skills",
     "question": "Which skills are used, how often, and which never are?",
     "scenarios": ["S-001", "S-002"], "endpoint": "/api/skills", "owner": None},
    {"id": "waves", "title": "Waves",
     "question": "What did a dispatched wave run, cost, and produce?",
     "scenarios": ["S-003", "S-004"], "endpoint": None, "owner": "feat-0056"},
    {"id": "cost", "title": "Cost and pressure",
     "question": "What was consumed, and how close to a limit?",
     "scenarios": ["S-010", "S-011", "S-017", "S-021"], "endpoint": None, "owner": "feat-0057"},
    {"id": "health", "title": "Health",
     "question": "What failed, and how often?",
     "scenarios": ["S-016"], "endpoint": None, "owner": "feat-0058"},
)

# Said in one place, and served to the page so the document and the surface cannot disagree
# about what "never used" was measured against. `docs/OBSERVATORY.md` states the same thing.
ROSTER_LABEL = "the skill directories under .agents/skills/, as install.py discovers them"

# The bucket a session lands in when nothing can attribute it to a project. It is a project
# in the report's arithmetic rather than a discard, because S-018 requires the per-project
# figures to sum to the unrestricted ones and a dropped session breaks that sum while every
# panel still renders.
UNATTRIBUTED = "(unattributed)"

# The staleness rule, in one sentence, served to the page for the same reason ROSTER_LABEL
# is: a registry entry can outlive the process that wrote it, so presence is evidence and
# not proof, and a reader must be told which of the two the report is showing them.
LIVENESS_POLICY = (
    "A session is reported running only where its registry entry's process is confirmed. "
    "An entry whose process is gone is reported ended and counted as a stale entry; one "
    "whose process cannot be checked is reported unverified, never running."
)

# Running first, then the ones that could not be established, then the settled past. The
# report exists to answer a question about now, so what is now goes at the top.
STATE_ORDER = ("running", "unverified", "ended")

# The two kinds of action this surface may offer against a session, and there is deliberately
# no third. `S-019` permits exactly these: an action referencing a session must "resolve to
# navigation or to a command presented for a person to run". Both are non-mutating by
# construction rather than by review: `navigate` opens something in the viewer's browser, and
# `copy-command` puts text on their clipboard. Neither can reach a session.
#
# Adding a kind here is the one edit that could make `S-019` false, which is why the set is a
# constant a test can read rather than a convention a reviewer has to remember.
ACTION_KINDS = ("navigate", "copy-command")

# Every action the surface offers. `S-019` is an enumeration claim, and that is what makes it
# testable: "nothing mutates a session" is untestable as prose and decidable as a list. The
# list lives here, the page renders from it and tags each element with `data-action`, and a
# test resolves the two against each other. A button added to the page without an entry here
# fails that test rather than quietly widening the surface.
#
# `field` names the session row's key that supplies the value, so an action whose field is
# empty on a given row is not offered for that row. `template` builds the text for a
# `copy-command`; a `navigate` action uses the field's value as the target.
ACTIONS = (
    {"id": "open-pr", "kind": "navigate", "label": "Pull request", "field": "pr_url",
     "template": None,
     "note": "Opens the session's pull request. A link the viewer follows is a request their "
             "browser makes, not one this report makes, so S-022 is untouched."},
    {"id": "copy-cwd", "kind": "copy-command", "label": "Copy path", "field": "cwd",
     "template": "{cwd}",
     "note": "Copies the working directory. A file:// link from an http:// page is blocked "
             "by browsers, so the path is offered as text rather than as a dead link."},
    {"id": "copy-resume", "kind": "copy-command", "label": "Copy resume command",
     "field": "session_id", "template": "claude --resume {session_id}",
     "note": "Copies the command that would resume this session. S-019 permits presenting a "
             "command for a person to run; running it is not this surface's to do. The flag "
             "is the CLI's own, confirmed against `claude --help` rather than assumed."},
)


class NotLoopback(ValueError):
    """The requested address is not a loopback address, so binding it would publish the
    corpus to the local network."""


def loopback_address(host: str) -> str:
    """The loopback address `host` names, or `NotLoopback`.

    `localhost` is resolved by table rather than by `socket.gethostbyname`, for two reasons:
    a name lookup is a network operation this contract would rather not perform at all, and a
    machine whose hosts file points `localhost` somewhere else must not be able to talk this
    server onto a routable interface.
    """
    if host.rstrip(".") == "localhost":
        return DEFAULT_HOST
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise NotLoopback(
            f"{host!r} is not an IP address. This server binds a loopback address only, "
            f"so the session corpus is never served to the local network."
        ) from None
    if not address.is_loopback:
        raise NotLoopback(
            f"{host!r} is not a loopback address. Binding it would serve the whole session "
            f"corpus to the local network, which the contract forbids. Use "
            f"{DEFAULT_HOST} or ::1."
        )
    return str(address)


def host_is_loopback(header) -> bool:
    """Whether a `Host` header names this machine's loopback interface.

    Binding a loopback address stops another machine reaching this server and does nothing
    about a browser on this one. The `Host` header is attacker-controlled, so a page on any
    origin can point a name it owns at 127.0.0.1, have the browser send that name here, and
    read every route. That is DNS rebinding, and what it reads is one maintainer's entire
    session history: session ids, project names, working directories, branches.

    `feat-0054` recorded this as a local-attacker concern outside `S-022`'s wording, which
    is about outbound connections, and left it to whichever task defined the surface's
    boundary. This is that task.

    An absent header is allowed. HTTP/1.0 clients and some command-line tools omit it, and
    no browser does, so refusing it would break the honest callers and stop none of the
    dishonest ones.
    """
    if header is None:
        return True
    host = str(header).strip()
    if host.startswith("["):                  # [::1] or [::1]:8787
        host = host[1:].split("]", 1)[0]
    elif host.count(":") == 1:                # 127.0.0.1:8787 or name:8787
        host = host.rsplit(":", 1)[0]
    if not host:
        return False
    if host.rstrip(".").lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def skill_roster(skills_dir: Path | None = None) -> list[str]:
    """Every skill the report counts against, whether or not the corpus mentions it.

    S-002 cannot be answered from the store: a skill that never appears in a transcript
    appears nowhere in the store either, so the set has to come from the skill directories
    themselves. It comes from `install.discover_skills()` rather than from a path spelled out
    here, so this and the installer can never disagree about what the installed set is.

    `skills_dir` overrides the location for a test that needs a roster it controls; it applies
    the same rule (a directory holding a `SKILL.md`) rather than a second one.
    """
    if skills_dir is None:
        return [directory.name for directory in install.discover_skills()]
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def projects(conn) -> list[str]:
    """Every project the store can report on, for the scope selector.

    The union of two tables rather than `message_occurrence` alone, because a session with no
    assistant message has no occurrence row and its project would therefore never appear in
    the selector while the fleet report counted it. Four of this maintainer's 155 sessions are
    in that position on 2026-08-28, so the gap is real rather than hypothetical.
    """
    return [row["project"] for row in conn.execute(
        "SELECT project FROM message_occurrence WHERE project IS NOT NULL "
        "UNION SELECT project FROM session WHERE project IS NOT NULL "
        "ORDER BY project"
    )]


def skills_report(conn, project: str | None = None,
                  roster: list[str] | None = None) -> dict:
    """The skills report: one row per skill, roster and corpus unioned.

    The count is **distinct messages carrying the attribution**, not lines in the corpus.
    `message` holds one canonical row per uuid, so a `COUNT(*)` over it is already the
    distinct-message figure; a forked or resumed session replays earlier history verbatim, so
    5,442 uuids in this maintainer's corpus appear in more than one transcript and counting
    occurrences would report every one of them twice. That is why the unscoped branch counts
    `message` and the scoped branch counts `DISTINCT m.uuid` rather than joined rows.

    Every roster skill appears, including one the corpus never mentions, which is reported at
    zero rather than left out (S-002). A skill the corpus carries that the roster does not is
    reported too, marked `installed: false`, because dropping it would overstate the roster's
    share of the total.
    """
    roster = skill_roster() if roster is None else list(roster)

    if project:
        rows = conn.execute(
            "SELECT m.attribution_skill AS skill, COUNT(DISTINCT m.uuid) AS uses "
            "FROM message m JOIN message_occurrence o ON o.uuid = m.uuid "
            "WHERE m.attribution_skill IS NOT NULL AND o.project = ? "
            "GROUP BY m.attribution_skill",
            (project,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT attribution_skill AS skill, COUNT(*) AS uses FROM message "
            "WHERE attribution_skill IS NOT NULL GROUP BY attribution_skill"
        ).fetchall()

    counted = {row["skill"]: row["uses"] for row in rows}
    names = sorted(set(roster) | set(counted))
    entries = [
        {"skill": name, "uses": counted.get(name, 0), "installed": name in roster}
        for name in names
    ]
    entries.sort(key=lambda entry: (-entry["uses"], entry["skill"]))

    installed = [entry for entry in entries if entry["installed"]]
    return {
        "report": "skills",
        "project": project,
        "roster_label": ROSTER_LABEL,
        "roster_size": len(roster),
        "installed_used": sum(1 for entry in installed if entry["uses"]),
        "installed_unused": sum(1 for entry in installed if not entry["uses"]),
        "total_uses": sum(entry["uses"] for entry in entries),
        "skills": entries,
    }


def scope_options(conn, registry=None, corpus=None) -> list[str]:
    """Every project any report can be restricted to, for the scope selector.

    `projects(conn)` plus whatever only the live registry knows about. A session that started
    minutes ago has no store row, so a project whose only session is that one would be counted
    by the fleet report and missing from the selector, which is the shape of gap where a
    reader sees a figure in one panel and cannot reach it from the other.
    """
    _, live = live_sessions(conn, registry, corpus)
    return sorted(set(projects(conn)) | {seen["project"] for seen in live.values()})


def _live_project(conn, session_id: str, corpus: Path) -> str:
    """The project a live session belongs to, asked of the two sources that actually know.

    The store first, which is authoritative for any session it has seen. Then the corpus,
    because a session that started minutes ago has a transcript and no store row yet, and the
    directory that transcript sits in *is* the project name.

    **The obvious third option, transforming `cwd` into a directory name, is deliberately
    absent.** It cannot work, and the reason is stronger than a bad hit rate: measured over
    this maintainer's corpus on 2026-08-28, the project directory is not a function of the
    recorded working directory at all, because two projects are each reached from more than
    one working directory. Six of twenty-six distinct `(cwd, project)` pairs disagree under
    the most permissive rule tried, every non-alphanumeric character to a dash, and a
    separator-only rule misses all twenty-six because project names also flatten spaces and
    underscores. The cause is that the working directory drifts within a session while the
    project directory does not: `D:\\hts-app\\docs` and `D:\\hts-app\\content-engine` both live
    under `D--hts-app`, and one worktree's sessions live under a different worktree's
    directory entirely. A transform would attribute those to projects that do not exist,
    which is worse than saying so.
    """
    row = conn.execute("SELECT project FROM session WHERE session_id = ?",
                       (session_id,)).fetchone()
    if row and row["project"]:
        return row["project"]
    try:
        for directory in sorted(corpus.iterdir()):
            if directory.is_dir() and (directory / f"{session_id}.jsonl").exists():
                return directory.name
    except OSError:
        pass
    return UNATTRIBUTED


def live_sessions(conn, registry=None, corpus=None) -> tuple:
    """`(what the registry held, {session_id: liveness})`, read at report time.

    Read per request rather than ingested into a table. Running-versus-ended is a question
    about now, and a stored answer would be as old as the last ingest; the contract's S-013,
    which makes an open report update itself, is `feat-0059`'s and is a different question
    from this one.

    Where two entries name one session, the stronger claim wins rather than whichever file
    sorted last, so the answer does not depend on a filename.
    """
    registry = ingest.DEFAULT_REGISTRY if registry is None else Path(registry)
    corpus = ingest.DEFAULT_CORPUS if corpus is None else Path(corpus)
    found = ingest.read_registry(registry)

    rank = {ingest.ALIVE: 0, ingest.UNKNOWN: 1, ingest.GONE: 2}
    live: dict = {}
    for entry in found["entries"]:
        session_id = entry["sessionId"]
        state, evidence = ingest.process_state(
            entry.get("pid"), entry.get("procStart"), entry.get("pidDomain"))
        held = live.get(session_id)
        if held and rank[held["process"]] <= rank[state]:
            continue
        live[session_id] = {
            "process": state, "evidence": evidence, "entry": entry,
            "project": _live_project(conn, session_id, corpus),
        }
    return found, live


def _started_at(entry: dict):
    """`startedAt` is epoch milliseconds in the registry. Rendered here rather than on the
    page, because the page's script is the one part of this surface with no execution
    coverage and a date it formats itself is a date nothing can check."""
    millis = entry.get("startedAt")
    if not isinstance(millis, (int, float)) or isinstance(millis, bool):
        return None
    try:
        return datetime.fromtimestamp(millis / 1000, timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def fleet_report(conn, project: str | None = None, registry=None, corpus=None) -> dict:
    """The fleet report: every session, where it is, and which are running (S-012, S-018).

    Two invariants are the point of the shape below, and both are arithmetic rather than
    visual because both can be false while every panel still renders.

    **Every session lands in exactly one project bucket**, including one nothing can
    attribute, which goes to `UNATTRIBUTED` rather than being dropped. That is what makes
    S-018's summing property hold: restrict to each project in turn, add the figures up, and
    the total is the unrestricted total.

    **Every session lands in exactly one state**, so `running + unverified + ended` equals
    `sessions`. A stale registry entry is `ended` with its entry marked `stale`, and is
    counted in `stale_entries` as well, so it is neither reported as running nor silent.
    """
    found, live = live_sessions(conn, registry, corpus)

    def row(session_id, project_name, branch, first, last, title, entrypoint, cwd,
            in_store, pr_url=None, pr_number=None):
        state, registry_state, evidence = "ended", "absent", "no entry in the live registry"
        entry = {}
        seen = live.get(session_id)
        if seen:
            entry = seen["entry"]
            evidence = seen["evidence"]
            state, registry_state = {
                ingest.ALIVE: ("running", "live"),
                ingest.GONE: ("ended", "stale"),
                ingest.UNKNOWN: ("unverified", "unchecked"),
            }[seen["process"]]
        return {
            "session_id": session_id, "project": project_name, "branch": branch,
            "first_activity": first, "last_activity": last, "title": title,
            "entrypoint": entrypoint, "cwd": cwd, "in_store": in_store,
            "pr_url": pr_url, "pr_number": pr_number,
            "state": state, "registry": registry_state, "evidence": evidence,
            "pid": entry.get("pid"), "kind": entry.get("kind"),
            "name": entry.get("name"), "started_at": _started_at(entry),
        }

    rows = [
        row(stored["session_id"], stored["project"] or UNATTRIBUTED, stored["git_branch"],
            stored["first_ts"], stored["last_ts"], stored["title"], stored["entrypoint"],
            stored["cwd"], True, stored["pr_url"], stored["pr_number"])
        for stored in conn.execute(
            "SELECT session_id, project, cwd, git_branch, title, first_ts, last_ts, "
            "entrypoint, pr_url, pr_number FROM session")
    ]
    # A live session the store has never seen. It is not an edge case: a session that started
    # minutes ago has written a transcript and the ingester has not read it yet, and dropping
    # it would leave the one report that answers a question about now blind to the newest
    # thing on the machine.
    known = {entry["session_id"] for entry in rows}
    for session_id, seen in live.items():
        if session_id not in known:
            rows.append(row(session_id, seen["project"], None, None, None, None,
                            seen["entry"].get("entrypoint"), seen["entry"].get("cwd"),
                            False))

    if project:
        rows = [entry for entry in rows if entry["project"] == project]

    # Three stable sorts, dominant last: running before unverified before ended, then most
    # recent activity first, then the id so a tie is not decided by dictionary order.
    rows.sort(key=lambda entry: entry["session_id"])
    rows.sort(key=lambda entry: entry["last_activity"] or "", reverse=True)
    rows.sort(key=lambda entry: STATE_ORDER.index(entry["state"]))

    by_project: dict = {}
    for entry in rows:
        bucket = by_project.setdefault(
            entry["project"],
            {"project": entry["project"], "sessions": 0, "running": 0, "ended": 0,
             "unverified": 0, "stale_entries": 0})
        bucket["sessions"] += 1
        bucket[entry["state"]] += 1
        if entry["registry"] == "stale":
            bucket["stale_entries"] += 1
    breakdown = sorted(by_project.values(),
                       key=lambda bucket: (-bucket["sessions"], bucket["project"]))

    return {
        "report": "fleet",
        "project": project,
        "registry": {
            "path": found["path"], "present": found["present"],
            "entries": len(found["entries"]), "unreadable": found["unreadable"],
            "notes": found["notes"],
        },
        "liveness_check": ingest.liveness_check(),
        "liveness_policy": LIVENESS_POLICY,
        "unattributed_label": UNATTRIBUTED,
        "totals": {
            "sessions": len(rows),
            "running": sum(1 for entry in rows if entry["state"] == "running"),
            "ended": sum(1 for entry in rows if entry["state"] == "ended"),
            "unverified": sum(1 for entry in rows if entry["state"] == "unverified"),
            "stale_entries": sum(1 for entry in rows if entry["registry"] == "stale"),
            "not_yet_ingested": sum(1 for entry in rows if not entry["in_store"]),
        },
        "projects": breakdown,
        "sessions": rows,
    }


class ObservatoryServer(ThreadingHTTPServer):
    """The server, carrying the store path and the roster the handler answers from."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, store: Path, roster=None, quiet: bool = False,
                 family=socket.AF_INET, registry=None, corpus=None):
        self.store = Path(store)
        self.roster = roster
        # Carried rather than read from the module defaults at the point of use, so a test
        # drives the fleet report against a registry and a corpus it controls.
        self.registry = ingest.DEFAULT_REGISTRY if registry is None else Path(registry)
        self.corpus = ingest.DEFAULT_CORPUS if corpus is None else Path(corpus)
        self.quiet = quiet
        # Read from the instance by `socketserver.TCPServer.__init__`, so it must be set
        # before the call. Set per instance rather than on the class, because ::1 and
        # 127.0.0.1 are both legal here and a class attribute would make the last caller win.
        self.address_family = family
        super().__init__(address, handler)


class ObservatoryHandler(BaseHTTPRequestHandler):
    """One GET-only handler. Every route reads; none of them writes anything, anywhere."""

    server_version = "observatory"
    sys_version = ""

    # -- plumbing ---------------------------------------------------------------------

    def log_message(self, fmt, *args):     # noqa: A003 (BaseHTTPRequestHandler's name)
        if not getattr(self.server, "quiet", False):
            super().log_message(fmt, *args)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The page is a view of a store that changes under it, so a cached answer is a wrong
        # answer rather than a stale nicety.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(status, json.dumps(payload, indent=1).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _refuse(self) -> None:
        """Anything that is not a GET or a HEAD. The surface is a report, so a method that
        exists to change something has no route here to decline politely."""
        self._json({"error": f"{self.command} is not served. This surface reads only."}, 405)

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    # -- routes -----------------------------------------------------------------------

    def do_GET(self) -> None:               # noqa: N802 (BaseHTTPRequestHandler's name)
        # Before routing, not after: a rebound request must not reach a report at all.
        if not host_is_loopback(self.headers.get("Host")):
            return self._json({
                "error": f"Host {self.headers.get('Host')!r} is not this machine's loopback "
                         f"interface. This surface answers only to a loopback name, because "
                         f"the Host header is attacker-controlled and what it would return "
                         f"is the whole session corpus."
            }, 403)
        parts = urlsplit(self.path)
        query = parse_qs(parts.query)
        project = (query.get("project") or [None])[0] or None
        route = parts.path

        if route in ("/", "/index.html"):
            return self._index()
        if route == "/api/reports":
            return self._json({"reports": list(REPORTS)})
        if route == "/api/meta":
            return self._with_store(lambda conn: {
                "store": str(self.server.store),
                "projects": scope_options(conn, self.server.registry, self.server.corpus),
                "roster_label": ROSTER_LABEL,
                "reports": list(REPORTS),
                "actions": list(ACTIONS),
                "action_kinds": list(ACTION_KINDS),
            })
        if route == "/api/skills":
            return self._with_store(
                lambda conn: skills_report(conn, project, self.server.roster))
        if route == "/api/fleet":
            return self._with_store(
                lambda conn: fleet_report(conn, project, self.server.registry,
                                          self.server.corpus))
        self._json({"error": f"no route for {route}"}, 404)

    do_HEAD = do_GET

    def _index(self) -> None:
        try:
            body = INDEX.read_bytes()
        except OSError as exc:
            return self._json({"error": f"the page is missing: {exc}"}, 500)
        self._send(200, body, "text/html; charset=utf-8")

    def _with_store(self, build) -> None:
        """Answer from the store, saying plainly when there is not one yet.

        A missing store is not an error and not an empty report: it means the ingester has not
        run, which is a different thing from a corpus with nothing in it, and the page says
        which. Opening it here would create one as a side effect of a GET.
        """
        store = self.server.store
        if not store.exists():
            return self._json({
                "store": str(store), "store_present": False,
                "message": f"No store at {store}. Run scripts/observatory/ingest.py first.",
            })
        try:
            conn = db.connect(store)
        except db.StoreUnusable as exc:
            return self._json({"store": str(store), "store_present": True,
                               "error": str(exc)}, 500)
        try:
            payload = build(conn)
        finally:
            conn.close()
        payload.setdefault("store", str(store))
        payload["store_present"] = True
        self._json(payload)


def make_server(store: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                roster=None, quiet: bool = False, registry=None,
                corpus=None) -> ObservatoryServer:
    """Build the server, refusing a non-loopback address before anything is bound."""
    address = loopback_address(host)
    family = (socket.AF_INET6 if ipaddress.ip_address(address).version == 6
              else socket.AF_INET)
    return ObservatoryServer((address, port), ObservatoryHandler, store=store,
                             roster=roster, quiet=quiet, family=family,
                             registry=registry, corpus=corpus)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the observatory store as one local page."
    )
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE,
                        help=f"store path (default: {DEFAULT_STORE})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"loopback address to bind (default: {DEFAULT_HOST}). "
                             f"A non-loopback address is refused.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port (default: {DEFAULT_PORT})")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY,
                        help=f"the harness's live-session registry, read to tell a running "
                             f"session from an ended one (default: {DEFAULT_REGISTRY})")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS,
                        help=f"corpus root, read only to place a live session the store has "
                             f"not seen yet (default: {DEFAULT_CORPUS})")
    parser.add_argument("--quiet", action="store_true", help="suppress the request log")
    args = parser.parse_args(argv)

    try:
        server = make_server(args.store, args.host, args.port, quiet=args.quiet,
                             registry=args.registry, corpus=args.corpus)
    except NotLoopback as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR could not bind {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 2

    host, port = server.server_address[0], server.server_address[1]
    print(f"Observatory on http://{host}:{port}/ over {args.store}")
    print(f"Roster for never-used skills: {ROSTER_LABEL}")
    print(f"Live registry: {args.registry}")
    print(f"Liveness check: {ingest.liveness_check()}")
    if not Path(args.registry).is_dir():
        print("No live registry there, so every session is reported ended.")
    if not Path(args.store).exists():
        print(f"No store at {args.store} yet. Run scripts/observatory/ingest.py first.")
    print("Loopback only. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
