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
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def _marked_draft(skill_dir: Path) -> bool:
    """Whether a skill's frontmatter marks it a draft, read independently of install.py.

    A second, deliberately crude reader: walk to the closing `---` and look for a line
    that is exactly `status: draft`. It exists so a test asserting which skills get
    placed has an oracle that does not call `status_of` or `partition_drafts`, the code
    it is checking. An expectation built from those would move together with the actual
    set if either ever misclassified a skill, which is the one failure S-015 is for.

    Crude on purpose: it does not check that the line sits under `metadata:`, so it is
    the looser of the two readers. That direction is safe here, since the two agreeing
    is the assertion and a spurious disagreement fails loudly rather than passing.
    """
    lines = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for raw in lines[1:]:
        if raw.strip() == "---":
            return False
        if raw.strip() == "status: draft":
            return True
    return False


@contextlib.contextmanager
def _working_directory(path: Path):
    """Run a block with the process working directory moved, then restore it.

    The `bug-0010` regressions need an install and its reversal to disagree about the
    current directory, since that is the only way a relative recorded target can be
    observed to mean two different places. Restoring in a `finally` matters more here
    than usual: a leaked `chdir` would silently re-point every later test's relative
    path, and the suite installs into directories it then deletes.
    """
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


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
        #
        # S-015 narrows S-001's "every skill" to every *shipped* skill, so the expected
        # set is the shipped one rather than everything discovered. The two are identical
        # while no skill carries a draft marker, which is the case as of 2026-08-05;
        # deriving the shipped set means the day one does, this test keeps asserting
        # S-001 instead of failing for a reason it has no opinion about.
        #
        # Derived by `_marked_draft` and deliberately NOT by `inst.partition_drafts`. The
        # partition is the code under test here: if it ever misclassified a skill, an
        # expectation built from it would move with the actual set and this test would
        # stay green through exactly the failure S-015 exists to catch.
        expected = {d.name for d in inst.discover_skills() if not _marked_draft(d)}
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

    def test_a_second_run_recognises_what_a_relative_home_placed(self):
        # Scenario S-003, and bug-0010. `install()` is a supported entry point
        # (chore-0017) and, before the fix, recorded each target exactly as `home` spelled
        # it, so a relative home wrote relative strings into a persisted record.
        # `is_managed()` compares `e.get("target") == str(target)` as an exact string, so
        # the second run matched nothing it had placed and reported a CONFLICT against its
        # own work, which is the opposite of what S-003 requires.
        #
        # Every other re-run test passes one already-absolute `self.home` to both runs, so
        # the two spellings agree by construction and the exact-string comparison succeeds
        # by accident. Only two runs that disagree on spelling can fail against the
        # pre-fix `install()`.
        with _working_directory(self.root):
            with contextlib.redirect_stdout(io.StringIO()):
                inst.install(["claude"], "copy", Path("home"), False, "core")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = inst.install(["claude"], "copy", self.home.resolve(), False, "core")

        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertNotIn("CONFLICT", out, "the tool must not refuse its own previous run")
        self.assertIn("updated", out)

    def test_every_recorded_target_is_absolute(self):
        # Scenarios S-003 and S-007 (supporting), and bug-0010. Both consequences follow
        # from one property of the record, and they fail at different layers: the
        # exact-string comparison in `is_managed()` and the existence check in
        # `uninstall()`. Asserting the property itself names the cause rather than only
        # those two symptoms, and it holds for a reader of the record that no scenario
        # here has thought of yet.
        with _working_directory(self.root):
            with contextlib.redirect_stdout(io.StringIO()):
                inst.install(["claude"], "copy", Path("home"), False, "core")

        recorded = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        self.assertTrue(recorded, "precondition: the run recorded its targets")
        self.assertEqual([e["target"] for e in recorded
                          if not Path(e["target"]).is_absolute()], [],
                         "a relative recorded target means whatever the reader's "
                         "directory makes it mean")

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
        #
        # The two record assertions below compare against the *resolved* spelling of
        # `other_home` (bug-0010). `install()` now resolves the home it is handed, and
        # `tempfile` does not promise a resolved path: on macOS it hands out one under
        # `/var`, a symlink to `/private/var`, so the recorded target is the resolved form
        # and a substring check against the unresolved one fails. That failure would be
        # correct and the assertion would be what is wrong, so this compares resolved
        # forms rather than being loosened until it passes. It cannot be observed on
        # Windows, where the two spellings agree; CI's macOS legs are the check.
        other_home = self.root / "other-home"
        other_home_recorded = str(other_home.resolve())

        self._install()                                    # into self.home
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.install(["claude"], "copy", other_home, False)

        recorded = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        self.assertTrue(any(other_home_recorded in e["target"] for e in recorded),
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
        self.assertTrue(all(other_home_recorded in e["target"] for e in left))
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

    def test_a_relative_home_is_reversible_and_never_orphans_its_targets(self):
        # Scenario S-007, and bug-0010. `install()` records each target as `home` spelled
        # it, so before the fix a relative home persisted relative strings. Such a string
        # has no fixed meaning: `Path.resolve()` reads it against whatever the current
        # directory happens to be when the record is read, which is why `bug-0009`'s
        # normalisation of both sides of the comparison could not repair it.
        #
        # Two reversals are needed, because no single one can fail against the pre-fix
        # code in both of its ways. Pre-fix, a relative entry is claimed only when the
        # reversal runs from the directory the install's spelling assumed; post-fix, an
        # entry is claimed only when `home` names the directory actually installed to.
        # Those are different runs, so each is a subtest:
        #
        # - `same directory`: the reversal names the installed directory from another cwd.
        #   Pre-fix the relative entries resolve beneath the wrong parent, match nothing,
        #   and the run reports nothing recorded while removing nothing.
        # - `same spelling`: the reversal repeats the install's own relative spelling from
        #   another cwd, so both sides resolve consistently and the entries are claimed.
        #   Pre-fix `Path(e["target"]).exists()` is then False, so every target is reported
        #   `gone` rather than removed and `save_manifest(others, dry)` drops all of them
        #   while their directories stay on disk: created, no longer recorded, and
        #   therefore permanently unmanaged. That is the state this test exists to forbid,
        #   and it is worse than the no-op `bug-0009` fixed.
        resolved = self.home.resolve()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        placed = resolved / ".claude" / "skills"

        def install_with_a_relative_home():
            with _working_directory(self.root):
                with contextlib.redirect_stdout(io.StringIO()):
                    inst.install(["claude"], "copy", Path("home"), False, "core")

        def reverse_from_elsewhere(home):
            with _working_directory(elsewhere):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = inst.uninstall(home, False)
            return code, buf.getvalue()

        def recorded():
            return json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]

        with self.subTest(reversal="same directory, another cwd"):
            install_with_a_relative_home()
            self.assertTrue(list(placed.iterdir()), "precondition: skills are on disk")

            code, out = reverse_from_elsewhere(Path("..") / "home")
            self.assertEqual(code, 0)
            self.assertIn("removed", out)
            self.assertNotIn("gone ", out, "a target on disk must not read as absent")
            self.assertEqual(list(placed.iterdir()), [])
            self.assertFalse((resolved / ".claude" / "rules").exists())
            self.assertEqual(recorded(), [], "the reversed entries must leave the record")

        with self.subTest(reversal="same spelling, another cwd"):
            install_with_a_relative_home()
            before = recorded()
            self.assertTrue(before, "precondition: the run recorded its targets")

            code, out = reverse_from_elsewhere(Path("home"))
            self.assertEqual(code, 0)
            self.assertNotIn("gone ", out)
            self.assertTrue(list(placed.iterdir()),
                            "nothing was removed, so the targets are still on disk")
            self.assertEqual(recorded(), before,
                             "a target still on disk must stay recorded, or the tool has "
                             "orphaned what it created")

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

        # *args/**kwargs deliberately: this double asserts on `mode` alone, so pinning the
        # rest of install()'s arity here only means a new parameter breaks a test that has
        # no opinion about it (which is exactly what feat-0038's --with-hooks did).
        def recording_install(tools, mode, *args, **kwargs):
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


# Resolved profile membership, by name, pinned in one place (bug-0038).
#
# A profile's seed in install.py is not its membership: the seed is expanded over the
# sibling links found in skill bodies, so writing `[doc-sync](../doc-sync/SKILL.md)` into
# any skill body can move skills between profiles. `chore-0040` did exactly that while
# correcting a sentence, and the only symptom was `core` and `spine` reporting the same
# description-character total, which took real diagnosis to trace back to one link.
# Comparing sets by name fails with the skill that moved, instead of with two numbers.
#
# `all` is not listed: its seed is None, so its membership is every shipped skill, and a
# literal list here would have to be edited by every new skill. It is checked as that
# property instead, below.
#
# A legitimate profile change updates this constant once and nothing else. An
# unintended one is what it exists to catch, so read the named difference before editing:
# if a skill you did not mean to move appears here, a sibling link is the defect.
EXPECTED_PROFILE_MEMBERSHIP = {
    "core": {"init-worktracking", "pr-describe", "project-bootstrap"},
    "spine": {"doc-author", "doc-revise", "doc-sync", "fix-batch", "house-review",
              "init-worktracking", "new-task", "pr-describe", "project-bootstrap",
              "reconcile-worktrees", "review-depth", "spec-author", "spec-conformance",
              "spec-plan-readiness", "spec-quality", "test-author", "test-quality",
              "verifier-agent"},
}


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

    def test_resolved_profile_membership_is_what_the_seed_and_its_closure_say(self):
        # Scenario S-013, bug-0038: the oracle is the set of names, not its size. Every
        # other assertion in this class is arithmetic or ordering, and a one-skill move
        # satisfies all of them. This one names the skill that moved.
        shipped, _ = inst.partition_drafts(inst.discover_skills())
        for name, expected in EXPECTED_PROFILE_MEMBERSHIP.items():
            with self.subTest(profile=name):
                selected, _ = inst.resolve_profile(name, shipped)
                self.assertEqual({d.name for d in selected}, expected)

    def test_the_all_profile_is_every_shipped_skill(self):
        # Scenario S-013, bug-0038: `all` has no seed to close over, so its membership is
        # asserted as that property rather than pinned as a list that every new skill
        # would have to edit.
        shipped, _ = inst.partition_drafts(inst.discover_skills())
        selected, added = inst.resolve_profile("all", shipped)
        self.assertEqual({d.name for d in selected}, {d.name for d in shipped})
        self.assertEqual(added, [])

    def test_each_pinned_profile_holds_its_seed_and_is_closed_over_it(self):
        # Scenario S-013, bug-0038: the pinned sets are a tripwire, not the contract.
        # This is the contract they snapshot, so an edit to the constant cannot quietly
        # record a membership the resolver would never produce.
        shipped, _ = inst.partition_drafts(inst.discover_skills())
        by_name = {d.name: d for d in shipped}
        for name, expected in EXPECTED_PROFILE_MEMBERSHIP.items():
            with self.subTest(profile=name):
                seed = {n for n in inst.PROFILE_SEEDS[name] if n in by_name}
                self.assertLessEqual(seed, expected, "the seed must survive resolution")
                for member in sorted(expected):
                    reachable = inst.sibling_refs(by_name[member]) & set(by_name)
                    self.assertLessEqual(reachable, expected,
                                         f"{member} links outside {name}")

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
        # Over the shipped set, matching what install.py prints and why: a draft is placed
        # by no profile, so counting its description reports a budget no run can incur.
        # Passing everything discovered here diverged the moment the kit gained its first
        # draft skill, which is a defect in this expectation rather than in the installer.
        budgets = inst.profile_budgets(inst.partition_drafts(inst.discover_skills())[0])
        self.assertIn("Description budget:", out)
        self.assertIn(f"{budgets['core']} characters for this profile", out)
        for name, total in budgets.items():
            self.assertIn(f"{name}={total}", out)

    def test_a_smaller_profile_costs_fewer_description_characters(self):
        # Scenario S-014: the figure has to track the selection, or it is decoration.
        budgets = inst.profile_budgets(inst.partition_drafts(inst.discover_skills())[0])
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


def _fixture_skill(skills_dir, name, description, status=None, refs=(), body_extra=""):
    """Write a minimal, valid SKILL.md into a fixture skills tree.

    `status` is written as the nested block form the marker requires. The flow form
    (`metadata: {status: draft}`) is deliberately not used here: validate-skills.py
    rejects a plain frontmatter scalar containing ": ", so it is not a legal spelling
    in this kit and a fixture written that way would be testing a shape no skill can use.
    """
    d = skills_dir / name
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"name: {name}", f"description: {description}"]
    if status is not None:
        lines += ["metadata:", f"  status: {status}"]
    lines += ["---", "", f"# {name}", ""]
    lines += [f"Composes [`{r}`](../{r}/SKILL.md)." for r in refs]
    if body_extra:
        lines.append(body_extra)
    (d / "SKILL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


class SiblingLinkIsAProfileEdgeTests(unittest.TestCase):
    """bug-0038, under S-013: markdown link syntax in a skill body is a profile edge.

    Run against a fixture tree rather than `.agents/skills/`, because the behaviour under
    test is what happens when a body is *edited*, and editing a real skill to prove it
    would change the kit's own install footprint.

    The failure this pins is not that the closure is wrong. It is correct, and
    deliberately so. It is that an author writing the readable link form for a skill they
    only meant to name changes what the installer places, with no signal. `chore-0040`
    tripped it and was caught only because the collapse was large enough to break a
    character-budget invariant; a one-skill pull satisfies every budget assertion.

    Two of the links `chore-0040` added were free, because their targets were already in
    the closure by another path. That is the trap in
    `test_a_link_to_a_skill_already_in_the_closure_changes_nothing`: the same edit is
    sometimes free and sometimes doubles a profile, which is precisely why the author
    cannot tell by looking.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.skills.mkdir()
        self._real = (inst.SKILLS_DIR, inst.PROFILE_SEEDS, inst.MANIFEST)
        inst.SKILLS_DIR = self.skills
        inst.MANIFEST = self.root / "manifest.json"
        inst.PROFILE_SEEDS = {"core": ["alpha"], "all": None}

    def tearDown(self):
        inst.SKILLS_DIR, inst.PROFILE_SEEDS, inst.MANIFEST = self._real
        self._tmp.cleanup()

    def _members(self, profile="core"):
        selected, _ = inst.resolve_profile(profile, inst.discover_skills())
        return {d.name for d in selected}

    def _placed(self, profile="core"):
        home = self.root / f"home-{profile}-{len(list(self.root.iterdir()))}"
        with contextlib.redirect_stdout(io.StringIO()):
            inst.install(["claude"], "copy", home, False, profile)
        base = home / ".claude" / "skills"
        return {p.name for p in base.iterdir()} if base.is_dir() else set()

    def test_a_link_to_a_skill_outside_the_closure_moves_it_into_the_profile(self):
        # bug-0038: one added link, and the profile grows by the linked skill and
        # everything it reaches. The assertion is a named difference, so the report says
        # `omega` and `zeta` rather than reporting that a number changed.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked", refs=["beta"])
        _fixture_skill(self.skills, "beta", "does beta things when asked")
        _fixture_skill(self.skills, "omega", "does omega things when asked", refs=["zeta"])
        _fixture_skill(self.skills, "zeta", "does zeta things when asked")
        before = self._members()
        self.assertEqual(before, {"alpha", "beta"})

        # The edit an author makes for readability: a neighbour written as a link.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked",
                       refs=["beta", "omega"])
        after = self._members()
        self.assertEqual(after - before, {"omega", "zeta"})
        self.assertEqual(after, {"alpha", "beta", "omega", "zeta"})
        self.assertEqual(self._placed(), after, "the install footprint follows the link")

    def test_a_link_to_a_skill_already_in_the_closure_changes_nothing(self):
        # bug-0038, the trap: `gamma` is already reached through `beta`, so linking it
        # from `alpha` too is free. Sometimes free and sometimes doubling is the reason
        # the rule has to be written down rather than learned from a failing test.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked", refs=["beta"])
        _fixture_skill(self.skills, "beta", "does beta things when asked", refs=["gamma"])
        _fixture_skill(self.skills, "gamma", "does gamma things when asked")
        before = self._members()
        self.assertEqual(before, {"alpha", "beta", "gamma"})

        _fixture_skill(self.skills, "alpha", "does alpha things when asked",
                       refs=["beta", "gamma"])
        self.assertEqual(self._members(), before)

    def test_naming_a_sibling_in_backticks_creates_no_edge(self):
        # bug-0038: the form AGENTS.md tells an author to use when they mean to state
        # chain position rather than composition. If this ever starts creating an edge,
        # the documented escape hatch is gone and every prose mention becomes load-bearing.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked", refs=["beta"],
                       body_extra="Runs after `omega` in the chain, and does not compose it.\n")
        _fixture_skill(self.skills, "beta", "does beta things when asked")
        _fixture_skill(self.skills, "omega", "does omega things when asked")
        self.assertEqual(inst.sibling_refs(self.skills / "alpha"), {"beta"})
        self.assertEqual(self._members(), {"alpha", "beta"})


class DraftMarkerTests(unittest.TestCase):
    """Scenario S-015: a skill marked a draft is placed by no profile.

    Run against a fixture skill tree, deliberately, and not against `.agents/skills/`.
    No skill there carries a draft marker as of 2026-08-05 (`review-depth`, the draft
    this behaviour was filed on, was blessed by `feat-0035`), so a real-tree test would
    prove nothing, and marking a real skill a draft to make one pass would regress that
    blessing and falsify a shipped catalog row.

    The bug population is not the over-delivery this fixes. It is the inverse: a marker
    read too eagerly drops a shipped skill from every profile, and an adopter's next
    re-install simply stops refreshing it with no error anywhere. A count assertion
    cannot see that, so every placement oracle here compares the placed set by name
    against an exact expected set.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.skills.mkdir()

        self._real = (inst.SKILLS_DIR, inst.PROFILE_SEEDS, inst.MANIFEST)
        inst.SKILLS_DIR = self.skills
        inst.MANIFEST = self.root / "manifest.json"
        # alpha composes beta, so `core` can only be sound as {alpha, beta}: that is the
        # S-013 closure, and it has to keep working with a draft in the tree.
        inst.PROFILE_SEEDS = {"core": ["alpha"], "spine": ["alpha", "delta"], "all": None}

    def tearDown(self):
        inst.SKILLS_DIR, inst.PROFILE_SEEDS, inst.MANIFEST = self._real
        self._tmp.cleanup()

    def _tree(self):
        """alpha (unmarked) -> beta (explicitly shipped); delta shipped; gamma a draft."""
        _fixture_skill(self.skills, "alpha", "does alpha things when asked", refs=["beta"])
        _fixture_skill(self.skills, "beta", "does beta things when asked", status="shipped")
        _fixture_skill(self.skills, "gamma", "an unblessed draft nobody should receive",
                       status="draft")
        _fixture_skill(self.skills, "delta", "does delta things when asked")

    def _install(self, profile, home=None, dry=False):
        home = home or self.root / f"home-{profile}"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.install(["claude"], "copy", home, dry, profile)
        return code, buf.getvalue(), home

    @staticmethod
    def _placed(home):
        base = home / ".claude" / "skills"
        return {p.name for p in base.iterdir()} if base.is_dir() else set()

    def test_a_draft_skill_is_placed_by_no_profile(self):
        # Scenario S-015, and the whole point of the marker: `all` included.
        self._tree()
        expected = {"core": {"alpha", "beta"},
                    "spine": {"alpha", "beta", "delta"},
                    "all": {"alpha", "beta", "delta"}}
        for profile, names in expected.items():
            with self.subTest(profile=profile):
                code, _, home = self._install(profile)
                self.assertEqual(code, 0)
                self.assertEqual(self._placed(home), names)
                self.assertNotIn("gamma", self._placed(home))

    def test_an_unmarked_skill_and_an_explicitly_shipped_one_are_both_placed(self):
        # Scenario S-015 (negative), the inverse failure stated directly: absence of a
        # marker means shipped. `alpha` carries none and `beta` says `shipped`; both are
        # placed by the profile that asks for everything.
        self._tree()
        _, _, home = self._install("all")
        self.assertEqual(self._placed(home), {"alpha", "beta", "delta"})

    def test_the_marker_is_read_from_frontmatter_and_not_from_the_body(self):
        # Scenario S-015 (negative). Several skills in this kit discuss draft status in
        # prose, and validate-skills.py's DRAFT_STATUS_RE matches `status: draft` anywhere
        # in the file. Reading the body the same way would drop a shipped skill from every
        # profile with no signal, which is the failure worth protecting against here.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked",
                       body_extra="This skill writes `status: draft` into every spec it "
                                  "authors, and the spec is a draft until approved.\n")
        self.assertEqual(inst.status_of(self.skills / "alpha"), "")
        _, _, home = self._install("all")
        self.assertEqual(self._placed(home), {"alpha"})

    def test_status_of_reads_each_marker_form(self):
        # Scenario S-015 at the lowest faithful layer. The unrecognised value is the
        # deliberate case: it reads as shipped, so a typo over-delivers rather than
        # silently withholding a skill.
        self._tree()
        _fixture_skill(self.skills, "typo", "a marker nobody spelled right", status="drafft")
        _fixture_skill(self.skills, "cased", "a marker in the wrong case", status="Draft")
        self.assertEqual(inst.status_of(self.skills / "alpha"), "")
        self.assertEqual(inst.status_of(self.skills / "beta"), "shipped")
        self.assertEqual(inst.status_of(self.skills / "gamma"), "draft")
        self.assertEqual(inst.status_of(self.skills / "typo"), "drafft")
        self.assertEqual(inst.status_of(self.skills / "cased"), "draft")

    def test_profile_closure_still_holds_with_a_draft_present(self):
        # Scenarios S-013 and S-015 together: excluding drafts must not weaken the
        # closure. Asserted against what actually landed on disk, so it runs through the
        # draft-aware resolution rather than around it.
        self._tree()
        names = {d.name for d in inst.discover_skills()}
        for profile in inst.PROFILE_SEEDS:
            with self.subTest(profile=profile):
                _, _, home = self._install(profile)
                placed = self._placed(home)
                self.assertTrue(placed, "precondition: the profile placed something")
                for name in placed:
                    missing = (inst.sibling_refs(self.skills / name) & names) - placed
                    self.assertEqual(missing, set(),
                                     f"{profile} shipped {name} without {sorted(missing)}")

    def test_a_profile_that_would_ship_a_reference_to_a_draft_places_nothing(self):
        # Scenario S-015: the case the closure and the marker disagree about. Dropping
        # the reference reintroduces the dangling sibling S-013 prevents, and following
        # it defeats the marker, so the run refuses and names both skills.
        _fixture_skill(self.skills, "alpha", "does alpha things when asked", refs=["gamma"])
        _fixture_skill(self.skills, "gamma", "an unblessed draft nobody should receive",
                       status="draft")
        code, out, home = self._install("all")
        self.assertEqual(code, 2)
        self.assertEqual(self._placed(home), set(), "nothing may be placed when refused")
        self.assertFalse((home / ".claude" / "rules").exists())
        self.assertIn("alpha", out)
        self.assertIn("'gamma'", out)
        self.assertIn("Refusing to place anything", out)

    def test_a_profile_seed_naming_a_draft_places_nothing(self):
        # Scenario S-015: the other silent resolution. The seed is filtered against the
        # shipped set, so without this the requested skill vanishes without a word.
        self._tree()
        inst.PROFILE_SEEDS = {"core": ["alpha", "gamma"], "all": None}
        code, out, home = self._install("core")
        self.assertEqual(code, 2)
        self.assertEqual(self._placed(home), set())
        self.assertIn("profile seed names 'gamma'", out)

    def test_the_run_names_the_drafts_it_held_back(self):
        # Scenario S-015: a skill silently absent from an install is the failure mode
        # this whole change is about, so the run has to say what it withheld. The
        # reported totals count the draft as discovered but not placed.
        self._tree()
        _, out, _ = self._install("all")
        self.assertIn("gamma", out)
        self.assertIn("excluded from every profile", out)
        self.assertIn("3 of 4 skill(s)", out)

    def test_a_draft_costs_no_profile_any_description_budget(self):
        # Scenario S-014 under S-015: the budget has to track what is placed. Counting a
        # draft would report a cost no run can incur.
        self._tree()
        long_draft = "d" * 400
        _fixture_skill(self.skills, "gamma", long_draft, status="draft")
        shipped, drafts = inst.partition_drafts(inst.discover_skills())
        self.assertEqual([d.name for d in drafts], ["gamma"])
        budgets = inst.profile_budgets(shipped)
        self.assertEqual(budgets["all"], sum(len(inst.description_of(d)) for d in shipped))
        _, out, _ = self._install("all")
        self.assertIn(f"all={budgets['all']}", out)
        self.assertNotIn(str(len(long_draft) + budgets["all"]), out)


class StalenessCheckTests(unittest.TestCase):
    """chore-0031: whether an installed set still matches the kit it came from.

    The defect is measured, not hypothetical. The globally installed `fix-batch` on the
    author's machine on 2026-08-06 was a wave-2-era snapshot missing two Step 3 items and
    the entire delegate report contract, and an agent invoking the skill by name got the
    older procedure. Nothing could have said so: a stale copy is a valid skill that passes
    `validate-skills.py`, passes Anthropic's validator, and reads correctly.

    So every oracle here is an exact one: an exit code, the offending skill and file named
    in the output, or the persisted digest map itself. A "the check ran" assertion would
    reproduce the silence rather than protect against it.

    Run against a fixture skills tree and a fixture rules module, deliberately, because
    both directions of divergence have to be reachable: an installed file edited after
    placement, and a *source* file edited after placement. The second is the actual bug and
    it cannot be staged against `.agents/`, which the suite must not mutate.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.rules = self.root / "rules"
        self.skills.mkdir()
        self.rules.mkdir()
        self.home = self.root / "home"

        self._real = (inst.SKILLS_DIR, inst.RULES_DIR, inst.PROFILE_SEEDS, inst.MANIFEST)
        inst.SKILLS_DIR = self.skills
        inst.RULES_DIR = self.rules
        inst.MANIFEST = self.root / "manifest.json"
        inst.PROFILE_SEEDS = {"core": ["alpha"], "spine": ["alpha"], "all": None}

        _fixture_skill(self.skills, "alpha", "does alpha things when asked")
        (self.skills / "alpha" / "templates").mkdir()
        (self.skills / "alpha" / "templates" / "report.md").write_text(
            "# report\n\nthe supporting file a stale install leaves behind\n",
            encoding="utf-8")
        _fixture_skill(self.skills, "beta", "does beta things when asked")
        (self.rules / "house-style.md").write_text(
            "# house style\n\nno em-dashes.\n", encoding="utf-8")

    def tearDown(self):
        (inst.SKILLS_DIR, inst.RULES_DIR,
         inst.PROFILE_SEEDS, inst.MANIFEST) = self._real
        self._tmp.cleanup()

    def _install(self, mode="copy", home=None):
        home = self.home if home is None else home
        with contextlib.redirect_stdout(io.StringIO()):
            code = inst.install(["claude"], mode, home, False, "all")
        self.assertEqual(code, 0, "precondition: the install itself must succeed")
        return home

    def _check(self, home=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.check(self.home if home is None else home)
        return code, buf.getvalue()

    def _entries(self):
        return json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]

    def _entry(self, name):
        return next(e for e in self._entries() if e["name"] == name)

    def _installed(self, *parts):
        return self.home.joinpath(".claude", "skills", *parts)

    @staticmethod
    def _status(out, name):
        """The status word the check reported for one entry, or None if it reported none.

        The report is one line per entry, `<status> <tool> <name>  <message>`, so this
        reads the verdict for a named entry rather than searching the whole output for a
        word. A substring assertion over the report would pass on a message that merely
        mentions the word, which is how a check that reports nothing useful still looks
        green.
        """
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == name:
                return parts[0]
        return None

    @staticmethod
    def _message(out, name):
        """The message the check reported for one entry, or None if it reported none.

        The sibling of `_status`, over the same `<status> <tool> <name>  <message>` line,
        and load-bearing for the same reason (bug-0020). A run whose unknown entries are a
        mix prints one remedy per entry, so an `assertIn` over the whole report is answered
        by whichever entry happens to carry the wanted sentence and says nothing at all
        about the entry under test.
        """
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == name:
                return " ".join(parts[3:])
        return None

    @staticmethod
    def _summary(out):
        """Everything the check printed after its per-entry lines, or "" if it printed none.

        Bounded to the tail on purpose, for `_message`'s reason one level up: the per-entry
        lines carry remedies of their own, so an assertion over the whole report cannot
        tell a summary that names the right remedy from an entry line that happens to.
        The counts line is the boundary, and it is the one line that always ends the report.
        """
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if "error(s)." in line:
                return "\n".join(lines[i + 1:])
        return ""

    def test_an_install_records_a_digest_for_every_file_it_places(self):
        # The baseline, at the lowest layer, and the reason it is per file rather than per
        # skill: a skill is a directory, and a stale `templates/report.md` is exactly as
        # silent as a stale `SKILL.md`. A per-skill digest would satisfy "records
        # something" and miss half the bug population.
        self._install()
        digests = self._entry("alpha")["digests"]
        self.assertEqual(sorted(digests), ["SKILL.md", "templates/report.md"])
        expected = hashlib.sha256(
            (self.skills / "alpha" / "templates" / "report.md").read_bytes()).hexdigest()
        self.assertEqual(digests["templates/report.md"], expected)

    def test_a_freshly_installed_tree_reports_current_and_exits_zero(self):
        # The check has to be quiet when nothing is wrong, or nobody will run it twice.
        self._install()
        code, out = self._check()
        self.assertEqual(code, 0)
        self.assertEqual([self._status(out, n) for n in ("alpha", "beta", "rules")],
                         ["ok", "ok", "ok"])
        self.assertIn("0 diverged", out)
        self.assertIn("0 unknown", out)

    def test_a_skill_revised_in_the_kit_after_the_install_is_named_and_exits_non_zero(self):
        # The measured defect itself: the source moves on, the installed snapshot does not,
        # and today nothing says so. The oracle names the skill and the file, because a
        # non-zero exit that does not say what went stale costs the reader the whole
        # investigation (the same reason check-provenance.py names the drifted source).
        self._install()
        source = self.skills / "alpha" / "SKILL.md"
        source.write_text(source.read_text(encoding="utf-8")
                          + "\nA step added after the install.\n", encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 1)
        self.assertEqual(self._status(out, "alpha"), "diverged")
        self.assertIn("SKILL.md:", out, "the report must name the file, not only the skill")
        self.assertEqual(self._status(out, "beta"), "ok",
                         "an untouched skill must not be swept up in the report")

    def test_a_stale_supporting_file_is_reported_when_the_skill_md_still_matches(self):
        # The half of the bug population a per-skill or SKILL.md-only digest would miss.
        self._install()
        source = self.skills / "alpha" / "templates" / "report.md"
        source.write_text("# report\n\nrewritten after the install\n", encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 1)
        self.assertEqual(self._status(out, "alpha"), "diverged")
        self.assertIn("templates/report.md", out)

    def test_a_manifest_written_before_this_change_reports_unknown_not_current(self):
        # The persisted-format risk. An older manifest carries no digests, and reporting
        # those entries as current would be a clean result for an unknown state, which is
        # the failure this check exists to remove one level up. Staged by stripping the key
        # from a real manifest, so the fixture is the actual older format rather than a
        # hand-written guess at it.
        self._install()
        older = {"entries": [{k: v for k, v in e.items() if k != "digests"}
                             for e in self._entries()]}
        inst.MANIFEST.write_bytes(json.dumps(older, indent=2).encode("utf-8"))

        code, out = self._check()
        self.assertEqual(code, 2, "an unanswerable check must not exit zero")
        self.assertEqual({self._status(out, n) for n in ("alpha", "beta", "rules")},
                         {"unknown"},
                         "no entry may read as current without a recorded baseline")
        self.assertIn("re-install to establish a baseline", out.lower())

    def _unknown_run(self):
        """A check over a manifest carrying no digests at all, as bug-0020 describes it.

        Staged exactly like the test above, by stripping the key from a real manifest, so
        every entry is unknown and the rules entry among them is the adopted one.
        """
        self._install()
        older = {"entries": [{k: v for k, v in e.items() if k != "digests"}
                             for e in self._entries()]}
        inst.MANIFEST.write_bytes(json.dumps(older, indent=2).encode("utf-8"))
        return self._check()

    def test_an_unrecorded_rules_entry_names_replace_adopted_rather_than_re_install(self):
        # bug-0020. Re-install is the right remedy for a derived entry and, since bug-0018,
        # a no-op for this one: a re-install of an unrecorded rules module preserves every
        # file and records nothing, so the adopter follows the instruction, nothing changes,
        # and the same instruction prints again. `--replace-adopted` is the one route that
        # establishes a baseline here, and the message that has to name it is this entry's
        # own, read per entry: the derived entries in this very run print the old sentence.
        code, out = self._unknown_run()
        self.assertEqual(code, 2, "the state is still unanswerable, so the exit code holds")
        self.assertEqual(self._status(out, "rules"), "unknown")
        self.assertIn("--replace-adopted", self._message(out, "rules"))

    def test_an_unrecorded_derived_entry_still_says_re_install(self):
        # The other half, and the reason the fix is name-scoped rather than a rewrite of the
        # shared sentence: re-installing a skill directory does establish a baseline, so
        # swapping this remedy for the adopted one would trade one wrong instruction for
        # another. Read per entry for the same reason as above, in the opposite direction.
        code, out = self._unknown_run()
        self.assertEqual(self._status(out, "alpha"), "unknown")
        message = self._message(out, "alpha")
        self.assertIn("Re-install to establish a baseline", message)
        self.assertNotIn("--replace-adopted", message)

    def test_the_run_summary_names_both_remedies_when_the_unknown_entries_are_a_mix(self):
        # The summary prints one line per status, not per kind, so a run whose unknown
        # entries include the rules module has to say both things or mis-advise half of
        # them. Bounded to the tail after the counts line, because the per-entry lines above
        # it already name both remedies and would answer either assertion on their own.
        code, out = self._unknown_run()
        summary = self._summary(out)
        self.assertIn("Re-install to establish one.", summary)
        self.assertIn("--replace-adopted", summary)
        self.assertEqual(code, 2)

    def test_an_adopter_edited_rules_file_is_not_reported_as_divergence(self):
        # The noise case, and the reason it is decided rather than mechanical. A lens is the
        # one file an adopter is invited to rewrite (build-adapters.md S-010 and S-014), so
        # an unconditional "differs from source" here fires on every run forever for anyone
        # who accepted the invitation, and a check that cries wolf is a check nobody runs.
        self._install()
        (self.home / ".claude" / "rules" / "house-style.md").write_text(
            "# house style\n\nmy own rules, deliberately.\n", encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 0)
        self.assertEqual(self._status(out, "rules"), "ok")
        self.assertIn("0 diverged", out)

    def test_a_rules_file_the_kit_revised_since_the_install_is_reported_as_revised(self):
        # The other half of the same decision. The adopter's copy is theirs, so what is
        # worth telling them is that the copy they were handed has moved, which is
        # check-provenance.py's question and is answerable only from the recorded baseline.
        # Exit-neutral on purpose: it is news, not a fault.
        self._install()
        (self.rules / "house-style.md").write_text(
            "# house style\n\nno em-dashes, and sentence-case headings.\n",
            encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 0, "news about an adopted file is not a failure")
        self.assertEqual(self._status(out, "rules"), "revised")
        self.assertIn("house-style.md", out)

    def test_an_installed_target_removed_by_hand_is_reported_rather_than_passing(self):
        # Absence is divergence too. A check that only compares files it can open would
        # report a clean run for a home the skill is simply gone from.
        self._install()
        shutil.rmtree(self._installed("alpha"))

        code, out = self._check()
        self.assertEqual(code, 1)
        self.assertEqual(self._status(out, "alpha"), "diverged")
        self.assertIn("gone", out)

    def test_a_rules_file_deleted_from_the_install_is_named_and_exits_non_zero(self):
        # bug-0022, the reproduction itself. The adopted comparison runs the recorded
        # baseline against the source and never opens the installed tree, so a lens that is
        # simply *gone* was reported `ok` at exit 0. Whole-directory absence is caught a
        # branch earlier; per-file absence was caught by nothing. The file deleted here is
        # house-review's entire rubric, which is the incident this kit cites more than any
        # other, and the installer's very next run already says the file is missing.
        (self.rules / "review-quality.md").write_text(
            "# review quality\n\nblocker, major, minor, nit.\n", encoding="utf-8")
        self._install()
        (self.home / ".claude" / "rules" / "review-quality.md").unlink()

        code, out = self._check()
        self.assertEqual(code, 1, "a lens missing from the install must not exit zero")
        self.assertEqual(self._status(out, "rules"), "diverged")
        self.assertIn("review-quality.md", out,
                      "the report must name the file, not only the module")

    def test_only_the_missing_lens_is_named_and_an_edited_one_is_not(self):
        # The failure direction bug-0022's risk section names: a check that swept an edited
        # lens into the same report would be noise on every run for exactly the people the
        # adopted exemption was written for. Absence and edit are different claims, and only
        # the first is being added.
        (self.rules / "review-quality.md").write_text(
            "# review quality\n\nblocker, major, minor, nit.\n", encoding="utf-8")
        self._install()
        (self.home / ".claude" / "rules" / "house-style.md").write_text(
            "# house style\n\nmy own rules, deliberately.\n", encoding="utf-8")
        (self.home / ".claude" / "rules" / "review-quality.md").unlink()

        _, out = self._check()
        named = [l for l in out.splitlines() if "gone from the installed module" in l]
        self.assertEqual(len(named), 1, f"exactly one file is missing, got {named}")
        self.assertIn("review-quality.md", named[0])

    def test_a_rules_file_the_adopter_added_is_ignored_by_the_check(self):
        # Ignored in both directions. The install side is pinned by
        # `test_a_lens_the_adopter_added_beside_the_kits_is_not_deleted`: it is neither
        # refreshed nor removed nor recorded. This is the check side of the same rule: a
        # file absent from the recorded baseline was placed by nobody, so it is neither
        # divergence nor news, and the new absence question must not read it backwards as
        # "in the install, absent from the record".
        self._install()
        (self.home / ".claude" / "rules" / "my-own-lens.md").write_text(
            "# my own lens\n\nrules the kit never shipped.\n", encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 0)
        self.assertEqual(self._status(out, "rules"), "ok")
        self.assertNotIn("my-own-lens.md", out)

    def test_a_missing_lens_and_a_moved_source_are_reported_in_one_entry(self):
        # The two questions are independent and the entry carries one status word, so the
        # actionable one wins and the other is not dropped on the floor. Reporting only the
        # status would silently lose whichever answer lost the tie, which is the partial
        # result A6 forbids.
        (self.rules / "review-quality.md").write_text(
            "# review quality\n\nblocker, major, minor, nit.\n", encoding="utf-8")
        self._install()
        (self.home / ".claude" / "rules" / "review-quality.md").unlink()
        (self.rules / "house-style.md").write_text(
            "# house style\n\nno em-dashes, and sentence-case headings.\n",
            encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 1, "the fault outranks the news")
        self.assertEqual(self._status(out, "rules"), "diverged")
        self.assertIn("review-quality.md", out)
        self.assertIn("house-style.md", out, "the upstream move must still be reported")

    def test_an_unanswerable_entry_still_outranks_a_missing_lens(self):
        # The documented precedence, unchanged: "could not answer" outranks "diverged",
        # because the first says the report itself cannot be trusted. Staged by stripping
        # one skill entry's digests while a rules file is missing, so both verdicts are live
        # in the same run.
        (self.rules / "review-quality.md").write_text(
            "# review quality\n\nblocker, major, minor, nit.\n", encoding="utf-8")
        self._install()
        (self.home / ".claude" / "rules" / "review-quality.md").unlink()
        entries = self._entries()
        for e in entries:
            if e["name"] == "alpha":
                e.pop("digests")
        inst.MANIFEST.write_text(json.dumps({"entries": entries}, indent=2),
                                 encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 2, "an unanswerable entry outranks a diverged one")
        self.assertEqual(self._status(out, "alpha"), "unknown")
        self.assertEqual(self._status(out, "rules"), "diverged")

    def test_the_check_never_rewrites_the_install_or_the_record(self):
        # The decision this shares with feat-0043: detect and report, never overwrite. An
        # adopter may have edited an installed file deliberately, and a check that "fixed"
        # it would destroy that without asking. Asserted over bytes on both sides, since a
        # silent repair is exactly what would otherwise make the divergence test go green.
        self._install()
        target = self._installed("alpha", "SKILL.md")
        target.write_bytes(b"---\nname: alpha\ndescription: mine now\n---\n")
        before_target = target.read_bytes()
        before_manifest = inst.MANIFEST.read_bytes()

        code, _ = self._check()
        self.assertEqual(code, 1)
        self.assertEqual(target.read_bytes(), before_target)
        self.assertEqual(inst.MANIFEST.read_bytes(), before_manifest)

    def test_the_check_is_scoped_to_the_home_it_is_given(self):
        # One manifest serves every home installed to from this checkout (S-012). Without
        # scoping, a diverged throwaway home would fail a check of the real one, which is
        # the same class of defect bug-0003 fixed for --uninstall.
        other = self.root / "other-home"
        self._install()
        self._install(home=other)
        shutil.rmtree(other / ".claude" / "skills" / "alpha")

        code, out = self._check()
        self.assertEqual(code, 0, "another home's divergence must not fail this one")
        self.assertNotIn(str(other), out)

    @unittest.skipUnless(SYMLINKS_WORK, "this platform or account cannot create symlinks")
    def test_a_symlinked_target_cannot_be_stale_and_is_not_reported(self):
        # The POSIX default. A link *is* its source, so digesting it against the source
        # would always agree, but a source edited after the install would still leave the
        # recorded digest behind. Reporting that as divergence would fire on every POSIX
        # install of a kit under development: noise, and wrong.
        self._install(mode="symlink")
        source = self.skills / "alpha" / "SKILL.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nrevised.\n",
                          encoding="utf-8")

        code, out = self._check()
        self.assertEqual(code, 0)
        self.assertEqual(self._status(out, "alpha"), "linked")
        self.assertNotIn("DIVERGED", out)

    def test_the_check_is_reachable_from_the_command_line(self):
        # The entrypoint layer: the flag has to be wired to the function, and `--home` has
        # to reach it, or every instruction in INSTALL.md is wrong.
        self._install()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--check", "--home", str(self.home)])
        self.assertEqual(code, 0)
        self.assertIn("current", buf.getvalue())

    def test_asking_to_check_and_uninstall_at_once_is_refused_and_removes_nothing(self):
        # Either precedence silently drops half the request, and one of those halves
        # deletes files.
        self._install()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--check", "--uninstall", "--home", str(self.home)])
        self.assertEqual(code, 2)
        self.assertTrue(self._installed("alpha").is_dir(),
                        "a refused invocation must not remove anything")

    def test_checking_a_home_with_nothing_recorded_does_not_report_it_as_current(self):
        # S-005's shape, one level up: a deleted record makes previous copies unmanaged, so
        # a check that found no entries has learned nothing about what is on disk. Exiting
        # zero there would answer "current" for a home it never looked at.
        code, out = self._check(self.root / "never-installed")
        self.assertEqual(code, 2)
        self.assertIn("nothing can be checked", out)


class HookRegistrationTests(unittest.TestCase):
    """feat-0038: the settings block a user pastes to activate the hooks.

    The defect worth protecting against is a registration that parses fine, looks right,
    and never runs. Found by dogfooding on Windows: the first draft hardcoded `python3`,
    which there resolves to the Microsoft Store app-execution alias, prints an install
    advertisement, and exits without executing the hook. Nothing surfaces that failure,
    so the guardrail is simply absent forever.
    """

    def test_the_interpreter_matches_the_platform(self):
        expected = "python" if os.name == "nt" else "python3"
        self.assertEqual(inst.hook_interpreter(), expected)

    def test_the_registration_names_a_runnable_interpreter(self):
        block = inst.claude_registration(Path("/tmp/home"))
        command = json.loads(block)["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith(inst.hook_interpreter() + " "))
        if os.name == "nt":
            # The specific regression: `python3 ` as the command prefix is the broken form.
            self.assertFalse(command.startswith("python3 "))

    def test_the_registration_path_is_absolute_and_has_no_tilde(self):
        # Whether a tilde is expanded depends on how the harness spawns the command, and a
        # registration that silently does not run is the worst outcome available here.
        block = inst.claude_registration(Path("/tmp/home"))
        command = json.loads(block)["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        self.assertNotIn("~", command)
        self.assertIn("delegation-reminder.py", command)

    def test_the_registration_is_valid_json_the_user_can_paste(self):
        # It is printed for a human to merge into settings.json. If it does not parse,
        # every downstream instruction in INSTALL.md is wrong.
        block = inst.claude_registration(Path("/tmp/home"))
        parsed = json.loads(block)
        entry = parsed["hooks"]["PostToolUse"][0]
        self.assertEqual(entry["hooks"][0]["type"], "command")
        self.assertTrue(entry["matcher"])
        # Deliberately NOT asserting the matcher's exact text here. Pinning the string in
        # this file is what broke when `Agent` was added to the hook: the code and two of
        # the three wirings were updated and this assertion was left behind, failing for a
        # change that was correct. What the matcher must actually satisfy is that it
        # covers the hook's own tool set, and that belongs in one place across all the
        # wirings: see WiringConsistencyTests in tests/test_hooks.py.


class RegistrationCarriesTheEventTests(unittest.TestCase):
    """feat-0046: the registration builder must not hardcode one lifecycle event.

    HOOK_REGISTRATIONS carried (script, matcher) while claude_registration() emitted the
    entries under a hardcoded PostToolUse. Every hook in the module was PostToolUse, so
    nothing surfaced it. A hook on any other event would have been placed by --with-hooks
    and never registered: installed, correct-looking, and doing nothing, which is the
    failure this module was already bitten by twice while it was being built.

    These tests exist so the event dimension cannot quietly collapse back.
    """

    def test_every_registration_entry_carries_an_event(self):
        for entry in inst.HOOK_REGISTRATIONS:
            with self.subTest(entry=entry[0]):
                self.assertEqual(3, len(entry),
                                 "expected (script, event, matcher)")
                self.assertTrue(entry[1], "the event must not be empty")

    def test_a_session_start_hook_is_registered_under_session_start(self):
        parsed = json.loads(inst.claude_registration(Path("/tmp/home")))
        self.assertIn("SessionStart", parsed["hooks"],
                      "a SessionStart hook must not be filed under PostToolUse")
        entry = parsed["hooks"]["SessionStart"][0]
        self.assertEqual("startup", entry["matcher"])
        self.assertIn("skill-reachability-reminder.py", entry["hooks"][0]["command"])

    def test_the_existing_post_tool_use_hooks_are_unchanged(self):
        # The widening must not disturb what already worked. Both hooks stay under
        # PostToolUse, in order.
        parsed = json.loads(inst.claude_registration(Path("/tmp/home")))
        commands = [e["hooks"][0]["command"] for e in parsed["hooks"]["PostToolUse"]]
        self.assertEqual(2, len(commands))
        self.assertIn("delegation-reminder.py", commands[0])
        self.assertIn("spec-conformance-gate.py", commands[1])

    def test_every_registered_script_exists_in_the_module(self):
        # A registration naming a script that is not there produces an entry that can
        # never fire, which is the same silence from the other direction.
        for script, _event, _matcher in inst.HOOK_REGISTRATIONS:
            with self.subTest(script=script):
                self.assertTrue((inst.HOOKS_DIR / script).is_file())

    def test_every_hook_in_the_module_is_registered(self):
        # The docstring's stated property: a hook added without an entry here shows up as
        # a missing entry rather than as a hook that was placed and never fires.
        registered = {script for script, _e, _m in inst.HOOK_REGISTRATIONS}
        present = {p.name for p in inst.discover_hooks()}
        self.assertEqual(present, registered,
                         "every hook in .agents/hooks/ needs a registration entry")


class HookPlacementTests(unittest.TestCase):
    """chore-0067: what `--with-hooks` actually places, records, and reverses.

    **Mostly characterization, not acceptance.** `docs/spec/install.md` still says nothing
    about hooks: `grep -in hook docs/spec/install.md` returns nothing, so there is no
    approved scenario to derive from and no test here carries an `S-NNN` id. Most
    assertions below pin the code's current observable behaviour so a change to it is
    deliberate rather than silent.

    chore-0067 wrote two of those pins over behaviour it suspected was wrong. bug-0048
    fixed one of them and the three opencode-and-claude activation tests at the foot of
    this class are acceptance of that fix rather than characterization, each saying so
    where it sits. The other, `test_every_installable_tool_has_a_hook_path`, is still a
    pin over a latent seam and bug-0048 deliberately left it alone.

    Why the placement path is worth its own class when `HookRegistrationTests` above
    already covers the printed registration thoroughly: the registration is the step
    *after* this one. Until this class existed, `grep -rn with_hooks tests/` returned
    nothing, so copying the module into `<home>/<subpath>`, recording its manifest entry,
    and reversing both were exercised by no test and by no gate. That matters more than an
    ordinary coverage gap for two reasons AGENTS.md and the task both name. The module is
    the only thing the kit ships that runs inside an adopter's session. And the manifest
    entry it writes is the baseline `install.py --check` and `install-currency-reminder.py`
    both measure later answers against, so a defect here is silent by construction: it
    produces a wrong baseline rather than an error.

    The manifest assertions are therefore the load-bearing half, not the files on disk.
    A test that checked only for placed files would pass against a run that recorded a
    digest for five of the six files in the module, which is the exact shape the task
    reported seeing in a real manifest.

    Fixture idiom mirrors `InstallAcceptanceTests` deliberately rather than inventing a
    second one: a temporary home, `inst.MANIFEST` redirected away from the real
    repository, and the real `.agents/hooks/` as the source, because the module actually
    shipping untested is the thing under test.
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

    # `core` rather than `all`: the profile axis has no bearing on hook placement, and the
    # smallest profile keeps a class that installs repeatedly cheap.
    def _install(self, tools=("claude",), mode="copy", dry=False, with_hooks=True):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.install(list(tools), mode, self.home, dry, "core", with_hooks)
        return code, buf.getvalue()

    def _uninstall(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.uninstall(self.home, False)
        return code, buf.getvalue()

    def _entries(self, name="hooks"):
        recorded = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        return [e for e in recorded if e.get("name") == name]

    @staticmethod
    def _module_files():
        """Every file the hooks module ships, read independently of `install.py`.

        Deliberately not `inst.digest_tree` or `inst.discover_hooks`. Both are code this
        class is checking: an expectation built from `digest_tree` would move with the
        record if it ever dropped a file, which is the one failure these tests exist to
        catch, and `discover_hooks` answers a narrower question (the `.py` hooks) than the
        one placement answers (the module).

        The two exclusions mirror what `_copy` refuses to place, so the byte-cache the
        test suite creates the moment it imports a hook is not counted as a missing file.
        """
        return {p.relative_to(inst.HOOKS_DIR).as_posix():
                hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(inst.HOOKS_DIR.rglob("*"))
                if p.is_file() and p.suffix != ".pyc"
                and "__pycache__" not in p.relative_to(inst.HOOKS_DIR).parts}

    def test_the_module_lands_under_each_tools_own_hook_path(self):
        # The placement half. Both tools in one run, because the two land at different
        # subpaths (`.claude/hooks` against `.agents/hooks`) and a test covering only the
        # Claude Code one would pass against a map that had lost its opencode row.
        code, _ = self._install(tools=("claude", "opencode"))
        self.assertEqual(code, 0)
        expected = self._module_files()
        self.assertTrue(expected, "precondition: the kit ships a hooks module")
        for tool, subpath in (("claude", Path(".claude") / "hooks"),
                              ("opencode", Path(".agents") / "hooks")):
            with self.subTest(tool=tool):
                landed = self.home / subpath
                self.assertTrue(landed.is_dir(), f"{tool} received no hooks module")
                self.assertEqual(
                    {p.relative_to(landed).as_posix():
                     hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(landed.rglob("*")) if p.is_file()},
                    expected,
                    "the placed module must be the kit's module, byte for byte")

    def test_the_placement_is_recorded_with_a_digest_for_every_file_in_the_module(self):
        # The load-bearing half, and the one assertion that fails against the manifest
        # shape the task reported: digests for five of six files, the sixth being the
        # hook whose own job is reporting a stale install.
        #
        # Compared against digests this test computed itself, not against the count, so a
        # record holding the right number of wrong digests fails too.
        self._install(tools=("claude", "opencode"))
        expected = self._module_files()
        entries = self._entries()
        self.assertEqual(2, len(entries), "one hooks entry per tool that received it")
        for entry in entries:
            with self.subTest(tool=entry["tool"]):
                self.assertEqual(str(inst.HOOKS_DIR), entry["source"])
                # Resolved on both sides deliberately. install() resolves the home it
                # is given, so the manifest always records a resolved absolute path,
                # and comparing it against an unresolved composition is a string test
                # that happens to hold only where the two spellings coincide. They do
                # not on a macOS runner, where /var is a symlink to /private/var, nor
                # on a Windows runner reached by its 8.3 short name.
                self.assertEqual(
                    str((self.home / inst.HOOK_SUBPATHS[entry["tool"]]).resolve()),
                    entry["target"])
                self.assertEqual(expected, entry["digests"],
                                 "every file in the module needs a recorded baseline; a "
                                 "file missing here is a later --check that cannot see it")

    def test_the_module_is_recorded_under_one_name_rather_than_per_file(self):
        # The detail the task's implementation notes single out as the one a test is most
        # likely to get wrong. A skill is recorded per skill directory; the whole hooks
        # module is recorded as a single entry named `hooks`, with the per-file detail
        # living inside that entry's `digests` map rather than in sibling entries.
        self._install()
        self.assertEqual(1, len(self._entries()))
        recorded = json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]
        self.assertEqual(
            [], [e for e in recorded if e.get("name", "").endswith(".py")],
            "no per-hook-file entry: the module is one record, digested per file")

    def test_more_files_land_than_the_run_counts_as_hooks(self):
        # Pins a distinction that reads like an off-by-one to anyone tidying up. The
        # summary counts `discover_hooks()`, which is the `*.py` hooks; placement copies
        # the module directory, so its README and .gitkeep land and are digested too.
        # Both are correct and they are answers to different questions, so a change that
        # collapsed them would be a decision rather than a cleanup.
        _code, out = self._install()
        hooks = inst.discover_hooks()
        self.assertIn(f"plus {len(hooks)} hook(s).", out)
        landed = sorted(p.name for p in (self.home / ".claude" / "hooks").iterdir())
        self.assertGreater(len(landed), len(hooks),
                           "the module ships more than its hooks, and all of it is placed")
        self.assertIn("README.md", landed)

    def test_without_the_flag_nothing_is_placed_and_nothing_is_recorded(self):
        # The negative control. Without it every assertion above would still pass against
        # an installer that placed the hooks module unconditionally, which is the opposite
        # of the opt-in rule AGENTS.md states for the one thing the kit runs in a session.
        code, out = self._install(tools=("claude", "opencode"), with_hooks=False)
        self.assertEqual(code, 0)
        self.assertFalse((self.home / ".claude" / "hooks").exists())
        self.assertFalse((self.home / ".agents" / "hooks").exists())
        self.assertEqual([], self._entries())
        self.assertNotIn("hook(s).", out)

    def test_a_dry_run_places_no_hooks_and_records_none(self):
        # S-006's shape applied to the opt-in module. The preview must not be the one
        # command that writes into a session-executing directory.
        code, out = self._install(dry=True)
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse(self.home.exists())
        self.assertFalse(inst.MANIFEST.exists())

    def test_a_second_run_updates_the_hooks_rather_than_conflicting(self):
        # S-003's shape applied to the hooks entry, and the property `run-checks.py`'s
        # install cycle depends on: that gate now runs the flag twice, so a hooks
        # placement that reported CONFLICT against its own previous run would fail the
        # acceptance command rather than the far quieter thing it did before.
        self._install()
        code, out = self._install()
        self.assertEqual(code, 0)
        hook_lines = [line for line in out.splitlines() if " hooks  ->" in line]
        self.assertTrue(hook_lines, "precondition: the second run reported the hooks")
        self.assertTrue(all("updated" in line for line in hook_lines), hook_lines)
        self.assertNotIn("CONFLICT", out)

    def test_uninstall_reverses_the_placement_and_drops_the_record(self):
        # S-007's shape applied to the hooks entry. Reversal is manifest-driven and needs
        # no flag of its own: `main()` returns from the uninstall branch before it ever
        # reads `--with-hooks`, so the recorded entry is what makes this work. That is
        # also what lets `run-checks.py` keep its existing cleanup unchanged.
        self._install(tools=("claude", "opencode"))
        self.assertTrue((self.home / ".claude" / "hooks").is_dir())
        code, out = self._uninstall()
        self.assertEqual(code, 0)
        self.assertIn("hooks", out)
        self.assertFalse((self.home / ".claude" / "hooks").exists())
        self.assertFalse((self.home / ".agents" / "hooks").exists())
        self.assertEqual([], self._entries())

    @unittest.skipUnless(SYMLINKS_WORK, "this platform/account cannot create symlinks")
    def test_symlink_mode_links_the_module_and_uninstall_removes_only_the_link(self):
        # Covered separately because it is the mode `run-checks.py`'s install cycle uses
        # by default on macOS and Linux, which is four of the six CI cells, and it takes a
        # different branch of `_place`. The final assertion is the one that matters: the
        # reversal must remove the link and leave the kit's own module alone.
        self._install(mode="symlink")
        placed = self.home / ".claude" / "hooks"
        self.assertTrue(placed.is_symlink())
        self.assertEqual(placed.resolve(), inst.HOOKS_DIR.resolve())
        self._uninstall()
        self.assertFalse(placed.exists() or placed.is_symlink())
        self.assertTrue((inst.HOOKS_DIR / "README.md").is_file(),
                        "reversing a link must never reach through it to the source")

    def test_codex_receives_no_hooks_because_it_receives_no_install_at_all(self):
        """The `codex` asymmetry, pinned as intended behaviour.

        The task states it as "`HOOK_SUBPATHS` maps `claude` and `opencode` and not
        `codex`, so `--with-hooks` places nothing for a Codex install". Re-derived
        2026-08-27, that premise is false in its middle term: there is no Codex install to
        place nothing for. `TOOL_SUBPATHS` and `HOOK_SUBPATHS` carry identical key sets,
        `codex` is absent from both, and `main()` rejects `--tools codex` at exit 2 before
        `install()` is ever called.

        The omission is intended, and consistent with how the rest of the kit routes
        Codex. `install.py` places into home-scoped discovery directories; Codex reads
        neither a home-scoped skills directory (which is why the module docstring sends
        Cursor and Copilot to `build-adapters.py`) nor a home-scoped hooks directory. Its
        hook wiring is repo-scoped in the committed `.codex/hooks.json`, per the wiring
        table in `.agents/hooks/README.md`, and `WiringConsistencyTests` in
        `tests/test_hooks.py` already holds it to the every-hook rule. A `codex` row in
        `HOOK_SUBPATHS` would place a second copy at a path nothing reads.
        """
        self.assertNotIn("codex", inst.TOOL_SUBPATHS)
        self.assertNotIn("codex", inst.HOOK_SUBPATHS)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--tools", "codex", "--with-hooks",
                              "--home", str(self.home)])
        self.assertEqual(code, 2)
        self.assertIn("Unknown tool(s)", buf.getvalue())
        self.assertFalse(self.home.exists(), "a rejected tool places nothing")

    def test_every_installable_tool_has_a_hook_path(self):
        # The seam the codex framing points at, stated where it actually is. The comment
        # above HOOK_SUBPATHS allows it to be a strict subset of TOOL_SUBPATHS ("absent
        # from this map means the tool has no hook mechanism this installer knows how to
        # place"), and the placement loop's `tool in HOOK_SUBPATHS` guard would then skip
        # that tool while printing nothing at all about the skip.
        #
        # Today the maps agree, so that branch is unreachable and the silent skip cannot
        # happen. Pinned rather than left implicit: this is characterization of the
        # current state, and a future tool that gets skills but no hooks should be a
        # decision that updates this test, not one that ships a wordless omission.
        self.assertEqual(set(inst.TOOL_SUBPATHS), set(inst.HOOK_SUBPATHS))

    def test_hooks_placed_for_opencode_alone_are_announced_and_named_inert(self):
        """bug-0048: **this test changed sides.**

        It was `test_hooks_placed_for_opencode_alone_are_announced_by_nothing`, a
        characterization pin written by chore-0067 over behaviour it believed wrong but
        did not scope fixing. That version asserted the silence: no "INACTIVE", no
        registration, nothing but "plus 4 hook(s)". Its docstring said the intended
        signal was this test failing when a follow-up fixed the defect, and named the
        rewrite as the correct response to that failure. This is the rewrite, so the
        assertions below are acceptance of chosen behaviour rather than a pin on
        observed behaviour, and the name no longer describes silence because there is
        none left to describe.

        The chosen behaviour: an opencode-only run says where the module landed, names
        the plugin that would have to read it, and reports it INERT because that plugin
        is not in this home. Placing it with a warning was chosen over placing it where
        opencode actually reads, which is project-scoped rather than home-scoped and so
        a different contract from the Claude path, and over refusing the combination.
        See the task's Decisions for both rejected branches.
        """
        _code, out = self._install(tools=("opencode",))
        # Resolved home joined to the subpath, mirroring what `install()` does, rather
        # than `.resolve()` over the whole path: in symlink mode the placed leaf is a
        # symlink into this repository, so resolving through it would compare against
        # the source tree instead of the target. Comparing an unresolved home against a
        # resolved one is the same defect from the other end, and it passes on Windows
        # and Linux while failing on a macOS runner whose /var is a symlink.
        target = self.home.resolve() / ".agents" / "hooks"
        reader = self.home.resolve() / ".opencode" / "plugins" / "zen-hooks.mjs"
        self.assertTrue(target.is_dir(), "precondition: the run did place the module")
        self.assertFalse(reader.exists(),
                         "precondition: this home carries no opencode plugin")
        self.assertIn("INERT", out, "an unread placement must say so")
        self.assertNotIn("LIVE", out)
        self.assertIn(str(target), out, "the run must say where the module landed")
        self.assertIn(str(reader), out, "the run must name the reader that is absent")
        # Matched against the block the Claude Code path prints rather than against a
        # loose word, so a skill name that happens to contain "register" cannot fail
        # this. Built from the resolved home because `install()` resolves before it
        # builds the block, and an unresolved spelling would be trivially absent.
        self.assertNotIn(inst.claude_registration(self.home.resolve()), out)

    def test_an_opencode_placement_a_plugin_would_read_is_reported_live(self):
        """bug-0048: the other branch of the same note, and why it is decided from disk.

        The rule chore-0058 and chore-0065 settled one level up is that a run which did
        something useful and a run which did nothing useful must be distinguishable in
        the output. One fixed sentence cannot satisfy that, so the note asks the
        filesystem: a `--home` pointing at a project root that carries
        `.opencode/plugins/zen-hooks.mjs` receives the module at exactly the
        `.agents/hooks` that plugin resolves against its own root, and the run says LIVE.

        Not a hypothetical configuration. It is the only one in which the opencode half
        of `--with-hooks` currently does anything, which is the reason refusing the
        tool-and-flag combination was rejected: refusing would have removed the one case
        that works.
        """
        reader = self.home / ".opencode" / "plugins" / "zen-hooks.mjs"
        reader.parent.mkdir(parents=True)
        reader.write_text("// stand-in for this kit's opencode adapter\n",
                          encoding="utf-8")
        _code, out = self._install(tools=("opencode",))
        self.assertIn("LIVE", out)
        self.assertNotIn("INERT", out)
        self.assertIn(str(self.home.resolve() / ".agents" / "hooks"), out)

    def test_every_tool_that_receives_the_module_is_told_about_it(self):
        """bug-0048: the invariant, rather than the two sentences that satisfy it today.

        The defect being fixed was one tool getting files and no words, so the property
        worth pinning is the count and not the wording: every tool that received the
        module gets exactly one activation note. Each branch opens with the same phrase
        so this is countable without a per-tool regex, which would be the second source
        of truth chore-0029 recorded the cost of.

        This is what makes the fix structural. A third tool added to `HOOK_SUBPATHS`
        without a branch of its own falls through to the fallback, which still opens with
        the phrase and still says something true, so this test keeps passing and the
        silence cannot come back by omission.
        """
        tools = sorted(inst.HOOK_SUBPATHS)
        _code, out = self._install(tools=tuple(tools))
        self.assertEqual(len(tools), out.count("The hooks are placed"),
                         "one activation note per tool that received the module")
        for tool in tools:
            with self.subTest(tool=tool):
                self.assertTrue((self.home / inst.HOOK_SUBPATHS[tool]).is_dir(),
                                "precondition: this tool really did receive it")

    def test_a_claude_placement_still_prints_the_registration_block(self):
        """bug-0048 replaced one `hooks and "claude" in tools` gate with one note per
        tool that received the module, and nothing asserted the Claude Code half of that
        gate printed anything from `install()`. `HookRegistrationTests` covers
        `claude_registration` as a function, and the only test that mentioned the printed
        block asserted its *absence* on the opencode path, so a refactor that dropped the
        block from the run entirely would have left the suite green.
        """
        _code, out = self._install(tools=("claude",))
        self.assertIn("INACTIVE", out)
        self.assertIn(inst.claude_registration(self.home.resolve()), out,
                      "the pasteable block is what makes the placement usable")


class AdoptedModulePreservationTests(unittest.TestCase):
    """bug-0018 and Scenario S-016: a re-install must not destroy an adopter's edited lens.

    The defect this class exists for was reproduced on 2026-08-06 against a throwaway home:
    install, append a line to the installed `house-style.md`, install again, and the line is
    gone at exit 0 with nothing printed about it. `_place` saw a managed target, called
    `_rm` on it, and copied the kit's tree back over the hole. For a directory that took the
    whole tree, so a lens the adopter *added* beside the kit's went with it.

    The two failure directions are not symmetric, and both are asserted here. Wrongly
    preserving costs a stale lens the adopter can see with `--check`; wrongly overwriting
    costs work nobody can recover. So the preservation tests assert byte-for-byte survival,
    and the refresh tests assert an untouched file still moves, because a guard broad enough
    to pin every adopter to whatever shipped first is the inverse bug and is just as silent.

    Run against a fixture skills tree and a fixture rules module, as `StalenessCheckTests`
    is and for the same reason: the source side has to be editable, and the suite must not
    mutate `.agents/`.
    """

    KIT_LENS = "# house style\n\nno em-dashes.\n"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.rules = self.root / "rules"
        self.skills.mkdir()
        self.rules.mkdir()
        self.home = self.root / "home"

        self._real = (inst.SKILLS_DIR, inst.RULES_DIR, inst.PROFILE_SEEDS, inst.MANIFEST)
        inst.SKILLS_DIR = self.skills
        inst.RULES_DIR = self.rules
        inst.MANIFEST = self.root / "manifest.json"
        inst.PROFILE_SEEDS = {"core": ["alpha"], "spine": ["alpha"], "all": None}

        _fixture_skill(self.skills, "alpha", "does alpha things when asked")
        (self.rules / "house-style.md").write_text(self.KIT_LENS, encoding="utf-8")
        (self.rules / "review-quality.md").write_text(
            "# review quality\n\nblocker, major, minor, nit.\n", encoding="utf-8")

    def tearDown(self):
        (inst.SKILLS_DIR, inst.RULES_DIR,
         inst.PROFILE_SEEDS, inst.MANIFEST) = self._real
        self._tmp.cleanup()

    def _install(self, mode="copy", home=None, replace_adopted=False):
        # The flag is passed only when it is being exercised, so a test about preservation
        # fails on what was preserved rather than on the signature. That distinction is not
        # cosmetic: against the pre-fix `install.py` every test here would otherwise error
        # with a TypeError, which proves the parameter is absent and says nothing at all
        # about the data loss the class exists for.
        home = self.home if home is None else home
        extra = {"replace_adopted": True} if replace_adopted else {}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.install(["claude"], mode, home, False, "all", **extra)
        return code, buf.getvalue()

    def _lens(self, name="house-style.md"):
        return self.home / ".claude" / "rules" / name

    def _entries(self):
        return json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]

    def _entry(self, name):
        return next(e for e in self._entries() if e["name"] == name)

    def test_an_adopter_edited_lens_survives_a_reinstall_byte_for_byte(self):
        # bug-0018, the reproduction itself. `.agents/rules/` is the module AGENTS.md
        # describes as swappable and `house-style.md` opens by inviting the reader to
        # rewrite, so this is the one file the kit specifically asks an adopter to own.
        # Bytes, not a substring: a fix that re-copied the kit's file and appended the
        # adopter's line would satisfy "the edit survives" while still having overwritten
        # everything else they wrote.
        code, _ = self._install()
        self.assertEqual(code, 0, "precondition: the first install must succeed")
        mine = self.KIT_LENS + "\nMY OWN HOUSE RULE: sentence-case headings, always.\n"
        self._lens().write_text(mine, encoding="utf-8")

        code, out = self._install()
        self.assertEqual(code, 0, "preserving an adopter's file is news, not a failure")
        self.assertEqual(self._lens().read_text(encoding="utf-8"), mine,
                         "the adopter's lens was overwritten by the re-install")
        self.assertNotIn("CONFLICT", out)

    def test_the_run_reports_what_it_preserved_rather_than_passing_silently(self):
        # A guard that works and says nothing is half a fix: the adopter cannot tell a run
        # that refreshed their lens from one that declined to, and the difference is the
        # whole point. The file is named, not just counted.
        self._install()
        self._lens().write_text(self.KIT_LENS + "\nmine.\n", encoding="utf-8")
        (self.rules / "house-style.md").write_text(
            self.KIT_LENS + "\nand sentence-case headings.\n", encoding="utf-8")

        _, out = self._install()
        self.assertIn("preserved", out)
        self.assertIn("house-style.md", out)

    def test_an_unedited_lens_is_still_refreshed_when_the_kit_revises_it(self):
        # The inverse failure, and the one that costs most if the guard is written too
        # broadly: a lens nobody touched must still move with the kit, or every adopter is
        # pinned to whatever shipped on the day they first installed and no tool anywhere
        # says so. This is the same distinction `--check` already draws between a file that
        # differs from its recorded baseline and one that differs only from the source.
        self._install()
        revised = self.KIT_LENS + "\nand sentence-case headings.\n"
        (self.rules / "house-style.md").write_text(revised, encoding="utf-8")

        code, _ = self._install()
        self.assertEqual(code, 0)
        self.assertEqual(self._lens().read_text(encoding="utf-8"), revised,
                         "an untouched lens must not be pinned to the first install")

    def test_a_skill_directory_is_still_replaced_because_it_is_derived(self):
        # The carve-out's boundary. `build-adapters.md` S-014 states the contrast the whole
        # design rests on: a skill's supporting files are derived and are refreshed, the
        # rules module is adopted and is preserved. Extending the guard to skills would
        # strand every adopter on a stale copy of the thing the kit exists to distribute.
        self._install()
        installed = self.home / ".claude" / "skills" / "alpha" / "SKILL.md"
        installed.write_text("---\nname: alpha\ndescription: mine now\n---\n",
                             encoding="utf-8")

        code, _ = self._install()
        self.assertEqual(code, 0)
        self.assertEqual(installed.read_text(encoding="utf-8"),
                         (self.skills / "alpha" / "SKILL.md").read_text(encoding="utf-8"),
                         "a derived skill file must still be replaced")

    def test_a_lens_the_adopter_added_beside_the_kits_is_not_deleted(self):
        # `_rm(target)` on a directory takes the whole tree, so this file disappeared even
        # though nothing the kit ships is named like it. It is not the kit's to manage: it
        # is neither refreshed nor removed nor recorded.
        self._install()
        theirs = self._lens("my-own-lens.md")
        theirs.write_text("# my own lens\n\nrules the kit never shipped.\n", encoding="utf-8")

        code, _ = self._install()
        self.assertEqual(code, 0)
        self.assertTrue(theirs.is_file(), "a file the adopter added must survive")
        self.assertIn("rules the kit never shipped", theirs.read_text(encoding="utf-8"))
        self.assertNotIn("my-own-lens.md", self._entry("rules")["digests"],
                         "the kit must not record a file it did not place")

    def test_a_preserved_lens_is_still_preserved_by_the_run_after_it(self):
        # The delayed version of the same data loss, and the reason the recorded baseline
        # for a preserved file must stay at what the kit last placed rather than being
        # rewritten to what is on disk. Record the adopter's own bytes as the baseline and
        # the next run finds them "untouched", refreshes over them, and destroys the edit
        # one install later than before.
        self._install()
        mine = self.KIT_LENS + "\nMY OWN HOUSE RULE.\n"
        self._lens().write_text(mine, encoding="utf-8")
        self._install()
        self._install()
        self.assertEqual(self._lens().read_text(encoding="utf-8"), mine,
                         "the edit survived one re-install and not the next")

    def test_a_lens_the_adopter_removed_is_no_longer_recorded_as_placed(self):
        # The other half of bug-0022. The removal branch named the file in plain words and
        # left `digests[rel]` standing from the recorded baseline, so the record went on
        # asserting a file the run had just said was gone. Nothing reconciled the two, which
        # is what let `--check` keep reading a baseline for a file nobody has.
        self._install()
        self._lens("review-quality.md").unlink()

        _, out = self._install()
        self.assertIn("you removed it", out, "precondition: the run must notice the removal")
        self.assertNotIn("review-quality.md", self._entry("rules")["digests"],
                         "the record must not claim a file the run reported as gone")
        self.assertIn("house-style.md", self._entry("rules")["digests"],
                      "the rest of the baseline must survive")

    def test_a_removal_recorded_by_one_run_is_no_longer_a_fault_at_the_next_check(self):
        # Why the record has to be reconciled and not merely be tidy. Without the drop, a
        # deliberate deletion is `diverged` at exit 1 on every check forever, which is
        # precisely the noise the adopted exemption exists to avoid: the adopter would have
        # no route back to a clean report except restoring a file they chose not to have.
        #
        # What the drop buys is bounded, and the bound is asserted rather than glossed. The
        # absence claim goes away and the run is no longer a fault, but the file is still
        # named, now under `revised`: with no baseline, a lens the adopter deleted is
        # indistinguishable from one the kit has newly started shipping, and the second is
        # worth telling them about. It resolves on the next install, which places the file
        # (see `test_the_run_after_a_recorded_removal_ships_the_lens_again`).
        self._install()
        self._lens("review-quality.md").unlink()
        self._install()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.check(self.home)
        out = buf.getvalue()
        self.assertEqual(code, 0, "a removal the record has accepted is not a fault")
        self.assertNotIn("gone from the installed module", out,
                         "the absence claim must not survive the record accepting it")

    def test_the_run_after_a_recorded_removal_ships_the_lens_again(self):
        # The seam this trade leaves open, pinned so it is visible rather than discovered.
        # Once the removal is dropped from the record, a later run cannot tell a lens the
        # adopter deleted from one they have never been sent, so it places it. Remembering
        # the removal instead would need the manifest to carry a tombstone, which is a
        # format change bug-0022 explicitly rules out ("no manifest migration"), and the
        # alternative it rules in is permanent false divergence. Nothing of the adopter's is
        # destroyed either way: the file they deleted is not there to lose.
        self._install()
        self._lens("review-quality.md").unlink()
        self._install()
        self.assertFalse(self._lens("review-quality.md").exists(),
                         "the run that records the removal must not restore it")

        self._install()
        self.assertTrue(self._lens("review-quality.md").is_file(),
                        "with no record of the removal, the kit's lens is placed as new")

    def test_a_manifest_predating_the_digests_preserves_the_lens_and_says_so(self):
        # chore-0031's baseline is per entry, so an install predating it records nothing and
        # an edited lens is indistinguishable from an untouched one. The failure directions
        # are not symmetric, so the unanswerable case preserves and states that the baseline
        # is unknown rather than resolving it silently in either direction.
        self._install()
        older = {"entries": [{k: v for k, v in e.items() if k != "digests"}
                             for e in self._entries()]}
        inst.MANIFEST.write_bytes(json.dumps(older, indent=2).encode("utf-8"))
        mine = self.KIT_LENS + "\nedited under the older format.\n"
        self._lens().write_text(mine, encoding="utf-8")

        code, out = self._install()
        self.assertEqual(code, 0)
        self.assertEqual(self._lens().read_text(encoding="utf-8"), mine)
        self.assertIn("unknown", out.lower())

    def test_the_replace_flag_takes_the_kits_copy_over_an_edited_lens(self):
        # "My lens is stale and I do want the kit's" is a real case, and without a flag the
        # only route is deleting the file by hand. Named explicitly rather than folded into
        # `--mode`, since it decides what happens to an adopter's work and not how files are
        # placed. It re-establishes a baseline too: the entry records what was just placed.
        self._install()
        self._lens().write_text(self.KIT_LENS + "\nstale, and I know it.\n", encoding="utf-8")

        code, _ = self._install(replace_adopted=True)
        self.assertEqual(code, 0)
        self.assertEqual(self._lens().read_text(encoding="utf-8"), self.KIT_LENS,
                         "--replace-adopted must take the kit's copy")
        self.assertEqual(self._entry("rules")["digests"], inst.digest_tree(self.rules))

    def test_the_replace_flag_is_reachable_from_the_command_line(self):
        # The entrypoint layer: a flag wired to nothing is the registered-and-inert failure
        # this repository has now hit three times.
        self._install()
        self._lens().write_text(self.KIT_LENS + "\nstale.\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.main(["--home", str(self.home), "--profile", "all",
                              "--mode", "copy", "--replace-adopted"])
        self.assertEqual(code, 0)
        self.assertEqual(self._lens().read_text(encoding="utf-8"), self.KIT_LENS)

    def test_a_lens_file_new_in_the_kit_is_placed_beside_an_edited_one(self):
        # Preserving what the adopter owns must not stop the kit delivering what it has
        # never sent. A file absent from the recorded baseline was placed by nobody, so
        # nothing of theirs is at risk in placing it now.
        self._install()
        self._lens().write_text(self.KIT_LENS + "\nmine.\n", encoding="utf-8")
        (self.rules / "autonomy.md").write_text(
            "# autonomy\n\ndetect and report, never rewrite.\n", encoding="utf-8")

        code, _ = self._install()
        self.assertEqual(code, 0)
        self.assertTrue(self._lens("autonomy.md").is_file(),
                        "a lens the kit newly ships must still arrive")
        self.assertIn("mine.", self._lens().read_text(encoding="utf-8"))

    def test_a_first_install_into_an_empty_home_is_unaffected(self):
        # The guard only has an opinion about a target this tool already placed. A clean
        # home has nothing to preserve, and must not report as though it did.
        code, out = self._install()
        self.assertEqual(code, 0)
        self.assertEqual(self._lens().read_text(encoding="utf-8"), self.KIT_LENS)
        self.assertNotIn("preserved", out)

    def test_an_unmanaged_rules_directory_is_still_refused(self):
        # Scenario S-004 is unchanged by this: a rules directory this tool did not place is
        # still a CONFLICT, not something to merge into. The preservation path is for
        # targets the tool created; this one is not the tool's at all.
        target = self.home / ".claude" / "rules"
        target.mkdir(parents=True)
        (target / "house-style.md").write_text("someone else's\n", encoding="utf-8")

        code, out = self._install()
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", out)
        self.assertEqual((target / "house-style.md").read_text(encoding="utf-8"),
                         "someone else's\n")

    @unittest.skipUnless(SYMLINKS_WORK, "this platform or account cannot create symlinks")
    def test_symlink_mode_is_untouched_by_the_guard(self):
        # In symlink mode the installed lens *is* the kit's file, so there is no adopter
        # copy to preserve and nothing to compare. The guard must not turn the POSIX
        # default's relink into a preserve.
        self._install(mode="symlink")
        self.assertTrue((self.home / ".claude" / "rules").is_symlink(),
                        "precondition: symlink mode placed a link")
        code, out = self._install(mode="symlink")
        self.assertEqual(code, 0)
        self.assertNotIn("preserved", out)
        self.assertTrue((self.home / ".claude" / "rules").is_symlink())


class CheckReportsWhatItComparedTests(unittest.TestCase):
    """The three defects the automated reviewer found on chore-0031's pull request.

    All three are the same underlying question in different clothes: what does `--check`
    say about something it did not, or could not, actually compare? A digest labelled with
    the wrong artifact, a crash where the mode promises an exit code, and an empty baseline
    treated as a real one all leave the reader believing the check answered a question it
    never asked.
    """

    def test_the_adopted_path_names_the_record_not_the_install(self):
        # `revised` compares the recorded baseline against the source, so calling the left
        # side "installed" printed a digest matching no file on disk. An adopter running a
        # checksum on their own lens got a third number and no way to reconcile it.
        moved = inst._compare({"a.md": "aa" * 32}, {"a.md": "bb" * 32},
                              "recorded", "source now")
        joined = "\n".join(moved)
        self.assertIn("recorded aaaaaaaaaaaa", joined)
        self.assertIn("source now bbbbbbbbbbbb", joined)
        self.assertNotIn("installed", joined)

    def test_the_derived_path_still_says_installed(self):
        # The default labels were correct for the divergence path and must not regress.
        moved = inst._compare({"a.md": "aa" * 32}, {"a.md": "bb" * 32})
        self.assertIn("installed aaaaaaaaaaaa, source bbbbbbbbbbbb", "\n".join(moved))

    def test_an_absence_is_reported_against_the_side_it_is_absent_from(self):
        self.assertIn("in the source now, absent from the recorded",
                      "\n".join(inst._compare({}, {"a.md": "aa" * 32},
                                              "recorded", "source now")))

    def test_an_unreadable_file_is_an_error_verdict_not_a_traceback(self):
        # digest_tree() reads bytes, and --check promises 0/1/2 rather than a stack trace.
        entry = {"target": str(Path(__file__)), "source": str(Path(__file__).parent),
                 "digests": {"x": "aa" * 32}, "name": "alpha"}
        with mock.patch.object(inst, "digest_tree", side_effect=PermissionError("locked")):
            status, message = inst._check_entry(entry)
        self.assertEqual(status, "error")
        self.assertIn("locked", message)

    def test_an_empty_digest_map_is_no_baseline_at_all(self):
        # Falsiness, not `is None`: an entry recording {} is exactly as unanswerable as one
        # recording nothing, and reporting it as comparable was a clean-looking partial.
        status, message = inst._check_entry({"target": ".", "source": ".", "digests": {}})
        self.assertEqual(status, "unknown")
        self.assertIn("Re-install", message)


MALFORMED_MANIFESTS = {
    "an entry with no target": {
        "entries": [{"tool": "claude", "name": "alpha", "source": "s"}]},
    "an entry whose target is null": {
        "entries": [{"tool": "claude", "name": "alpha", "target": None, "source": "s"}]},
    "a top-level list rather than an object": [
        {"tool": "claude", "name": "alpha", "target": "t", "source": "s"}],
    "an entry that is not an object": {"entries": ["alpha"]},
}

# Runs install.py exactly as its own `__main__` guard does, with only the manifest
# constant moved off the real repository. A subprocess and not an in-process call,
# because the defect under test is what a *process* reports: an uncaught exception
# inside main() prints a traceback to stderr and exits 1, and 1 is this tool's word for
# "an installed target has diverged". An in-process call sees the exception and never
# sees either half of the wrong answer.
_DRIVER = """\
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("zen_install", sys.argv[1])
inst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inst)
inst.MANIFEST = Path(sys.argv[2])
raise SystemExit(inst.main(sys.argv[3:]))
"""


class MalformedManifestTests(unittest.TestCase):
    """bug-0024: a manifest that parses but is the wrong shape must not exit 1.

    All four shapes below were reproduced against this file on 2026-08-08 and again on
    2026-08-20, after `bug-0022`, `feat-0049`, and `chore-0042` had each edited it. Every
    one raised out of `main()`, which the CLI turns into a traceback at exit 1. Exit 1 in
    this tool means "at least one installed target has diverged from its source", so a
    caller scripting around `--check` was told its install had drifted when in fact
    nothing had been compared. The true state is exit 2, could not run, which the
    acceptance command, `check-provenance.py`, and `check()`'s own docstring all rank
    above 1 for that reason.

    The manifest is per-machine and gitignored, so these shapes come from an interrupted
    write, a full disk, or a partly synced home rather than from an attacker.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.manifest = self.root / "manifest.json"
        self.driver = self.root / "driver.py"
        self.driver.write_text(_DRIVER, encoding="utf-8")

    def _write(self, payload):
        self.manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _run(self, *argv):
        """The CLI, at the process layer. Returns the completed process."""
        return subprocess.run(
            [sys.executable, str(self.driver), str(MODULE_PATH), str(self.manifest),
             *argv],
            capture_output=True, text=True, timeout=300)

    def _commands(self):
        return (("--check", "--home", str(self.home)),
                ("--uninstall", "--dry-run", "--home", str(self.home)),
                ("--dry-run", "--home", str(self.home), "--tools", "claude"))

    def _assert_could_not_run(self, result):
        self.assertEqual(result.returncode, 2,
                         f"expected 2 (could not run), got {result.returncode}.\n"
                         f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        self.assertNotIn("Traceback (most recent call last)", result.stderr)
        self.assertEqual(result.stderr.strip(), "")

    def test_every_malformed_shape_is_could_not_run_rather_than_diverged(self):
        for label, payload in MALFORMED_MANIFESTS.items():
            for argv in self._commands():
                with self.subTest(shape=label, command=argv[0]):
                    self._write(payload)
                    self._assert_could_not_run(self._run(*argv))

    def test_the_report_names_the_manifest_and_the_offending_entry(self):
        entry_level = ("an entry with no target", "an entry whose target is null",
                       "an entry that is not an object")
        for label in entry_level:
            with self.subTest(shape=label):
                self._write(MALFORMED_MANIFESTS[label])
                out = self._run("--check", "--home", str(self.home)).stdout
                self.assertIn(str(self.manifest), out)
                self.assertIn("entry 0", out)
                self.assertIn("re-install", out.lower())

    def test_a_wrong_top_level_shape_says_what_the_file_is_instead(self):
        self._write(MALFORMED_MANIFESTS["a top-level list rather than an object"])
        out = self._run("--check", "--home", str(self.home)).stdout
        self.assertIn(str(self.manifest), out)
        self.assertIn("a list", out)
        self.assertIn("re-install", out.lower())

    def test_a_named_entry_is_reported_by_its_name_as_well_as_its_index(self):
        # The index alone is a poor handle in a record of a hundred entries, and the name
        # is the column the tool prints everywhere else.
        self._write({"entries": [{"tool": "claude", "name": "alpha",
                                  "target": str(self.home / "alpha")},
                                 {"tool": "claude", "name": "house-review"}]})
        out = self._run("--check", "--home", str(self.home)).stdout
        self.assertIn("entry 1", out)
        self.assertIn("house-review", out)

    def test_an_unknown_extra_key_is_still_a_valid_record(self):
        # A reader that faults on what it does not recognise turns an upgrade written by
        # a later version of this tool into what looks like corruption. Asserted through
        # --uninstall because it answers 0 for a record it could read and 2 for one it
        # could not, so the two outcomes are actually distinguishable.
        placed = self.home / ".claude" / "skills" / "alpha"
        placed.mkdir(parents=True)
        self._write({"schema": 7, "entries": [
            {"tool": "claude", "name": "alpha", "target": str(placed),
             "source": str(REPO_ROOT), "mode": "copy", "provenance": {"run": 3}}]})
        result = self._run("--uninstall", "--dry-run", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("alpha", result.stdout)
        self.assertNotIn("Cannot read the install record", result.stdout)

    def test_corrupt_bytes_still_degrade_to_an_empty_record(self):
        # The pre-existing behaviour, unchanged: bytes that do not parse never named an
        # install, so reading them as nothing recorded is truthful. Only a file that
        # parses carries a record worth refusing to act on.
        self.manifest.write_text("{not json at all", encoding="utf-8")

        removal = self._run("--uninstall", "--dry-run", "--home", str(self.home))
        self.assertEqual(removal.returncode, 0, removal.stdout + removal.stderr)
        self.assertIn("Nothing recorded as installed.", removal.stdout)
        self.assertNotIn("Cannot read the install record", removal.stdout)

        # --check answers 2 here too, but for its own pre-existing reason (S-005,
        # nothing recorded beneath this home), not because the file was rejected.
        checked = self._run("--check", "--home", str(self.home))
        self.assertEqual(checked.returncode, 2)
        self.assertIn("Nothing recorded as installed beneath", checked.stdout)
        self.assertNotIn("Cannot read the install record", checked.stdout)


class MalformedManifestInstallChoiceTests(unittest.TestCase):
    """What a real (not dry-run) install does with a record it cannot read.

    bug-0024 left this an open choice: refuse, or treat the record as empty and let every
    existing target report CONFLICT. Refusing is the choice, and it is asserted here
    rather than left implicit, because the alternative is not merely a different message:
    proceeding ends in `save_manifest`, which writes a fresh record over the damaged one
    and takes with it every target recorded under a home this run never looked at.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self._real_manifest = inst.MANIFEST
        inst.MANIFEST = self.root / "manifest.json"
        self.addCleanup(self._restore)

    def _restore(self):
        inst.MANIFEST = self._real_manifest

    def test_a_real_install_places_nothing_and_leaves_the_record_alone(self):
        damaged = json.dumps(MALFORMED_MANIFESTS["an entry with no target"], indent=2)
        inst.MANIFEST.write_text(damaged, encoding="utf-8")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = inst.install(["claude"], "copy", self.home, dry=False, profile="core")

        self.assertEqual(rc, 2, buf.getvalue())
        self.assertIn("Nothing was placed", buf.getvalue())
        self.assertFalse(self.home.exists(),
                         "a refused install must not create the discovery directory")
        self.assertEqual(inst.MANIFEST.read_text(encoding="utf-8"), damaged,
                         "the damaged record must survive the run that refused it")


class UninstallSurvivesAPartialRecordTests(unittest.TestCase):
    """bug-0053: `uninstall()` deleted a target and then died on an optional key.

    `_validate_manifest()` requires only `target`; `tool` and `name` are optional so that a
    record written by another version of this tool reads as a record rather than as
    corruption (`bug-0024`). `uninstall()` subscripted both, so a manifest this validator
    accepts killed the run at the print statement, one line after `_rm()` had already taken
    the file, and the `save_manifest()` at the end of the loop never ran. The file was gone
    and the record still claimed it, which is the over-claiming direction and the one the
    next run reads to decide what it placed.

    These drive `uninstall()` directly rather than through the CLI, because the defect is in
    the loop rather than in argument handling, and directly is where a mid-loop failure can
    be induced without a subprocess.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self._real_manifest = inst.MANIFEST
        inst.MANIFEST = self.root / "manifest.json"
        self.addCleanup(self._restore)

    def _restore(self):
        inst.MANIFEST = self._real_manifest

    def _place(self, name):
        """A directory under the home, as an install would leave one."""
        target = self.home / ".claude" / "skills" / name
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("placed by the test\n", encoding="utf-8")
        return target

    def _record(self, entries):
        inst.MANIFEST.write_text(json.dumps({"entries": entries}, indent=2),
                                 encoding="utf-8")

    def _entries(self):
        return json.loads(inst.MANIFEST.read_text(encoding="utf-8"))["entries"]

    def _uninstall(self, dry=False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.uninstall(self.home, dry)
        return code, buf.getvalue()

    def _bare_entry(self, name):
        """An entry the validator accepts and the old code could not print: `target` only."""
        return {"target": str(self._place(name)),
                "source": str(inst.SKILLS_DIR / name), "mode": "copy"}

    def test_an_entry_with_no_tool_or_name_is_removed_rather_than_raising(self):
        entry = self._bare_entry("doc-sync")
        self._record([entry])
        target = Path(entry["target"])

        inst._validate_manifest({"entries": [entry]})    # the premise: this record is legal

        code, out = self._uninstall()

        self.assertEqual(code, 0, out)
        self.assertFalse(target.exists(), "the recorded target was not removed")
        self.assertEqual(self._entries(), [],
                         "the record still claims a target that has been removed")
        self.assertIn("(unnamed entry)", out,
                      "an entry with no name is removed silently, so a reader cannot tell "
                      "which record the line came from")

    def test_the_dry_run_over_the_same_record_removes_nothing_and_does_not_raise(self):
        """The preview a careful person takes first raised in the same place as the real
        run, so the one step that exists to make this safe was the step that failed."""
        entry = self._bare_entry("doc-sync")
        self._record([entry])
        target = Path(entry["target"])

        code, out = self._uninstall(dry=True)

        self.assertEqual(code, 0, out)
        self.assertTrue(target.exists(), "a dry run removed the target")
        self.assertEqual(len(self._entries()), 1, "a dry run rewrote the record")
        self.assertIn("[dry-run]", out)

    def test_a_failure_part_way_through_leaves_a_record_that_matches_the_disk(self):
        """The property the fix is really about, and it is not about missing keys.

        Whatever stops the loop, the record must claim exactly what is still on disk. The
        failure is induced at `_rm` rather than by patching `save_manifest`, so this still
        fails if the loop is restructured: a real `_rm` can fail on a permission error, a
        file held open, or a full disk, and the old code lost the record of every removal
        that had already succeeded.
        """
        first, second, third = (self._bare_entry(n) for n in ("a-skill", "b-skill",
                                                              "c-skill"))
        self._record([first, second, third])
        doomed = Path(second["target"])
        real_rm = inst._rm

        def rm(target):
            if Path(target) == doomed:
                raise OSError(13, "permission denied")
            return real_rm(target)

        inst._rm = rm
        self.addCleanup(lambda: setattr(inst, "_rm", real_rm))

        buf = io.StringIO()
        with self.assertRaises(OSError):
            with contextlib.redirect_stdout(buf):
                inst.uninstall(self.home, dry=False)

        self.assertFalse(Path(first["target"]).exists(), "the first target survived")
        self.assertTrue(doomed.exists(), "the target whose removal failed is gone anyway")
        self.assertTrue(Path(third["target"]).exists(),
                        "a target after the failure was removed")

        remaining = [e["target"] for e in self._entries()]
        self.assertNotIn(first["target"], remaining,
                         "the record still claims a target this run removed, which is the "
                         "over-claiming direction bug-0053 was filed for")
        self.assertIn(second["target"], remaining,
                      "the record dropped a target that is still on disk")
        self.assertIn(third["target"], remaining,
                      "the record dropped a target that was never reached")

    def test_a_target_recorded_under_another_home_is_untouched_by_the_failure(self):
        """The `finally` writes `others` back too, so a partial run must not take another
        home's entries with it. That scoping is `S-007` and `S-012` and predates this fix."""
        mine = self._bare_entry("a-skill")
        elsewhere = {"target": str(self.root / "other-home" / ".claude" / "skills" / "x"),
                     "tool": "claude", "name": "x", "mode": "copy"}
        self._record([mine, elsewhere])
        real_rm = inst._rm
        inst._rm = lambda target: (_ for _ in ()).throw(OSError(13, "denied"))
        self.addCleanup(lambda: setattr(inst, "_rm", real_rm))

        buf = io.StringIO()
        with self.assertRaises(OSError):
            with contextlib.redirect_stdout(buf):
                inst.uninstall(self.home, dry=False)

        remaining = [e["target"] for e in self._entries()]
        self.assertIn(elsewhere["target"], remaining,
                      "another home's record was lost by a failure in this one")

    def test_every_consumer_of_an_optional_key_reaches_it_through_get(self):
        """The comment above `_OPTIONAL_ENTRY_TYPES` is the only statement of which reader
        touches which key, and a reader trusting it is how this shipped. This asserts the
        property that comment describes, over the source, so a fourth consumer added with a
        subscript puts the trap back and fails here.

        `_validate_manifest()` is excluded, and the exclusion is the point rather than a
        convenience. It is the one function whose job is to inspect a shape before anything
        trusts it, so it subscripts `name` inside an `isinstance(entry.get("name"), str)`
        guard, which is correct and idiomatic there. Everywhere else the entry has already
        been accepted and the key is optional by contract, so a bare subscript is a defect.
        The first version of this assertion scanned the whole file and flagged that guarded
        line; narrowing it was the right answer and editing the validator to satisfy it
        would have been the wrong one.
        """
        source = Path(inst.__file__).read_text(encoding="utf-8")
        start = source.index("def _validate_manifest(")
        end = source.index("\ndef ", start)
        consumers = source[:start] + source[end:]
        self.assertIn("entry.get(\"name\")", source[start:end],
                      "the validator no longer guards the subscript this exclusion assumes, "
                      "so the exclusion is now hiding something")

        for key in inst._OPTIONAL_ENTRY_TYPES:
            for spelling in (f'e["{key}"]', f"e['{key}']",
                             f'entry["{key}"]', f"entry['{key}']"):
                with self.subTest(key=key, spelling=spelling):
                    self.assertNotIn(
                        spelling, consumers,
                        f"{spelling} subscripts an optional manifest key, which "
                        f"_validate_manifest does not require: read it through .get()")


class OrphanedRecordTests(unittest.TestCase):
    """chore-0082 item 2: a record of an install whose home is gone too.

    Reversal is scoped to `--home` by design (`S-007`, `S-012`), so `uninstall()` rewrites
    only the entries it did not remove. An entry for a home that was *deleted* rather than
    uninstalled is never in `mine`, never pruned, and counted `diverged` forever, inflating
    the one number a person reads as a currency signal.

    Observed for real on 2026-08-29: twenty such entries under a throwaway `fakehome` from
    another session, `0 of 20` targets still on disk. They were not merely noise in a count.
    Registering `install-currency-reminder.py` made it report them as installed copies that
    had "gone stale", naming real skills, when the actual install was current: a guardrail
    asserting something false at every session start.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self._real_manifest = inst.MANIFEST
        inst.MANIFEST = self.root / "manifest.json"
        self.addCleanup(setattr, inst, "MANIFEST", self._real_manifest)

    def _entry(self, home, name, place):
        target = home / ".claude" / "skills" / name
        if place:
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("placed\n", encoding="utf-8")
        return {"tool": "claude", "name": name, "mode": "copy", "target": str(target),
                "source": str(inst.SKILLS_DIR / "doc-sync"),
                "digests": {"SKILL.md": "0" * 64}}

    def _check(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inst.check(self.home)
        return code, buf.getvalue()

    def test_a_home_that_is_gone_reads_differently_from_a_target_that_is_gone(self):
        # Both are `diverged`, and they need different things from a reader: one is a file
        # somebody removed and re-installing restores it, the other is a record of an install
        # that no longer exists anywhere and re-installing would recreate a tree nobody wants.
        dead_home = self.root / "gone"
        removed = self._entry(self.home, "alpha", place=False)
        self.home.joinpath(".claude", "skills").mkdir(parents=True, exist_ok=True)
        orphan = self._entry(dead_home, "beta", place=False)
        inst.MANIFEST.write_text(json.dumps({"entries": [removed, orphan]}), encoding="utf-8")

        # `check` is scoped to `--home`, so run it over the parent that holds both.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            inst.check(self.root)
        out = buf.getvalue()

        self.assertIn("the installed target is gone: ", out)
        self.assertIn("so is the home it sat in", out)
        self.assertIn("nothing will prune them", out,
                      "the summary does not tell a reader these will never leave the record")

    def test_a_target_gone_from_a_live_home_is_not_called_an_orphan(self):
        # The negative case. Calling a live install's missing file an orphan would invite
        # deleting a record that a re-install would legitimately restore.
        self.home.joinpath(".claude", "skills").mkdir(parents=True)
        entry = self._entry(self.home, "alpha", place=False)
        inst.MANIFEST.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")

        _, out = self._check()

        self.assertIn("the installed target is gone", out)
        self.assertNotIn("so is the home it sat in", out)
        self.assertNotIn("nothing will prune them", out)

    def test_home_derivation_walks_up_to_the_discovery_directory(self):
        # The home is derived from the target rather than recorded, because the manifest has
        # never carried it and a new key would be unreadable for every entry written before.
        home = Path(self.root) / "somewhere"
        for sub in ((".claude", "skills", "doc-sync"), (".agents", "rules"),
                    (".claude", "hooks")):
            with self.subTest(sub=sub):
                self.assertEqual(inst._home_of(home.joinpath(*sub)), home)

    def test_a_target_with_no_discovery_marker_reads_as_still_there(self):
        # The safe direction: the only thing this decides is whether --check calls an entry
        # litter, and calling real litter live costs a line where the reverse invites
        # deleting a live record.
        odd = self.root / "not-a-home" / "thing"
        odd.mkdir(parents=True)
        self.assertTrue(inst._home_of(odd).exists())


if __name__ == "__main__":
    unittest.main()
