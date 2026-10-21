"""Acceptance tests for the sitrep board's core (feat-0066).

Derived from `docs/spec/sitrep.md`, scenarios S-001 to S-007, S-010 and S-014. Each test names the
scenario it proves in its docstring, so `spec-conformance` can map a row to its evidence.

test-quality notes: the heading and ordering rules are unit tests over task text, calling
`waiting_reasons()` and `classify()` directly, because those rules are pure. The scenarios whose
outcome depends on a repository fact (closed, tracked, dependency state) run against a throwaway
git repository, because that fact is invisible to an in-process call that never has a repository
of its own. That is the split the readiness record set.

Oracles assert the exact list, the exact reason, and the exact order, never "is non-empty":
a board that drops the only P1 from the queue still produces a non-empty queue, which is exactly
what the prototype this replaces did.

The defect each group protects against:
  waiting   - a question answered only above it clears the queue (S-001 to S-004)
  closed    - a finished task keeps nagging the person (S-005)
  order     - the P1 is buried below P2 work (S-006)
  blocked   - a task is dispatched before what it needs is done (S-007)
  untracked - one machine's scratch file reads as repository state (S-010, S-014, Goal 1)
"""
import importlib.util
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".agents" / "skills" / "sitrep" / "scripts" / "sitrep.py"

_spec = importlib.util.spec_from_file_location("sitrep_board_under_test", SCRIPT)
sitrep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sitrep)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "sitrep test", "GIT_AUTHOR_EMAIL": "sitrep@example.invalid",
    "GIT_COMMITTER_NAME": "sitrep test", "GIT_COMMITTER_EMAIL": "sitrep@example.invalid",
}


def run_git(cwd, *args):
    env = dict(os.environ)
    env.update(GIT_IDENTITY)
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, env=env,
    )


def _writable_then_retry(func, path, _exc):
    """Windows marks git's object files read-only, which a plain rmtree cannot delete."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class ThrowawayRepo:
    """A real git repository in a temporary directory, removed when the test ends."""

    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp(prefix="sitrep-"))
        test.addCleanup(shutil.rmtree, self.dir, onerror=_writable_then_retry)
        run_git(self.dir, "init", "-q")

    def write(self, rel, text):
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message="commit"):
        run_git(self.dir, "add", "-A")
        run_git(self.dir, "commit", "-q", "--allow-empty", "-m", message)


def task_text(task_id, *, priority="P2", depends=(), body=""):
    """A task file in the shape `init-worktracking` scaffolds."""
    return (
        "---\n"
        f"id: {task_id}\n"
        f"title: Task {task_id}\n"
        "type: feat\n"
        "status: open\n"
        f"priority: {priority}\n"
        'parent: "a goal"\n'
        f"depends_on: [{', '.join(depends)}]\n"
        "touched_files:\n"
        "  - somewhere\n"
        "created: 2026-09-11\n"
        "---\n"
        "\n"
        "## Problem\n"
        "\n"
        "Something is missing.\n"
        f"{body}"
    )


QUESTION = "\n## Open question (founder decision)\n\nWhich way?\n"
DECISION = "\n## Decision (2026-09-11)\n\nThis way.\n"


class WaitingOnYouTests(unittest.TestCase):
    """What puts a task on the person's queue, and what takes it off."""

    def test_s001_an_open_question_with_no_decision_below_it_waits_on_the_person(self):
        """S-001: an open question with no decision below it waits on the person."""
        self.assertEqual(sitrep.waiting_reasons(QUESTION), ["open question"])

    def test_s001_a_level_three_heading_is_not_an_open_question(self):
        """S-001, the surface's precision: only a level-two heading counts."""
        self.assertEqual(sitrep.waiting_reasons("\n### Open question\n\nNot this one.\n"), [])

    def test_s001_the_heading_is_matched_in_any_letter_case(self):
        """S-001: a capitalised heading must not lose a row from the queue."""
        self.assertEqual(sitrep.waiting_reasons("\n## Open Question\n\nWhich?\n"), ["open question"])

    def test_s002_a_decision_above_a_newer_question_does_not_answer_it(self):
        """S-002: a decision above a newer question does not answer it.

        This is feat-0057's shape in hts-app, the case the prototype dropped from the queue.
        """
        self.assertEqual(sitrep.waiting_reasons(DECISION + QUESTION), ["open question"])

    def test_s002_the_last_question_decides_when_there_are_several(self):
        """S-002: question, decision, new question still waits, whatever came first."""
        self.assertEqual(sitrep.waiting_reasons(QUESTION + DECISION + QUESTION), ["open question"])

    def test_s003_a_decision_below_a_question_answers_it(self):
        """S-003: a decision below a question answers it."""
        self.assertEqual(sitrep.waiting_reasons(QUESTION + DECISION), [])

    def test_s003_one_decision_below_every_question_answers_them_all(self):
        """S-003: a decision below the last question answers every question above it."""
        self.assertEqual(sitrep.waiting_reasons(QUESTION + QUESTION + DECISION), [])

    def test_s004_work_held_for_a_human_eye_waits_on_the_person(self):
        """S-004: a heading carrying the phrase, at any level and in any case, waits."""
        for heading in ("## Landed 2026-09-10, and held open for a human eye",
                        "### HELD OPEN FOR A HUMAN EYE"):
            with self.subTest(heading=heading):
                self.assertEqual(sitrep.waiting_reasons(f"\n{heading}\n\nLook at it.\n"),
                                 ["needs a human eye"])

    def test_s004_the_phrase_in_prose_is_not_a_heading(self):
        """S-004: only a heading carries the marker, so prose that mentions it does not."""
        self.assertEqual(
            sitrep.waiting_reasons("\nThis was held open for a human eye last week.\n"), [])


class ClosedTaskTests(unittest.TestCase):

    def test_s005_a_closed_task_never_waits_on_the_person(self):
        """S-005: a task under `.tasks/done/` never waits, whatever its body says."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/done/feat-0001-finished.md", task_text("feat-0001", body=QUESTION))
        repo.write(".tasks/feat-0002-open.md", task_text("feat-0002", body=QUESTION))
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertEqual([e["id"] for e in board["waiting"]], ["feat-0002"])


class OrderTests(unittest.TestCase):

    def test_s006_waiting_entries_are_ordered_by_priority_then_id(self):
        """S-006: P1 first, then downward; the same priority in id order; none last."""
        tasks = [
            sitrep.parse_task(f".tasks/{tid}-x.md", task_text(tid, priority=p, body=QUESTION))
            for tid, p in (("feat-0003", "P2"), ("feat-0005", "P1"), ("feat-0001", "P3"),
                           ("feat-0002", "P2"), ("feat-0004", ""))
        ]
        waiting, _, _ = sitrep.classify(tasks)
        self.assertEqual([e["id"] for e in waiting],
                         ["feat-0005", "feat-0002", "feat-0003", "feat-0001", "feat-0004"])


class BlockedTests(unittest.TestCase):

    def test_s007_a_task_with_an_unfinished_dependency_is_blocked(self):
        """S-007: blocked lists the task and names each dependency that is not done."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/done/feat-0001-done.md", task_text("feat-0001"))
        repo.write(".tasks/feat-0002-needs-two.md",
                   task_text("feat-0002", depends=("feat-0001", "bug-0009")))
        repo.write(".tasks/bug-0009-open.md", task_text("bug-0009"))
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertEqual([(e["id"], e["waits_on"]) for e in board["blocked"]],
                         [("feat-0002", ["bug-0009"])])

    def test_s007_a_task_whose_dependencies_are_all_done_is_not_blocked(self):
        """S-007: once every dependency is under `.tasks/done/`, the task is not blocked."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/done/feat-0001-done.md", task_text("feat-0001"))
        repo.write(".tasks/feat-0002-ready.md", task_text("feat-0002", depends=("feat-0001",)))
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertEqual(board["blocked"], [])
        self.assertEqual([e["id"] for e in board["planned"]], ["feat-0002"])


class NoTrackingTests(unittest.TestCase):

    def test_s010_a_repository_without_task_tracking_still_gets_a_board(self):
        """S-010: no `.tasks/` gives a board with the notice and nothing waiting or blocked.

        Its in-flight and changed sections are present here and filled by `feat-0067`, whose
        tests run this scenario again against a repository with work in flight.
        """
        repo = ThrowawayRepo(self)
        repo.write("README.md", "# a project with no task files\n")
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertIn("no task tracking", board["notices"])
        self.assertEqual((board["waiting"], board["blocked"]), ([], []))
        self.assertIn("in_flight", board)
        self.assertIn("changed", board)


class ProvenanceTests(unittest.TestCase):

    def test_s014_a_task_entry_is_green_and_names_its_task_file(self):
        """S-014: every task on the board carries tier Green and names its file."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/feat-0001-waits.md", task_text("feat-0001", body=QUESTION))
        repo.write(".tasks/feat-0002-blocked.md", task_text("feat-0002", depends=("feat-0009",)))
        repo.write(".tasks/feat-0003-planned.md", task_text("feat-0003"))
        repo.commit()
        board = sitrep.build_board(repo.dir)
        entries = board["waiting"] + board["blocked"] + board["planned"]
        self.assertEqual(len(entries), 3)
        for entry in entries:
            with self.subTest(task=entry["id"]):
                self.assertEqual(entry["tier"], "green")
                self.assertEqual(entry["provenance"], entry["file"])
                self.assertTrue(entry["file"].startswith(".tasks/"))

    def test_an_untracked_task_file_is_not_state(self):
        """Goal 1, the tracked-records half: a task file git does not track is not read."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/feat-0001-tracked.md", task_text("feat-0001"))
        repo.commit()
        repo.write(".tasks/feat-0002-untracked.md", task_text("feat-0002", body=QUESTION))
        board = sitrep.build_board(repo.dir)
        self.assertEqual(board["waiting"], [])
        self.assertEqual([e["id"] for e in board["planned"]], ["feat-0001"])


if __name__ == "__main__":
    unittest.main()
