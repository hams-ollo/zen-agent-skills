"""Acceptance tests for scripts/build-adapters.py.

Derived from the behavioral contract in docs/spec/build-adapters.md. Each test is
tagged with the scenario id it covers. Standard library only, per the conventions
section of AGENTS.md.

test-quality notes: the plausible defect is a skill body inlined into an adapter
whose relative links no longer resolve, which is silent (the adapter renders fine,
the agent reading it just finds nothing where the rubric should be). Link rewriting
is pure string work and is covered at the unit layer on `rewrite_links`. The oracle
that actually protects the contract is a filesystem one, because the bug is about
where files land relative to each other, so `TestEmittedTreeResolves` emits the real
kit into a temp directory and resolves every relative link on disk. That test fails
against verbatim inlining, which is the known-bad behavior it was written for.

Every scenario S-001 through S-013 has a covering test. The runs that write do so
into a temp directory; the one test that targets the repository itself (S-011) uses
a preview run, so it asserts the no-op without depending on it.
"""
import contextlib
import importlib.util
import io
import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "build-adapters.py"

# build-adapters.py has a hyphen in its name, so it is not importable normally.
_spec = importlib.util.spec_from_file_location("build_adapters", MODULE_PATH)
ba = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ba)

LINK = re.compile(r"\]\(([^)\s]+)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def _run(args):
    """Drive main(), returning (exit_code, captured_stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ba.main(args)
    return code, buf.getvalue()


class TestRewriteLinks(unittest.TestCase):
    """Scenarios S-003 through S-008: the three rewritten link classes, and the two left alone."""

    def test_sibling_skill_points_at_the_adapter_beside_it(self):
        # Scenario S-003.
        body = "See [`fix-batch`](../fix-batch/SKILL.md) for the batch."
        self.assertIn("](fix-batch.mdc)", ba.rewrite_links(body, "house-review", ".mdc"))

    def test_sibling_skill_keeps_its_anchor(self):
        # Scenario S-004.
        body = "Use [layer selection](../test-quality/SKILL.md#layer-selection)."
        out = ba.rewrite_links(body, "spec-plan-readiness", ".prompt.md")
        self.assertIn("](test-quality.prompt.md#layer-selection)", out)

    def test_link_title_is_preserved(self):
        # Scenario S-005.
        body = 'See [`fix-batch`](../fix-batch/SKILL.md "the batch skill").'
        out = ba.rewrite_links(body, "house-review", ".mdc")
        self.assertIn('](fix-batch.mdc "the batch skill")', out)

    def test_rules_module_points_at_the_shared_location(self):
        # Scenario S-006.
        body = "Apply the [`review-quality`](../../rules/review-quality.md) lens."
        out = ba.rewrite_links(body, "house-review", ".mdc")
        self.assertIn("](../../.agents/rules/review-quality.md)", out)

    def test_skill_local_asset_points_into_the_shared_skill_directory(self):
        # Scenario S-007.
        body = "Templates live in [`templates/`](templates/ruff.toml)."
        out = ba.rewrite_links(body, "project-bootstrap", ".mdc")
        self.assertIn("](../../.agents/skills/project-bootstrap/templates/ruff.toml)", out)

    def test_external_and_anchor_links_are_left_alone(self):
        # Scenario S-008: emitted byte-for-byte, so the oracle is whole-string equality.
        body = "See [spec](https://keepachangelog.com) and [below](#design-choices)."
        self.assertEqual(ba.rewrite_links(body, "pr-describe", ".mdc"), body)


class TestEmittedTreeResolves(unittest.TestCase):
    """Scenarios S-001, S-002, S-009, S-010: what a real run puts on disk."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        _run(["--out", str(self.out)])

    def tearDown(self):
        self._tmp.cleanup()

    def _adapters(self):
        return sorted(list(self.out.glob(".cursor/rules/*.mdc"))
                      + list(self.out.glob(".github/prompts/*.prompt.md")))

    def test_every_relative_link_in_every_adapter_resolves(self):
        # Scenarios S-003 through S-009 together, at the layer the defect lives at:
        # the unit tests prove each rewrite in isolation, this proves the result
        # actually resolves against the material the run emitted alongside it.
        broken, checked = [], 0
        for f in self._adapters():
            for target in LINK.findall(f.read_text(encoding="utf-8")):
                if target.lower().startswith(SKIP_PREFIXES):
                    continue
                checked += 1
                if not (f.parent / target.split("#")[0]).exists():
                    broken.append(f"{f.name} -> {target}")
        self.assertGreater(checked, 100, "expected the real kit's link volume")
        self.assertEqual(broken, [], f"{len(broken)} dangling link(s): {broken[:5]}")

    def test_the_review_rubric_is_emitted_with_its_content(self):
        # Scenario S-009: house-review is the skill that loses the most to a dangling
        # lens, since its severities and rubric categories live entirely in that file.
        lens = self.out / ".agents" / "rules" / "review-quality.md"
        self.assertTrue(lens.is_file())
        self.assertIn("blocker", lens.read_text(encoding="utf-8"))

    def test_each_adapter_carries_its_harness_frontmatter_and_the_banner(self):
        # Scenario S-002.
        cursor = (self.out / ".cursor" / "rules" / "house-review.mdc").read_text(encoding="utf-8")
        vscode = (self.out / ".github" / "prompts" / "house-review.prompt.md").read_text(encoding="utf-8")
        self.assertIn("alwaysApply: false", cursor)
        self.assertIn("description:", cursor)
        self.assertIn("mode: agent", vscode)
        self.assertIn("description:", vscode)
        for text in (cursor, vscode):
            self.assertIn(".agents/skills/house-review/SKILL.md", text)
            self.assertIn("Do not edit here", text)

    def test_an_existing_rules_file_is_not_clobbered(self):
        # Scenario S-010: the rules module is swappable, so a project's own copy
        # outranks the kit's. This is the contract rule with no other enforcement.
        lens = self.out / ".agents" / "rules" / "house-style.md"
        lens.write_text("# my own house style\n", encoding="utf-8")
        _run(["--out", str(self.out)])
        self.assertEqual(lens.read_text(encoding="utf-8"), "# my own house style\n")

    def test_a_rerun_refreshes_derived_assets_and_preserves_adopted_ones(self):
        # Scenario S-014. Both halves in one test, because the contrast is the
        # requirement: asserting either alone cannot distinguish a deliberate rule
        # from an accident, which is how the skill-asset half went unstated until
        # the feat-0026 audit found it outside the contract.
        edited = "EDITED BY THE ADOPTER\n"
        adopted = self.out / ".agents" / "rules" / "house-style.md"
        derived = (self.out / ".agents" / "skills" / "project-bootstrap"
                   / "templates" / "ruff.toml")
        self.assertTrue(derived.is_file(), "expected the emitted skill template")
        kit_version = derived.read_text(encoding="utf-8")

        adopted.write_text(edited, encoding="utf-8")
        derived.write_text(edited, encoding="utf-8")
        _run(["--out", str(self.out)])

        self.assertEqual(adopted.read_text(encoding="utf-8"), edited,
                         "an adopted file must survive a re-run")
        self.assertEqual(derived.read_text(encoding="utf-8"), kit_version,
                         "a derived file must be refreshed from the kit")


class TestInvocationContract(unittest.TestCase):
    """Scenarios S-001, S-011, S-012, S-013: what each way of invoking it does."""

    def test_a_single_target_emits_only_that_target(self):
        # Scenario S-001: one adapter per skill for the requested target, none for
        # the other, plus a zero exit and the summary line.
        expected = len(ba.discover_skills())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            code, printed = _run(["--target", "cursor", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(len(list(out.glob(".cursor/rules/*.mdc"))), expected)
            self.assertEqual(len(list(out.glob(".github/prompts/*"))), 0)
            self.assertIn(f"for {expected} skill(s)", printed)

    def test_a_preview_run_writes_nothing(self):
        # Scenario S-012: the defect this guards is a "preview" that is not one.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            code, printed = _run(["--out", str(out), "--dry-run"])
            self.assertEqual(code, 0)
            self.assertEqual([p for p in out.rglob("*") if p.is_file()], [])
            self.assertIn("[dry-run]", printed)

    def test_generating_into_the_kit_itself_copies_no_shared_file(self):
        # Scenario S-011: source and destination are the same file, so nothing is
        # copied onto itself. Asserted through a preview run, so this test cannot
        # write into the repository even if the no-op regressed.
        code, printed = _run(["--out", str(REPO_ROOT), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("plus 0 shared asset file(s)", printed)

    def test_an_unrecognized_target_is_rejected_and_writes_nothing(self):
        # Scenario S-013: rejected before anything is emitted, so a partial run is
        # not left behind. The valid target in the list must not save it.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            code, printed = _run(["--target", "cursor,bogus", "--out", str(out)])
            self.assertEqual(code, 2)
            self.assertIn("bogus", printed)
            self.assertEqual([p for p in out.rglob("*") if p.is_file()], [])


if __name__ == "__main__":
    unittest.main()
