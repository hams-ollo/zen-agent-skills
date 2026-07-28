"""Acceptance tests for scripts/validate-skills.py.

Derived from the behavioral contract in docs/spec/validate-skills.md via the test-author
skill (in-kit dogfood, 2026-07-24; extended 2026-07-27 to the amended contract's S-009
through S-016). Each test is tagged with the scenario id it covers. Standard library only,
per the conventions section of AGENTS.md.

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


class TestDescriptionCeiling(unittest.TestCase):
    """Scenarios S-017 and S-018: the 1024-character harness limit, measured correctly.

    The bug population is a description that reads fine and is silently rejected by the
    harness, so the oracle is the exit code plus the measured length in the message, not
    just the presence of a finding. S-018 is tested separately because a ceiling built on
    the wrong measurement would fail descriptions the harness accepts: the pre-fix parser
    counted the `>-` indicator, so a block scalar measured three characters long.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_description_over_the_limit_errors(self):
        # Scenario S-017: over 1024 characters is an error and a non-zero exit.
        long_desc = "word " * 250  # 1250 chars
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=long_desc.strip()))
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ERROR", out)
        self.assertIn("over the 1024-char limit", out)
        self.assertIn("1249 chars", out)

    def test_description_at_the_limit_does_not_error(self):
        # Scenario S-017 (boundary): exactly at the limit is allowed, so the check is
        # `>` and not `>=`. An off-by-one here would reject a legal description.
        exact = "x" * vs.MAX_DESC_CHARS
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=exact))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_block_scalar_description_is_measured_without_its_indicator(self):
        # Scenario S-018: the measured value excludes the `>-` indicator. Written as a
        # block scalar whose text is exactly at the limit: it must pass. Before the fix
        # the parser yielded ">- " + text, measured 3 over, and this errored.
        text = "y" * vs.MAX_DESC_CHARS
        frontmatter = f"---\nname: alpha\ndescription: >-\n  {text}\n---\n"
        _write_skill(self.root, "alpha", frontmatter)
        code, out = _run(self.root)
        self.assertEqual(code, 0, "a block scalar at the limit must not be measured 3 over")
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_block_scalar_indicators_are_stripped_but_plain_scalars_are_not(self):
        # Scenario S-018 at the parser layer, across every indicator form. The negative
        # case is the one that matters: stripping too eagerly would silently shorten a
        # description rather than fail, which is the failure mode with no symptom.
        for indicator in ("|", "|-", "|+", ">", ">-", ">+"):
            with self.subTest(indicator=indicator):
                fm, _ = vs.parse_frontmatter(
                    f"---\nname: x\ndescription: {indicator}\n  real text here\n---\nbody\n"
                )
                self.assertEqual(fm["description"], "real text here")
        plain, _ = vs.parse_frontmatter("---\nname: x\ndescription: real text here\n---\nbody\n")
        self.assertEqual(plain["description"], "real text here")

    def test_prose_beginning_with_an_angle_bracket_is_preserved(self):
        # Scenario S-018 (negative): the strip is anchored to the field line's head and
        # bounded to one substitution, so content is never eaten.
        fm, _ = vs.parse_frontmatter(
            "---\nname: x\ndescription: >-\n  >> quoted prose > with angle brackets\n---\nb\n"
        )
        self.assertEqual(fm["description"], ">> quoted prose > with angle brackets")


class TestFrontmatterParseability(unittest.TestCase):
    """Scenario S-019: frontmatter no real YAML parser can read fails.

    The bug population is a plain unquoted value containing ": ", which YAML reads as a
    nested mapping. Eight skills shipped that way and every gate passed, because this
    script's own parser is a regex. The negative cases carry the weight: the same text
    quoted or in a block scalar is valid, and flagging those would push authors toward
    contorting descriptions to satisfy a checker rather than a parser.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_plain_scalar_with_a_colon_errors(self):
        # Scenario S-019: the exact construct that shipped in eight skills.
        desc = ("Scaffold a work-tracking system into the current repository: AGENTS.md, a "
                ".tasks/ directory, and a validate.py checker. Use it when setting one up.")
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=desc))
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("nested mapping", out)
        self.assertIn("`description`", out)

    def test_plain_scalar_ending_in_a_colon_errors(self):
        # Scenario S-019: the other half of the same construct, a value YAML reads as a
        # key awaiting its own value.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC + " Trigger on:"))
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("nested mapping", out)

    def test_a_block_scalar_containing_a_colon_is_fine(self):
        # Scenario S-019 (negative): this is the fix bug-0007 applied to all eight, so a
        # false positive here would reject the corrected tree.
        frontmatter = ("---\nname: alpha\ndescription: >-\n"
                       "  Scaffold a system into this repository: AGENTS.md and a .tasks/ directory,\n"
                       "  which is what you want when setting one up for the first time.\n---\n")
        _write_skill(self.root, "alpha", frontmatter)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_quoted_scalar_containing_a_colon_is_fine(self):
        # Scenario S-019 (negative): quoting is the other valid form.
        _write_skill(self.root, "alpha",
                     f'---\nname: alpha\ndescription: "{LONG_DESC} Namely: this one."\n---\n')
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_url_in_a_plain_scalar_is_not_flagged(self):
        # Scenario S-019 (negative): "https://x" has a colon with no following space, so
        # it is valid plain YAML. Flagging it would be the obvious over-broad mistake.
        _write_skill(self.root, "alpha",
                     GOOD_FM.format(name="alpha", desc=LONG_DESC + " See https://example.com/guide"))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_every_shipped_skill_has_parseable_frontmatter(self):
        # Scenario S-019 against the real tree, which is the assertion that would have
        # caught bug-0007. The unit cases above prove the check works; this proves the
        # kit satisfies it.
        errors = []
        for d in sorted(p for p in (REPO_ROOT / ".agents" / "skills").iterdir() if p.is_dir()):
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            vs.check_frontmatter_is_parseable(text, d.name, errors)
        self.assertEqual(errors, [])


class TestLinkChecks(unittest.TestCase):
    """Scenarios S-009 through S-013: link resolution, portability, and what is skipped."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_unresolved_relative_link_errors(self):
        # Scenario S-009: a relative link whose target does not exist on disk is an error.
        body = "See [the missing file](nonexistent-file.md) for details.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("link target does not exist: nonexistent-file.md", out)

    def test_dangling_sibling_skill_reference_errors(self):
        # Scenario S-010: a ../<name>/SKILL.md link to a skill that does not exist is an error.
        body = "Use [`document`](../document/SKILL.md) instead.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("references sibling skill 'document'", out)
        self.assertIn("no such skill exists in this kit", out)

    def test_valid_sibling_skill_reference_does_not_error(self):
        # Scenario S-010 (negative): a link to a skill that does exist is not flagged.
        body = "Use [`beta`](../beta/SKILL.md) instead.\n"
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        _write_skill(self.root, "beta", GOOD_FM.format(name="beta", desc=LONG_DESC))
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 2 skill(s): 0 error(s), 0 warning(s).", out)

    def test_link_escaping_the_shipped_tree_errors(self):
        # Scenario S-011: a link above the .agents/ tree resolves in the repo but dangles once installed.
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
        # Scenario S-012: ../../rules/<file>.md is legal, because install.py ships the
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
        # Scenario S-013: http, https, mailto and same-page anchors are not resolved on disk.
        body = (
            "See [docs](https://example.com/guide), [help](http://example.com), "
            "[contact](mailto:someone@example.com), and [a section](#some-section).\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)


class TestStatusContradictionCheck(unittest.TestCase):
    """Scenario S-014: a skill asserting both draft and shipped warns but does not fail.

    The oracle is table-driven over the bug population rather than the one phrasing
    that happened to be implemented. The 2026-07-27 conformance audit found this check
    matched "is a draft" plus a "- Shipped" list item and missed four other plausible
    phrasings, so a test that only exercised the canonical case proved nothing about
    the contract it claimed to protect.
    """

    CONTRADICTIONS = {
        "canonical": "This skill is a draft.\n\n- Shipped 2026-07-24, blessed.\n",
        "remains a draft": "This skill remains a draft.\n\n- Shipped 2026-07-24, blessed.\n",
        "prose status line": "Status: draft pending iteration.\n\n- Shipped 2026-07-24.\n",
        "shipped not a list item": "This skill is a draft.\n\nShipped 2026-07-24, blessed.\n",
        "blessed rather than shipped": "This skill is a draft.\n\n- Blessed 2026-07-24 after dogfooding.\n",
    }

    # Each of these carries at most one half of the contradiction, so none is a finding.
    # The conjunction is what makes the check specific, which is why each half can afford
    # to match generously.
    NON_CONTRADICTIONS = {
        "draft alone": "This skill is a draft pending field iteration.\n",
        "shipped alone": "- Shipped 2026-07-24, blessed after dogfooding.\n",
        "prose discussing drafts": (
            "A document using 'draft' still needs a contradicting fact.\n\n"
            "- Shipped 2026-07-24.\n"
        ),
        "draft refers to something else": (
            "This skill only ever writes `status: draft` for the spec it authors.\n"
        ),
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_body(self, body):
        for child in self.root.iterdir():
            if child.is_dir():
                for f in child.iterdir():
                    f.unlink()
                child.rmdir()
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        return _run(self.root)

    def test_every_contradiction_phrasing_warns_and_exits_zero(self):
        # Scenario S-014: the warning fires, and it stays a warning.
        for label, body in self.CONTRADICTIONS.items():
            with self.subTest(phrasing=label):
                code, out = self._run_body(body)
                self.assertEqual(code, 0, f"{label} must warn, not fail")
                self.assertIn("asserts both draft and shipped status", out, label)

    def test_a_single_assertion_is_not_a_contradiction(self):
        # Scenario S-014: "Either assertion alone is not a contradiction."
        for label, body in self.NON_CONTRADICTIONS.items():
            with self.subTest(phrasing=label):
                _, out = self._run_body(body)
                self.assertNotIn("asserts both draft and shipped status", out, label)


class TestSkillsDirectoryPreconditions(unittest.TestCase):
    """Scenarios S-015 and S-016: an unreadable directory is not a zero-skill success.

    The defect these protect against is the quiet one: reporting success because
    nothing was checked. S-015 must fail, S-016 must not, and the pair is only
    meaningful together.
    """

    def test_absent_directory_fails(self):
        # Scenario S-015: a missing directory errors rather than reporting zero skills.
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run(Path(tmp) / "does-not-exist")
        self.assertEqual(code, 1)
        self.assertIn("no skills directory", out)
        self.assertNotIn("Checked 0 skill", out)

    def test_empty_directory_succeeds(self):
        # Scenario S-016: an empty directory is a legitimate zero-skill result.
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run(Path(tmp))
        self.assertEqual(code, 0)
        self.assertIn("No skills found", out)


if __name__ == "__main__":
    unittest.main()
