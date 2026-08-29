#!/usr/bin/env python3
"""Tests for the waves report (`feat-0056`): S-003 and S-004 of `docs/spec/agent-observatory.md`.

Every test names the scenario it proves. `S-003` is the per-run half, "each dispatched agent is
reported with its type, the model it resolved to, its duration, its token total, its tool-call
count, and whether it completed or ended without completing". `S-004` is the grouping half, "a
session that dispatched several agents against separate isolated workspaces" reported as one
wave, "each with the workspace and branch it was given and its own start and end time".

**The fixtures are shaped from the corpus, not from memory.** Each record kind below was read
off this maintainer's own transcripts on 2026-08-29 before it was written here, because a
hand-written fixture carrying a field combination the corpus never produces is how `feat-0053`
shipped a passing test over a store column that was NULL on every real row. The three shapes
that matter:

- The dispatch is an `assistant` record whose `message.content` holds a `tool_use` block named
  `Agent`. Exactly one per record: of 278 dispatches in the corpus, no assistant record carries
  two, so a wave is never one message with several blocks.
- The result is a `user` record carrying `toolUseResult` with `agentId`, and the dispatching
  tool-use id lives on its `tool_result` content block rather than in `sourceToolUseID`.
- The workspace and branch live only in the `agent-<id>.meta.json` sidecar beside the subagent
  transcript. No transcript record carries either.

Standard library only, matching the rest of `tests/`.
"""

from __future__ import annotations

import http.client
import json
import re
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.observatory import db, ingest, serve      # noqa: E402

UI_INDEX = REPO_ROOT / "scripts" / "observatory" / "ui" / "index.html"


class WavesTestCase(unittest.TestCase):
    """A corpus holding dispatches, their results, and the subagent transcripts they produced."""

    PROJECT = "D--demo"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obs-waves-"))
        self.corpus = self.tmp / "projects"
        self.project = self.corpus / self.PROJECT
        self.project.mkdir(parents=True)
        self.store = self.tmp / "store.db"
        self.registry = self.tmp / "sessions"      # never created: see test_observatory_serve
        self.lines: dict = {}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- record shapes ---------------------------------------------------------------

    @staticmethod
    def _shell(rtype, uuid, sid, ts, **extra):
        record = {
            "type": rtype, "uuid": uuid, "parentUuid": None, "sessionId": sid,
            "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main", "version": "2.1.247",
            "entrypoint": "claude-desktop", "isSidechain": False,
        }
        record.update(extra)
        return record

    def dispatch(self, uuid, tool_use_id, sid="s1", ts="2026-08-01T10:00:00.000Z",
                 description="do a thing", subagent_type="general-purpose"):
        """The dispatching assistant record: one `Agent` tool_use block, as the corpus has it."""
        record = self._shell("assistant", uuid, sid, ts)
        record["message"] = {
            "model": "claude-opus-5", "role": "assistant", "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "id": tool_use_id, "name": "Agent",
                         "input": {"description": description,
                                   "subagent_type": subagent_type,
                                   "prompt": "PROMPT-BODY-THAT-MUST-NOT-BE-REPORTED"},
                         "caller": {"type": "direct"}}],
            "usage": {"input_tokens": 2, "output_tokens": 40,
                      "cache_read_input_tokens": 100, "cache_creation_input_tokens": 10},
        }
        return record

    def result(self, uuid, tool_use_id, agent_id, sid="s1",
               ts="2026-08-01T10:00:01.000Z", status="async_launched",
               resolved_model="claude-opus-5", agent_type=None,
               total_tokens=None, total_duration_ms=None, total_tool_use_count=None):
        """The result record. `async_launched` is the corpus's overwhelming majority: 314 of
        343 agent-result records say it, 29 say `completed`, and no third value appears."""
        record = self._shell("user", uuid, sid, ts,
                             sourceToolAssistantUUID="ignored-by-the-store")
        record["message"] = {
            "role": "user",
            "content": [{"tool_use_id": tool_use_id, "type": "tool_result",
                         "content": "RESULT-BODY-THAT-MUST-NOT-BE-REPORTED"}],
        }
        payload = {"status": status, "agentId": agent_id,
                   "resolvedModel": resolved_model,
                   "prompt": "PROMPT-BODY-THAT-MUST-NOT-BE-REPORTED"}
        if status == "async_launched":
            payload.update({"isAsync": True, "description": "do a thing",
                            "outputFile": "C:\\tmp\\out", "canReadOutputFile": True})
        if total_tokens is not None:
            payload.update({"agentType": agent_type, "totalTokens": total_tokens,
                            "totalDurationMs": total_duration_ms,
                            "totalToolUseCount": total_tool_use_count,
                            "content": "RESULT-BODY-THAT-MUST-NOT-BE-REPORTED"})
        record["toolUseResult"] = payload
        return record

    def agent_message(self, uuid, agent_id, sid="s1", ts="2026-08-01T10:00:05.000Z",
                      usage=(2, 50, 1000, 30), tool_use_ids=(),
                      agent_type="general-purpose"):
        """One message from inside the subagent's own transcript.

        A subagent transcript reuses its parent's `sessionId`, which is why `agentId` is the
        only thing that separates 16,426 subagent messages from the dispatching session's own.
        """
        record = self._shell("assistant", uuid, sid, ts, isSidechain=True,
                             agentId=agent_id, attributionAgent=agent_type)
        record["message"] = {
            "model": "claude-opus-5", "role": "assistant",
            "content": [{"type": "tool_use", "id": tool_use_id, "name": "Read",
                         "input": {"file_path": "x"}} for tool_use_id in tool_use_ids],
            "usage": {"input_tokens": usage[0], "output_tokens": usage[1],
                      "cache_read_input_tokens": usage[2],
                      "cache_creation_input_tokens": usage[3]},
        }
        return record

    def sidecar(self, agent_id, sid="s1", agent_type="general-purpose",
                description="do a thing", worktree=True, spawn_depth=1,
                tool_use_id=None):
        """The `agent-<id>.meta.json` sidecar, the only source of workspace and branch."""
        directory = self.project / sid / "subagents"
        directory.mkdir(parents=True, exist_ok=True)
        payload = {"agentType": agent_type, "description": description,
                   "toolUseId": tool_use_id, "spawnDepth": spawn_depth, "model": "opus"}
        if worktree:
            payload["worktreePath"] = f"D:\\demo\\.claude\\worktrees\\agent-{agent_id}"
            payload["worktreeBranch"] = f"worktree-agent-{agent_id}"
        (directory / f"agent-{agent_id}.meta.json").write_text(
            json.dumps(payload), encoding="utf-8", newline="\n")

    # -- writing and reading ---------------------------------------------------------

    def append(self, records, name="session.jsonl", subdir=None):
        """Append records to a transcript, which is how the corpus grows."""
        path = (self.project / subdir / name) if subdir else (self.project / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(json.dumps(r) + "\n" for r in records)
        with path.open("ab") as handle:
            handle.write(body.encode("utf-8"))
        return path

    def build(self):
        return ingest.ingest(self.corpus, self.store)

    def report(self, project=None, gap_seconds=serve.WAVE_GAP_SECONDS):
        conn = db.connect(self.store)
        try:
            return serve.waves_report(conn, project, gap_seconds)
        finally:
            conn.close()

    # -- one whole dispatched agent, assembled ---------------------------------------

    def dispatched(self, agent_id, tool_use_id, at, sid="s1", status="async_launched",
                   worktree=True, spawn_depth=1, agent_type="general-purpose",
                   description=None, messages=None, completion=None):
        """A dispatch, its result, its sidecar, and its own transcript, written as one unit.

        `at` is the dispatch timestamp. `messages` is a list of `(ts, usage, tool_use_ids)`
        for the subagent's own transcript; `completion` is
        `(total_tokens, total_duration_ms, total_tool_use_count)` for a run the harness
        recorded a completion record for.
        """
        description = description or f"work {agent_id}"
        records = [self.dispatch(f"d-{agent_id}", tool_use_id, sid=sid, ts=at,
                                 description=description, subagent_type=agent_type)]
        if status is not None:
            total_tokens, total_duration_ms, total_tool_use_count = (
                completion if completion else (None, None, None))
            records.append(self.result(
                f"r-{agent_id}", tool_use_id, agent_id, sid=sid, ts=at, status=status,
                agent_type=agent_type if completion else None,
                total_tokens=total_tokens, total_duration_ms=total_duration_ms,
                total_tool_use_count=total_tool_use_count))
        self.append(records)
        self.sidecar(agent_id, sid=sid, agent_type=agent_type, description=description,
                     worktree=worktree, spawn_depth=spawn_depth, tool_use_id=tool_use_id)
        for index, (ts, usage, tool_use_ids) in enumerate(messages or []):
            self.append([self.agent_message(f"m-{agent_id}-{index}", agent_id, sid=sid,
                                            ts=ts, usage=usage, tool_use_ids=tool_use_ids,
                                            agent_type=agent_type)],
                        name=f"agent-{agent_id}.jsonl", subdir=f"{sid}/subagents")

    @staticmethod
    def run_of(payload, agent_id):
        found = [run for run in payload["runs"] if run["agent_id"] == agent_id]
        assert len(found) == 1, f"{agent_id} appears {len(found)} time(s) in the report"
        return found[0]


class TestSubagentRuns(WavesTestCase):
    """S-003: subagent runs are reported with their outcome and cost."""

    def test_s003_each_dispatched_agent_is_reported_with_type_model_duration_tokens_and_tools(
            self):
        """The scenario's Then, field by field, over a run the harness recorded in full.

        The oracle is the exact six-tuple rather than "the fields are present": a report that
        returned zeros for all of them, or that swapped tokens and tool calls, would satisfy a
        presence check and satisfies nothing here.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        agent_type="Explore",
                        completion=(122287, 378560, 24),
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ("t1",))])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertEqual(
            (run["agent_type"], run["resolved_model"], run["duration_ms"],
             run["tokens"], run["tool_calls"], run["outcome"]),
            ("Explore", "claude-opus-5", 378560, 122287, 24, "completed"))

    def test_s003_a_completed_runs_figures_are_the_harnesss_own_and_say_so(self):
        """Each figure carries its basis, because an exact figure and an approximation must
        never share a column without a reader being told which is which."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        completion=(122287, 378560, 24),
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ("t1",))])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertEqual((run["tokens_basis"], run["duration_basis"],
                          run["tool_calls_basis"]), ("reported", "reported", "reported"))

    def test_s003_a_backgrounded_launch_is_reported_launched_rather_than_as_a_failure(self):
        """The case the corpus is made of: 254 of 278 runs. The dispatch was acknowledged, no
        completion record exists anywhere, and that is not a failed run."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ())])
        self.build()

        payload = self.report()
        run = self.run_of(payload, "a1")

        self.assertEqual(run["outcome"], "launched")
        self.assertEqual(run["status"], "async_launched")
        self.assertEqual(payload["totals"]["outcomes"],
                         {"completed": 0, "launched": 1, "unrecorded": 0, "unrecognised": 0})

    def test_s003_a_run_with_no_result_record_is_reported_unrecorded_rather_than_as_a_failure(
            self):
        """The in-flight case: an agent still running, or interrupted, when the corpus was
        read. Nothing acknowledged its dispatch, so only the sidecar knows it exists.

        Five runs in this maintainer's corpus are in exactly this position on 2026-08-29.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status=None,
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ())])
        self.build()

        payload = self.report()
        run = self.run_of(payload, "a1")

        self.assertEqual(run["outcome"], "unrecorded")
        self.assertIsNone(run["status"])
        self.assertEqual(payload["totals"]["outcomes"]["unrecorded"], 1)
        self.assertEqual(payload["totals"]["outcomes"]["completed"], 0)

    def test_s003_an_in_flight_run_still_carries_its_type_model_and_figures(self):
        """"Not a failure" is not enough on its own. A run with no completion record must still
        answer the scenario's other five fields, or it has been reported as an absence."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status=None,
                        agent_type="Explore",
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ("t1", "t2")),
                                  ("2026-08-01T10:02:05.000Z", (2, 60, 2000, 40), ("t3",))])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertEqual(run["agent_type"], "Explore")
        self.assertEqual(run["tool_calls"], 3)
        self.assertEqual(run["duration_ms"], 120000)
        self.assertEqual(run["tokens"], 2102)
        self.assertEqual(run["tokens_basis"], "derived")

    def test_s003_a_derived_token_total_is_the_last_messages_own_accounting(self):
        """The derivation, pinned against the mutation that looks obviously right and is off by
        a factor of tens: summing every message.

        Checked against the 19 runs carrying both a completion record and their own messages on
        2026-08-29: the harness's total equals the last message's four token kinds added up,
        exactly on 17 and within 9 percent on the other two, while the sum over all messages
        overstates it by 20 to 60 times, because each message's input and cache-read counts
        include the whole conversation before it again.

        The fixture makes the two answers unmistakable: the sum is 6,600 and the last message
        is 3,300, so a report doing either is identifiable from the number alone.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:05.000Z", (100, 100, 500, 400), ()),
                                  ("2026-08-01T10:00:10.000Z", (100, 200, 1000, 900), ()),
                                  ("2026-08-01T10:00:20.000Z", (100, 300, 2000, 900), ())])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertEqual(run["tokens"], 3300,
                         "the derived total is not the last message's own accounting")
        self.assertNotEqual(run["tokens"], 6600,
                            "the derived total sums every message, which double-counts the "
                            "conversation prefix on each one")

    def test_s003_a_forked_session_replaying_history_does_not_double_a_runs_figures(self):
        """A forked or resumed session replays earlier history verbatim under a **new** session
        id, which is why 5,442 message ids in this maintainer's corpus appear under more than
        one. A figure built over `message_occurrence`, which records every session a message
        was seen in, therefore doubles; one built over `message`, which holds one canonical row
        per uuid, does not. Both are one join apart in the query, and the difference is
        invisible until a fork exists.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:05.000Z", (100, 100, 500, 400), ("t1",)),
                                  ("2026-08-01T10:00:20.000Z", (100, 300, 2000, 900), ("t2",))])
        self.build()
        before = self.run_of(self.report(), "a1")

        # The fork: the same uuids, the same agent id, a different session id. Verbatim in
        # every other respect, which is what the harness actually writes.
        original = self.project / "s1" / "subagents" / "agent-a1.jsonl"
        forked = []
        for line in original.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                record["sessionId"] = "s1-fork"
                forked.append(record)
        self.append(forked, name="agent-a1.jsonl", subdir="s1-fork/subagents")
        self.build()
        after = self.run_of(self.report(), "a1")

        self.assertEqual((after["tokens"], after["tool_calls"], after["messages"]),
                         (before["tokens"], before["tool_calls"], before["messages"]),
                         "a forked session's replayed history changed the run's figures, so "
                         "the report is counting occurrences rather than distinct messages")
        self.assertEqual((after["tool_calls"], after["messages"]), (2, 2))

    def test_s003_a_run_with_neither_a_completion_record_nor_messages_reports_unknown(self):
        """Unknown rather than zero. A zero is a figure somebody measured, and reporting one
        here would put an invented number beside 267 real ones with nothing to tell them
        apart. Ten runs in this maintainer's corpus are in this position."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertIsNone(run["tokens"])
        self.assertIsNone(run["tool_calls"])
        self.assertIsNone(run["duration_ms"])
        self.assertEqual((run["tokens_basis"], run["tool_calls_basis"],
                          run["duration_basis"]), ("unknown", "unknown", "unknown"))

    def test_s003_a_derived_tool_call_count_of_zero_is_a_measured_zero(self):
        """The other side of the rule above: an agent that wrote messages and called no tool
        really did call none, and reporting that as unknown would lose a real figure."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ())])
        self.build()

        run = self.run_of(self.report(), "a1")

        self.assertEqual(run["tool_calls"], 0)
        self.assertEqual(run["tool_calls_basis"], "derived")

    def test_s003_an_unrecognised_status_is_reported_as_itself(self):
        """A status added upstream must not arrive silently as one of the three this report
        knows. Today the corpus writes exactly two values; the day it writes a third, the
        report has to say so rather than absorb it."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="cancelled",
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ())])
        self.build()

        payload = self.report()
        run = self.run_of(payload, "a1")

        self.assertEqual(run["outcome"], "unrecognised")
        self.assertEqual(run["status"], "cancelled")
        self.assertEqual(payload["totals"]["outcomes"]["unrecognised"], 1)

    def test_s003_no_outcome_the_report_can_produce_means_the_run_failed(self):
        """An enumeration claim, which is what makes it decidable. Every outcome
        `_outcome_of` can return is declared in `RUN_OUTCOMES` with a meaning, and the two
        sets are resolved against each other rather than reviewed.
        """
        reachable = {serve._outcome_of(status) for status in
                     (None, "completed", "async_launched", "something-new", "")}
        declared = {entry["id"] for entry in serve.RUN_OUTCOMES}

        self.assertEqual(reachable, declared,
                         "an outcome the report can produce is not declared, or a declared "
                         "one is unreachable")
        for entry in serve.RUN_OUTCOMES:
            with self.subTest(outcome=entry["id"]):
                self.assertTrue(entry["meaning"].strip(),
                                f"outcome {entry['id']} is offered with no meaning")
                self.assertNotIn("fail", entry["id"],
                                 "an outcome is named as a failure, which the corpus cannot "
                                 "establish: it records no failed status at all")

    def test_s003_the_report_is_served_over_http_and_matches_the_store(self):
        """The route half. Calling the function directly cannot catch an endpoint that is
        registered and unrouted, which is the mutation `feat-0054` recorded."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        completion=(122287, 378560, 24),
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ("t1",))])
        self.build()
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0, quiet=True,
                                   registry=self.registry, corpus=self.corpus)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)

        connection = http.client.HTTPConnection(*server.server_address[:2], timeout=10)
        try:
            connection.request("GET", "/api/waves")
            response = connection.getresponse()
            status, served = response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

        self.assertEqual(status, 200)
        self.assertEqual(served["report"], "waves")
        self.assertEqual(served["totals"], self.report()["totals"])
        self.assertEqual(self.run_of(served, "a1")["tokens"], 122287)


class TestDispatchedWave(WavesTestCase):
    """S-004: a dispatched wave is reported as one unit of work."""

    def wave_fixture(self):
        """Three agents into three isolated worktrees, dispatched 20 and 24 seconds apart.

        Those intervals are the corpus's own: of the 60 gaps between consecutive isolated
        dispatches on this maintainer's machine, 53 are 53.3 seconds or less and the median is
        about 17.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:10.000Z", (2, 50, 1000, 30), ("t1",)),
                                  ("2026-08-01T10:05:00.000Z", (2, 50, 1000, 30), ())])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z",
                        messages=[("2026-08-01T10:00:30.000Z", (2, 50, 1000, 30), ("t2",)),
                                  ("2026-08-01T10:06:00.000Z", (2, 50, 1000, 30), ())])
        self.dispatched("a3", "toolu_3", "2026-08-01T10:00:44.000Z",
                        messages=[("2026-08-01T10:00:50.000Z", (2, 50, 1000, 30), ("t3",)),
                                  ("2026-08-01T10:07:00.000Z", (2, 50, 1000, 30), ())])
        self.build()

    def test_s004_agents_dispatched_against_separate_workspaces_are_reported_as_one_wave(self):
        """The scenario's Then: those agents, together, as one unit rather than three rows a
        reader has to spot the relationship between."""
        self.wave_fixture()

        payload = self.report()

        self.assertEqual(len(payload["waves"]), 1)
        wave = payload["waves"][0]
        self.assertEqual([member["agent_id"] for member in wave["members"]],
                         ["a1", "a2", "a3"])
        self.assertEqual((wave["size"], wave["isolated"], wave["workspaces"],
                          wave["branches"]), (3, 3, 3, 3))

    def test_s004_each_wave_member_carries_the_workspace_and_branch_it_was_given(self):
        """In those words. Both come from the sidecar and from nowhere else: no transcript
        record carries either, which is why `feat-0053` had to read the sidecars at all."""
        self.wave_fixture()

        wave = self.report()["waves"][0]

        self.assertEqual(
            [(m["worktree_path"], m["worktree_branch"]) for m in wave["members"]],
            [("D:\\demo\\.claude\\worktrees\\agent-a1", "worktree-agent-a1"),
             ("D:\\demo\\.claude\\worktrees\\agent-a2", "worktree-agent-a2"),
             ("D:\\demo\\.claude\\worktrees\\agent-a3", "worktree-agent-a3")])

    def test_s004_each_wave_member_carries_its_own_start_and_end_time(self):
        """"Its own" is the load-bearing word. A wave has one span and its members have three,
        and reporting the wave's twice would lose exactly what the grouping is for."""
        self.wave_fixture()

        wave = self.report()["waves"][0]

        self.assertEqual([(m["started"], m["ended"]) for m in wave["members"]],
                         [("2026-08-01T10:00:00.000Z", "2026-08-01T10:05:00.000Z"),
                          ("2026-08-01T10:00:20.000Z", "2026-08-01T10:06:00.000Z"),
                          ("2026-08-01T10:00:44.000Z", "2026-08-01T10:07:00.000Z")])
        self.assertEqual((wave["started"], wave["ended"]),
                         ("2026-08-01T10:00:00.000Z", "2026-08-01T10:07:00.000Z"))

    def test_s004_a_dispatch_after_a_long_pause_starts_a_new_wave(self):
        """The rule has to separate as well as group, or every session is one wave. The pause
        here is 25 minutes, which is the shortest gap between two observed `fix-batch` bursts
        on this maintainer's machine."""
        self.wave_fixture()
        self.dispatched("a4", "toolu_4", "2026-08-01T10:25:44.000Z",
                        messages=[("2026-08-01T10:26:00.000Z", (2, 50, 1000, 30), ())])
        self.build()

        payload = self.report()

        self.assertEqual([wave["size"] for wave in payload["waves"]], [1, 3],
                         "the pause did not start a new wave, or it split the first one")
        self.assertEqual(payload["waves"][0]["members"][0]["agent_id"], "a4",
                         "waves are not ordered most recent first")

    def test_s004_the_gap_that_separates_two_waves_is_the_stated_one(self):
        """Pins the threshold to the constant rather than to a coincidence: one second under
        it groups and one second over it separates, at the exact declared value."""
        gap = serve.WAVE_GAP_SECONDS
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.build()

        together = self.report(gap_seconds=gap)
        self.assertEqual(len(together["waves"]), 1)
        self.assertEqual(together["wave_gap_seconds"], gap)

        # Second dispatch exactly one second beyond the declared gap.
        self.dispatched("a2", "toolu_2", "2026-08-01T10:05:01.000Z", messages=[])
        self.build()

        self.assertEqual(len(self.report(gap_seconds=gap)["waves"]), 2,
                         f"a dispatch {gap + 1:g}s later was folded into the same wave")
        self.assertEqual(len(self.report(gap_seconds=gap + 2)["waves"]), 1,
                         "the gap is not the parameter the grouping actually uses")

    def test_s004_two_sessions_dispatching_at_the_same_moment_are_two_waves(self):
        """A wave belongs to the session that dispatched it. Time proximity alone would merge
        two unrelated projects' batches into one unit of work that never existed."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", sid="s1", messages=[])
        self.dispatched("b1", "toolu_2", "2026-08-01T10:00:02.000Z", sid="s2", messages=[])
        self.build()

        payload = self.report()

        self.assertEqual(len(payload["waves"]), 2)
        self.assertEqual({wave["session_id"] for wave in payload["waves"]}, {"s1", "s2"})

    def test_s004_every_dispatched_agent_belongs_to_exactly_one_wave(self):
        """The arithmetic that makes the grouping trustworthy rather than merely present: the
        wave sizes add up to the runs. A dropped or duplicated member breaks this while every
        panel still renders, which is the failure class `S-018` is written around.

        One member is deliberately not worktree-isolated. `S-004`'s Given names isolated
        workspaces, and a grouping that quietly kept only those would satisfy every other
        assertion here while losing 200 of this maintainer's 278 runs.
        """
        self.wave_fixture()
        self.dispatched("a4", "toolu_4", "2026-08-01T11:00:00.000Z", sid="s2", messages=[])
        self.dispatched("a5", "toolu_5", "2026-08-01T12:00:00.000Z", worktree=False,
                        messages=[])
        self.build()

        payload = self.report()
        conn = db.connect(self.store)
        try:
            stored = conn.execute("SELECT COUNT(*) FROM agent_run").fetchone()[0]
        finally:
            conn.close()

        # Against the store, not against the report's own list. Counting the runs from the
        # waves would make this identity true by construction: a grouping that dropped a member
        # would drop it from both sides and the arithmetic would still balance. Found by
        # mutation, after an earlier version did exactly that.
        self.assertEqual(stored, 5)
        self.assertEqual(payload["totals"]["runs"], stored)
        self.assertEqual(len(payload["runs"]), stored)
        self.assertEqual(sum(wave["size"] for wave in payload["waves"]),
                         payload["totals"]["runs"])
        self.assertEqual(
            sorted(m["agent_id"] for wave in payload["waves"] for m in wave["members"]),
            sorted(run["agent_id"] for run in payload["runs"]))
        # And in the same order, because the two are rendered as two tables on one page and a
        # reader moving between them is following a row, not a set.
        self.assertEqual(
            [run["agent_id"] for run in payload["runs"]],
            [m["agent_id"] for wave in payload["waves"] for m in wave["members"]],
            "the run list is not the wave list read straight through")

    def test_s004_a_run_with_no_start_time_becomes_its_own_wave(self):
        """A run nothing can place in time must not be attached to whichever neighbour it
        happened to sort next to. It is reported, and it is reported alone."""
        self.wave_fixture()
        # A sidecar with no dispatch record and no messages: nothing gives it a time.
        self.sidecar("a9", worktree=False, tool_use_id="toolu_9")
        self.append([self.result("r-a9", "toolu_9", "a9", ts="2026-08-01T10:00:30.000Z")])
        self.build()

        payload = self.report()
        placed = {m["agent_id"] for wave in payload["waves"] if wave["size"] > 1
                  for m in wave["members"]}

        self.assertNotIn("a9", placed, "a run with no start time joined a wave in time")
        self.assertIsNone(self.run_of(payload, "a9")["started"])
        self.assertEqual(payload["totals"]["runs"], 4)

    def test_s004_a_nested_dispatch_keeps_the_depth_the_harness_recorded(self):
        """An agent can dispatch an agent. The report flattens, which is a choice, so the depth
        has to survive the flattening or the choice has silently become a loss."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z", spawn_depth=2,
                        messages=[])
        self.build()

        payload = self.report()
        wave = payload["waves"][0]

        self.assertEqual(self.run_of(payload, "a2")["spawn_depth"], 2)
        self.assertEqual(wave["max_depth"], 2)
        self.assertEqual(wave["nested"], 1)
        self.assertEqual(payload["totals"]["nested_runs"], 1)
        self.assertEqual(payload["totals"]["max_depth"], 2)

    def test_s004_the_rule_that_decides_a_wave_reaches_the_report_surface(self):
        """The acceptance criterion in its own words: the rule is stated in the report, not
        only in the code. Both halves are asserted, the payload and the page, because a rule
        the server carries and the page drops has not reached a reader."""
        self.wave_fixture()

        payload = self.report()

        self.assertEqual(payload["wave_rule"], serve.WAVE_RULE)
        self.assertEqual(payload["wave_rule_bound"], serve.WAVE_RULE_BOUND)
        self.assertIn(f"{serve.WAVE_GAP_SECONDS:g} seconds", payload["wave_rule"],
                      "the stated rule does not carry the gap it actually uses")
        page = UI_INDEX.read_text(encoding="utf-8")
        # The whole rendering expression, not the bare field name. `data.wave_rule` is a
        # prefix of `data.wave_rule_bound`, so asserting the substring passed with the rule
        # itself deleted: found by mutation, which is the only thing that finds an assertion
        # another line already satisfies.
        for field in ("data.wave_rule", "data.wave_rule_bound", "data.nesting_policy",
                      "data.outcome_policy"):
            with self.subTest(field=field):
                self.assertIn(f"text: {field} }}", page,
                              f"the page never renders {field}, so the rule and its bound "
                              f"stay in the code where no reader sees them")

    def test_s004_each_members_bar_places_its_own_span_inside_the_waves(self):
        """The timeline's arithmetic, computed on the server because the page's script has no
        execution coverage here. Three members over a 420-second wave: the first starts at
        the wave's start, the second 20 seconds in, the third 44."""
        self.wave_fixture()

        wave = self.report()["waves"][0]

        self.assertEqual(wave["span_ms"], 420000)
        offsets = [round(member["bar"]["offset"], 4) for member in wave["members"]]
        widths = [round(member["bar"]["width"], 4) for member in wave["members"]]
        self.assertEqual(offsets, [0.0, round(20 / 420, 4), round(44 / 420, 4)])
        self.assertEqual(widths, [round(300 / 420, 4), round(340 / 420, 4),
                                  round(376 / 420, 4)])
        for member in wave["members"]:
            with self.subTest(member=member["agent_id"]):
                self.assertLessEqual(member["bar"]["offset"] + member["bar"]["width"], 1.0,
                                     "a member's bar runs past the end of its own wave")

    def test_s004_a_run_whose_last_message_predates_its_dispatch_gets_no_backwards_bar(self):
        """The one comparison in the timeline arithmetic that an input can actually reach.

        A run's start is its dispatch record and its end is its last message, and nothing
        guarantees the second is later: a replayed or clock-skewed transcript puts them the
        other way round, and the difference is then negative. It becomes a zero-width mark, not
        a bar drawn backwards from a position it never occupied.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:04:00.000Z", (2, 50, 1000, 30), ())])
        # Dispatched at 10:05, with its only message stamped a minute before that.
        self.dispatched("a2", "toolu_2", "2026-08-01T10:05:00.000Z",
                        messages=[("2026-08-01T10:04:00.000Z", (2, 50, 1000, 30), ())])
        self.build()

        wave = self.report()["waves"][0]
        late = [m for m in wave["members"] if m["agent_id"] == "a2"][0]

        self.assertLess(late["ended"], late["started"],
                        "the fixture no longer produces the negative span it exists for")
        self.assertEqual(late["bar"]["width"], 0.0)
        self.assertEqual(late["bar"]["offset"], 1.0)
        self.assertEqual(wave["ended"], "2026-08-01T10:05:00.000Z",
                         "the wave's window no longer reaches its last dispatch, so a member "
                         "can be placed outside the timeline it is drawn in")

    def test_s004_no_members_bar_falls_outside_its_own_wave(self):
        """The invariant that replaced a clamp. `_bar` does no clamping, because the wave's
        window is built to contain every member, so a bar cannot leave it. That is a property
        to assert rather than a branch to write, and it is asserted over the awkward shapes
        rather than the tidy one: a member with no messages at all, one dispatched after every
        other member had finished, and one whose last message predates its own dispatch.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:02:00.000Z", (2, 50, 1000, 30), ())])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:03:00.000Z", messages=[])
        self.dispatched("a3", "toolu_3", "2026-08-01T10:04:00.000Z",
                        messages=[("2026-08-01T10:01:00.000Z", (2, 50, 1000, 30), ())])
        self.build()

        wave = self.report()["waves"][0]

        self.assertEqual(wave["size"], 3)
        for member in wave["members"]:
            with self.subTest(member=member["agent_id"]):
                bar = member["bar"]
                self.assertGreaterEqual(bar["offset"], 0.0)
                self.assertLessEqual(bar["offset"] + bar["width"], 1.0,
                                     "a member's bar falls outside its own wave's window")

    def test_s004_a_wave_with_no_span_gives_every_member_the_full_width(self):
        """The degenerate input, constructed rather than waited for: a wave of one dispatch
        with no messages has no span, and dividing by it would be the page's first crash."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.build()

        wave = self.report()["waves"][0]

        self.assertEqual(wave["span_ms"], 0)
        self.assertEqual(wave["members"][0]["bar"], {"offset": 0.0, "width": 1.0})

    def test_s004_a_wave_totals_only_the_figures_it_actually_has(self):
        """A wave holding one measured member and one unmeasured one reports the sum it can
        make and says how many it made it from, rather than presenting a half-total as whole."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z",
                        messages=[("2026-08-01T10:00:05.000Z", (100, 100, 500, 300), ("t1",))])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z", messages=[])
        self.build()

        wave = self.report()["waves"][0]

        self.assertEqual(wave["size"], 2)
        self.assertEqual(wave["tokens"], 1000)
        self.assertEqual(wave["tokens_known"], 1)
        self.assertEqual(wave["tool_calls"], 1)
        self.assertEqual(wave["tool_calls_known"], 1)

    def test_s004_one_derived_member_makes_the_whole_waves_total_derived(self):
        """Exactness does not survive addition, and the sum has to say so.

        The wave here is deliberately mixed: one member the harness reported in full, one
        known only from its own messages. Reporting the total as `reported` would let the
        exact member launder the approximate one, and the reader is shown a sum that claims
        a precision no member of it has. The all-reported case is asserted beside it, because
        a rule that answered `derived` unconditionally would satisfy the first assertion.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        completion=(1000, 2000, 7),
                        messages=[("2026-08-01T10:00:05.000Z", (10, 20, 30, 40), ("t1",))])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z",
                        messages=[("2026-08-01T10:00:25.000Z", (100, 100, 500, 300), ("t2",))])
        self.build()

        wave = self.report()["waves"][0]
        self.assertEqual(wave["size"], 2)
        self.assertEqual(wave["tokens_known"], 2, "both members carry a token figure")
        self.assertEqual(wave["tokens_basis"], "derived",
                         "a wave holding one derived member reports its total as reported, "
                         "so the page renders it as an exact figure that it is not")
        self.assertEqual(wave["tool_calls_basis"], "derived")

    def test_s004_a_wave_whose_members_were_all_reported_is_not_marked_derived(self):
        """The other half of the rule. Marking every total derived would be safe and wrong:
        it spends the marker's meaning, and a reader who sees a tilde on everything stops
        reading it as anything."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        completion=(1000, 2000, 7), messages=[])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z", status="completed",
                        completion=(500, 500, 3), messages=[])
        self.build()

        wave = self.report()["waves"][0]
        self.assertEqual(wave["tokens_basis"], "reported")
        self.assertEqual(wave["tool_calls_basis"], "reported")
        self.assertEqual(wave["tool_calls"], 10, "the sum is still the sum")
        # The span is the exception, and it is asserted here rather than beside the sums
        # because it does not follow them. A wave's end time is only ever a member's last
        # message, so the span is derived even when every figure around it was reported by
        # the harness. Left unpinned, flipping it to `reported` renders every wave span on
        # the page as a bare exact-looking figure, which is the whole thing the tilde is for.
        self.assertEqual(wave["span_basis"], "derived",
                         "a wave span was reported as exact, and no member's end time is "
                         "ever a harness figure, so it cannot be")

    def test_s004_a_wave_with_no_token_figure_at_all_reports_an_unknown_basis(self):
        """`unknown` is the third answer, and it is not `derived` over an empty set: a sum of
        nothing marked derived would render as `0 ~`, a measured-looking zero."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.build()

        wave = self.report()["waves"][0]
        self.assertIsNone(wave["tokens"])
        self.assertEqual(wave["tokens_basis"], "unknown")


class TestWavesAcrossProjects(WavesTestCase):
    """The scope selector over this report. Not a scenario this task claims, and asserted
    anyway because the shell offers the selector on every tab and a report that ignored it
    would look scoped and be wrong."""

    def test_the_scoped_report_partitions_the_runs(self):
        """Three runs across two projects, deliberately unevenly. An even split would be
        satisfied by a scoped report that truncated to one row per project, which is the
        mutation this exact shape exists to kill.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.dispatched("a2", "toolu_2", "2026-08-01T10:00:20.000Z", messages=[])
        other = self.corpus / "D--other"
        other.mkdir(parents=True)
        self.project, keep = other, self.project
        self.dispatched("b1", "toolu_3", "2026-08-01T10:00:00.000Z", sid="s2", messages=[])
        self.project = keep
        self.build()

        everywhere = self.report()
        here = self.report(project="D--demo")
        there = self.report(project="D--other")

        self.assertEqual(everywhere["totals"]["runs"], 3)
        self.assertEqual(here["totals"]["runs"] + there["totals"]["runs"],
                         everywhere["totals"]["runs"])
        self.assertEqual([run["agent_id"] for run in here["runs"]], ["a1", "a2"])
        self.assertEqual([run["agent_id"] for run in there["runs"]], ["b1"])
        self.assertEqual(here["project"], "D--demo")


class TestNoTranscriptBodyIsRead(WavesTestCase):
    """The task's scope boundary, made mechanical.

    The contract's Non-Goals exclude reconstructing conversation content, and this report is
    counts, durations and outcomes only. The fixture plants two distinctive strings, in the
    dispatch prompt and in the result content, and the assertion is that neither reaches the
    payload at all.
    """

    def test_no_prompt_or_result_body_reaches_the_report(self):
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", status="completed",
                        completion=(122287, 378560, 24),
                        messages=[("2026-08-01T10:00:05.000Z", (2, 50, 1000, 30), ("t1",))])
        self.build()

        serialised = json.dumps(self.report())

        self.assertNotIn("PROMPT-BODY-THAT-MUST-NOT-BE-REPORTED", serialised)
        self.assertNotIn("RESULT-BODY-THAT-MUST-NOT-BE-REPORTED", serialised)

    def test_the_store_holds_no_column_a_transcript_body_could_arrive_in(self):
        """The stronger half, and the reason the assertion above can stay short: the report
        cannot leak a body it has no column to read one from. Asserted over the two tables
        this report selects from, so a column added later that could carry prose fails here
        rather than being noticed in review."""
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z", messages=[])
        self.build()
        conn = db.connect(self.store)
        try:
            columns = {table: {row["name"] for row in
                               conn.execute(f"PRAGMA table_info({table})")}
                       for table in ("agent_run", "message")}
        finally:
            conn.close()

        for table, forbidden in (("agent_run", {"prompt", "content", "output", "text"}),
                                 ("message", {"content", "text", "body", "prompt"})):
            with self.subTest(table=table):
                self.assertEqual(columns[table] & forbidden, set(),
                                 f"{table} gained a column that can hold conversation "
                                 f"content, which this report would then be able to read")


class TestWavesPage(WavesTestCase):
    """Structural assertions over the page's source, carrying the bound `feat-0054` stated:
    the standard library has no JavaScript engine and this repository ships no dependency to
    add one, so these pin specific regressions rather than the page's behaviour."""

    def renderer_body(self) -> str:
        """The body of `RENDERERS.waves`, from its key to the end of the registry."""
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("  waves: function (data, into) {")
        return html[start:html.index("\n};", start)]

    def test_the_waves_report_is_built_and_owed_by_nobody(self):
        entry = [report for report in serve.REPORTS if report["id"] == "waves"][0]
        self.assertEqual(entry["endpoint"], "/api/waves")
        self.assertIsNone(entry["owner"])
        self.assertEqual(entry["scenarios"], ["S-003", "S-004"])

    def test_the_waves_renderer_maps_every_returned_row_without_filtering(self):
        """Kills the mutation that drops rows at the surface while the API still returns them,
        which no API-level test can see. An independent verification of `feat-0054` showed the
        skills renderer could drop every zero-count row with the whole suite green."""
        body = self.renderer_body()
        for collection in ("data.waves", "data.runs", "data.projects"):
            with self.subTest(collection=collection):
                self.assertIn(collection + ".map(", body,
                              f"the renderer no longer maps the {collection} the API returned")
                for hostile in (".filter(", ".slice(", ".splice("):
                    self.assertNotIn(
                        collection + hostile, body,
                        f"the renderer applies {hostile} to {collection}, so a run the report "
                        f"counted can be missing from the page")

    def test_the_waves_renderer_builds_no_interactive_element_of_its_own(self):
        """`S-019`'s enumeration is derived from one tagged construction site. This report
        renders per-run rows, which is exactly where an untagged control would appear, and the
        widened guard in `test_observatory_serve.py` names this renderer as a reason it was
        widened. Asserted here too, at the renderer rather than over the whole script, so a
        failure says which report grew the control."""
        body = self.renderer_body()
        for forbidden in ('el("a"', 'el("button"', 'el("form"', 'el("input"',
                          'el("select"', "addEventListener", "location.href",
                          "window.open", "fetch("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body,
                                 f"the waves renderer builds {forbidden}, which is outside "
                                 f"the enumeration S-019 is proven by")

    def test_the_renderer_shows_the_basis_beside_every_derived_figure(self):
        """A derived figure rendered as a bare number is the defect this report is most likely
        to ship: it reads as exact and is not. The page marks it, and `withBasis` is the only
        place that decision is made."""
        body = self.renderer_body()
        for field in ("run.duration_basis", "run.tokens_basis", "run.tool_calls_basis",
                      "wave.tokens_basis", "wave.tool_calls_basis", "wave.span_basis"):
            with self.subTest(field=field):
                self.assertIn(field, body,
                              f"the page renders a figure without {field}, so a derived "
                              f"figure and a reported one look identical")

    def test_both_legends_reach_the_payload_with_every_entry_they_declare(self):
        """The two legends are the only place the page says what `launched` and `~` mean.

        Emptied, every table still renders and every figure still looks fine, so nothing else
        in the suite notices: the reader simply loses the sentence that told them an absence
        is not a failure. Asserted against the declarations rather than against a copy, so a
        fifth outcome added upstream is carried here without this test being edited.
        """
        self.dispatched("a1", "toolu_1", "2026-08-01T10:00:00.000Z")
        self.build()
        data = self.report()
        self.assertEqual(data["outcomes_legend"], list(serve.RUN_OUTCOMES),
                         "the outcome legend does not carry every declared outcome, so the "
                         "page explains fewer outcomes than its rows can show")
        self.assertEqual(data["bases_legend"], list(serve.FIGURE_BASES),
                         "the basis legend does not carry every declared basis, so a marked "
                         "figure has no key a reader can look it up in")
        legend = self.renderer_body()
        legend = legend[legend.index("What each outcome means"):]
        self.assertIn("entry.label", legend,
                      "the outcome legend renders only the terse id, so the wordings the "
                      "documentation uses for these outcomes reach no reader and a row's "
                      "tag has to be matched to its explanation by guessing")
        for entry in data["outcomes_legend"]:
            with self.subTest(outcome=entry["id"]):
                self.assertTrue(entry["label"].strip(),
                                f"outcome {entry['id']} reaches the page with no wording, so "
                                f"its legend row renders blank")
                self.assertTrue(entry["meaning"].strip())

    def test_the_marker_function_actually_distinguishes_the_two_bases(self):
        """Passing a basis to `withBasis` proves nothing if `withBasis` ignores it.

        The test above asserts every call site hands over its basis, which a body of
        `return text;` satisfies completely while rendering every derived figure as a bare
        number: the exact defect the call sites exist to prevent. So this asserts the
        decision itself, on the function rather than on its callers.
        """
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("function withBasis(")
        body = html[start:html.index("\n}", start)]
        self.assertIn('"reported"', body,
                      "`withBasis` never names the reported basis, so it cannot be telling "
                      "the two apart whatever its call sites pass in")
        self.assertIn('"unknown"', body,
                      "`withBasis` never names the unknown basis, so an unmeasured figure "
                      "renders as a number with a tilde rather than as unknown")
        self.assertIn('" ~"', body,
                      "`withBasis` emits no marker, so a derived figure and a reported one "
                      "render identically")

    def test_a_wave_total_assembled_from_some_of_its_members_says_so(self):
        """A sum over three of five members is not the wave's cost, and rendered bare it is
        indistinguishable from one that is."""
        body = self.renderer_body()
        for field in ("wave.tokens_known", "wave.tool_calls_known"):
            with self.subTest(field=field):
                self.assertIn(field, body,
                              f"the wave table renders a total without {field}, so a partial "
                              f"total reads as the whole wave's figure")
        html = UI_INDEX.read_text(encoding="utf-8")
        start = html.index("function waveTotal(")
        helper = html[start:html.index("\n}", start)]
        self.assertIn("of", helper,
                      "`waveTotal` renders no count, so the partiality it is passed is "
                      "discarded before a reader sees it")
        self.assertIn("withBasis(", helper,
                      "`waveTotal` does not defer to `withBasis`, so the wave tables and the "
                      "run tables can disagree about how a derived figure is marked")


class TestDegenerateInputs(WavesTestCase):
    """The empty and near-empty cases, constructed rather than waited for, per the conventions
    section of `AGENTS.md`: a check that cannot fail is unchecked, whatever it printed."""

    def test_a_corpus_with_no_dispatches_reports_no_waves_rather_than_failing(self):
        self.append([self._shell("assistant", "u1", "s1", "2026-08-01T10:00:00.000Z",
                                 message={"model": "claude-opus-5", "content": [],
                                          "usage": {}})])
        self.build()

        payload = self.report()

        self.assertEqual(payload["waves"], [])
        self.assertEqual(payload["runs"], [])
        self.assertEqual(payload["totals"]["runs"], 0)
        self.assertIsNone(payload["totals"]["tokens"])
        self.assertEqual(payload["wave_rule"], serve.WAVE_RULE)

    def test_a_missing_store_is_stated_rather_than_reported_as_an_empty_corpus(self):
        """"The ingester has not run" and "nothing was dispatched" are different answers, and
        the surface must not merge them. Routed through the handler's own helper, which is
        what the page actually reaches."""
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0, quiet=True,
                                   registry=self.registry, corpus=self.corpus)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)

        connection = http.client.HTTPConnection(*server.server_address[:2], timeout=10)
        try:
            connection.request("GET", "/api/waves")
            payload = json.loads(connection.getresponse().read().decode("utf-8"))
        finally:
            connection.close()

        self.assertFalse(payload["store_present"])
        self.assertIn("ingest.py", payload["message"])
        self.assertFalse(self.store.exists(),
                         "answering a GET created a store as a side effect")

    def test_the_calibration_the_gap_rests_on_is_recorded_beside_it(self):
        """The threshold is a judgement made from measurements, and a number with no recorded
        basis is a number the next reader has to re-derive or trust. `chore-0033` is the
        precedent: state the arithmetic, not the claim."""
        source = (REPO_ROOT / "scripts" / "observatory" / "serve.py").read_text(
            encoding="utf-8")
        window = source[source.index("WAVE_GAP_SECONDS = "):]
        preamble = source[:source.index("WAVE_GAP_SECONDS = ")]
        calibration = preamble[preamble.rindex("\n#", 0, len(preamble) - 1) - 900:]

        self.assertTrue(re.search(r"\b53\.3\b", calibration),
                        "the measured gap distribution the threshold rests on is no longer "
                        "recorded next to it")
        self.assertTrue(re.search(r"\b1,?524\.7\b", calibration),
                        "the valley the threshold sits in is no longer recorded")
        self.assertEqual(serve.WAVE_GAP_SECONDS, 300.0)
        self.assertIn("WAVE_RULE_BOUND", window,
                      "the rule's bound no longer travels with the rule")


if __name__ == "__main__":
    unittest.main()
