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
surface offers no such action at all.

Exit codes, matching `run-checks.py` and `ingest.py`:

    0  the server ran and was stopped
    2  the server could not start (a non-loopback address, or a port already in use)

Contract: `docs/spec/agent-observatory.md`. Scenarios: S-001, S-002.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
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
from scripts.observatory import db              # noqa: E402
from scripts.observatory.ingest import DEFAULT_STORE   # noqa: E402

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
     "scenarios": ["S-012", "S-018"], "endpoint": None, "owner": "feat-0055"},
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
    """Every project the store holds messages for, for the scope selector."""
    return [row["project"] for row in conn.execute(
        "SELECT DISTINCT project FROM message_occurrence "
        "WHERE project IS NOT NULL ORDER BY project"
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


class ObservatoryServer(ThreadingHTTPServer):
    """The server, carrying the store path and the roster the handler answers from."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, store: Path, roster=None, quiet: bool = False,
                 family=socket.AF_INET):
        self.store = Path(store)
        self.roster = roster
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
                "projects": projects(conn),
                "roster_label": ROSTER_LABEL,
                "reports": list(REPORTS),
            })
        if route == "/api/skills":
            return self._with_store(
                lambda conn: skills_report(conn, project, self.server.roster))
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
                roster=None, quiet: bool = False) -> ObservatoryServer:
    """Build the server, refusing a non-loopback address before anything is bound."""
    address = loopback_address(host)
    family = (socket.AF_INET6 if ipaddress.ip_address(address).version == 6
              else socket.AF_INET)
    return ObservatoryServer((address, port), ObservatoryHandler, store=store,
                             roster=roster, quiet=quiet, family=family)


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
    parser.add_argument("--quiet", action="store_true", help="suppress the request log")
    args = parser.parse_args(argv)

    try:
        server = make_server(args.store, args.host, args.port, quiet=args.quiet)
    except NotLoopback as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR could not bind {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 2

    host, port = server.server_address[0], server.server_address[1]
    print(f"Observatory on http://{host}:{port}/ over {args.store}")
    print(f"Roster for never-used skills: {ROSTER_LABEL}")
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
