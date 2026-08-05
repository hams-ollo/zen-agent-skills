"""Acceptance tests for .tasks/validate.py.

Two areas, added by two tasks. The `external` field tests are derived from
docs/spec/tracker-links.md and each is tagged with the scenario id it covers. The link
tests come from `bug-0011` and have no spec behind them; the validator as a whole has no
contract yet, only the `external` field does.

Standard library only, per the conventions section of AGENTS.md.

Scope is still deliberately narrow. `.tasks/validate.py` had no test file before
`feat-0030`, and backfilling coverage for the whole validator remains separate work; the
file does not pretend to be a full suite.
"""
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".tasks" / "validate.py"

_spec = importlib.util.spec_from_file_location("zen_tasks_validate", MODULE_PATH)
tv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tv)

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
    """A throwaway repository root with a .tasks/ tree, shared by both areas."""

    def setUp(self):
        # Mirror a real repository: a root holding .tasks/ and the file the fixture
        # names in touched_files. The validator reports paths relative to REPO_ROOT,
        # so the task file has to actually live beneath it.
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tasks = self.root / ".tasks"
        self.tasks.mkdir()
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")

        self._real_tasks_dir = tv.TASKS_DIR
        self._real_repo_root = tv.REPO_ROOT
        tv.TASKS_DIR = self.tasks
        tv.REPO_ROOT = self.root

    def tearDown(self):
        tv.TASKS_DIR = self._real_tasks_dir
        tv.REPO_ROOT = self._real_repo_root
        self._tmp.cleanup()

    def _run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tv.main(["--strict"])
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


if __name__ == "__main__":
    unittest.main()
