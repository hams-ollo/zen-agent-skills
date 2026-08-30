#!/usr/bin/env python3
"""Tests for the observatory server, its page shell, and the skills report (`feat-0054`).

Each test names the scenario it proves, from `docs/spec/agent-observatory.md`. Four are covered
here: S-001 and S-002 from `feat-0054`, and S-012 and S-018 from `feat-0055`. The rest of the
contract belongs to `feat-0053` (already covered in `test_observatory.py`) and to the three
report tasks that follow.

The live-session fixtures are deliberately built from real process states rather than from a
stubbed prober, and they are the same three on every operating system: this test runner's own
pid is running, a subprocess that has been waited on is gone, and an entry stamped with another
machine's pid domain cannot be checked. So the assertions below exercise the real check on
whichever platform they run on, and a report that treated registry presence as proof of
liveness fails them everywhere rather than on one CI cell.

Standard library only, matching the rest of `tests/`. The HTTP client is `http.client` against
a loopback server this suite starts and stops itself, so nothing here reaches a remote host.
"""

from __future__ import annotations

import http.client
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import install                            # noqa: E402
from scripts.observatory import db, ingest, serve      # noqa: E402

UI_INDEX = REPO_ROOT / "scripts" / "observatory" / "ui" / "index.html"
COMPANION_SKILL = REPO_ROOT / ".agents" / "skills" / "agent-observatory" / "SKILL.md"

RENDERER_KEY = re.compile(r"\n  \w+: function \(data, into\) \{")


def renderer_source(name: str) -> str:
    """The body of `RENDERERS.<name>` in the page, from its key to the next renderer's.

    Bounded at the next member rather than at the end of the registry, because a renderer
    added below would otherwise be swallowed into the previous one's body and every assertion
    about that body would quietly begin covering two functions. `feat-0055` hit the same trap
    from the other side, when a renderer added *above* a fixed positional slice made it assert
    about the wrong function, and `feat-0058` reached it from below by adding one at the end.
    """
    html = UI_INDEX.read_text(encoding="utf-8")
    start = html.index(f"  {name}: function (data, into) {{")
    following = RENDERER_KEY.search(html, start + 1)
    end = following.start() if following else html.index("\n};", start)
    return html[start:end]


class ServeTestCase(unittest.TestCase):
    """A corpus, a store built from it, and the roster the report counts against.

    The roster is a fixture directory rather than this repository's own `.agents/skills/`, so
    the S-002 assertions do not silently change meaning the day a skill is added or renamed.
    One test, `test_s002_the_roster_is_the_installers_own_skill_directories`, deliberately
    exercises the real one.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obs-serve-"))
        self.corpus = self.tmp / "projects"
        self.project = self.corpus / "D--demo"
        self.project.mkdir(parents=True)
        self.store = self.tmp / "store.db"
        self.skills_dir = self.tmp / "skills"
        self.skills_dir.mkdir()
        # Deliberately not created. An absent registry is the default here so that no test
        # reads the live registry of the machine it is running on: this suite would otherwise
        # report whichever sessions the developer happened to have open, and `meta.projects`
        # would carry their projects. The tests that want a registry make one.
        self.registry = self.tmp / "sessions"
        self._reaped = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- fixtures -------------------------------------------------------------------

    def make_skill(self, name):
        directory = self.skills_dir / name
        directory.mkdir()
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a fixture skill\n---\n\nBody.\n",
            encoding="utf-8", newline="\n")

    @staticmethod
    def record(uuid, sid="s1", skill=None, ts="2026-08-01T10:00:00.000Z"):
        """One assistant record, shaped as the corpus shapes them.

        `attributionSkill` is the field the store reads and the only per-message skill
        attribution the corpus carries: confirmed against the maintainer's 124,918 records on
        2026-08-28, where it appears on 6,518 lines under 21 distinct names.
        """
        return {
            "type": "assistant", "uuid": uuid, "parentUuid": None, "sessionId": sid,
            "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main", "version": "2.1.246",
            "entrypoint": "claude-desktop", "slug": "demo", "isSidechain": False,
            "attributionSkill": skill,
            "message": {"model": "claude-opus-5", "role": "assistant", "content": [],
                        "usage": {"input_tokens": 1, "output_tokens": 2,
                                  "cache_read_input_tokens": 3,
                                  "cache_creation_input_tokens": 4}},
        }

    def write_transcript(self, records, name="session.jsonl", project=None):
        path = (project or self.project) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(json.dumps(r) + "\n" for r in records)
        path.write_bytes(body.encode("utf-8"))
        return path

    def build_store(self, records=None, name="session.jsonl", project=None):
        self.write_transcript(records or [], name=name, project=project)
        return ingest.ingest(self.corpus, self.store)

    def report(self, project=None, roster=None):
        conn = db.connect(self.store)
        try:
            return serve.skills_report(
                conn, project,
                serve.skill_roster(self.skills_dir) if roster is None else roster)
        finally:
            conn.close()

    @staticmethod
    def uses(payload):
        return {row["skill"]: row["uses"] for row in payload["skills"]}

    # -- live-registry fixtures -----------------------------------------------------

    def entry(self, session_id, pid, proc_start=None, pid_domain=None, name=None,
              cwd="D:\\demo", started_at=1787966447301, file_name=None):
        """One registry entry, shaped as `~/.claude/sessions/<pid>.json` shapes them.

        The field names are the harness's own, confirmed against three live entries on
        2026-08-28: `pid`, `sessionId`, `cwd`, `startedAt`, `procStart`, `version`, `kind`,
        `entrypoint`, `pidDomain`, and `name`.
        """
        self.registry.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": pid, "sessionId": session_id, "cwd": cwd, "startedAt": started_at,
            "version": "2.1.247", "kind": "interactive", "entrypoint": "claude-desktop",
            "pidDomain": sys.platform + ":here" if pid_domain is None else pid_domain,
            "name": name or ("session-" + session_id),
        }
        if proc_start is not None:
            payload["procStart"] = proc_start
        path = self.registry / (file_name or f"{pid}.json")
        path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def user_record(uuid, sid="s1", ts="2026-08-01T10:00:00.000Z"):
        """A user record. It creates a session row and no `message_occurrence` row, because
        only assistant records carry the per-message figures that table exists for."""
        return {"type": "user", "uuid": uuid, "parentUuid": None, "sessionId": sid,
                "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main",
                "message": {"role": "user", "content": "hello"}}

    def running_pid(self):
        """A pid that is certainly alive: this test runner's own."""
        return os.getpid()

    def reaped_pid(self):
        """A pid whose process has certainly exited.

        The `Popen` object is kept for the lifetime of the test on purpose. On Windows it
        holds an open handle to the exited process, which both keeps the pid from being
        reused underneath the assertion and is what lets `GetExitCodeProcess` report the
        exit rather than the lookup failing outright. Both routes conclude `gone`.
        """
        proc = subprocess.Popen([sys.executable, "-c", "pass"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait()
        self._reaped.append(proc)
        return proc.pid

    FOREIGN_DOMAIN = "not-this-platform:another-machine"

    def fleet(self, project=None):
        conn = db.connect(self.store)
        try:
            return serve.fleet_report(conn, project, registry=self.registry,
                                      corpus=self.corpus)
        finally:
            conn.close()

    @staticmethod
    def by_session(payload):
        return {row["session_id"]: row for row in payload["sessions"]}


class ServerTestCase(ServeTestCase):
    """Adds a running loopback server for the tests that go over HTTP."""

    def serve_on_loopback(self, roster=None):
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0,
                                   roster=roster, quiet=True,
                                   registry=self.registry, corpus=self.corpus)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        # Cleanups run last-registered-first, so these read backwards on purpose: the loop is
        # stopped, then joined, and only then is the socket closed. Closing first leaves
        # `serve_forever` selecting on a closed handle, which is an OSError on Windows.
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        return server

    def fetch(self, server, path):
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def fetch_json(self, server, path):
        status, body = self.fetch(server, path)
        return status, json.loads(body.decode("utf-8"))


class TestSkillUsage(ServerTestCase):
    """S-001: skill usage is reported from attribution already in the corpus."""

    def replayed_corpus(self):
        """Two messages carrying `doc-sync`, one of which a forked session replays.

        The distinction the acceptance criterion turns on: three lines in the corpus carry the
        attribution, and only two distinct messages do. 5,442 uuids in the maintainer's corpus
        are in this position, so a report counting lines overstates every skill that was ever
        resumed or forked.
        """
        self.build_store([
            self.record("a1", sid="s1", skill="doc-sync"),
            self.record("a2", sid="s1", skill="doc-sync"),
            self.record("a3", sid="s1", skill="fix-batch"),
            self.record("n1", sid="s1"),
            self.record("a1", sid="s-fork", skill="doc-sync"),   # replayed verbatim
        ])

    def test_s001_a_skill_use_count_is_distinct_messages_not_corpus_lines(self):
        """S-001: the totals equal the attribution present in the corpus, counted once.

        The fixture is built so the two candidate oracles disagree: `doc-sync` is on three
        lines and on two messages. An implementation counting occurrences reports 3 here.
        """
        self.replayed_corpus()
        payload = self.report()

        conn = db.connect(self.store)
        try:
            lines = conn.execute(
                "SELECT COUNT(*) AS n FROM message_occurrence o JOIN message m "
                "ON m.uuid = o.uuid WHERE m.attribution_skill = 'doc-sync'"
            ).fetchone()["n"]
        finally:
            conn.close()

        self.assertEqual(lines, 3, "the fixture no longer distinguishes the two oracles")
        self.assertEqual(self.uses(payload)["doc-sync"], 2,
                         "a replayed message was counted twice")
        self.assertEqual(self.uses(payload)["fix-batch"], 1)

    def test_s001_the_reported_total_equals_the_attribution_in_the_corpus(self):
        """S-001's Then, taken as a whole rather than one skill at a time."""
        self.replayed_corpus()
        payload = self.report()

        conn = db.connect(self.store)
        try:
            attributed = conn.execute(
                "SELECT COUNT(*) AS n FROM message WHERE attribution_skill IS NOT NULL"
            ).fetchone()["n"]
        finally:
            conn.close()

        self.assertEqual(attributed, 3)
        self.assertEqual(payload["total_uses"], attributed,
                         "the report's total is not the attribution the corpus carries")
        self.assertNotIn(None, self.uses(payload),
                         "messages carrying no attribution were reported as a skill")

    def test_s001_every_skill_in_the_corpus_is_reported_with_its_name_and_count(self):
        self.replayed_corpus()
        named = self.uses(self.report())
        self.assertEqual({k: v for k, v in named.items() if v},
                         {"doc-sync": 2, "fix-batch": 1})

    def test_s001_the_report_is_served_over_http_and_matches_the_store(self):
        """S-001 through the surface a person actually uses, not only the function."""
        self.replayed_corpus()
        self.make_skill("doc-sync")
        server = self.serve_on_loopback(roster=["doc-sync"])

        status, payload = self.fetch_json(server, "/api/skills")

        self.assertEqual(status, 200)
        self.assertTrue(payload["store_present"])
        self.assertEqual(self.uses(payload), {"doc-sync": 2, "fix-batch": 1})
        self.assertEqual(payload["total_uses"], 3)

    def test_the_scope_selector_restricts_the_report_to_one_project(self):
        """Not a scenario of this task. The scope selector is part of the shell every later
        report inherits, so the query behind it is asserted here rather than left to
        `feat-0055`, which owns S-018 itself."""
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        other = self.corpus / "D--other"
        self.build_store([self.record("b1", sid="s2", skill="doc-sync"),
                          self.record("b2", sid="s2", skill="new-task")],
                         name="other.jsonl", project=other)

        roster = ["doc-sync", "new-task"]
        self.assertEqual(self.uses(self.report(roster=roster))["doc-sync"], 2)
        self.assertEqual(self.uses(self.report("D--demo", roster))["doc-sync"], 1)
        self.assertEqual(self.uses(self.report("D--other", roster))["new-task"], 1)
        self.assertEqual(self.uses(self.report("D--demo", roster))["new-task"], 0,
                         "a skill used only in another project leaked into this one")

    def test_the_scoped_count_deduplicates_history_replayed_within_one_project(self):
        """The scoped query's `COUNT(DISTINCT m.uuid)` had no fixture, so `COUNT(*)` survived
        the suite. It is not cosmetic: on the maintainer's real corpus, scoped to this
        repository, `new-task` would read 510 instead of 339 and five other skills would
        likewise inflate. A forked session replays history into a second transcript of the same
        project, which is the case built here and which the unscoped fixtures never produce."""
        replayed = self.record("r1", sid="s1", skill="new-task")
        # The same message, replayed verbatim into a second session of the SAME project. Two
        # corpus lines, one message, and the count must be one.
        forked = dict(replayed, sessionId="s1-fork")
        self.build_store([replayed, self.record("r2", sid="s1", skill="new-task"), forked])

        roster = ["new-task"]
        self.assertEqual(
            self.uses(self.report("D--demo", roster))["new-task"], 2,
            "the project-scoped count counted a replayed line as a second use")
        self.assertEqual(
            self.uses(self.report(roster=roster))["new-task"], 2,
            "the unscoped and scoped counts disagree over the same single project")


class TestPageBehaviour(ServerTestCase):
    """The page's script is the one deliverable here with no execution coverage, because the
    standard library has no JavaScript engine and this repository ships no dependency to add
    one. An independent verification showed what that costs: the renderer could drop every
    zero-count row and all 29 tests stayed green, which is exactly what S-002 forbids, at the
    surface a person actually reads.

    These are structural assertions over the source plus one real cross-check between the two
    registries. **They are weaker than execution and the bound is stated rather than implied**:
    they pin the specific regressions that were demonstrated to survive, not the page's
    behaviour in general. Executing the page needs a browser, which `feat-0059` will have to
    stand up anyway for the live path.
    """

    def renderer_body(self) -> str:
        """The body of `RENDERERS.skills`, from its key to the next renderer's.

        Anchored on the skills key rather than on `var RENDERERS` plus a fixed span, because
        the registry gained a renderer above this one in `feat-0055` and a positional slice
        silently began asserting about the wrong function. Bounded at the next renderer for
        the mirror-image reason, once `feat-0058` added one below it.
        """
        return renderer_source("skills")

    def test_the_skills_renderer_maps_every_returned_row_without_filtering(self):
        """Kills the mutation that drops zero-count rows at the surface while the API still
        returns them, which no API-level test can see."""
        body = self.renderer_body()
        self.assertIn("data.skills.map(", body,
                      "the renderer no longer maps the rows the API returned")
        for hostile in (".filter(", ".slice(", ".splice("):
            self.assertNotIn(
                f"data.skills{hostile}", body,
                f"the renderer applies {hostile} to the rows before rendering them, so a "
                f"skill the API reported can be missing from the page")

    def test_every_registered_endpoint_is_a_route_the_server_serves(self):
        """The registry and the routing table are two lists that must agree. Renaming an
        endpoint in one leaves the page fetching a 404 with a green suite, because the HTTP
        tests request literal paths rather than the registry's value."""
        endpoints = [r["endpoint"] for r in serve.REPORTS if r["endpoint"]]
        self.assertTrue(endpoints, "no report declares an endpoint, so this asserts nothing")
        server = self.serve_on_loopback()
        for endpoint in endpoints:
            status, _ = self.fetch(server, endpoint)
            self.assertEqual(
                status, 200,
                f"REPORTS declares {endpoint} but the server has no route for it")

    def test_a_report_with_no_endpoint_declares_the_task_that_owes_it(self):
        """The four unbuilt reports must say who owns them rather than rendering as broken."""
        for report in serve.REPORTS:
            if report["endpoint"] is None:
                self.assertTrue(report["owner"],
                                f"report {report['id']} has neither an endpoint nor an owner")
                self.assertTrue(report["scenarios"],
                                f"report {report['id']} names no scenario")

    def test_the_page_sends_the_scope_with_every_report_request(self):
        """Kills the mutation that drops the project parameter page-side, which leaves the
        scope selector visibly present and silently inert."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("function scoped(")
        scoped = html[start:start + 400]
        self.assertIn("STATE.project", scoped,
                      "scoped() no longer consults the selected project")
        self.assertIn("project=", scoped,
                      "scoped() no longer appends the project query parameter")


class TestNeverUsedSkills(ServerTestCase):
    """S-002: a skill that has never been used is reported as zero, not omitted."""

    def test_s002_an_installed_skill_absent_from_the_corpus_is_reported_as_zero(self):
        for name in ("doc-sync", "verifier-agent", "test-quality"):
            self.make_skill(name)
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])

        payload = self.report()
        counts = self.uses(payload)

        self.assertIn("verifier-agent", counts,
                      "a skill the corpus never mentions was left out of the report")
        self.assertEqual(counts["verifier-agent"], 0)
        self.assertEqual(counts["test-quality"], 0)
        self.assertEqual(payload["installed_unused"], 2)
        self.assertEqual(payload["installed_used"], 1)
        self.assertEqual(payload["roster_size"], 3)

    def test_s002_every_installed_skill_appears_even_when_the_corpus_is_empty(self):
        """The degenerate input: nothing has ever been used, so every roster skill is zero.

        A report built by grouping the store and decorating the result reports nothing here,
        which is the shape of the answer S-002 exists to forbid.
        """
        for name in ("doc-sync", "verifier-agent"):
            self.make_skill(name)
        self.build_store([])

        payload = self.report()

        self.assertEqual(self.uses(payload), {"doc-sync": 0, "verifier-agent": 0})
        self.assertEqual(payload["installed_unused"], 2)
        self.assertEqual(payload["total_uses"], 0)

    def test_s002_a_skill_in_the_corpus_but_not_the_roster_is_marked_as_such(self):
        """"Never used" is meaningless without saying what it was counted against, and the
        corpus carries names from outside this kit: `code-review`, `claude-api`, and
        `anthropic-skills:brain-dump` are three of the 21 attributed names on the maintainer's
        machine. Dropping them would understate the total; counting them as roster skills would
        overstate the roster."""
        self.make_skill("doc-sync")
        self.build_store([self.record("a1", sid="s1", skill="doc-sync"),
                          self.record("a2", sid="s1", skill="anthropic-skills:brain-dump")])

        payload = self.report()
        installed = {row["skill"]: row["installed"] for row in payload["skills"]}

        self.assertTrue(installed["doc-sync"])
        self.assertFalse(installed["anthropic-skills:brain-dump"],
                         "a corpus-only skill was counted as part of the installed roster")
        self.assertEqual(payload["roster_size"], 1)
        self.assertEqual(payload["total_uses"], 2, "a corpus-only skill was dropped")

    def test_s002_the_roster_is_the_installers_own_skill_directories(self):
        """The roster comes from `install.discover_skills()` rather than a path written into
        the server, so the two cannot disagree about what the installed set is."""
        self.assertEqual(serve.skill_roster(),
                         [d.name for d in install.discover_skills()])
        self.assertEqual(serve.skill_roster(),
                         sorted(d.name for d in (REPO_ROOT / ".agents" / "skills").iterdir()
                                if (d / "SKILL.md").is_file()))
        self.assertGreater(len(serve.skill_roster()), 0,
                           "the roster is empty, so every S-002 assertion is vacuous")

    def test_s002_the_report_names_the_roster_it_counted_against(self):
        self.make_skill("doc-sync")
        self.build_store([])
        self.assertIn(".agents/skills", self.report()["roster_label"])


class TestLoopbackOnly(ServerTestCase):
    """The one failure here with a consequence outside the repository: a server bound beyond
    loopback publishes one maintainer's whole session corpus to the local network."""

    def test_the_server_binds_a_loopback_address(self):
        server = self.serve_on_loopback()
        bound = ipaddress.ip_address(server.server_address[0])
        self.assertTrue(bound.is_loopback,
                        f"the server bound {bound}, which is not a loopback address")

    def test_the_bound_socket_answers_on_loopback_and_the_route_works(self):
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        server = self.serve_on_loopback(roster=[])
        status, payload = self.fetch_json(server, "/api/skills")
        self.assertEqual(status, 200)
        self.assertEqual(self.uses(payload), {"doc-sync": 1})

    def test_a_non_loopback_address_is_refused_before_anything_is_bound(self):
        for host in ("0.0.0.0", "192.168.1.10", "::"):
            with self.subTest(host=host):
                with self.assertRaises(serve.NotLoopback):
                    serve.loopback_address(host)

    def test_a_hostname_is_refused_rather_than_resolved(self):
        """A name lookup is a network operation, and a hosts file that points `localhost`
        elsewhere must not be able to talk this server onto a routable interface."""
        self.assertEqual(serve.loopback_address("localhost"), "127.0.0.1")
        with self.assertRaises(serve.NotLoopback):
            serve.loopback_address("example.invalid")

    def test_main_exits_two_on_a_non_loopback_host_and_binds_nothing(self):
        """`serve_forever` is stubbed out on purpose, and not for speed.

        Without the stub, an implementation that stopped refusing `0.0.0.0` would bind it and
        then block in the accept loop, so this test would hang rather than fail. A test whose
        failure mode is a hang is worse than no test: it reports nothing and costs the run.
        With the stub, the same defect returns 0 with a recorded bind, which fails twice.
        """
        bound = []
        real_bind = socket.socket.bind
        real_serve = serve.ObservatoryServer.serve_forever

        def recording_bind(self_socket, address):
            bound.append(address)
            return real_bind(self_socket, address)

        socket.socket.bind = recording_bind
        serve.ObservatoryServer.serve_forever = lambda self, *a, **kw: None
        stderr, sys.stderr = sys.stderr, io.StringIO()
        stdout, sys.stdout = sys.stdout, io.StringIO()
        try:
            rc = serve.main(["--host", "0.0.0.0", "--store", str(self.store), "--quiet"])
        finally:
            socket.socket.bind = real_bind
            serve.ObservatoryServer.serve_forever = real_serve
            sys.stderr.close()
            sys.stdout.close()
            sys.stderr, sys.stdout = stderr, stdout

        self.assertEqual(rc, 2, "a non-loopback host was accepted")
        self.assertEqual(bound, [], "a socket was bound before the address was checked")



class TestNoExternalAsset(unittest.TestCase):
    """The page must render with the network unavailable, so it must request nothing."""

    def setUp(self):
        self.html = UI_INDEX.read_text(encoding="utf-8")

    def test_the_page_requests_no_subresource_at_all(self):
        """The strongest form of the acceptance criterion: not "no external subresource" but
        no subresource, so there is nothing for a missing network to fail to deliver."""
        self.assertNotRegex(self.html, r"<script[^>]*\ssrc\s*=",
                            "the page loads a script from somewhere")
        self.assertNotRegex(self.html, r"<link[^>]*\srel\s*=\s*[\"']?stylesheet",
                            "the page loads a stylesheet from somewhere")
        self.assertNotRegex(self.html, r"<(img|iframe|video|audio|source|embed|object)\b",
                            "the page embeds a resource")
        self.assertNotIn("@import", self.html)
        self.assertNotRegex(self.html, r"url\(\s*[\"']?(https?:)?//",
                            "a stylesheet rule fetches something")

    def test_no_src_or_href_attribute_names_a_remote_target(self):
        targets = re.findall(r"\b(?:src|href)\s*=\s*[\"']([^\"']*)[\"']", self.html)
        for target in targets:
            with self.subTest(target=target):
                self.assertFalse(target.startswith("//"), "protocol-relative URL")
                self.assertNotRegex(target, r"^[a-zA-Z][a-zA-Z0-9+.-]*:",
                                    "absolute URL with a scheme")

    def test_the_acceptance_greps_find_nothing(self):
        """The task's own grep, run as a test rather than by hand."""
        ui_dir = UI_INDEX.parent
        pattern = re.compile(r"cdn|unpkg|jsdelivr|googleapis|<script src=\"http",
                             re.IGNORECASE)
        for path in sorted(ui_dir.rglob("*")):
            if path.is_file():
                self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")),
                                  f"{path} names an external asset host")

    def test_no_javascript_toolchain_is_introduced(self):
        for name in ("package.json", "package-lock.json", "yarn.lock",
                     "pnpm-lock.yaml", "bun.lockb"):
            self.assertEqual(list(REPO_ROOT.rglob(name)), [],
                             f"{name} was introduced")
        self.assertEqual([p for p in REPO_ROOT.rglob("node_modules") if p.is_dir()], [],
                         "node_modules was introduced")

    def test_the_server_imports_nothing_that_can_reach_a_remote_host(self):
        """`urllib.parse` is deliberately not on this list. It is a string parser and opens
        nothing; `urllib.request` is the one that can, and it is."""
        source = Path(serve.__file__).read_text(encoding="utf-8")
        for name in ("urllib.request", "http.client", "requests", "ftplib", "smtplib",
                     "telnetlib", "xmlrpc"):
            self.assertNotIn(f"import {name}", source,
                             f"serve.py imports {name}")


class TestServingOpensNoRemoteConnection(ServerTestCase):
    """S-022's shape, applied to the surface `feat-0054` adds. `feat-0053` proved it for the
    ingester; a server that fetched anything while rendering would reopen the hole."""

    def test_a_full_page_and_data_load_connects_only_to_loopback(self):
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        server = self.serve_on_loopback(roster=["doc-sync", "verifier-agent"])

        targets = []
        real_connect = socket.socket.connect

        def recording_connect(self_socket, address):
            targets.append(address)
            return real_connect(self_socket, address)

        socket.socket.connect = recording_connect
        try:
            page_status, page = self.fetch(server, "/")
            meta_status, meta = self.fetch_json(server, "/api/meta")
            skills_status, skills = self.fetch_json(server, "/api/skills")
        finally:
            socket.socket.connect = real_connect

        self.assertEqual((page_status, meta_status, skills_status), (200, 200, 200))
        self.assertIn(b"Agent observatory", page)
        self.assertEqual(meta["projects"], ["D--demo"])
        self.assertEqual(self.uses(skills)["verifier-agent"], 0)
        self.assertTrue(targets, "nothing connected, so this asserted nothing")
        for address in targets:
            with self.subTest(address=address):
                self.assertTrue(ipaddress.ip_address(address[0]).is_loopback,
                                f"a connection was made to {address[0]}")


class TestPageShell(ServerTestCase):
    """The shell is a deliverable in its own right: four later tasks slot their report into it
    rather than each reinventing layout, navigation, and the scope selector."""

    def test_every_report_in_the_contracts_proposed_surface_has_a_slot(self):
        ids = [report["id"] for report in serve.REPORTS]
        self.assertEqual(ids, ["fleet", "skills", "waves", "cost", "health"])
        for report in serve.REPORTS:
            with self.subTest(report=report["id"]):
                self.assertTrue(report["scenarios"], "a report claims no scenario")
                built = report["endpoint"] is not None
                self.assertEqual(built, report["owner"] is None,
                                 "a report is both built and owed, or neither")

    def test_the_unbuilt_reports_name_the_task_that_owes_them(self):
        """The set shrinks as reports land. `feat-0058` built the health report, so `health`
        left it; `waves` and `cost` are still owed and must still name their owner."""
        owed = {r["id"]: r["owner"] for r in serve.REPORTS if r["endpoint"] is None}
        # Every report in the contract's Proposed Surface is now built, so this map is empty
        # and the equality alone no longer proves anything: an empty expectation is satisfied
        # by a registry that lost the `owner` field entirely. The invariant below is what the
        # test is actually for, and it survives the map being empty: a report is owed if and
        # only if it names the task that owes it, so a sixth report added without an endpoint
        # and without an owner fails here rather than rendering a blank panel.
        self.assertEqual(owed, {})
        for report in serve.REPORTS:
            with self.subTest(report=report["id"]):
                self.assertEqual(
                    report["endpoint"] is None, report["owner"] is not None,
                    f"report {report['id']} either serves nothing and names nobody, or "
                    f"serves a route while still claiming to be owed")

    def test_the_shell_renders_navigation_from_the_registry_not_from_markup(self):
        """A shell that hardcoded its tabs would make each later task edit the markup, which is
        the reinvention this task exists to prevent."""
        html = UI_INDEX.read_text(encoding="utf-8")
        self.assertIn("RENDERERS", html)
        for report in serve.REPORTS:
            self.assertNotIn(f">{report['title']}</button>", html,
                             "a report tab is hardcoded in the markup")

    def test_the_scope_selectors_choice_reaches_the_report_over_http(self):
        """The route half of the scope selector, which the direct-call test cannot reach.

        Found by mutation: dropping the `project` query parameter in `do_GET` left every test
        green, because the scope test called the report function directly and nothing drove
        the URL the page actually requests.
        """
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        other = self.corpus / "D--other"
        self.build_store([self.record("b1", sid="s2", skill="doc-sync")],
                         name="other.jsonl", project=other)
        server = self.serve_on_loopback(roster=[])

        _, everywhere = self.fetch_json(server, "/api/skills")
        _, here = self.fetch_json(server, "/api/skills?project=D--demo")

        self.assertEqual(self.uses(everywhere)["doc-sync"], 2)
        self.assertEqual(here["project"], "D--demo",
                         "the requested scope did not reach the report")
        self.assertEqual(self.uses(here)["doc-sync"], 1,
                         "the scope selector's choice was ignored by the route")

    def test_the_meta_route_carries_the_registry_and_the_scope_options(self):
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        server = self.serve_on_loopback(roster=[])
        status, meta = self.fetch_json(server, "/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in meta["reports"]],
                         [r["id"] for r in serve.REPORTS])
        self.assertEqual(meta["projects"], ["D--demo"])

    def test_a_missing_store_is_stated_rather_than_reported_as_an_empty_corpus(self):
        """S-007's habit, applied to the surface: "the ingester has not run" and "the corpus
        holds nothing" are different answers and the page must not merge them."""
        server = self.serve_on_loopback(roster=[])
        status, payload = self.fetch_json(server, "/api/skills")
        self.assertEqual(status, 200)
        self.assertFalse(payload["store_present"])
        self.assertIn("ingest.py", payload["message"])
        self.assertFalse(self.store.exists(),
                         "answering a GET created a store as a side effect")

    def test_the_surface_serves_reads_only(self):
        """`S-019` and `S-020` are `feat-0060`'s and are not claimed here. This asserts the
        weaker thing this task is responsible for: no route on this surface writes."""
        self.build_store([self.record("a1", sid="s1")])
        server = self.serve_on_loopback(roster=[])
        host, port = server.server_address[0], server.server_address[1]
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            with self.subTest(method=method):
                conn = http.client.HTTPConnection(host, port, timeout=10)
                try:
                    conn.request(method, "/api/skills")
                    self.assertEqual(conn.getresponse().status, 405)
                finally:
                    conn.close()

    def test_an_unknown_route_is_a_404_rather_than_the_page(self):
        server = self.serve_on_loopback(roster=[])
        status, _ = self.fetch(server, "/api/nothing-here")
        self.assertEqual(status, 404)


class TestFleetState(ServerTestCase):
    """S-012: a running session is distinguished from an ended one."""

    def two_sessions(self):
        """Two sessions in one project, with distinct last activity."""
        self.build_store([self.record("a1", sid="s-live", ts="2026-08-01T10:00:00.000Z")],
                         name="live.jsonl")
        self.build_store([self.record("b1", sid="s-done", ts="2026-08-02T11:00:00.000Z")],
                         name="done.jsonl")

    def test_s012_a_session_in_the_live_registry_is_reported_as_running(self):
        self.two_sessions()
        self.entry("s-live", self.running_pid())

        payload = self.fleet()
        row = self.by_session(payload)["s-live"]

        self.assertEqual(row["state"], "running")
        self.assertEqual(row["registry"], "live")
        self.assertEqual(payload["totals"]["running"], 1)

    def test_s012_a_session_absent_from_the_registry_is_reported_as_ended(self):
        self.two_sessions()
        self.entry("s-live", self.running_pid())

        row = self.by_session(self.fleet())["s-done"]

        self.assertEqual(row["state"], "ended")
        self.assertEqual(row["registry"], "absent")
        self.assertIsNone(row["pid"])

    def test_s012_each_session_carries_its_project_its_branch_and_its_last_activity(self):
        """The three fields S-012's Then names, on both sides of the distinction."""
        self.two_sessions()
        self.entry("s-live", self.running_pid())

        rows = self.by_session(self.fleet())

        for session_id in ("s-live", "s-done"):
            with self.subTest(session=session_id):
                self.assertEqual(rows[session_id]["project"], "D--demo")
                self.assertEqual(rows[session_id]["branch"], "main")
        self.assertEqual(rows["s-live"]["last_activity"], "2026-08-01T10:00:00.000Z")
        self.assertEqual(rows["s-done"]["last_activity"], "2026-08-02T11:00:00.000Z")

    def test_s012_a_stale_registry_entry_is_reported_ended_rather_than_running(self):
        """The consequential risk the task names. A registry entry can outlive the process
        that wrote it, so an implementation treating presence as proof reports a crashed
        session as live. Here the entry is present and its process is certainly gone, and the
        report has to say so rather than trust the file."""
        self.two_sessions()
        self.entry("s-live", self.reaped_pid())

        payload = self.fleet()
        row = self.by_session(payload)["s-live"]

        self.assertEqual(row["state"], "ended",
                         "a registry entry whose process is gone was reported as running")
        self.assertEqual(row["registry"], "stale")
        self.assertTrue(row["evidence"], "a stale entry was reported with no reason given")
        self.assertEqual(payload["totals"]["running"], 0)
        self.assertEqual(payload["totals"]["stale_entries"], 1,
                         "a stale entry was absorbed instead of counted")

    def test_s012_an_unverifiable_entry_is_reported_unverified_rather_than_running(self):
        """The pid here is alive: it is this test runner's own. What makes it unverifiable is
        that the entry claims another machine's pid domain, so the pid names no process on
        this one. An implementation that ignored the domain would report running, which is
        the same failure as trusting a stale entry reached by a different route."""
        self.two_sessions()
        self.entry("s-live", self.running_pid(), pid_domain=self.FOREIGN_DOMAIN)

        payload = self.fleet()
        row = self.by_session(payload)["s-live"]

        self.assertEqual(row["state"], "unverified",
                         "a pid from another machine's table was read as a local process")
        self.assertEqual(row["registry"], "unchecked")
        self.assertEqual(payload["totals"]["running"], 0)
        self.assertEqual(payload["totals"]["unverified"], 1)

    def test_s012_the_report_renders_with_the_registry_absent(self):
        self.two_sessions()
        self.assertFalse(self.registry.exists(), "the fixture created a registry")

        payload = self.fleet()

        self.assertFalse(payload["registry"]["present"])
        self.assertEqual(payload["registry"]["entries"], 0)
        self.assertEqual(payload["totals"]["sessions"], 2)
        self.assertEqual(payload["totals"]["ended"], 2)
        self.assertFalse(self.registry.exists(),
                         "reading an absent registry created one")

    def test_s012_the_report_renders_with_the_registry_empty(self):
        """Present and holding nothing is a different answer from absent, and both render."""
        self.two_sessions()
        self.registry.mkdir(parents=True)

        payload = self.fleet()

        self.assertTrue(payload["registry"]["present"])
        self.assertEqual(payload["registry"]["entries"], 0)
        self.assertEqual(payload["totals"]["ended"], 2)

    def test_s012_the_report_states_which_check_it_ran_and_what_it_does_with_a_stale_entry(
            self):
        """A report that says "running" without saying what it checked is the thing this
        task's Risks section calls worse than one that says it cannot tell."""
        self.two_sessions()
        payload = self.fleet()

        self.assertTrue(payload["liveness_check"])
        for outcome in ("running", "ended", "unverified"):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, payload["liveness_policy"],
                              f"the stated policy does not say when a session is {outcome}")

    def test_s012_the_report_is_served_over_http_and_matches_the_store(self):
        """S-012 through the surface a person actually uses, not only the function."""
        self.two_sessions()
        self.entry("s-live", self.running_pid())
        server = self.serve_on_loopback(roster=[])

        status, payload = self.fetch_json(server, "/api/fleet")

        self.assertEqual(status, 200)
        self.assertTrue(payload["store_present"])
        rows = self.by_session(payload)
        self.assertEqual(rows["s-live"]["state"], "running")
        self.assertEqual(rows["s-done"]["state"], "ended")
        self.assertEqual(payload["totals"], self.fleet()["totals"])

    def test_s012_two_entries_naming_one_session_are_resolved_by_the_stronger_claim(self):
        """`live_sessions()` states this rule and nothing asserted it, so last-writer-wins
        survived the whole suite when an outside verification tried it.

        Entries are read in sorted filename order, so the fixture runs the collision both
        ways round: the alive entry sorts first for one session and last for the other. A
        rule that took whichever file it read last gets one of them wrong whichever way it
        leans, which is the point of testing both.
        """
        self.two_sessions()
        self.entry("s-live", self.running_pid(), file_name="a-alive.json")
        self.entry("s-live", self.reaped_pid(), file_name="z-gone.json")
        self.entry("s-done", self.reaped_pid(), file_name="a-gone.json")
        self.entry("s-done", self.running_pid(), file_name="z-alive.json")

        rows = self.by_session(self.fleet())

        for session_id in ("s-live", "s-done"):
            with self.subTest(session=session_id):
                self.assertEqual(rows[session_id]["state"], "running",
                                 "the answer depended on which entry file sorted last")

    def test_s012_a_live_sessions_start_time_is_a_timestamp_not_raw_milliseconds(self):
        """`_started_at()` converts on the server, and its docstring says why: the page's
        script has no execution coverage, so a date the page formats itself is a date nothing
        can check. Nothing checked the conversion either, and returning the raw milliseconds
        survived the suite."""
        self.two_sessions()
        self.entry("s-live", self.running_pid(), started_at=1787966447301)

        rows = self.by_session(self.fleet())

        self.assertEqual(rows["s-live"]["started_at"], "2026-08-29T01:20:47.301000+00:00")
        self.assertIsNone(rows["s-done"]["started_at"],
                          "a session with no registry entry reported a start time")

    def test_s012_an_entry_whose_start_time_is_unusable_reports_none_not_a_crash(self):
        """The registry belongs to another program. A field that is missing, or is a string
        where a number was expected, must not take the report down with it."""
        self.two_sessions()
        self.entry("s-live", self.running_pid(), started_at="not-a-number")

        self.assertIsNone(self.by_session(self.fleet())["s-live"]["started_at"])

    def test_s012_a_running_session_sorts_above_an_ended_one_that_is_more_recent(self):
        """The report answers a question about now, so `s-live` leads even though `s-done`
        has the later timestamp. Sorting by activity alone would bury the running session."""
        self.two_sessions()
        self.entry("s-live", self.running_pid())

        order = [row["session_id"] for row in self.fleet()["sessions"]]

        self.assertEqual(order, ["s-live", "s-done"])


class TestFleetProjects(ServerTestCase):
    """S-018: every project reported in one place, and the per-project figures add up."""

    def three_projects(self):
        """Two projects in the store, a live entry in each, and a third live session the
        store has never seen.

        The mix is the point. The summing property is easy to hold when every session came
        out of one query and hard when the report unions two sources, which is exactly what
        this report does, so a fixture drawn only from the store would not test it.
        """
        other = self.corpus / "D--other"
        self.build_store([self.record("a1", sid="s-a1"), self.record("a2", sid="s-a2")])
        self.build_store([self.record("b1", sid="s-b1")], name="other.jsonl", project=other)
        self.entry("s-a1", self.running_pid())
        self.entry("s-b1", self.reaped_pid())
        self.entry("s-ghost", self.running_pid(), pid_domain=self.FOREIGN_DOMAIN,
                   file_name="ghost.json")

    def test_s018_per_project_figures_sum_to_the_unrestricted_figures(self):
        """S-018's arithmetic, asserted rather than inspected. This is the criterion the task
        made arithmetic on purpose: dropping a session leaves every panel rendering and only
        the sum wrong."""
        self.three_projects()
        everywhere = self.fleet()
        self.assertTrue(everywhere["projects"], "the report declares no projects at all")

        summed = {"sessions": 0, "running": 0, "ended": 0, "unverified": 0}
        for bucket in everywhere["projects"]:
            scoped = self.fleet(bucket["project"])
            for figure in summed:
                summed[figure] += scoped["totals"][figure]

        for figure, total in summed.items():
            with self.subTest(figure=figure):
                self.assertEqual(
                    total, everywhere["totals"][figure],
                    f"the per-project {figure} figures do not sum to the unrestricted one")
        self.assertEqual(everywhere["totals"]["sessions"], 4,
                         "the fixture no longer holds the four sessions this counts on")

    def test_s018_a_live_session_matching_no_known_project_is_counted_not_dropped(self):
        """The quiet failure the task's Risks section names: a session nothing can attribute
        is dropped, S-018's summing property goes false, and every panel still renders."""
        self.three_projects()
        payload = self.fleet()

        row = self.by_session(payload)["s-ghost"]
        self.assertEqual(row["project"], payload["unattributed_label"])
        self.assertFalse(row["in_store"])

        buckets = {bucket["project"]: bucket for bucket in payload["projects"]}
        self.assertIn(payload["unattributed_label"], buckets,
                      "a session attributed to no project vanished from the breakdown")
        self.assertEqual(buckets[payload["unattributed_label"]]["sessions"], 1)

    def test_s018_a_live_session_absent_from_the_store_is_placed_by_its_transcript(self):
        """A session that started minutes ago has a transcript and no store row yet, and the
        directory that transcript sits in is its project.

        Deriving the project from the recorded working directory instead cannot work, which is
        why nothing here tries. Over this maintainer's corpus on 2026-08-28 the project is not
        a function of the working directory at all, two projects being reached from more than
        one, and six of twenty-six distinct `(cwd, project)` pairs disagree under the most
        permissive rule tried. The working directory drifts within a session; the project
        directory does not.
        """
        self.build_store([self.record("a1", sid="s-a1")])
        # Written and never ingested, exactly as a just-started session's transcript is.
        self.write_transcript([], name="s-fresh.jsonl")
        self.entry("s-fresh", self.running_pid())

        row = self.by_session(self.fleet())["s-fresh"]

        self.assertEqual(row["project"], "D--demo",
                         "a live session was not placed by the transcript beside it")
        self.assertEqual(row["state"], "running")
        self.assertFalse(row["in_store"])
        self.assertEqual(self.fleet()["totals"]["not_yet_ingested"], 1)

    def test_s018_the_per_project_breakdown_counts_each_state_not_only_the_sessions(self):
        """The page renders running, unverified, and ended as columns beside the session
        count, and an outside verification found nothing asserting any of the three: making
        every project report zero running sessions left all 102 tests green.

        That is the same shape `feat-0054`'s verification found in the skills renderer, a
        figure correct in the header and wrong in the table beside it, so the expected counts
        are written out here rather than derived, and the breakdown is then tied to the
        scoped report so the two paths cannot drift apart in silence.
        """
        self.three_projects()
        payload = self.fleet()
        buckets = {bucket["project"]: bucket for bucket in payload["projects"]}

        self.assertEqual(
            {name: (bucket["sessions"], bucket["running"], bucket["unverified"],
                    bucket["ended"], bucket["stale_entries"])
             for name, bucket in buckets.items()},
            {"D--demo": (2, 1, 0, 1, 0),
             "D--other": (1, 0, 0, 1, 1),
             payload["unattributed_label"]: (1, 0, 1, 0, 0)})

        for name, bucket in buckets.items():
            with self.subTest(project=name):
                totals = self.fleet(name)["totals"]
                figures = ("sessions", "running", "ended", "unverified", "stale_entries")
                self.assertEqual(
                    {figure: bucket[figure] for figure in figures},
                    {figure: totals[figure] for figure in figures},
                    "a project's breakdown row disagrees with that project's own report")

    def test_s018_a_stored_session_with_no_project_is_bucketed_rather_than_left_out(self):
        """The defensive half of the unattributed bucket. The live half is well covered; this
        branch is reached only by a stored session whose project is NULL, which no corpus
        shape produces today because the ingester derives it from a directory name that
        always exists, and 0 of 155 stored sessions carry one.

        It is asserted anyway because the criterion it serves is arithmetic: an unbucketed row
        breaks the sum while every panel still renders, which is exactly the failure the task
        made this criterion arithmetic to catch. The row is written directly, since nothing
        else can produce it.
        """
        self.build_store([self.record("a1", sid="s-a1")])
        conn = db.connect(self.store)
        try:
            conn.execute(
                "INSERT INTO session (session_id, project) VALUES ('s-null', NULL)")
            conn.commit()
        finally:
            conn.close()

        payload = self.fleet()

        self.assertEqual(self.by_session(payload)["s-null"]["project"],
                         payload["unattributed_label"],
                         "a stored session with no project was left unbucketed")
        summed = sum(self.fleet(bucket["project"])["totals"]["sessions"]
                     for bucket in payload["projects"])
        self.assertEqual(summed, payload["totals"]["sessions"])

    def test_s018_the_state_counts_partition_the_sessions(self):
        """Every session is in exactly one state, at every scope. A session counted twice, or
        in none, would leave the header figures disagreeing with their own breakdown."""
        self.three_projects()
        scopes = [None] + [bucket["project"] for bucket in self.fleet()["projects"]]

        for scope in scopes:
            with self.subTest(scope=scope):
                totals = self.fleet(scope)["totals"]
                self.assertEqual(
                    totals["running"] + totals["ended"] + totals["unverified"],
                    totals["sessions"],
                    "a session is in two states at once, or in none")

    def test_s018_the_scoped_report_carries_only_that_projects_sessions(self):
        """The route half of the scope selector, which the direct call cannot reach."""
        self.three_projects()
        server = self.serve_on_loopback(roster=[])

        _, everywhere = self.fetch_json(server, "/api/fleet")
        _, here = self.fetch_json(server, "/api/fleet?project=D--demo")

        self.assertEqual(here["project"], "D--demo",
                         "the requested scope did not reach the report")
        self.assertEqual({row["project"] for row in here["sessions"]}, {"D--demo"},
                         "another project's sessions leaked into a scoped report")
        self.assertEqual(here["totals"]["sessions"], 2)
        self.assertEqual(everywhere["totals"]["sessions"], 4)

    def test_s018_the_scope_selector_offers_every_project_the_fleet_counts(self):
        """A project the report counts and the selector cannot reach is a figure a reader can
        see and not follow."""
        self.three_projects()
        server = self.serve_on_loopback(roster=[])

        _, meta = self.fetch_json(server, "/api/meta")
        counted = {bucket["project"] for bucket in self.fleet()["projects"]}

        self.assertTrue(counted)
        self.assertLessEqual(
            counted, set(meta["projects"]),
            "the fleet report counts a project the scope selector never offers")

    def test_s018_a_project_whose_session_carries_no_message_is_still_offered(self):
        """`message_occurrence` holds assistant messages only, so a session that produced
        none has no row there. Four of this maintainer's 155 sessions were in that position
        on 2026-08-28, and a selector built from occurrences alone never offered their
        project while the fleet report counted it."""
        quiet = self.corpus / "D--quiet"
        self.build_store([self.user_record("u1", sid="s-quiet")],
                         name="quiet.jsonl", project=quiet)

        conn = db.connect(self.store)
        try:
            occurrences = conn.execute(
                "SELECT COUNT(*) AS n FROM message_occurrence WHERE project = 'D--quiet'"
            ).fetchone()["n"]
            self.assertEqual(occurrences, 0,
                             "the fixture no longer builds a session with no occurrence row")
            self.assertIn("D--quiet", serve.projects(conn),
                          "a project whose only session carries no message was not offered")
        finally:
            conn.close()


class TestSkillsReportAcrossProjects(ServerTestCase):
    """S-018 applied to the report `feat-0054` shipped, because the scenario says "any
    report" rather than "the fleet report"."""

    def test_s018_the_skills_report_identity_holds_when_no_message_spans_projects(self):
        other = self.corpus / "D--other"
        self.build_store([self.record("a1", sid="s1", skill="doc-sync"),
                          self.record("a2", sid="s1", skill="new-task")])
        self.build_store([self.record("b1", sid="s2", skill="doc-sync")],
                         name="other.jsonl", project=other)
        roster = ["doc-sync", "new-task"]

        everywhere = self.report(roster=roster)["total_uses"]
        summed = sum(self.report(project, roster)["total_uses"]
                     for project in ("D--demo", "D--other"))

        self.assertEqual(everywhere, 3)
        self.assertEqual(summed, everywhere,
                         "the per-project skill figures do not sum to the unrestricted one")

    def test_s018_a_message_replayed_into_another_project_is_the_stated_bound(self):
        """The one case where the identity above does not hold, pinned rather than left for
        someone to find in a figure.

        A forked or resumed session replays earlier history verbatim, and where the fork lands
        in a different project directory the same message occurs under two projects: the
        unscoped figure counts the message once and each scoped figure counts it, so the sum
        exceeds the total. It does not happen in this maintainer's corpus, where 0 of 54,222
        messages appear under more than one project as of 2026-08-28, which is why the
        identity holds there. This test exists so that the day it stops holding, the change is
        visible here rather than in a number nobody rechecks.
        """
        other = self.corpus / "D--other"
        replayed = self.record("r1", sid="s1", skill="doc-sync")
        self.build_store([replayed])
        self.build_store([dict(replayed, sessionId="s1-fork")],
                         name="other.jsonl", project=other)
        roster = ["doc-sync"]

        everywhere = self.report(roster=roster)["total_uses"]
        summed = sum(self.report(project, roster)["total_uses"]
                     for project in ("D--demo", "D--other"))

        self.assertEqual(everywhere, 1, "the same message was counted twice in the total")
        self.assertEqual(summed, 2,
                         "the scoped figures no longer both count a cross-project replay")
        self.assertGreater(
            summed, everywhere,
            "the cross-project bound this test pins no longer holds. If the skills report "
            "now attributes each message to one project, S-018's identity is unconditional "
            "and the conformance matrix should stop stating this bound")


class TestFleetPageBehaviour(ServerTestCase):
    """Structural assertions over the page's source, carrying the bound `feat-0054` stated:
    the standard library has no JavaScript engine and this repository ships no dependency to
    add one, so these pin the specific regressions that were shown to survive a green suite,
    not the page's behaviour in general.
    """

    def renderer_body(self) -> str:
        """The body of `RENDERERS.fleet`, from its key to the next renderer's."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("  fleet: function (data, into) {")
        end = html.index("  skills: function (data, into) {")
        self.assertGreater(end, start, "the fleet renderer is no longer where this looks")
        return html[start:end]

    def test_the_fleet_renderer_maps_every_returned_row_without_filtering(self):
        """Kills the mutation that drops rows at the surface while the API still returns
        them, which no API-level test can see. An independent verification of `feat-0054`
        showed the shape: the skills renderer could drop every zero-count row with all
        twenty-nine tests green."""
        body = self.renderer_body()
        for collection in ("data.sessions", "data.projects"):
            with self.subTest(collection=collection):
                self.assertIn(collection + ".map(", body,
                              f"the renderer no longer maps the {collection} the API returned")
                for hostile in (".filter(", ".slice(", ".splice("):
                    self.assertNotIn(
                        collection + hostile, body,
                        f"the renderer applies {hostile} to {collection} before rendering, "
                        f"so a session the report counted can be missing from the page")

    def test_the_fleet_renderer_builds_no_interactive_element_of_its_own(self):
        """The renderer must not construct an action directly, because `S-019`'s enumeration
        is derived from one tagged construction site (`actionControl`) and an element built
        anywhere else escapes it.

        This assertion predates the actions and its reason has changed rather than weakened:
        it used to mean the surface offered nothing, and now it means the surface offers only
        what the registry declares.
        """
        body = self.renderer_body()
        for forbidden in ("<a ", 'el("a"', 'el("button"', 'el("form"', 'el("input"',
                          "addEventListener", "location.href", "window.open", "fetch("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body,
                                 f"the fleet renderer builds {forbidden} directly instead of "
                                 f"going through actionControl, so it is outside the "
                                 f"enumeration S-019 is proven by")
        self.assertIn("actionCell(row)", body,
                      "the renderer no longer offers the declared actions at all")

    def test_the_fleet_renderer_does_not_contradict_the_footnote_about_being_live(self):
        """Both sentences are on screen at once, so they cannot be allowed to disagree.

        An outside verification read "Correct as of when this report was requested, not
        live: press Refresh to ask again" directly above a footer saying "Following the
        corpus live", and then watched the page re-fetch on its own, which made the first
        sentence false rather than merely stale.
        """
        body = self.renderer_body()
        # Comments stripped first. The phrase appears in the comment that explains this very
        # fix, so asserting on the raw body matched prose rather than code, which is the
        # third time in this component that an assertion has been satisfied or broken by a
        # sentence rather than by a statement.
        code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)

        self.assertIn("STATE.live", code,
                      "the fleet subtitle does not consult whether the page is following, "
                      "so it can claim the opposite of what the footnote says")
        self.assertNotIn("not live", code,
                         "the fleet subtitle still asserts the page is not live")

    def test_the_fleet_renderer_reports_the_state_the_server_established(self):
        """Kills the mutation that derives liveness page-side, for instance from whether a
        row carries a pid, which would put the decision somewhere no test can reach."""
        body = self.renderer_body()
        self.assertIn("text: row.state", body,
                      "the state badge no longer prints the state the report established")
        for stated in ("liveness_check", "liveness_policy", "unattributed_label"):
            with self.subTest(stated=stated):
                self.assertIn(stated, body,
                              f"the page no longer tells a reader about {stated}")

    def test_the_default_report_comes_from_the_registry_not_a_hardcoded_id(self):
        """`feat-0054` opened on the skills report by name. The registry is the contract's
        Proposed Surface order and Fleet leads it, so a hardcoded default has to be edited
        again the next time that order changes."""
        html = UI_INDEX.read_text(encoding="utf-8")
        boot = html[html.index("function boot("):][:900]
        state = html[html.index("var STATE = "):][:200]

        self.assertIn("STATE.reports[0]", boot,
                      "the page no longer takes its default report from the registry")
        self.assertNotIn('current: "skills"', state,
                         "the default report is hardcoded again")
        self.assertEqual(serve.REPORTS[0]["id"], "fleet",
                         "Fleet no longer leads the registry, so the default has moved")


class TestActionBoundary(ServerTestCase):
    """S-019: the reporting surface offers no session mutation.

    "Nothing mutates a session" is untestable as prose and decidable as a list, which is why
    the contract phrases it as an enumeration. The list is `serve.ACTIONS`, the page renders
    from it and tags each element with `data-action`, and the assertions below resolve the two
    against each other so a control added to the page without an entry is caught mechanically
    rather than by a reviewer noticing.
    """

    def page(self) -> str:
        return UI_INDEX.read_text(encoding="utf-8")

    def construction_site(self) -> str:
        """The body of `actionControl`, the one place an action element is built."""
        html = self.page()
        start = html.index("function actionControl(")
        end = html.index("function actionCell(", start)
        return html[start:end]

    def test_s019_every_action_the_surface_offers_resolves_to_a_non_mutating_kind(self):
        """S-019's Then, over the enumeration itself: an action referencing a session must
        resolve to navigation or to a command presented for a person to run. Both permitted
        kinds are that by construction, and there is deliberately no third."""
        self.assertEqual(set(serve.ACTION_KINDS), {"navigate", "copy-command"},
                         "a third action kind was introduced, and S-019 permits only "
                         "navigation and a command presented for a person to run")
        self.assertTrue(serve.ACTIONS, "the surface declares no actions, so this asserts "
                                       "nothing and S-019 is vacuous again")
        for action in serve.ACTIONS:
            with self.subTest(action=action["id"]):
                self.assertIn(action["kind"], serve.ACTION_KINDS)
                for key in ("id", "kind", "label", "field", "note"):
                    self.assertTrue(action.get(key) or key == "template",
                                    f"action {action['id']} declares no {key}")

    def test_s019_the_enumeration_is_derived_from_the_page_not_maintained_by_hand(self):
        """The criterion the task states in those words: a newly added action must appear in
        the enumeration without this test being edited.

        It holds because every `data-action` the page carries has to resolve to a declared
        action. A control tagged with an id nobody declared fails here; an untagged control
        fails the next test.
        """
        declared = {action["id"] for action in serve.ACTIONS}
        tagged = set(re.findall(r'"data-action":\s*([A-Za-z_.]+|"[^"]+")', self.page()))

        self.assertTrue(tagged, "the page tags no element, so the enumeration is unenforced")
        for token in tagged:
            with self.subTest(token=token):
                if token.startswith('"'):
                    self.assertIn(token.strip('"'), declared,
                                  "the page tags an element with an action id the server "
                                  "does not declare")
                else:
                    self.assertEqual(
                        token, "action.id",
                        "the page tags an element from something other than the declared "
                        "action, so the two lists can drift apart")

    def test_s019_every_element_the_construction_site_returns_is_tagged(self):
        """The other half. The enumeration is only complete if no element escapes it, which
        holds because all three are built in one function and every one of its returns carries
        the tag. Counting is the mechanical form of that claim."""
        body = self.construction_site()
        built = sum(body.count(f'el("{tag}"') for tag in ("a", "button", "code", "input",
                                                          "form", "select", "textarea"))
        tagged = body.count('"data-action"')

        self.assertGreater(built, 0, "the construction site builds nothing")
        self.assertEqual(built, tagged,
                         f"actionControl builds {built} element(s) and tags {tagged}: an "
                         f"untagged element is outside the enumeration S-019 is proven by")

    def test_s019_the_construction_site_cannot_reach_a_session(self):
        """A navigate action opens something and a copy-command writes to the clipboard.
        Neither may acquire a way to talk to a session, which is what these would be."""
        body = self.construction_site()
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon",
                          "location.href =", "document.forms", "method=\"post\""):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body,
                                 f"the action construction site introduces {forbidden}, "
                                 f"which is a route to a session rather than navigation or "
                                 f"a command presented for a person to run")

    # The renderers and helpers permitted to build an interactive element, and what each is
    # for. `renderNav` builds the report tabs, which are page chrome and reference no session;
    # `actionControl` builds every session-directed control and tags each one. Anything else
    # building a control is unreviewed surface, which is what the widened check below catches.
    INTERACTIVE_BUILDERS = {"renderNav", "actionControl"}
    INTERACTIVE_TAGS = ("a", "button", "form", "input", "select", "textarea")

    def script_blocks(self) -> dict:
        """Every named function body in the page's script, renderers included.

        Renderers are object-literal members (`  fleet: function (data, into) {`) rather than
        top-level declarations, so both forms are recognised. Splitting by name is what makes
        the assertion below name the offender instead of just failing.
        """
        html = self.page()
        script = html[html.index("<script>"):html.index("</script>")]
        marks = list(re.finditer(r"\n(?:function (\w+)\(|  (\w+): function \()", script))
        blocks = {}
        for index, mark in enumerate(marks):
            end = marks[index + 1].start() if index + 1 < len(marks) else len(script)
            blocks[mark.group(1) or mark.group(2)] = script[mark.start():end]
        return blocks

    def test_s019_no_part_of_the_page_builds_a_control_outside_the_tagged_site(self):
        """The task's Risks section says `S-019` "is one added button away from being false.
        The enumeration test is the guard."

        An outside verification showed the guard was narrower than that: it covered
        `actionControl` and the fleet renderer, so an untagged control added to any of the
        other four renderers survived the whole suite. That is not hypothetical for long,
        because `feat-0056`'s waves report renders per-session rows.

        So the check is over the whole script and names which function offended. A renderer
        that grows a control appears in this set and fails without the test being edited.
        """
        blocks = self.script_blocks()
        self.assertIn("actionControl", blocks, "the script no longer parses as expected")

        building = {name for name, body in blocks.items()
                    if any(f'el("{tag}"' in body for tag in self.INTERACTIVE_TAGS)}

        self.assertEqual(
            building, self.INTERACTIVE_BUILDERS,
            "a function outside the permitted set builds an interactive element. Every "
            "session-directed control must come from actionControl, which tags it, or "
            "S-019's enumeration no longer covers the page")

    def test_s019_the_actions_reach_the_page_from_the_server_registry(self):
        """The page must not carry its own copy of the list, or the two drift and the
        enumeration stops meaning anything."""
        self.build_store([self.record("a1", sid="s1")])
        server = self.serve_on_loopback(roster=[])

        _, meta = self.fetch_json(server, "/api/meta")

        self.assertEqual([a["id"] for a in meta["actions"]],
                         [a["id"] for a in serve.ACTIONS])
        self.assertEqual(meta["action_kinds"], list(serve.ACTION_KINDS))
        self.assertIn("STATE.actions = meta.actions", self.page(),
                      "the page no longer takes its actions from the server's registry")

    def test_s019_a_navigate_action_targets_stored_data_rather_than_a_composed_url(self):
        """The one action that produces a remote target takes it from the store verbatim. A
        template would let the page build a URL of its own, which is a different and much
        larger claim to have to defend."""
        navigate = [a for a in serve.ACTIONS if a["kind"] == "navigate"]
        self.assertTrue(navigate)
        for action in navigate:
            with self.subTest(action=action["id"]):
                self.assertIsNone(action["template"],
                                  "a navigate action composes its target instead of taking "
                                  "it from the store")
        # The attribute, not the word. Asserting on the bare word passed against the comment
        # that explains it, so removing the attribute survived the whole suite: found by
        # mutation, which is the only thing that finds an assertion prose can satisfy.
        self.assertIn('rel: "noreferrer noopener"', self.construction_site(),
                      "the outbound link no longer suppresses the referrer, so following it "
                      "hands the loopback URL to its destination")

    def test_s019_a_mutating_method_is_declined_on_every_route_the_handler_defines(self):
        """Derived from the handler rather than restated: every `do_*` it defines is either
        one of the two readers or the refusal. A `do_POST` that did something would be caught
        without this test being edited."""
        handler = serve.ObservatoryHandler
        methods = {name for name in dir(handler) if name.startswith("do_")}

        self.assertEqual(methods, {"do_GET", "do_HEAD", "do_POST", "do_PUT", "do_PATCH",
                                   "do_DELETE"})
        for name in methods - {"do_GET", "do_HEAD"}:
            with self.subTest(method=name):
                self.assertIs(getattr(handler, name), handler._refuse,
                              f"{name} is no longer the refusal, so this surface may write")

    def test_s019_the_page_states_the_enumeration_rather_than_leaving_it_to_be_inferred(self):
        """S-019 is answered by enumerating what is offered, so the surface says it. A reader
        who has to infer the boundary from which buttons happen to be present has not been
        told it."""
        body = self.renderer_body_fleet()
        self.assertIn("STATE.actions.map(", body,
                      "the page no longer lists its own actions for a reader")
        self.assertIn("Non-Goals", body,
                      "the page states the enumeration without saying what is excluded")

    def renderer_body_fleet(self) -> str:
        html = self.page()
        start = html.index("  fleet: function (data, into) {")
        return html[start:html.index("  skills: function (data, into) {", start)]


class TestNavigateSchemeAllowList(ServerTestCase):
    """bug-0055: a corpus value reached an `href` with no scheme check.

    Every field in a fleet row comes out of a session transcript, which this repository did
    not write. `pr_url` is the one that reached an interpreted context rather than a text
    node, so a `javascript:` URI recorded there became a link labelled "Pull request" whose
    one click ran script in this surface's own origin, able to read every route on the
    server.

    The decision is made in `serve.followable_url` rather than on the page, and these tests
    are why: the suite has no JavaScript runtime by design (see the `node_modules` assertion
    elsewhere in this file), so a check written in the page could only be asserted by reading
    its source. Here it is executed, against values that travelled the whole path the defect
    took: transcript, ingester, store, route.
    """

    PR_SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def pr_records(self, url):
        """A transcript that records a pull request link, as the corpus shapes one."""
        return [
            self.record("u1", sid=self.PR_SESSION),
            {"type": "pr-link", "sessionId": self.PR_SESSION, "prNumber": 80,
             "prUrl": url, "timestamp": "2026-08-01T10:00:01.000Z"},
        ]

    def fleet_row(self, url):
        """The row `/api/fleet` serves for a session whose transcript recorded `url`."""
        self.build_store(self.pr_records(url))
        server = self.serve_on_loopback()
        status, payload = self.fetch_json(server, "/api/fleet")
        self.assertEqual(status, 200)
        rows = [r for r in payload["sessions"] if r["session_id"] == self.PR_SESSION]
        self.assertEqual(len(rows), 1, "the ingested session is not in the fleet report")
        return rows[0]

    def test_a_javascript_url_from_a_transcript_is_not_offered_as_an_href(self):
        """The reported defect, driven from an ingested transcript rather than a built row,
        so the test covers the path the value actually took."""
        hostile = "javascript:fetch('/api/fleet').then(r=>r.text())"
        row = self.fleet_row(hostile)

        self.assertIsNone(row["pr_href"],
                          "a javascript: URI recorded in a transcript is still offered to "
                          "the page as something a browser may be pointed at")
        self.assertEqual(row["pr_url"], hostile,
                         "the report no longer records what the corpus said, so it and the "
                         "transcript disagree")

    def test_the_refusal_is_an_allow_list_and_not_a_javascript_denylist(self):
        """`data:` and `vbscript:` execute too, and a check that names only `javascript:`
        would pass both. Casing and embedded control characters are the other half: browsers
        normalise them away before dispatching the scheme, so a prefix test that does not
        would refuse the safe spelling and admit the dangerous one."""
        for hostile in ("data:text/html;base64,PHNjcmlwdD4=",
                        "vbscript:msgbox(1)",
                        "JaVaScRiPt:alert(1)",
                        "java\nscript:alert(1)",
                        "\tjavascript:alert(1)",
                        "//evil.example.com/pull/1",
                        "/relative/pull/1",
                        "   ",
                        ""):
            with self.subTest(hostile=hostile):
                self.assertIsNone(serve.followable_url(hostile),
                                  f"{hostile!r} is offered as a followable URL")
        for bad_type in (None, 80, ["https://example.com"], {"url": "https://example.com"}):
            with self.subTest(bad_type=bad_type):
                self.assertIsNone(serve.followable_url(bad_type),
                                  "a non-string value is treated as a URL")

    def test_a_real_pull_request_url_still_reaches_the_page_as_a_link(self):
        """The failure direction that matters as much as the fix: a check strict enough to
        refuse a genuine pull request removes a working control, and would be noticed only by
        someone who expected a link to be there."""
        real = "https://github.com/hams-ollo/zen-agent-skills/pull/80"
        row = self.fleet_row(real)

        self.assertEqual(row["pr_href"], real,
                         "a real pull request URL is no longer followable")
        self.assertEqual(row["pr_url"], real)
        for good in ("http://localhost:8787/pull/1",
                     "HTTPS://github.com/o/r/pull/1",
                     "  https://github.com/o/r/pull/1  "):
            with self.subTest(good=good):
                self.assertIsNotNone(serve.followable_url(good),
                                     f"{good!r} is refused, and it should not be")

    def test_a_session_with_no_pull_request_offers_no_link_and_no_text(self):
        """The common row. An action whose field is empty is not offered at all, which is the
        existing behaviour and must survive the change."""
        row = self.fleet_row("")
        self.assertIsNone(row["pr_href"])
        self.assertFalse(row["pr_url"], "an absent pull request became a value")

    def test_the_allow_list_is_a_constant_the_page_and_this_test_both_read(self):
        """`ACTION_KINDS` is a constant rather than a literal because it is the edit that
        could make S-019 false. This is the same shape for the same reason: the allow-list is
        the edit that could make the fix false."""
        self.assertEqual(serve.ACTION_URL_SCHEMES, ("http:", "https:"),
                         "the scheme allow-list changed, which is a decision rather than a "
                         "refactor: state why in the task that changes it")
        navigate = [a for a in serve.ACTIONS if a["kind"] == "navigate"]
        self.assertTrue(navigate, "no navigate action is declared")
        for action in navigate:
            with self.subTest(action=action["id"]):
                self.assertIn("href_field", action,
                              "a navigate action declares no href_field, so the page has "
                              "nothing safe to point at and would fall back to the raw value")

    def test_the_page_takes_the_href_from_the_server_and_never_from_the_raw_field(self):
        """The page-side half. This is a source assertion and is deliberately weaker than the
        four above, because the suite has no JavaScript runtime and a test asserting one
        would be the first. That is why the decision was put in `followable_url` where it is
        executed; what remains here is the wiring, which source can answer."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("function actionControl(")
        body = html[start:html.index("function actionCell(", start)]

        self.assertIn("action.href_field", body,
                      "the page no longer reads the server's followable value")
        self.assertNotIn("href: value", body,
                         "the page sets href from the raw corpus field again, which is "
                         "bug-0055 exactly")
        self.assertIn("href: href", body,
                      "the anchor no longer takes the checked value")
        self.assertIn('rel: "noreferrer noopener"', body,
                      "the anchor lost its referrer and opener protection")

    def test_a_refused_value_is_shown_to_the_viewer_rather_than_hidden(self):
        """Refusing to make it clickable is not the same as pretending it is not there. The
        report's contract is that it shows what the corpus holds, so a refused URL is still
        rendered, as text."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("function actionControl(")
        body = html[start:html.index("function actionCell(", start)]
        navigate_branch = body[body.index('if (action.kind === "navigate")'):]
        fallback = navigate_branch[:navigate_branch.index("return el(\"a\"")]

        self.assertIn('el("code"', fallback,
                      "a refused URL is dropped rather than shown, so the viewer cannot see "
                      "what the corpus recorded")
        self.assertIn("text: value", fallback,
                      "the fallback shows something other than the recorded value")


class TestHostHeader(ServerTestCase):
    """A rebound request must not reach a report.

    Binding a loopback address stops another machine reaching this server and does nothing
    about a browser on this one. The `Host` header is attacker-controlled, so a page on any
    origin can point a name it owns at 127.0.0.1 and read every route here, and what it reads
    is one maintainer's whole session history.

    `feat-0054` recorded this as outside `S-022`'s wording, which is about outbound
    connections, and left it to whichever task defined the surface's boundary. It was then
    missed by that task and found by an outside verification, which demonstrated a foreign
    `Host` returning 155 sessions with their working directories.
    """

    def fetch_with_host(self, server, path, host_header):
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("GET", path, headers={"Host": host_header})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_a_foreign_host_header_is_refused_on_every_route(self):
        """The report routes are derived from `REPORTS` rather than listed here, so a report
        added later is covered without this test being edited. It was a hand-written list, and
        `feat-0058` added `/api/health` to a guard that would have gone on asserting about
        four routes while a fifth served the corpus to any origin that asked."""
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        server = self.serve_on_loopback(roster=[])
        reports = [r["endpoint"] for r in serve.REPORTS if r["endpoint"]]
        self.assertIn("/api/health", reports, "the health report declares no endpoint")

        for route in ["/", "/api/meta", "/api/reports"] + reports:
            with self.subTest(route=route):
                status, body = self.fetch_with_host(server, route, "evil.example.com")
                self.assertEqual(status, 403,
                                 f"{route} answered a request naming another origin's host")
                self.assertNotIn(b"doc-sync", body,
                                 "the refusal leaked report content anyway")

    def test_a_loopback_host_header_is_served(self):
        """The refusal must not break the honest caller, which is a browser on this machine
        sending the address or name it was given."""
        self.build_store([self.record("a1", sid="s1", skill="doc-sync")])
        server = self.serve_on_loopback(roster=[])
        port = server.server_address[1]

        for header in (f"127.0.0.1:{port}", "127.0.0.1", "localhost", f"localhost:{port}",
                       "[::1]", f"[::1]:{port}", "127.0.0.2"):
            with self.subTest(host=header):
                status, _ = self.fetch_with_host(server, "/api/skills", header)
                self.assertEqual(status, 200, f"a loopback host {header!r} was refused")

    def test_the_host_check_decides_the_header_without_a_server(self):
        """The unit form, so every shape is covered cheaply and the parse is pinned."""
        for header in (None, "localhost", "localhost.", "LOCALHOST", "127.0.0.1",
                       "127.0.0.1:8787", "127.1.2.3", "[::1]", "[::1]:8787", "::1"):
            with self.subTest(allowed=header):
                self.assertTrue(serve.host_is_loopback(header), f"{header!r} was refused")
        # The suffix forms are here because a mutation replacing the equality with
        # `endswith("localhost")` survived without them. `attacker.localhost` and
        # `notlocalhost` are what that mutation would let through, and the strict equality
        # is a decision this pins rather than a detail: widening to `*.localhost` later
        # means changing the code and this list together, deliberately.
        for header in ("evil.example.com", "evil.example.com:8787", "example.invalid",
                       "192.168.1.10", "10.0.0.1", "[2001:db8::1]", "", "   ",
                       "localhost.evil.com", "attacker.localhost", "notlocalhost",
                       "0.0.0.0"):
            with self.subTest(refused=header):
                self.assertFalse(serve.host_is_loopback(header), f"{header!r} was allowed")

    def test_the_check_runs_before_the_route_is_resolved(self):
        """A rebound request must not reach a report even on a route that does not exist, or
        the 404 becomes an oracle for which routes are there."""
        server = self.serve_on_loopback(roster=[])
        status, _ = self.fetch_with_host(server, "/api/nothing-here", "evil.example.com")
        self.assertEqual(status, 403,
                         "an unknown route answered 404 rather than refusing the host, "
                         "which tells a rebound page which routes exist")


class TestControlDegradesWithoutTheHarness(ServeTestCase):
    """S-020: control is available only where the harness exposes it, and its absence
    degrades.

    **These are structural assertions over the skill's prose, and that is a real bound rather
    than an oversight.** A skill body is instructions to a model, so a test can assert the
    declining instruction is present and cannot assert a model obeyed it. That is weaker than
    execution, and it is stated here rather than left for a verifier to discover.
    """

    def body(self) -> str:
        return COMPANION_SKILL.read_text(encoding="utf-8")

    def test_s020_the_skill_declines_with_the_reason_stated(self):
        body = self.body()
        self.assertIn("declined", body,
                      "the skill does not say a session-directed request is declined")
        self.assertIn("no session-management capability", body,
                      "the skill declines without stating the reason S-020 requires")

    def test_s020_the_navigation_actions_remain_available_when_control_does_not(self):
        """S-020's second clause: the `S-019` actions survive the absence of control, so the
        skill has to name what is still there rather than only what is gone."""
        body = self.body()
        self.assertIn("still available", body)
        for affordance in ("pull request", "working directory", "resume command"):
            with self.subTest(affordance=affordance):
                self.assertIn(affordance, body,
                              f"the decline does not tell the reader {affordance} is still "
                              f"available")

    def test_s020_no_alternative_route_to_the_same_effect_is_attempted(self):
        """The clause with teeth. The harness's live registry records a messaging path, and
        writing to it is exactly the route S-020 has in mind."""
        body = self.body()
        self.assertIn("Attempt nothing else", body)
        for route in ("shell out", "socket"):
            with self.subTest(route=route):
                self.assertIn(route, body,
                              f"the skill does not rule out reaching a session by {route}")

    def test_s020_the_harness_dependent_half_sits_in_a_labelled_optional_section(self):
        """The portability contract requires it: no other harness exposes these tools, and a
        body that assumes one is not portable."""
        body = self.body()
        self.assertRegex(body, r"(?m)^##\s+Optional:",
                         "the harness-specific capability is not in a section labelled "
                         "optional, so a body assuming one harness reads as universal")
        optional = body[body.index("## Optional:"):]
        self.assertIn("does not", optional,
                      "the optional section does not say what happens without the capability")

    def test_s020_the_skill_ends_no_session_and_says_so(self):
        """Archiving stops the process, which is ending a session, and the contract's
        Non-Goals exclude all four verbs. The skill names them rather than omitting them and
        leaving the reader to assume."""
        body = self.body()
        for verb in ("start", "resume", "interrupt", "end"):
            with self.subTest(verb=verb):
                self.assertIn(verb, body.lower())
        self.assertIn("Non-Goals", body,
                      "the skill excludes the four verbs without saying on whose authority")

    def test_the_companion_skill_is_a_draft_and_no_profile_places_it(self):
        """The consequential risk the task names. A skill that is not excluded is placed into
        user-scope discovery and starts triggering in unrelated sessions before it has been
        used once. Proven against the real installer rather than by reading the frontmatter."""
        self.assertRegex(self.body(), r"(?m)^metadata:\n\s+status:\s*draft\s*$",
                         "the draft marker is absent or not in the block form install.py "
                         "parses, so the skill would ship")

        home = self.tmp / "install-home"
        # Captured rather than left to print: a dry run over 21 skills times 2 tools buries
        # the suite's own output, and the summary it prints is what this asserts on anyway.
        stdout, sys.stdout = sys.stdout, io.StringIO()
        try:
            placed = install.main(["--dry-run", "--profile", "all", "--home", str(home)])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout.close()
            sys.stdout = stdout

        self.assertEqual(placed, 0)
        self.assertIn("agent-observatory",
                      [d.name for d in install.discover_skills()],
                      "the skill is not discoverable at all, so its exclusion proves nothing")
        self.assertIn("excluded from every profile, including 'all': agent-observatory",
                      output, "the installer did not exclude the draft skill")
        self.assertNotIn("copied    claude   agent-observatory", output,
                         "the draft skill was placed into a discovery location")

    def test_the_companion_skill_is_reported_by_the_observatory_as_never_used(self):
        """The kit reports on itself, so adding a skill moves the observatory's own figure.
        Asserted rather than left to surprise a reader of `docs/OBSERVATORY.md`."""
        self.build_store([])
        payload = self.report(roster=serve.skill_roster())
        counts = {row["skill"]: row["uses"] for row in payload["skills"]}

        self.assertEqual(counts.get("agent-observatory"), 0,
                         "the new skill is missing from the roster the report counts against")


class TestLiveWatcher(ServeTestCase):
    """S-013 and S-015 at the level where they are decidable.

    The watcher is driven a tick at a time rather than left to its thread, because a test
    that sleeps and hopes is a test that fails on a slow machine and passes on a fast one
    while proving the same nothing. The thread is exercised once, end to end, in
    `TestLiveOverHttp`.
    """

    def watcher(self, poll_seconds=0.01):
        return serve.LiveWatcher(self.store, self.corpus,
                                 self.tmp / "events.jsonl", poll_seconds)

    def append_record(self, uuid, sid="s-live", name="session.jsonl"):
        path = self.project / name
        with path.open("ab") as handle:
            handle.write((json.dumps(self.record(uuid, sid=sid)) + "\n").encode("utf-8"))

    def spool(self, *events):
        path = self.tmp / "events.jsonl"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(event) + "\n")
        return path

    def test_s013_appended_records_produce_an_event_without_anyone_asking(self):
        """S-013's Then: the open report reflects the new work without being requested
        again. The event is what carries "without being requested", and the store holding
        the record is what makes the re-read show it."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()

        self.assertIsNone(watcher.poll_once(),
                          "the first look folded nothing in, so it had nothing to announce")
        self.append_record("a2")
        event = watcher.poll_once()

        self.assertIsNotNone(event, "an appended record produced no event")
        self.assertEqual(event["type"], "change")
        self.assertEqual(event["source"], "corpus")
        self.assertEqual(event["records"], 1, "the appended record was not folded in")

        conn = db.connect(self.store)
        try:
            seen = conn.execute("SELECT COUNT(*) AS n FROM message").fetchone()["n"]
        finally:
            conn.close()
        self.assertEqual(seen, 2, "the store does not hold the record the event announced")

    def test_an_unchanged_corpus_is_not_ingested_at_all(self):
        """The cheap fingerprint exists so an idle tick costs 38 milliseconds instead of
        167. Removing that guard leaves the *output* correct, because a second guard drops
        an event with no records, so only counting the ingests catches it."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()
        watcher.poll_once()

        calls = []
        real = ingest.ingest
        ingest.ingest = lambda *a, **kw: (calls.append(a), real(*a, **kw))[1]
        try:
            watcher.poll_once()
            watcher.poll_once()
        finally:
            ingest.ingest = real

        self.assertEqual(calls, [],
                         "an unchanged corpus was ingested anyway, so the cheap probe is "
                         "not saving the work it exists to save")

    def test_s013_an_unchanged_corpus_produces_no_event(self):
        """An event per tick would make the page re-fetch forever and would tell a reader
        nothing. Silence is the correct output for nothing happening."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()
        watcher.poll_once()

        self.assertIsNone(watcher.poll_once())
        self.assertIsNone(watcher.poll_once())

    def test_s014_the_watcher_works_with_no_spool_present_and_reports_no_error(self):
        """S-014: with no optional source configured, the report still reflects the work and
        nothing reports an error attributable to the missing source."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = serve.LiveWatcher(self.store, self.corpus,
                                    self.tmp / "nothing-here.jsonl", 0.01)
        watcher.poll_once()
        self.append_record("a2")

        event = watcher.poll_once()

        self.assertIsNotNone(event, "the default path needs the optional source to work")
        self.assertEqual(event["source"], "corpus")
        self.assertEqual(event["hook_events"], 0)
        self.assertFalse((self.tmp / "nothing-here.jsonl").exists(),
                         "looking for an absent spool created one")

    def test_s014_the_stated_delay_is_a_number_and_the_page_and_document_agree(self):
        """S-014 requires the delay to be stated rather than left as "slower". A reader
        cannot judge slower without knowing by how much, so the number lives in one place
        and both the page and the document take it from there."""
        self.assertIsInstance(serve.DEFAULT_POLL_SECONDS, float)
        self.assertGreater(serve.DEFAULT_POLL_SECONDS, 0)

        page = UI_INDEX.read_text(encoding="utf-8")
        self.assertIn("poll_seconds", page,
                      "the page does not state the delay it was told")
        # Defining live() and never calling it leaves every other assertion here true and
        # the page dead, which is what commenting out the call proved.
        boot = page[page.index("function boot("):]
        # Anchored, not a substring: commenting the call out leaves "live();" inside
        # "// live();" and satisfied the first version of this assertion.
        self.assertRegex(boot, r"(?m)^\s*live\(\);",
                         "boot() never opens the live channel, so the page defines it and "
                         "then does not follow anything")

        doc = (REPO_ROOT / "docs" / "OBSERVATORY.md").read_text(encoding="utf-8")
        stated = f"{serve.DEFAULT_POLL_SECONDS:g}"
        # The number in a sentence, not the digit anywhere. Asserting on the bare digit
        # passed against every date in the document, which is an assertion that cannot
        # fail, and this component has now shipped two of those.
        self.assertIn(f"within about {stated} seconds", doc,
                      f"docs/OBSERVATORY.md does not state the {stated} second delay in a "
                      f"sentence, so a reader is told the default path is slower without "
                      f"being told by how much")

    def test_s015_an_event_from_the_spool_is_attributed_to_the_hook(self):
        """S-015: events are attributed to the source they arrived from. There are exactly
        two, and the difference is what a reader needs to know whether the optional source
        is doing anything."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()
        watcher.poll_once()

        self.append_record("a2")
        self.spool({"ts": "2026-08-29T00:00:00Z", "source": "hook", "session_id": "s-live"})
        event = watcher.poll_once()

        self.assertEqual(event["source"], "hook")
        self.assertEqual(event["hook_events"], 1)

    def test_s015_the_optional_source_changes_no_figure(self):
        """S-015's Then, as an equality rather than a description: the reported figures with
        the source active are identical to a corpus-only run over the same work.

        It holds by construction because an event is a hint to look and never a datum, and
        this is the test that would catch anyone making it a datum.
        """
        records = [self.record("a1", sid="s1", skill="doc-sync"),
                   self.record("a2", sid="s1", skill="doc-sync"),
                   self.record("a3", sid="s1", skill="new-task")]

        # Run A: the corpus alone, ingested the ordinary way.
        self.build_store(records)
        corpus_only = self.report(roster=["doc-sync", "new-task"])

        # Run B: the same work, a fresh store, and the hook shouting about all of it.
        second = self.tmp / "with-events.db"
        watcher = serve.LiveWatcher(second, self.corpus, self.tmp / "events.jsonl", 0.01)
        self.spool(*[{"ts": "2026-08-29T00:00:0%dZ" % i, "source": "hook",
                      "session_id": "s1"} for i in range(3)])
        watcher.poll_once()
        watcher.poll_once()

        conn = db.connect(second)
        try:
            with_events = serve.skills_report(conn, None, ["doc-sync", "new-task"])
        finally:
            conn.close()

        self.assertEqual(corpus_only["total_uses"], 3,
                         "the fixture no longer carries the work this compares")
        self.assertEqual(self.uses(with_events), self.uses(corpus_only),
                         "the optional source changed a figure, which S-015 forbids")
        self.assertEqual(with_events["total_uses"], corpus_only["total_uses"])

    def test_s015_the_reconciliation_rule_is_stated_where_a_reader_meets_it(self):
        """The rule is the whole defence against double counting, so it is served rather
        than left in a comment somebody has to find."""
        self.assertIn("hint to look", serve.EVENT_POLICY)
        self.assertIn("never a datum", serve.EVENT_POLICY)

    def test_the_spool_is_consumed_so_one_event_does_not_fire_forever(self):
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()
        watcher.poll_once()
        self.spool({"source": "hook"})

        first = watcher.poll_once()
        second = watcher.poll_once()

        self.assertIsNotNone(first)
        self.assertIsNone(second, "the same spooled event fired twice")

    def test_a_half_written_spool_line_is_left_for_the_next_look(self):
        """The hook writes from inside a live session and may be mid-append, so the spool
        reader stops at the last newline for the same reason the corpus reader does."""
        self.build_store([self.record("a1", sid="s-live")])
        watcher = self.watcher()
        watcher.poll_once()

        path = self.tmp / "events.jsonl"
        path.write_text('{"source": "hook"}\n{"source": "ho', encoding="utf-8",
                        newline="\n")
        first = watcher.poll_once()
        self.assertEqual(first["hook_events"], 1, "the partial line was consumed")

        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write('ok"}\n')
        self.assertEqual(watcher.poll_once()["hook_events"], 1,
                         "the completed line was skipped")

    def test_the_watcher_runs_only_while_something_is_listening(self):
        """A background loop that polls with nobody watching is a cost with no reader, and
        this component's whole posture is that it costs nothing when unused."""
        watcher = self.watcher(poll_seconds=0.01)
        self.assertEqual(watcher.listeners(), 0)
        self.assertIsNone(watcher._thread)

        channel = watcher.subscribe()
        self.assertEqual(watcher.listeners(), 1)
        self.assertTrue(watcher._thread.is_alive())

        watcher.unsubscribe(channel)
        watcher._thread.join(timeout=5)
        self.assertEqual(watcher.listeners(), 0)
        self.assertFalse(watcher._thread.is_alive(),
                         "the watcher kept polling after the last page closed")

    def test_a_fingerprint_is_cheaper_than_an_ingest_and_notices_both_kinds_of_change(self):
        """The probe has to see an append that keeps the size the same and a rewrite that
        keeps the timestamp the same, or the watcher misses work."""
        self.build_store([self.record("a1", sid="s-live")])
        spool = self.tmp / "events.jsonl"
        path = self.project / "session.jsonl"

        # A rewrite that keeps the byte count. Size alone cannot see it.
        before = serve.corpus_fingerprint(self.corpus, spool)
        body = path.read_bytes()
        path.write_bytes(body.replace(b'"a1"', b'"a9"'))
        self.assertEqual(path.stat().st_size, len(body),
                         "the fixture changed the size, so it no longer isolates mtime")
        self.assertNotEqual(serve.corpus_fingerprint(self.corpus, spool), before,
                            "an equal-length rewrite was missed, so the probe keys on size "
                            "alone and a transcript replaced in place is invisible")

        # An append whose timestamp is put back. Mtime alone cannot see it.
        before_append = serve.corpus_fingerprint(self.corpus, spool)
        stat_before = path.stat()
        with path.open("ab") as handle:
            handle.write((json.dumps(self.record("a3", sid="s-live")) + "\n")
                         .encode("utf-8"))
        os.utime(path, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns))

        self.assertEqual(path.stat().st_mtime_ns, stat_before.st_mtime_ns,
                         "the fixture could not hold the timestamp, so it no longer "
                         "isolates size")
        self.assertNotEqual(
            serve.corpus_fingerprint(self.corpus, spool), before_append,
            "an append with an unchanged timestamp was missed, so the probe keys on mtime "
            "alone and a same-second append is invisible")

        # And the spool, which is the third thing the probe has to see.
        after = serve.corpus_fingerprint(self.corpus, spool)
        self.spool({"source": "hook"})
        self.assertNotEqual(serve.corpus_fingerprint(self.corpus, spool), after,
                            "a spooled event did not change the fingerprint")

    def test_the_default_spool_is_never_placed_inside_the_corpus(self):
        """S-009 forbids adding a file to anything the harness owns, and the spool is the
        one file this component creates. The rule was a comment until a mutation moving the
        default into the corpus survived the whole suite."""
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0, roster=[],
                                   quiet=True, registry=self.registry,
                                   corpus=self.corpus)
        try:
            spool = Path(server.spool).resolve()
        finally:
            server.server_close()

        self.assertEqual(spool.parent, self.store.parent.resolve(),
                         "the default spool no longer sits beside the store")
        self.assertNotIn(self.corpus.resolve(), spool.parents,
                         "the default spool sits inside the corpus, which is the one tree "
                         "S-009 says must be byte-for-byte unchanged")

    def test_an_absent_corpus_is_an_empty_fingerprint_rather_than_a_crash(self):
        """Both degenerate inputs, and a bound worth stating.

        `pathlib` yields nothing for a missing directory and for a path that is a file, on
        this platform, rather than raising. So the `except OSError` inside
        `corpus_fingerprint` is a guard for a case nothing here reaches: removing it changes
        no observable behaviour and no test can see the difference. That is recorded rather
        than covered up, because a mutation surviving is only acceptable when the reason is
        known.
        """
        a_file = self.tmp / "not-a-directory.txt"
        a_file.write_text("x", encoding="utf-8", newline="\n")

        self.assertEqual(serve.corpus_fingerprint(self.tmp / "no-corpus"), {})
        self.assertEqual(serve.corpus_fingerprint(a_file), {})
        self.assertFalse((self.tmp / "no-corpus").exists(),
                         "looking at an absent corpus created one")


class TestObservatoryHook(ServeTestCase):
    """The optional event source, which is the one part of this component that runs inside
    somebody else's session.

    Everything here is about it not mattering when it goes wrong. A dashboard that can slow
    or break a coding session is worse than no dashboard, so the criteria are that it always
    exits 0, never writes to stdout, and never touches anything the harness owns.
    """

    HOOK = REPO_ROOT / ".agents" / "hooks" / "observatory-event.py"

    def load(self):
        """Import the hook by path, the way the harness runs it: no package, no repo."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("observatory_event", self.HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_hook(self, payload, env=None):
        module = self.load()
        out = io.StringIO()
        code = module.main(stdin=io.StringIO(json.dumps(payload)), stdout=out)
        return code, out.getvalue()

    def test_the_hook_appends_one_line_and_says_nothing(self):
        code, out = self.run_hook({"session_id": "s1", "cwd": str(self.tmp),
                                   "hook_event_name": "Stop"})

        self.assertEqual(code, 0)
        self.assertEqual(out, "", "the hook wrote to stdout, which the harness parses")
        spool = self.tmp / ".observatory" / "events.jsonl"
        self.assertTrue(spool.exists(), "no event was spooled")
        lines = spool.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(event["source"], "hook")
        self.assertEqual(event["session_id"], "s1")

    def test_the_hook_writes_nothing_to_the_real_stdout_the_harness_reads(self):
        """Run as a subprocess, because that is how the harness runs it and because an
        injected stream cannot see a bare `print`.

        An outside verification showed what that costs: a hook emitting
        `{"decision": "block", "reason": "..."}`, which is precisely how a `Stop` hook tells
        the harness to block a session, survived the whole suite under an assertion whose
        failure message was "the hook wrote to stdout, which the harness parses".
        """
        result = subprocess.run(
            [sys.executable, str(self.HOOK)],
            input=json.dumps({"session_id": "s1", "cwd": str(self.tmp),
                              "hook_event_name": "Stop"}),
            capture_output=True, text=True, timeout=30)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "",
                         "the hook wrote to the stdout the harness parses, which is how a "
                         "Stop hook blocks a session")
        self.assertEqual(result.stderr, "", "the hook wrote to stderr")
        self.assertTrue((self.tmp / ".observatory" / "events.jsonl").exists(),
                        "the subprocess run spooled nothing, so this asserted nothing")

    def test_the_hook_binds_stdout_like_every_other_hook_in_the_module(self):
        """The module's contract gives every hook an injectable `stdout`, and the other four
        bind it. Taking the parameter and dropping it is what made silence untestable."""
        source = self.HOOK.read_text(encoding="utf-8")
        self.assertIn("stdout = sys.stdout if stdout is None else stdout", source,
                      "main() takes a stdout parameter and never binds it, so every "
                      "assertion about what it writes there is unfalsifiable")

    def test_the_hook_exits_zero_on_anything_it_is_given(self):
        """Every failure path returns 0. This hook has nothing to say that is worth one
        interrupted run."""
        module = self.load()
        for stdin_text in ("", "not json at all", "[]", "null", '{"cwd": 12345}'):
            with self.subTest(stdin=stdin_text[:20]):
                out = io.StringIO()
                self.assertEqual(
                    module.main(stdin=io.StringIO(stdin_text), stdout=out), 0)
                self.assertEqual(out.getvalue(), "")

    def test_the_spool_append_reports_failure_rather_than_raising(self):
        """`append` documents that it never raises. `main` has its own guard, so narrowing
        this one is invisible from the outside: the contract has to be asserted here."""
        module = self.load()
        blocked = self.tmp / "blocked-file"
        blocked.write_text("not a directory", encoding="utf-8", newline="\n")

        self.assertIs(module.append(blocked / "x" / "events.jsonl", {"a": 1}), False,
                      "append raised or claimed success on an unwritable path")

    def test_the_hook_exits_zero_when_the_spool_cannot_be_written(self):
        """The case that matters: something is wrong with the disk or the path, and the
        session must not notice."""
        module = self.load()
        blocked = self.tmp / "blocked"
        blocked.write_text("i am a file, not a directory", encoding="utf-8", newline="\n")
        out = io.StringIO()

        code = module.main(
            stdin=io.StringIO(json.dumps({"session_id": "s1", "cwd": str(blocked)})),
            stdout=out)

        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "")

    def test_the_hook_never_writes_where_the_harness_lives(self):
        """S-009 covers everything the harness owns, and this is the only piece of the
        observatory with the access to break it."""
        source = self.HOOK.read_text(encoding="utf-8")
        for forbidden in (".claude", "projects", "sessions"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f'"{forbidden}"', source,
                                 f"the hook names {forbidden!r} as a path component")
        self.assertIn(".observatory", source)

    def test_the_hook_opens_no_socket_and_imports_nothing_from_this_repository(self):
        """A file append cannot block on a connect or wait out a read timeout. That is the
        whole reason the event source is a spool file rather than a request."""
        source = self.HOOK.read_text(encoding="utf-8")
        # Import statements, not bare words. The first version of this matched "socket" and
        # "subprocess" in the docstring that explains why neither is used, which is the same
        # defect as an assertion prose can satisfy, arriving from the other direction.
        imports = re.findall(r"(?m)^\s*(?:import|from)\s+([\w.]+)", source)
        for forbidden in ("socket", "urllib", "http", "requests", "subprocess",
                          "scripts", "asyncio", "ssl"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, [name.split(".")[0] for name in imports],
                                 f"the hook imports {forbidden}, which can block inside "
                                 f"somebody else's session")
        self.assertEqual(sorted(imports),
                         ["__future__", "datetime", "json", "os", "pathlib", "sys"],
                         "the hook's import list changed; every entry must be standard "
                         "library and none may block")

    def test_the_spool_is_capped_so_nothing_grows_without_bound_in_a_session(self):
        """Nobody may ever drain it. Losing an old hint costs nothing, because a hint is
        not a datum."""
        module = self.load()
        spool = self.tmp / ".observatory" / "events.jsonl"
        spool.parent.mkdir(parents=True)
        spool.write_text("x" * (module.MAX_SPOOL_BYTES + 10), encoding="utf-8",
                         newline="\n")

        module.main(stdin=io.StringIO(json.dumps({"cwd": str(self.tmp)})),
                    stdout=io.StringIO())

        self.assertLess(spool.stat().st_size, module.MAX_SPOOL_BYTES,
                        "the spool grew past its cap inside a live session")

    def test_the_spool_location_follows_the_session_and_can_be_overridden(self):
        module = self.load()
        payload = {"cwd": str(self.tmp / "projectA")}
        self.assertEqual(module.spool_path(payload, env={}),
                         self.tmp / "projectA" / ".observatory" / "events.jsonl")
        self.assertEqual(module.spool_path(payload, env={"OBSERVATORY_SPOOL": "X.jsonl"}),
                         Path("X.jsonl"))

    def test_the_hook_spools_no_conversation_content(self):
        """The contract excludes reconstructing conversation content, and a hook that
        spooled a prompt would put it in a file the contract never described."""
        code, _ = self.run_hook({"session_id": "s1", "cwd": str(self.tmp),
                                 "prompt": "SECRET PROMPT TEXT",
                                 "tool_input": {"command": "SECRET COMMAND"}})
        self.assertEqual(code, 0)
        spooled = (self.tmp / ".observatory" / "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("SECRET", spooled,
                         "the hook spooled conversation content")


class TestLiveOverHttp(ServerTestCase):
    """S-013 through the channel a page actually opens, once, end to end."""

    def read_events(self, server, seconds=10.0):
        """Open the stream and collect parsed events until the deadline."""
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=seconds)
        conn.request("GET", "/api/events")
        response = conn.getresponse()
        collected, deadline = [], time.monotonic() + seconds
        try:
            while time.monotonic() < deadline:
                line = response.fp.readline()
                if not line:
                    break
                if line.startswith(b"data: "):
                    collected.append(json.loads(line[6:].decode("utf-8")))
                    if len(collected) >= 2:
                        break
        finally:
            conn.close()
        return collected

    def test_s013_an_open_stream_is_told_about_work_it_did_not_ask_for(self):
        self.build_store([self.record("a1", sid="s-live")])
        server = self.serve_on_loopback(roster=[])
        server.watcher.poll_seconds = 0.05

        appended = threading.Event()

        def append_after_a_moment():
            time.sleep(0.6)                  # let the baseline tick happen first
            path = self.project / "session.jsonl"
            with path.open("ab") as handle:
                handle.write((json.dumps(self.record("a2", sid="s-live")) + "\n")
                             .encode("utf-8"))
            appended.set()

        threading.Thread(target=append_after_a_moment, daemon=True).start()
        events = self.read_events(server)

        self.assertTrue(appended.wait(10), "the fixture never appended")
        self.assertTrue(events, "the stream delivered nothing at all")
        self.assertEqual(events[0]["type"], "open",
                         "the stream did not announce itself, so a page cannot tell it is "
                         "following rather than silently dead")
        self.assertEqual(events[0]["poll_seconds"], 0.05)
        self.assertTrue(any(e.get("type") == "change" for e in events),
                        "appending a record produced no change event on an open stream")

    def test_the_stream_declares_itself_as_an_event_stream(self):
        server = self.serve_on_loopback(roster=[])
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("HEAD", "/api/events")
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("text/event-stream", response.getheader("Content-Type"))
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
        finally:
            conn.close()

    def test_a_head_on_the_stream_returns_rather_than_holding_a_thread(self):
        """`do_HEAD` is `do_GET`, so without a guard a HEAD here would block until the
        process ended. The test is that the request completes at all."""
        server = self.serve_on_loopback(roster=[])
        host, port = server.server_address[0], server.server_address[1]
        finished = threading.Event()

        def ask():
            conn = http.client.HTTPConnection(host, port, timeout=5)
            try:
                conn.request("HEAD", "/api/events")
                conn.getresponse().read()
                finished.set()
            finally:
                conn.close()

        threading.Thread(target=ask, daemon=True).start()
        self.assertTrue(finished.wait(8), "a HEAD on the event stream never returned")

        # The client returns for a HEAD whether or not the server thread does, because
        # http.client knows a HEAD has no body. The property that matters is server-side:
        # the handler must not subscribe and sit in the loop.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and server.watcher.listeners():
            time.sleep(0.05)
        self.assertEqual(server.watcher.listeners(), 0,
                         "a HEAD subscribed to the stream and held a thread in the loop")

    def test_the_stream_is_refused_to_a_rebound_host_like_every_other_route(self):
        """A long-lived channel handing the corpus to a rebound page would be worse than a
        single response doing it, not better."""
        server = self.serve_on_loopback(roster=[])
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("GET", "/api/events", headers={"Host": "evil.example.com"})
            self.assertEqual(conn.getresponse().status, 403)
        finally:
            conn.close()


class HealthTestCase(ServerTestCase):
    """Fixtures for the health report (`feat-0058`, `S-016`).

    Every record shape below was read off this maintainer's real corpus on 2026-08-29 rather
    than invented, because a fixture that agrees only with the ingester proves the two agree
    and nothing about whether either matches what the harness writes. What was confirmed: a
    hook outcome is an `attachment` whose `attachment.type` starts `hook_`, carrying
    `hookName`, `hookEvent`, `stderr`, `exitCode`, `command`, and `durationMs`; an API error is
    a `system` record with `subtype: api_error` carrying `error` and `retryAttempt`; and a run
    that ended abnormally is an `assistant` record carrying `isApiErrorMessage` with
    `apiErrorStatus`, or `isAbortedMidStream`.
    """

    def hook_record(self, uuid, sid="s1", ts="2026-08-01T10:00:00.000Z",
                    kind="hook_non_blocking_error", exit_code=49,
                    stderr="Failed with non-blocking status code: Python was not found",
                    hook_name="SessionStart:startup", hook_event="SessionStart",
                    command="python3 .agents/hooks/skill-reachability-reminder.py",
                    duration_ms=206, tool_use_id=None):
        """One hook outcome. `exit_code=None` omits the field, which is what the harness does
        for a hook that contributed context rather than exiting on a status."""
        attachment = {"type": kind, "hookName": hook_name, "hookEvent": hook_event,
                      "toolUseID": tool_use_id or (uuid + "-tool"), "stderr": stderr,
                      "stdout": ""}
        if exit_code is not None:
            attachment["exitCode"] = exit_code
            attachment["command"] = command
            attachment["durationMs"] = duration_ms
        return {"type": "attachment", "uuid": uuid, "parentUuid": None, "sessionId": sid,
                "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main",
                "entrypoint": "claude-desktop", "attachment": attachment}

    def api_error_record(self, uuid, sid="s1", ts="2026-08-01T10:00:00.000Z", attempt=1,
                         message="Connection error."):
        return {"type": "system", "subtype": "api_error", "level": "error", "uuid": uuid,
                "parentUuid": None, "sessionId": sid, "timestamp": ts, "cwd": "D:\\demo",
                "gitBranch": "main", "entrypoint": "claude-desktop",
                "error": {"message": message, "status": 500, "formatted": message},
                "retryInMs": 607, "retryAttempt": attempt, "maxRetries": 10,
                "source": "request_retry"}

    def abnormal_record(self, uuid, sid="s1", ts="2026-08-01T10:00:00.000Z",
                        api_error=True, status=429, aborted=False, error="rate_limit"):
        record = self.record(uuid, sid=sid, ts=ts)
        if api_error:
            record["isApiErrorMessage"] = True
            record["apiErrorStatus"] = status
            record["error"] = error
        if aborted:
            record["isAbortedMidStream"] = True
        return record

    def compact_record(self, uuid, sid="s1", ts="2026-08-01T10:00:00.000Z"):
        return {"type": "system", "subtype": "compact_boundary", "uuid": uuid,
                "parentUuid": None, "sessionId": sid, "timestamp": ts, "cwd": "D:\\demo",
                "gitBranch": "main", "entrypoint": "claude-desktop",
                "content": "Conversation compacted",
                "compactMetadata": {"trigger": "auto", "preTokens": 999216}}

    def health(self, project=None):
        conn = db.connect(self.store)
        try:
            return serve.health_report(conn, project)
        finally:
            conn.close()


class TestHealthHookFailures(HealthTestCase):
    """S-016, first part: a hook failure with its session, its time, and its exit status."""

    def test_s016_a_hook_failure_is_reported_with_its_session_time_exit_status_and_output(
            self):
        """S-016's Then, over a hook, field by field. The exit status is named in the
        scenario's own wording, which is why it is asserted as a value rather than as
        presence."""
        self.build_store([self.hook_record("h1", sid="s1",
                                           ts="2026-08-01T10:00:00.000Z")])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 1)
        failure = payload["hook_failures"][0]
        self.assertEqual(failure["session_id"], "s1")
        self.assertEqual(failure["ts"], "2026-08-01T10:00:00.000Z")
        self.assertEqual(failure["exit_code"], 49)
        self.assertEqual(failure["hook_name"], "SessionStart:startup")
        self.assertEqual(failure["hook_event"], "SessionStart")
        self.assertEqual(failure["command"],
                         "python3 .agents/hooks/skill-reachability-reminder.py")
        self.assertIn("Python was not found", failure["detail"])

    def test_s016_a_hook_that_exited_zero_is_a_run_and_not_a_failure(self):
        """The two must not collapse into each other. A report that counted every hook record
        as a failure would read as 296 failures on this maintainer's corpus rather than 14,
        and one that counted none would read as zero: both are one predicate away."""
        self.build_store([
            self.hook_record("h1", kind="hook_success", exit_code=0, stderr=""),
            self.hook_record("h2", kind="hook_non_blocking_error", exit_code=49),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_events"], 2)
        self.assertEqual(payload["totals"]["hook_failures"], 1)
        self.assertEqual([row["kind"] for row in payload["hook_failures"]],
                         ["hook_non_blocking_error"])

    def test_s016_the_hook_denominator_counts_hooks_and_not_every_health_record(self):
        """`hook_events` is the denominator the page prints beside a zero-failure result:
        "None recorded, out of N hook records in scope." It is the number a reader uses to
        decide whether that zero means anything, so it has to be hooks.

        Every other fixture in this class is made of hook records alone, where counting hooks
        and counting everything give the same answer. This one deliberately mixes kinds, which
        is the only shape that can tell the two apart: on this maintainer's corpus the wrong
        rule reads 347 rather than 298, and every assertion elsewhere still passes.
        """
        self.build_store([
            self.hook_record("h1", kind="hook_success", exit_code=0, stderr=""),
            self.hook_record("h2", kind="hook_non_blocking_error", exit_code=49),
            self.api_error_record("e1"),
            self.abnormal_record("r1"),
            self.compact_record("c1"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_events"], 2,
                         "the hook denominator counted records that are not hooks, so a "
                         "zero-failure result is judged against the wrong population")
        self.assertEqual(payload["totals"]["events"], 4,
                         "the unrestricted event count went missing while hooks were "
                         "filtered, so the two figures no longer describe the same corpus")
        self.assertEqual(payload["totals"]["hook_failures"], 1)

    def test_s016_the_affected_session_count_is_the_union_of_every_kind_of_trouble(self):
        """A headline figure with no test is a headline figure that can be anything.

        `sessions_affected` is rendered beside the counts as "sessions with a health record",
        and it is a union over two populations that overlap: the sessions events touched and
        the sessions abnormal runs touched. Two things it must not be, and both leave every
        other assertion in this file green: the event half alone, which drops a session whose
        only trouble was an abnormal run, and a count of events, which is not a count of
        sessions at all.

        Built so that no two of the three candidate answers agree, which is the only shape
        that can tell them apart: five health events fall in three sessions, and a fourth
        session is reached only through an abnormal run. So the union is 4, the event half
        alone is 3, and the event count is 5, and a fixture where any two of those coincided
        would pass under the wrong rule.
        """
        self.build_store([
            self.hook_record("h1", sid="s1", ts="2026-08-01T10:00:01.000Z",
                             kind="hook_non_blocking_error", exit_code=49),
            self.hook_record("h2", sid="s2", ts="2026-08-01T10:00:02.000Z",
                             kind="hook_non_blocking_error", exit_code=49),
            self.api_error_record("e1", sid="s2", ts="2026-08-01T10:00:03.000Z"),
            self.api_error_record("e2", sid="s3", ts="2026-08-01T10:00:04.000Z"),
            self.api_error_record("e3", sid="s3", ts="2026-08-01T10:00:05.000Z"),
            self.abnormal_record("r1", sid="s4", ts="2026-08-01T10:00:06.000Z"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["sessions_affected"], 4,
                         "the affected-session count is not the union of the four sessions "
                         "in trouble, so the page's headline names the wrong number")
        self.assertEqual(payload["totals"]["events"], 5,
                         "five health events over three sessions, plus an abnormal run in a "
                         "fourth: if this figure equals the count above, the headline is "
                         "counting events and not sessions")
        self.assertEqual(payload["totals"]["abnormal_runs"], 1,
                         "s4 reaches the union only through its abnormal run, so this is the "
                         "half a rule that forgot abnormal runs would drop")

    def test_s016_a_hook_with_no_exit_status_is_not_reported_as_having_succeeded(self):
        """All 205 `hook_additional_context` records on this maintainer's corpus carry no
        exit status at all, so a rule reading a missing status as zero would silently assert
        success for two thirds of every hook record in the store."""
        self.build_store([self.hook_record("h1", kind="hook_additional_context",
                                           exit_code=None, stderr="")])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_events"], 1)
        self.assertEqual(payload["totals"]["hook_failures"], 0)
        ledger = {row["kind"]: row for row in payload["kinds"]}
        self.assertEqual(ledger["hook_additional_context"]["events"], 1)
        conn = db.connect(self.store)
        try:
            self.assertIsNone(serve.health_events(conn)[0]["exit_code"],
                              "a missing exit status was invented rather than left "
                              "unrecorded")
        finally:
            conn.close()

    def test_s016_a_kind_naming_an_error_is_a_failure_even_with_no_exit_status(self):
        """The half of the rule an exit-code test cannot reach. A hook whose record names an
        error and carries no status is a failure the corpus told us about directly."""
        self.build_store([self.hook_record("h1", kind="hook_blocking_error",
                                           exit_code=None, stderr="blew up")])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 1)
        self.assertEqual(payload["hook_failures"][0]["kind"], "hook_blocking_error")

    def test_s016_a_hook_that_exited_non_zero_is_a_failure_whatever_its_kind_is_called(self):
        """The other half, and the one every other test here reached only by accident.

        Found by mutation: deleting the exit-status branch outright left every assertion in
        this file green, because every failing fixture used a kind whose name contains
        "error" and the kind rule alone still classified it. On this corpus the two halves
        agree, which is exactly why nothing noticed. The scenario names the exit status, so
        the case where only the status says so has to be constructed deliberately.
        """
        self.build_store([self.hook_record("h1", kind="hook_success", exit_code=3,
                                           stderr="the hook fell over")])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 1,
                         "a hook that exited non-zero was read as a success because its "
                         "record is not called an error")
        failure = payload["hook_failures"][0]
        self.assertEqual(failure["kind"], "hook_success")
        self.assertEqual(failure["exit_code"], 3)


class TestHealthApiRetries(HealthTestCase):
    """S-016, second part: an API error with its retry count."""

    def test_s016_a_retried_api_error_is_reported_with_its_attempt_count(self):
        """The scenario names the retry count, so the figure is asserted as a number. A report
        that listed four attempts as four unrelated errors would state the same facts and
        answer a different question."""
        self.build_store([
            self.api_error_record(f"e{n}", sid="s1", attempt=n,
                                  ts=f"2026-08-01T10:00:0{n}.000Z")
            for n in (1, 2, 3, 4)
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["api_errors"], 4)
        self.assertEqual(payload["totals"]["retry_episodes"], 1)
        self.assertEqual(payload["totals"]["worst_attempts"], 4)
        episode = payload["retry_episodes"][0]
        self.assertEqual(episode["session_id"], "s1")
        self.assertEqual(episode["attempts"], 4)
        self.assertEqual(episode["events"], 4)
        self.assertEqual(episode["first_ts"], "2026-08-01T10:00:01.000Z")
        self.assertEqual(episode["last_ts"], "2026-08-01T10:00:04.000Z")
        self.assertIn("Connection error", episode["detail"])

    def test_s016_a_retry_count_that_stops_rising_starts_a_new_episode(self):
        """Two requests that each took two attempts are two episodes of two, not one of four
        and not four of one. Nothing but the counter resetting separates them."""
        self.build_store([
            self.api_error_record("e1", attempt=1, ts="2026-08-01T10:00:01.000Z"),
            self.api_error_record("e2", attempt=2, ts="2026-08-01T10:00:02.000Z"),
            self.api_error_record("e3", attempt=1, ts="2026-08-01T11:00:01.000Z"),
            self.api_error_record("e4", attempt=2, ts="2026-08-01T11:00:02.000Z"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["api_errors"], 4)
        self.assertEqual(payload["totals"]["retry_episodes"], 2)
        self.assertEqual([episode["attempts"] for episode in payload["retry_episodes"]],
                         [2, 2])
        self.assertEqual(payload["totals"]["worst_attempts"], 2)

    def test_s016_an_error_that_was_retried_and_then_succeeded_is_still_reported(self):
        """The acceptance criterion's "whether or not it eventually succeeded". The session
        goes on to do ordinary work after the retries, and the episode is reported with its
        attempt count all the same, because the interesting signal is the cost of the request
        rather than its verdict."""
        self.build_store([
            self.api_error_record("e1", sid="s1", attempt=1,
                                  ts="2026-08-01T10:00:01.000Z"),
            self.api_error_record("e2", sid="s1", attempt=2,
                                  ts="2026-08-01T10:00:02.000Z"),
            self.record("a1", sid="s1", ts="2026-08-01T10:00:03.000Z"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["retry_episodes"], 1)
        self.assertEqual(payload["retry_episodes"][0]["attempts"], 2)
        self.assertEqual(payload["totals"]["abnormal_runs"], 0,
                         "an ordinary message that followed retries was read as a failure")
        self.assertFalse(payload["empty"])


class TestHealthAbnormalRuns(HealthTestCase):
    """S-016, third part: a run that ended abnormally."""

    def test_s016_a_run_that_ended_abnormally_is_reported_as_such(self):
        """Both markers the corpus carries, asserted separately, because they sit on different
        fields and a report reading only one would be silently half-blind. 26 records carry
        the first on this maintainer's corpus and 2 carry the second."""
        self.build_store([
            self.abnormal_record("m1", sid="s1", ts="2026-08-01T10:00:01.000Z",
                                 api_error=True, status=429, error="rate_limit"),
            self.abnormal_record("m2", sid="s1", ts="2026-08-01T10:00:02.000Z",
                                 api_error=False, aborted=True),
            self.record("a1", sid="s1", ts="2026-08-01T10:00:03.000Z"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["abnormal_runs"], 2)
        runs = {run["uuid"]: run for run in payload["abnormal_runs"]}
        self.assertEqual(runs["m1"]["markers"], ["API error"])
        self.assertEqual(runs["m1"]["status"], "429")
        self.assertEqual(runs["m1"]["session_id"], "s1")
        self.assertEqual(runs["m1"]["ts"], "2026-08-01T10:00:01.000Z")
        self.assertEqual(runs["m1"]["detail"], "rate_limit")
        self.assertEqual(runs["m2"]["markers"], ["aborted mid stream"])
        self.assertNotIn("a1", runs, "an ordinary message was reported as an abnormal end")

    def test_s016_a_run_carrying_both_markers_is_reported_with_both(self):
        """A record may carry both, which is why the report names them as a list rather than
        picking one and calling it the kind."""
        self.build_store([self.abnormal_record("m1", api_error=True, aborted=True)])

        payload = self.health()

        self.assertEqual(payload["totals"]["abnormal_runs"], 1)
        self.assertEqual(payload["abnormal_runs"][0]["markers"],
                         ["API error", "aborted mid stream"])


class TestHealthCounting(HealthTestCase):
    """The counting rule, which is the difference between 14 hook failures and 19."""

    def replayed_hook_failure(self):
        """One hook failure, written into two transcripts under two session ids.

        This is what a forked or resumed session does: it replays earlier records verbatim
        into a new transcript. On this maintainer's corpus 428 `health_event` rows carry 345
        distinct events for exactly this reason, and the 19 rows that look like hook failures
        are 14 real ones.
        """
        failure = self.hook_record("h1", sid="s1", ts="2026-08-01T10:00:00.000Z")
        self.write_transcript([failure], name="original.jsonl")
        forked = json.loads(json.dumps(failure))
        forked["sessionId"] = "s2"
        self.write_transcript([forked], name="forked.jsonl")
        return ingest.ingest(self.corpus, self.store)

    def test_s016_a_failure_replayed_into_a_forked_session_is_counted_once(self):
        """The trap this component has hit before, arriving at a table with no
        canonical-versus-occurrence split to lean on. Counting rows overstates by however much
        history has been replayed."""
        self.replayed_hook_failure()

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 1,
                         "a replayed failure was counted twice")
        self.assertEqual(payload["totals"]["events"], 1)
        self.assertEqual(payload["totals"]["records"], 2,
                         "the report no longer says how many records the event was written "
                         "as, so the gap it deduplicated is invisible")
        failure = payload["hook_failures"][0]
        self.assertEqual(failure["sessions"], ["s1", "s2"],
                         "the report names one session and hides the other")
        self.assertEqual(failure["replays"], 1)

    def test_s016_the_record_count_equals_the_rows_the_store_holds(self):
        """The identity that makes the deduplication checkable rather than asserted: the
        events reported, expanded by their replays, are exactly the rows in the store."""
        self.replayed_hook_failure()
        conn = db.connect(self.store)
        try:
            rows = conn.execute("SELECT COUNT(*) AS n FROM health_event").fetchone()["n"]
        finally:
            conn.close()

        self.assertEqual(self.health()["totals"]["records"], rows)

    def test_s016_an_abnormal_run_replayed_into_a_forked_session_names_both_sessions(self):
        """The same replay, over the other source. `message` is canonical per uuid, so the
        count was right without anything being done about it, and the session list was not:
        found by mutation, which showed that dropping the occurrence lookup entirely and
        naming only the canonical row's own session left every assertion here green. One of
        the 28 abnormal runs on this maintainer's corpus is in that position.
        """
        abnormal = self.abnormal_record("m1", sid="s1", ts="2026-08-01T10:00:00.000Z")
        self.write_transcript([abnormal], name="original.jsonl")
        forked = json.loads(json.dumps(abnormal))
        forked["sessionId"] = "s2"
        self.write_transcript([forked], name="forked.jsonl")
        ingest.ingest(self.corpus, self.store)

        payload = self.health()

        self.assertEqual(payload["totals"]["abnormal_runs"], 1,
                         "a replayed abnormal run was counted twice")
        run = payload["abnormal_runs"][0]
        self.assertEqual(run["sessions"], ["s1", "s2"],
                         "the report names one session and hides the other, so a run "
                         "replayed into a fork looks like it happened in one place")
        self.assertEqual(run["replays"], 1)

    def test_s016_two_genuinely_distinct_failures_are_not_collapsed_into_one(self):
        """The other direction, and the one an over-eager identity would break. Two failures
        differing only in when they happened are two failures."""
        self.build_store([
            self.hook_record("h1", sid="s1", ts="2026-08-01T10:00:01.000Z"),
            self.hook_record("h2", sid="s1", ts="2026-08-01T10:00:02.000Z"),
        ])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 2)
        self.assertEqual(payload["totals"]["events"], 2)


class TestHealthEmptyAndBounds(HealthTestCase):
    """What the report says when it has nothing to say, and what it says it cannot see."""

    def test_s016_a_corpus_with_no_health_events_is_reported_as_explicitly_empty(self):
        """A panel of four zeroes and no tables is indistinguishable from one that failed to
        load, and telling a reader that nothing failed is the whole of what this report does
        on a healthy corpus."""
        self.build_store([self.record("a1", sid="s1")])

        payload = self.health()

        self.assertTrue(payload["empty"])
        self.assertEqual(payload["totals"]["events"], 0)
        self.assertEqual(payload["hook_failures"], [])
        self.assertEqual(payload["retry_episodes"], [])
        self.assertEqual(payload["abnormal_runs"], [])
        self.assertTrue(payload["blind_spot"],
                        "an empty report drops the sentence saying what it cannot see, which "
                        "is the one report where that sentence matters most")

    def test_s016_health_records_that_are_not_failures_still_read_as_an_empty_report(self):
        """`empty` is not "no records". A corpus can carry hook outcomes that all succeeded,
        and that is a clean health report rather than a populated one."""
        self.build_store([
            self.hook_record("h1", kind="hook_success", exit_code=0, stderr=""),
            self.compact_record("c1"),
        ])

        payload = self.health()

        self.assertTrue(payload["empty"], "records that are not failures were read as some")
        self.assertEqual(payload["totals"]["events"], 2)
        self.assertEqual(payload["totals"]["hook_failures"], 0)

    def test_s016_the_report_states_that_a_failure_leaving_no_record_is_invisible_to_it(self):
        """Asserted as a served field the page consumes, not as a word appearing somewhere in
        the source. This repository has twice had an assertion on a bare word satisfied by a
        docstring and broken by a comment, so the claim here is that the sentence reaches a
        reader, which is a statement about the wiring rather than about the prose."""
        self.build_store([self.record("a1", sid="s1")])
        server = self.serve_on_loopback(roster=[])

        _, payload = self.fetch_json(server, "/api/health")

        self.assertEqual(payload["blind_spot"], serve.HEALTH_BLIND_SPOT)
        self.assertIn("data.blind_spot", renderer_source("health"),
                      "the page no longer renders the qualification the server serves, so a "
                      "reader meets the figures without it")

        # The equality above moves with the constant, so on its own it proves the sentence
        # arrives and never what it says: rewriting `HEALTH_BLIND_SPOT` to "Everything is
        # fine." satisfies it completely, and the page then prints that in the exact slot the
        # caveat is reserved for. These two assert the claim rather than the delivery. They
        # are on the constant itself, not on a scan of the file, so the failure that has bitten
        # this component twice, a bare phrase matched inside a comment or a docstring, cannot
        # reach them.
        stated = payload["blind_spot"].lower()
        self.assertIn("record", stated,
                      "the blind-spot sentence does not mention records, so it cannot be "
                      "saying that a failure leaving none is invisible here")
        self.assertIn("not evidence", stated,
                      "the blind-spot sentence never tells the reader what they may not "
                      "conclude, which is the whole of what the criterion asks it to say")

    def test_s016_a_kind_the_report_does_not_count_is_listed_rather_than_dropped(self):
        """A record silently dropped from a report about failures is the failure this report
        exists to stop. Compaction is not a failure and belongs to `S-017`, and a reader must
        be able to see that it was read and not counted."""
        self.build_store([self.compact_record("c1"), self.hook_record("h1")])

        payload = self.health()

        ledger = {row["kind"]: row for row in payload["kinds"]}
        self.assertIn("compact_boundary", ledger)
        self.assertEqual(ledger["compact_boundary"]["events"], 1)
        self.assertFalse(ledger["compact_boundary"]["counted"])
        self.assertIn("S-017", ledger["compact_boundary"]["role"])
        self.assertEqual(payload["totals"]["hook_failures"], 1)
        self.assertEqual(payload["totals"]["api_errors"], 0)
        self.assertEqual(payload["totals"]["abnormal_runs"], 0)

    def test_s016_a_kind_the_ingester_can_write_and_this_corpus_lacks_is_listed_at_zero(self):
        """`feat-0053`'s verification recorded that every `stop_hook_summary` record on this
        maintainer's corpus carries empty `hookErrors` and false `preventedContinuation`, so
        the ingester's branch for it writes no row and `prevented_continuation` is NULL
        everywhere. **That is a bound, not a repair**, and a ledger built only from what the
        store happens to hold would show it as nothing rather than as zero."""
        self.build_store([self.hook_record("h1")])

        ledger = {row["kind"]: row for row in self.health()["kinds"]}

        self.assertIn("stop_hook_summary", ledger,
                      "a kind the ingester can write vanished from the ledger because this "
                      "corpus has none of it, which is what makes a bound look like an "
                      "absence")
        self.assertEqual(ledger["stop_hook_summary"]["events"], 0)
        self.assertIn("bound", ledger["stop_hook_summary"]["role"])

    def test_s016_a_stop_hook_summary_that_did_report_something_is_counted_as_a_failure(self):
        """The branch that is filtered to zero on this corpus, exercised against a record the
        ingester would actually write one for.

        **This does not lift the bound and must not be read as doing so.** The corpus is where
        the branch contributes nothing, and a fixture cannot change that; what this pins is
        that the report classifies such a row correctly if one ever arrives, so the zero is a
        statement about the corpus rather than about untested code.
        """
        self.build_store([{
            "type": "system", "subtype": "stop_hook_summary", "uuid": "sh1",
            "parentUuid": None, "sessionId": "s1", "timestamp": "2026-08-01T10:00:00.000Z",
            "cwd": "D:\\demo", "gitBranch": "main", "entrypoint": "claude-desktop",
            "hookErrors": ["Stop hook blew up"], "preventedContinuation": False,
            "toolUseID": "t1",
        }])

        payload = self.health()

        self.assertEqual(payload["totals"]["hook_failures"], 1)
        failure = payload["hook_failures"][0]
        self.assertEqual(failure["kind"], "stop_hook_summary")
        self.assertEqual(failure["session_id"], "s1")
        self.assertIn("Stop hook blew up", failure["detail"])


class TestHealthOverHttpAndScope(HealthTestCase):
    """The report through the real surface, and under the shell's scope selector."""

    def test_s016_the_report_is_served_over_http_and_matches_the_store(self):
        """The registry, the route, and the report have to agree. A report function nothing
        routes to is not a report anyone can read."""
        self.build_store([self.hook_record("h1"), self.api_error_record("e1"),
                          self.abnormal_record("m1")])
        server = self.serve_on_loopback(roster=[])

        status, payload = self.fetch_json(server, "/api/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["report"], "health")
        self.assertTrue(payload["store_present"])
        self.assertEqual(payload["totals"], self.health()["totals"])
        health = [r for r in serve.REPORTS if r["id"] == "health"][0]
        self.assertEqual(health["endpoint"], "/api/health")
        self.assertIsNone(health["owner"], "a built report still names a task that owes it")

    def test_s016_the_scope_selector_restricts_the_health_report_to_one_project(self):
        """The shell sends the selected project with every report request, so a report that
        ignored it would leave the selector visibly present and silently inert."""
        other = self.corpus / "D--other"
        self.write_transcript([self.hook_record("h1", sid="s1")], name="a.jsonl")
        self.write_transcript([self.hook_record("h2", sid="s2")], name="b.jsonl",
                              project=other)
        ingest.ingest(self.corpus, self.store)

        everything = self.health()
        scoped = self.health("D--demo")

        self.assertEqual(everything["totals"]["hook_failures"], 2)
        self.assertEqual(scoped["totals"]["hook_failures"], 1)
        self.assertEqual(scoped["hook_failures"][0]["session_id"], "s1")
        self.assertEqual(scoped["project"], "D--demo")

    def test_s018_the_per_project_health_figures_sum_to_the_unrestricted_figures(self):
        """The same arithmetic the fleet report holds, over this report's figures. Not
        `S-016`'s, but the property the scope selector is worth having only if it has."""
        other = self.corpus / "D--other"
        self.write_transcript([self.hook_record("h1", sid="s1"),
                               self.api_error_record("e1", sid="s1"),
                               self.abnormal_record("m1", sid="s1")], name="a.jsonl")
        self.write_transcript([self.hook_record("h2", sid="s2"),
                               self.abnormal_record("m2", sid="s2")], name="b.jsonl",
                              project=other)
        ingest.ingest(self.corpus, self.store)

        everything = self.health()["totals"]
        parts = [self.health(name)["totals"] for name in ("D--demo", "D--other")]

        for figure in ("events", "records", "hook_events", "hook_failures", "api_errors",
                       "abnormal_runs"):
            with self.subTest(figure=figure):
                self.assertEqual(sum(part[figure] for part in parts), everything[figure],
                                 f"the per-project {figure} no longer sum to the total")


class TestHealthPageBehaviour(HealthTestCase):
    """Structural assertions over the health renderer, carrying the bound `feat-0054` stated:
    the standard library has no JavaScript engine and this repository ships no dependency to
    add one, so these pin specific regressions rather than the page's behaviour in general.
    """

    def renderer_body(self) -> str:
        return renderer_source("health")

    def test_the_health_renderer_maps_every_returned_row_without_filtering(self):
        """Kills the mutation that drops rows at the surface while the API still returns them.
        An independent verification of `feat-0054` demonstrated exactly this shape: the skills
        renderer could drop every zero-count row with the whole suite green."""
        body = self.renderer_body()
        for collection in ("data.hook_failures", "data.retry_episodes",
                           "data.abnormal_runs", "data.kinds"):
            with self.subTest(collection=collection):
                self.assertIn(collection + ".map(", body,
                              f"the renderer no longer maps the {collection} the API "
                              f"returned")
                for hostile in (".filter(", ".slice(", ".splice("):
                    self.assertNotIn(
                        collection + hostile, body,
                        f"the renderer applies {hostile} to {collection} before rendering, "
                        f"so a failure the report counted can be missing from the page")

    def test_the_health_renderer_states_the_empty_case_rather_than_rendering_nothing(self):
        """The acceptance criterion in the page's own terms: the server says `empty` and the
        renderer has to do something with it, or a clean corpus renders as a blank panel."""
        body = self.renderer_body()
        self.assertIn("data.empty", body,
                      "the renderer ignores the server's empty flag, so a corpus with no "
                      "health events renders as a blank panel")
        self.assertIn("data.blind_spot", body)
        self.assertIn("data.replay_policy", body)

    def test_the_health_renderer_builds_no_interactive_element_of_its_own(self):
        """`S-019`'s enumeration is derived from one tagged construction site, and an element
        built anywhere else escapes it. This report renders per-session rows, which is the
        shape the guard was widened for."""
        body = self.renderer_body()
        for forbidden in ("<a ", 'el("a"', 'el("button"', 'el("form"', 'el("input"',
                          'el("select"', "addEventListener", "location.href", "window.open",
                          "fetch("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body,
                                 f"the health renderer builds {forbidden} directly, so it is "
                                 f"outside the enumeration S-019 is proven by")


if __name__ == "__main__":
    unittest.main()
