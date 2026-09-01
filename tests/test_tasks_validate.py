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

`bug-0029` adds a third area over the same pair of files one level up: the task
template the scaffold ships alongside that validator. It had lost the `external` field
the validator now checks and the `## Decisions` section two shipped skills read it for,
so an adopter got a rule enforced and never explained.

`bug-0061` adds the dependency graph, back over the pair of validators. Every
`depends_on` entry was checked on its own and the graph the entries form was checked not
at all, so two tasks naming each other passed `--strict` at exit 0 while neither could
ever become dispatchable.

Standard library only, per the conventions section of AGENTS.md.

Scope is still deliberately narrow. `.tasks/validate.py` had no test file before
`feat-0030`, and backfilling coverage for the whole validator remains separate work; the
file does not pretend to be a full suite.
"""
import ast
import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".tasks" / "validate.py"
TEMPLATE_PATH = (REPO_ROOT / ".agents" / "skills" / "init-worktracking"
                 / "templates" / "validate.py")
TASK_TEMPLATE_PATH = REPO_ROOT / ".tasks" / "_TEMPLATE.md"
TASK_TEMPLATE_TMPL_PATH = (REPO_ROOT / ".agents" / "skills" / "init-worktracking"
                           / "templates" / "_TEMPLATE.md.tmpl")

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

    def _unmatched_lines(self, out):
        """Every `no document matched:` line, so a test can assert which pattern died.

        Asserted as whole lines rather than with `assertIn`, because the patterns
        overlap as substrings: `*.md` occurs inside `no-such-directory/**/*.md`, so a
        containment check could not tell blaming the dead pattern apart from blaming
        every pattern in the run.
        """
        return [line for line in out.splitlines()
                if line.startswith("no document matched:")]

    def test_one_pattern_matching_nothing_fails_even_when_others_match(self):
        # `chore-0032`: the guard fired per run rather than per pattern, so it caught
        # only the case where every pattern died. Measured against this repository on
        # 2026-08-27, before the fix: `--links '*.md' 'docs/**/*.md'
        # 'totally-gone/**/*.md'` reported 44 documents and exit 0, and renaming `docs/`
        # would have left the same command reporting 9 of 45 at exit 0.
        #
        # The live documents are the point of the fixture, not scenery: they are what
        # produces the reassuring count that makes the dead pattern invisible.
        (self.root / "CHANGELOG.md").write_text(
            "See [the readme](README.md).\n", encoding="utf-8")
        code, out = self._run_links("*.md", "no-such-directory/**/*.md")
        self.assertNotEqual(
            code, 0,
            f"a dead pattern must fail the run even when another matches\n{out}")
        self.assertIn("checked 2 documents, 0 broken link(s)", out)

    def test_the_failure_names_the_pattern_that_matched_nothing(self):
        # "No document matched" without saying which glob died sends the reader to
        # check every pattern by hand, and being self-explaining is the whole value
        # here. The live pattern must not be blamed alongside the dead one.
        (self.root / "CHANGELOG.md").write_text(
            "See [the readme](README.md).\n", encoding="utf-8")
        _code, out = self._run_links("*.md", "no-such-directory/**/*.md")
        self.assertEqual(
            self._unmatched_lines(out),
            ["no document matched: no-such-directory/**/*.md"],
            f"exactly the dead pattern is named\n{out}")

    def test_every_pattern_dead_still_fails_and_names_each_of_them(self):
        # The guard the per-pattern rule replaces, kept rather than superseded. A
        # stricter rule that stopped covering the all-dead case would be a regression
        # hidden inside a fix, and it is the case the mode was originally built for.
        code, out = self._run_links("gone/**/*.md", "also-gone/**/*.md")
        self.assertNotEqual(code, 0, f"no pattern matched anything\n{out}")
        self.assertIn("checked 0 documents", out)
        self.assertEqual(
            sorted(self._unmatched_lines(out)),
            ["no document matched: also-gone/**/*.md",
             "no document matched: gone/**/*.md"],
            f"each dead pattern is named, not merely counted\n{out}")

    def test_the_mode_with_no_pattern_at_all_still_fails(self):
        # `--links` with nothing after it is the degenerate input, and it reaches the
        # per-pattern loop with nothing to iterate. Without its own branch the run
        # would report zero documents, find no pattern to blame, and exit 0, which is
        # the exact shape this mode exists to make impossible.
        code, out = self._run_links()
        self.assertNotEqual(code, 0, f"a run over no pattern must not pass\n{out}")
        self.assertIn("no pattern given", out)


class TemplateDocsLinkModeTests(unittest.TestCase):
    """`chore-0032`: the per-pattern guard in the tree the scaffold actually lands in.

    Driven as a subprocess over a bare scaffolded tree for the reason
    `TemplateStandaloneTests` gives: what matters is the file surviving the trip into a
    repository holding nothing else from this kit.

    The case worth pinning is the one the task's risk section named as costliest, a gate
    that now fails for a legitimate reason. A scaffolded repository may have no
    `.github/` and no `docs/`, so a caller that passes the patterns it actually has must
    pass, and only a caller naming a tree that is not there may fail. That is also why
    the template's usage line documents `'*.md'` alone and adds `'docs/**/*.md'` as
    conditional prose: no scaffolded caller can then carry a pattern it does not have.
    """

    def _scaffold(self, tmp):
        """A repository with a tracker, two documents, and no `.github/` or `docs/`."""
        root = Path(tmp)
        tasks = root / ".tasks"
        tasks.mkdir()
        (tasks / "validate.py").write_text(
            TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "README.md").write_text(
            "See [the changelog](CHANGELOG.md).\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "See [the readme](README.md).\n", encoding="utf-8")
        return root, tasks

    def _run_links(self, root, tasks, *patterns):
        return subprocess.run(
            [sys.executable, str(tasks / "validate.py"), "--links", *patterns],
            capture_output=True, text=True, cwd=str(root))

    def test_a_repository_with_no_github_or_docs_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, tasks = self._scaffold(tmp)
            proc = self._run_links(root, tasks, "*.md")
        self.assertEqual(
            proc.returncode, 0,
            f"the patterns a scaffolded repository has must not fail\n"
            f"{proc.stdout}\n{proc.stderr}")
        self.assertIn("checked 2 documents, 0 broken link(s)", proc.stdout)

    def test_the_same_tree_fails_when_a_caller_names_a_directory_it_lacks(self):
        # The other half of the pair. Without it the test above would pass just as well
        # against a guard that had been deleted, and there is deliberately no way to
        # mark a pattern optional: a caller in a repository with no `docs/` drops the
        # pattern instead of relaxing the rule.
        with tempfile.TemporaryDirectory() as tmp:
            root, tasks = self._scaffold(tmp)
            proc = self._run_links(root, tasks, "*.md", "docs/**/*.md")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("no document matched: docs/**/*.md", proc.stdout)


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


class TaskTemplateCopiesAgreeTests(unittest.TestCase):
    """`bug-0029`: the two task templates carry the same fields and sections.

    `.tasks/_TEMPLATE.md` and the copy `init-worktracking` scaffolds are the same
    contract stated twice, for the same reason the validator is: a scaffolded repository
    has no way to read this one. The template one directory up from the validator drifted
    in exactly the way `bug-0026` found the validator itself had. It lost the `external`
    field, so `pr-describe`'s closing reference could never fire in a scaffolded
    repository, and it lost `## Decisions`, which `fix-batch` names as the definition of
    the admissible entry kinds it dispatches agents to fill in. Neither absence announced
    itself, because a skill pointing at a section that does not exist still reads
    correctly.

    Only the field names and the section headings are compared. The prose under them is
    deliberately retargeted at a scaffolded repository (`bug-0017`) and is supposed to
    differ, so pinning it would fail on every honest edit and teach the next author to
    delete this test.
    """

    @staticmethod
    def _frontmatter_keys(path):
        """The frontmatter keys of `path`, read by the validator's own parser.

        Parsed rather than pattern-matched so the test agrees with the code an adopter
        actually runs: a key this parser cannot see is a key no validator will check.
        """
        parsed = tv.parse_frontmatter(path.read_text(encoding="utf-8"))
        if parsed is None:
            raise AssertionError(f"{path} has no frontmatter block")
        return set(parsed)

    @staticmethod
    def _headings(path):
        """The `## ` section headings of `path`, as a set."""
        return set(re.findall(
            r"^## (.+)$", path.read_text(encoding="utf-8"), flags=re.MULTILINE))

    def test_the_frontmatter_fields_are_identical_in_both_templates(self):
        self.assertEqual(
            self._frontmatter_keys(TASK_TEMPLATE_PATH),
            self._frontmatter_keys(TASK_TEMPLATE_TMPL_PATH),
            ".tasks/_TEMPLATE.md and the init-worktracking task template offer "
            "different frontmatter fields. Their comments may be retargeted; the set "
            "of fields may not differ. Carry the field into both copies.")

    def test_the_section_headings_are_identical_in_both_templates(self):
        self.assertEqual(
            self._headings(TASK_TEMPLATE_PATH),
            self._headings(TASK_TEMPLATE_TMPL_PATH),
            ".tasks/_TEMPLATE.md and the init-worktracking task template offer "
            "different sections. Their prose may be retargeted; the set of headings "
            "may not differ. Carry the section into both copies.")


class ScaffoldedTaskTemplateTests(TasksRootTestCase):
    """`bug-0029`: what the scaffold ships still passes what the scaffold validates.

    The two halves land in an adopter's repository together, so the field the template
    now offers has to be one the shipped validator accepts. Driven against the template
    validator rather than this repository's copy, because the adopter runs that one.
    """

    module = tvt

    def test_the_shipped_template_filled_in_with_an_external_value_validates(self):
        filled = (TASK_TEMPLATE_TMPL_PATH.read_text(encoding="utf-8")
                  .replace("id: TYPE-NNNN", "id: feat-0099")
                  .replace('external: ""', 'external: "#123"')
                  .replace("  - path/to/file/the/task/will/change", "  - README.md")
                  .replace("  - path/to/its/test", "  - README.md")
                  .replace("created: YYYY-MM-DD", "created: 2026-08-19"))
        self.assertIn('external: "#123"', filled,
                      "the shipped template offers no external field to fill in")
        (self.tasks / "feat-0099-test.md").write_text(filled, encoding="utf-8")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_the_lite_form_parent_validates_against_the_shipped_validator(self):
        """`bug-0030`: at lite there is no ROADMAP.md, so `parent` holds free text.

        That task verified this by hand and deliberately added no test, to stay inside
        its `touched_files` while a sibling was editing this module. The collision did
        not materialise, so the check is pinned here instead of resting on one run.
        """
        stripped = (TASK_TEMPLATE_TMPL_PATH.read_text(encoding="utf-8")
                    .replace("id: TYPE-NNNN", "id: feat-0098")
                    .replace('parent: "ROADMAP#N feature-slug"',
                             'parent: "offline-first sync"')
                    .replace("  - path/to/file/the/task/will/change", "  - README.md")
                    .replace("  - path/to/its/test", "  - README.md")
                    .replace("created: YYYY-MM-DD", "created: 2026-08-19"))
        self.assertIn('parent: "offline-first sync"', stripped,
                      "the lite substitution did not replace the seeded parent value")
        self.assertNotIn('parent: "ROADMAP#N', stripped,
                         "the ROADMAP-form parent survived the substitution")
        (self.tasks / "feat-0098-test.md").write_text(stripped, encoding="utf-8")
        code, out = self._run()
        self.assertEqual(code, 0, out)


class UndecodableFileTests(TasksRootTestCase):
    """chore-0081: one stray byte took the whole validator down with a traceback.

    The population is a file that is not UTF-8, which is the contract every file this reads
    is held to. Before this, `read_text(encoding="utf-8")` with no handler meant a single
    byte anywhere in `.tasks/` killed the run on a `UnicodeDecodeError` that named no file
    and read as a defect in the validator rather than a diagnosis of the file.

    Reported and skipped, never read past. `errors="ignore"` was rejected in the task: a
    task file whose frontmatter is quietly mangled would validate, which is worse than the
    traceback it replaces.
    """

    module = tv

    def _write_undecodable(self, name="bug-0001-probe.md"):
        path = self.tasks / name
        path.write_bytes(TASK.format(external="").encode("utf-8") + b"\xff\xfe rubbish")
        return path

    def test_an_undecodable_task_file_is_reported_rather_than_raising(self):
        self._write_undecodable()
        code, out = self._run()          # would raise before the fix, not return
        self.assertEqual(code, 1, out)
        self.assertIn("not valid UTF-8", out)
        self.assertIn("bug-0001-probe.md", out)

    def test_the_message_names_the_byte_and_its_offset(self):
        # The message is the deliverable, not the catch. Path, offset and byte are what turn
        # a five-minute puzzle into a one-line fix.
        self._write_undecodable()
        _, out = self._run()
        self.assertIn("0xff", out)
        self.assertRegex(out, r"at offset \d+")

    def test_each_check_that_could_not_run_says_which_one_it_was(self):
        # Two checks read the same file and both must report it. An identical sentence twice
        # leaves a reader unable to tell which check could not run, so they are distinct.
        self._write_undecodable()
        _, out = self._run()
        self.assertIn("frontmatter could not be read", out)
        self.assertIn("links could not be checked", out)

    def test_the_file_is_skipped_rather_than_read_past(self):
        # The fix must not be an `errors="ignore"` in disguise. A mangled file that still
        # parsed would be counted as a valid task, so the count is the assertion.
        self._write_undecodable()
        _, out = self._run()
        self.assertNotIn("0 error(s)", out,
                         "an undecodable file passed validation, which means it was read "
                         "past rather than reported")

    def test_a_good_tree_is_unaffected(self):
        # The negative case. A validator that reports every file as undecodable would satisfy
        # every assertion above.
        (self.tasks / "feat-0099-test.md").write_text(TASK.format(external=""),
                                                      encoding="utf-8")
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn("not valid UTF-8", out)


class UndecodableFileTemplateTests(UndecodableFileTests):
    """The same behaviour in the copy `init-worktracking` writes into other repositories.

    Run against the template as a loaded module rather than compared as text, because the two
    files deliberately differ: the template is the generic version, and this repository's copy
    carries its own history in its comments. `chore-0081` was filed asking that the two
    "match", which was a false premise: they were already 119 lines apart by design. What has
    to match is the behaviour, which is what subclassing asserts.
    """

    module = tvt


class ScaffoldManifestTests(TasksRootTestCase):
    """`chore-0060`: the id high-water mark in the scaffold manifest, read at last.

    `.tasks/.scaffold.json` records the highest id in use per type, and `new-task` tells
    an author to prefer it over scanning the tree. Nothing read it. A search for
    `scaffold.json` and `id_high_water` across the skills, the tracker, the tests and
    the scripts returned six hits and every one was prose in a skill body: no validator,
    no gate, no test. It had drifted below the backlog while every gate stayed green, so
    an agent following the instruction as written was handed ids that were already
    taken, and found out from the duplicate-id error, after the task files existed and
    had been cross-referenced.

    The population is a manifest that disagrees with the tree it describes. The cases
    that must stay silent matter as much as the one that must fire: this validator ships
    into every repository the scaffold touches, and a warning on a clean adopter tree is
    the outcome this file's own comments say to design against.
    """

    module = tv

    def _write_task(self, tid):
        """Write one open task file carrying `tid`, named after it."""
        ttype = tid.split("-", 1)[0]
        text = (TASK.format(external="")
                .replace("id: feat-0099", f"id: {tid}")
                .replace("type: feat", f"type: {ttype}"))
        (self.tasks / f"{tid}-test.md").write_text(text, encoding="utf-8")

    def _manifest_path(self):
        return self.tasks / self.module.SCAFFOLD_MANIFEST

    def _write_manifest(self, raw):
        """Write the manifest verbatim, so a malformed one is expressible."""
        self._manifest_path().write_text(raw, encoding="utf-8")

    def _write_high_water(self, **recorded):
        self._write_manifest(json.dumps({"generator": "init-worktracking",
                                         "id_high_water": recorded}))

    def _run_lenient(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.module.main([])
        return code, buf.getvalue()

    def test_a_recorded_high_water_below_the_tree_is_reported(self):
        # The defect itself, and the acceptance criterion. chore-0007 is in the tree and
        # the manifest says the highest chore is 5, which is exactly the state that
        # hands the next author an id already taken.
        self._write_task("chore-0007")
        self._write_high_water(chore=5)
        code, out = self._run()
        self.assertEqual(code, 1, f"--strict must fail on a stale manifest\n{out}")
        self.assertIn(".scaffold.json", out)
        self.assertIn("chore-0007", out)

    def test_the_finding_names_both_numbers(self):
        # The message is the deliverable. "The manifest is stale" sends the reader off
        # to scan the tree by hand, which is the work the record exists to save.
        self._write_task("chore-0007")
        self._write_high_water(chore=5)
        _, out = self._run()
        self.assertIn("is 5", out)
        self.assertIn("chore-0007", out)

    def test_the_finding_is_a_warning_that_only_strict_promotes(self):
        # A recorded decision, not an accident of implementation, and the same one the
        # mislabelled-link check made: a default run in an adopter's tree reports this
        # without failing, and only --strict, which a backlog gate runs, promotes it.
        self._write_task("chore-0007")
        self._write_high_water(chore=5)
        code, out = self._run_lenient()
        self.assertEqual(code, 0,
                         f"a default run must not fail an adopter's tree\n{out}")
        self.assertIn("WARN", out)
        self.assertIn(".scaffold.json", out)

    def test_a_manifest_level_with_the_tree_is_silent(self):
        self._write_task("chore-0007")
        self._write_high_water(chore=7)
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_a_manifest_ahead_of_the_tree_is_silent(self):
        # Ahead is the normal state, not a finding: an id is consumed when a task is
        # authored, and a task can be abandoned without its id ever being reused.
        self._write_task("chore-0007")
        self._write_high_water(chore=9)
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_a_type_the_tree_has_never_used_is_not_compared(self):
        # The adopter case the task named outright: a scaffolded tree that has never
        # filed a bug must not be told its bug high-water is wrong. The seeded manifest
        # lists all four types with zeros, and three of them match nothing for a long
        # time.
        self._write_task("chore-0007")
        self._write_high_water(bug=0, feat=0, chore=7, epic=0)
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_an_absent_manifest_is_not_a_finding(self):
        # A tracker with no manifest has no second source of truth to be wrong about.
        self._write_task("chore-0007")
        self.assertFalse(self._manifest_path().exists())
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_a_manifest_without_the_key_is_not_a_finding(self):
        self._write_task("chore-0007")
        self._write_manifest(json.dumps({"generator": "init-worktracking",
                                         "tier": "lite"}))
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_an_empty_high_water_object_is_not_a_finding(self):
        self._write_task("chore-0007")
        self._write_high_water()
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".scaffold.json", out)

    def test_a_manifest_that_is_not_valid_json_is_reported_rather_than_raising(self):
        # This check reads a file nothing else here reads, so a corrupt one must not
        # take the run down. Reporting rather than skipping is the other half: a
        # manifest that cannot be parsed is a guard that has silently stopped guarding,
        # which is the failure this check was added to close rather than to join.
        self._write_task("chore-0007")
        self._write_manifest("{ not json at all\n")
        code, out = self._run()          # would raise if the parse were unguarded
        self.assertEqual(code, 1, out)
        self.assertIn(".scaffold.json", out)
        self.assertIn("not valid JSON", out)

    def test_a_manifest_that_is_not_utf8_is_reported_rather_than_raising(self):
        self._write_task("chore-0007")
        self._manifest_path().write_bytes(
            b'{"id_high_water": {"chore": 5}, "note": "\xff\xfe"}')
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("not valid UTF-8", out)

    def test_a_high_water_that_is_not_a_number_is_reported_rather_than_skipped(self):
        # Same reasoning as the unreadable manifest: a value no comparison can use means
        # the check quietly does nothing while the record still looks authoritative.
        self._write_task("chore-0007")
        self._write_high_water(chore="7")
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn(".scaffold.json", out)

    def test_a_boolean_is_not_mistaken_for_a_number(self):
        # `True == 1` in Python, so a bool passes an isinstance(int) test and would be
        # compared as the number one, reporting a stale high-water that says nothing
        # about what is actually wrong with the file.
        self._write_task("chore-0007")
        self._write_high_water(chore=True)
        _, out = self._run()
        self.assertIn("not a whole number", out)

    def test_a_current_manifest_over_a_real_backlog_is_unaffected(self):
        # The negative case. A check that reported every manifest it read would satisfy
        # the assertions above without telling two states apart.
        self._write_task("chore-0007")
        self._write_task("bug-0003")
        self._write_high_water(bug=3, feat=0, chore=7, epic=0)
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertIn("0 error(s), 0 warning(s)", out)


class ScaffoldManifestTemplateTests(ScaffoldManifestTests):
    """The same guard in the copy `init-worktracking` writes into other repositories.

    The manifest is written by that skill, into the tree this template lands in, so the
    adopter's copy is where a stale high-water actually costs an id. Run as a loaded
    module rather than compared as text, for the reason the undecodable-file suite gives
    above: the two files differ by design, and it is the behaviour that has to match.
    """

    module = tvt


class DependencyCycleTests(TasksRootTestCase):
    """`bug-0061`: a ring of depends_on edges that no dispatch can ever satisfy.

    The validator checked each edge on its own, that it is not the task's own id and that
    it names a task that exists, and nothing about the graph the edges form. A task naming
    itself was caught; two tasks naming each other were not, and neither was any longer
    ring. The lifecycle rule is that a task is dispatchable once every id in its
    depends_on is in done/, so no member of a ring can ever reach that state, and the gate
    certified the pair valid at exit 0. The only thing that surfaced it was a person
    noticing that a batch had nothing ready.

    The cases that must stay silent matter as much as the one that must fire. This
    validator ships into every repository the scaffold touches, and failing a clean
    adopter backlog over a diamond, or over a dependency that is already done, is the
    outcome that gets a check switched off.
    """

    module = tv

    def _write_task(self, tid, depends_on=(), done=False):
        """One task file carrying `tid` and the dependencies it names."""
        ttype = tid.split("-", 1)[0]
        deps = "".join(f"\n  - {dep}" for dep in depends_on) or " []"
        text = (TASK.format(external="")
                .replace("id: feat-0099", f"id: {tid}")
                .replace("type: feat", f"type: {ttype}")
                .replace("depends_on: []", f"depends_on:{deps}"))
        directory = self.tasks
        if done:
            text = text.replace("status: open", "status: done")
            directory = self.tasks / "done"
            directory.mkdir(exist_ok=True)
        (directory / f"{tid}-test.md").write_text(text, encoding="utf-8")

    def _write_scalar_task(self, tid, dep):
        """One task file whose depends_on is a bare scalar rather than a list.

        Legal YAML, and a shape a person writes by hand for a single dependency. It
        differs from _write_task above in exactly that: the value is not a list.
        """
        ttype = tid.split("-", 1)[0]
        text = (TASK.format(external="")
                .replace("id: feat-0099", f"id: {tid}")
                .replace("type: feat", f"type: {ttype}")
                .replace("depends_on: []", f"depends_on: {dep}"))
        (self.tasks / f"{tid}-test.md").write_text(text, encoding="utf-8")

    @staticmethod
    def _cycle_lines(out):
        """The reported cycle lines, whole, so a change to the message cannot slip by."""
        return [line for line in out.splitlines() if "depends_on cycle" in line]

    @staticmethod
    def _unresolved_lines(out):
        """The reported unresolved-dependency lines, whole.

        Whole rather than counted, because the defect this pins is what the message
        names: one line per character reads as nine unrelated findings.
        """
        return [line for line in out.splitlines() if "depends_on unresolved" in line]

    def test_a_two_node_cycle_is_reported_as_an_error(self):
        # The defect itself. Two otherwise valid tasks naming each other, which passed
        # --strict at exit 0 while neither could ever be dispatched.
        self._write_task("feat-0098", ["feat-0099"])
        self._write_task("feat-0099", ["feat-0098"])
        code, out = self._run()
        self.assertEqual(code, 1, f"--strict must fail on a dependency cycle\n{out}")
        self.assertEqual(
            self._cycle_lines(out),
            ["ERROR .tasks/feat-0098-test.md: depends_on cycle: "
             "feat-0098 -> feat-0099 -> feat-0098"],
            out)

    def test_a_cycle_leaves_the_count_line_accurate(self):
        # run-checks.py parses this line, so a finding that never reaches the count is a
        # finding the acceptance command reports as a pass.
        self._write_task("feat-0098", ["feat-0099"])
        self._write_task("feat-0099", ["feat-0098"])
        _, out = self._run()
        self.assertIn("Checked 2 task files: 1 error(s), 0 warning(s).", out)

    def test_a_three_node_cycle_is_reported_as_an_error(self):
        # Nothing about the check is special to a pair, and a longer ring is the harder
        # one for a reader to see by hand.
        self._write_task("feat-0098", ["feat-0099"])
        self._write_task("feat-0099", ["feat-0100"])
        self._write_task("feat-0100", ["feat-0098"])
        code, out = self._run()
        self.assertEqual(code, 1, f"--strict must fail on a dependency cycle\n{out}")
        self.assertEqual(
            self._cycle_lines(out),
            ["ERROR .tasks/feat-0098-test.md: depends_on cycle: "
             "feat-0098 -> feat-0099 -> feat-0100 -> feat-0098"],
            out)

    def test_every_ring_is_reported_and_not_only_the_first(self):
        # Two disjoint rings. Stopping at the first sends the reader back for a second
        # run to learn about the second, which is the shape of gate that gets ignored.
        self._write_task("feat-0098", ["feat-0099"])
        self._write_task("feat-0099", ["feat-0098"])
        self._write_task("chore-0001", ["chore-0002"])
        self._write_task("chore-0002", ["chore-0001"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertEqual(
            self._cycle_lines(out),
            ["ERROR .tasks/chore-0001-test.md: depends_on cycle: "
             "chore-0001 -> chore-0002 -> chore-0001",
             "ERROR .tasks/feat-0098-test.md: depends_on cycle: "
             "feat-0098 -> feat-0099 -> feat-0098"],
            out)

    def test_the_reported_ring_starts_at_its_lowest_id(self):
        # Determinism rather than taste. The search reaches this ring through feat-0100,
        # so an unnormalised report names the same two files in an order that depends on
        # where the walk happened to enter, and the output stops being diffable.
        self._write_task("feat-0098", ["feat-0100"])
        self._write_task("feat-0100", ["feat-0099"])
        self._write_task("feat-0099", ["feat-0100"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertEqual(
            self._cycle_lines(out),
            ["ERROR .tasks/feat-0099-test.md: depends_on cycle: "
             "feat-0099 -> feat-0100 -> feat-0099"],
            out)

    def test_a_self_dependency_keeps_its_own_message(self):
        # Deliberately not folded into the cycle report: a one-node ring rendered as a
        # path is a worse message than the direct one, and the direct one is what a
        # reader gets first.
        self._write_task("feat-0098", ["feat-0098"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("depends_on lists itself: feat-0098", out)
        self.assertEqual(self._cycle_lines(out), [], out)

    def test_a_dependency_on_a_completed_task_is_valid(self):
        # A satisfied dependency, which is the state every closed task leaves behind. The
        # graph has to carry the ids in done/ or the whole ledger becomes a false
        # positive.
        self._write_task("feat-0098", ["feat-0099"])
        self._write_task("feat-0099", done=True)
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_a_ring_with_a_member_in_done_is_reported(self):
        # The case above pins a dependency *into* done/ as satisfied and silent. This is
        # the other shape and the opposite answer: a ring one of whose members lives in
        # done/ is a genuine backlog defect, because the open member waits on an id that
        # waits on it and can never be dispatched. The behaviour was already correct and
        # nothing asserted it, so a later change could make a done member terminate the
        # search and hide exactly the defect the check exists for (`chore-0089`).
        self._write_task("chore-0001", ["feat-0098"], done=True)
        self._write_task("feat-0098", ["chore-0001"])
        code, out = self._run()
        self.assertEqual(code, 1, f"--strict must fail on a ring through done/\n{out}")
        self.assertEqual(
            self._cycle_lines(out),
            ["ERROR .tasks/done/chore-0001-test.md: depends_on cycle: "
             "chore-0001 -> feat-0098 -> chore-0001"],
            out)

    def test_a_scalar_depends_on_is_read_as_one_id_and_not_as_characters(self):
        # A scalar is legal YAML and the frontmatter parser returns it as a string, so
        # the loop walked it character by character and reported one unresolved
        # dependency per letter. Harmless to the graph, since a single character is
        # never a known id, and unreadable to the person holding the output
        # (`chore-0089`).
        self._write_scalar_task("feat-0098", "feat-0099")
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertEqual(
            self._unresolved_lines(out),
            ["ERROR .tasks/feat-0098-test.md: depends_on unresolved: 'feat-0099' "
             "is not a known task id"],
            out)

    def test_a_chain_and_a_diamond_are_valid(self):
        # The false positive worth designing against. Two paths that meet again are not a
        # ring, and a search that only asks whether a node has been seen before reports
        # the second path as one.
        self._write_task("feat-0098", ["feat-0099", "feat-0100"])
        self._write_task("feat-0099", ["chore-0001"])
        self._write_task("feat-0100", ["chore-0001"])
        self._write_task("chore-0001", ["chore-0002"])
        self._write_task("chore-0002")
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertIn("Checked 5 task files: 0 error(s), 0 warning(s).", out)

    def test_a_chain_deeper_than_the_recursion_limit_is_walked(self):
        # Driven against the helper rather than through a fixture of files, because the
        # property is about the search and not about the backlog: the recursive form of
        # this walk dies on a chain longer than the interpreter's own limit, which is a
        # real failure over a directory of arbitrary size and an uninteresting one.
        depth = sys.getrecursionlimit() * 2
        chain = {f"feat-{n:04d}": {f"feat-{n + 1:04d}"} for n in range(depth)}
        self.assertEqual(self.module.dependency_cycles(chain), [],
                         "a chain is not a ring, however deep it runs")
        chain[f"feat-{depth:04d}"] = {"feat-0000"}
        found = self.module.dependency_cycles(chain)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "feat-0000")
        self.assertEqual(len(found[0]), depth + 1)


class TemplateDependencyCycleTests(DependencyCycleTests):
    """The same guard in the copy `init-worktracking` writes into other repositories.

    `bug-0026` is why this subclass exists rather than a sentence claiming both copies
    were changed: the check that made a shipped feature safe landed in one copy alone and
    every gate stayed green. Run as a loaded module rather than compared as text, for the
    reason the suites above give: the two files differ by design, and it is the behaviour
    that has to match.
    """

    module = tvt


class HelperCopiesAgreeTests(unittest.TestCase):
    """The three copies of the undecodable-file diagnosis produce one message.

    `.tasks/validate.py` cannot import from `scripts/`, because it ships into repositories
    where nothing named `scripts/` exists, so the helper is duplicated rather than shared.
    That is the trade `chore-0081` accepted and `chore-0059` is open on for the link helpers.
    The duplication is only safe while a test holds the copies to one message, which is this.
    """

    @staticmethod
    def _message_from(module, path):
        try:
            module.read_text_utf8(path)
        except module.NotUTF8 as exc:
            return str(exc)
        raise AssertionError("the helper decoded a file that is not UTF-8")

    def test_every_copy_of_the_helper_produces_the_identical_message(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "zen_textio", REPO_ROOT / "scripts" / "_textio.py")
        textio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(textio)

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "sample.md"
            bad.write_bytes(b"fine so far\n\xff\xfe rubbish")
            messages = {name: self._message_from(module, bad) for name, module in (
                ("scripts/_textio.py", textio),
                (".tasks/validate.py", tv),
                ("init-worktracking template", tvt),
            )}

        distinct = set(messages.values())
        self.assertEqual(len(distinct), 1,
                         "the copies of the undecodable-file diagnosis have drifted apart, "
                         f"which is what duplicating it risks: {messages}")
        only = distinct.pop()
        self.assertIn("not valid UTF-8", only)
        self.assertIn("0xff", only)
        self.assertIn("re-save it as UTF-8", only)


if __name__ == "__main__":
    unittest.main()
