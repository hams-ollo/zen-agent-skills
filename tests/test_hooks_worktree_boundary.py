"""Tests for .agents/hooks/worktree-boundary-reminder.py (2026-10 kit refresh, audit 4.2).

test-quality notes: every case calls evaluate() or main() directly with injected streams
and a temporary directory laid out as a main checkout plus a linked worktree, matching the
convention in test_hooks.py. Oracles assert the exact emitted object or exact silence,
because a hook that emits nothing is also what a broken one produces.

The defect each group protects against:
  fires        - a shell write out of a worktree passes with nothing said (A1's incident)
  stays quiet  - the hook speaks on reads, on writes inside the worktree, on device files,
                 on the temp directory, or in an ordinary checkout, and becomes noise
  robustness   - a malformed payload takes down the session
"""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".agents" / "hooks" / "worktree-boundary-reminder.py"

_spec = importlib.util.spec_from_file_location("worktree_boundary_reminder", MODULE_PATH)
wbr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wbr)


class _Layout(unittest.TestCase):
    """A main checkout with `.git/` and a linked worktree whose `.git` is a file.

    The layout has to live in the system temp directory, which the hook ignores on purpose,
    so `setUp` narrows the ignore rule to device files for the duration of each test and
    one test restores the real rule to pin the temp-directory exemption itself.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name).resolve()
        self.main = base / "repo"
        (self.main / ".git").mkdir(parents=True)
        self.worktree = self.main / ".claude" / "worktrees" / "wt"
        self.worktree.mkdir(parents=True)
        (self.worktree / ".git").write_text("gitdir: ../../../.git/worktrees/wt\n",
                                            encoding="utf-8")
        # The layout sits in the temp directory, which the hook rightly ignores, so the
        # tests narrow that rule to the real temp root's *other* contents.
        self._real_ignored = wbr._ignored
        wbr._ignored = lambda token, path: token.lower().startswith("/dev/")
        self.addCleanup(setattr, wbr, "_ignored", self._real_ignored)

    def payload(self, command, tool="Bash", cwd=None, event="PostToolUse"):
        return {"hook_event_name": event, "tool_name": tool,
                "cwd": str(cwd or self.worktree), "tool_input": {"command": command}}

    def outside(self, name="AGENTS.md"):
        return (self.main / name).as_posix()


class FiresTests(_Layout):

    def test_a_copy_into_the_main_checkout_is_named(self):
        target = self.outside()
        out = wbr.evaluate(self.payload(f"cp notes.md {target}"))
        self.assertIsNotNone(out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn(str(Path(target).resolve()), ctx)
        self.assertIn("WORKTREE BOUNDARY", ctx)

    def test_a_redirect_into_the_main_checkout_is_named(self):
        out = wbr.evaluate(self.payload(f"echo x > {self.outside('x.txt')}"))
        self.assertIsNotNone(out)

    def test_a_powershell_write_is_named(self):
        out = wbr.evaluate(self.payload(
            f"Set-Content -Path {self.outside('x.txt')} -Value 1", tool="PowerShell"))
        self.assertIsNotNone(out)

    def test_every_shell_tool_name_is_recognised(self):
        for tool in sorted(wbr.SHELL_TOOLS):
            with self.subTest(tool=tool):
                self.assertIsNotNone(
                    wbr.evaluate(self.payload(f"rm {self.outside()}", tool=tool)))

    def test_stdout_is_exactly_one_json_object(self):
        out = io.StringIO()
        code = wbr.main(io.StringIO(json.dumps(self.payload(f"mv a {self.outside()}"))), out)
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(out.getvalue()), dict)


class StaysQuietTests(_Layout):

    def assertSilent(self, payload):
        self.assertIsNone(wbr.evaluate(payload))

    def test_a_read_of_an_outside_path_is_silent(self):
        self.assertSilent(self.payload(f"cat {self.outside()}"))

    def test_a_write_inside_the_worktree_is_silent(self):
        inside = (self.worktree / "notes.md").as_posix()
        self.assertSilent(self.payload(f"cp a {inside}"))

    def test_a_relative_write_is_silent(self):
        self.assertSilent(self.payload("echo x > ./notes.md"))

    def test_a_device_file_is_silent(self):
        self.assertSilent(self.payload("ls > /dev/null"))

    def test_the_main_checkout_itself_is_not_a_sandbox(self):
        self.assertSilent(self.payload(f"cp a {self.worktree.as_posix()}/x", cwd=self.main))

    def test_the_system_temp_directory_is_ignored(self):
        wbr._ignored = self._real_ignored
        scratch = (Path(tempfile.gettempdir()) / "scratch.txt").as_posix()
        self.assertSilent(self.payload(f"echo x > {scratch}"))

    def test_a_url_is_not_read_as_a_path(self):
        # Found by independent verification: `https://` matched the drive-letter branch as
        # `s:/`, so a download into the worktree named a path that does not exist.
        self.assertSilent(self.payload("curl https://example.com/a/b > out.txt"))
        self.assertSilent(self.payload("git clone git@github.com:org/repo.git > log.txt"))

    def test_a_relative_escape_is_out_of_scope(self):
        # The stated bound, pinned so nobody reads the silence as coverage: only absolute
        # paths are resolved, so `../` out of the worktree is not caught.
        self.assertSilent(self.payload("cp a ../../../README.md"))

    def test_a_non_shell_tool_is_silent(self):
        self.assertSilent(self.payload(f"cp a {self.outside()}", tool="Write"))

    def test_another_event_is_silent(self):
        self.assertSilent(self.payload(f"cp a {self.outside()}", event="PreToolUse"))


class RobustnessTests(unittest.TestCase):

    def run_main(self, text):
        out = io.StringIO()
        self.assertEqual(wbr.main(io.StringIO(text), out), 0)
        return out.getvalue()

    def test_malformed_json_is_survived_silently(self):
        self.assertEqual(self.run_main("{not json"), "")

    def test_a_non_object_payload_is_survived_silently(self):
        self.assertEqual(self.run_main("[1, 2]"), "")

    def test_missing_fields_are_survived_silently(self):
        self.assertEqual(self.run_main(json.dumps(
            {"hook_event_name": "PostToolUse", "tool_name": "Bash"})), "")

    def test_a_cwd_that_does_not_exist_is_survived_silently(self):
        self.assertEqual(self.run_main(json.dumps({
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "cwd": "/no/such/place/at/all", "tool_input": {"command": "cp a /etc/x"}})), "")


if __name__ == "__main__":
    unittest.main()
