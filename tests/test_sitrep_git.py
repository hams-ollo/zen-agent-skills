"""Acceptance tests for in-flight work and changes, read from git (feat-0067).

Derived from `docs/spec/sitrep.md`, scenarios S-008, S-009, S-011 and S-039, with S-010 run again
now that a board without task tracking has in-flight work to carry. Each test names the scenario
it proves in its docstring.

test-quality notes: every scenario here is a fact about git state, so each runs against a real
throwaway repository with real worktrees, branches, and a local bare remote. A fake of
`git worktree list` would prove only that the parser reads the fake.

The defect each group protects against:
  worktrees   - uncommitted work reads as nothing in progress, the prototype's failure (S-008)
  branches    - unmerged or unpushed work is invisible (S-009)
  integration - the board compares against the wrong branch and says nothing (S-009, S-039)
  changes     - a closed task reads as updated, or an update as nothing (S-011)
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

_spec = importlib.util.spec_from_file_location("sitrep_git_under_test", SCRIPT)
sitrep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sitrep)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "sitrep test", "GIT_AUTHOR_EMAIL": "sitrep@example.invalid",
    "GIT_COMMITTER_NAME": "sitrep test", "GIT_COMMITTER_EMAIL": "sitrep@example.invalid",
}


def run_git(cwd, *args):
    env = dict(os.environ)
    env.update(GIT_IDENTITY)
    proc = subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, check=True, capture_output=True, text=True, env=env)
    return proc.stdout.strip()


def _writable_then_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def scratch_dir(test, prefix):
    path = Path(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, path, onerror=_writable_then_retry)
    return path


class ThrowawayRepo:
    def __init__(self, test, branch="main"):
        self.dir = scratch_dir(test, "sitrep-git-")
        run_git(self.dir, "init", "-q", "-b", branch)

    def write(self, rel, text):
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message="commit"):
        run_git(self.dir, "add", "-A")
        run_git(self.dir, "commit", "-q", "--allow-empty", "-m", message)
        return run_git(self.dir, "rev-parse", "HEAD")


def task_text(task_id, extra=""):
    return (f"---\nid: {task_id}\ntitle: Task {task_id}\ntype: feat\nstatus: open\npriority: P2\n"
            f"parent: \"a goal\"\ndepends_on: []\ncreated: 2026-09-11\n---\n\n## Problem\n\nX.\n{extra}")


class WorktreeTests(unittest.TestCase):

    def test_s008_uncommitted_work_in_a_worktree_is_in_flight(self):
        """S-008: a worktree with uncommitted changes is in flight, with its branch and count.

        No task file says `in_progress`, which is the state every repository of the author's was
        in when the prototype reported nothing in progress.
        """
        repo = ThrowawayRepo(self)
        repo.write(".tasks/feat-0001-a.md", task_text("feat-0001"))
        repo.commit()
        target = scratch_dir(self, "sitrep-wt-") / "feature"
        run_git(repo.dir, "worktree", "add", "-q", str(target), "-b", "feature")
        (target / "new.txt").write_text("unadded work\n", encoding="utf-8")
        (target / ".tasks" / "feat-0001-a.md").write_text(task_text("feat-0001", "edited\n"),
                                                          encoding="utf-8")

        board = sitrep.build_board(repo.dir)
        worktrees = [e for e in board["in_flight"] if e["kind"] == "worktree"]
        self.assertEqual(len(worktrees), 1, board["in_flight"])
        self.assertEqual(Path(worktrees[0]["name"]).resolve(), target.resolve())
        self.assertEqual(worktrees[0]["branch"], "feature")
        self.assertEqual(worktrees[0]["changed_paths"], 2)
        self.assertEqual(worktrees[0]["tier"], "purple")

    def test_s008_a_clean_worktree_is_not_in_flight(self):
        """S-008: a worktree with nothing uncommitted is not listed."""
        repo = ThrowawayRepo(self)
        repo.write("a.txt", "a\n")
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertEqual([e for e in board["in_flight"] if e["kind"] == "worktree"], [])


class BranchTests(unittest.TestCase):

    def test_s009_a_branch_with_unmerged_commits_is_in_flight(self):
        """S-009: a branch holding commits `main` lacks is listed, with how many; a merged one is not."""
        repo = ThrowawayRepo(self)
        repo.write("a.txt", "a\n")
        repo.commit()
        run_git(repo.dir, "branch", "merged")
        run_git(repo.dir, "switch", "-q", "-c", "feature")
        repo.write("b.txt", "b\n")
        repo.commit("feature work")
        run_git(repo.dir, "switch", "-q", "main")

        board = sitrep.build_board(repo.dir)
        branches = [(e["name"], e["unmerged_commits"]) for e in board["in_flight"]
                    if e["kind"] == "branch"]
        self.assertEqual(branches, [("feature", 1)])

    def test_s009_the_default_branch_of_origin_is_the_integration_branch(self):
        """S-009, the surface's default: with no declaration, `origin`'s default branch wins."""
        repo = ThrowawayRepo(self)
        repo.write("a.txt", "a\n")
        repo.commit()
        remote = scratch_dir(self, "sitrep-remote-") / "origin.git"
        run_git(remote.parent, "init", "-q", "--bare", "-b", "main", str(remote))
        run_git(repo.dir, "remote", "add", "origin", str(remote))
        run_git(repo.dir, "push", "-q", "origin", "main")
        run_git(repo.dir, "remote", "set-head", "origin", "main")
        repo.write("local.txt", "not pushed\n")
        repo.commit("unpushed")

        self.assertEqual(sitrep.resolve_integration(repo.dir), ("origin/main", None))
        board = sitrep.build_board(repo.dir)
        self.assertEqual([(e["name"], e["unmerged_commits"]) for e in board["in_flight"]
                          if e["kind"] == "branch"], [("main", 1)])

    def test_s009_a_declared_branch_that_does_not_exist_is_reported(self):
        """S-009's surface: a declared integration branch that does not resolve is named, not replaced."""
        repo = ThrowawayRepo(self)
        repo.write("a.txt", "a\n")
        repo.commit()
        self.assertEqual(sitrep.resolve_integration(repo.dir, "developer"),
                         (None, "integration branch not found: developer"))


class NoIntegrationBranchTests(unittest.TestCase):

    def test_s039_a_repository_with_no_integration_branch_reports_no_branches_and_says_so(self):
        """S-039: no declaration, no `origin`, no `main`: no branches, worktrees still, and the notice."""
        repo = ThrowawayRepo(self, branch="trunk")
        repo.write("a.txt", "a\n")
        repo.commit()
        run_git(repo.dir, "switch", "-q", "-c", "feature")
        repo.write("b.txt", "b\n")
        repo.commit()
        repo.write("dirty.txt", "uncommitted\n")

        board = sitrep.build_board(repo.dir)
        self.assertIn("no integration branch", board["notices"])
        self.assertEqual([e for e in board["in_flight"] if e["kind"] == "branch"], [])
        self.assertEqual([e["kind"] for e in board["in_flight"]], ["worktree"])


class ChangedSinceTests(unittest.TestCase):

    def test_s011_changes_since_a_revision_are_summarised(self):
        """S-011: the commit count, the task moved into `done/` as closed, the one edited as updated."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/feat-0001-to-close.md", task_text("feat-0001"))
        repo.write(".tasks/feat-0002-to-edit.md", task_text("feat-0002"))
        base = repo.commit("base")
        (repo.dir / ".tasks" / "done").mkdir()
        run_git(repo.dir, "mv", ".tasks/feat-0001-to-close.md", ".tasks/done/feat-0001-to-close.md")
        repo.write(".tasks/feat-0002-to-edit.md", task_text("feat-0002", "\nMore detail.\n"))
        repo.commit("close one, edit one")
        repo.write("notes.txt", "unrelated\n")
        repo.commit("unrelated")

        board = sitrep.build_board(repo.dir, base=base)
        self.assertEqual(board["changed"],
                         {"commits": 2, "closed": ["feat-0001"], "updated": ["feat-0002"]})


class NoTrackingWithWorkInFlightTests(unittest.TestCase):

    def test_s010_a_board_without_task_tracking_carries_its_work_in_flight(self):
        """S-010 again: with no `.tasks/`, uncommitted work still appears in flight."""
        repo = ThrowawayRepo(self)
        repo.write("README.md", "# no task files\n")
        repo.commit()
        repo.write("draft.md", "work in progress\n")

        board = sitrep.build_board(repo.dir)
        self.assertIn("no task tracking", board["notices"])
        self.assertEqual([e["kind"] for e in board["in_flight"]], ["worktree"])
        self.assertEqual((board["waiting"], board["blocked"]), ([], []))


if __name__ == "__main__":
    unittest.main()
