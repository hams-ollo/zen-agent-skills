---
title: code-review verification
spec: docs/spec/code-review.md
task: .tasks/feat-0024-exercise-verifier-blocked-branch.md
verified: 2026-07-27
verdict: blocked
branch_exercised: verifier-agent S-005 (spec not approved)
---

# code-review verification record

A [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) run against the
[`code-review`](../../.agents/skills/code-review/SKILL.md) implementation, performed 2026-07-27 to
exercise the `blocked` verdict on real work (`feat-0024`).

This is also the first **evaluation record**, the reusable format for the two remaining unexercised
branches. Its shape is the standard verifier-agent output, plus the three frontmatter fields an
evaluation needs on top of a verification: which branch was exercised, what triggered it, and the
verdict.

## Why this trigger is real and not staged

The branch fires because [`docs/spec/code-review.md`](code-review.md) carries `status: draft`. That
spec is one the kit genuinely wants: `code-review` is shipped, load-bearing, composes a swappable
lens, and had no contract. It was drafted properly with `spec-author`, self-checked to `ready`
against the `spec-quality` lens, and written `status: draft` because only a human sets `approved`.

It happens to be unapproved at the moment verification runs, which is precisely the situation the
branch exists to catch. A fixture spec written to trigger `blocked` would have proven the branch can
run, not that it fires when it should.

## Result

```text
verdict: blocked
blocking_reasons:
  - reason: the supplied contract is not approved
    detail: docs/spec/code-review.md carries `status: draft`. A draft spec is one no human has
      agreed to, so verifying against it would launder an unapproved contract into evidence.
commands:
  - not executed. A blocked run reports no pass or fail for the work itself, so no verification
    command was run and none is reported.
conformance:
  not assessed: verification did not proceed past the approval precondition
criteria:
  - not assessed: the same precondition stops the run before any criterion is checked
findings:
  - defect: none observed. The implementation was not verified, which is what `blocked` means.
    where: n/a
```

`.agents/skills/code-review/SKILL.md` is byte-for-byte unchanged, confirmed by comparing its object
hash against `HEAD`. Verification is read-only and a blocked run changes even less than a completed
one.

## Did the branch behave as its contract describes?

Yes, on every clause. [`verifier-agent.md`](verifier-agent.md) S-005 requires that a draft spec
produce `verdict: blocked`, that the run state the contract is unapproved, and that it "does not
execute the verification or report a pass or a fail." All three held: the verdict is `blocked`, the
blocking reason names the unapproved contract, no command was run, and no pass or fail was reported
for `code-review`.

The output format rules held too. `blocking_reasons` is non-empty exactly because the verdict is not
`pass`, and `conformance` reads as not assessed rather than being inferred from anything.

## Two observations from the run

**S-006's precondition was independently true, and the contract did not say what to do about that.**
Alongside the unapproved spec, `code-review` has no declared verification command: no task in flight
carries acceptance criteria for it and no test file exists. That is S-006's trigger, satisfied at the
same moment as S-005's. Read literally, verifier-agent's Step 1 told the run to "stop and return
`blocked`" at the first precondition, so this record reports one blocking reason, which is what the
procedure produced on the day. But `blocking_reasons` is a list, which suggests accumulation, and the
contract never said which behavior was intended when both preconditions hold.

**Resolved by `chore-0014` on 2026-07-27: the behavior is to accumulate.** Both preconditions are now
checked before returning, and every reason that holds is reported in a fixed order, specified as
[`verifier-agent.md`](verifier-agent.md) S-011. Re-run against the same state, this record would carry
two blocking reasons rather than one: the unapproved contract first, the missing command second. The
single-reason record above is preserved as what the procedure produced at the time, because a ledger
entry that describes a past run is not corrected to match a later contract.

**"Exercising a branch" of a skill means something weaker than exercising a branch of a program, and
the evaluation format should not pretend otherwise.** These skills are prose procedures, so a branch
is reached by an agent following the procedure, not by code executing. This record is evidence that
the procedure, followed faithfully against a real trigger, produces the specified outcome. It is not
evidence that the outcome is mechanically enforced, because nothing enforces it. Any future
evaluation record should state which of the two it is.

## Evaluation record format

For the two remaining branches, `test-author`'s characterization mode and `spec-plan-readiness`'s
blocking paths, reuse this shape:

1. **Frontmatter**: `spec`, `task`, `verified`, `verdict`, and `branch_exercised` naming the skill and
   scenario id.
2. **Why this trigger is real**: what produced the condition, and why it was not staged.
3. **Result**: the skill's own declared output format, verbatim, with nothing added or omitted.
4. **Did the branch behave as its contract describes**: clause by clause against the scenario, saying
   plainly where it did not.
5. **Observations**: what the run revealed that the contract does not cover.

Keep it to one page. If producing the record costs more than reaching the branch, the format is
wrong.
