"""Acceptance tests for scripts/validate-skills.py.

Derived from the behavioral contract in docs/spec/validate-skills.md via the test-author
skill (in-kit dogfood, 2026-07-24). Each test is tagged with the scenario id it covers.
Standard library only, per AGENTS.md section 6.

test-quality notes: the parsing scenarios are covered at the lowest faithful layer (unit tests
on parse_frontmatter, a pure function); the whole-run scenarios are covered at the component
layer (main() against temporary fixture skill directories). Oracles assert exact observable
outcomes: the exit code plus the specific error or warning text, never "does not crash".

Scenario S-008 ("description states what and when") is intentionally not covered: the
implementation only length-proxies it, an accepted divergence recorded in
docs/spec/validate-skills.conformance.md. Writing a passing test there would assert behavior that
does not exist.
"""
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "validate-skills.py"

# validate-skills.py has a hyphen in its name, so it is not importable by a normal import.
_spec = importlib.util.spec_from_file_location("validate_skills", MODULE_PATH)
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)

GOOD_FM = "---\nname: {name}\ndescription: {desc}\n---\n"
LONG_DESC = ("Use this skill when you need a thorough action whose description states both what it "
             "does and when to use it.")


def _write_skill(root: Path, name: str, frontmatter: str, body: str = "body text\n") -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(frontmatter + body, encoding="utf-8")


def _run(skills_dir: Path):
    """Run main() against skills_dir, returning (exit_code, captured_stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = vs.main(skills_dir)
    return code, buf.getvalue()


class TestParseFrontmatter(unittest.TestCase):
    """Scenario S-002 at the lowest faithful layer: the frontmatter parser's bug population."""

    def test_no_leading_delimiter(self):
        # Scenario S-002: a body whose first line is not `---` has no frontmatter.
        data, body_lines = vs.parse_frontmatter("no frontmatter here\njust text\n")
        self.assertIsNone(data)
        self.assertEqual(body_lines, 0)

    def test_unterminated_frontmatter(self):
        # Scenario S-002: an opened but never-closed `---` block is not valid frontmatter.
        data, _ = vs.parse_frontmatter("---\nname: x\ndescription: y\n(no closing delimiter)\n")
        self.assertIsNone(data)

    def test_quotes_are_stripped(self):
        data, _ = vs.parse_frontmatter('---\nname: "spec-quality"\ndescription: \'a description\'\n---\nb\n')
        self.assertEqual(data["name"], "spec-quality")
        self.assertEqual(data["description"], "a description")

    def test_folded_continuation_is_joined(self):
        data, _ = vs.parse_frontmatter("---\nname: x\ndescription: line one\n  line two\n---\nb\n")
        self.assertEqual(data["description"], "line one line two")


class TestValidatorRun(unittest.TestCase):
    """Scenarios S-001, S-003..S-007 at the component layer: main() over fixture directories."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_directory_without_skill_md_errors(self):
        # Scenario S-001: a skill directory with no SKILL.md is an error, non-zero exit.
        (self.root / "lonely").mkdir()
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("no SKILL.md", out)

    def test_no_frontmatter_errors(self):
        # Scenario S-002: a SKILL.md without frontmatter is an error, non-zero exit.
        _write_skill(self.root, "bad", frontmatter="not frontmatter at all\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("no YAML frontmatter", out)

    def test_name_not_matching_directory_errors(self):
        # Scenario S-003: frontmatter name differing from the directory is an error.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="beta", desc=LONG_DESC))
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("!=", out)

    def test_missing_description_errors(self):
        # Scenario S-004: a missing description key is an error.
        _write_skill(self.root, "gamma", frontmatter="---\nname: gamma\n---\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("missing `description`", out)

    def test_thin_description_warns_but_exits_zero(self):
        # Scenario S-005: a too-short description warns and does not fail.
        _write_skill(self.root, "delta", GOOD_FM.format(name="delta", desc="too short"))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)
        self.assertIn("thin", out)

    def test_oversized_body_warns_but_exits_zero(self):
        # Scenario S-006: a body over the line guideline warns and does not fail.
        big_body = "\n".join(f"line {i}" for i in range(600)) + "\n"
        _write_skill(self.root, "epsilon", GOOD_FM.format(name="epsilon", desc=LONG_DESC), body=big_body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)

    def test_all_valid_exits_zero_with_summary(self):
        # Scenario S-007: an all-valid skills directory exits zero and prints the summary.
        _write_skill(self.root, "zeta", GOOD_FM.format(name="zeta", desc=LONG_DESC))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)


class TestLinkChecks(unittest.TestCase):
    """New checks: unresolved relative links and dangling sibling-skill references."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_unresolved_relative_link_errors(self):
        # A relative link whose target does not exist on disk is an error.
        body = "See [the missing file](nonexistent-file.md) for details.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("link target does not exist: nonexistent-file.md", out)

    def test_dangling_sibling_skill_reference_errors(self):
        # A ../<name>/SKILL.md link to a skill that does not exist in this kit is an error.
        body = "Use [`document`](../document/SKILL.md) instead.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("references sibling skill 'document'", out)
        self.assertIn("no such skill exists in this kit", out)

    def test_valid_sibling_skill_reference_does_not_error(self):
        # A ../<name>/SKILL.md link to a skill that does exist is not flagged.
        body = "Use [`beta`](../beta/SKILL.md) instead.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        _write_skill(self.root, "beta", GOOD_FM.format(name="beta", desc=LONG_DESC))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 2 skill(s): 0 error(s), 0 warning(s).", out)

    def test_link_escaping_the_shipped_tree_errors(self):
        # A link above the .agents/ tree resolves in the repo but dangles once installed.
        # The bug population is exactly this: the target exists on disk, so an
        # existence-only check passes it.
        agents = self.root / "agents"
        skills = agents / "skills"
        (self.root / "AGENTS.md").write_text("real file\n", encoding="utf-8")
        body = "Read [`AGENTS.md`](../../../AGENTS.md) before dispatching.\n"
        _write_skill(skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(skills)
        self.assertEqual(code, 1)
        self.assertIn("link escapes the shipped skill tree: ../../../AGENTS.md", out)

    def test_rules_module_link_does_not_error(self):
        # ../../rules/<file>.md is the one legitimate escape: install.py ships the
        # rules module as the sibling of the skills directory.
        agents = self.root / "agents"
        skills = agents / "skills"
        (agents / "rules").mkdir(parents=True)
        (agents / "rules" / "house-style.md").write_text("# style\n", encoding="utf-8")
        body = "Follow [`house-style.md`](../../rules/house-style.md).\n"
        _write_skill(skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(skills)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_external_and_anchor_links_are_skipped(self):
        # http, https, mailto links and same-page anchors are not resolved on disk.
        body = (
            "See [docs](https://example.com/guide), [help](http://example.com), "
            "[contact](mailto:someone@example.com), and [a section](#some-section).\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)


class TestStatusContradictionCheck(unittest.TestCase):
    """New check: a skill asserting both draft and shipped status warns but does not fail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_draft_and_shipped_contradiction_warns_but_exits_zero(self):
        body = (
            "The skill overall is a draft pending field iteration, but these are settled.\n\n"
            "- Shipped 2026-07-24, blessed after dogfooding on this kit's own change.\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)
        self.assertIn("asserts both draft and shipped status", out)

    def test_draft_alone_does_not_warn(self):
        # Only a draft assertion, no shipped bullet: not a contradiction.
        body = "The skill overall is a draft pending field iteration.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertNotIn("asserts both draft and shipped status", out)

    def test_shipped_alone_does_not_warn(self):
        # Only a shipped bullet, no draft assertion: not a contradiction.
        body = "- Shipped 2026-07-24, blessed after dogfooding on this kit's own change.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertNotIn("asserts both draft and shipped status", out)


if __name__ == "__main__":
    unittest.main()
