"""Acceptance tests for the person's watermark (feat-0069).

Derived from `docs/spec/sitrep.md`, scenarios S-021 to S-026 and S-040, as amended by `chore-0093`
and re-approved by Hans Havlik: the watermark moves at the next board, read from the session
transcript, when a prompt marked as typed by a person follows a shown sitrep. Each test names the
scenario it proves in its docstring.

test-quality notes: the watermark is state outside the repository read against transcripts, so
every test runs with a temporary home directory, a throwaway repository, and JSONL transcripts in
the record shapes `chore-0093` measured across 626 real ones: `origin.kind: human` on a typed
prompt, `task-notification` on a background completion, no origin on a side-chain prompt or a
print-mode one. The home directory is redirected through the environment, both `HOME` and
`USERPROFILE`, because `Path.home()` reads the second on Windows.

Oracles assert the watermark's revision and kind together with what changed-since then reports,
because a watermark that moved to the wrong revision still "moved". "Nothing inside the repository
changed" is checked by hashing every file under it, `.git` included, rather than by asking git,
since git's own view is exactly what a stray write to the index would hide.

Each rule in the counting has a test that fails when that rule alone is removed, including the two
a measured transcript never exercises on its own: a side-chain prompt is excluded even if it were
marked, and a prompt typed before the sitrep was shown, which every resumed session holds, never
counts as a reply to it.

The defect each group protects against:
  first look - a new person sees nothing, or everything ever (S-021)
  replies    - catching up is not recorded, or recorded at the wrong revision (S-022)
  unattended - a session nobody typed in clears the person's markers (S-023, S-040)
  reset      - a rebased-away watermark crashes or lies (S-024)
  people     - one person's catching up moves another's watermark (S-025)
  explicit   - a one-off look moves the watermark it was meant to leave alone (S-026)
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".agents" / "skills" / "sitrep" / "scripts" / "sitrep.py"

_spec = importlib.util.spec_from_file_location("sitrep_watermark_under_test", SCRIPT)
sitrep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sitrep)

NOW = dt.datetime(2026, 9, 11, 12, 0, tzinfo=dt.timezone.utc)
MINUTE = dt.timedelta(minutes=1)


def iso(moment):
    return moment.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _writable_then_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def scratch(test, prefix):
    path = Path(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, path, onerror=_writable_then_retry)
    return path


def snapshot(root):
    """Every file under `root`, `.git` included, by content hash."""
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def run_git(cwd, *args, when=None):
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "sitrep test", "GIT_AUTHOR_EMAIL": "sitrep@example.invalid",
                "GIT_COMMITTER_NAME": "sitrep test", "GIT_COMMITTER_EMAIL": "sitrep@example.invalid"})
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    proc = subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, check=True, capture_output=True, text=True, env=env)
    return proc.stdout.strip()


class Repo:
    def __init__(self, test):
        self.dir = scratch(test, "sitrep-wm-")
        run_git(self.dir, "init", "-q", "-b", "main")
        self.n = 0

    def commit(self, when=None):
        self.n += 1
        (self.dir / f"file{self.n}.txt").write_text(f"{self.n}\n", encoding="utf-8")
        run_git(self.dir, "add", "-A")
        run_git(self.dir, "commit", "-q", "-m", f"commit {self.n}", when=when)
        return run_git(self.dir, "rev-parse", "HEAD")


def as_person(test, home):
    """Run the rest of the test as the person whose home directory is `home`."""
    patcher = mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)})
    patcher.start()
    test.addCleanup(patcher.stop)


def transcript(test, *records):
    path = scratch(test, "sitrep-tx-") / "session.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


def prompt(at, **overrides):
    """A main-thread prompt record, typed by a person unless `overrides` say otherwise."""
    record = {"type": "user", "isSidechain": False, "origin": {"kind": "human"},
              "timestamp": iso(at), "message": {"role": "user", "content": "next"}}
    record.update(overrides)
    return record


def caught_up_at(repo, revision, days_ago=5):
    """Give the current person a stored watermark at `revision`, and return where it is kept."""
    path = sitrep.state_path(repo.dir)
    sitrep.save_state(path, {"watermark": {"revision": revision,
                                           "shown_at": iso(NOW - dt.timedelta(days=days_ago))},
                             "shown": []})
    return path


class FirstLookTests(unittest.TestCase):

    def test_s021_a_first_look_covers_the_last_seven_days(self):
        """S-021: no watermark gives the commits dated within seven days, kind `first-look`.

        Running a board with no sitrep ever shown writes nothing under the person's home either.
        """
        home = scratch(self, "sitrep-home-")
        as_person(self, home)
        repo = Repo(self)
        repo.commit(when=NOW - dt.timedelta(days=30))
        repo.commit(when=NOW - dt.timedelta(days=2))
        repo.commit(when=NOW - dt.timedelta(days=1))
        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual(board["watermark"]["kind"], "first-look")
        self.assertEqual(board["changed"]["commits"], 2)
        self.assertFalse((home / ".claude").exists())

    def test_s021_a_repository_younger_than_the_window_counts_its_whole_history(self):
        """S-021's edge: with nothing older than seven days, every commit is new."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        repo.commit(when=NOW - dt.timedelta(days=1))
        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual((board["watermark"], board["changed"]["commits"]),
                         ({"revision": None, "kind": "first-look"}, 1))


class ReplyTests(unittest.TestCase):

    def test_s022_a_reply_moves_the_watermark_to_the_revision_the_person_was_shown(self):
        """S-022: shown A, B committed after, then the person types: the next board is at A and lists B.

        Every file inside the repository, `.git` included, is byte-identical before and after, and
        the only state written is under the person's home directory.
        """
        home = scratch(self, "sitrep-home-")
        as_person(self, home)
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        shown_at = NOW - dt.timedelta(hours=2)
        tx = transcript(self, prompt(shown_at + MINUTE))
        sitrep.record_shown(repo.dir, a, "s1", tx, now=shown_at)
        repo.commit(when=NOW - dt.timedelta(hours=1))
        before = snapshot(repo.dir)

        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual(board["watermark"], {"revision": a, "kind": "caught-up"})
        self.assertEqual(board["changed"]["commits"], 1)
        self.assertEqual(snapshot(repo.dir), before)
        state = sitrep.state_path(repo.dir)
        self.assertTrue(state.is_file())
        self.assertTrue(str(state).startswith(str(home)))

    def test_s022_the_most_recent_answered_sitrep_wins_across_sessions(self):
        """S-022 across sessions: sitreps at A, then B, both answered; the watermark lands on B.

        Recorded newest first, so an implementation that takes whichever it read last fails too.
        """
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        b = repo.commit(when=NOW - dt.timedelta(hours=5))
        earlier, later = NOW - dt.timedelta(hours=4), NOW - dt.timedelta(hours=2)
        sitrep.record_shown(repo.dir, b, "s2", transcript(self, prompt(later + MINUTE)), now=later)
        sitrep.record_shown(repo.dir, a, "s1", transcript(self, prompt(earlier + MINUTE)), now=earlier)
        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual(board["watermark"], {"revision": b, "kind": "caught-up"})
        self.assertEqual(board["changed"]["commits"], 0)


class UnattendedTests(unittest.TestCase):

    def test_s023_a_session_the_person_never_writes_in_leaves_the_watermark_alone(self):
        """S-023: shown B, then only a background notification and a sub-agent prompt: still at A."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        b = repo.commit(when=NOW - dt.timedelta(hours=3))
        path = caught_up_at(repo, a)
        shown_at = NOW - dt.timedelta(hours=2)
        tx = transcript(self,
                        prompt(shown_at + MINUTE, origin={"kind": "task-notification"}),
                        prompt(shown_at + 2 * MINUTE, isSidechain=True, origin=None))
        sitrep.record_shown(repo.dir, b, "background", tx, now=shown_at)

        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual(board["watermark"], {"revision": a, "kind": "caught-up"})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["watermark"]["revision"], a)

    def test_s023_prompts_typed_before_the_sitrep_was_shown_do_not_count(self):
        """S-023, resumed: the person's earlier prompts predate the sitrep, so they answer nothing."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        shown_at = NOW - dt.timedelta(hours=2)
        tx = transcript(self, prompt(shown_at - 30 * MINUTE), prompt(shown_at - 5 * MINUTE))
        sitrep.record_shown(repo.dir, a, "resumed", tx, now=shown_at)
        self.assertEqual(sitrep.build_board(repo.dir, now=NOW)["watermark"]["kind"], "first-look")

    def test_s023_a_side_chain_prompt_never_counts_even_carrying_a_human_mark(self):
        """S-023: a sub-agent's prompt is excluded for being in the side chain, not only for lacking a mark."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        shown_at = NOW - dt.timedelta(hours=2)
        tx = transcript(self, prompt(shown_at + MINUTE, isSidechain=True))
        sitrep.record_shown(repo.dir, a, "sub-agent", tx, now=shown_at)
        self.assertEqual(sitrep.build_board(repo.dir, now=NOW)["watermark"]["kind"], "first-look")

    def test_s023_a_missing_transcript_counts_as_no_prompt(self):
        """S-023: a transcript that is gone cannot move the watermark."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        sitrep.record_shown(repo.dir, a, "s1", str(Path(tempfile.gettempdir()) / "no-such.jsonl"),
                            now=NOW - dt.timedelta(hours=1))
        self.assertEqual(sitrep.build_board(repo.dir, now=NOW)["watermark"]["kind"], "first-look")

    def test_s040_a_prompt_nobody_is_marked_as_typing_never_moves_the_watermark(self):
        """S-040: a print-mode prompt, carrying no author mark, does not count."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        shown_at = NOW - dt.timedelta(hours=2)
        unmarked = prompt(shown_at + MINUTE, promptSource="sdk")
        del unmarked["origin"]
        sitrep.record_shown(repo.dir, a, "print-mode", transcript(self, unmarked), now=shown_at)
        self.assertEqual(sitrep.build_board(repo.dir, now=NOW)["watermark"]["kind"], "first-look")


class ResetTests(unittest.TestCase):

    def test_s024_a_watermark_on_a_vanished_commit_resets_to_a_first_look(self):
        """S-024: a watermark naming a commit the repository lacks resets, with the notice."""
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        repo.commit(when=NOW - dt.timedelta(days=1))
        caught_up_at(repo, "0" * 40)
        board = sitrep.build_board(repo.dir, now=NOW)
        self.assertEqual(board["watermark"]["kind"], "reset")
        self.assertIn("watermark reset", board["notices"])
        self.assertEqual(board["changed"]["commits"], 1)


class PeopleTests(unittest.TestCase):

    def test_s025_each_person_has_their_own_watermark(self):
        """S-025: both shown B; one replies and moves to B, the other stays at A."""
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        b = repo.commit(when=NOW - dt.timedelta(hours=3))
        shown_at = NOW - dt.timedelta(hours=2)
        homes = {name: scratch(self, f"sitrep-{name}-") for name in ("hans", "lukas")}
        for name, home in homes.items():
            with mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
                caught_up_at(repo, a)
                replies = [prompt(shown_at + MINUTE)] if name == "hans" else []
                sitrep.record_shown(repo.dir, b, name, transcript(self, *replies), now=shown_at)
        results = {}
        for name, home in homes.items():
            with mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
                results[name] = sitrep.build_board(repo.dir, now=NOW)["watermark"]
        self.assertEqual(results["hans"], {"revision": b, "kind": "caught-up"})
        self.assertEqual(results["lukas"], {"revision": a, "kind": "caught-up"})


class ExplicitSinceTests(unittest.TestCase):

    def test_s026_an_explicit_since_leaves_the_watermark_alone(self):
        """S-026: `since` B is used for the run, kind `explicit`, and the stored watermark stays at A.

        An answered sitrep at C is pending, so a board that consulted the watermark at all would
        move it and rewrite the stored state; the explicit run must leave that state byte for byte.
        """
        as_person(self, scratch(self, "sitrep-home-"))
        repo = Repo(self)
        a = repo.commit(when=NOW - dt.timedelta(days=20))
        b = repo.commit(when=NOW - dt.timedelta(days=10))
        c = repo.commit(when=NOW - dt.timedelta(days=1))
        path = caught_up_at(repo, a)
        shown_at = NOW - dt.timedelta(hours=2)
        sitrep.record_shown(repo.dir, c, "s1", transcript(self, prompt(shown_at + MINUTE)), now=shown_at)
        stored = path.read_bytes()

        board = sitrep.build_board(repo.dir, since=b, now=NOW)
        self.assertEqual(board["watermark"], {"revision": b, "kind": "explicit"})
        self.assertEqual(board["changed"]["commits"], 1)
        self.assertEqual(path.read_bytes(), stored)


if __name__ == "__main__":
    unittest.main()
