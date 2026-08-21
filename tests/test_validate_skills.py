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

# The upper end of the lens-declaration window, asserted rather than assumed. The real
# lenses are 30 to 300 lines long, so a window at or above this stops distinguishing an
# opening from a body and the "declares itself" test becomes "mentions a lens anywhere".
MAX_LENS_WINDOW = 25

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


class TestSchemaConformance(unittest.TestCase):
    """Scenarios S-020 and S-021: the two schema rules the kit was passing by accident.

    Both are hard failures at the consumer, and neither was checked here. `human-handoff`
    was violating S-020 in the field. S-021 is an allow-list, so its negative cases matter
    as much as its positive one: rejecting a legal property would fail a valid skill and
    look like a kit bug.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_angle_bracket_in_description_errors(self):
        # Scenario S-020: the exact construct human-handoff shipped, a <placeholder> in a
        # trigger phrase.
        desc = LONG_DESC + ' Trigger on "draft a message to <name> about where we are".'
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=desc))
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("angle bracket", out)

    def test_a_block_scalar_description_is_not_flagged_for_its_own_indicator(self):
        # Scenario S-020 (negative): the field line reads `description: >-`. Checking raw
        # text instead of the parsed value would flag the twelve skills that use one.
        frontmatter = (f"---\nname: alpha\ndescription: >-\n  {LONG_DESC}\n---\n")
        _write_skill(self.root, "alpha", frontmatter)
        code, out = _run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_an_unrecognised_frontmatter_key_errors(self):
        # Scenario S-021: `version` is the likeliest wrong guess, because Anthropic's own
        # example skill documents it as optional while their validator rejects it.
        fm = f"---\nname: alpha\ndescription: {LONG_DESC}\nversion: 1.0.0\n---\n"
        _write_skill(self.root, "alpha", fm)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("'version'", out)
        self.assertIn("not in the skill schema", out)

    def test_every_allowed_key_is_accepted(self):
        # Scenario S-021 (negative): all six permitted properties together must pass, or
        # the allow-list would reject a valid skill. `license` in particular is what
        # chore-0022 goes on to add.
        fm = ("---\nname: alpha\n"
              f"description: {LONG_DESC}\n"
              "license: MIT\n"
              "allowed-tools: Read, Grep\n"
              "metadata: some-value\n"
              "compatibility: claude-code\n---\n")
        _write_skill(self.root, "alpha", fm)
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_the_shipped_kit_satisfies_both_schema_rules(self):
        # S-020 and S-021 against the real tree, which is the assertion that would have
        # caught human-handoff.
        skills = sorted(p for p in (REPO_ROOT / ".agents" / "skills").iterdir() if p.is_dir())
        offenders = {"angle_brackets": [], "unknown_keys": []}
        for d in skills:
            fm, _ = vs.parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
            if "<" in fm.get("description", "") or ">" in fm.get("description", ""):
                offenders["angle_brackets"].append(d.name)
            extra = sorted(set(fm) - vs.ALLOWED_FRONTMATTER_KEYS)
            if extra:
                offenders["unknown_keys"].append((d.name, extra))
        self.assertEqual(offenders, {"angle_brackets": [], "unknown_keys": []})


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


class TestLinkChecksInsideCodeSpansAndFences(unittest.TestCase):
    """Scenario S-009 refined: a link that renders as literal text is not a link.

    The bug population is a skill body that *shows* an example markdown link, which the
    documentation skills are the likeliest to want. `check_links()` matched every link
    with a bare regex and resolved each one on disk, so the example failed the lint and
    the error message never named a fence as the cause (bug-0027).

    The negative cases carry the weight here, because the cheap way to remove a false
    positive is to switch the check off: a genuine broken link outside any span, and one
    below an unterminated fence, must both still be reported.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_link_inside_a_fenced_block_is_not_reported(self):
        # Scenario S-009: the exact reproduction recorded in bug-0027, a `markdown`
        # fenced block holding one ordinary link to a target that does not exist.
        body = (
            "Write the reference like this:\n\n"
            "```markdown\n"
            "See [the notes](references/does-not-exist.md) for details.\n"
            "```\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 0, f"a fenced link is not a link\n{out}")
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_link_inside_an_inline_code_span_is_not_reported(self):
        # Scenario S-009: markdown opens a span with a backtick run of any length and
        # closes it with a run of the same length, so knowing only the single form fixes
        # half the occurrences. The double form is what an author reaches for the moment
        # the text being quoted contains a backtick of its own.
        forms = {
            "single backtick": "Write `[the notes](references/does-not-exist.md)` in the body.\n",
            "double backtick": "Write ``[`notes`](references/does-not-exist.md)`` in the body.\n",
        }
        for label, body in forms.items():
            with self.subTest(form=label):
                _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC),
                             body=body)
                code, out = _run(self.root)
                self.assertEqual(code, 0, f"{label}: a quoted link is not a link\n{out}")
                self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_real_broken_link_beside_a_fence_is_still_reported(self):
        # Scenario S-009 (negative): the exclusion must not switch the check off. The
        # fence here is closed and the genuine link sits after it, so a scanner that ran
        # the fence past its closing delimiter would pass this file for the wrong reason.
        body = (
            "```markdown\n"
            "See [an example](references/does-not-exist.md).\n"
            "```\n\n"
            "See [the real target](really-missing.md) for details.\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("link target does not exist: really-missing.md", out)
        self.assertNotIn("does-not-exist.md", out)

    def test_an_unterminated_fence_does_not_swallow_the_body_below_it(self):
        # Scenario S-009 (negative): an opening fence that is never closed yields no
        # range at all. A detector that ran it to end of file would disable the link
        # check for everything below and still exit clean, which is the one failure
        # indistinguishable from success (the trade bug-0015 and bug-0017 chose).
        body = (
            "```markdown\n"
            "a fence that is never closed\n\n"
            "See [the real target](really-missing.md) for details.\n"
        )
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.root)
        self.assertEqual(code, 1, f"an unterminated fence must not suppress what follows it\n{out}")
        self.assertIn("link target does not exist: really-missing.md", out)

    def test_a_link_escaping_the_shipped_tree_is_not_reported_inside_a_fence(self):
        # Scenario S-011 against the same exclusion, and a recorded decision rather than
        # an accident: a fenced link is skipped by every branch of check_links(), the
        # escape branch included. The portability rule protects a reader who clicks a
        # link that dangles once the skill is installed, and a link rendered as literal
        # text is clicked by nobody. Splitting the rule so existence is skipped inside a
        # fence while the escape check still fires would leave an author unable to show
        # the very example the escape rule exists to teach. Outside a fence the rule is
        # unchanged: test_link_escaping_the_shipped_tree_errors above still holds.
        agents = self.root / "agents"
        skills = agents / "skills"
        (self.root / "AGENTS.md").write_text("real file\n", encoding="utf-8")
        body = (
            "Never write a link like this one:\n\n"
            "```markdown\n"
            "Read [`AGENTS.md`](../../../AGENTS.md) before dispatching.\n"
            "```\n"
        )
        _write_skill(skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(skills)
        self.assertEqual(code, 0, out)
        self.assertNotIn("escapes the shipped skill tree", out)

    def test_every_shipped_skill_still_passes_the_link_check(self):
        # Scenario S-009 against the real tree: the assertion that the exclusion did not
        # change what the kit's own skills report. Every real skill still lints clean.
        skills_dir = REPO_ROOT / ".agents" / "skills"
        skills = sorted(p for p in skills_dir.iterdir() if p.is_dir())
        names = {d.name for d in skills}
        errors = []
        for d in skills:
            skill_md = d / "SKILL.md"
            vs.check_links(skill_md, skill_md.read_text(encoding="utf-8"), names, d.name,
                           errors, skills_dir.parent.resolve())
        self.assertEqual(errors, [])


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


class TestLensComposition(unittest.TestCase):
    """A self-declared lens under `.agents/rules/` that no skill references fails (feat-0048).

    The bug population is a lens that reads perfectly and reaches nobody. `autonomy.md`
    shipped calling itself "the third beside house-style.md and review-quality.md" while
    no skill composed it, and every gate passed, because nothing here read the rules
    directory at all. A lens is composed rather than run, so an uncomposed one is inert
    and the swappability promise fails with it: an adopter rewrites the ceiling and
    nothing changes.

    The negative cases carry the weight, as they do for the link checks above. This rule
    reads files nobody asked it to lint, so a false positive lands on a document whose
    author never opted into being a lens, and the cheap response to that is to delete the
    rule. A plain rules document with no inbound reference must pass.
    """

    LENS_OPENING = (
        "# Zen example lens (edit freely)\n\n"
        "This file is a **swappable module**, the fourth beside the other three.\n\n"
        "It governs something.\n"
    )
    PLAIN_RULES_DOC = (
        "# What lives in this directory\n\n"
        "One file per swappable module the skills compose. Replace any of them.\n"
    )

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "agents" / "skills"
        self.rules = self.root / "agents" / "rules"
        self.rules.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_rules(self, name: str, text: str) -> None:
        (self.rules / name).write_text(text, encoding="utf-8")

    def test_a_self_declared_lens_with_no_inbound_reference_errors(self):
        # The feat-0048 condition itself: the lens declares, no skill points back.
        self._write_rules("example.md", self.LENS_OPENING)
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        code, out = _run(self.skills)
        self.assertEqual(code, 1)
        self.assertIn("declares itself a lens but no skill references it", out)
        self.assertIn("agents/rules/example.md", out)

    def test_a_referenced_lens_does_not_error(self):
        # The wiring this task performs, in miniature: one skill points at the lens the
        # way the five real ones now do, and the rule is satisfied.
        self._write_rules("example.md", self.LENS_OPENING)
        body = "Follow [`example.md`](../../rules/example.md) when nobody is watching.\n"
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_non_lens_rules_file_without_references_passes(self):
        # The other direction, and the one that keeps the rule from being deleted: a
        # rules-directory document that never presents itself as a lens is not required
        # to be composed, even though it mentions swappable modules in its body.
        self._write_rules("README.md", self.PLAIN_RULES_DOC)
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)
        self.assertNotIn("declares itself a lens", out)

    def test_the_bare_subject_word_is_not_a_reference(self):
        # A skill that merely discusses the topic gives a reader no way to reach the
        # module, so the reference has to name the file. Without this the rule would be
        # satisfied by prose and stop protecting anything.
        self._write_rules("autonomy.md", self.LENS_OPENING)
        body = "Respect the autonomy ceiling when running unattended.\n"
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 1, out)
        self.assertIn("declares itself a lens but no skill references it", out)

    def test_a_prose_mention_naming_the_file_counts_as_a_reference(self):
        # The portability contract in AGENTS.md tells a skill to name some files in prose
        # rather than link to them, so requiring a markdown link specifically would push
        # authors to break one rule to satisfy another.
        #
        # The mention here sits inside an inline code span, because backticks are how the
        # house style writes a filename in prose. bug-0040 excluded fenced blocks from this
        # rule and deliberately left spans counting, so this fixture is also the pin on
        # that decision: the span exclusion S-022 applies to links would fail the exact
        # form S-023 protects.
        self._write_rules("example.md", self.LENS_OPENING)
        body = "The ceiling is stated in `example.md` beside this skill.\n"
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)

    def test_a_mention_only_inside_a_fenced_block_is_not_a_reference(self):
        # Scenario S-023 (bug-0040): a fenced block is the body *showing* what a reference
        # looks like, most often sample text a skill tells some other agent to write, so it
        # points no reader at the module and composes nothing. The filename appears nowhere
        # else in this fixture on purpose: a body that also named it in prose would pass
        # either way and prove nothing.
        self._write_rules("example.md", self.LENS_OPENING)
        body = (
            "Give the delegate a line shaped like this one:\n\n"
            "```markdown\n"
            "Follow [`example.md`](../../rules/example.md) when nobody is watching.\n"
            "```\n"
        )
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 1, out)
        self.assertIn("declares itself a lens but no skill references it", out)

    def test_a_real_reference_beside_a_fenced_example_still_counts(self):
        # Scenario S-023 (negative): the exclusion must not switch the rule off. The fence
        # here is closed and the genuine reference sits after it, so a scanner that ran the
        # fence past its closing delimiter would fail this skill for the wrong reason.
        self._write_rules("example.md", self.LENS_OPENING)
        body = (
            "Give the delegate a line shaped like this one:\n\n"
            "```markdown\n"
            "Follow [`example.md`](../../rules/example.md) when nobody is watching.\n"
            "```\n\n"
            "This skill itself follows [`example.md`](../../rules/example.md).\n"
        )
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_an_unterminated_fence_does_not_hide_the_reference_below_it(self):
        # Scenario S-023 (negative): an opening fence that is never closed yields no range
        # at all, so the real reference below it still counts. The opposite trade would let
        # one stray fence suppress every mention under it and report the lens as unwired.
        self._write_rules("example.md", self.LENS_OPENING)
        body = (
            "```markdown\n"
            "a fence that is never closed\n\n"
            "This skill follows [`example.md`](../../rules/example.md).\n"
        )
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC), body=body)
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)

    def test_a_declaration_below_the_opening_window_is_not_a_declaration(self):
        # Why the window is bounded at all: LENS_DECLARATION_RE matches the bare word
        # "lens", which any rules document may use when describing its neighbours. Only
        # the opening is a declaration about *this* file, so a mention further down must
        # not conscript a document into being a lens.
        deep = self.PLAIN_RULES_DOC + "\n" * 40 + "This file is a **swappable module**.\n"
        self._write_rules("README.md", deep)
        _write_skill(self.skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        code, out = _run(self.skills)
        self.assertEqual(code, 0, out)

    def test_the_opening_window_clears_every_shipped_lens_with_margin(self):
        # Why the bound is 10 lines and not smaller: it must hold every real lens, with
        # room for a longer title block, and it must stay well short of a whole body.
        # Bounded in both directions rather than asserted as a bare number, matching how
        # bug-0026 asks a drift assertion to be bounded: if a future lens declares itself
        # later than this, the constant is what moves, and this test says so.
        rules_dir = REPO_ROOT / ".agents" / "rules"
        for path in sorted(rules_dir.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            declaring = [i + 1 for i, line in enumerate(lines)
                         if vs.LENS_DECLARATION_RE.search(line)]
            with self.subTest(lens=path.name):
                self.assertTrue(declaring, f"{path.name} no longer declares itself a lens")
                self.assertLessEqual(
                    declaring[0], vs.LENS_DECLARATION_LINES,
                    f"{path.name} declares itself on line {declaring[0]}, past the "
                    f"{vs.LENS_DECLARATION_LINES}-line opening window",
                )
        self.assertLess(vs.LENS_DECLARATION_LINES, MAX_LENS_WINDOW,
                        "a window this wide stops being an opening and reads the body")

    def test_every_shipped_lens_is_composed_by_at_least_one_skill(self):
        # The rule against the real tree: the assertion that would have caught
        # autonomy.md, and that catches the next lens added without wiring.
        skills_dir = REPO_ROOT / ".agents" / "skills"
        skill_texts = {d.name: (d / "SKILL.md").read_text(encoding="utf-8")
                       for d in sorted(skills_dir.iterdir()) if d.is_dir()}
        errors = []
        vs.check_lenses_are_composed(skills_dir.parent / "rules", skill_texts, errors)
        self.assertEqual(errors, [])

    def test_autonomy_is_composed_by_exactly_the_five_skills_it_cites(self):
        # feat-0048's own acceptance criterion, kept as a test because the wiring list is
        # the lens's outbound links: a skill gets a reference if and only if the lens
        # claims one of its rules. A sixth reference would make the lens look composed
        # somewhere it is not load-bearing, and a fifth missing one leaves a cited skill
        # unable to reach the module.
        skills_dir = REPO_ROOT / ".agents" / "skills"
        referencing = sorted(d.name for d in skills_dir.iterdir()
                             if d.is_dir()
                             and "autonomy.md" in (d / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(
            referencing,
            ["doc-sync", "fix-batch", "pr-describe", "spec-conformance", "verifier-agent"],
        )


class TestSupportingFileLinkChecks(unittest.TestCase):
    """Characterization tests for chore-0036: the files a skill ships beside its SKILL.md.

    **Characterization, not acceptance.** `chore-0036` declares `scenarios: []`, so no
    scenario in docs/spec/validate-skills.md states this rule and these tests carry no
    S-NNN tag. They pin observable behavior that the contract does not yet describe, and
    the divergence is recorded in docs/spec/validate-skills.conformance.md rather than
    papered over with an id these tests would not actually be derived from.

    The bug population is a coverage hole rather than a live defect: `check_links()` ran
    only on `SKILL.md`, the CI `--links` globs never reach `.agents/`, and the templates
    carry a `.tmpl` suffix no `.md` glob would match. So the one tree that installs into
    an adopter's repository was the only tree nothing link-checked.

    The exclusion carries as much weight here as the check. A template's links are
    authored for the repository it is written into, so resolving them where the template
    currently sits would report every one of them as broken and the rule would be
    switched off rather than satisfied. `test_a_template_suffix_file_is_not_checked` is
    the pin on that bound, and the counting test is what keeps the exclusion from
    quietly becoming the whole rule.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_supporting(self, skill: str, relpath: str, text: str) -> Path:
        path = self.root / skill / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def test_unresolved_link_in_a_supporting_file_errors_and_names_the_file(self):
        # The headline gap. This fails against the pre-chore-0036 script, which read no
        # file but SKILL.md, and the message must name the supporting file rather than
        # the skill: an error pointing at SKILL.md for a link that is not in it sends the
        # reader to the wrong file.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "references/notes.md",
                               "See [the missing file](nonexistent-file.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("alpha/references/notes.md: link target does not exist: "
                      "nonexistent-file.md", out)

    def test_a_supporting_file_whose_links_resolve_passes(self):
        # The negative that keeps the rule usable. Both forms a real supporting file
        # uses: a link within its own directory, and one reaching back up into the skill.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "references/glossary.md", "# terms\n")
        self._write_supporting(
            "alpha", "references/notes.md",
            "See [the glossary](glossary.md) and [the body](../SKILL.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("Checked 1 skill(s): 0 error(s), 0 warning(s).", out)

    def test_a_link_escaping_the_shipped_tree_from_a_supporting_file_errors(self):
        # The portability rule S-011 carries over unchanged. The target exists on disk,
        # which is the whole bug population: an existence-only check passes it, and the
        # link dangles the moment the skill is installed without this repository around
        # it. A supporting file is one directory deeper than a SKILL.md, so the escaping
        # path has one more `..` than S-011's fixture does.
        agents = self.root / "agents"
        skills = agents / "skills"
        (self.root / "AGENTS.md").write_text("real file\n", encoding="utf-8", newline="\n")
        _write_skill(skills, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        path = skills / "alpha" / "references" / "notes.md"
        path.parent.mkdir(parents=True)
        path.write_text("Read [`AGENTS.md`](../../../../AGENTS.md) first.\n",
                        encoding="utf-8", newline="\n")
        code, out = _run(skills)
        self.assertEqual(code, 1)
        self.assertIn("alpha/references/notes.md: link escapes the shipped skill tree: "
                      "../../../../AGENTS.md", out)

    def test_a_template_suffix_file_is_not_checked(self):
        # The stated exclusion, pinned. `AGENTS.md.tmpl` is written into an adopter's
        # repository root, where `.tasks/` and `ROADMAP.md` resolve; here they resolve
        # nowhere, and reporting them would make the rule unusable. Both a plain relative
        # target and one that escapes the shipped tree are covered, because the exclusion
        # is at the file level and not per-rule.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting(
            "alpha", "templates/AGENTS.md.tmpl",
            "Work lives in [`.tasks/`](.tasks/) and history in "
            "[the log](../../../../CHANGELOG.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("AGENTS.md.tmpl", out)

    def test_the_exclusion_is_by_suffix_and_not_by_directory_name(self):
        # The decision recorded in chore-0036, stated as a test so it cannot drift into
        # folklore. `project-bootstrap/templates/house-code-style.md` is a real file that
        # documents the directory it sits in, is read in place, and is linked from its
        # SKILL.md; a rule that excluded `templates/` wholesale would stop checking it
        # for a reason that has nothing to do with where its links resolve.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "templates/readme.md",
                               "See [the missing file](nonexistent-file.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("alpha/templates/readme.md: link target does not exist", out)

    def test_a_non_markdown_supporting_file_is_not_read(self):
        # Markdown link syntax inside a Python or TOML file is not a link, and reading
        # one would report a defect against a file whose format has no such construct.
        # `init-worktracking` ships a `validate.py`, so this is the shipped case.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "templates/validate.py",
                               '"""See [the notes](nonexistent-file.md)."""\n')
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("nonexistent-file.md", out)

    def test_a_sibling_skill_shortcut_is_not_applied_to_a_supporting_file(self):
        # The false negative the `sibling_shortcut` flag removes. `../beta/SKILL.md` from
        # a SKILL.md names the sibling skill `beta` and is legal (S-010); from a
        # supporting file one level deeper it names a subdirectory of *this* skill, which
        # does not exist. Reading it as a skill name would clear a broken link precisely
        # when a skill of that name happens to exist, so the fixture ships a real `beta`.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        _write_skill(self.root, "beta", GOOD_FM.format(name="beta", desc=LONG_DESC))
        self._write_supporting("alpha", "references/notes.md",
                               "See [`beta`](../beta/SKILL.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("alpha/references/notes.md: link target does not exist: "
                      "../beta/SKILL.md", out)
        self.assertNotIn("no such skill exists in this kit", out)

    def test_a_link_inside_a_fence_in_a_supporting_file_is_not_reported(self):
        # chore-0036 depends on bug-0027 for correctness and not only for ordering: a
        # reference file full of fenced examples would light up the moment the checked
        # set widened. The guard lives in `_link_targets()`, which every caller of
        # `check_links()` goes through, so it reaches a supporting file too. The genuine
        # broken link after the closed fence is the half that must still be reported.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting(
            "alpha", "references/notes.md",
            "```markdown\nSee [an example](does-not-exist.md).\n```\n\n"
            "See [the real target](really-missing.md).\n")
        code, out = _run(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("link target does not exist: really-missing.md", out)
        self.assertNotIn("does-not-exist.md", out)

    def test_the_run_reports_how_many_supporting_files_it_checked_and_skipped(self):
        # A coverage number that cannot be compared across runs is the gap this rule
        # closes rather than a report of it. All three counts are asserted together:
        # "0 checked" reads the same whether the exclusion is correct or the walk is
        # broken, until the number of files it declined to read sits beside it.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "references/notes.md", "no links here\n")
        self._write_supporting("alpha", "templates/AGENTS.md.tmpl", "a template\n")
        self._write_supporting("alpha", "templates/ruff.toml", "line-length = 100\n")
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("Link-checked 1 supporting file(s) beside them; skipped 1 "
                      "template(s) whose links are written for another repository and "
                      "1 non-markdown file(s).", out)

    def test_a_skill_with_no_supporting_files_reports_zero(self):
        # The floor of the same line, so the count is present on every run rather than
        # only when there is something to say.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("Link-checked 0 supporting file(s) beside them; skipped 0 "
                      "template(s)", out)

    def test_classification_of_the_real_shipped_supporting_files(self):
        # The shipped inventory, counted rather than described. chore-0036 was written
        # from a survey claiming 14 files across two skills with nine in
        # `init-worktracking`; the numbers are pinned here so the next reader gets the
        # count from the tree instead of from prose. Asserted as the classification
        # rather than as bare totals, because the totals move whenever a skill is added
        # and the split between checked and excluded is the part the rule is about.
        skills_dir = REPO_ROOT / ".agents" / "skills"
        names = {d.name for d in skills_dir.iterdir() if d.is_dir()}
        counts = {"markdown": 0, "template": 0, "other": 0}
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            for kind, n in vs.check_supporting_files(
                    d, names, d.name, [], skills_dir.parent.resolve()).items():
                counts[kind] += n
        self.assertEqual(counts, {"markdown": 1, "template": 8, "other": 5})

    def test_a_byte_cache_is_not_counted_as_a_supporting_file(self):
        # The count has to be a fact about the kit and not about whether the tests have
        # run yet. `init-worktracking/templates/validate.py` grows a `__pycache__` the
        # moment the suite imports it, which made the assertion above report six
        # non-markdown files on a second run and five on a clean checkout. install.py
        # copies a skill with `ignore_patterns("__pycache__", "*.pyc")`, so a byte cache
        # is in no installed skill; `_is_shipped` mirrors that list and this pins it.
        _write_skill(self.root, "alpha", GOOD_FM.format(name="alpha", desc=LONG_DESC))
        self._write_supporting("alpha", "templates/validate.py", "# a template script\n")
        cache = self.root / "alpha" / "templates" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "validate.cpython-311.pyc").write_bytes(b"\x00compiled\x00")
        code, out = _run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("and 1 non-markdown file(s).", out)

    def test_every_shipped_supporting_file_passes_the_link_check(self):
        # The rule against the real tree. chore-0036 recorded a hand simulation on
        # 2026-08-08 finding 0 dangling links, which is what makes this a coverage gap
        # and not a live defect; this is that simulation made mechanical.
        skills_dir = REPO_ROOT / ".agents" / "skills"
        names = {d.name for d in skills_dir.iterdir() if d.is_dir()}
        errors = []
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            vs.check_supporting_files(d, names, d.name, errors,
                                      skills_dir.parent.resolve())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
