---
title: test-author conformance
spec: docs/spec/test-author.md
audited: 2026-08-05
---

# test-author conformance matrix

Spec-vs-implementation audit of [`test-author`](../../.agents/skills/test-author/SKILL.md) against
[`test-author.md`](test-author.md). Produced by `chore-0025`. `test-author` shipped as `feat-0018`
on 2026-07-24, drafted against a spec that `spec-author` had itself produced, and had never been
audited against it.

## What this audit can and cannot establish

`test-author` is a prose skill, so the evidence column cites a clause rather than a code path, and
this establishes that the skill **instructs** the specified behavior rather than that anything
enforces it. Same limit as [`verifier-agent.conformance.md`](verifier-agent.conformance.md).

There is one piece of stronger evidence available here than for the other prose skills, and it is
used where it applies: `test-author`'s own dogfood produced
[`tests/test_validate_skills.py`](../../tests/test_validate_skills.py), a real artifact that either
does or does not carry the scenario tagging and coverage honesty this contract requires. Where a row
cites that file, the evidence is an observed output rather than an instruction.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 derive acceptance tests from an approved spec | Conformed | Procedure step 3 / "tag each with the scenario id it covers", and step 5 / "scenarios in the spec, tests written, scenarios covered, and scenarios omitted each with a stated reason" | all three obligations are present: one test per scenario, the id tag, and the coverage report with reasons. Corroborated by output: `tests/test_validate_skills.py` tags each test with its scenario id and its docstring states the S-008 omission with a reason |
| Scenarios | S-002 choose layer and oracle via test-quality | Conformed | Procedure step 3 / "name the plausible defect, pick the **lowest faithful layer** that still reproduces the risk", composing [`test-quality`](../../.agents/skills/test-quality/SKILL.md) | the "records the layer and oracle it chose" half is satisfied by step 3's instruction to state them; corroborated by the `test-quality notes` paragraph in the dogfooded test file, which names both |
| Scenarios | S-003 characterization tests for uncovered legacy code | Conformed | "Modes" / "assert the current observable behavior to pin it before a change, and label the tests as characterization in the name or an adjacent comment", with step 1's "In characterization mode there is no spec to gate" | both halves present: assert current behavior, and label it. The labelling instruction offers two placements (name or adjacent comment) where the scenario says only "labels them"; that is a permitted narrowing to something checkable, not a divergence |
| Scenarios | S-004 bug-fix regression proven to fail first | Conformed | Procedure step 4 / "before trusting a regression test, confirm it fails against the pre-fix behavior" | the scenario's second half ("reproduces the reported symptom") is the weaker half of the clause and is implied rather than stated as a separate check. Noted, not scored as a divergence, because a test that fails against pre-fix behavior for a different reason would not satisfy the stated instruction either |
| Scenarios | S-005 no faithful test possible | Conformed | Procedure step 5 / "do not write a low-value passing test in its place: report the gap and classify it as smoke, diagnostic, or deferred" | the three classifications match the contract's enum exactly, and the prohibition is explicit rather than implied. This is the scenario most likely to be quietly skipped in practice, so the explicit "do not" earns its place |
| Proposed Surface | Inputs: approved spec path, implementation scope, task acceptance criteria | Conformed | "Inputs" section, split into required-for-acceptance and required-for-characterization | the split is a refinement the contract does not describe but does not forbid; it is what makes the two modes usable |
| Proposed Surface | Mode: `acceptance` or `characterization`, inferred with user override | Conformed | "Modes" / "Infer the mode from the inputs, and let the user override it" | the override clause is stated, which is the half most easily lost |
| Proposed Surface | Output: test files in the repository's own framework, tagged with the covering scenario id | Conformed | Procedure step 2 (discover and match the repository's test infrastructure) and step 3 (tag with the scenario id) | "the repository's own framework" is satisfied by step 2's discovery rather than by naming a framework, which is what the portability contract in section 5 of `AGENTS.md` requires |
| Proposed Surface | Coverage report: scenarios covered, and omissions each with a stated reason | Conformed | Procedure step 5 | corroborated by output: the dogfooded suite omits S-008 and states why, rather than writing a passing test for behavior that does not exist |
| Goals | Derive focused acceptance tests from a spec and task criteria | Conformed | steps 1, 3, and 5 | covered by S-001 |
| Goals | Retain characterization support for legacy code | Conformed | "Modes", step 1's skip, step 4's labelling | covered by S-003 |
| Goals | Compose `test-quality` for layer and oracle choice | Conformed | step 3, and the skill's stated composition of the lens | covered by S-002 |
| Constraints | Never edits production code | Conformed | Procedure step 4 heading / "Write the tests, and never touch production code" | stated in a step heading, which is the strongest placement available in a prose skill |
| Constraints | Gates the spec with `spec-quality` before deriving | Conformed | Procedure step 1 / "Read the spec and gate it with spec-quality" | |
| Non-Goals | Does not run the batch or judge quality | Conformed | "When not to use" | |
| Open Questions | None | Conformed | spec states `None.` | nothing to reconcile |

## Coverage proof

**Audited** (16 items): scenarios S-001 through S-005; the four Proposed Surface rows (inputs, mode,
output, coverage report); the three Goals; the two Constraints; the Non-Goals; and the Open
Questions section.

**Unreconciled**: none.

**Not-built**: none. Every scenario and every surface element has evidence.

## Two notes that are not divergences

Recorded because a later reader will re-derive them otherwise, and because a matrix with nothing but
`Conformed` rows deserves to say where it looked hardest.

**S-004's second half is the weakest evidence in this matrix.** The contract asks for two things:
that the test fails against pre-fix behavior, and that it reproduces the reported symptom. The skill
states the first explicitly and leaves the second implicit. A test can fail against pre-fix behavior
for an unrelated reason and still satisfy a literal reading of the instruction. It is scored
`Conformed` because the instruction as written would not be met by such a test either, but if this
contract is ever tightened, that is the clause to tighten.

**The strongest evidence here is an artifact, not a clause.** `test-author`'s dogfood produced a
suite that omitted a scenario and said why, rather than manufacturing a passing test for an accepted
divergence. That is the behavior S-001 and S-005 exist to require, observed rather than instructed.
No other prose skill in this repository has that kind of corroboration available, which is worth
remembering when the other matrices read as thinner.
