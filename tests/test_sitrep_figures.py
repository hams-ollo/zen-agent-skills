"""Acceptance tests for evidence tiers and declared figures (feat-0068).

Derived from `docs/spec/sitrep.md`, scenarios S-012, S-013 and S-015 to S-020. Each test names the
scenario it proves in its docstring.

test-quality notes: a tier is a claim about a repository fact (is this file held at the current
revision, does this test exist), so every scenario that assigns one runs against a real throwaway
repository. The lowest-tier rule (S-019) is arithmetic and is also tested directly on
`count_figure()`. Oracles assert the exact value, tier, and provenance together, because a figure
with the right number and the wrong tier is the precise failure this task exists to remove.

The defect each group protects against:
  tiers    - a number reads more solid than its source supports (S-012, S-013, S-015)
  pins     - Gold is claimed for a test that is not there (S-016, S-017)
  manual   - a hand-entered value hides who said so (S-018)
  counts   - a count of Green things reads as a Purple measurement (S-019)
  failures - a broken declaration invents a value instead of saying so (S-020)
"""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".agents" / "skills" / "sitrep" / "scripts" / "sitrep.py"

_spec = importlib.util.spec_from_file_location("sitrep_figures_under_test", SCRIPT)
sitrep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sitrep)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "sitrep test", "GIT_AUTHOR_EMAIL": "sitrep@example.invalid",
    "GIT_COMMITTER_NAME": "sitrep test", "GIT_COMMITTER_EMAIL": "sitrep@example.invalid",
}

BANK = {"items": [{"s": "approved", "released": True}, {"s": "approved", "released": False},
                  {"s": "rejected", "released": True}],
        "counts": {"skills": 78}}


def run_git(cwd, *args):
    env = dict(os.environ)
    env.update(GIT_IDENTITY)
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                   cwd=cwd, check=True, capture_output=True, env=env)


def _writable_then_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class ThrowawayRepo:
    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp(prefix="sitrep-fig-"))
        test.addCleanup(shutil.rmtree, self.dir, onerror=_writable_then_retry)
        run_git(self.dir, "init", "-q", "-b", "main")

    def write(self, rel, content):
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else json.dumps(content)
        path.write_text(text, encoding="utf-8")

    def configure(self, config):
        self.write(".sitrep.json", config)

    def commit(self, message="commit"):
        run_git(self.dir, "add", "-A")
        run_git(self.dir, "commit", "-q", "--allow-empty", "-m", message)


def figure(board, name):
    matches = [f for f in board["figures"] if f["name"] == name]
    return matches[0] if matches else None


COUNT = {"name": "approved", "file": "data/bank.json", "kind": "count", "select": "items[s=approved]"}
VALUE = {"name": "skills", "file": "data/bank.json", "kind": "value", "select": "counts.skills"}


class TierTests(unittest.TestCase):

    def test_s012_a_count_over_a_tracked_file_is_purple_and_read_at_the_current_revision(self):
        """S-012: the number of elements selected, at HEAD, tier Purple, naming the file.

        An uncommitted edit to the data file must not move it, because the tier says what the
        repository holds and one machine's edit is not that.
        """
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.configure({"figures": [COUNT]})
        repo.commit()
        repo.write("data/bank.json", {"items": []})
        got = figure(sitrep.build_board(repo.dir), "approved")
        self.assertEqual((got["value"], got["tier"], got["provenance"]), (2, "purple", "data/bank.json"))

    def test_s012_a_filter_matches_a_non_string_in_its_json_spelling(self):
        """S-012's `select` surface: `[released=true]` matches JSON `true`."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.configure({"figures": [dict(COUNT, name="released", select="items[released=true]")]})
        repo.commit()
        self.assertEqual(figure(sitrep.build_board(repo.dir), "released")["value"], 2)

    def test_s013_a_value_read_from_a_tracked_file_is_blue(self):
        """S-013: the value at the selection, tier Blue, naming the file."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.configure({"figures": [VALUE]})
        repo.commit()
        got = figure(sitrep.build_board(repo.dir), "skills")
        self.assertEqual((got["value"], got["tier"], got["provenance"]), (78, "blue", "data/bank.json"))

    def test_s015_anything_from_an_untracked_file_is_white_even_when_counted_and_pinned(self):
        """S-015: an untracked source is White and labelled, whatever it is declared as or pinned to."""
        repo = ThrowawayRepo(self)
        repo.write("tests/test_numbers.py", "def test_two_approved():\n    pass\n")
        repo.configure({"figures": [COUNT], "pins": [{"figure": "approved", "test": "test_two_approved"}]})
        repo.commit()
        repo.write("data/bank.json", BANK)
        got = figure(sitrep.build_board(repo.dir), "approved")
        self.assertEqual((got["value"], got["tier"], got["label"]), (2, "white", "untracked"))


class PinTests(unittest.TestCase):

    def test_s016_a_pinned_figure_whose_test_exists_is_gold(self):
        """S-016: a tracked figure pinned to a test a tracked test file contains is Gold, naming it."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.write("tests/test_numbers.py", "def test_two_approved():\n    assert True\n")
        repo.configure({"figures": [COUNT], "pins": [{"figure": "approved", "test": "test_two_approved"}]})
        repo.commit()
        got = figure(sitrep.build_board(repo.dir), "approved")
        self.assertEqual((got["tier"], got["pinned_by"]), ("gold", "test_two_approved"))

    def test_s017_a_pinned_figure_whose_test_is_missing_is_downgraded_and_reported(self):
        """S-017: no such test keeps the tier the source earns, and a notice names both."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.write("tests/test_numbers.py", "def test_something_else():\n    pass\n")
        repo.configure({"figures": [COUNT], "pins": [{"figure": "approved", "test": "test_gone"}]})
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertEqual(figure(board, "approved")["tier"], "purple")
        self.assertIn("pinned test not found: test_gone (figure approved)", board["notices"])

    def test_s017_a_name_in_a_file_that_is_not_a_test_file_does_not_count(self):
        """S-017, the surface's term: only a tracked test file can supply Gold."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.write("notes.md", "test_two_approved is mentioned here, but this is not a test file\n")
        repo.configure({"figures": [COUNT], "pins": [{"figure": "approved", "test": "test_two_approved"}]})
        repo.commit()
        self.assertEqual(figure(sitrep.build_board(repo.dir), "approved")["tier"], "purple")


class ManualTests(unittest.TestCase):

    def test_s018_a_hand_entered_value_is_white_and_shows_who_said_so(self):
        """S-018: a manual value carries White and its stated source."""
        repo = ThrowawayRepo(self)
        repo.configure({"manual": [{"name": "minutes per review", "value": 1.3,
                                    "source": "measured over the n50 packet, 2026-08"}]})
        repo.commit()
        got = figure(sitrep.build_board(repo.dir), "minutes per review")
        self.assertEqual((got["value"], got["tier"], got["provenance"]),
                         (1.3, "white", "measured over the n50 packet, 2026-08"))


class CountTierTests(unittest.TestCase):

    def test_s019_a_count_carries_the_lowest_tier_among_what_it_counts(self):
        """S-019: mixed tiers give the weakest; an empty list gives the source's own tier."""
        mixed = [{"tier": "purple"}, {"tier": "gold"}, {"tier": "green"}]
        self.assertEqual(sitrep.count_figure("x", mixed, "white")["tier"], "green")
        self.assertEqual(sitrep.count_figure("x", [], "purple")["tier"], "purple")

    def test_s019_the_board_counts_its_own_entries_by_that_rule(self):
        """S-019 on a real board: waiting on you is a Green count, in flight a Purple one."""
        repo = ThrowawayRepo(self)
        repo.write(".tasks/feat-0001-a.md",
                   "---\nid: feat-0001\ntitle: A\nstatus: open\npriority: P1\ndepends_on: []\n---\n"
                   "\n## Open question\n\nWhich?\n")
        repo.commit()
        repo.write("uncommitted.txt", "work\n")
        board = sitrep.build_board(repo.dir)
        self.assertEqual((figure(board, "waiting on you")["value"], figure(board, "waiting on you")["tier"]),
                         (1, "green"))
        self.assertEqual(figure(board, "in flight")["tier"], "purple")


class FailureTests(unittest.TestCase):

    def test_s020_a_figure_that_cannot_be_read_is_a_notice_not_a_guess(self):
        """S-020: a missing file, a non-JSON file, and an empty selection each give a notice, no value."""
        repo = ThrowawayRepo(self)
        repo.write("data/bank.json", BANK)
        repo.write("data/notes.txt", "not json at all\n")
        repo.configure({"figures": [
            {"name": "gone", "file": "data/missing.json", "kind": "count", "select": "items"},
            {"name": "prose", "file": "data/notes.txt", "kind": "count", "select": "items"},
            {"name": "empty", "file": "data/bank.json", "kind": "value", "select": "counts.nothing"},
        ]})
        repo.commit()
        board = sitrep.build_board(repo.dir)
        for name in ("gone", "prose", "empty"):
            with self.subTest(figure=name):
                self.assertIsNone(figure(board, name))
                self.assertTrue(any(n.startswith(f"figure {name} could not be read:")
                                    for n in board["notices"]), board["notices"])

    def test_s020_an_unreadable_configuration_is_a_notice(self):
        """S-020's neighbour: a broken `.sitrep.json` is reported and the rest of the board stands."""
        repo = ThrowawayRepo(self)
        repo.configure("{ not json")
        repo.commit()
        board = sitrep.build_board(repo.dir)
        self.assertIn("configuration could not be read: .sitrep.json (JSONDecodeError)", board["notices"])
        self.assertIsNotNone(figure(board, "waiting on you"))


class ConfiguredIntegrationBranchTests(unittest.TestCase):

    def test_the_declared_integration_branch_is_read_from_the_configuration(self):
        """S-009's surface, completed here: `integration_branch` in `.sitrep.json` is used."""
        repo = ThrowawayRepo(self)
        repo.write("a.txt", "a\n")
        repo.commit()
        run_git(repo.dir, "branch", "release")
        run_git(repo.dir, "switch", "-q", "-c", "feature")
        repo.write("b.txt", "b\n")
        repo.configure({"integration_branch": "release"})
        repo.commit("feature and config")
        board = sitrep.build_board(repo.dir)
        branches = {e["name"]: e["unmerged_commits"] for e in board["in_flight"] if e["kind"] == "branch"}
        self.assertEqual(branches, {"feature": 1})


if __name__ == "__main__":
    unittest.main()
