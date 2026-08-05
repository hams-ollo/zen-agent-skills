"""Acceptance tests for .agents/hooks/spec-conformance-gate.py.

Covers feat-0039. Standard library only, per the conventions section of AGENTS.md.

test-quality notes: the gate reads the filesystem, so these run against real temporary
directories rather than a mocked `os.listdir`. That is still the lowest faithful layer:
the behavior under test *is* "does a sibling file exist", and a mock would assert that the
code calls a function rather than that the rule holds.

Oracles assert the exact decision and, where it matters, the presence of the escape in the
reason string. A gate whose reason omits its escape is a trap, so that is a behavior, not
cosmetics.

The defect each group protects against:
  approved     - the single most damaging regression available: treating `approved` as
                 closing blocks every spec in this repository on the hook's first run
  spec close   - the portable trigger stops firing
  task close   - the trigger this repository actually exercises stops firing
  escapes      - a block with no way out, or one that fires on unrelated files
  robustness   - a malformed payload takes down the session
"""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".agents" / "hooks" / "spec-conformance-gate.py"

_spec = importlib.util.spec_from_file_location("spec_conformance_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def run(payload):
    out = io.StringIO()
    code = gate.main(stdin=io.StringIO(json.dumps(payload)), stdout=out)
    text = out.getvalue()
    return code, (json.loads(text) if text else None)


def edit(path, cwd=None, tool="Edit"):
    payload = {"hook_event_name": "PostToolUse", "tool_name": tool,
               "tool_input": {"file_path": str(path)}}
    if cwd:
        payload["cwd"] = str(cwd)
    return payload


class GateTestCase(unittest.TestCase):
    """A throwaway repository with a spec directory and a task directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".git").mkdir()
        self.specs = self.root / "docs" / "spec"
        self.specs.mkdir(parents=True)
        self.tasks = self.root / ".tasks"
        self.tasks.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def write_spec(self, name, status, extra=""):
        p = self.specs / f"{name}.md"
        p.write_text(f"---\ntitle: {name}\nstatus: {status}\n{extra}---\n\n# {name}\n",
                     encoding="utf-8")
        return p

    def write_matrix(self, name):
        p = self.specs / f"{name}.conformance.md"
        p.write_text("---\ntitle: matrix\n---\n\n# matrix\n", encoding="utf-8")
        return p

    def write_task(self, name, status, spec_ref=None, extra=""):
        p = self.tasks / f"{name}.md"
        ref = f"spec: {spec_ref}\n" if spec_ref else ""
        p.write_text(f"---\nid: {name}\nstatus: {status}\n{ref}{extra}---\n\n# {name}\n",
                     encoding="utf-8")
        return p


class ApprovedIsNotTerminalTests(GateTestCase):
    """The deliberate divergence from upstream, pinned so a future sync cannot revert it.

    Upstream's terminal set includes `approved`. In this kit `approved` means approved for
    decomposition, not closed, and every spec in this repository carries it. Restoring it
    would block them all on the hook's first run.
    """

    def test_an_approved_spec_without_a_matrix_does_not_block(self):
        spec = self.write_spec("widget", "approved")
        code, out = run(edit(spec))
        self.assertEqual(code, 0)
        self.assertIsNone(out, "an approved spec must never be treated as closing")

    def test_approved_is_absent_from_the_terminal_set(self):
        # Asserted directly as well as behaviorally: this is the line a careless upstream
        # sync would restore, and the behavioral test above would then fail confusingly.
        self.assertNotIn("approved", gate.TERMINAL_STATUSES)

    def test_a_draft_spec_without_a_matrix_does_not_block(self):
        spec = self.write_spec("widget", "draft")
        self.assertIsNone(run(edit(spec))[1])

    def test_every_spec_in_this_repository_passes_the_gate(self):
        # The end-to-end version of the same guarantee, against the real docs/spec/.
        real = REPO_ROOT / "docs" / "spec"
        blocked = []
        for path in sorted(real.glob("*.md")):
            _, out = run(edit(path, cwd=REPO_ROOT))
            if out:
                blocked.append(path.name)
        self.assertEqual(blocked, [], f"the gate blocks this repo's own specs: {blocked}")


class SpecCloseTests(GateTestCase):
    """Shape A: a spec file reaching a terminal status."""

    def test_a_terminal_spec_without_a_matrix_blocks(self):
        spec = self.write_spec("widget", "shipped")
        code, out = run(edit(spec))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("widget.md", out["reason"])

    def test_every_terminal_status_blocks(self):
        for status in sorted(gate.TERMINAL_STATUSES):
            with self.subTest(status=status):
                spec = self.write_spec(f"s_{status}", status)
                self.assertIsNotNone(run(edit(spec))[1])

    def test_a_terminal_spec_with_a_sibling_matrix_passes(self):
        spec = self.write_spec("widget", "shipped")
        self.write_matrix("widget")
        self.assertIsNone(run(edit(spec))[1])

    def test_a_frontmatter_declaration_satisfies_the_gate(self):
        spec = self.write_spec("widget", "shipped", extra="conformance: audited in PR 12\n")
        self.assertIsNone(run(edit(spec))[1])

    def test_a_non_spec_file_is_ignored(self):
        p = self.root / "NOTES.md"
        p.write_text("---\nstatus: shipped\n---\n\n# notes\n", encoding="utf-8")
        self.assertIsNone(run(edit(p))[1])

    def test_a_type_field_marks_a_contract_outside_a_spec_directory(self):
        p = self.root / "contract.md"
        p.write_text("---\ntype: contract\nstatus: shipped\n---\n\n# c\n", encoding="utf-8")
        self.assertIsNotNone(run(edit(p))[1])


class TaskCloseTests(GateTestCase):
    """Shape B: a task claiming a spec, closing while that spec has no matrix.

    This is the trigger this repository actually exercises, because its spec lifecycle is
    `draft` -> `approved` and no spec ever reaches a terminal status.
    """

    def test_closing_a_task_whose_spec_has_no_matrix_blocks(self):
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "done", "docs/spec/widget.md")
        code, out = run(edit(task, cwd=self.root))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("docs/spec/widget.md", out["reason"])

    def test_the_same_task_passes_once_the_matrix_exists(self):
        self.write_spec("widget", "approved")
        self.write_matrix("widget")
        task = self.write_task("feat-0001", "done", "docs/spec/widget.md")
        self.assertIsNone(run(edit(task, cwd=self.root))[1])

    def test_a_task_still_in_progress_does_not_block(self):
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "in_progress", "docs/spec/widget.md")
        self.assertIsNone(run(edit(task, cwd=self.root))[1])

    def test_a_task_claiming_no_spec_does_not_block(self):
        task = self.write_task("chore-0001", "done")
        self.assertIsNone(run(edit(task, cwd=self.root))[1])

    def test_a_quoted_spec_reference_resolves(self):
        # Both quoted and bare forms occur in this repository's task files.
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "done", '"docs/spec/widget.md"')
        self.assertIsNotNone(run(edit(task, cwd=self.root))[1])

    def test_an_unresolvable_spec_reference_does_not_block(self):
        # A dangling reference is a task-file defect for validate.py to report. Blocking on
        # it would be this hook answering a question it was not asked, and would strand the
        # author with a gate they cannot clear by writing a matrix.
        task = self.write_task("feat-0001", "done", "docs/spec/nope.md")
        self.assertIsNone(run(edit(task, cwd=self.root))[1])

    def test_the_root_is_found_without_a_cwd_in_the_payload(self):
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "done", "docs/spec/widget.md")
        self.assertIsNotNone(run(edit(task))[1], "walk-up root resolution failed")

    def test_a_task_declaring_conformance_in_frontmatter_passes(self):
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "done", "docs/spec/widget.md",
                               extra="conformance: recorded in the PR body\n")
        self.assertIsNone(run(edit(task, cwd=self.root))[1])


class EscapeAndMessageTests(GateTestCase):
    """A block must name the way out, or whoever hits it uninstalls the hook."""

    def test_a_spec_block_names_both_escapes(self):
        spec = self.write_spec("widget", "shipped")
        reason = run(edit(spec))[1]["reason"]
        self.assertIn("spec-conformance", reason)
        self.assertIn("conformance:", reason)

    def test_a_task_block_names_both_escapes(self):
        self.write_spec("widget", "approved")
        task = self.write_task("feat-0001", "done", "docs/spec/widget.md")
        reason = run(edit(task, cwd=self.root))[1]["reason"]
        self.assertIn("spec-conformance", reason)
        self.assertIn("conformance:", reason)


class PayloadShapeTests(GateTestCase):
    """Both harness payload shapes reach the same decision."""

    def test_an_apply_patch_command_is_read(self):
        spec = self.write_spec("widget", "shipped")
        payload = {"hook_event_name": "PostToolUse", "tool_name": "apply_patch",
                   "tool_input": {"command": f"*** Update File: {spec}\n@@\n-a\n+b\n"}}
        self.assertIsNotNone(run(payload)[1])

    def test_a_patch_touching_several_files_blocks_on_the_offending_one(self):
        self.write_spec("clean", "shipped")
        self.write_matrix("clean")
        bad = self.write_spec("dirty", "shipped")
        command = (f"*** Update File: {self.specs / 'clean.md'}\n@@\n-a\n+b\n"
                   f"*** Update File: {bad}\n@@\n-c\n+d\n")
        payload = {"hook_event_name": "PostToolUse", "tool_name": "apply_patch",
                   "tool_input": {"command": command}}
        out = run(payload)[1]
        self.assertIsNotNone(out)
        self.assertIn("dirty.md", out["reason"])


class RobustnessTests(GateTestCase):
    """Fail open, always."""

    def test_a_wrong_event_is_silent(self):
        spec = self.write_spec("widget", "shipped")
        payload = edit(spec)
        payload["hook_event_name"] = "PreToolUse"
        self.assertIsNone(run(payload)[1])

    def test_malformed_json_exits_zero_silently(self):
        out = io.StringIO()
        self.assertEqual(gate.main(stdin=io.StringIO("not json {{"), stdout=out), 0)
        self.assertEqual(out.getvalue(), "")

    def test_a_missing_file_is_silent(self):
        self.assertIsNone(run(edit(self.root / "gone.md"))[1])

    def test_a_file_without_frontmatter_is_silent(self):
        p = self.specs / "plain.md"
        p.write_text("# just a heading\n", encoding="utf-8")
        self.assertIsNone(run(edit(p))[1])

    def test_a_non_object_payload_is_silent(self):
        for text in ("[]", '"s"', "42", "null"):
            with self.subTest(payload=text):
                out = io.StringIO()
                self.assertEqual(gate.main(stdin=io.StringIO(text), stdout=out), 0)
                self.assertEqual(out.getvalue(), "")

    def test_a_directory_named_like_a_file_is_survived(self):
        d = self.specs / "weird.md"
        d.mkdir()
        self.assertIsNone(run(edit(d))[1])


if __name__ == "__main__":
    unittest.main()
