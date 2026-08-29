#!/usr/bin/env python3
"""Tests for the observatory store and ingester (`feat-0053`).

Each test names the scenario it proves, from `docs/spec/agent-observatory.md`. The six covered
here are S-005 to S-009 and S-022; the rest of the contract belongs to later tasks.

Standard library only, matching the rest of `tests/`.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.observatory import db, ingest  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "observatory" / "sample-session.jsonl"


def sha_tree(root: Path) -> dict:
    """SHA256 of every file under `root`, keyed by relative path."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class ObservatoryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obs-test-"))
        self.corpus = self.tmp / "projects"
        self.project = self.corpus / "D--demo"
        self.project.mkdir(parents=True)
        self.store = self.tmp / "store.db"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_transcript(self, name="session.jsonl", records=None, trailing=""):
        """Write a transcript with LF endings, plus an optional unterminated fragment."""
        path = self.project / name
        body = "".join(json.dumps(r) + "\n" for r in (records or []))
        with path.open("wb") as fh:
            fh.write((body + trailing).encode("utf-8"))
        return path

    @staticmethod
    def record(uuid, sid="s1", skill=None, ts="2026-08-01T10:00:00.000Z"):
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

    def counts(self):
        conn = db.connect(self.store)
        try:
            return {t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                    for t in ("session", "message", "tool_call", "agent_run", "health_event")}
        finally:
            conn.close()


class TestIdempotence(ObservatoryTestCase):
    def test_s005_reingesting_an_unchanged_corpus_adds_no_rows(self):
        """S-005: re-reporting an unchanged corpus changes nothing."""
        self.write_transcript(records=[self.record("a1"), self.record("a2")])

        first = ingest.ingest(self.corpus, self.store)
        before = self.counts()
        second = ingest.ingest(self.corpus, self.store)
        after = self.counts()

        self.assertEqual(first["records"], 2)
        self.assertEqual(before, after, "second run changed the row counts")
        self.assertEqual(second["records"], 0, "second run re-read records")
        self.assertEqual(second["files_read"], 0, "second run opened an unchanged transcript")


class TestIncremental(ObservatoryTestCase):
    def test_s006_second_run_reads_only_what_was_appended(self):
        """S-006: new records are picked up without re-reading the corpus."""
        path = self.write_transcript(records=[self.record("a1")])
        first = ingest.ingest(self.corpus, self.store)
        self.assertEqual(first["records"], 1)

        appended = json.dumps(self.record("a2")) + "\n"
        with path.open("ab") as fh:
            fh.write(appended.encode("utf-8"))

        second = ingest.ingest(self.corpus, self.store)

        self.assertEqual(second["records"], 1, "the appended record was not picked up alone")
        self.assertEqual(
            second["bytes_read"], len(appended.encode("utf-8")),
            "the second run read more than the appended bytes, so it re-read the corpus",
        )
        self.assertEqual(self.counts()["message"], 2)


class TestEmptyCorpus(ObservatoryTestCase):
    def test_s007_empty_corpus_is_distinguishable_by_exit_code(self):
        """S-007: an empty corpus is reported as empty, and not as success over nothing."""
        empty_rc = ingest.main(["--corpus", str(self.corpus), "--store", str(self.store),
                                "--quiet"])
        self.write_transcript(records=[self.record("a1")])
        populated_rc = ingest.main(["--corpus", str(self.corpus), "--store", str(self.store),
                                    "--quiet"])

        self.assertEqual(empty_rc, 2)
        self.assertEqual(populated_rc, 0)
        self.assertNotEqual(empty_rc, populated_rc,
                            "an empty corpus is indistinguishable from a populated one")

    def test_s007_a_missing_corpus_directory_is_also_empty_not_a_crash(self):
        """S-007: the degenerate input is stated, not absorbed."""
        rc = ingest.main(["--corpus", str(self.tmp / "nope"), "--store", str(self.store),
                          "--quiet"])
        self.assertEqual(rc, 2)


class TestUnreadableRecords(ObservatoryTestCase):
    def test_s008_incomplete_final_record_is_reported_and_not_consumed(self):
        """S-008: a half-written final record is reported, and picked up once complete.

        This is the pairing with S-006 that loses data when it is wrong: advancing the offset
        past a partial line means the rest of that record is never read.
        """
        partial = json.dumps(self.record("a2"))[:40]
        path = self.write_transcript(records=[self.record("a1")], trailing=partial)

        first = ingest.ingest(self.corpus, self.store)
        self.assertEqual(first["records"], 1)
        self.assertEqual(first["unreadable"], 1)
        self.assertTrue(any("incomplete final record" in n for n in first["notes"]))
        self.assertTrue(any(str(path) in n for n in first["notes"]),
                        "the note does not say where the unread record is")

        # Complete the record. It must now be read, which proves it was never skipped.
        with path.open("wb") as fh:
            fh.write((json.dumps(self.record("a1")) + "\n"
                      + json.dumps(self.record("a2")) + "\n").encode("utf-8"))

        second = ingest.ingest(self.corpus, self.store)
        self.assertEqual(second["records"], 1, "the completed record was skipped")
        self.assertEqual(self.counts()["message"], 2)

    def test_s008_terminated_but_unparseable_record_is_reported_and_stepped_over(self):
        """S-008: a corrupt but complete line is counted and does not stall the run."""
        path = self.project / "session.jsonl"
        body = (json.dumps(self.record("a1")) + "\n"
                + "{not json at all\n"
                + json.dumps(self.record("a2")) + "\n")
        with path.open("wb") as fh:
            fh.write(body.encode("utf-8"))

        result = ingest.ingest(self.corpus, self.store)

        self.assertEqual(result["records"], 2, "records after the corrupt line were lost")
        self.assertEqual(result["unreadable"], 1)
        self.assertTrue(any("does not parse" in n for n in result["notes"]))


class TestReadOnly(ObservatoryTestCase):
    def test_s009_the_corpus_is_byte_for_byte_unchanged(self):
        """S-009: nothing the harness owns is modified."""
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        self.write_transcript(records=[self.record("a1")], trailing="{partial")

        before = sha_tree(self.corpus)
        ingest.ingest(self.corpus, self.store)
        ingest.ingest(self.corpus, self.store)
        after = sha_tree(self.corpus)

        self.assertEqual(before, after, "ingest modified the corpus")
        self.assertNotEqual(before, {}, "the corpus was empty, so this proved nothing")

    def test_s009_the_store_is_written_outside_the_corpus(self):
        """S-009: a run adds no file to the harness's tree either."""
        self.write_transcript(records=[self.record("a1")])
        names_before = set(sha_tree(self.corpus))
        ingest.ingest(self.corpus, self.store)
        self.assertEqual(set(sha_tree(self.corpus)), names_before,
                         "ingest created a file inside the corpus")
        self.assertTrue(self.store.exists())


class TestNoNetwork(ObservatoryTestCase):
    def test_s022_no_socket_is_opened_during_a_full_ingest(self):
        """S-022: no data leaves the machine."""
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        self.write_transcript(records=[self.record("a1")])

        opened = []
        real_socket = socket.socket

        def forbidden(*args, **kwargs):
            opened.append(args)
            raise AssertionError("ingest attempted to open a socket")

        socket.socket = forbidden
        try:
            ingest.ingest(self.corpus, self.store)
        finally:
            socket.socket = real_socket

        self.assertEqual(opened, [], "a socket was opened during ingest")

    def test_s022_the_modules_import_nothing_network_capable(self):
        """S-022, from the other side: the import graph carries no network client."""
        forbidden = {"urllib", "urllib.request", "http.client", "requests", "socket",
                     "ftplib", "smtplib", "telnetlib"}
        for module in (db, ingest):
            source = Path(module.__file__).read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(
                    f"import {name}", source,
                    f"{Path(module.__file__).name} imports {name}",
                )


class TestFixtureExtraction(ObservatoryTestCase):
    def test_the_committed_fixture_populates_every_table(self):
        """Not a scenario. Guards the record shapes the six scenarios above ride on."""
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM session WHERE session_id = 's-fixture'").fetchone()
            self.assertEqual(row["title"], "A fixture session")
            self.assertEqual(row["pr_number"], 42)
            self.assertEqual(row["git_branch"], "main")

            skill = conn.execute(
                "SELECT COUNT(*) AS n FROM message WHERE attribution_skill = 'doc-sync'"
            ).fetchone()["n"]
            self.assertEqual(skill, 2)

            msg = conn.execute("SELECT * FROM message WHERE uuid = 'a1'").fetchone()
            self.assertEqual(
                (msg["input_tokens"], msg["output_tokens"], msg["cache_read_tokens"],
                 msg["cache_creation_tokens"], msg["thinking_tokens"]),
                (10, 20, 30, 40, 5))

            agent = conn.execute("SELECT * FROM agent_run WHERE agent_id = 'ag-1'").fetchone()
            self.assertEqual(agent["agent_type"], "Explore")
            self.assertEqual(agent["total_duration_ms"], 7233)

            tool = conn.execute(
                "SELECT * FROM tool_call WHERE tool_use_id = 'toolu_1'").fetchone()
            self.assertEqual(tool["name"], "Agent")
            self.assertEqual(tool["subagent_type"], "Explore")

            # The dispatching tool_use id comes from the tool_result block. Reading
            # `sourceToolUseID` instead left this NULL on every row of the real corpus and
            # made this join, which S-004 depends on, return nothing.
            self.assertEqual(agent["tool_use_id"], "toolu_1")
            joined = conn.execute(
                "SELECT COUNT(*) AS n FROM agent_run a JOIN tool_call t "
                "ON a.tool_use_id = t.tool_use_id").fetchone()["n"]
            self.assertEqual(joined, 1, "agent_run does not join to the tool_call that spawned it")

            health = conn.execute(
                "SELECT COUNT(*) AS n FROM health_event WHERE kind = 'api_error'"
            ).fetchone()["n"]
            self.assertEqual(health, 1)
        finally:
            conn.close()


class TestForkedHistory(ObservatoryTestCase):
    """A forked or resumed session replays earlier history verbatim into a new transcript, so
    one message legitimately appears under more than one sessionId. Totals must not
    double-count it and attribution must not be arbitrary."""

    def test_a_replayed_message_is_stored_once_and_its_sessions_are_both_recorded(self):
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            rows = conn.execute(
                "SELECT COUNT(*) AS n FROM message WHERE uuid = 'a1'").fetchone()["n"]
            self.assertEqual(rows, 1, "a replayed message was counted twice in totals")

            sessions = {r["session_id"] for r in conn.execute(
                "SELECT session_id FROM message_occurrence WHERE uuid = 'a1'")}
            self.assertEqual(sessions, {"s-fixture", "s-fork"},
                             "the sessions a replayed message appeared in were not recorded")
        finally:
            conn.close()

    def test_attribution_is_first_seen_and_does_not_move_on_re_ingest(self):
        """Last-writer-wins would let a later run silently move a message to another session."""
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        first = conn.execute(
            "SELECT session_id FROM message WHERE uuid = 'a1'").fetchone()["session_id"]
        conn.close()

        # Assert the literal winner, not merely that it is stable. Run-to-run stability is
        # also true of last-writer-wins over a sorted corpus, so comparing the value to itself
        # proves nothing: an independent verification restored the defect and this test stayed
        # green. `s-fixture` is the first occurrence in the fixture; `s-fork` is the replay.
        self.assertEqual(first, "s-fixture",
                         "the canonical row took the replayed session, not the first-seen one")

        # Force a full re-read the way a replaced transcript does, then confirm nothing moved.
        conn = db.connect(self.store)
        conn.execute("DELETE FROM ingest_state")
        conn.commit()
        conn.close()
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            again = conn.execute(
                "SELECT session_id FROM message WHERE uuid = 'a1'").fetchone()["session_id"]
            self.assertEqual(first, again, "re-ingesting moved a message's attribution")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) AS n FROM message WHERE uuid='a1'"
                             ).fetchone()["n"], 1)
        finally:
            conn.close()


class TestReplacedTranscript(ObservatoryTestCase):
    """The path where the store's own conflict handling is load-bearing rather than the offset
    bookkeeping. An independent verification found no test reached it."""

    def test_a_shortened_transcript_is_re_read_without_duplicating_rows(self):
        path = self.write_transcript(
            records=[self.record("a1"), self.record("a2"), self.record("a3")])
        ingest.ingest(self.corpus, self.store)
        self.assertEqual(self.counts()["message"], 3)

        # Replace with a shorter file. `stat.st_size < start` resets the offset to 0, so the
        # records are read a second time. Without the uuid conflict clause they would insert
        # again and the message count would climb.
        with path.open("wb") as fh:
            fh.write((json.dumps(self.record("a1")) + "\n"
                      + json.dumps(self.record("a2")) + "\n").encode("utf-8"))

        result = ingest.ingest(self.corpus, self.store)

        self.assertEqual(result["records"], 2, "the shortened transcript was not re-read")
        self.assertEqual(self.counts()["message"], 3,
                         "re-reading a replaced transcript duplicated rows")


class TestHookHealth(ObservatoryTestCase):
    """Hook outcomes arrive on `attachment` records, not `system` ones, and their numeric fields
    are strings in the corpus. Reading only `system` left `exit_code` NULL on every row."""

    def test_a_hook_failure_is_stored_with_its_exit_status_as_a_number(self):
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM health_event WHERE kind = 'hook_non_blocking_error'").fetchone()
            self.assertIsNotNone(row, "a hook failure produced no health event")
            self.assertEqual(row["hook_name"], "SessionStart:startup")
            self.assertEqual(row["hook_event"], "SessionStart")
            # Stored as integers even though the corpus carries them as strings, so that
            # `exit_code != 0` is a numeric comparison rather than a string one.
            self.assertEqual(row["exit_code"], 49)
            self.assertEqual(row["duration_ms"], 206)
            self.assertIsInstance(row["exit_code"], int)

            nonzero = conn.execute(
                "SELECT COUNT(*) AS n FROM health_event WHERE exit_code != 0").fetchone()["n"]
            self.assertEqual(nonzero, 1)
        finally:
            conn.close()

    def test_a_non_numeric_exit_code_becomes_null_rather_than_a_string(self):
        """SQLite's INTEGER affinity silently converts `"49"`, so the numeric case cannot tell
        a coerced implementation from an uncoerced one. It is the non-numeric case that can:
        affinity leaves a string sitting in an INTEGER column, where every later
        `exit_code != 0` comparison is a string comparison and quietly wrong."""
        rec = {
            "type": "attachment", "uuid": "at9", "sessionId": "s1",
            "timestamp": "2026-08-01T10:00:00.000Z", "cwd": "D:\\demo", "gitBranch": "main",
            "attachment": {"type": "hook_non_blocking_error", "hookName": "h",
                           "hookEvent": "Stop", "toolUseID": "t9", "stderr": "",
                           "exitCode": "killed", "durationMs": "n/a"},
        }
        self.write_transcript(records=[rec])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM health_event WHERE tool_use_id = 't9'").fetchone()
            self.assertIsNone(row["exit_code"], "a non-numeric exit code was stored as a string")
            self.assertIsNone(row["duration_ms"])
        finally:
            conn.close()

    def test_an_api_error_carries_its_retry_attempt(self):
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)
        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM health_event WHERE kind = 'api_error'").fetchone()
            self.assertEqual(row["attempt"], 2)
        finally:
            conn.close()


class TestSubagentAttribution(ObservatoryTestCase):
    """A subagent transcript reuses the parent's sessionId, so without these fields a subagent's
    messages are indistinguishable from the parent session's own."""

    def test_a_subagent_message_is_attributable_to_its_agent(self):
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute("SELECT * FROM message WHERE uuid = 'sa1'").fetchone()
            self.assertEqual(row["agent_id"], "ag-1")
            self.assertEqual(row["attribution_agent"], "Explore")
            self.assertEqual(row["is_sidechain"], 1)
            self.assertEqual(row["session_id"], "s-fixture",
                             "subagent transcripts reuse the parent session id")

            # The point of the columns: per-agent figures become derivable.
            tokens = conn.execute(
                "SELECT SUM(output_tokens) AS t FROM message WHERE agent_id = 'ag-1'"
            ).fetchone()["t"]
            self.assertEqual(tokens, 149)
        finally:
            conn.close()

    def test_the_sidecar_supplies_the_workspace_and_branch_s004_requires(self):
        """No transcript record carries either, so the `.meta.json` sidecar is the only source."""
        shutil.copy(FIXTURE, self.project / "fixture.jsonl")
        subagents = self.project / "s-fixture" / "subagents"
        subagents.mkdir(parents=True)
        (subagents / "agent-ag-1.meta.json").write_text(json.dumps({
            "agentType": "Explore", "description": "a fixture agent", "toolUseId": "toolu_1",
            "spawnDepth": 1, "spawnedWithWorktree": True,
            "worktreePath": "D:\\demo\\.claude\\worktrees\\agent-ag-1",
            "worktreeBranch": "worktree-agent-ag-1",
        }), encoding="utf-8", newline="\n")

        result = ingest.ingest(self.corpus, self.store)
        self.assertGreaterEqual(result["sidecars"], 1, "the sidecar was not read")

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM agent_run WHERE agent_id = 'ag-1'").fetchone()
            self.assertEqual(row["worktree_branch"], "worktree-agent-ag-1")
            self.assertEqual(row["spawn_depth"], 1)
            self.assertEqual(row["description"], "a fixture agent")
            # The transcript-derived metrics must survive the sidecar upsert.
            self.assertEqual(row["total_duration_ms"], 7233)
            self.assertEqual(row["agent_type"], "Explore")
        finally:
            conn.close()


class TestPathIdentity(ObservatoryTestCase):
    """S-006's guarantee must not depend on how the caller spelled the corpus path."""

    def test_the_same_corpus_reached_by_a_different_spelling_is_not_re_read(self):
        self.write_transcript(records=[self.record("a1")])
        first = ingest.ingest(self.corpus, self.store)
        self.assertGreater(first["bytes_read"], 0)

        # Same directory, spelled with a redundant `..` hop. A `.` segment will not do: pathlib
        # collapses it on construction, so the string is identical and the test proves nothing.
        # `..` is preserved because it cannot be collapsed safely in the presence of symlinks.
        respelled = self.corpus / ".." / self.corpus.name
        self.assertNotEqual(str(respelled), str(self.corpus),
                            "the two spellings are identical, so this asserts nothing")
        again = ingest.ingest(respelled, self.store)

        self.assertEqual(again["bytes_read"], 0, "a re-spelled corpus path caused a re-read")
        conn = db.connect(self.store)
        try:
            rows = conn.execute("SELECT COUNT(*) AS n FROM ingest_state").fetchone()["n"]
            self.assertEqual(rows, 1, "one transcript produced more than one ingest_state row")
        finally:
            conn.close()


class TestContextAndCompaction(ObservatoryTestCase):
    """S-017's two sources. Both are in the corpus and neither has another home."""

    def test_the_context_budget_series_is_parsed_into_numbers(self):
        rec = {"type": "attachment", "uuid": "c1", "sessionId": "s1",
               "timestamp": "2026-08-01T10:00:00.000Z", "cwd": "D:\\demo", "gitBranch": "m",
               "attachment": {"type": "total_tokens_reminder",
                              "text": "<total_tokens>14977910 tokens left</total_tokens>"}}
        self.write_transcript(records=[rec])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute("SELECT * FROM context_sample").fetchone()
            self.assertIsNotNone(row, "the context budget series was dropped")
            self.assertEqual(row["tokens_left"], 14977910)
            self.assertIsInstance(row["tokens_left"], int,
                                  "stored as prose a report would have to re-parse")
        finally:
            conn.close()

    def test_a_compaction_boundary_is_identifiable(self):
        rec = {"type": "system", "subtype": "compact_boundary", "uuid": "cb1",
               "sessionId": "s1", "timestamp": "2026-08-01T10:00:00.000Z", "cwd": "D:\\demo",
               "gitBranch": "m", "compactMetadata": {"trigger": "auto", "preTokens": 12345}}
        self.write_transcript(records=[rec])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM health_event WHERE kind = 'compact_boundary'").fetchone()
            self.assertIsNotNone(row, "compaction occasions are not identifiable")
            self.assertIn("auto", row["detail"])
        finally:
            conn.close()


class TestAbnormalTermination(ObservatoryTestCase):
    """S-016's third part. These markers sit on assistant records and nowhere else."""

    def test_an_api_error_message_and_an_aborted_stream_are_recorded(self):
        err = self.record("e1")
        err.update({"isApiErrorMessage": True, "apiErrorStatus": "rate_limit",
                    "error": "rate_limit"})
        aborted = self.record("e2")
        aborted["isAbortedMidStream"] = True
        self.write_transcript(records=[err, aborted, self.record("ok1")])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            e1 = conn.execute("SELECT * FROM message WHERE uuid = 'e1'").fetchone()
            self.assertEqual(e1["is_api_error"], 1)
            self.assertEqual(e1["api_error_status"], "rate_limit")
            e2 = conn.execute("SELECT * FROM message WHERE uuid = 'e2'").fetchone()
            self.assertEqual(e2["is_aborted_mid_stream"], 1)
            ok = conn.execute("SELECT * FROM message WHERE uuid = 'ok1'").fetchone()
            self.assertIsNone(ok["is_api_error"], "a healthy record was marked as an error")
        finally:
            conn.close()


class TestUnguardedBehaviours(ObservatoryTestCase):
    """Behaviours an independent verification found were asserted by nothing, each demonstrated
    by a mutation that survived the suite."""

    def test_transcripts_are_opened_in_a_mode_that_cannot_write(self):
        """S-009's rationale is the open mode, not only the resulting bytes. Hashing before and
        after cannot tell `rb` from `r+b`, so the mode itself is asserted here."""
        self.write_transcript(records=[self.record("a1")])
        modes = []
        real_open = Path.open

        def recording_open(self_path, mode="r", *args, **kwargs):
            if str(self_path).endswith(".jsonl"):
                modes.append(mode)
            return real_open(self_path, mode, *args, **kwargs)

        Path.open = recording_open
        try:
            ingest.ingest(self.corpus, self.store)
        finally:
            Path.open = real_open

        self.assertTrue(modes, "no transcript was opened")
        for mode in modes:
            self.assertEqual(mode, "rb", f"a transcript was opened in writable mode {mode!r}")

    def test_a_subagent_transcript_is_attributed_to_its_project_not_its_session(self):
        """S-018 rests entirely on the project column, and subagent transcripts sit two
        directories deeper than a top-level one."""
        subagents = self.project / "sess-1" / "subagents"
        subagents.mkdir(parents=True)
        body = json.dumps(self.record("sub1", sid="sess-1")) + "\n"
        (subagents / "agent-x.jsonl").write_bytes(body.encode("utf-8"))
        self.write_transcript(records=[self.record("top1")])

        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            projects = {r["project"] for r in conn.execute(
                "SELECT DISTINCT project FROM message_occurrence")}
            self.assertEqual(projects, {"D--demo"},
                             "a subagent transcript was attributed to the wrong project")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) AS n FROM message").fetchone()["n"], 2,
                "a nested subagent transcript was not discovered at all")
        finally:
            conn.close()

    def test_session_first_and_last_activity_span_the_whole_session(self):
        self.write_transcript(records=[
            self.record("m1", ts="2026-08-01T10:00:00.000Z"),
            self.record("m3", ts="2026-08-01T12:00:00.000Z"),
            self.record("m2", ts="2026-08-01T11:00:00.000Z"),
        ])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute("SELECT * FROM session WHERE session_id = 's1'").fetchone()
            self.assertEqual(row["first_ts"], "2026-08-01T10:00:00.000Z")
            self.assertEqual(row["last_ts"], "2026-08-01T12:00:00.000Z",
                             "last activity took the last record rather than the latest")
        finally:
            conn.close()

    def test_a_skill_invocation_records_which_skill(self):
        rec = self.record("s1msg")
        rec["message"]["content"] = [
            {"type": "tool_use", "id": "toolu_s", "name": "Skill", "input": {"skill": "doc-sync"}}]
        self.write_transcript(records=[rec])
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            row = conn.execute(
                "SELECT * FROM tool_call WHERE tool_use_id = 'toolu_s'").fetchone()
            self.assertEqual(row["skill_name"], "doc-sync")
        finally:
            conn.close()

    def test_re_reading_a_transcript_does_not_duplicate_health_events(self):
        """S-005 says no duplicate record is introduced. It was proven for `message` only."""
        rec = {"type": "system", "subtype": "api_error", "uuid": "sy1", "sessionId": "s1",
               "timestamp": "2026-08-01T10:00:00.000Z", "cwd": "D:\\demo", "gitBranch": "m",
               "error": "overloaded", "retryAttempt": 1, "toolUseID": "t1"}
        self.write_transcript(records=[rec])
        ingest.ingest(self.corpus, self.store)
        conn = db.connect(self.store)
        conn.execute("DELETE FROM ingest_state")   # force the re-read path
        conn.commit()
        conn.close()
        ingest.ingest(self.corpus, self.store)

        conn = db.connect(self.store)
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) AS n FROM health_event").fetchone()["n"], 1,
                "re-reading a transcript duplicated a health event")
        finally:
            conn.close()


class TestSchema(ObservatoryTestCase):
    def test_a_store_from_a_newer_schema_is_refused_not_misread(self):
        """Forward-only migrations: a shape this code does not know is an error, not a guess."""
        conn = db.connect(self.store)
        conn.execute("UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                     (str(db.SCHEMA_VERSION + 1),))
        conn.commit()
        conn.close()

        with self.assertRaises(db.SchemaTooNew):
            db.connect(self.store)

    def test_an_older_store_is_rebuilt_rather_than_left_holding_a_stale_shape(self):
        """The downgrade branch was guarded by nothing: deleting the whole DROP loop survived
        the suite. `CREATE TABLE IF NOT EXISTS` would silently keep a table missing its new
        columns, which is how a schema change becomes invisible."""
        self.write_transcript(records=[self.record("a1")])
        ingest.ingest(self.corpus, self.store)

        # Fake an older store: a narrower table, stale rows, and an older recorded version.
        conn = db.connect(self.store)
        conn.execute("DROP TABLE context_sample")
        conn.execute("CREATE TABLE context_sample (session_id TEXT)")
        conn.execute("INSERT INTO context_sample (session_id) VALUES ('stale')")
        conn.execute("UPDATE schema_meta SET value = '1' WHERE key = 'schema_version'")
        conn.commit()
        conn.close()

        conn = db.connect(self.store)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(context_sample)")}
            self.assertIn("tokens_left", cols,
                          "an older narrow table survived the migration")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) AS n FROM context_sample").fetchone()["n"], 0,
                "stale rows survived the rebuild")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) AS n FROM ingest_state").fetchone()["n"], 0,
                "offsets survived, so the corpus would never be re-read")
            self.assertEqual(
                conn.execute("SELECT value FROM schema_meta "
                             "WHERE key='schema_version'").fetchone()["value"],
                str(db.SCHEMA_VERSION))
        finally:
            conn.close()

        # And the rebuild refills correctly rather than leaving the store empty.
        again = ingest.ingest(self.corpus, self.store)
        self.assertEqual(again["records"], 1)

    def test_a_non_integer_schema_version_is_reported_not_a_traceback(self):
        conn = db.connect(self.store)
        conn.execute("UPDATE schema_meta SET value = 'v3' WHERE key = 'schema_version'")
        conn.commit()
        conn.close()
        self.write_transcript(records=[self.record("a1")])

        err = io.StringIO()
        real_stderr, sys.stderr = sys.stderr, err
        try:
            rc = ingest.main(["--corpus", str(self.corpus), "--store", str(self.store)])
        finally:
            sys.stderr = real_stderr
        self.assertEqual(rc, 1, "a corrupt schema version escaped as a traceback")

    def test_main_reports_a_too_new_store_as_could_not_run(self):
        self.write_transcript(records=[self.record("a1")])
        conn = db.connect(self.store)
        conn.execute("UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                     (str(db.SCHEMA_VERSION + 1),))
        conn.commit()
        conn.close()

        err = io.StringIO()
        real_stderr, sys.stderr = sys.stderr, err
        try:
            rc = ingest.main(["--corpus", str(self.corpus), "--store", str(self.store)])
        finally:
            sys.stderr = real_stderr
        self.assertEqual(rc, 1)
        self.assertIn("schema version", err.getvalue())


class RegistryTestCase(ObservatoryTestCase):
    """A registry directory this suite controls, never the machine's own.

    The liveness fixtures are real process states rather than a stubbed prober, and they are
    the same three on every operating system: this runner's own pid is alive, a subprocess
    that has been waited on is gone, and an entry stamped with another machine's pid domain
    cannot be checked. So each assertion exercises the real check on whichever platform it
    runs on, rather than one platform's branch and a mock everywhere else.
    """

    def setUp(self):
        super().setUp()
        self.registry = self.tmp / "sessions"
        self.registry.mkdir()
        self._reaped = []

    def write_entry(self, name, **fields):
        path = self.registry / name
        path.write_text(json.dumps(fields), encoding="utf-8", newline="\n")
        return path

    def reaped_pid(self):
        """A pid whose process has certainly exited.

        The `Popen` object is kept for the test's lifetime deliberately. On Windows it holds
        an open handle to the exited process, which keeps the pid from being reused under the
        assertion and is what lets `GetExitCodeProcess` report the exit rather than the
        lookup failing outright. Both routes conclude `gone`, which is the point.
        """
        proc = subprocess.Popen([sys.executable, "-c", "pass"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait()
        self._reaped.append(proc)
        return proc.pid


class TestRegistryReader(RegistryTestCase):
    """The live-session registry, the one source S-012 needs and the store does not hold."""

    def test_the_registry_reader_finds_every_entry_and_ignores_the_key_files(self):
        """The directory holds `<pid>.<hash>.key` files beside the entries. They name no
        session and reading them as entries would report unreadable records that are not
        records at all."""
        self.write_entry("100.json", pid=100, sessionId="s-one", cwd="D:\\a")
        self.write_entry("200.json", pid=200, sessionId="s-two", cwd="D:\\b")
        (self.registry / "100.abcdef.key").write_text("not json", encoding="utf-8",
                                                      newline="\n")

        found = ingest.read_registry(self.registry)

        self.assertTrue(found["present"])
        self.assertEqual({entry["sessionId"] for entry in found["entries"]},
                         {"s-one", "s-two"})
        self.assertEqual(found["unreadable"], 0,
                         "a .key file was counted as an unreadable entry")

    def test_the_registry_reader_reports_an_unparseable_entry_rather_than_dropping_it(self):
        """S-008's habit, applied to the second source: the harness may be writing an entry
        as this reads it, and a half-written file is stated rather than absorbed."""
        self.write_entry("100.json", pid=100, sessionId="s-one")
        (self.registry / "200.json").write_text('{"pid": 200, "sessi',
                                                encoding="utf-8", newline="\n")

        found = ingest.read_registry(self.registry)

        self.assertEqual(len(found["entries"]), 1)
        self.assertEqual(found["unreadable"], 1,
                         "an entry that did not parse was dropped without being counted")
        self.assertTrue(any("200.json" in note for note in found["notes"]),
                        "the unreadable entry was counted without being named")

    def test_the_registry_reader_reports_an_entry_naming_no_session(self):
        """An entry with no `sessionId` parses and still names nothing. Treating it as an
        entry would put a session with no id into the report."""
        self.write_entry("100.json", pid=100)

        found = ingest.read_registry(self.registry)

        self.assertEqual(found["entries"], [])
        self.assertEqual(found["unreadable"], 1)

    def test_an_absent_registry_is_an_empty_answer_rather_than_an_error(self):
        """A machine with no session running has no registry, and the report must render."""
        absent = self.tmp / "no-registry-here"

        found = ingest.read_registry(absent)

        self.assertFalse(found["present"])
        self.assertEqual(found["entries"], [])
        self.assertEqual(found["unreadable"], 0)
        self.assertFalse(absent.exists(), "reading an absent registry created one")

    def test_reading_the_registry_changes_nothing_in_it(self):
        """S-009 covers everything the harness owns, and the registry is the second such
        thing this code reads. `feat-0053` proved it for the corpus; nothing had asked it of
        this directory."""
        self.write_entry("100.json", pid=100, sessionId="s-one")
        (self.registry / "100.abcdef.key").write_text("opaque", encoding="utf-8",
                                                      newline="\n")
        before = sha_tree(self.registry)

        ingest.read_registry(self.registry)

        self.assertEqual(sha_tree(self.registry), before,
                         "reading the registry modified a file the harness owns")


class TestProcessState(RegistryTestCase):
    """Whether a registry entry's process is still there. The whole of S-012's liveness."""

    def test_this_running_process_is_reported_alive(self):
        state, evidence = ingest.process_state(os.getpid())
        self.assertEqual(state, ingest.ALIVE, evidence)

    def test_a_reaped_process_is_reported_gone_rather_than_alive(self):
        """The stale-entry case at its source. A registry entry can outlive its process, so
        an implementation that answered from the entry alone reports this one alive."""
        state, evidence = ingest.process_state(self.reaped_pid())
        self.assertEqual(state, ingest.GONE, evidence)

    def test_an_entry_with_no_usable_pid_is_unknown_rather_than_alive(self):
        for pid in (None, 0, -1, "not-a-pid", True):
            with self.subTest(pid=pid):
                state, _ = ingest.process_state(pid)
                self.assertEqual(state, ingest.UNKNOWN)

    def test_an_entry_from_another_machines_pid_domain_is_not_checked(self):
        """`pidDomain` is `<platform>:<host>`, so an entry another machine wrote names a pid
        in a table this one cannot query. The pid used here is alive locally, so an
        implementation ignoring the domain reports running rather than unverified.

        Open Question 3 of the contract scopes the whole thing to one machine. This is what
        that scope looks like when the assumption is broken rather than assumed.
        """
        state, evidence = ingest.process_state(
            os.getpid(), pid_domain="not-this-platform:another-machine")
        self.assertEqual(state, ingest.UNKNOWN, evidence)

    def test_os_kill_is_never_reached_on_the_windows_liveness_path(self):
        """On Windows, CPython's `os.kill` calls `TerminateProcess` for every signal that is
        not a console control event. So `os.kill(pid, 0)`, the POSIX idiom for "does this pid
        exist", kills the session it was asked about: the observatory would end the very
        sessions its fleet report exists to show.

        The stub raises rather than records, so a reintroduction fails here loudly instead of
        being read back from a list nobody asserts on.
        """
        calls = []

        def refuse(*args, **kwargs):
            calls.append(args)
            raise AssertionError("os.kill was called on a Windows liveness path")

        real_kill = os.kill
        os.kill = refuse
        try:
            state, _ = ingest.process_state(os.getpid(), platform="win32")
            self.assertIn(state, (ingest.ALIVE, ingest.UNKNOWN))
            if os.name == "nt":
                # The POSIX branch must also refuse to run here, for the same reason.
                state, _ = ingest.process_state(os.getpid(), platform="linux")
                self.assertEqual(state, ingest.UNKNOWN)
        finally:
            os.kill = real_kill
        self.assertEqual(calls, [], "os.kill was reached on a Windows process table")

    def test_a_platform_with_no_defined_check_is_unknown_rather_than_assumed_alive(self):
        state, _ = ingest.process_state(os.getpid(), platform="some-future-os")
        self.assertEqual(state, ingest.UNKNOWN)

    def test_the_liveness_check_names_what_this_build_can_establish(self):
        """The phrase the report shows a reader. It has to change with the platform, because
        the whole point of saying it is that the Windows check is stronger than the POSIX one
        and a reader must not assume the strong one everywhere."""
        self.assertTrue(ingest.liveness_check())
        self.assertTrue(ingest.liveness_check("some-future-os").startswith("none"))
        if os.name == "nt":
            # Both words, not just "identity". Identity needs a recorded start time to
            # compare against, so a label promising it unconditionally is false for an
            # entry that carries none. An automated review of pull request 76 caught the
            # first published label doing exactly that, and this is what stops it coming
            # back: the overstating string named only identity.
            label = ingest.liveness_check()
            self.assertIn("identity", label)
            self.assertIn("presence", label,
                          "the Windows label claims identity without naming the presence "
                          "fallback an entry with no recorded start time actually gets")
        elif os.name == "posix":
            self.assertIn("presence", ingest.liveness_check())

    @unittest.skipUnless(sys.platform == "win32",
                         "the presence fallback is a Windows-path branch")
    def test_an_entry_with_no_recorded_start_time_is_confirmed_on_presence_alone(self):
        """The bound behind the Windows label, and the thing the first published wording
        overstated. Identity needs something to compare against, so an entry carrying no
        `procStart` gets the weaker check, and the evidence has to say the pid was not
        matched rather than implying it was."""
        state, evidence = ingest.process_state(os.getpid(), proc_start=None)

        self.assertEqual(state, ingest.ALIVE)
        self.assertIn("no comparable", evidence,
                      "an entry with no recorded start time was reported as though its pid "
                      "had been matched to the entry")

    @unittest.skipUnless(sys.platform == "win32",
                         "process identity is established from procStart, which is verified "
                         "only on Windows")
    def test_a_pid_whose_start_time_disagrees_with_the_entry_is_reported_gone(self):
        """Pid reuse, the failure presence alone cannot see. The pid is this process and is
        certainly alive; what makes the entry stale is that the process now holding the pid
        is not the one the entry recorded.

        `procStart` is the creation FILETIME. Confirmed on 2026-08-28 against three live
        entries: `134324400435518083` is 1787966443.6 epoch seconds, 3.7 seconds before that
        entry's own `startedAt`, and equal to the process start time the operating system
        reports. This test is skipped on Linux and macOS, where `procStart`'s meaning is not
        verified and the check is presence only.
        """
        alive, _ = ingest.process_state(os.getpid(), proc_start=None)
        self.assertEqual(alive, ingest.ALIVE)

        state, evidence = ingest.process_state(os.getpid(), proc_start="1")

        self.assertEqual(state, ingest.GONE,
                         "a reused pid was reported alive on the strength of the pid alone")
        self.assertIn("reused", evidence)


if __name__ == "__main__":
    unittest.main()
