---
title: systematic-debugging conformance
spec: docs/spec/systematic-debugging.md
audited: 2026-08-29
---

# systematic-debugging conformance matrix

Spec-vs-implementation audit of
[`systematic-debugging`](../../.agents/skills/systematic-debugging/SKILL.md) against
[`systematic-debugging.md`](systematic-debugging.md). Produced at `feat-0061`'s closeout, which is
the closeout [`README.md`](README.md) recorded this matrix as owed at.

The contract carries **fifteen** scenarios rather than the thirteen it was approved with:
`chore-0078` settled both of its Open Questions on 2026-08-29 and added `S-014` and `S-015`. That
amendment is pending the author's re-approval, so the two rows below audit clauses a human has not
yet re-read.

## What this audit can and cannot establish

`systematic-debugging` is a prose skill, so both sides of this audit are natural language and the
evidence column cites a clause rather than a code path. **That establishes the skill instructs the
specified behavior, not that anything enforces it.** Same limit as
[`test-author.conformance.md`](test-author.conformance.md) and
[`verifier-agent.conformance.md`](verifier-agent.conformance.md), and it is the limit
[`README.md`](README.md) states for every matrix over a skill.

Two pieces of evidence stronger than a clause are available here, and both are used where they
apply.

**The structural suite.** [`tests/test_systematic_debugging.py`](../../tests/test_systematic_debugging.py)
carries one test per scenario, and several of them decide something a reading cannot: the verdict
vocabulary is compared as an exact set over the skill's `## Verdicts` table **and** over every
`verdict: X` span in its body, so a fourth verdict fails wherever it is introduced and a missing one
fails; every record field is compared against the presence condition this contract gives for it; and
the draft exclusion is proven by running the real installer rather than by reading the frontmatter.
Where a row cites a test, the evidence is a decided property rather than a clause.

**The body-wide half of that claim was added after an independent verification demolished the
narrower one.** The first version compared the table alone, which is a much smaller claim than it
reads as: a fourth verdict instructed in Procedure step 6 left the table untouched, and the Procedure
is what an agent follows. The sentence above stated the stronger property while the suite decided the
weaker one, which is the shape `AGENTS.md` names in its conventions section, a check that cannot fail
being reported as coverage.

**Twenty-five mutations, all killed, and ten of them only after the suite was strengthened.** Run in
one pass on 2026-08-29 so the count is measured rather than added up: fifteen, then five, then five.
The suite
was run against fifteen deliberate defects in the skill, one at a time, each a way the contract could
be broken: a fourth verdict invented in the table, a presence condition widened to `always`,
`S-014`'s bound weakened back to the end of the run, the no-copy path deleted, a tool named as
required, the boundary ordering dropped, the inline default inverted. All fifteen failed the suite.

**Those fifteen shared a shape, and an independent verification found it.** Every one was a deletion
or a replacement of asserted text, and a presence assertion cannot see an **addition that contradicts
it**. Five further mutations, designed by the verifier rather than the author, all survived: an
escape hatch permitting in-place instrumentation with a restore before exit, a fourth verdict
instructed in Procedure step 6, a record cell rewritten to admit "a new one where none of them fits",
the one-variable-per-trial Constraint deleted outright, and Procedure step 1 removed entirely. Four
new assertions close them, including a per-sentence exclusion rather than a per-word one, because
this section legitimately uses "cleaning up afterwards" in the sentence that rejects it and a
bare-word check would have been broken by the prose explaining the rule.

**Then `feat-0062` added five instructions and five more mutations.** Each correction the dogfood
produced was, on arrival, a paragraph nothing was scoped to and therefore silently deletable, which
is the same class a third time. All five now have assertions and all five fail when the instruction
is cut. All twenty-five fail the suite. A structural test that cannot fail is unchecked whatever it
printed, and the survivors are why that sentence is worth more than the kills that preceded them.

**What neither buys.** Nothing here observes an agent following the procedure. `feat-0062` is the
task that did, and its result belongs in this matrix rather than only in a task file.

**The dogfood, 2026-08-29, and it refuted its own output.** The skill was run on a real defect, the
`database is locked` failure in `scripts/observatory/serve.py`. It reached `root_cause_found`, and an
independent check then refuted the cause: the trial the run called confirming was raising a SQLite
busy timeout, which ends any wait whatever is waiting, so it was consistent with the hypothesis and
did not test it. Two further single-variable cells, which nobody had run, showed a different change
fixing the same symptom at baseline latency and showed the record's stated mechanism was not involved
at all.

**That result cuts two ways and both belong here.** The procedure did change the answer: reading the
code produced a wrong cause, and the boundary probe killed it in one run. And the procedure then let
a second wrong cause through, under a counterfactual that could not have failed. Five corrections
went into the skill as a result, three from the run and two from the refutation, and each is asserted
in the suite. `feat-0063` is the second run, by a session that did not write the skill, on a defect
it did not choose, and the skill stays a draft until then.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 a reproducible defect yields a named cause | Conformed | Procedure step 5 / "The result confirms it." branch, which returns `root_cause_found` and requires `confirming_observation` to state "what was observed that would have differed had the hypothesis been wrong"; `test_s001_a_confirmed_hypothesis_returns_a_cause_with_a_disconfirming_observation` | **the row the dogfood put pressure on.** The contract's wording was satisfiable by a trial that could not have failed, and `feat-0062`'s own run did exactly that. The scenario is not wrong and the skill now says the missing half outright: "a sufficient condition is not the cause until you have looked for a second change that also makes it go away". Whether the contract should say it too is a live question and not a divergence today |
| Scenarios | S-002 a defect that will not reproduce is a verdict, not a failure | Conformed | Procedure step 2 / "It does not reproduce." branch, carrying `not_reproducible`, `missing_input`, and "no `root_cause` is offered"; `test_s002_a_defect_that_will_not_reproduce_returns_a_verdict_and_no_cause` | all three obligations present, including the prohibition, which is the half most easily lost. "This is a result." carries the scenario's title claim into the body a model reads |
| Scenarios | S-003 a disproved hypothesis is recorded, not discarded | Conformed | Procedure step 5 / "The result contradicts the hypothesis." branch, which "retains the hypothesis, its trial" and the "disconfirming result", with the next hypothesis a "separate entry" stated "before its own trial"; `test_s003_a_disproved_hypothesis_is_retained_and_the_next_is_a_separate_entry` | the ordering clause is the one with teeth and it is stated rather than implied |
| Scenarios | S-004 an investigation that will not converge terminates with a verdict | Conformed | Procedure step 6 / "Do not start another hypothesis.", with "`bound_reached` names the bound and the count" and the statement that "shape of the system, rather than any single defect, is" the subject; `test_s004_reaching_the_bound_returns_architectural_with_the_bound_and_the_count` | the bound's declaration is placed in Inputs rather than in step 6, and requires it "before the first trial", which the contract does not say and which is what stops a bound being chosen afterwards to fit the count |
| Scenarios | S-005 a request to fix is refused | Conformed | Procedure step 8 / "A request to diagnose and then fix is answered with the diagnosis alone." plus "perform no repair" and "leave every tracked file as you found it"; the "When not to use" bullet "You want the defect fixed."; `test_s005_a_request_to_diagnose_and_then_fix_is_refused_in_the_imperative` | the skill closes a loophole the scenario's observable leaves open. "Do not apply the fix in a copy either and offer it as a patch." binds the refusal to producing the change rather than to where it lands, which a no-tracked-file-differs test cannot see |
| Scenarios | S-006 the diagnosis carries what a task file's bar demands | Conformed | Procedure step 8, naming `implicated_files`, the "basis for an acceptance command", and `regression_observable`, and connecting them to `new-task`; `test_s006_the_record_carries_the_three_things_a_task_file_cannot_otherwise_obtain` | all three fields carry their purpose rather than only their names, which is what makes the hand-off legible to whoever writes the task |
| Scenarios | S-007 a report without any way to observe it is answered, not guessed at | Conformed | Procedure step 2 / "There is no way to observe it." branch, carrying `not_reproducible`, `missing_input`, and "Do not infer a root cause from reading code alone."; `test_s007_a_report_with_no_way_to_observe_it_yields_no_cause_from_reading_alone` | the prohibition is in the imperative and carries its reason, "more dangerous than an empty answer", which is the half that survives being read once |
| Scenarios | S-008 a failure crossing components is localized before it is explained | Conformed | Procedure step 4, requiring the "boundary at which behavior first diverges" and that the observation "goes in `hypotheses` **before** any entry proposing a cause"; `test_s008_the_boundary_observation_is_required_before_any_entry_proposing_a_cause` | the ordering is the scenario's whole content and it is stated as an ordering rather than as two separate requirements. Folded in from upstream, adapted to end at the record rather than at a fix |
| Scenarios | S-009 the record of a run is not rewritten by a later one | Conformed | Procedure step 8 / "A persisted record is never rewritten by a later run.", with "stays exactly as it was" and the later run "persisted as a separate record"; `test_s009_a_later_run_is_persisted_separately_and_the_earlier_record_is_unchanged` | both halves present, and the reason, "stops being evidence", is carried. This is the rule an agent trying to be helpful breaks first |
| Scenarios | S-010 the report itself can be the defect | Conformed | Procedure step 7, returning `root_cause_found` "naming **the report** as the thing in error", citing "the contract you checked it against", with `implicated_files` and `regression_observable` "absent"; `test_s010_a_report_in_error_names_the_report_and_omits_the_two_code_fields` | the absence is asserted as its own obligation in the suite, not inferred from the presence conditions elsewhere. The contract requires an omission here and a presence on S-006, and only a test that checks both can tell them apart |
| Scenarios | S-011 a dispatched agent can tell its own defect from one it uncovered | Conformed | Procedure step 2 / "run the reproduction twice", against the working tree "and against the unmodified base", with both outcomes stated in `reproduction`; `test_s011_an_isolated_agent_reproduces_against_the_tree_and_the_unmodified_base` | the skill states why the distinction matters, that the two "want opposite things done about them", which is what keeps the second run from being dropped under time pressure |
| Scenarios | S-012 an intermittent defect is classified rather than declared fixed | Conformed | Procedure step 2 / "record the **observed rate** in `reproduction`", "as attempts and successes rather than as an adjective", gating the verdict with "`root_cause_found` is available only once such a condition is found"; `test_s012_an_intermittent_defect_records_a_rate_and_needs_a_reliable_condition` | the "as attempts and successes" clause is a narrowing the contract does not require, and it is what makes the rate a figure rather than a word |
| Scenarios | S-013 the record is not written to disk unless asked for | Conformed | Procedure step 8 / "return the record inline and create no file" and "write the same record there and nowhere else"; the Inputs row for the record destination; `test_s013_no_destination_creates_no_file_and_a_destination_takes_the_same_record` | the checkable pair is stated as a pair. The suite asserts both halves plus the Inputs row, so making the destination required would fail even with the prose intact |
| Scenarios | S-014 instrumentation lives in a copy, never in the tracked files | Conformed | Procedure step 3 / "Instrumentation goes in a copy this run made for the purpose." and "At no point during the run does any tracked source, test, or config file differ from its state at the start", covering a run that "reaches a verdict, is interrupted, or fails partway"; `test_s014_instrumentation_lives_in_a_copy_and_the_bound_is_every_point_in_the_run` | added by `chore-0078` and pending re-approval. The suite pins the every-point bound specifically, because the end-of-run phrasing is satisfied by the alternative this scenario exists to reject |
| Scenarios | S-015 a repository that cannot be copied is answered, not refused | Conformed | Procedure step 3 / "Where no working copy can be made at all", which adds "no instrumentation, and continue read-only", records the weakened instrument in `reproduction`, and states "The run still reaches a verdict"; `test_s015_a_target_that_cannot_be_copied_still_reaches_a_verdict_read_only` | added by `chore-0078` and pending re-approval. `test_s014_names_no_tool_as_required_so_a_non_git_target_is_not_excluded` guards the other side of it, failing if the skill names a mechanism the contract deliberately left open |
| Proposed Surface | Verdicts: exactly one per run, three values | Conformed | the `## Verdicts` table, plus "Exactly one per run" and "There is no fourth"; `test_the_verdicts_are_exactly_the_three_the_contract_names` | decided as an exact set rather than by presence. A skill that kept all three and added a fourth fails, which a presence check would not catch |
| Proposed Surface | Diagnosis record: ten fields, each with its presence condition | Conformed | the `## The diagnosis record` table; `test_every_record_field_carries_its_presence_condition` | every condition compared against the contract's own words. The skill adds that an unmet field "is **omitted**, not filled with a placeholder", which the contract implies and does not say |
| Proposed Surface | Inputs: defect report, reproduction steps, investigation bound, record destination | Conformed | the `## Inputs` table; `test_the_four_inputs_appear_with_their_required_flags` | required flags compared as well as names, so a skill that made the bound mandatory would fail |
| Goals | 1. A named root cause with the evidence that established it | Conformed | the opening line, "named cause with the evidence that established it", and step 5's confirm branch | covered by S-001 |
| Goals | 2. A deterministic verdict, so an unattended run cannot end ambiguously | Conformed | `## Verdicts` / "a run that ends without one of these has not ended" | covered by S-002, S-004, and the exact-set test |
| Goals | 3. A diagnosis that feeds `new-task` directly | Conformed | Procedure step 8, "the reason this skill sits upstream of `new-task` rather than beside it" | covered by S-006 |
| Goals | 4. Refuse to repair | Conformed | Procedure step 8 and the "When not to use" bullet | covered by S-005 |
| Goals | 5. Bound the investigation | Conformed | Inputs / "The default bound is five disproved hypotheses" and Procedure step 6 | covered by S-004. The number is the skill's, per Open Question 2 |
| Constraints | Read-only with respect to tracked files | Conformed | Procedure step 3's every-point bound and step 8's "leave every tracked file as you found it" | covered by S-005 and S-014. The contract's own bullet now points at those two rather than restating the rule |
| Constraints | One hypothesis at a time | Conformed | Procedure step 5 / "Vary one thing." with the reason a multi-variable trial "cannot attribute its own outcome" | stated as a heading and an imperative, which is the strongest placement available in a prose skill |
| Constraints | The record is returned inline unless a destination is supplied | Conformed | Procedure step 8 | covered by S-013 |
| Constraints | Harness-portable | Conformed | Procedure step 3 / "Nothing here requires a particular tool", and a procedure stated in observations and commands rather than in named tooling | asserted rather than only claimed: `test_s014_names_no_tool_as_required_so_a_non_git_target_is_not_excluded` fails if a mechanism is named |
| Constraints | This contract owns the kit's classification vocabulary | Conformed | Notes / "This skill's three verdicts are the classification vocabulary." | `feat-0042` consumes this and stays open; its dependency was retargeted here |
| Non-Goals | Fixing, writing the test, writing the task file, judging quality, confirming a fix, diagnosing the agent's own reasoning, deciding whether it is worth fixing | Conformed | the `## When not to use` section, one bullet per Non-Goal, each naming what does take the job | the last two were added during this audit. The skill covered five of seven and a reader would not have known the other two were excluded |
| Open Questions | 1. Where instrumentation may live | Conformed | settled in the contract by `chore-0078`; implemented at Procedure step 3 | recorded as settled in the contract rather than left to this implementation, which was the point of doing `chore-0078` first |
| Open Questions | 2. The default investigation bound | Conformed | left out of the contract by `chore-0078`; set to five in the skill's Inputs section | the contract's own recommendation, adopted. The number is a tuning value and retuning it is not an amendment |

## Coverage proof

**Scenarios**: 15 conformed + 0 diverged + 0 not-built = 15, which is every scenario in the
contract as amended by `chore-0078`. Counted from the file: `grep -c "^### Scenario"
docs/spec/systematic-debugging.md` returns 15, and the rows above carry `S-001` through `S-015` with
no gap and no repeat.

**Audited** (31 items): the fifteen scenarios; the three Proposed Surface elements (verdicts,
diagnosis record, inputs); the five Goals; the five Constraints; the Non-Goals as one row covering
all seven; and both Open Questions.

**Unreconciled**: none.

**Not-built**: none, in the sense this matrix can decide. Every scenario has an instruction in the
skill and a test naming it. See the limit above for what that does not mean.

## Where this audit looked hardest, and what it found

A matrix with nothing but `Conformed` rows deserves to say where it pushed, so here are the three
places it did.

**The Non-Goals row is the only thing this audit changed.** The skill covered five of the contract's
seven Non-Goals in its `## When not to use` section and was silent on two: that it does not diagnose
the agent's own reasoning failures, and that it does not decide whether a defect is worth fixing.
Silence there is not neutral, because `When not to use` is the section a reader checks before
invoking a skill, and a scope limit that appears only in the contract reaches nobody who is deciding
whether to run it. Both bullets were added and the row is `Conformed` because of that edit rather
than in spite of it.

**S-005's observable has a loophole and the skill closes it.** "No tracked file differs from its
state at the start of the run" is satisfied by a run that writes the fix into a copy and hands the
diff over as a patch. That is repair, and no test over the tracked files could see it. The skill says
so in as many words; the contract does not, and it does not need to, because the Goal above the
scenario is "refuse to repair" and the scenario is one observable of it.

**The two scenarios that could most easily have been written as intentions are `S-009` and `S-013`,
and neither is.** Both are about the record's persistence, where "the record is not rewritten" reads
identically whether or not anything makes it true. Each is stated as a pair of concrete behaviors, no
destination against a destination, and earlier record against later record, which is what the suite
is able to assert on.

## What would change this matrix

The obvious one: a run. `feat-0062` uses the skill on a real defect, and its findings are the first
evidence that the procedure does anything, as opposed to instructing something. If that run shows a
step that cannot be followed, the affected row here becomes `Diverged` and the contract or the skill
moves. A matrix re-derived after that run is worth more than this one, and this one says so rather
than waiting to be corrected.
