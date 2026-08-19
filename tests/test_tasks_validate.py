"""Acceptance tests for .tasks/validate.py and the copy `init-worktracking` scaffolds.

Two areas, added by two tasks. The `external` field tests are derived from
docs/spec/tracker-links.md and each is tagged with the scenario id it covers. The link
tests come from `bug-0011` and have no spec behind them; the validator as a whole has no
contract yet, only the `external` field does.

Both copies of the validator are driven here, not just this repository's. `bug-0026`
found the `external` guard and the injectable `main(argv=None)` present only in the copy
that authored them, so every repository the kit scaffolds got the feature `pr-describe`
ships and none of the check that makes it safe. A contract that holds in one copy and
not the other is the failure this file now tests for directly.

Standard library only, per the conventions section of AGENTS.md.

Scope is still deliberately narrow. `.tasks/validate.py` had no test file before
`feat-0030`, and backfilling coverage for the whole validator remains separate work; the
file does not pretend to be a full suite.
"""
import ast
import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".tasks" / "validate.py"
TEMPLATE_PATH = (REPO_ROOT / ".agents" / "skills" / "init-worktracking"
                 / "templates" / "validate.py")

_spec = importlib.util.spec_from_file_location("zen_tasks_validate", MODULE_PATH)
tv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tv)

# The template is loaded as a second, independent module rather than compared as text,
# so the tests below exercise what a scaffolded repository would actually run. It is
# never registered in sys.modules, so the two copies cannot shadow one another.
_template_spec = importlib.util.spec_from_file_location(
    "zen_tasks_validate_template", TEMPLATE_PATH)
tvt = importlib.util.module_from_spec(_template_spec)
_template_spec.loader.exec_module(tvt)

TASK = """---
id: feat-0099
title: A task used only by this test
type: feat
status: open
priority: P1
parent: "ROADMAP#9 tracker-links"
depends_on: []
{external}touched_files:
  - README.md
created: 2026-07-28
---

## Problem

Body content is not what this test exercises.
"""


class TasksRootTestCase(unittest.TestCase):
    """A throwaway repository root with a .tasks/ tree, shared by both areas.

    Which copy of the validator a case drives is a class attribute, so a subclass can
    re-run an entire suite against the template without a second fixture. `bug-0026`
    chose that over duplicating the setup: a fixture maintained twice drifts for the
    same reason the validator itself did.
    """

    module = tv

    def setUp(self):
        # Mirror a real repository: a root holding .tasks/ and the file the fixture
        # names in touched_files. The validator reports paths relative to REPO_ROOT,
        # so the task file has to actually live beneath it.
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tasks = self.root / ".tasks"
        self.tasks.mkdir()
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")

        self._real_tasks_dir = self.module.TASKS_DIR
        self._real_repo_root = self.module.REPO_ROOT
        self.module.TASKS_DIR = self.tasks
        self.module.REPO_ROOT = self.root

    def tearDown(self):
        self.module.TASKS_DIR = self._real_tasks_dir
        self.module.REPO_ROOT = self._real_repo_root
        self._tmp.cleanup()

    def _run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.module.main(["--strict"])
        return code, buf.getvalue()


class ExternalFieldTests(TasksRootTestCase):
    """Scenarios S-007 and S-008."""

    def _write(self, external_line):
        (self.tasks / "feat-0099-test.md").write_text(
            TASK.format(external=external_line), encoding="utf-8")

    def test_a_malformed_external_fails_validation(self):
        # Scenario S-007: a value GitHub would not recognise must fail before it can
        # reach a pull request body, naming the file and the value.
        self._write('external: "issue 123"\n')
        code, out = self._run()
        self.assertNotEqual(code, 0, "a malformed external must exit non-zero")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn("issue 123", out)

    def test_a_bare_number_is_rejected(self):
        # Scenario S-007: a bare number is the tempting shorthand and is deliberately
        # not accepted, so the stored value stays identical to GitHub's own syntax.
        self._write("external: 123\n")
        code, _ = self._run()
        self.assertNotEqual(code, 0)

    def test_an_absent_external_is_valid(self):
        # Scenario S-008: the link is optional.
        self._write("")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_same_repository_reference_is_accepted(self):
        # Scenario S-008 (accepted form): `#123`.
        self._write('external: "#123"\n')
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_cross_repository_reference_is_accepted(self):
        # Scenario S-008 (accepted form): `owner/repo#123`, which S-005 requires be
        # carried into the pull request body unchanged.
        self._write('external: "hams-ollo/zen-agent-skills#123"\n')
        code, out = self._run()
        self.assertEqual(code, 0, out)


class TemplateExternalFieldTests(ExternalFieldTests):
    """Scenarios S-007 and S-008, over the copy `init-worktracking` scaffolds.

    `bug-0026`: the guard existed only in the repository that authored it. `pr-describe`
    ships to adopters and tells an agent a task file may carry an `external` field, and
    `init-worktracking` scaffolded the tracker into that same repository with a validator
    that never checked it. So every repository the kit set up got the feature and not the
    check, which is the exact silent failure S-007 exists to prevent: a form GitHub does
    not recognise is ignored, and the issue simply never closes.

    The whole parent suite is re-run rather than restated, deliberately. S-007 and S-008
    are one contract, so the two copies are held to one set of assertions; a template
    test written separately could pass while asserting something weaker.
    """

    module = tvt


class TemplateInjectableArgvTests(TasksRootTestCase):
    """`chore-0017`'s injectable CLI layer, carried into the template by `bug-0026`.

    The point of `main(argv=None)` is that the CLI layer is reachable from a test in the
    repository the scaffold lands in. The template had `main()` reading `sys.argv`
    directly, so an adopter could test every helper in the file and never the entry point
    that decides the exit code.
    """

    module = tvt

    def _write_task_naming_a_missing_file(self):
        # A warning, not an error: a missing touched_files path warns by default and is
        # promoted only by --strict. That gap is what makes the flag observable, which is
        # what lets these tests prove which argv was actually read.
        (self.tasks / "feat-0099-test.md").write_text(
            TASK.format(external="").replace("  - README.md", "  - no-such-file.md"),
            encoding="utf-8")

    def _run_with(self, argv, sys_argv):
        buf = io.StringIO()
        real = sys.argv
        sys.argv = sys_argv
        try:
            with contextlib.redirect_stdout(buf):
                code = self.module.main() if argv is None else self.module.main(argv)
        finally:
            sys.argv = real
        return code, buf.getvalue()

    def test_an_injected_argv_is_read_instead_of_sys_argv(self):
        # The oracle that actually proves injection rather than coincidence: sys.argv
        # and the injected argv disagree about --strict, and the injected one has to
        # win. Passing an argv that happened to agree with sys.argv would prove nothing.
        self._write_task_naming_a_missing_file()
        code, out = self._run_with(["--strict"], ["validate.py"])
        self.assertNotEqual(
            code, 0, f"the injected --strict must be the argv that is read\n{out}")
        self.assertIn("no-such-file.md", out)

    def test_an_injected_empty_argv_overrides_a_strict_sys_argv(self):
        # The same discrimination in the other direction, so the test cannot pass by
        # a main() that merely concatenates the two sources.
        self._write_task_naming_a_missing_file()
        code, out = self._run_with([], ["validate.py", "--strict"])
        self.assertEqual(code, 0, f"sys.argv must not leak past an injected argv\n{out}")

    def test_calling_main_with_no_argument_still_reads_sys_argv(self):
        # The compatibility half. The template is run as a standalone script by whoever
        # scaffolds it, so making the CLI testable must not change what the CLI does.
        self._write_task_naming_a_missing_file()
        code, out = self._run_with(None, ["validate.py", "--strict"])
        self.assertNotEqual(
            code, 0, f"the standalone CLI must still honour sys.argv\n{out}")


class TemplateStandaloneTests(unittest.TestCase):
    """`chore-0029`: the template validator runs in a tree holding nothing else.

    Pinned here because `bug-0026` added a module-level regex and a new check to it, and
    the failure mode worth guarding is an import or a reference that only resolves in
    this repository. A scaffolded tree has no `docs/spec/`, no `scripts/`, and no sibling
    from this kit, so the file has to stand entirely on its own.
    """

    def test_it_validates_a_bare_scaffolded_tree_as_a_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / ".tasks"
            tasks.mkdir()
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            # The only file from this kit in the tree is the validator itself.
            (tasks / "validate.py").write_text(
                TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (tasks / "feat-0099-test.md").write_text(
                TASK.format(external='external: "#123"\n'), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(tasks / "validate.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root))

        self.assertEqual(
            proc.returncode, 0,
            f"the template must validate a bare tree standalone\n"
            f"{proc.stdout}\n{proc.stderr}")

    def test_it_rejects_a_malformed_external_as_a_subprocess(self):
        # Scenario S-007 through the real entry point an adopter runs, rather than
        # through an imported module: the check has to survive the trip into a
        # scaffolded tree, which is the whole subject of bug-0026.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / ".tasks"
            tasks.mkdir()
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            (tasks / "validate.py").write_text(
                TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (tasks / "feat-0099-test.md").write_text(
                TASK.format(external='external: "issue 123"\n'), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(tasks / "validate.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root))

        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("issue 123", proc.stdout)


class RelativeLinkTests(TasksRootTestCase):
    """`bug-0011`: links are validated where the file currently lives.

    The defect these pin down is not a malformed link. It is a correct link that stops
    being correct because the file moved: a task authored in .tasks/ links to
    `../README.md`, the lifecycle moves it to .tasks/done/ at closeout, and `../` now
    means .tasks/. 101 links across 36 files had broken this way while every command in
    the repository reported success.
    """

    def _write(self, body, *, in_done=False):
        """Write a task file carrying `body`, either in .tasks/ or in .tasks/done/."""
        if in_done:
            directory = self.tasks / "done"
            directory.mkdir(exist_ok=True)
            status = "done"
        else:
            directory = self.tasks
            status = "open"
        (directory / "feat-0099-test.md").write_text(
            TASK.format(external="").replace("status: open", f"status: {status}")
            + "\n" + body + "\n",
            encoding="utf-8")

    def test_a_link_that_the_move_to_done_breaks_is_caught(self):
        # The whole defect in one case: `../README.md` resolves from .tasks/ and does
        # not from .tasks/done/, and only the second is an error.
        self._write("See [the readme](../README.md).", in_done=True)
        code, out = self._run()
        self.assertNotEqual(code, 0, f"a dangling link must exit non-zero\n{out}")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn("../README.md", out)

    def test_the_same_link_is_valid_before_the_move(self):
        # The other half of the pair. Without this the check could be passing for the
        # wrong reason, by rejecting the link everywhere rather than by resolving it
        # against the directory the file is actually in.
        self._write("See [the readme](../README.md).")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_absolute_and_fragment_only_targets_are_skipped(self):
        # Matching the docs link step in .github/workflows/checks.yml: off-disk schemes
        # are not the filesystem's to resolve, and a bare `#anchor` has no target to
        # check. Anchor validation is a separate question from this one.
        self._write(
            "[web](https://example.com/x) [plain](http://example.com/x) "
            "[mail](mailto:someone@example.com) [anchor](#a-heading)")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_file_scheme_link_is_skipped(self):
        # An adopting repository may mandate absolute `file:` links in its own house
        # style, and this checker has no standing to resolve a path outside the
        # repository. Before this was skipped, every such link was read as relative and
        # reported broken, so a repository that had committed to the convention could
        # not run the validator at all. Its own conventions win; see the skill's
        # Conventions section.
        self._write(
            "[a module](file:///d:/some-repo/src/thing.py) "
            "[a doc](file:///c:/other/README.md)")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_fragment_is_stripped_before_the_target_is_resolved(self):
        # `../README.md#section` points at a real file, so it must pass; the fragment
        # is not part of the path.
        self._write("See [a section](../README.md#a-heading).")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_prose_that_merely_quotes_link_syntax_is_not_treated_as_a_link(self):
        # A bare closing fragment is how a document talks *about* a link. Task files in
        # this repository genuinely contain one, so a looser pattern would fail the
        # build on documentation rather than on a broken link.
        self._write("The skills all end their links with `](../nope/missing.md)`.")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_broken_link_inside_a_fenced_code_block_is_not_reported(self):
        # `bug-0023`: `bug-0017` taught mislabelled_links() that a fenced link renders
        # as literal text, and broken_links() never learned it, even though it is what
        # both callers actually run. A task file quoting a broken link as the example of
        # the bug it documents is the case this exists for.
        self._write(
            "The docs link step printed:\n\n"
            "```text\n"
            "[the readme](../does-not-exist.md)\n"
            "```\n")
        code, out = self._run()
        self.assertEqual(code, 0, f"a fenced link is not a link\n{out}")

    def test_a_broken_link_inside_a_single_backtick_code_span_is_not_reported(self):
        # `bug-0023`, the inline half, from `bug-0015`. A backticked link is not
        # clickable by anybody, so there is nothing to resolve and nothing to report.
        self._write("Write it as `[the readme](./nope.md)` to quote it literally.")
        code, out = self._run()
        self.assertEqual(code, 0, f"a backticked link is not a link\n{out}")

    def test_a_broken_link_inside_a_double_backtick_code_span_is_not_reported(self):
        # `bug-0015` again: a span opens with a run of any length, and the double form
        # is what an author reaches for the moment the quoted text carries a backtick of
        # its own. A fix that knows only the single form fixes half the occurrences.
        self._write("It printed `` [`the readme`](./nope.md) `` and failed.")
        code, out = self._run()
        self.assertEqual(code, 0, f"a double-backtick span is a code span too\n{out}")

    def test_a_broken_link_outside_any_span_or_fence_is_still_reported(self):
        # The guard the exclusion cannot be allowed to defeat. `bug-0023`'s risk section
        # names the direction that costs most: a check that quietly stops finding real
        # broken links reports success while doing nothing. The closed fence and the lone
        # backtick above are both decoys; the link on the last line is genuinely dangling.
        self._write(
            "The shape `[x](./nope.md)` is literal text, and a lone ` backtick opens "
            "nothing.\n\n"
            "```md\n"
            "[x](./nope.md)\n"
            "```\n\n"
            "See [the readme](../nowhere/missing.md) for the installer.")
        code, out = self._run()
        self.assertNotEqual(
            code, 0, f"a real broken link must survive the exclusion\n{out}")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn("../nowhere/missing.md", out)

    def test_an_unterminated_fence_does_not_suppress_a_broken_link_after_it(self):
        # `bug-0017`'s trade, inherited here: an opening fence with no closer opens
        # nothing, exactly as an unmatched backtick run opens nothing. Running an
        # unclosed fence to end of file would switch the link check off for everything
        # below it and still exit clean, which is the one failure indistinguishable from
        # success.
        self._write(
            "```md\n"
            "a fence that is never closed\n"
            "\n"
            "See [the readme](../nowhere/missing.md) for the installer.")
        code, out = self._run()
        self.assertNotEqual(
            code, 0,
            f"an unterminated fence must not suppress what follows it\n{out}")
        self.assertIn("../nowhere/missing.md", out)

    def test_a_non_task_document_under_tasks_is_checked_too(self):
        # The link scan is deliberately wider than the task-file scan: a broken link in
        # .tasks/README.md is exactly as clickable as one in a task file, and that file
        # is skipped by every other check in the validator.
        self._write("No links here.")
        (self.tasks / "README.md").write_text(
            "See [nothing](../nowhere/missing.md).\n", encoding="utf-8")
        code, out = self._run()
        self.assertNotEqual(code, 0, f"README.md must be link-checked\n{out}")
        self.assertIn("../nowhere/missing.md", out)


class MislabelledLinkTests(TasksRootTestCase):
    """`bug-0012`: the class underneath a dangling link, a link that resolves wrongly.

    `bug-0011` closed the dangling class by resolving every link from the directory the
    file actually lives in. It cannot see this one. `.tasks/README.md` exists, so
    `../README.md` written from `.tasks/done/` resolves, existence is satisfied, and the
    reader still lands on a file the link text never named. Three completed task files
    in this repository carried exactly that link while every check reported success.

    The fixture differs from RelativeLinkTests in the one way that matters: it creates
    `.tasks/README.md` as well as the root `README.md`, which is what makes the wrong
    target resolvable and the defect reachable at all.
    """

    def setUp(self):
        super().setUp()
        # The second README is the whole premise. Without it `../README.md` from done/
        # dangles and bug-0011's check reports it, so this class would be testing that
        # check rather than this one.
        (self.tasks / "README.md").write_text("the tasks readme\n", encoding="utf-8")

    def _write(self, body):
        """Write a completed task file in .tasks/done/ carrying `body`."""
        directory = self.tasks / "done"
        directory.mkdir(exist_ok=True)
        (directory / "feat-0099-test.md").write_text(
            TASK.format(external="").replace("status: open", "status: done")
            + "\n" + body + "\n",
            encoding="utf-8")

    def _run_lenient(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tv.main([])
        return code, buf.getvalue()

    def test_text_naming_a_path_that_resolves_elsewhere_is_reported(self):
        # The defect itself. The text names `README.md`, which is a real file at the
        # repository root; the target opens `.tasks/README.md`. Both exist, so nothing
        # dangles and only this check can see the difference.
        self._write("[`README.md`](../README.md) says the installer is idempotent.")
        code, out = self._run()
        self.assertNotEqual(
            code, 0,
            f"a link opening a file its text does not name must be reported\n{out}")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn("../README.md", out)
        self.assertIn(".tasks/README.md", out)

    def test_text_naming_the_path_it_actually_opens_is_not_reported(self):
        # The true-negative half of the pair above. Without it the check could pass for
        # the wrong reason, by firing on any path-shaped link text rather than on a
        # mismatch. `.tasks/README.md` is what `../README.md` means from done/, so this
        # link is correct and must stay silent.
        self._write("[`.tasks/README.md`](../README.md) has 6 relative links.")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_prose_link_text_is_not_reported(self):
        # Link text that reads as a sentence names no path, so there is nothing to
        # compare and nothing to claim. Firing here would be the expensive failure: it
        # pressures an author into rewording a historical record to satisfy a checker.
        self._write("See [the readme](../README.md) for the spine.")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_path_with_a_line_suffix_is_not_reported(self):
        # `path:line` is a citation of a location, not a claim about which file the link
        # opens, and this exact link is correct today in done/bug-0002. Under the
        # prefer-under-firing rule the suffix form is left alone rather than parsed.
        self._write("[`.tasks/README.md:29`](../README.md) cites section 5.")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_link_inside_a_single_backtick_code_span_is_not_reported(self):
        # `bug-0015`: a backticked link renders as literal text and is not clickable by
        # anyone, so there is no reader to mislead and nothing to report. This is the
        # form `bug-0012`'s own Problem table uses to quote the wrong link, which is
        # what a task file documenting a link bug has to be able to do.
        self._write("`[README.md](../README.md)` renders as text, not as a link.")
        code, out = self._run()
        self.assertEqual(code, 0, f"a backticked link is not a link\n{out}")

    def test_a_link_inside_a_double_backtick_code_span_is_not_reported(self):
        # `bug-0015`: markdown opens a code span with a run of backticks of any length,
        # and the double form is what an author reaches for when the quoted text itself
        # contains a backtick. `bug-0012`'s Implementation notes use exactly this, so a
        # fix that knows only the single form leaves that file still failing.
        self._write("It fires on `` [`README.md`](../README.md) `` from done/.")
        code, out = self._run()
        self.assertEqual(code, 0, f"a double-backtick span is a code span too\n{out}")

    def test_a_link_inside_a_fenced_code_block_is_not_reported(self):
        # `bug-0017`: a fence's delimiters sit alone on lines of their own, so the
        # within-a-line pairing in code_span_ranges() never matches them and a link that
        # renders as literal text inside a fence went on being reported after the inline
        # form was fixed. Quoting a whole broken link in a fenced block is what a task
        # file documenting a link bug has to be able to do: `chore-0029`'s own Problem
        # section quotes a CI failure this way.
        self._write(
            "The docs link step printed:\n\n"
            "```\n"
            "[README.md](../README.md)\n"
            "```\n")
        code, out = self._run()
        self.assertEqual(code, 0, f"a fenced link is not a link\n{out}")

    def test_a_mislabelled_link_outside_a_code_span_is_still_reported(self):
        # `bug-0015`'s risk section, extended by `bug-0017`: over-skipping costs more
        # than the false positive it removes, because a disabled check reports success.
        # This is the guard against both skips failing open at once. A span detector
        # that paired backticks across the whole file would let the unmatched backtick
        # below swallow the genuine link, and a fence detector that ran an unclosed
        # fence to end of file would swallow it too; either way this file would pass for
        # the wrong reason. The fence here is closed and the link on the last line sits
        # outside it, names the root README.md, opens .tasks/README.md, and must still
        # be reported.
        self._write(
            "The shape `[README.md](../README.md)` is literal text, and a lone ` "
            "backtick opens nothing.\n\n"
            "```md\n"
            "[README.md](../README.md)\n"
            "```\n\n"
            "See [`README.md`](../README.md) for the installer.")
        code, out = self._run()
        self.assertNotEqual(
            code, 0,
            f"a real mislabelled link must survive the code-span skip\n{out}")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn("../README.md", out)
        self.assertIn(".tasks/README.md", out)

    def test_an_unterminated_fence_does_not_suppress_the_findings_after_it(self):
        # `bug-0017`: the costly failure named in its risk section. An opening fence with
        # no closer must open nothing, exactly as an unmatched backtick run opens
        # nothing, because the alternative switches the check off for the whole rest of
        # the file and still exits clean. The link below the dangling fence is genuinely
        # mislabelled and is the only thing standing between that failure and a green
        # build, so it must be reported.
        self._write(
            "```md\n"
            "a fence that is never closed\n"
            "\n"
            "See [`README.md`](../README.md) for the installer.")
        code, out = self._run()
        self.assertNotEqual(
            code, 0,
            f"an unterminated fence must not suppress what follows it\n{out}")
        self.assertIn("feat-0099-test.md", out)
        self.assertIn(".tasks/README.md", out)

    def test_the_finding_is_a_warning_rather_than_an_error(self):
        # A deliberate, recorded decision, not an accident of implementation. The check
        # is a heuristic and it ships to every scaffolded repository, so a default run
        # reports it without failing; only --strict, which this repository's CI uses,
        # promotes it. A heuristic that fails an adopter's clean tree is the failure
        # this task's risk section says costs most.
        self._write("[`README.md`](../README.md) says the installer is idempotent.")
        code, out = self._run_lenient()
        self.assertEqual(code, 0, f"a default run must not fail on a heuristic\n{out}")
        self.assertIn("WARN", out)
        self.assertIn("../README.md", out)


class DocsLinkModeTests(TasksRootTestCase):
    """`chore-0029`: the docs link gate calls this rule instead of restating it.

    The rule for what counts as a relative link and whether it resolves was authored
    three times: in `.tasks/validate.py`, in the `init-worktracking` template, and inline
    in a heredoc inside `.github/workflows/checks.yml`. The first two were kept in step
    deliberately; the third was not, and it drifted. A `CHANGELOG.md` entry that quoted a
    malformed link inside a code span passed `--strict` and failed CI, and the entry was
    reworded to satisfy a checker rather than to say what it meant.

    The two file sets stay disjoint on purpose, so these tests pin the caller, not the
    coverage. The failure worth designing against is not a missed broken link: it is a
    check that runs over nothing, because a wrong glob makes the gate pass instantly,
    report zero broken links over zero documents, and turn a broken tree green.
    """

    def _run_links(self, *patterns):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tv.main(["--links", *patterns])
        return code, buf.getvalue()

    def test_a_broken_relative_link_in_a_matched_document_fails(self):
        # The gate's whole job, over a file set validate.py's backlog walk never sees.
        # Wave 2's closeout broke three links in exactly this position, in CHANGELOG.md
        # and ROADMAP.md, which `--strict` passed clean over.
        (self.root / "CHANGELOG.md").write_text(
            "See [the plan](ROADMAP.md).\n", encoding="utf-8")
        code, out = self._run_links("*.md")
        self.assertNotEqual(code, 0, f"a dangling link must exit non-zero\n{out}")
        self.assertIn("broken link: CHANGELOG.md -> ROADMAP.md", out)

    def test_a_resolving_link_passes_and_the_document_count_is_reported(self):
        # The count is load-bearing, not decoration: it is the only thing in the output
        # that distinguishes a clean run from a run over an empty file set, and both
        # print zero broken links. `docs/guide.md` also pins that a target resolves from
        # the document's own directory rather than from the repository root, which is
        # what makes `../README.md` correct here and wrong one directory down.
        (self.root / "CHANGELOG.md").write_text(
            "See [the readme](README.md).\n", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "guide.md").write_text(
            "See [the readme](../README.md).\n", encoding="utf-8")
        code, out = self._run_links("*.md", "docs/**/*.md")
        self.assertEqual(code, 0, out)
        self.assertIn("checked 3 documents, 0 broken link(s)", out)

    def test_patterns_that_match_no_document_fail_rather_than_pass_silently(self):
        # The failure this mode is designed against. A glob that stops matching (a
        # renamed directory, a moved docs tree) would otherwise report success while
        # checking nothing, which is worse than a broken link because it is invisible.
        code, out = self._run_links("no-such-directory/**/*.md")
        self.assertNotEqual(
            code, 0, f"a check over zero documents must not pass\n{out}")
        self.assertIn("checked 0 documents", out)
        self.assertIn("no-such-directory/**/*.md", out)


class ValidatorCopiesAgreeTests(unittest.TestCase):
    """`bug-0023` and `bug-0026`: the two copies move together or not at all.

    `.tasks/validate.py` and the `init-worktracking` template are deliberate near
    duplicates, because a scaffolded repository has no way to import from this one. The
    duplication is tolerated; the drift is not, and it has already happened twice. A
    third copy inline in CI learned nothing from `bug-0015` and disagreed with this file
    about what counts as a link while a comment said the two could not (`chore-0029`).
    Then `bug-0026` found the `external` check and `main(argv=None)` in this copy alone.

    Docstrings are compared by nobody here on purpose: they are retargeted at a
    scaffolded repository rather than at this one, so they are expected to differ
    (`bug-0017`). The executable code is not.
    """

    LINK_FUNCTIONS = ("broken_links", "code_span_ranges", "fenced_block_ranges",
                      "mislabelled_links", "check_links")
    # The regexes both copies use to decide what a link is and where it may not count.
    # This list is no longer the outer boundary of the guarantee, only a sharper message
    # for the names most likely to drift: the whole-module comparison below covers every
    # module-level name including `EXTERNAL_RE`. That distinction is what `bug-0026`
    # cost. This comment previously recorded `EXTERNAL_RE` as belonging to this
    # repository alone, so no list-driven check could ever have reported its absence
    # from the template; the guarantee has to hold over names nobody thought to enumerate.
    LINK_NAMES = ("LINK_RE", "LINK_SKIP_PREFIXES", "LINK_TEXT_RE", "TEXT_PATH_RE",
                  "LINE_SUFFIX_RE", "BACKTICK_RUN_RE", "FENCE_RE")

    @staticmethod
    def _executable_code(path):
        """Every executable statement in `path`, as comparable lines, minus docstrings.

        Compared as a dumped AST rather than as text so a comment, a line wrap, or a
        blank line can never fail this test: the template's comments are deliberately
        retargeted at a scaffolded repository and are expected to differ. Docstrings are
        dropped at module, class, and function level for the same reason. Comments never
        reach the AST at all, so they cost nothing to exclude.

        The result is split into lines so a failure renders as a diff naming the
        statement that drifted rather than as one unreadable string.
        """
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = node.body
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    node.body = body[1:]
        return ast.dump(tree, indent=1).splitlines()

    def test_the_executable_code_is_identical_in_both_copies(self):
        """The durable half of `bug-0026`: a guarantee that needs no list.

        The two tests below pin named functions and named regexes, which is precisely
        why the `external` check could be missing from the template for months with
        every gate green: a list-driven check cannot report a name that nobody added to
        the list. This one enumerates nothing, so it fails on the next rule either copy
        gains alone, whatever that rule turns out to be.

        The full comparison is affordable rather than brittle because the two files are
        near duplicates by design and their executable code is currently exact. If a
        divergence is ever introduced deliberately, narrow this to an allow-list of
        known-different nodes and say why, rather than deleting the test: the narrower
        checks below are what this replaced.
        """
        self.assertEqual(
            self._executable_code(MODULE_PATH),
            self._executable_code(TEMPLATE_PATH),
            ".tasks/validate.py and the init-worktracking template have drifted. "
            "Their docstrings and comments may differ; their executable code may not. "
            "Carry the change into both copies, or narrow this test and say why.")

    @staticmethod
    def _body_without_docstring(path, name):
        """The AST of one top-level function in `path`, minus its docstring.

        Compared as an AST rather than as text so that a comment, a line wrap, or the
        blank line between two statements never fails this test. The only difference it
        can see is a difference in what the code does.
        """
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                body = node.body
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    body = body[1:]
                return [ast.dump(stmt) for stmt in body]
        raise AssertionError(f"{path} defines no function named {name!r}")

    @staticmethod
    def _assignment(path, name):
        """The AST of one top-level `NAME = ...` assignment in `path`."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.dump(node.value)
        raise AssertionError(f"{path} assigns no name {name!r}")

    def test_the_link_functions_are_identical_in_both_copies(self):
        for name in self.LINK_FUNCTIONS:
            with self.subTest(function=name):
                self.assertEqual(
                    self._body_without_docstring(MODULE_PATH, name),
                    self._body_without_docstring(TEMPLATE_PATH, name),
                    f"{name}() differs between .tasks/validate.py and the "
                    f"init-worktracking template; both copies move together")

    def test_the_link_regexes_are_identical_in_both_copies(self):
        for name in self.LINK_NAMES:
            with self.subTest(name=name):
                self.assertEqual(
                    self._assignment(MODULE_PATH, name),
                    self._assignment(TEMPLATE_PATH, name),
                    f"{name} differs between .tasks/validate.py and the "
                    f"init-worktracking template; both copies move together")


if __name__ == "__main__":
    unittest.main()
