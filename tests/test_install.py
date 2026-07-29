"""Acceptance tests for scripts/install.py.

Derived from the behavioral contract in docs/spec/install.md. Each test is tagged with
the scenario id it covers. Standard library only, per the conventions section of AGENTS.md.

These began as characterization tests (`feat-0027`), written before the contract existed
to pin behavior so the spec would describe rather than wish. `feat-0029` wrote that
contract and promoted them: each assertion is now checked against a stated scenario, so
a failure means the tool diverged from its contract rather than merely changed.

S-009 (an unrecognised tool is rejected) and S-010 (the platform-dependent default mode)
once had no test. Both lived in `main()`, which took no argv, so the CLI layer could not
be driven from a test. That was not a gap in the contract but a coverage gap caused by
the code's shape, which made it a contract-backed reason to give `install.py` the
injectable entry point that `validate-skills.py` and `build-adapters.py` both have.
`chore-0017` added it, and both scenarios are covered here now, by
`test_an_unrecognised_tool_is_rejected_before_anything_is_placed` and
`test_the_default_mode_suits_the_platform`. S-010 is covered on the running platform's
branch only; docs/spec/install.conformance.md records why.

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


def _symlinks_work() -> bool:
    """Whether this platform and account can create a directory symlink at all.

    Windows without Developer Mode cannot, which is the whole reason S-011 exists.
    Probed rather than inferred from `os.name`, since the answer depends on the
    account's privileges and not only on the platform.
    """
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "src"
        src.mkdir()
        try:
            os.symlink(src, Path(d) / "link", target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


SYMLINKS_WORK = _symlinks_work()


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

    def _install(self, tools=("claude",), mode="copy", dry=False, profile="all"):
        # Defaults to `all` so every pre-existing scenario keeps asserting over the whole
        # skill set, which is what it was written against. The profile axis (S-013) is
        # covered separately, including its own default.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.install(list(tools), mode, self.home, dry, profile)
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

    def test_uninstall_of_one_home_leaves_another_homes_install_intact(self):
        # Scenario S-012: one manifest serves every home installed to from this checkout,
        # because install() merges into the existing record. Before bug-0003 this test
        # failed: uninstall ignored its `home` argument, removed every recorded target,
        # and emptied the whole record, so reversing a throwaway home destroyed the real
        # installation while reporting success.
        other_home = self.root / "other-home"

        self._install()                                    # into self.home
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.install(["claude"], "copy", other_home, False)

        recorded = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        self.assertTrue(any(str(other_home) in e["target"] for e in recorded),
                        "both homes should be in one record, or this test proves nothing")

        code, out = self._uninstall()                      # reverse self.home only
        self.assertEqual(code, 0)

        # The reversed home is gone.
        self.assertEqual(list((self.home / ".claude" / "skills").iterdir()), [])
        # The untouched home still has its skills on disk.
        survivors = list((other_home / ".claude" / "skills").iterdir())
        self.assertTrue(survivors, "the other home's targets must survive")
        self.assertTrue((other_home / ".claude" / "rules").exists())
        # And is still recorded, so it can be reversed later.
        left = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        self.assertTrue(left, "the other home's entries must remain in the record")
        self.assertTrue(all(str(other_home) in e["target"] for e in left))
        self.assertIn("Kept", out)

    def test_uninstall_reports_when_nothing_is_recorded_for_this_home(self):
        # Scenario S-012 (second half): asking to reverse a home that holds nothing is not
        # an error and must not fall through to removing another home's targets.
        self._install()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.uninstall(self.root / "never-installed", False)
        self.assertEqual(code, 0)
        self.assertIn("Nothing recorded as installed beneath", buf.getvalue())
        self.assertTrue(list((self.home / ".claude" / "skills").iterdir()),
                        "the installed home must be untouched")

    def test_uninstall_honours_a_home_the_caller_has_not_resolved(self):
        # Scenario S-007, and bug-0009. `uninstall()` is a supported entry point
        # (chore-0017), so the scoping check cannot depend on the caller having
        # resolved its argument the way `main()` does. Before the fix `_beneath()`
        # compared both sides as spelled, so a relative or `..`-bearing home matched
        # no recorded target: `mine` came out empty, nothing was removed, and the run
        # printed the nothing-recorded line and exited zero.
        #
        # The rest of the suite passes the same `self.home` object to both sides, so
        # the two spellings agree by construction and the lexical comparison succeeds
        # by accident. Only an install and an uninstall that disagree on spelling can
        # fail against the pre-fix code.
        resolved = self.home.resolve()
        spellings = {
            "relative": Path("home"),
            "dot-dot": self.root / ".." / self.root.name / "home",
        }
        placed = resolved / ".claude" / "skills"

        for label, home in spellings.items():
            with self.subTest(spelling=label):
                with contextlib.redirect_stdout(io.StringIO()):
                    inst.install(["claude"], "copy", resolved, False, "core")
                self.assertTrue(list(placed.iterdir()), "precondition: skills are on disk")

                cwd = os.getcwd()
                os.chdir(self.root)
                try:
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        code = inst.uninstall(home, False)
                finally:
                    os.chdir(cwd)

                out = buf.getvalue()
                self.assertEqual(code, 0)
                self.assertNotIn("Nothing recorded as installed beneath", out,
                                 "an unresolved home must not read as an empty one")
                self.assertIn("removed", out)
                self.assertEqual(list(placed.iterdir()), [])
                self.assertFalse((resolved / ".claude" / "rules").exists())
                self.assertEqual(
                    json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"], [],
                    "the reversed entries must leave the record")

    @unittest.skipUnless(SYMLINKS_WORK, "this platform or account cannot create symlinks")
    def test_uninstall_in_symlink_mode_removes_the_links_it_placed(self):
        # Scenario S-007 in the mode that is the POSIX default and had no test.
        #
        # A guard rather than a regression proof: it passes before and after bug-0009,
        # and exists to fail against the plausible wrong fix. Every recorded target here
        # *is* a link back to its source in this checkout, so a scoping check that
        # resolved a target's final component would follow it out of the home entirely,
        # match nothing, and reproduce the same silent no-op the fix removes.
        with contextlib.redirect_stdout(io.StringIO()):
            inst.install(["claude"], "symlink", self.home, False, "core")
        placed = self.home / ".claude" / "skills"
        self.assertTrue(any(p.is_symlink() for p in placed.iterdir()),
                        "precondition: symlink mode placed links, not copies")

        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("removed", out)
        self.assertEqual(list(placed.iterdir()), [])
        self.assertFalse((self.home / ".claude" / "rules").exists())

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

        def recording_install(tools, mode, home, dry, profile=inst.DEFAULT_PROFILE):
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


class ProfileTests(unittest.TestCase):
    """Scenarios S-013 and S-014: the profile axis, its closure, and its budget report.

    The defect worth protecting against is not a wrong count. It is a profile that
    installs a skill whose composed sibling is absent, which is silent: the skill loads,
    reads correctly, and the reference it depends on resolves to nothing. That is the
    failure `install.py` already shipped once with the rules module, so the load-bearing
    assertion here is the closure one, not the arithmetic.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self._real_manifest = inst.MANIFEST
        inst.MANIFEST = self.root / "manifest.json"

    def tearDown(self):
        inst.MANIFEST = self._real_manifest
        self._tmp.cleanup()

    def test_every_profile_is_closed_over_sibling_references(self):
        # Scenario S-013: no placed skill may reference a skill the same run did not place.
        all_skills = inst.discover_skills()
        for name in inst.PROFILE_SEEDS:
            with self.subTest(profile=name):
                selected, _ = inst.resolve_profile(name, all_skills)
                placed = {d.name for d in selected}
                for d in selected:
                    missing = inst.sibling_refs(d) & set(n.name for n in all_skills) - placed
                    self.assertEqual(missing, set(),
                                     f"{name} would ship {d.name} without {sorted(missing)}")

    def test_the_default_profile_places_fewer_than_all_skills(self):
        # Scenario S-013: the point of the axis is that the default costs less than
        # everything. A default equal to `all` would satisfy the flag and not the goal.
        all_skills = inst.discover_skills()
        selected, _ = inst.resolve_profile(inst.DEFAULT_PROFILE, all_skills)
        self.assertLess(len(selected), len(all_skills))

    def test_profiles_are_nested_from_smallest_to_largest(self):
        # Scenario S-013: core is a subset of spine, and spine of all. A profile set that
        # crossed over would make "smaller profile" meaningless.
        all_skills = inst.discover_skills()
        core = {d.name for d in inst.resolve_profile("core", all_skills)[0]}
        spine = {d.name for d in inst.resolve_profile("spine", all_skills)[0]}
        every = {d.name for d in inst.resolve_profile("all", all_skills)[0]}
        self.assertTrue(core < spine < every)

    def test_an_expanded_seed_is_reported(self):
        # Scenario S-013: a request that silently grew is the thing the report exists to
        # prevent. `spine`'s seed is not closed, so this run must say so.
        _, added = inst.resolve_profile("spine", inst.discover_skills())
        self.assertTrue(added, "the spine seed is expected to require expansion")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.install(["claude"], "copy", self.home, True, "spine")
        self.assertIn("expanded to stay closed over sibling references", buf.getvalue())

    def test_an_unclosed_request_is_not_reported_as_expanded(self):
        # Scenario S-013 (negative): `core` is already closed, so no notice belongs.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.install(["claude"], "copy", self.home, True, "core")
        self.assertNotIn("expanded to stay closed", buf.getvalue())

    def test_the_summary_reports_the_budget_for_every_profile(self):
        # Scenario S-014: the installed profile's total, and each profile's, so the
        # number is comparable rather than absolute.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.install(["claude"], "copy", self.home, True, "core")
        out = buf.getvalue()
        budgets = inst.profile_budgets(inst.discover_skills())
        self.assertIn("Description budget:", out)
        self.assertIn(f"{budgets['core']} characters for this profile", out)
        for name, total in budgets.items():
            self.assertIn(f"{name}={total}", out)

    def test_a_smaller_profile_costs_fewer_description_characters(self):
        # Scenario S-014: the figure has to track the selection, or it is decoration.
        budgets = inst.profile_budgets(inst.discover_skills())
        self.assertLess(budgets["core"], budgets["spine"])
        self.assertLess(budgets["spine"], budgets["all"])

    def test_a_description_is_measured_without_its_block_scalar_indicator(self):
        # Scenario S-014: four skills write `description: >-`. Counting the indicator
        # would inflate the reported budget by three characters per such skill.
        handoff = next(d for d in inst.discover_skills() if d.name == "agent-handoff")
        desc = inst.description_of(handoff)
        self.assertFalse(desc.startswith(">"))
        self.assertTrue(desc.startswith("Turns the current session"))

    def test_an_unrecognised_profile_places_nothing_and_exits_non_zero(self):
        # Scenario S-013: rejected the way an unrecognised tool is (S-009).
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--home", str(self.home), "--profile", "enormous"])
        self.assertEqual(code, 2)
        self.assertIn("Unknown profile", buf.getvalue())
        self.assertFalse((self.home / ".claude" / "skills").exists())

    def test_uninstall_reverses_targets_a_different_profile_placed(self):
        # Scenario S-007 with S-013: reversal is scoped by home, not by profile. An
        # adopter who installs `all` then reverses must not be left with orphans
        # because the default profile is narrower than what they placed.
        with contextlib.redirect_stdout(io.StringIO()):
            inst.install(["claude"], "copy", self.home, False, "all")
            code = inst.uninstall(self.home, False)
        self.assertEqual(code, 0)
        remaining = list((self.home / ".claude" / "skills").iterdir())
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
