"""Acceptance tests for .agents/hooks/skill-reachability-reminder.py (feat-0046).

Derived from docs/spec/cloud-executable.md, S-008 to S-016.

test-quality notes: every scenario is covered at the lowest faithful layer, calling
evaluate() and main() directly with injected streams and a temporary filesystem, matching
the convention in test_hooks.py. Oracles assert the exact emitted object or exact silence,
never "does not crash", because a hook that emits nothing is exactly what a broken one
also produces.

The defect each group protects against:
  reports      - a session starts with nothing loaded and is never told (S-008)
  stays quiet  - the hook speaks on every start and becomes a line agents skip (S-010)
  source       - it repeats itself on resume, clear, compact, and fork (S-013)
  writes       - a hook that never writes starts writing a cache or marker (S-014)
  robustness   - a malformed payload takes down the session (S-015)
  no detection - it grows an environment check and answers differently by host (S-016)
"""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".agents" / "hooks" / "skill-reachability-reminder.py"

_spec = importlib.util.spec_from_file_location("skill_reachability_reminder", MODULE_PATH)
srr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srr)


def place_skill(root: Path, subpath: Path, name="alpha"):
    """Create one discoverable skill under root/subpath."""
    skill = root / subpath / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
    return skill


def payload(source="startup", cwd=None, event="SessionStart"):
    p = {"hook_event_name": event, "source": source}
    if cwd is not None:
        p["cwd"] = str(cwd)
    return p


class ReachabilityTests(unittest.TestCase):
    """S-008 to S-012: what counts as reachable, and what is reported."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_skills_anywhere_is_reported(self):
        # S-008.
        out = srr.evaluate(payload(cwd=self.project), home=self.home)
        self.assertIsNotNone(out, "an unreachable session must be told")
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual("SessionStart", out["hookSpecificOutput"]["hookEventName"])
        self.assertIn("NO SKILLS REACHABLE", context)
        self.assertIn("install.py", context, "the report must name the way out")

    def test_project_scope_skills_count_as_reachable(self):
        # S-009. The case a cloud session would be fixed by.
        place_skill(self.project, Path(".claude") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_user_scope_skills_count_as_reachable(self):
        # S-010, and the ordinary local case.
        place_skill(self.home, Path(".claude") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_the_opencode_scope_counts_too(self):
        # Both discovery directories are checked at both scopes. A session with only the
        # opencode tree installed is not an unreachable session.
        place_skill(self.home, Path(".agents") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_an_empty_discovery_directory_is_not_reachable(self):
        # --uninstall leaves the parent directory behind, so treating its existence as
        # reachability would report success for a home whose skills were just removed.
        # Verified against the real installer: after an uninstall the tree is
        # .claude/skills with no files under it.
        (self.home / ".claude" / "skills").mkdir(parents=True)
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_directory_without_skill_md_does_not_count(self):
        # A stray directory in the discovery path is not a skill.
        (self.home / ".claude" / "skills" / "notes").mkdir(parents=True)
        (self.home / ".claude" / "skills" / "notes" / "README.md").write_text("x")
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_stale_install_is_still_reachable_and_still_silent(self):
        # S-011. The hook answers reachability, not currency: a skill whose content has
        # drifted from its source is still reachable, and this hook makes no claim about
        # it. Its silence therefore means reachable and never means current.
        skill = place_skill(self.home, Path(".claude") / "skills")
        (skill / "SKILL.md").write_text("---\nname: alpha\n---\nedited since install\n",
                                        encoding="utf-8")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_skills_present_with_no_manifest_are_reachable(self):
        # S-012. The manifest is not consulted at all: reachability is a filesystem
        # question. install.py --check answers the other one and exits 2 for the same
        # home, which test_install.py already pins. Both answers are correct.
        place_skill(self.home, Path(".claude") / "skills")
        self.assertFalse((self.home / "scripts").exists(), "no manifest anywhere")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))


class SourceTests(unittest.TestCase):
    """S-013: only a genuinely new session fires."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_startup_fires(self):
        self.assertIsNotNone(
            srr.evaluate(payload("startup", cwd=self.root), home=self.home))

    def test_the_continuing_sources_do_not_fire(self):
        # Each is a session whose agent has already been told. Tested one at a time so a
        # failure names which source regressed.
        for source in ("resume", "clear", "compact", "fork"):
            with self.subTest(source=source):
                self.assertIsNone(
                    srr.evaluate(payload(source, cwd=self.root), home=self.home),
                    f"source {source} must not fire even when unreachable")

    def test_another_event_does_not_fire(self):
        # Two-stage filtering: the harness matcher is coarse, this is the precise check.
        self.assertIsNone(
            srr.evaluate(payload("startup", cwd=self.root, event="PostToolUse"),
                         home=self.home))


class SideEffectTests(unittest.TestCase):
    """S-014: it writes nothing, in every case."""

    def _tree(self, root):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*"))

    def test_the_reporting_path_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "home").mkdir()
            before = self._tree(root)
            srr.evaluate(payload(cwd=root / "project"), home=root / "home")
            self.assertEqual(before, self._tree(root),
                             "the hook must not create a cache, marker, or log")

    def test_the_silent_path_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            place_skill(home, Path(".claude") / "skills")
            before = self._tree(root)
            srr.evaluate(payload(cwd=root), home=home)
            self.assertEqual(before, self._tree(root))


class RobustnessTests(unittest.TestCase):
    """S-015: an unreadable payload leaves the session unchanged."""

    def run_main(self, text):
        out = io.StringIO()
        code = srr.main(stdin=io.StringIO(text), stdout=out)
        return code, out.getvalue()

    def test_malformed_json_is_silent_and_exits_zero(self):
        code, out = self.run_main("{not json")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_empty_stdin_is_silent_and_exits_zero(self):
        code, out = self.run_main("")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_a_non_object_payload_is_silent(self):
        code, out = self.run_main("[1, 2, 3]")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_a_payload_missing_every_field_is_silent(self):
        code, out = self.run_main("{}")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_main_emits_exactly_one_json_object_when_it_fires(self):
        # main() resolves the user scope through Path.home() and takes no injection point
        # for it, which is correct for a hook: the streams are injectable because the
        # module contract requires it, and nothing else needs to be. So this steers
        # Path.home() through the environment it reads, covering both platforms, rather
        # than reaching into the module. Without it this test passes or fails depending on
        # whether the machine running it happens to have skills installed.
        saved = dict(os.environ)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["HOME"] = tmp          # POSIX
                os.environ["USERPROFILE"] = tmp   # Windows
                code, out = self.run_main(json.dumps(payload(cwd=tmp)))
        finally:
            os.environ.clear()
            os.environ.update(saved)

        self.assertEqual(0, code)
        parsed = json.loads(out)  # raises if it is not exactly one object
        self.assertIn("hookSpecificOutput", parsed)
        self.assertEqual("SessionStart", parsed["hookSpecificOutput"]["hookEventName"])


class NoEnvironmentDetectionTests(unittest.TestCase):
    """S-016: the answer does not depend on where it runs."""

    def test_output_is_byte_identical_across_differing_environments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "home").mkdir()
            args = (payload(cwd=root / "project"),)
            kwargs = {"home": root / "home"}

            first = srr.evaluate(*args, **kwargs)
            saved = dict(os.environ)
            try:
                # Plausible cloud-ish markers. None of them may change the answer.
                os.environ["CI"] = "true"
                os.environ["CLAUDE_CODE_CLOUD"] = "1"
                os.environ["CODESPACES"] = "true"
                second = srr.evaluate(*args, **kwargs)
            finally:
                os.environ.clear()
                os.environ.update(saved)

        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_the_source_reads_no_environment(self):
        # A structural guard: the honest way to keep S-016 true is not to look. If this
        # ever needs relaxing, that is a contract change, not a test to loosen.
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("os.environ", "getenv", "platform."):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
