"""Tests for scripts/check-citations.py, the conformance-matrix citation guard (chore-0049).

Every test here runs against a fixture tree built in a temporary directory rather than
against this repository. That is deliberate: a test asserting "the real matrices are
clean" passes for as long as they happen to be clean and proves nothing about the
checker, which is the shape of guard this task exists to stop shipping. The fixtures
construct the stale citation on purpose, so each test fails if the checker stops looking.

The forms the checker decides, and the forms it declines to, are both asserted. An
unchecked citation being counted as unchecked is as load-bearing as an unresolved one
being reported: a checker that silently treats what it cannot decide as passing is the
thing `spec-conformance`'s coverage proof exists to forbid.
"""
import importlib.util
import io
import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Loaded by path: the filename has a hyphen, so it is not importable as a module name.
# Mirrors how the other script tests in this suite reach their subject.
_spec = importlib.util.spec_from_file_location(
    "check_citations", REPO_ROOT / "scripts" / "check-citations.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


MATRIX_HEADER = """---
title: thing conformance
spec: docs/spec/thing.md
---

# thing conformance matrix

Spec-vs-implementation audit of [`scripts/thing.py`](../../scripts/thing.py) against
[`thing.md`](thing.md).

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
"""

SUBJECT = '''"""A fixture subject."""


WIDGET_RE = "w"


def assemble(parts):
    # a comment between the guard and its return
    if not parts:
        return None
    return "".join(parts)
'''


class _Tree:
    """A throwaway repository root holding one matrix, one subject, and one test file."""

    def __init__(self, rows, subject=SUBJECT, tests="def test_assembles_the_parts():\n    pass\n"):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        (self.root / "docs" / "spec").mkdir(parents=True)
        (self.root / "scripts").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "scripts" / "thing.py").write_text(subject, encoding="utf-8")
        (self.root / "tests" / "test_thing.py").write_text(tests, encoding="utf-8")
        (self.root / "docs" / "spec" / "thing.md").write_text("# thing\n", encoding="utf-8")
        (self.root / "docs" / "spec" / "thing.conformance.md").write_text(
            MATRIX_HEADER + "".join(rows), encoding="utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def run(self):
        out = io.StringIO()
        code = cc.main([], out=out, root=self.root)
        return code, out.getvalue()

    def audit(self):
        return cc.audit(self.root)


def row(evidence, item="S-001 a thing", note=""):
    return f"| Scenarios | {item} | Conformed | {evidence} | {note} |\n"


THREE_COLUMN_HEADER = """---
title: thing conformance
spec: docs/spec/thing.md
---

# thing conformance matrix

Spec-vs-implementation audit of [`scripts/thing.py`](../../scripts/thing.py) against
[`thing.md`](thing.md).

## Matrix

| Scenario | Status | Evidence |
|---|---|---|
"""

NO_EVIDENCE_HEADER = THREE_COLUMN_HEADER.replace(
    "| Scenario | Status | Evidence |", "| Scenario | Status | Finding |")


class _ShapedTree(_Tree):
    """A tree whose matrix uses a column layout other than the five-column house shape."""

    def __init__(self, header, rows, **kwargs):
        super().__init__([], **kwargs)
        (self.root / "docs" / "spec" / "thing.conformance.md").write_text(
            header + "".join(rows), encoding="utf-8")


def three_column_row(evidence, item="S-001 a thing"):
    return f"| {item} | Conformed | {evidence} |\n"


class ColumnLayoutTests(unittest.TestCase):
    """`bug-0049`: a matrix whose columns are not the house shape was skipped in silence.

    The evidence column was read at a fixed index and a row needed four or more cells, so
    a three-column matrix yielded no rows at all. Every one of its citations went
    unaudited, the run reported `0 unresolved`, and four closed tasks cited this gate as
    green over that file. The reproduction below is the one from the task: inject a
    citation that resolves nowhere and watch what the run says.
    """

    def test_a_dead_citation_in_a_three_column_matrix_is_reported(self):
        """The reproduction. Before the fix this exited 0 with byte-identical output."""
        with _ShapedTree(THREE_COLUMN_HEADER,
                         [three_column_row("`scripts/thing.py` / `no_such_symbol()`")]) as tree:
            code, out = tree.run()

        self.assertEqual(code, 1,
                         "a citation resolving nowhere in a three-column matrix was not "
                         "reported, so the gate cannot fail on that shape")
        self.assertIn("no_such_symbol", out)

    def test_a_live_citation_in_a_three_column_matrix_is_not_reported(self):
        """The other half, so the fix is not simply failing everything it now reads."""
        with _ShapedTree(THREE_COLUMN_HEADER,
                         [three_column_row("`scripts/thing.py` / `assemble()`")]) as tree:
            code, out = tree.run()

        self.assertEqual(code, 0)
        self.assertIn("0 unresolved", out)

    def test_a_three_column_matrix_contributes_citations_at_all(self):
        """The count is what four closed tasks read as coverage. It was zero for that
        file, and the two figures in the summary were the only place it showed."""
        with _ShapedTree(THREE_COLUMN_HEADER,
                         [three_column_row("`scripts/thing.py` / `assemble()`")]) as tree:
            result = cc.audit(tree.root)

        self.assertGreater(result.extracted, 0,
                           "a three-column matrix yielded no citations, which is the "
                           "defect bug-0049 recorded")
        self.assertEqual(result.unreadable, [])

    def test_the_item_column_is_found_by_its_heading_not_its_position(self):
        """`Scenario` sits where `Item` sits in the house shape, and the reported item has
        to name the row rather than whatever column happened to be second."""
        with _ShapedTree(THREE_COLUMN_HEADER,
                         [three_column_row("`scripts/thing.py` / `no_such_symbol()`",
                                           item="S-042 the item")]) as tree:
            _, out = tree.run()

        self.assertIn("S-042 the item", out,
                      "the reported row was identified by position rather than by the "
                      "column its heading names")

    def test_a_matrix_with_no_evidence_column_is_reported_as_unread_not_clean(self):
        """The generalisation, and the part that matters more than the fix.

        Widening one shape leaves the next unanticipated one failing the same way. A
        matrix the checker cannot find an evidence column in is named and the run reports
        it could not run, which is the same answer the module already gives when it finds
        no matrix at all: no question asked is not a clean answer.
        """
        with _ShapedTree(NO_EVIDENCE_HEADER,
                         [three_column_row("`scripts/thing.py` / `no_such_symbol()`")]) as tree:
            code, out = tree.run()

        self.assertEqual(code, 2,
                         "a matrix the checker could not read was reported as a clean run")
        self.assertIn("COULD NOT READ", out)
        self.assertIn("thing.conformance.md", out,
                      "the unreadable matrix was counted but not named, which is how this "
                      "defect stayed invisible")

    def test_a_matrix_that_cites_nothing_is_named_but_does_not_fail_the_run(self):
        """A spec whose scenarios are all not-built has nothing to cite yet. Failing that
        would be the false alarm this checker's design deliberately avoids, so it is
        reported and the run stays clean."""
        with _ShapedTree(THREE_COLUMN_HEADER,
                         [three_column_row("Owned by feat-0056.")]) as tree:
            code, out = tree.run()

        self.assertEqual(code, 0, "a matrix with nothing to cite failed the run")
        # The name, not just the phrase. Asserting the phrase alone let a mutation drop the
        # filename and keep the sentence, which reports that *something* cited nothing
        # without saying what, and naming it is the entire value of the line.
        note = [line for line in out.splitlines() if "yielded no citation" in line]
        self.assertEqual(len(note), 1, "the note about a matrix citing nothing is missing")
        self.assertIn("thing.conformance.md", note[0],
                      "a matrix contributing nothing was reported without being named, so "
                      "a reader cannot tell which file it was")

    def test_the_house_five_column_shape_still_reads_exactly_as_before(self):
        """The regression that would matter most: ten of the eleven real matrices use the
        five-column shape, and this change must not move them."""
        with _Tree([row("`scripts/thing.py` / `no_such_symbol()`")]) as tree:
            code, out = tree.run()

        self.assertEqual(code, 1)
        self.assertIn("no_such_symbol", out)

        with _Tree([row("`scripts/thing.py` / `assemble()`")]) as tree:
            code, _ = tree.run()
        self.assertEqual(code, 0)


class QuotedPhraseTests(unittest.TestCase):
    """The acceptance criterion: a phrase that no longer appears in the named file."""

    def test_a_phrase_absent_from_the_named_file_is_reported(self):
        with _Tree([row("`assemble()` / `return \"-\".join(parts)`")]) as tree:
            code, report = tree.run()
        self.assertEqual(1, code, "an unresolved citation must fail the check")
        self.assertIn('return "-".join(parts)', report)
        self.assertIn("thing.conformance.md", report)
        self.assertIn("1 unresolved", report)

    def test_a_phrase_still_present_in_the_named_file_is_not_reported(self):
        with _Tree([row("`assemble()` / `return \"\".join(parts)`")]) as tree:
            code, report = tree.run()
        self.assertEqual(0, code)
        self.assertIn("0 unresolved", report)

    def test_a_phrase_collapsed_across_an_intervening_comment_still_resolves(self):
        # Measured against the real corpus on 2026-08-28: the S-010 row of
        # cloud-executable.conformance.md cites `if reachable(project_root, home):
        # return None`, and the hook has two comment lines between the guard and the
        # return. The citation is correct and a literal substring test flags it, which is
        # the false-positive class that gets a checker switched off.
        with _Tree([row("`assemble()` / `if not parts: return None`")]) as tree:
            code, report = tree.run()
        self.assertEqual(0, code, "an intervening comment does not break a citation")

    def test_quoting_style_does_not_decide_a_citation(self):
        # Measured on the real corpus: the bootstrap-registration row cites
        # `matcher: "startup"` where .claude/settings.json holds `"matcher": "startup"`.
        # A citation may render quoting differently from the source it quotes.
        with _Tree([row("`assemble()` / `return ''.join(parts)`")]) as tree:
            code, _ = tree.run()
        self.assertEqual(0, code)


class ElisionTests(unittest.TestCase):
    """A signposted elision is unchecked, never a failure.

    Three rows in build-adapters.conformance.md are written this way and all three are
    correct: `SHARED/skills/<name>/<target>` (S-007), `any(start <= m.start() < end ...)`
    (S-018), and `for fname, obj in ...` (S-015). An author who writes `...` has said
    they are not quoting; a substring test cannot decide text nobody claimed was there.
    """

    def test_an_ellipsis_phrase_is_unchecked_rather_than_unresolved(self):
        with _Tree([row("`assemble()` / `for part, index in ...`")]) as tree:
            code, report = tree.run()
            found = [c for c in tree.audit().citations if "for part, index" in c.text]
        self.assertEqual(0, code, "an elision must not fail the check")
        self.assertEqual(["unchecked"], [c.status for c in found])
        self.assertEqual(["signposted elision"], [c.reason for c in found])
        self.assertIn("signposted elision", report)

    def test_an_angle_bracket_placeholder_is_unchecked(self):
        with _Tree([row("`assemble()` / `parts/<name>/<target> joined`")]) as tree:
            code, _ = tree.run()
            found = [c for c in tree.audit().citations if "<name>" in c.text]
        self.assertEqual(0, code)
        self.assertEqual(["unchecked"], [c.status for c in found])

    def test_an_elision_is_not_quietly_counted_as_audited(self):
        with _Tree([row("`assemble()` / `for part, index in ...`")]) as tree:
            result = tree.audit()
        self.assertEqual(0, len([c for c in result.citations
                                 if c.status == "resolved" and "..." in c.text]))


class SymbolTests(unittest.TestCase):
    """A symbol name is decidable for Python: a renamed symbol leaves the file entirely."""

    def test_a_symbol_absent_from_the_named_file_is_reported(self):
        with _Tree([row("`disassemble()` / the loop")]) as tree:
            code, report = tree.run()
        self.assertEqual(1, code)
        self.assertIn("disassemble()", report)

    def test_a_constant_absent_from_the_named_file_is_reported(self):
        with _Tree([row("`GADGET_RE` in the module")]) as tree:
            code, report = tree.run()
        self.assertEqual(1, code)
        self.assertIn("GADGET_RE", report)

    def test_a_constant_still_present_is_not_reported(self):
        with _Tree([row("`WIDGET_RE` in the module")]) as tree:
            code, _ = tree.run()
        self.assertEqual(0, code)

    def test_a_builtin_is_unchecked_because_the_test_would_be_vacuous(self):
        # `sum()` appears in build-adapters.conformance.md's S-012 row as prose about a
        # builtin call, not as a citation of a definition. Checking a builtin's presence
        # is a test that cannot fail for any Python file, and a check that cannot fail is
        # unchecked whatever it printed (AGENTS.md, on bug-0045).
        with _Tree([row("`assemble()` / a `sum()` over the parts")]) as tree:
            code, _ = tree.run()
            found = [c for c in tree.audit().citations if c.text == "sum()"]
        self.assertEqual(0, code)
        self.assertEqual(["unchecked"], [c.status for c in found])


class TestNameTests(unittest.TestCase):
    """A cited test name is a Python function name, so it needs no file attribution."""

    def test_a_cited_test_that_no_longer_exists_is_reported(self):
        with _Tree([row("`assemble()`", note="Test `test_assembles_the_pieces`")]) as tree:
            code, report = tree.run()
        self.assertEqual(1, code)
        self.assertIn("test_assembles_the_pieces", report)

    def test_a_cited_test_that_exists_is_not_reported(self):
        with _Tree([row("`assemble()`", note="Test `test_assembles_the_parts`")]) as tree:
            code, _ = tree.run()
        self.assertEqual(0, code)

    def test_a_test_name_is_read_from_the_note_column_too(self):
        # Matrices differ on where they put test evidence: cloud-executable puts it in the
        # Note column, build-adapters in a separate coverage table. A test name is
        # self-identifying, so it is read from the whole row rather than from one column.
        with _Tree([row("`assemble()`", note="Test `test_assembles_the_pieces`")]) as tree:
            found = [c for c in tree.audit().citations
                     if c.text == "test_assembles_the_pieces"]
        self.assertEqual(["unresolved"], [c.status for c in found])


class CoverageProofTests(unittest.TestCase):
    """The run states audited and unaudited counts, and the arithmetic rather than a claim."""

    def test_the_report_states_both_counts_and_the_arithmetic(self):
        with _Tree([row("`assemble()` / `return \"\".join(parts)` and `--flag`")]) as tree:
            _, report = tree.run()
            result = tree.audit()
        self.assertIn(f"{result.audited} audited + {result.unaudited} unaudited "
                      f"= {result.extracted} extracted", report)

    def test_the_counts_actually_add_up(self):
        with _Tree([row("`assemble()` / `return \"\".join(parts)` and `--flag` and `S-001`"),
                    row("`WIDGET_RE` / `for part, index in ...`", item="S-002 another")]) as tree:
            result = tree.audit()
        self.assertEqual(result.extracted, result.audited + result.unaudited)
        self.assertEqual(result.extracted, len(result.citations))

    def test_an_undecidable_form_is_counted_unaudited_not_passing(self):
        with _Tree([row("`assemble()` / the `--flag` option")]) as tree:
            result = tree.audit()
            flag = [c for c in result.citations if c.text == "--flag"]
        self.assertEqual(["unchecked"], [c.status for c in flag])
        self.assertGreaterEqual(result.unaudited, 1)

    def test_a_citation_with_no_resolvable_subject_is_unchecked_not_passing(self):
        # A matrix whose header names no file that resolves. Nothing can be decided about
        # its phrases, and guessing is the failure mode the coverage proof forbids.
        with _Tree([]) as tree:
            matrix = tree.root / "docs" / "spec" / "thing.conformance.md"
            matrix.write_text(
                "# orphan conformance matrix\n\nAudit of nothing.\n\n## Matrix\n\n"
                "| Section | Item | Status | Evidence | Note |\n|---|---|---|---|---|\n"
                + row("`return \"-\".join(parts)`"), encoding="utf-8")
            code, report = tree.run()
            result = tree.audit()
        self.assertEqual(0, code, "an unattributable citation is unchecked, not failed")
        self.assertIn("no resolvable subject file", report)
        self.assertGreaterEqual(result.unaudited, 1)

    def test_the_summary_line_varies_with_what_was_examined(self):
        # chore-0064's lesson, applied here at birth rather than after the fact: the line
        # run-checks.py surfaces beneath this gate's status must differ between a run over
        # a populated tree and a run over a smaller one, or the gate reports coverage it
        # did not have (bug-0045).
        with _Tree([row("`assemble()` / `return \"\".join(parts)`")]) as one:
            _, small = one.run()
        with _Tree([row("`assemble()` / `return \"\".join(parts)`"),
                    row("`WIDGET_RE` / `if not parts:`", item="S-002 another")]) as two:
            _, large = two.run()
        self.assertNotEqual(small, large)
        self.assertNotEqual(small.strip().splitlines()[-1], large.strip().splitlines()[-1])


def breakdown_sum(report, prefix):
    """(stated total, sum of the breakdown beneath it) for one coverage-proof line.

    Parsed from the printed text rather than from the `Result`, because the defect this
    guards against lived in the report's caller and not in the counting: `Result` knew
    `audited` was 396 while the line beneath it printed forms summing to 401. A test that
    only re-added the object's own numbers would have agreed with the object and missed it.
    """
    for line in report.splitlines():
        if not line.startswith(prefix):
            continue
        stated = int(re.match(r"[A-Za-z]+ (\d+) of \d+", line).group(1))
        segment = line.split(": ", 1)[1].rstrip(".")
        if segment == "nothing":
            return stated, 0
        return stated, sum(int(part.rsplit(" ", 1)[1]) for part in segment.split(", "))
    raise AssertionError(f"no line starting {prefix!r} in:\n{report}")


# One row of each disposition, so both halves of the partition are non-trivial and the
# five-citation gap the first delivery had is present in miniature: `sum()` is a decidable
# form deliberately not audited, and so is the elided phrase. Under the shape that shipped
# first, the audited breakdown counted both and summed to 5 beneath a stated total of 3.
MIXED_ROWS = [
    row('`assemble()` / `return "".join(parts)`'),
    row('`assemble()` / a `sum()` over the parts, `for part, index in ...`, the `--flag`',
        item="S-002 another"),
]


class CoverageArithmeticTests(unittest.TestCase):
    """The one number the acceptance criterion names, pinned rather than eyeballed.

    "The run states the audited and unaudited counts, and the arithmetic rather than the
    claim." A breakdown that does not add up to the total it sits under is precisely what
    that criterion exists to prevent, and in a checker whose whole purpose is making stale
    claims falsifiable it is the worst possible place for it. It was wrong on first
    delivery and caught in verification, so it is pinned at both levels here: the object's
    counts, and the bytes the run actually prints.
    """

    def test_the_audited_breakdown_sums_to_the_audited_count(self):
        with _Tree(MIXED_ROWS) as tree:
            result = tree.audit()
        self.assertEqual(result.audited, sum(result.audited_kinds().values()))

    def test_the_unaudited_breakdown_sums_to_the_unaudited_count(self):
        with _Tree(MIXED_ROWS) as tree:
            result = tree.audit()
        self.assertEqual(result.unaudited, sum(result.unaudited_reasons().values()))

    def test_no_unaudited_citation_leaks_into_the_audited_breakdown(self):
        # The defect stated directly. Both dispositions below have a decidable form, which
        # is what let them pass a filter that only excluded the `other` kind.
        with _Tree(MIXED_ROWS) as tree:
            result = tree.audit()
            declined = [c for c in result.citations if c.status == "unchecked"]
        self.assertEqual({"symbol", "quoted phrase", "other"},
                         {c.kind for c in declined},
                         "the fixture must hold a declined citation of a decidable form")
        self.assertEqual(len([c for c in result.citations if c.status != "unchecked"]),
                         sum(result.audited_kinds().values()))

    def test_the_printed_audited_breakdown_sums_to_its_stated_total(self):
        with _Tree(MIXED_ROWS) as tree:
            _, report = tree.run()
        stated, summed = breakdown_sum(report, "Audited ")
        self.assertEqual(stated, summed,
                         f"the audited breakdown does not close:\n{report}")

    def test_the_printed_unaudited_breakdown_sums_to_its_stated_total(self):
        with _Tree(MIXED_ROWS) as tree:
            _, report = tree.run()
        stated, summed = breakdown_sum(report, "Unaudited ")
        self.assertEqual(stated, summed,
                         f"the unaudited breakdown does not close:\n{report}")

    def test_no_reason_carries_a_comma_so_the_breakdown_stays_parseable(self):
        # The line above is machine-checked now, and a reason containing ", " would split
        # into two entries and make the parse silently wrong rather than loudly broken.
        for name in dir(cc):
            if name.startswith("UNCHECKED_"):
                with self.subTest(reason=name):
                    self.assertNotIn(", ", getattr(cc, name))

    def test_both_breakdowns_close_over_the_real_corpus(self):
        # The fixtures prove the rule; this proves it on the input the defect appeared on.
        result = cc.audit(REPO_ROOT)
        self.assertEqual(result.audited, sum(result.audited_kinds().values()))
        self.assertEqual(result.unaudited, sum(result.unaudited_reasons().values()))
        self.assertEqual(result.extracted, result.audited + result.unaudited)

    def test_the_printed_breakdowns_close_over_the_real_corpus(self):
        out = io.StringIO()
        cc.main([], out=out)
        report = out.getvalue()
        for prefix in ("Audited ", "Unaudited "):
            with self.subTest(line=prefix):
                stated, summed = breakdown_sum(report, prefix)
                self.assertEqual(stated, summed, report)


class DegenerateInputTests(unittest.TestCase):
    """Construct the empty input and see what the tool actually says (AGENTS.md).

    A guard that reports `ok` over a tree holding nothing is the class this task belongs
    to, so this checker is asked the question at birth instead of after someone finds it.
    """

    def test_a_tree_with_no_matrices_cannot_run_rather_than_passing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "docs" / "spec").mkdir(parents=True)
            out = io.StringIO()
            code = cc.main([], out=out, root=root)
        self.assertEqual(2, code, "no matrices means the question was not asked")
        self.assertIn("no conformance matri", out.getvalue().lower())

    def test_a_matrix_with_no_rows_is_reported_as_examining_nothing(self):
        with _Tree([]) as tree:
            code, report = tree.run()
        self.assertEqual(0, code)
        self.assertIn("0 audited", report)


class StrayCheckoutTests(unittest.TestCase):
    """A finding must not depend on whether someone has an agent worktree open.

    `fix-batch` puts an isolated checkout under `.claude/worktrees/`, so a machine mid-batch
    holds a second copy of every script here. The basename index resolves a bare backticked
    filename only when exactly one file carries the name, so an unskipped stray copy would
    stop resolving it and report every phrase cited against that file as unresolved.
    """

    def test_a_worktree_copy_does_not_make_a_filename_ambiguous(self):
        with _Tree([row("`thing.py` / `return \"\".join(parts)`")]) as tree:
            stray = tree.root / ".claude" / "worktrees" / "wt-x" / "scripts"
            stray.mkdir(parents=True)
            (stray / "thing.py").write_text("# a stale copy\n", encoding="utf-8")
            code, report = tree.run()
        self.assertEqual(0, code, report)

    def test_the_stray_copy_is_absent_from_the_index_entirely(self):
        with _Tree([]) as tree:
            stray = tree.root / ".claude" / "worktrees" / "wt-x" / "scripts"
            stray.mkdir(parents=True)
            (stray / "thing.py").write_text("# a stale copy\n", encoding="utf-8")
            holders = cc._index_by_basename(tree.root).get("thing.py", [])
            self.assertEqual(1, len(holders), "only the real file may be indexed")
            # Compared by filesystem identity rather than by string, and inside the
            # fixture's lifetime because `samefile` stats both sides. A path built from an
            # unresolved root and one recorded from a resolved root differ on macOS, where
            # /var resolves to /private/var, and on Windows, where a temporary directory
            # is reachable by an 8.3 short name.
            self.assertTrue(holders[0].samefile(tree.root / "scripts" / "thing.py"))


class ArgumentTests(unittest.TestCase):
    """No flags, for the reason run-checks.py takes none: one question, one answer."""

    def test_any_argument_is_refused(self):
        out = io.StringIO()
        code = cc.main(["--only", "cloud-executable"], out=out)
        self.assertEqual(2, code)
        self.assertIn("takes no arguments", out.getvalue())


class RealCorpusTests(unittest.TestCase):
    """The one thing worth asserting about this repository's own matrices.

    Not that they are clean: that is what the gate reports on every run, and pinning it
    here would duplicate the gate while quietly turning a real future finding into a red
    test in an unrelated suite. What is worth pinning is that the checker still reaches
    them at all, since a glob that stops matching is how a guard goes silent.
    """

    def test_the_real_matrices_are_reached_and_something_is_audited(self):
        result = cc.audit(REPO_ROOT)
        self.assertGreater(len(result.matrices), 0, "the matrix glob matches nothing")
        self.assertGreater(result.audited, 0, "no citation in the corpus was decidable")
        self.assertEqual(result.extracted, result.audited + result.unaudited)

    def test_the_line_number_citation_form_is_still_absent(self):
        # bug-0037 removed line-number citations and nothing should reintroduce them.
        # This checker deliberately does not make them safe again; it decides symbols,
        # test names, and quoted phrases, none of which is a line anchor.
        import re
        anchor = re.compile(r"[A-Za-z0-9_./-]+\.(?:md|py|json|mjs|yml):[0-9]+")
        for matrix in cc.matrices_under(REPO_ROOT):
            with self.subTest(matrix=matrix.name):
                self.assertEqual([], anchor.findall(matrix.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
