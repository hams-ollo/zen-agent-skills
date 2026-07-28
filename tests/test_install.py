"""Acceptance tests for scripts/install.py.

Derived from the behavioral contract in docs/spec/install.md. Each test is tagged with
the scenario id it covers. Standard library only, per the conventions section of AGENTS.md.

These began as characterization tests (`feat-0027`), written before the contract existed
to pin behavior so the spec would describe rather than wish. `feat-0029` wrote that
contract and promoted them: each assertion is now checked against a stated scenario, so
a failure means the tool diverged from its contract rather than merely changed.

S-009 (an unrecognised tool is rejected) and S-010 (the platform-dependent default mode)
have no test. Both live in `main()`, which takes no argv, so the CLI layer cannot be
driven from a test. That is not a gap in the contract but a coverage gap caused by the
code's shape, and it is now a contract-backed reason to give `install.py` the injectable
entry point that `validate-skills.py` and `build-adapters.py` both have.

One testability constraint remains worked around rather than fixed:

- `MANIFEST` is a module-level constant pointing at `scripts/.install-manifest.json`, so
  any test calling `install()` would write into the real repository. Each test redirects
  it to a temp path and restores it afterwards.

Recorded as a finding in docs/spec/install.characterization.md.
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "install.py"

_spec = importlib.util.spec_from_file_location("zen_install", MODULE_PATH)
inst = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inst)


class InstallAcceptanceTests(unittest.TestCase):
    """Scenarios S-001 through S-008 and S-011, at the component layer."""

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
        # Scenario S-001 (supporting): the set of skills is those directories holding a
        # SKILL.md. S-001 presupposes this definition without stating it; see the matrix.
        found = inst.discover_skills()
        self.assertTrue(all((d / "SKILL.md").is_file() for d in found))
        self.assertEqual([d.name for d in found], sorted(d.name for d in found))

    def test_install_places_every_skill_and_the_rules_module(self):
        # Scenarios S-001 and S-002: one directory per skill under the requested tool's
        # discovery path, plus the rules module.
        expected = {d.name for d in inst.discover_skills()}
        code, _ = self._install()
        self.assertEqual(code, 0)
        placed = {p.name for p in (self.home / ".claude" / "skills").iterdir()}
        self.assertEqual(placed, expected)
        self.assertTrue((self.home / ".claude" / "rules" / "house-style.md").is_file())

    def test_the_rules_module_lands_where_a_skill_reference_resolves(self):
        # Scenario S-002: the module lands where the skills' own references resolve,
        # which is the property the 2026-07-27 blocker violated.
        self._install()
        skill = self.home / ".claude" / "skills" / "house-review" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertTrue((skill.parent / ".." / ".." / "rules" / "review-quality.md").exists())

    def test_a_second_run_updates_rather_than_conflicting(self):
        # Scenario S-003: a re-run recognises the tool's own targets rather than
        # reporting a conflict against its own work.
        self._install()
        code, out = self._install()
        self.assertEqual(code, 0)
        self.assertIn("updated", out)
        self.assertNotIn("CONFLICT", out)

    def test_an_unmanaged_file_at_a_target_is_reported_and_skipped(self):
        # Scenario S-004: an unmanaged target is refused, not overwritten.
        target = self.home / ".claude" / "skills" / "doc-sync"
        target.parent.mkdir(parents=True)
        target.write_text("someone else's file\n", encoding="utf-8")
        code, out = self._install()
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", out)
        self.assertEqual(target.read_text(encoding="utf-8"), "someone else's file\n")

    def test_a_dry_run_writes_nothing_at_all(self):
        # Scenario S-006: a preview run writes neither targets nor the record.
        code, out = self._install(dry=True)
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse(self.home.exists())
        self.assertFalse(inst.MANIFEST.exists())

    def test_uninstall_removes_what_was_installed_and_empties_the_manifest(self):
        # Scenario S-007: reversing a run removes exactly what it recorded.
        self._install()
        self.assertTrue((self.home / ".claude" / "skills").iterdir())
        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("removed", out)
        self.assertEqual(list((self.home / ".claude" / "skills").iterdir()), [])
        self.assertFalse((self.home / ".claude" / "rules").exists())
        self.assertEqual(json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"], [])

    def test_uninstall_with_no_manifest_reports_nothing_recorded(self):
        # Scenario S-008: reversing with nothing recorded is not an error.
        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("Nothing recorded as installed", out)

    def test_a_lost_record_makes_previous_copies_unmanaged(self):
        # Scenario S-005: a copied directory carries nothing distinguishing it from a
        # user's own, so losing the record means the tool must refuse its own past work
        # rather than assume it. Surprising but correct, which is why it is specified.
        self._install()
        inst.MANIFEST.unlink()
        code, out = self._install()
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", out)

    def test_a_refused_symlink_reports_what_to_do_instead(self):
        # Scenario S-011: the failure a Windows user without Developer Mode hits, which
        # must name the way out rather than surface an OSError.
        real = os.symlink

        def refuse(*args, **kwargs):
            raise OSError("privilege not held")

        os.symlink = refuse
        try:
            with self.assertRaises(SystemExit) as caught:
                inst._link(Path("src"), self.root / "dst")
        finally:
            os.symlink = real
        message = str(caught.exception)
        self.assertIn("--mode copy", message)
        self.assertIn("Developer Mode", message)

    def test_an_unrecognised_tool_is_rejected_before_anything_is_placed(self):
        # Scenario S-009. The list pairs a supported tool with an unsupported one, so
        # this also proves the valid entry does not rescue the invocation.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--tools", "claude,bogus", "--home", str(self.home)])
        self.assertEqual(code, 2)
        self.assertIn("bogus", buf.getvalue())
        self.assertFalse(self.home.exists(), "nothing may be placed when a tool is unrecognised")

    def test_the_default_mode_suits_the_platform(self):
        # Scenario S-010, on the platform actually running the test. It captures the mode
        # main() passes through rather than re-deriving the rule, so it fails if the
        # default is changed or the flag stops being wired to it.
        #
        # Only the running platform's branch is exercised, and deliberately so: the rule
        # reads `os.name`, and faking that breaks `pathlib`, which selects PosixPath or
        # WindowsPath from the same attribute and raises on instantiation. An assertion
        # that hardcoded "copy" would pass everywhere while meaning nothing off Windows,
        # so this derives the expectation from the platform and checks the wiring.
        expected = "copy" if os.name == "nt" else "symlink"
        seen = []

        def recording_install(tools, mode, home, dry):
            seen.append(mode)
            return 0

        real_install = inst.install
        inst.install = recording_install
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                inst.main(["--home", str(self.home)])
        finally:
            inst.install = real_install
        self.assertEqual(seen, [expected])


if __name__ == "__main__":
    unittest.main()
