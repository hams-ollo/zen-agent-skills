#!/usr/bin/env python3
"""Tests for the observatory server, its page shell, and the skills report (`feat-0054`).

Each test names the scenario it proves, from `docs/spec/agent-observatory.md`. The two covered
here are S-001 and S-002; the rest of the contract belongs to `feat-0053` (already covered in
`test_observatory.py`) and to the four report tasks that follow this one.

Standard library only, matching the rest of `tests/`. The HTTP client is `http.client` against
a loopback server this suite starts and stops itself, so nothing here reaches a remote host.
"""

from __future__ import annotations

import http.client
import io
import ipaddress
import json
import re
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import install                            # noqa: E402
from scripts.observatory import db, ingest, serve      # noqa: E402

UI_INDEX = REPO_ROOT / "scripts" / "observatory" / "ui" / "index.html"


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


class ServerTestCase(ServeTestCase):
    """Adds a running loopback server for the tests that go over HTTP."""

    def serve_on_loopback(self, roster=None):
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0,
                                   roster=roster, quiet=True)
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
        """The body of `RENDERERS.skills`, from its key to the end of the registry."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("var RENDERERS")
        return html[start:start + 2000]

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

    def test_the_four_unbuilt_reports_name_the_task_that_owes_them(self):
        owed = {r["id"]: r["owner"] for r in serve.REPORTS if r["endpoint"] is None}
        self.assertEqual(owed, {"fleet": "feat-0055", "waves": "feat-0056",
                                "cost": "feat-0057", "health": "feat-0058"})

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


if __name__ == "__main__":
    unittest.main()
