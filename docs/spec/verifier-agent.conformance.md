---
title: verifier-agent conformance
spec: docs/spec/verifier-agent.md
audited: 2026-07-27
---

# verifier-agent conformance matrix

Spec-vs-implementation audit of [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md)
against [`verifier-agent.md`](verifier-agent.md). Produced by `chore-0014`, after the `feat-0024` run
found that the kit's most safety-critical skill had an approved contract since 2026-07-24 and had
never once been audited against it.

## What this audit can and cannot establish

`verifier-agent` is a prose skill, not a program, so both sides of this audit are natural language and
the evidence column cites a clause rather than a code path. That makes this weaker than a code-vs-spec
audit in a specific way: it establishes that the skill **instructs** the specified behavior, not that
anything **enforces** it. A skill can conform perfectly here and still be ignored by the agent running
it.

That limit is worth stating plainly rather than leaving implied, because it is the same limit recorded
in [`house-review.verification.md`](house-review.verification.md) about exercising a branch of a prose
skill. Conformance for a prose skill answers "does the instruction match the contract", and nothing
more. What closes the remaining gap is exercising the branch on real work, which is what the Epic A
item 8 evaluation records are for.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 everything passes | Conformed | Output format / the `verdict: pass` rule, with Step 2 and Step 4 | pass requires every command succeeded, every criterion `met`, every unreconciled item accepted-with-reason; Step 2 records exit status per command and Step 4 maps each criterion to evidence |
| Scenarios | S-002 a declared command fails | Conformed | Step 2 / "record for each: the command as written, its exit status, and the excerpt of its output that is the actual evidence", with the `verdict: fail` rule | the excerpt requirement is what satisfies "reproduces the relevant portion" |
| Scenarios | S-003 commands pass but the contract diverges | Conformed | Step 3 / "an item marked **to-fix** is a live divergence and withholds a passing verdict, even when every command passed", with the `verdict: fail` rule | the "even when every command passed" clause is the whole point of the scenario and is stated explicitly |
| Scenarios | S-004 a divergence already accepted with a reason | Conformed | Step 3 / "an item marked **accepted-with-reason** does not fail the run, and must still be listed in the report with its recorded reason" | also covered by Step 3's closing rule against renegotiating a recorded disposition |
| Scenarios | S-005 the spec was never approved | Conformed | Step 1 / first precondition bullet, with the `verdict: blocked` rule | amended 2026-07-27 to say "with a blocking reason" rather than implying a single-reason return |
| Scenarios | S-006 no command is declared, or one cannot run | Conformed | Step 1 / second precondition bullet, with the `verdict: blocked` rule | the "do not substitute a command you think is equivalent" clause covers the scenario's second half |
| Scenarios | S-011 both blocking preconditions hold | Conformed | Step 1 / "Check both before returning, and report every reason that holds ... List the reasons in the order above" | added by this task. The fixed order is what makes the record deterministic, which S-011 requires and the goal-1 determinism rule depends on |
| Scenarios | S-007 an acceptance criterion has no evidence | Conformed | Step 4 / "When nothing demonstrates a criterion, mark it `unmet` and state that no evidence was found", with the `verdict: fail` rule | the explicit prohibitions (do not infer from a green suite, an adjacent criterion, or the implementer's report) are stronger than the scenario requires |
| Scenarios | S-008 acceptance criteria only, with no spec | Conformed | Step 1 / "If no spec is supplied at all, that is not a blocker; continue, and record that conformance was not assessed", with the `conformance` output rule | the output rule pins the exact wording `not assessed: no spec supplied` |
| Scenarios | S-009 a repairable defect is found | Conformed | Step 5 / "Verification is read-only ... byte-for-byte unchanged. This holds even when the fix is one line and obvious", with the `findings` output rule | the "one line and obvious" clause names the exact temptation the scenario guards |
| Scenarios | S-010 no report destination is supplied | Conformed | Step 5 / "By default the report is returned inline and no file is created", and Inputs / the optional report destination | stated twice, consistently |
| Proposed Surface | Inputs, required and optional | Conformed | Inputs section / the required and optional lists | matches the surface exactly, including "You never invent one" for the command |
| Proposed Surface | `verdict`, `blocking_reasons`, `commands`, `conformance`, `criteria`, `findings` | Conformed | Output format / the fenced field list and its Rules | field order in the skill matches the surface's order; `blocking_reasons` non-empty exactly when the verdict is not `pass` |
| Proposed Surface | Report delivery | Conformed | Step 5 and Inputs | inline by default, file only when a destination is supplied |

## Coverage proof

- **audited**: S-001 through S-011, and all four Proposed Surface groupings (inputs, the six output
  fields, the verdict values, report delivery). Every spec item was checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

## Observations

**The scenario ids are not in numeric order in the spec, deliberately.** S-011 sits between S-006 and
S-007, grouped with the other two blocking preconditions it completes. Ids are stable and never
renumbered, so grouping by concern was preferred over renumbering or appending. A reader scanning for
S-011 at the end will not find it there.

**Every scenario conforms, and that is a weaker result than it looks.** This contract was drafted by
`spec-author` from the same intent that produced the skill, on the same day, by the same process. A
clean matrix under those conditions mostly confirms that the two documents still agree with each
other. The `feat-0024` run is the stronger evidence, because it put the skill against a real trigger
and checked the outcome clause by clause. Reading this matrix as independent confirmation would
overstate it.

**What is genuinely absent is enforcement.** Nothing mechanically checks that a `blocked` verdict is
returned when a spec is unapproved; the skill says to, and an agent may or may not. Of the three
Epic A item 8 branches, one is now exercised on real work
([`house-review.verification.md`](house-review.verification.md)) and two remain. Until those run, the
strongest claim available for this skill is that its instructions match its contract and one of its
three hardest paths has been observed behaving correctly once.
