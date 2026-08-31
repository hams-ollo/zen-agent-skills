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

Every scenario S-001 through S-017 has a covering test. The runs that write do so
into a temp directory; the one test that targets the repository itself (S-011) uses
a preview run, so it asserts the no-op without depending on it.

`TestDestinationContainment` carries no scenario id, deliberately. No scenario in
the spec governs where a write may land, so it is a characterization test pinning
observed behavior rather than an acceptance test deriving from the contract, and
tagging it with an id would claim a contract line that does not exist. Amending the
spec is chore-0087.
"""
import contextlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class TestRewriteLinksInsideCodeSpansAndFences(unittest.TestCase):
    """Scenario S-018: a link that renders as literal text is not a link.

    The bug population is a skill body that *shows* a markdown link as an example, which
    the documentation skills are the likeliest to want. `rewrite_links()` matched every
    link with a bare regex and repointed each one, so the example was rewritten in each
    generated adapter and the body said one thing in the kit and a different thing
    everywhere it shipped (bug-0028).

    test-quality notes: this is pure string work over a body, so the unit layer on
    `rewrite_links` is the lowest faithful one, and the oracle is whole-string equality
    rather than a substring, because "emitted unchanged" is a claim about the whole body
    and a substring check passes while the rest of it is mangled. The negative cases
    carry the weight, because the cheap way to remove a false rewrite is to stop
    rewriting: a real link beside a closed fence, and one below an unterminated fence,
    must both still be repointed.

    S-018 is an exception to S-003 through S-008 and takes precedence over all of them:
    those scenarios sort a link by its kind, this one decides whether the text is a link
    at all. S-008 is the closest of them ("external and same-page links are emitted
    unchanged") and still governs a different question.

    The tests predate the id. bug-0028 wrote them when no scenario stated the rule and
    tagged them to the scenarios they refine; chore-0043 added S-018 to the contract on
    2026-08-19, and chore-0045 retagged them here.
    """

    # The two inlining targets differ only in the extension a sibling link is given, so
    # every case is asserted for both. The plugin target inlines nothing; see the last
    # test in this class.
    EXTS = (".mdc", ".prompt.md")

    # One fence holding all three rewritten classes at once: a sibling skill (S-003), the
    # rules module (S-006), and a skill-local supporting file (S-007). One of them
    # surviving proves nothing about the other two, since each is a separate branch.
    FENCED = (
        "Write the references like this:\n\n"
        "```markdown\n"
        "See [`doc-revise`](../doc-revise/SKILL.md) for the edit discipline.\n"
        "Apply the [`house-style`](../../rules/house-style.md) module.\n"
        "Fill in [the template](templates/task.md).\n"
        "```\n"
    )

    def test_a_link_inside_a_fenced_block_is_emitted_unchanged(self):
        # Scenario S-018 over the three rewritten classes at once: inside a fence none
        # of S-003, S-006, S-007 fires.
        for ext in self.EXTS:
            with self.subTest(ext=ext):
                self.assertEqual(ba.rewrite_links(self.FENCED, "doc-author", ext),
                                 self.FENCED)

    def test_a_link_inside_an_inline_code_span_is_emitted_unchanged(self):
        # Scenario S-018, the inline-span half. Markdown opens a span with a backtick
        # run of any length and closes it with a run of the same length, so a rule that
        # knows only the single form fixes half the occurrences. The double form is what
        # an author reaches for the moment the text being quoted contains a backtick of
        # its own.
        forms = {
            "single backtick": "Write `[the notes](../doc-revise/SKILL.md)` in the body.\n",
            "double backtick": "Write ``[`notes`](../doc-revise/SKILL.md)`` in the body.\n",
        }
        for label, body in forms.items():
            for ext in self.EXTS:
                with self.subTest(form=label, ext=ext):
                    self.assertEqual(ba.rewrite_links(body, "doc-author", ext), body)

    def test_a_real_link_beside_a_fence_is_still_rewritten(self):
        # Scenario S-018 (negative): the exclusion must not switch the rewrite off. The
        # fence here is closed and the genuine link sits after it, so a scanner that ran
        # the fence past its closing delimiter would leave the real link unrewritten and
        # dangling in every adapter. The genuine link also wraps its text in a code span,
        # which is how nearly every link in this kit is written, so an exclusion keyed to
        # the wrong bracket would suppress the whole tree rather than one example.
        body = (
            "```markdown\n"
            "See [an example](../doc-revise/SKILL.md).\n"
            "```\n\n"
            "Then read [`fix-batch`](../fix-batch/SKILL.md) for the real thing.\n"
        )
        for ext in self.EXTS:
            with self.subTest(ext=ext):
                out = ba.rewrite_links(body, "doc-author", ext)
                self.assertIn("](../doc-revise/SKILL.md)", out)
                self.assertIn(f"](fix-batch{ext})", out)
                self.assertNotIn(f"](doc-revise{ext})", out)

    def test_an_unterminated_fence_does_not_suppress_the_rewrite_below_it(self):
        # Scenario S-018 (negative): an opening fence that is never closed yields no
        # range at all, the same trade bug-0015, bug-0017, bug-0023, and bug-0027 all
        # made. A detector that ran it to end of file would disable the rewrite for the
        # rest of the body and still report success, which is the one failure
        # indistinguishable from success.
        body = (
            "```markdown\n"
            "a fence that is never closed\n\n"
            "Then read [`fix-batch`](../fix-batch/SKILL.md) for the real thing.\n"
        )
        for ext in self.EXTS:
            with self.subTest(ext=ext):
                self.assertIn(f"](fix-batch{ext})",
                              ba.rewrite_links(body, "doc-author", ext))

    def test_the_plugin_target_copies_a_body_byte_for_byte(self):
        # Scenario S-018's "in every target" clause. The third target rewrites nothing
        # at all (S-016): it copies the SKILL.md, so a fenced example survives there by
        # construction rather than by exclusion.
        # Asserted rather than assumed, because the criterion is "unchanged in every
        # target" and a rewrite added here later would break it silently.
        src = ba.discover_skills()[0]
        with tempfile.TemporaryDirectory() as tmp:
            dest = ba.emit_plugin(src, src.name, "", "", Path(tmp), False)
            self.assertEqual(dest.read_bytes(), (src / "SKILL.md").read_bytes())


class TestFrontmatterParsing(unittest.TestCase):
    """Scenario S-002 at the parser layer: what counts as the description's value.

    The negative case is the load-bearing one. Stripping too eagerly would shorten a
    description silently rather than fail, and a silently shortened description is the
    same class of defect as the indicator it removes.
    """

    def test_block_scalar_indicators_are_stripped(self):
        for indicator in ("|", "|-", "|+", ">", ">-", ">+"):
            with self.subTest(indicator=indicator):
                fm, _ = ba.split_frontmatter(
                    f"---\nname: x\ndescription: {indicator}\n  real text here\n---\nbody\n"
                )
                self.assertEqual(fm["description"], "real text here")

    def test_a_plain_scalar_is_left_alone(self):
        fm, _ = ba.split_frontmatter(
            "---\nname: x\ndescription: plain text > with a bracket\n---\nbody\n"
        )
        self.assertEqual(fm["description"], "plain text > with a bracket")


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

    def test_a_block_scalar_description_emits_its_text_not_its_yaml(self):
        # Scenario S-002 (bug-0006). Four skills write `description: >-`, and the parser
        # captured the indicator, so every adapter for them opened with
        # `description: ">- Turns ..."`: valid YAML carrying three characters of syntax
        # where the description should start. The test below it asserts only that
        # `description:` is present, which is precisely why this shipped unnoticed, so
        # this oracle is on the value.
        for rel in (Path(".cursor") / "rules" / "agent-handoff.mdc",
                    Path(".github") / "prompts" / "agent-handoff.prompt.md"):
            with self.subTest(adapter=rel.as_posix()):
                text = (self.out / rel).read_text(encoding="utf-8")
                line = next(l for l in text.splitlines() if l.startswith("description:"))
                self.assertNotIn(">-", line)
                self.assertTrue(line.startswith('description: "Turns the current session'), line)

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


class TestEmittedRulesModuleResolves(unittest.TestCase):
    """Scenarios S-009 and S-016, read from inside the rules module (bug-0044).

    test-quality notes: the defect is the mirror image of the one
    `TestEmittedTreeResolves` guards. That class walks the emitted *adapters*, this
    one walks the emitted *lenses*, because both existing filesystem walks exclude
    the rules module by construction: `_adapters()` globs `.cursor/rules/*.mdc` and
    `.github/prompts/*.prompt.md`, and the plugin walk globs `skills/*/SKILL.md`. A
    lens is neither, so seven `../skills/<name>/SKILL.md` links shipped dangling in
    every cursor and vscode tree while both walks reported clean.

    Each target is emitted into a directory of its own rather than read out of one
    combined run, because cursor and vscode share a Layout and therefore one copy of
    the module. A link form that resolves only because the other target's adapters
    happen to sit in the same tree is not a link that resolves for an adopter who
    built one target. The plugin target is walked here too, so a fix for the two
    inlining layouts cannot be paid for out of the layout that already worked.

    The named-file assertion is not decoration. The oracle is "nothing dangles",
    which an empty glob satisfies, so the walk asserts what it walked before it
    asserts what it found.
    """

    LENSES = ("autonomy.md", "house-style.md", "review-quality.md")

    def _emitted_rules_dir(self, target):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        code, _ = _run(["--out", str(out), "--target", target])
        self.assertEqual(code, 0, f"the {target} build did not exit 0")
        return out / ba.LAYOUTS[target].rules_dir

    def test_every_relative_link_in_every_emitted_rules_file_resolves(self):
        for target in ("cursor", "vscode", "plugin"):
            with self.subTest(target=target):
                rules = self._emitted_rules_dir(target)
                emitted = sorted(p.name for p in rules.glob("*.md"))
                for lens in self.LENSES:
                    self.assertIn(lens, emitted, f"{lens} was not emitted for {target}")

                broken, checked = [], 0
                for f in sorted(rules.glob("*.md")):
                    for link in LINK.findall(f.read_text(encoding="utf-8")):
                        if link.lower().startswith(SKIP_PREFIXES):
                            continue
                        checked += 1
                        if not (f.parent / link.split("#")[0]).exists():
                            broken.append(f"{f.name} -> {link}")
                self.assertGreaterEqual(
                    checked, 3, "expected the module's own cross-lens links")
                self.assertEqual(
                    broken, [],
                    f"{target}: {len(broken)} dangling link(s) in the emitted "
                    f"rules module: {broken}")


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


class TestSharedAssetAccounting(unittest.TestCase):
    """Scenario S-012's second half: a preview's counts must describe the real run.

    test-quality notes: the defect (bug-0025) is a number, not a file, so no oracle
    over the emitted tree can see it. `TestEmittedTreeResolves` passes against the
    bug and always would, because the tree a real run leaves behind is correct; it
    is the preview's report of that tree that was wrong, by a factor of the skill
    count. The oracle therefore has to be the reported count itself, and it has to
    be differential: an absolute number would be a restatement of today's kit
    inventory that a new rules file breaks, whereas dry-run-equals-real-run is the
    property S-012 actually states and holds for any inventory.

    The counts are read back out of stdout rather than off a return value, because
    stdout is where a reader gets them and a preview nobody can read has no use.
    """

    ASSETS_RE = re.compile(r"plus (\d+) shared asset file\(s\)")

    def _assets(self, printed):
        m = self.ASSETS_RE.search(printed)
        self.assertIsNotNone(m, f"no shared asset count in output:\n{printed}")
        return int(m.group(1))

    def _rules_sources(self):
        return sorted(p.relative_to(ba.RULES_DIR).as_posix()
                      for p in ba.RULES_DIR.rglob("*") if p.is_file())

    def test_a_preview_reports_the_asset_count_a_real_run_writes(self):
        # The bug: the rules module was re-emitted once per skill, and only a real
        # run's `dest.exists()` collapsed the duplicates, so the preview counted
        # them all. Both target sets are exercised because the single-layout case
        # (cursor and vscode share one) and the two-layout case (cursor and plugin
        # each get their own copy) have different correct answers, and a fix that
        # hoists the emission has to keep emitting it once *per layout*.
        for target in ("cursor,vscode", "cursor,plugin"):
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp)
                    _, preview = _run(["--target", target, "--out", str(out), "--dry-run"])
                    _, real = _run(["--target", target, "--out", str(out)])
                    self.assertEqual(self._assets(preview), self._assets(real),
                                     "the preview must report what the real run writes")

    def test_a_real_run_counts_exactly_the_files_it_left_on_disk(self):
        # The other half of the same property, and the reason the equality above is
        # not satisfiable by making both numbers equally wrong: this pins the real
        # run's count to the tree it produced. The rules half is asserted by name
        # as well, since "each rules file exactly once" is invisible in a total.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _, printed = _run(["--out", str(out)])
            on_disk = [p for root in (".agents/rules", ".agents/skills")
                       for p in (out / root).rglob("*") if p.is_file()]
            self.assertEqual(self._assets(printed), len(on_disk))
            self.assertEqual(
                sorted(p.relative_to(out / ".agents" / "rules").as_posix()
                       for p in (out / ".agents" / "rules").rglob("*") if p.is_file()),
                self._rules_sources())

    def test_an_adopted_rules_file_is_left_alone_and_counted_in_neither_run(self):
        # S-010 in the reporting dimension. The file surviving is already covered;
        # what is not is that a preview must not promise to write it either, which
        # is the same divergence as the bug from the other side.
        with tempfile.TemporaryDirectory() as tmp:
            _, fresh = _run(["--out", tmp, "--dry-run"])
            baseline = self._assets(fresh)

        mine = "# my own house style\n"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            adopted = out / ".agents" / "rules" / "house-style.md"
            adopted.parent.mkdir(parents=True)
            adopted.write_text(mine, encoding="utf-8")

            _, preview = _run(["--out", str(out), "--dry-run"])
            self.assertEqual(self._assets(preview), baseline - 1,
                             "a preview must not offer to write a file it would skip")
            self.assertEqual(adopted.read_text(encoding="utf-8"), mine)

            _, real = _run(["--out", str(out)])
            self.assertEqual(self._assets(real), baseline - 1)
            self.assertEqual(adopted.read_text(encoding="utf-8"), mine)


class TestPluginTarget(unittest.TestCase):
    """Scenarios S-015, S-016, S-017: the Claude Code plugin distribution tree.

    test-quality notes: the defect this class exists for is an installed plugin
    whose composed lens is absent, which is silent in the same way the original
    dangling-link defect was. A manifest validator cannot see it, and neither can
    a unit test on `rewrite_links`, because the plugin target rewrites nothing:
    the layout is what makes the source links resolve. So the faithful layer is
    the filesystem, and the oracle is resolving every link on disk against the
    emitted tree and asserting that none of them leaves the plugin root, since
    installing a plugin copies that directory and a path leaving it lands
    nowhere.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        self.code, self.printed = _run(["--target", "plugin", "--out", str(self.out)])

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_plugin_tree_and_its_two_manifests_are_emitted(self):
        # Scenario S-015. The oracle is on the manifest values rather than on the
        # keys being present: a marketplace entry naming a different plugin, or a
        # source that is not the emitted root, installs something other than what
        # was built, and both are well-formed JSON.
        expected = len(ba.discover_skills())
        self.assertEqual(self.code, 0)
        self.assertEqual(len(list(self.out.glob("skills/*/SKILL.md"))), expected)
        self.assertEqual(list(self.out.glob(".cursor/rules/*")), [],
                         "the plugin target is not an inlining target")
        self.assertEqual(list(self.out.glob(".github/prompts/*")), [])

        read = lambda f: json.loads((self.out / ".claude-plugin" / f).read_text(encoding="utf-8"))
        plugin, market = read("plugin.json"), read("marketplace.json")
        listed, = market["plugins"]
        self.assertEqual(listed["source"], "./")
        self.assertEqual(listed["name"], plugin["name"])
        self.assertEqual(listed["version"], plugin["version"])
        self.assertIn(f"for {expected} skill(s)", self.printed)
        self.assertIn("2 plugin manifest file(s)", self.printed)

    def test_every_link_in_the_emitted_tree_resolves_inside_the_plugin_root(self):
        # Scenario S-016, resolved on disk rather than read out of the link text.
        # The text is what looks right; what dangles is the path it lands on once
        # the directory has been copied to the install location. Both halves
        # matter: a link that resolves only because the kit happens to sit above
        # the output root is the exact defect, and it would pass an existence
        # check alone.
        root = self.out.resolve()
        broken, escaped, checked = [], [], 0
        for f in sorted(root.glob("skills/*/SKILL.md")):
            for target in LINK.findall(f.read_text(encoding="utf-8")):
                if target.lower().startswith(SKIP_PREFIXES):
                    continue
                checked += 1
                resolved = f.parent / target.split("#")[0]
                if not resolved.exists():
                    broken.append(f"{f.parent.name} -> {target}")
                elif not resolved.resolve().is_relative_to(root):
                    escaped.append(f"{f.parent.name} -> {target}")
        self.assertGreater(checked, 100, "expected the real kit's link volume")
        self.assertEqual(broken, [], f"{len(broken)} dangling link(s): {broken[:5]}")
        self.assertEqual(escaped, [], f"{len(escaped)} link(s) leaving the plugin: {escaped[:5]}")

    def test_house_review_reaches_its_rubric_from_inside_the_plugin(self):
        # Scenario S-016, on the skill that loses the most to a dangling lens: its
        # severities and rubric categories live entirely in that file, so it
        # arrives looking complete and reviews against nothing.
        skill = self.out / "skills" / "house-review" / "SKILL.md"
        links = {t for t in LINK.findall(skill.read_text(encoding="utf-8"))
                 if t.endswith("rules/review-quality.md")}
        self.assertEqual(len(links), 1, f"expected one rubric reference, got {links}")
        rubric = (skill.parent / links.pop()).resolve()
        self.assertTrue(rubric.is_file(), "the rubric reference does not resolve to a file")
        self.assertTrue(rubric.is_relative_to(self.out.resolve()))
        self.assertIn("blocker", rubric.read_text(encoding="utf-8"))
        # One authoritative copy. The module is swappable by design, and a copy
        # per skill would make swapping it twenty edits instead of one.
        self.assertEqual([p.relative_to(self.out).as_posix()
                          for p in self.out.rglob("review-quality.md")],
                         ["rules/review-quality.md"])

    def test_the_plugin_target_is_opt_in(self):
        # Scenario S-017. Both halves, because the contrast is the requirement:
        # asserting the absence alone would also pass if the target emitted
        # nothing at all. The risk guarded is a default run, whose --out is the
        # working directory, writing a .claude-plugin/ into the project that
        # invoked it, where it becomes the hand-maintained manifest this
        # generator exists to replace.
        self.assertTrue((self.out / ".claude-plugin").is_dir(),
                        "requested explicitly, the manifests must be written")
        with tempfile.TemporaryDirectory() as tmp:
            default = Path(tmp)
            code, _ = _run(["--out", str(default)])
            self.assertEqual(code, 0)
            self.assertFalse((default / ".claude-plugin").exists())
            self.assertFalse((default / "skills").exists())


class TestSkillAssetsExcludeBytecode(unittest.TestCase):
    """bug-0036: a byte-cache is not part of the skill payload, in any layout.

    test-quality notes: the condition is built rather than observed. Whether a real
    skill directory holds a `__pycache__` depends on whether the suite has already
    imported what is in it, so a test that emits the real kit passes or fails by
    ordering, which is worse than no test. This makes its own fixture skill instead,
    and asserts the contrast in one place: the bytecode is gone and the ordinary
    `.py` beside it survives. Asserting the exclusion alone would also pass if the
    rule swallowed `templates/validate.py`, which `init-worktracking` is unusable
    without.

    Both oracles, on disk and on the returned list, because the return value is what
    the run counts and reports: emitting nothing while still counting it would trade
    this defect for bug-0025's.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.out = root / "out"
        self.skill = root / "src" / "fixture-skill"
        templates = self.skill / "templates"
        (templates / "__pycache__").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("---\nname: fixture-skill\n---\n", encoding="utf-8")
        (templates / "validate.py").write_text("# a real shipped template\n", encoding="utf-8")
        (templates / "__pycache__" / "validate.cpython-311.pyc").write_bytes(b"\x00\x00\x00\x00")
        # An artefact inside __pycache__ whose suffix is not .pyc: the directory
        # half of the predicate has to catch this one on its own.
        (templates / "__pycache__" / "stale.json").write_text("{}", encoding="utf-8")
        # And a byte-cache outside any __pycache__, for the suffix half.
        (self.skill / "loose.pyc").write_bytes(b"\x00\x00\x00\x00")

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_target_receives_a_byte_cache_and_a_real_template_still_emits(self):
        for name, layout in ba.LAYOUTS.items():
            with self.subTest(target=name):
                out = self.out / name
                written = ba.emit_skill_assets(self.skill, out, False, layout)
                rels = [p.relative_to(out).as_posix() for p in written]
                on_disk = [p.relative_to(out).as_posix()
                           for p in out.rglob("*") if p.is_file()]

                expected = f"{layout.assets_dir}/fixture-skill/templates/validate.py"
                self.assertIn(expected, rels, "a real template must still be emitted")
                self.assertEqual(on_disk, [expected])
                self.assertEqual(
                    (out / expected).read_text(encoding="utf-8"),
                    "# a real shipped template\n")

                for reported in (rels, on_disk):
                    self.assertFalse(
                        [p for p in reported
                         if p.endswith(".pyc") or "__pycache__" in p.split("/")],
                        f"byte-cache emitted or counted into {name}: {reported}")


class TestDestinationContainment(unittest.TestCase):
    """bug-0060: a frontmatter `name` becomes a path component of both inlining
    destinations, so a `..` segment in one walks out of the output root.

    test-quality notes: characterization, not acceptance. See the module docstring
    for why there is no S-NNN id.

    The oracle is the filesystem rather than the return value or the exception,
    because the defect is a file existing where it should not. An emitter that
    returned an escaping path and wrote nothing would be harmless, and one that
    returned a contained path and wrote outside would be the bug, and the two are
    indistinguishable from the return value. That is the escape the shipped code
    already half-knew about: `_main`'s print line branches on
    `dest.is_relative_to(out)`, so it formats the escape and writes it anyway.

    Two layers, because there are two distinct failure modes. `_write`'s containment
    check is reached through the emitters directly, which is the only way to drive it
    with a name `_main` now rejects before dispatch. The run-level behavior, a
    non-zero exit and a message rather than a quiet skip, is driven through `main()`
    over a fixture skill tree. Either layer alone passes against a build that escapes
    quietly at the other.

    Every path here stays inside a `TemporaryDirectory`. The traversal name carries
    exactly enough `..` segments to leave `<out>` and land in the sandbox directory
    above it, so the escape is provable without a write ever reaching a real location.
    """

    # Three segments up from `<out>/.cursor/rules/` is `<out>/..`, which is the
    # `nested/` directory `_sandbox` puts between the temp root and the output root.
    ESCAPING_NAME = "../../../escaped"

    def _sandbox(self):
        """A temp root holding nothing but the output root, two levels down.

        Nothing else is placed under it, so any file this returns that is not under
        `out` was put there by the code under test.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        return root, root / "nested" / "out"

    def _source_tree(self, name=None):
        """A one-skill source tree, in its own temp directory rather than the sandbox.

        Kept apart so the sandbox holds only what the run wrote. `name` is the
        frontmatter value; the directory is always `traversal-fixture`, which is what
        makes the two disagree.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        skills = Path(tmp.name).resolve() / "skills"
        skill = skills / "traversal-fixture"
        skill.mkdir(parents=True)
        if name is not None:
            (skill / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: a fixture skill\n---\n\nBody.\n",
                encoding="utf-8")
        return skills, skill

    @contextlib.contextmanager
    def _kit(self, skills_dir):
        """Point the tool at a fixture tree, with no rules module to place.

        `RULES_DIR` is redirected to an absent path so `emit_rules_module` is a no-op,
        which keeps the sandbox holding only the per-skill writes under test.
        """
        with mock.patch.object(ba, "SKILLS_DIR", skills_dir), \
             mock.patch.object(ba, "RULES_DIR", skills_dir.parent / "absent-rules"):
            yield

    def _outside(self, root, out):
        """Every file under `root` that is not under the resolved output root."""
        return sorted(str(p) for p in root.rglob("*")
                      if p.is_file() and not p.resolve().is_relative_to(out.resolve()))

    def test_a_traversal_name_writes_nothing_outside_the_output_root(self):
        # The emitters are driven directly, below `_main`'s name check, so this
        # reaches the shared write boundary rather than the guard in front of it.
        for target in ("cursor", "vscode"):
            with self.subTest(target=target):
                root, out = self._sandbox()
                _, skill = self._source_tree()
                raised = None
                try:
                    ba.EMITTERS[target](skill, self.ESCAPING_NAME, "a fixture skill",
                                        "Body.\n", out, False)
                except Exception as exc:  # noqa: BLE001 - typed below, after the oracle
                    raised = exc
                self.assertEqual(
                    self._outside(root, out), [],
                    f"{target} wrote outside the resolved output root {out}")
                self.assertIsInstance(
                    raised, ba.OutsideOutputRoot,
                    f"{target} must refuse the destination, not skip it silently")

    def test_the_write_boundary_refuses_before_the_preview_branch(self):
        # `_write` returns early on `dry`, so a check placed after that branch never
        # fires in the one place this repository runs the tool: run-checks.py's
        # adapters gate is a --dry-run.
        root, out = self._sandbox()
        dest = out / ".cursor" / "rules" / ".." / ".." / ".." / "escaped.mdc"
        with self.assertRaises(ba.OutsideOutputRoot):
            ba._write(dest, "content\n", True, out)
        self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def test_a_traversal_name_fails_the_run_naming_the_skill_and_a_destination(self):
        root, out = self._sandbox()
        skills, _ = self._source_tree(self.ESCAPING_NAME)
        # Derived here from the documented `cursor` path shape rather than read back
        # from the tool, so the message is checked against an independent statement of
        # where the name lands. `cursor` is the first of the two default targets.
        escaped = (out / ".cursor" / "rules" / f"{self.ESCAPING_NAME}.mdc").resolve()
        self.assertFalse(escaped.is_relative_to(out.resolve()),
                         "fixture is wrong: the name must actually leave the root")

        with self._kit(skills):
            code, printed = _run(["--out", str(out)])

        self.assertEqual(self._outside(root, out), [],
                         f"the run wrote outside the resolved output root {out}")
        self.assertEqual(code, 2, f"the run must fail, not emit; it printed:\n{printed}")
        self.assertIn("traversal-fixture", printed)
        self.assertIn(self.ESCAPING_NAME, printed)
        # The refusal has to show a path that resolves outside the root, not only the
        # root it stayed inside of. Naming the root alone leaves a reader unable to see
        # that the name escapes at all, which is the fact carrying the severity.
        self.assertIn(str(escaped), printed,
                      "the refusal must name a destination outside the output root, "
                      f"not only the root itself; it printed:\n{printed}")
        self.assertIn(str(out), printed, "the output root must stay in the message")

    def test_the_named_destination_follows_the_requested_target(self):
        # The representative destination belongs to a target the run actually asked
        # for, so it cannot be hardcoded to cursor. And a plugin-only run derives no
        # path from the name at all, so it must not claim an escape that cannot happen:
        # a refusal that overstated what would occur is the same defect as one that
        # understated it.
        root, out = self._sandbox()
        skills, _ = self._source_tree(self.ESCAPING_NAME)
        with self._kit(skills):
            code, printed = _run(["--target", "vscode", "--out", str(out)])
        self.assertEqual(code, 2, printed)
        self.assertIn(str((out / ".github" / "prompts"
                           / f"{self.ESCAPING_NAME}.prompt.md").resolve()), printed)
        self.assertNotIn(".mdc", printed, "named cursor's destination for a vscode run")

        root, out = self._sandbox()
        skills, _ = self._source_tree(self.ESCAPING_NAME)
        with self._kit(skills):
            code, printed = _run(["--target", "plugin", "--out", str(out)])
        self.assertEqual(code, 2, printed)
        self.assertIn("No requested target derives a destination", printed)
        self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def test_a_preview_refuses_the_same_input_a_real_run_refuses(self):
        root, out = self._sandbox()
        skills, _ = self._source_tree(self.ESCAPING_NAME)
        with self._kit(skills):
            code, printed = _run(["--out", str(out), "--dry-run"])
        self.assertEqual(code, 2, f"a preview must refuse what a real run refuses; "
                                  f"it printed:\n{printed}")
        self.assertIn("traversal-fixture", printed)
        self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def test_a_name_matching_its_directory_still_emits_both_adapters(self):
        # The guard must be invisible on valid input, so the same fixture with an
        # honest name emits exactly what it emitted before the guard existed.
        root, out = self._sandbox()
        skills, _ = self._source_tree("traversal-fixture")
        with self._kit(skills):
            code, printed = _run(["--out", str(out)])
        self.assertEqual(code, 0, printed)
        self.assertEqual(
            sorted(p.relative_to(out).as_posix()
                   for p in out.rglob("*") if p.is_file()),
            [".cursor/rules/traversal-fixture.mdc",
             ".github/prompts/traversal-fixture.prompt.md"])
        self.assertEqual(self._outside(root, out), [])


if __name__ == "__main__":
    unittest.main()
