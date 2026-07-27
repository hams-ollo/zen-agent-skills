"""CHARACTERIZATION tests for scripts/install.py.

These are characterization tests, not acceptance tests. `install.py` has no spec, so
there is no contract to derive from: every assertion below pins the behavior the script
exhibits **today**, so that a later change to it is a visible diff rather than a silent
one. Read them as "this is what it does", never as "this is what it should do". If one
fails after a deliberate change, the right response may well be to update the test.

Written 2026-07-27 via `test-author`'s characterization mode (`feat-0027`), on the kit's
only script with neither a contract nor coverage.

Two testability constraints, worked around here rather than fixed, because
characterization pins current behavior and never edits production code:

- `MANIFEST` is a module-level constant pointing at `scripts/.install-manifest.json`, so
  any test calling `install()` would write into the real repository. Each test redirects
  it to a temp path and restores it afterwards.
- `main()` calls `parse_args()` with no argv, so the CLI layer cannot be driven from a
  test the way `validate-skills.py` and `build-adapters.py` can. Only the functions below
  `main()` are exercised.

Both are recorded as findings in docs/spec/install.characterization.md.
"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "install.py"

_spec = importlib.util.spec_from_file_location("zen_install", MODULE_PATH)
inst = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inst)


class InstallCharacterizationTests(unittest.TestCase):
    """Pins the observable behavior of install() and uninstall() as of 2026-07-27."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        # Redirect the manifest away from the real repository for the duration.
        self._real_manifest = inst.MANIFEST
        inst.MANIFEST = self.root / "manifest.json"

    def tearDown(self):
        inst.MANIFEST = self._real_manifest
        self._tmp.cleanup()

    def _install(self, tools=("claude",), mode="copy", dry=False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.install(list(tools), mode, self.home, dry)
        return code, buf.getvalue()

    def _uninstall(self, dry=False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.uninstall(self.home, dry)
        return code, buf.getvalue()

    def test_discover_skills_returns_only_directories_holding_a_skill_md(self):
        # Characterization: discovery is by the presence of SKILL.md, sorted by name.
        found = inst.discover_skills()
        self.assertTrue(all((d / "SKILL.md").is_file() for d in found))
        self.assertEqual([d.name for d in found], sorted(d.name for d in found))

    def test_install_places_every_skill_and_the_rules_module(self):
        # Characterization: one directory per skill under <home>/.claude/skills, plus
        # the rules module as its sibling.
        expected = {d.name for d in inst.discover_skills()}
        code, _ = self._install()
        self.assertEqual(code, 0)
        placed = {p.name for p in (self.home / ".claude" / "skills").iterdir()}
        self.assertEqual(placed, expected)
        self.assertTrue((self.home / ".claude" / "rules" / "house-style.md").is_file())

    def test_the_rules_module_lands_where_a_skill_reference_resolves(self):
        # Characterization, and the property the 2026-07-27 fix existed to create:
        # ../../rules/<file> from an installed skill must resolve on disk.
        self._install()
        skill = self.home / ".claude" / "skills" / "house-review" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertTrue((skill.parent / ".." / ".." / "rules" / "review-quality.md").exists())

    def test_a_second_run_updates_rather_than_conflicting(self):
        # Characterization: re-running is idempotent because the manifest records what
        # this tool created, so its own targets are recognised instead of refused.
        self._install()
        code, out = self._install()
        self.assertEqual(code, 0)
        self.assertIn("updated", out)
        self.assertNotIn("CONFLICT", out)

    def test_an_unmanaged_file_at_a_target_is_reported_and_skipped(self):
        # Characterization: a real file this tool did not create is never overwritten.
        target = self.home / ".claude" / "skills" / "doc-sync"
        target.parent.mkdir(parents=True)
        target.write_text("someone else's file\n", encoding="utf-8")
        code, out = self._install()
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", out)
        self.assertEqual(target.read_text(encoding="utf-8"), "someone else's file\n")

    def test_a_dry_run_writes_nothing_at_all(self):
        # Characterization: no target, and no manifest either.
        code, out = self._install(dry=True)
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse(self.home.exists())
        self.assertFalse(inst.MANIFEST.exists())

    def test_uninstall_removes_what_was_installed_and_empties_the_manifest(self):
        # Characterization: uninstall is driven by the manifest, not by scanning.
        self._install()
        self.assertTrue((self.home / ".claude" / "skills").iterdir())
        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("removed", out)
        self.assertEqual(list((self.home / ".claude" / "skills").iterdir()), [])
        self.assertFalse((self.home / ".claude" / "rules").exists())
        self.assertEqual(json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"], [])

    def test_uninstall_with_no_manifest_reports_nothing_recorded(self):
        # Characterization: the no-op path exits zero rather than erroring.
        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("Nothing recorded as installed", out)


if __name__ == "__main__":
    unittest.main()
