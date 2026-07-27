"""Acceptance tests for scripts/build-adapters.py.

Standard library only, per the conventions section of AGENTS.md.

test-quality notes: the plausible defect is a skill body inlined into an adapter
whose relative links no longer resolve, which is silent (the adapter renders fine,
the agent reading it just finds nothing where the rubric should be). Link rewriting
is pure string work and is covered at the unit layer on `rewrite_links`. The oracle
that actually protects the contract is a filesystem one, because the bug is about
where files land relative to each other, so `TestEmittedTreeResolves` emits the real
kit into a temp directory and resolves every relative link on disk. That test fails
against verbatim inlining, which is the known-bad behavior it was written for.
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


class TestRewriteLinks(unittest.TestCase):
    """The three link classes a skill body carries, plus the two it must not touch."""

    def test_sibling_skill_points_at_the_adapter_beside_it(self):
        body = "See [`fix-batch`](../fix-batch/SKILL.md) for the batch."
        self.assertIn("](fix-batch.mdc)", ba.rewrite_links(body, "code-review", ".mdc"))

    def test_sibling_skill_keeps_its_anchor(self):
        body = "Use [layer selection](../test-quality/SKILL.md#layer-selection)."
        out = ba.rewrite_links(body, "spec-plan-readiness", ".prompt.md")
        self.assertIn("](test-quality.prompt.md#layer-selection)", out)

    def test_rules_module_points_at_the_shared_location(self):
        body = "Apply the [`review-quality`](../../rules/review-quality.md) lens."
        out = ba.rewrite_links(body, "code-review", ".mdc")
        self.assertIn("](../../.agents/rules/review-quality.md)", out)

    def test_skill_local_asset_points_into_the_shared_skill_directory(self):
        body = "Templates live in [`templates/`](templates/ruff.toml)."
        out = ba.rewrite_links(body, "project-bootstrap", ".mdc")
        self.assertIn("](../../.agents/skills/project-bootstrap/templates/ruff.toml)", out)

    def test_external_and_anchor_links_are_left_alone(self):
        body = "See [spec](https://keepachangelog.com) and [below](#design-choices)."
        self.assertEqual(ba.rewrite_links(body, "pr-describe", ".mdc"), body)

    def test_link_title_is_preserved(self):
        body = 'See [`fix-batch`](../fix-batch/SKILL.md "the batch skill").'
        out = ba.rewrite_links(body, "code-review", ".mdc")
        self.assertIn('](fix-batch.mdc "the batch skill")', out)


class TestEmittedTreeResolves(unittest.TestCase):
    """The contract: every relative link in every emitted adapter resolves on disk."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ba.main(["--out", str(self.out)])

    def tearDown(self):
        self._tmp.cleanup()

    def _adapters(self):
        return sorted(list(self.out.glob(".cursor/rules/*.mdc"))
                      + list(self.out.glob(".github/prompts/*.prompt.md")))

    def test_every_relative_link_in_every_adapter_resolves(self):
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
        # code-review is the skill that loses the most to a dangling lens: its
        # severities and rubric categories live entirely in the lens file.
        lens = self.out / ".agents" / "rules" / "review-quality.md"
        self.assertTrue(lens.is_file())
        self.assertIn("blocker", lens.read_text(encoding="utf-8"))

    def test_an_existing_rules_file_is_not_clobbered(self):
        # The rules module is swappable, so a project's own copy outranks the kit's.
        lens = self.out / ".agents" / "rules" / "house-style.md"
        lens.write_text("# my own house style\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ba.main(["--out", str(self.out)])
        self.assertEqual(lens.read_text(encoding="utf-8"), "# my own house style\n")


if __name__ == "__main__":
    unittest.main()
