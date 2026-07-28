"""Acceptance tests for the `external` field in .tasks/validate.py.

Derived from docs/spec/tracker-links.md. Each test is tagged with the scenario id it
covers. Standard library only, per the conventions section of AGENTS.md.

Scope is deliberately narrow. `.tasks/validate.py` had no test file before `feat-0030`,
and backfilling coverage for the whole validator is separate work; these cover only the
two scenarios this task owns, so the file does not pretend to be a full suite.
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


class ExternalFieldTests(unittest.TestCase):
    """Scenarios S-007 and S-008."""

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

    def _write(self, external_line):
        (self.tasks / "feat-0099-test.md").write_text(
            TASK.format(external=external_line), encoding="utf-8")

    def _run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tv.main(["--strict"])
        return code, buf.getvalue()

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


if __name__ == "__main__":
    unittest.main()
