#!/usr/bin/env python3
"""Tests for the `systematic-debugging` skill (`feat-0061`).

One test per scenario in `docs/spec/systematic-debugging.md`, S-001 through S-015, each named
so the scenario it proves is identifiable. S-014 and S-015 arrived from `chore-0078`, which
settled the contract's first Open Question on 2026-08-29.

**These are structural assertions over the skill's prose, and that is a real bound rather than
an oversight.** A skill body is instructions to a model, so a test can assert an instruction is
present and cannot assert a model obeyed it. That is weaker than execution, and it is stated
here rather than left for a verifier to discover. The precedent is
`TestControlDegradesWithoutTheHarness` in `test_observatory_serve.py`, which states the same
bound over the same kind of artifact. Closing the gap is `feat-0062`'s job, by running the
skill on a real defect; nothing in this file can do it.

What a structural test can still decide, and what this file therefore spends its effort on:

- **Exact sets, not presence.** The verdict vocabulary is read out of its table and compared as
  a set, so a fourth verdict fails and a missing one fails. A test asserting only that the
  three appear passes against a skill that also invented a fourth.
- **Presence conditions, not just fields.** Every record field is compared against the
  condition the contract gives for when it is present, and `implicated_files` and
  `regression_observable` being **absent** on S-010 is asserted as its own obligation.
- **A form, not a bare phrase.** Every assertion below is scoped to a named section located by
  its heading, or to a table located by its alignment rule. This kit has three recorded
  occasions where an assertion matching a bare word in source text was satisfied by a comment,
  broken by a comment, and once satisfied by the comment explaining the very fix. Markdown has
  no comments to strip, so the equivalent trap here is a phrase that happens to appear in the
  wrong section, and scoping is what removes it. `section()` raises rather than returning
  nothing when a heading is gone, so a restructured body fails loudly instead of vacuously.

Standard library only, matching the rest of `tests/`.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import install                                      # noqa: E402

SKILL = REPO_ROOT / ".agents" / "skills" / "systematic-debugging" / "SKILL.md"

# The three verdicts, from the contract's Proposed Surface. Written out here rather than
# derived from the skill, because a test that reads its expectation out of the thing it is
# testing proves the file is self-consistent and nothing else.
VERDICTS = frozenset({"root_cause_found", "not_reproducible", "architectural"})

# Field name -> the contract's own "Present when" text, backticks stripped. The conditions are
# half the contract here: a record listing every field with no conditions is a record whose
# reader cannot tell an omission from an oversight.
RECORD_FIELDS = {
    "verdict": "always",
    "symptom": "always",
    "reproduction": "always",
    "hypotheses": "always",
    "root_cause": "root_cause_found",
    "confirming_observation": "root_cause_found",
    "implicated_files": "root_cause_found, and the cause implicates code",
    "regression_observable": "root_cause_found, and the cause implicates code",
    "missing_input": "not_reproducible",
    "bound_reached": "architectural",
}

INPUTS = {"Defect report": "yes", "Reproduction steps": "no",
          "Investigation bound": "no", "Record destination": "no"}


def body() -> str:
    return SKILL.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The text under `heading`, up to the next heading of the same or shallower level.

    Bounded at the next same-or-shallower heading rather than at a fixed offset, so a section
    gaining a subsection keeps its whole body and a section added below is not swallowed into
    the one above it. Raises when the heading is absent, because a scoped assertion over an
    empty string passes for the wrong reason, which is the failure mode this helper exists to
    remove rather than to introduce one level down.
    """
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise AssertionError(
            f"the skill body has no heading {heading!r}, so every assertion scoped to it "
            f"would have passed over an empty string") from None
    for j in range(start + 1, len(lines)):
        candidate = lines[j]
        if candidate.startswith("#"):
            if len(candidate) - len(candidate.lstrip("#")) <= level:
                return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


def table_rows(text: str) -> list[list[str]]:
    """Body rows of every pipe table in `text`, as lists of stripped cells.

    A body row is one that follows an alignment rule, so the header is dropped by what it is
    rather than by its position, and a table gaining a row above does not shift what a caller
    reads. `bug-0049` is the recorded cost of reading a matrix by fixed position.
    """
    rows: list[list[str]] = []
    in_body = False
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            in_body = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and all(c and set(c) <= set("-:") for c in cells):
            in_body = True
            continue
        if in_body:
            rows.append(cells)
    return rows


def token(cell: str) -> str:
    """The single backticked token in `cell`, or the cell itself when it carries none."""
    match = re.fullmatch(r"`([^`]+)`", cell.strip())
    return match.group(1) if match else cell.strip()


def flat(text: str) -> str:
    """`text` with every run of whitespace collapsed to one space, and the ends trimmed."""
    return re.sub(r"\s+", " ", text).strip()


def bullet(text: str, lead: str) -> str:
    """The bullet in `text` whose first line begins `- **<lead>`, with its continuations.

    Scoping to one bullet is what stops an assertion about the does-not-reproduce branch being
    satisfied by a sentence in the branch beside it.
    """
    lines = text.splitlines()
    opener = f"- **{lead}"
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(opener))
    except StopIteration:
        raise AssertionError(f"no bullet beginning {opener!r} in the section") from None
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith("- ") or (line and not line.startswith(" ")):
            break
        out.append(line)
    return "\n".join(out)


class SkillTestCase(unittest.TestCase):
    """Shared body reader. Read per test rather than once at import, so a test run reflects
    the file on disk at the time it ran rather than at collection time."""

    def setUp(self):
        self.body = body()

    def assertContains(self, haystack: str, needle: str, why: str):
        """Substring assertion with whitespace collapsed on both sides.

        A markdown body is hard-wrapped, so an obligation asserted on here can sit either side
        of a line break and moves whenever a sentence above it is edited. Matching the raw text
        would make every one of these assertions a test of the current line width: it fails on
        a rewrap that changed nothing, and it teaches the next author to loosen the assertion
        rather than to reflow the prose. Wording, case, and punctuation are content and are
        still compared exactly.
        """
        self.assertIn(flat(needle), flat(haystack), f"{why} (looked for {needle!r})")


class TestTheVerdictVocabulary(SkillTestCase):
    """The contract's Proposed Surface, and the one assertion most easily written too weakly."""

    def test_the_verdicts_are_exactly_the_three_the_contract_names(self):
        rows = table_rows(section(self.body, "## Verdicts"))
        names = [token(row[0]) for row in rows]
        self.assertEqual(set(names), set(VERDICTS),
                         "the skill's verdict table is not exactly the contract's three "
                         "verdicts, so a run could end on a vocabulary nothing else here reads")
        self.assertEqual(len(names), len(VERDICTS),
                         "a verdict is listed twice, so the table is not a vocabulary")

    def test_no_fourth_verdict_is_instructed_anywhere_in_the_body(self):
        """The exact-set test above reads the `## Verdicts` table and nothing else, which is
        a narrower claim than it looks. From an independent verification of `feat-0061`: a
        fourth verdict instructed in a Procedure step leaves that table untouched, and the
        Procedure is what an agent actually follows. So the set is taken from every
        `verdict: X` span in the body, and the record's own field cell is checked for a
        cardinality it does not have.
        """
        named = set(re.findall(r"`verdict:\s*([a-z_]+)`", self.body))
        self.assertTrue(named, "no `verdict: X` span appears in the body at all, so this "
                               "assertion could not fail")
        self.assertEqual(named, set(VERDICTS),
                         "a verdict token outside the contract's three is instructed in the "
                         "body, or one of the three is never actually returned by any step")

        cell = {token(row[0]): row[2] for row in
                table_rows(section(self.body, "## The diagnosis record"))}["verdict"]
        self.assertRegex(cell, r"(?i)one of the three above",
                         "the record does not bind `verdict` to the three")
        self.assertNotRegex(cell, r"(?i)\b(four|five|another|a new one)\b",
                            "the record's `verdict` field admits a value outside the three")

    def test_exactly_one_verdict_per_run_is_stated_rather_than_implied(self):
        head = section(self.body, "## Verdicts")
        self.assertRegex(head, r"(?i)exactly one per run",
                         "the skill lists the verdicts without saying a run returns one")
        self.assertRegex(head, r"(?i)there is no fourth",
                         "nothing closes the set, so an invented fourth verdict is not "
                         "excluded by the body a model actually reads")


class TestTheDiagnosisRecord(SkillTestCase):
    """Every field, with the condition the contract gives for when it is present."""

    def rows(self):
        return {token(r[0]): r[1] for r in
                table_rows(section(self.body, "## The diagnosis record"))}

    def test_every_record_field_appears_and_no_others(self):
        self.assertEqual(set(self.rows()), set(RECORD_FIELDS),
                         "the record table does not match the contract's field set")

    def test_every_record_field_carries_its_presence_condition(self):
        got = self.rows()
        for field, condition in RECORD_FIELDS.items():
            with self.subTest(field=field):
                self.assertEqual(got[field].replace("`", ""), condition,
                                 f"{field}'s presence condition does not match the contract")

    def test_an_unmet_field_is_omitted_rather_than_emptied(self):
        """The condition column is only meaningful if the body says what an unmet one does."""
        self.assertRegex(section(self.body, "## The diagnosis record"),
                         r"(?i)is \*\*omitted\*\*, not filled with a placeholder",
                         "the record says when each field is present and never what happens "
                         "when it is not, so an empty placeholder satisfies the table")

    def test_the_four_inputs_appear_with_their_required_flags(self):
        got = {r[0]: r[1] for r in table_rows(section(self.body, "## Inputs"))}
        self.assertEqual(got, INPUTS,
                         "the skill's inputs do not match the contract's four, or one has the "
                         "wrong required flag")


class TestScenarios(SkillTestCase):
    """One test per scenario. Each is scoped to the section that carries the obligation."""

    # S-001: a reproducible defect yields a named cause.
    def test_s001_a_confirmed_hypothesis_returns_a_cause_with_a_disconfirming_observation(self):
        confirm = bullet(section(self.body, "### 5. One hypothesis at a time"),
                         "The result confirms it.")
        self.assertContains(confirm, "`verdict: root_cause_found`",
                            "the confirm branch does not name the verdict it returns")
        self.assertContains(confirm, "`root_cause`",
                            "the confirm branch does not require the cause to be stated")
        self.assertContains(confirm, "`confirming_observation`",
                            "the confirm branch does not require a confirming observation")
        self.assertContains(
            confirm, "would have differed had the hypothesis been wrong",
            "the confirming observation is required without the counterfactual that makes it "
            "evidence, so any observation at all satisfies it")
        self.assertContains(
            confirm, "the hypothesis is still open",
            "nothing says what to do when no observation would have differed, so a trial that "
            "could not have failed still closes the run")

    # S-002: a defect that will not reproduce is a verdict, not a failure.
    def test_s002_a_defect_that_will_not_reproduce_returns_a_verdict_and_no_cause(self):
        branch = bullet(section(self.body, "### 2. Reproduce before you explain"),
                        "It does not reproduce.")
        self.assertContains(branch, "`verdict: not_reproducible`",
                            "the non-reproducing branch does not name its verdict")
        self.assertContains(branch, "`missing_input`",
                            "the branch does not require what would change the answer")
        self.assertContains(branch, "no `root_cause` is offered",
                            "the branch does not forbid a cause, so one may still be guessed")
        self.assertContains(
            branch, "This is a result.",
            "the branch does not say the verdict is a result rather than a failed run, which "
            "is the sentence that stops it being retried until it produces a cause")

    # S-003: a disproved hypothesis is recorded, not discarded.
    def test_s003_a_disproved_hypothesis_is_retained_and_the_next_is_a_separate_entry(self):
        branch = bullet(section(self.body, "### 5. One hypothesis at a time"),
                        "The result contradicts the hypothesis.")
        self.assertContains(branch, "retains the hypothesis, its trial",
                            "the disproved branch does not require the hypothesis to be kept")
        self.assertContains(branch, "disconfirming result",
                            "the disproved branch does not require the result to be kept")
        self.assertContains(branch, "**separate entry**",
                            "nothing stops the next hypothesis overwriting the last one")
        self.assertContains(branch, "before its own trial",
                            "the next hypothesis is not required to be stated before its trial")

    # S-004: an investigation that will not converge terminates with a verdict.
    def test_s004_reaching_the_bound_returns_architectural_with_the_bound_and_the_count(self):
        stop = section(self.body, "### 6. Stop at the bound")
        self.assertContains(stop, "`verdict: architectural`",
                            "the bound section does not name the verdict it returns")
        self.assertContains(stop, "`bound_reached` names the bound and the count",
                            "the bound and the count are not both required")
        self.assertContains(stop, "Do not start another hypothesis.",
                            "the bound is stated without being binding")
        self.assertContains(
            stop, "shape of the system, rather than any single defect, is",
            "the verdict is returned without the statement that makes it mean something "
            "different from a failed run")
        self.assertRegex(
            section(self.body, "## Inputs"), r"declare it in the record before the\s+first trial",
            "the bound is not required to be declared before the trials, so a bound chosen "
            "afterwards to fit the count would satisfy the scenario")

    # S-005: a request to fix is refused.
    def test_s005_a_request_to_diagnose_and_then_fix_is_refused_in_the_imperative(self):
        step = section(self.body, "### 8. Return the record, and do not repair")
        self.assertContains(
            step, "**A request to diagnose and then fix is answered with the diagnosis alone.**",
            "the skill does not refuse a request that asks it to diagnose and then repair")
        self.assertContains(step, "perform no repair",
                            "the refusal does not say the repair is not performed")
        self.assertContains(step, "leave every tracked file as you found it",
                            "the refusal does not carry the observable half of S-005")
        self.assertContains(
            step, "**Do not apply the fix in a copy either and offer it as a patch.**",
            "the refusal is bound to the tracked files rather than to producing the change, so "
            "the same fix handed over as a patch would satisfy it")

    def test_s005_the_when_not_to_use_section_declines_the_fix_rather_than_deferring_it(self):
        declines = bullet(section(self.body, "## When not to use"), "You want the defect fixed.")
        self.assertContains(declines, "does not fix anything",
                            "the skill does not decline to fix in the section a reader checks "
                            "before invoking it")
        self.assertContains(declines, "`fix-batch`",
                            "the decline does not name what does take the fix, which is what "
                            "makes it a redirection rather than a refusal")

    # S-006: the diagnosis carries what a task file's bar demands.
    def test_s006_the_record_carries_the_three_things_a_task_file_cannot_otherwise_obtain(self):
        step = section(self.body, "### 8. Return the record, and do not repair")
        for field in ("`implicated_files`", "`reproduction`", "`regression_observable`"):
            with self.subTest(field=field):
                self.assertContains(step, field,
                                    "the hand-off to a task file does not name this field")
        self.assertContains(step, "basis for an acceptance command",
                            "the reproduction is handed over without saying what it is for")
        self.assertContains(step, "`new-task`",
                            "the record is not connected to the skill that consumes it")

    # S-007: a report without any way to observe it is answered, not guessed at.
    def test_s007_a_report_with_no_way_to_observe_it_yields_no_cause_from_reading_alone(self):
        branch = bullet(section(self.body, "### 2. Reproduce before you explain"),
                        "There is no way to observe it.")
        self.assertContains(branch, "`verdict: not_reproducible`",
                            "the unobservable branch does not name its verdict")
        self.assertContains(branch, "`missing_input` naming what is\n  absent",
                            "the branch does not require what is absent to be named")
        self.assertContains(
            branch, "**Do not infer a root cause from reading code alone.**",
            "the branch does not forbid the one thing it exists to forbid")
        self.assertContains(
            branch, "more dangerous than an empty answer",
            "the prohibition is stated without the reason, which is the half that survives "
            "being read once")

    # S-008: a failure crossing components is localized before it is explained.
    def test_s008_the_boundary_observation_is_required_before_any_entry_proposing_a_cause(self):
        step = section(self.body, "### 4. Localize before you explain")
        self.assertContains(step, "boundary at which behavior first diverges",
                            "the section does not require the boundary to be found")
        self.assertContains(
            step, "goes in `hypotheses` **before** any entry proposing a cause",
            "the ordering S-008 turns on is absent, so an explanation may be recorded before "
            "the observation that placed it")
        self.assertContains(step, "log what enters and what leaves at each boundary",
                            "the section requires a boundary without saying how to find it")
        self.assertContains(
            step, "first wrong rather than first noticed",
            "backward tracing stops at the symptom, which is where a bad value is noticed "
            "rather than where it was made")

    # S-009: the record of a run is not rewritten by a later one.
    def test_s009_a_later_run_is_persisted_separately_and_the_earlier_record_is_unchanged(self):
        step = section(self.body, "### 8. Return the record, and do not repair")
        self.assertContains(step, "never rewritten by a later run",
                            "nothing stops a later run editing an earlier record")
        self.assertContains(step, "stays exactly as it was",
                            "the earlier record is not required to be left unchanged")
        self.assertContains(step, "persisted as a separate record",
                            "the later run has nowhere to go that is not the earlier record")
        self.assertContains(
            step, "stops being evidence",
            "the rule is stated without the reason, and this is the rule most often broken by "
            "an agent trying to be helpful")

    # S-010: the report itself can be the defect.
    def test_s010_a_report_in_error_names_the_report_and_omits_the_two_code_fields(self):
        step = section(self.body, "### 7. When the report is the thing in error")
        self.assertContains(step, "`verdict: root_cause_found`",
                            "the report-in-error case does not name its verdict")
        self.assertContains(step, "naming **the report** as the thing in error",
                            "the cause is not required to name the report itself")
        self.assertContains(step, "cite the contract you checked it against",
                            "the claim that the report is wrong carries no evidence")
        self.assertRegex(
            step,
            r"`implicated_files` and `regression_observable` are\s+\*\*absent\*\*",
            "the two code-implicating fields are not required to be absent, which is as much "
            "an obligation here as their presence is on S-006")
        self.assertContains(
            step, "send someone to change correct code",
            "the absence is required without the consequence of getting it wrong")

    # S-011: a dispatched agent can tell its own defect from one it uncovered.
    def test_s011_an_isolated_agent_reproduces_against_the_tree_and_the_unmodified_base(self):
        step = section(self.body, "### 2. Reproduce before you explain")
        self.assertContains(step, "run the reproduction twice",
                            "one run cannot distinguish an introduced defect from one found")
        self.assertContains(step, "against your\nworking tree, and against the unmodified base",
                            "the two tree states the scenario names are not both required")
        self.assertContains(step, "State both outcomes in\n`reproduction`",
                            "the pair is run and not recorded, so the record cannot show it")
        self.assertContains(
            step, "want opposite things done about them",
            "the reason the distinction matters is absent, and it is the reason an agent "
            "under time pressure keeps the second run")

    # S-012: an intermittent defect is classified rather than declared fixed.
    def test_s012_an_intermittent_defect_records_a_rate_and_needs_a_reliable_condition(self):
        step = section(self.body, "### 2. Reproduce before you explain")
        self.assertContains(step, "record the **observed rate** in `reproduction`",
                            "an intermittent defect is not required to carry a rate")
        self.assertContains(
            step, "as attempts and successes rather\nthan as an adjective",
            "the rate may be recorded as a word, which is the form that hides whether anyone "
            "counted")
        self.assertContains(
            step, "`root_cause_found` is available only once such a\ncondition is found",
            "the verdict is not gated on a condition that reliably reproduces the behavior")
        self.assertContains(
            step, "**An attempt that happened to pass is not evidence that anything was fixed.**",
            "nothing forbids the one move S-012 exists to forbid")

    # S-013: the record is not written to disk unless asked for.
    def test_s013_no_destination_creates_no_file_and_a_destination_takes_the_same_record(self):
        step = section(self.body, "### 8. Return the record, and do not repair")
        self.assertContains(
            step, "return the record inline and create no file",
            "the no-destination half is missing, so a run may persist a record nobody asked for")
        self.assertContains(step, "write the same record there and nowhere else",
                            "the with-destination half is missing, or does not require the "
                            "same record rather than a different one")
        self.assertContains(
            step, "promised only to read",
            "the rule is stated without the reason it is not merely a preference")
        self.assertEqual(
            {r[0]: r[1] for r in table_rows(section(self.body, "## Inputs"))}["Record destination"],
            "no",
            "the record destination is required, which contradicts the inline default")

    # S-014: instrumentation lives in a copy, never in the tracked files.
    def test_s014_instrumentation_lives_in_a_copy_and_the_bound_is_every_point_in_the_run(self):
        step = section(self.body, "### 3. Work in a copy, and never in the tracked files")
        self.assertContains(
            step, "**Instrumentation goes in a copy this run made for the purpose. Never in the "
                  "tracked files, not even\nbriefly.**",
            "the instruction to work in a copy is absent or is not in the imperative. Note what "
            "this does not decide: a presence assertion cannot see a permission added beside it, "
            "so the exclusion is the separate test below")
        self.assertContains(
            step, "At no point during the run does any tracked source, test, or config file "
                  "differ from its state at the\nstart",
            "the bound is not stated over every point in the run, which is the whole "
            "strengthening S-014 makes over S-005's end-of-run observable")
        self.assertContains(
            step, "whether the run reaches a verdict, is interrupted, or fails partway",
            "the three ways a run can end are not covered, and the interrupted one is the case "
            "instrument-then-clean-up fails on")
        self.assertContains(
            step, "invisible until a run dies",
            "the reason the rejected alternative is worse is absent, so a later reader has "
            "nothing to weigh before relaxing this")

    def test_s014_no_sentence_permits_or_undoes_an_edit_to_the_tracked_files(self):
        """The exclusion the presence assertions above cannot make, from an independent
        verification of `feat-0061`.

        Every other assertion in this file checks that something is present, and a presence
        check cannot see an **addition that contradicts it**. An escape hatch is an addition:
        appending "where making a copy is awkward it is acceptable to instrument the tracked
        files directly and restore them before the run ends" leaves every sentence this file
        asserts on intact, and reproduces exactly the alternative `chore-0078` rejected.

        **Asserted per sentence rather than per word, deliberately.** This section legitimately
        uses "cleaning up afterwards" in the sentence that rejects it, so a bare-word exclusion
        would be broken by the very prose explaining the rule. That is not hypothetical here:
        this kit has three recorded occasions where an assertion matching a bare word in source
        text was satisfied by a comment, broken by a comment, and once satisfied by the comment
        explaining the very fix. The form is the pairing, a permission or an undo in the same
        sentence as the tracked files, which the rejecting prose never produces.
        """
        step = section(self.body, "### 3. Work in a copy, and never in the tracked files")
        permission = re.compile(
            r"(?i)\b(acceptable|permitted|permissible|allowed|allowable|fine|okay|may|can)\b")
        undo = re.compile(r"(?i)\b(restore|restores|restoring|revert|reverts|reverting|undo|"
                          r"undoes|undoing|put back|puts back)\b")
        for sentence in re.split(r"(?<=[.!?])\s+", flat(step)):
            if not re.search(r"(?i)tracked (source|file)", sentence):
                continue
            with self.subTest(sentence=sentence[:60]):
                self.assertNotRegex(
                    sentence, permission,
                    "a sentence permits something about the tracked files, and the only "
                    "permitted thing is leaving them alone")
                self.assertNotRegex(
                    sentence, undo,
                    "a sentence offers to undo an edit to the tracked files, which is the "
                    "instrument-in-place alternative S-014 exists to reject")

    def test_s014_names_no_tool_as_required_so_a_non_git_target_is_not_excluded(self):
        """The contract states the property and deliberately names no mechanism. A skill that
        named one would be false of exactly the targets S-015 is about."""
        step = section(self.body, "### 3. Work in a copy, and never in the tracked files")
        self.assertContains(step, "Nothing here requires a particular tool",
                            "the skill does not say the mechanism is open")
        for tool in ("git worktree", "git clone", "git stash"):
            with self.subTest(tool=tool):
                self.assertNotIn(tool, step,
                                 f"the skill names {tool} where the contract deliberately "
                                 f"names no mechanism")

    # S-015: a repository that cannot be copied is answered, not refused.
    def test_s015_a_target_that_cannot_be_copied_still_reaches_a_verdict_read_only(self):
        step = section(self.body, "### 3. Work in a copy, and never in the tracked files")
        self.assertContains(step, "**Where no working copy can be made at all**",
                            "the no-copy case is not answered, so a reader has to guess "
                            "between instrumenting in place and refusing to run")
        self.assertContains(step, "add no instrumentation, and continue read-only",
                            "the no-copy path does not forbid instrumentation, which is the "
                            "half that would otherwise leak back into the tracked files")
        self.assertContains(
            step, "Record in `reproduction` that the observation was made without instrumentation",
            "the weakened instrument is not recorded, so a reader cannot tell this diagnosis "
            "from one made with full instrumentation")
        self.assertContains(step, "**The run still reaches a verdict**",
                            "the no-copy path may end without a verdict, which turns a "
                            "portability limit into an ambiguous run")


class TestTheContractsConstraints(SkillTestCase):
    """Two obligations the scenario tests leave uncovered, both found by an independent
    verification of `feat-0061` after every scenario test was already green.

    Neither is a scenario, so neither was reached by a `test_sNNN_` method, and both turned
    out to be silently deletable: the whole paragraph could be removed and all thirty-one
    tests still passed. A contract Constraint is as binding as a scenario and has no `S-NNN`
    to hang a test on, which is exactly how it gets missed.
    """

    def test_the_one_variable_per_trial_rule_is_present_with_its_reason(self):
        """The contract's Constraint "One hypothesis at a time", whose stated reason is that a
        trial varying more than one thing "cannot attribute its own result, so it produces no
        evidence regardless of outcome"."""
        step = section(self.body, "### 5. One hypothesis at a time")
        self.assertContains(step, "**Vary one thing.**",
                            "the one-variable rule is absent, so a trial that changes three "
                            "things at once is not excluded by anything a model reads")
        self.assertContains(
            step, "cannot attribute its own outcome",
            "the rule is stated without the reason, which is what distinguishes it from a "
            "preference about tidiness")

    def test_the_symptom_is_restated_as_an_observable_before_anything_is_run(self):
        """The `symptom` field's content is "restated as an observable", and the record table
        alone does not say when or how that happens. Procedure step 1 does, and nothing
        asserted it existed: renaming the heading left every other test green."""
        step = section(self.body, "### 1. Restate the symptom as an observable")
        self.assertContains(
            step, "something that can be observed",
            "step 1 does not require the report to be turned into an observation")
        self.assertContains(
            step, "Read the error text completely",
            "the cheapest evidence available is not asked for, and it is the one most often "
            "skipped")


class TestWhatTheDogfoodAdded(SkillTestCase):
    """Three instructions `feat-0062` added after running the skill on a real defect.

    Each closes a place where the procedure, as written, cost the run something measurable.
    They are asserted rather than left in prose for the reason the verification of `feat-0061`
    established: an unasserted paragraph in this body is silently deletable, and the three
    survivors it found were all paragraphs nothing was scoped to.
    """

    def test_an_unfired_reproduction_is_checked_for_an_uncontrolled_variable_first(self):
        """The dogfood's first two reproduction attempts failed, and not because the defect is
        intermittent: the writer simply did not hold the store for long enough. The contract
        asks for a rate, and what the run needed was a knob."""
        step = section(self.body, "### 2. Reproduce before you explain")
        self.assertContains(
            step, "check whether you are the one varying it",
            "nothing tells a reader to look for an uncontrolled variable before calling a "
            "defect intermittent, which is the reading that turns a harness problem into a "
            "property of the system")
        self.assertContains(
            step, "the fix is a knob rather\nthan a rate",
            "the remedy is not named, so a reader who suspects a variable is still told only "
            "to count attempts")
        self.assertContains(
            step, "Record what you pinned and to what",
            "a pinned variable is not recorded, so a later reader cannot tell a deterministic "
            "reproduction from a lucky one")

    def test_a_measurement_is_checked_against_a_second_source_before_it_becomes_a_hypothesis(self):
        """The dogfood formed a hypothesis from its own harness's timings, which turned out to
        be an artifact, and spent a trial disproving it. The trial was correctly recorded, and
        nothing in the procedure would have avoided it."""
        step = section(self.body, "### 1. Restate the symptom as an observable")
        self.assertContains(
            step, "is a claim about your harness until something else agrees with it",
            "nothing warns that a figure from the reader's own instrument is not yet evidence")
        self.assertContains(
            step, "check it against a second source",
            "the warning is given without the remedy, so a reader who agrees with it does not "
            "know what to do next")

    def test_a_sufficient_condition_is_not_accepted_as_the_cause_without_a_second_look(self):
        """The correction the dogfood earned the hard way. Its own `root_cause_found` was
        refuted by an independent check: the trial that "confirmed" it, raising a timeout,
        would have flipped the outcome whatever the blocking statement was, and a different
        single change fixed the same symptom at baseline latency. The skill's confirming
        observation, as written, did not require the counterfactual to discriminate."""
        step = section(self.body, "### 5. One hypothesis at a time")
        self.assertContains(
            step, "merely consistent with your hypothesis has confirmed nothing",
            "nothing distinguishes a trial that confirms from one that is only compatible, "
            "which is how a sufficient condition gets recorded as a cause")
        self.assertContains(
            step, "a sufficient condition is not the cause until you have looked for a second "
                  "change that also makes it go away",
            "the reader is not told to look for a second sufficient change, which is the only "
            "move that separates a cause from its neighbourhood")
        self.assertContains(
            step, "a counterfactual that would hold whatever the answer turned out to be",
            "the tell is not named, so a reader who agrees with the rule still cannot spot "
            "the trial it applies to")

    def test_the_probe_must_cover_the_whole_suspect_region(self):
        """Also from the refutation: the dogfood's boundary probe instrumented three
        statements of a five-statement function, reported both as returning in 0.000s, and
        concluded the function was innocent. The block was at the fifth."""
        step = section(self.body, "### 4. Localize before you explain")
        self.assertContains(
            step, "not the part you already suspect",
            "the reader is not told to instrument beyond their own theory, so a probe returns "
            "a clean result for everything it was not pointed at")
        self.assertContains(
            step, "The gap in the instrumentation is where the answer will be",
            "the consequence is not stated, and it is what makes the rule worth the extra "
            "probes rather than a counsel of perfection")

    def test_the_copy_boundary_is_given_a_rule_rather_than_left_to_judgment(self):
        """Step 3 required a copy and said nothing about what to put in it. For a component
        rather than a file that is a real decision, and getting it wrong debugs the copy."""
        step = section(self.body, "### 3. Work in a copy, and never in the tracked files")
        self.assertContains(
            step, "Copy enough that the thing still runs, and no more.",
            "the copy's boundary is left entirely to judgment")
        self.assertContains(
            step, "its imports, its package layout, and its data files",
            "the rule names no criterion, so it restates the problem rather than answering it")


class TestTheSkillIsADraftAndNoProfilePlacesIt(SkillTestCase):
    """The consequential risk `feat-0061` names. A skill that is not excluded is placed into
    user-scope discovery and starts triggering in unrelated sessions before it has been used
    once. Proven against the real installer rather than by reading the frontmatter."""

    def test_the_draft_marker_is_in_the_block_form_the_installer_parses(self):
        self.assertRegex(self.body, r"(?m)^metadata:\n\s+status\s*:\s*draft\s*$",
                         "the draft marker is absent or not in the block form install.py "
                         "parses, so the skill would ship")

    def test_no_profile_places_it_including_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "install-home"
            # Captured rather than left to print: a dry run over every skill times two tools
            # buries the suite's own output, and the summary is what this asserts on anyway.
            stdout, sys.stdout = sys.stdout, io.StringIO()
            try:
                placed = install.main(["--dry-run", "--profile", "all", "--home", str(home)])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout.close()
                sys.stdout = stdout

        self.assertEqual(placed, 0)
        self.assertIn("systematic-debugging", [d.name for d in install.discover_skills()],
                      "the skill is not discoverable at all, so its exclusion proves nothing")
        self.assertRegex(
            output, r"excluded from every profile, including 'all':[^\n]*systematic-debugging",
            "the installer did not exclude the draft skill")
        self.assertNotIn("copied    claude   systematic-debugging", output,
                         "the draft skill was placed into a discovery location")

    def test_the_draft_is_absent_from_the_shipped_set_the_budget_is_measured_over(self):
        """`feat-0060` recorded that the description budget is printed over the shipped set
        rather than the discovered set. A draft must therefore contribute nothing to it."""
        shipped, drafts = install.partition_drafts(install.discover_skills())
        self.assertIn("systematic-debugging", {d.name for d in drafts})
        self.assertNotIn("systematic-debugging", {d.name for d in shipped},
                         "the draft is in the shipped set, so it is inside every profile's "
                         "description budget and in front of adopters")


class TestTheFoldInIsAttributed(SkillTestCase):
    """The skill is adapted from an external source, so `AGENTS.md` requires a provenance
    block. Parsed with the checker's own parser rather than by matching text, so a block that
    this suite accepts and `check-provenance.py` cannot read is not possible."""

    def parser(self):
        path = REPO_ROOT / "scripts" / "check-provenance.py"
        spec = importlib.util.spec_from_file_location("check_provenance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_the_provenance_block_carries_every_required_field(self):
        cp = self.parser()
        records = cp.parse_records(self.body)
        self.assertEqual(len(records), 1, "the skill carries no provenance block, or more "
                                          "than one where it draws on one upstream file")
        record = records[0]
        for key in cp.REQUIRED_KEYS:
            with self.subTest(key=key):
                self.assertTrue(record.get(key), f"the provenance block has no {key}")
        self.assertTrue(record["source"].startswith("https://raw.githubusercontent.com/"),
                        "the source is not a re-fetchable raw URL, so nothing can drift-check it")
        self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$",
                         "the digest is not a sha256 of anything")

    def test_the_departures_from_upstream_are_stated_rather_than_left_to_a_reader(self):
        """A digest answers whether upstream changed. It does not say what was deliberately
        not folded in, and this skill drops upstream's entire fourth phase."""
        prov = section(self.body, "## Provenance")
        self.assertContains(prov, "ends at the diagnosis and refuses to",
                            "the provenance note does not record that upstream implements the "
                            "fix and this skill does not")
        self.assertContains(prov, "deterministic verdict",
                            "the provenance note does not record the gate-versus-verdict "
                            "departure the roadmap decided")


class TestTheHouseConventions(SkillTestCase):
    """Rules `validate-skills.py` does not decide, and that a shipped skill has broken before."""

    def test_the_house_style_module_is_named_so_an_adopter_who_swaps_it_is_obeyed(self):
        self.assertContains(section(self.body, "## Conventions"),
                            ".agents/rules/house-style.md",
                            "the skill does not point at the swappable house-style module")

    def test_the_body_carries_no_em_dash(self):
        self.assertNotIn("—", self.body,
                         "the house style forbids em-dashes and this body carries one")

    def test_the_body_links_to_nothing_outside_the_skill_tree(self):
        """`validate-skills.py` enforces this, and it is asserted here too because the contract
        this skill implements lives in `docs/spec/`, which is exactly the tempting link."""
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", self.body):
            with self.subTest(target=target):
                self.assertFalse(target.startswith("../../"),
                                 "a link escapes the skill tree, so it resolves in this "
                                 "repository and dangles everywhere the skill actually runs")


if __name__ == "__main__":
    unittest.main()
