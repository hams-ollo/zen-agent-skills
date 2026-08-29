---
title: systematic-debugging
status: approved
---

# systematic-debugging

Behavioral contract for the `systematic-debugging` skill. Drafted 2026-08-18 by the `spec-author`
skill from the 2026-08-18 review pass, and self-checked to `ready` with the `spec-quality` lens.
**Approved by the author on 2026-08-19.**

**Amended 2026-08-29 (`chore-0078`) to settle both Open Questions before anything was built against
this contract: `S-014` and `S-015` are new, and the Constraints bullet on read-only posture now
points at them.** This amendment is **pending the author's re-approval**. Open Question 1 asked where
temporary instrumentation may live, and it blocked implementation rather than deferring cleanly:
`S-005`'s observable, that no tracked file differs when the run ends, is satisfied both by
instrumenting the tracked files and cleaning up afterwards and by working only in a copy, and the
first fails only on a run that dies partway, which is to say only when something else has already
gone wrong. Leaving it open would have let whoever wrote the implementation decide this contract's
most consequential safety property. The answer, decided by the author on 2026-08-29, is the copy, and
it is stated as a property a reader can check rather than as a mechanism: naming `git worktree` would
fix an implementation and would be false of a target repository that is not a git repository.
Open Question 2 is settled by adopting this contract's own recommendation, recorded in place so a
later reader does not reopen it as an oversight. `status` is left reading `approved` per the
convention in [`README.md`](README.md), for the reason that file gives. Nothing else in this contract
changes, and `S-001` through `S-013` are untouched.

## Problem

The kit's spine assumes work arrives already diagnosed. Nothing in it establishes a cause.

[`spec-author`](../../.agents/skills/spec-author/SKILL.md) accepts "a raw idea, feature request, or
bug" and turns it straight into a contract. [`new-task`](../../.agents/skills/new-task/SKILL.md) sets
the bar a task file must clear: honest `touched_files`, a `## Problem` grounded in reproduction, and
an acceptance command that passes only when the work is done. **All three of those require the cause
to already be known.** A bug arriving at either skill undiagnosed produces a contract or a task file
written against a symptom, and the failure is silent, because a task file about a symptom looks
exactly like a task file about a cause.

The work is being done, without a skill guiding it. The diagnostic quality in this repository's own
backlog is high and entirely unguided: `bug-0026` carries a docstring-stripped diff of two files
isolating the two lines that differ, and `chore-0038` item 3 carries a reproduced `rc=2` traceback
captured deliberately from a subdirectory to prove a working-directory dependency. Neither followed a
procedure, so neither is repeatable and neither survives as a standard.

Two consequences make this worth answering now. An unattended run has no diagnosis step at all, so a
[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) agent meeting an unexplained failure has
nothing to fall back on but guessing, which is the behavior the kit exists to prevent. And `feat-0042`
is scoped to force a classification into `false_positive`, `core_issue`, or `futility` after repeated
failure, which is a diagnostic distinction being drawn inside a review-fix loop rather than by
anything that diagnoses.

## Goals

1. Turn a reported defect into a **named root cause with the evidence that established it**, distinct
   from the symptom that was reported.
2. Return a **deterministic verdict**, so a run that could not find a cause is never mistaken for one
   that did, and an unattended run cannot end ambiguously.
3. Produce a diagnosis that **feeds `new-task` directly**, carrying the facts a task file's bar
   demands and cannot otherwise obtain.
4. **Refuse to repair.** The skill diagnoses; every other skill in the spine keeps its job.
5. **Bound the investigation**, so a hypothesis loop that will not converge terminates with a verdict
   rather than running until a context window ends.

## Non-Goals

- **Fixing the defect.** The fix is a task, dispatched by `fix-batch`.
- **Writing the regression test.** That is [`test-author`](../../.agents/skills/test-author/SKILL.md),
  which the diagnosis feeds by naming the observable the test must pin.
- **Writing the task file.** That is `new-task`.
- **Judging code quality.** A cause that happens to sit in ugly code is still just the cause;
  [`house-review`](../../.agents/skills/house-review/SKILL.md) owns quality.
- **Confirming a fix worked.** That is [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md).
- **Diagnosing the agent's own reasoning failures.** This contract covers defects in a repository
  under work, not misfires of the harness running it.
- **Deciding whether the defect is worth fixing.** Priority is the author's, and is expressed on the
  task file.

## Constraints

- **Read-only with respect to tracked files.** The skill may read anything and may run commands, and
  no tracked source, test, or config file differs when the run ends. This mirrors the posture
  `verifier-agent` and `house-review` already hold, and it is what keeps a diagnosis admissible as
  evidence rather than becoming the change it was meant to explain. Where the investigation needs to
  observe something reading cannot reach, `S-014` says where the instrumentation lives and `S-015`
  says what happens where it cannot live anywhere. Those two carry the rule; this bullet points at
  them rather than restating it, because a restatement is a second copy that can come to disagree
  with the first.
- **One hypothesis at a time.** A trial that varies more than one thing cannot attribute its own
  result, so it produces no evidence regardless of outcome.
- **The record is returned inline unless a destination is supplied**, matching `verifier-agent`'s
  rule for the same choice. A run that persists a report nobody asked for writes into a repository it
  promised only to read.
- **Harness-portable.** No dependency on a particular agent runtime, debugger, or language toolchain,
  per the portability contract in `AGENTS.md`. The procedure is stated in terms of observations and
  commands the target repository already has.
- **This contract owns the kit's classification vocabulary.** Decided by the author 2026-08-18. The
  three verdicts above are the kit's single vocabulary for "what did the investigation conclude", and
  `feat-0042` consumes them rather than defining `false_positive`, `core_issue` and `futility` as a
  parallel set. The correspondence it was scoped against is exact enough to make two vocabularies a
  translation layer rather than a distinction: `false_positive` is `not_reproducible` reached from the
  reviewing side, `core_issue` is `root_cause_found`, and `futility` is `architectural` triggered by a
  repeat count rather than a hypothesis count. A skill that must classify after repeated failure calls
  this one and reports its verdict.

## Scenarios

### Scenario S-001: a reproducible defect yields a named cause
- **Given** a defect report with enough detail to attempt a reproduction
- **When** the skill runs, the reproduction succeeds, and a hypothesis is confirmed
- **Then** it returns `verdict: root_cause_found` with `symptom` restating the reported behavior as
  an observable, `reproduction` naming the steps that produced it, `root_cause` stating the cause as
  a claim about program behavior, and `confirming_observation` stating what was observed that would
  have differed had the hypothesis been wrong

### Scenario S-002: a defect that will not reproduce is a verdict, not a failure
- **Given** a defect report whose stated steps do not produce the reported behavior
- **When** the skill has attempted the reproduction and recorded what it observed instead
- **Then** it returns `verdict: not_reproducible` with `reproduction` naming what was attempted and
  what was observed, and `missing_input` naming what would change the answer, and no `root_cause` is
  offered

### Scenario S-003: a disproved hypothesis is recorded, not discarded
- **Given** an investigation in progress with a stated hypothesis
- **When** the trial's result contradicts that hypothesis
- **Then** `hypotheses` retains that hypothesis, its trial, and its disconfirming result, and the
  next hypothesis appears in `hypotheses` as a separate entry stated before its own trial

### Scenario S-004: an investigation that will not converge terminates with a verdict
- **Given** an investigation that has reached the declared bound on disproved hypotheses
- **When** no confirmed cause has been established
- **Then** it returns `verdict: architectural` with `bound_reached` naming the bound and the count,
  `hypotheses` carrying every hypothesis tried and why each was disproved, and a statement that the
  shape of the system rather than any single defect is the subject

### Scenario S-005: a request to fix is refused
- **Given** a run whose request asks the skill to diagnose and then repair the defect
- **When** the skill completes its diagnosis
- **Then** it returns the diagnosis, performs no repair, and no tracked file differs from its state
  at the start of the run

### Scenario S-006: the diagnosis carries what a task file's bar demands
- **Given** a run that returned `verdict: root_cause_found` for a cause that implicates code
- **When** the diagnosis is handed to `new-task`
- **Then** `implicated_files` names the files the cause implicates, `reproduction` supplies the basis
  for an acceptance command, and `regression_observable` names the observable a regression test must
  pin

### Scenario S-007: a report without any way to observe it is answered, not guessed at
- **Given** a defect report that states a symptom and supplies no way to observe it
- **When** the skill cannot construct a reproduction from the repository's own tests or tooling
- **Then** it returns `verdict: not_reproducible` with `missing_input` naming what is absent, and no
  `root_cause` inferred from reading code alone

### Scenario S-008: a failure crossing components is localized before it is explained
- **Given** a defect whose symptom surfaces in one component and whose cause may lie in another
- **When** the skill investigates
- **Then** `hypotheses` shows the boundary at which the behavior first diverges, and the observation
  that placed it, appearing before any entry proposing why it diverges

### Scenario S-009: the record of a run is not rewritten by a later one
- **Given** a persisted record whose verdict was `not_reproducible` or `architectural`
- **When** a later run on the same defect reaches a different verdict
- **Then** the earlier record is unchanged and the later run is persisted as a separate record,
  because a record revised to match a later state stops being evidence

### Scenario S-010: the report itself can be the defect
- **Given** a reproduction that exhibits behavior differing from what the report described
- **When** the observed behavior matches the system's stated contract and the report does not
- **Then** it returns `verdict: root_cause_found` with `root_cause` naming the report as the thing in
  error and citing the contract checked against, and `implicated_files` and `regression_observable`
  are absent, because there is no code defect to fix or pin

### Scenario S-011: a dispatched agent can tell its own defect from one it uncovered
- **Given** an agent working a task in isolation that meets a failure its task file does not describe
- **When** the agent invokes this skill
- **Then** `reproduction` states the outcome against the working tree and against the unmodified base
  it started from, so the record distinguishes a defect the agent introduced from one already present

### Scenario S-012: an intermittent defect is classified rather than declared fixed
- **Given** a defect that reproduces on some attempts and not others
- **When** the skill has repeated the reproduction
- **Then** `reproduction` states the observed rate, `hypotheses` states each condition tried and its
  outcome, and `verdict: root_cause_found` is returned only when a condition that reliably produces
  the behavior has been found, never on the strength of an attempt that happened to pass

### Scenario S-013: the record is not written to disk unless asked for
- **Given** a run with no record destination supplied
- **When** the run completes at any verdict
- **Then** the record is returned inline and no file is created, and when a destination is supplied
  instead, the same record is written there

### Scenario S-014: instrumentation lives in a copy, never in the tracked files
- **Given** an investigation that needs to execute code or add temporary instrumentation to observe
  behavior reading alone cannot reach
- **When** the skill adds that instrumentation
- **Then** the instrumentation exists only in a copy the run made for the purpose, and at no point
  during the run does any tracked file differ from its state at the start, whether the run reaches a
  verdict, is interrupted, or fails partway

### Scenario S-015: a repository that cannot be copied is answered, not refused
- **Given** a target repository offering no way to make a working copy for the run
- **When** an observation would otherwise require instrumentation
- **Then** no instrumentation is added and no tracked file is edited, `reproduction` records that the
  observation was made without instrumentation, and the run continues to a verdict on the evidence it
  could gather

## Proposed Surface

**Verdicts.** Exactly one per run.

| Verdict | Meaning |
|---|---|
| `root_cause_found` | A cause was named and confirmed by an observation that could have disconfirmed it. |
| `not_reproducible` | The reported behavior could not be produced. Not a failure of the run. |
| `architectural` | The bound was reached with no confirmed cause; the system's shape is the subject. |

**Diagnosis record.**

| Field | Present when | Content |
|---|---|---|
| `verdict` | always | One of the three above. |
| `symptom` | always | The reported behavior, restated as an observable. |
| `reproduction` | always | The steps or command, what they produced, the tree state they ran against, and the observed rate when the symptom is intermittent. |
| `hypotheses` | always | Each hypothesis stated, its trial, and its result, in order, including disproved ones. |
| `root_cause` | `root_cause_found` | The cause as a claim about behavior, and where it originates. |
| `confirming_observation` | `root_cause_found` | What was observed that would have differed had the hypothesis been wrong. |
| `implicated_files` | `root_cause_found`, and the cause implicates code | Files the cause implicates, for a task file's `touched_files`. |
| `regression_observable` | `root_cause_found`, and the cause implicates code | The observable a regression test must pin. |
| `missing_input` | `not_reproducible` | What would make a reproduction possible. |
| `bound_reached` | `architectural` | The bound, and the count of disproved hypotheses. |

**Inputs.**

| Input | Required | Content |
|---|---|---|
| Defect report | yes | The reported behavior, in whatever form it arrived. |
| Reproduction steps | no | Supplied steps, when the reporter had them. |
| Investigation bound | no | Maximum disproved hypotheses before `architectural`. |
| Record destination | no | Where to persist the record. Without it the record is returned inline. |

## Open Questions

Both are settled. Neither is reopened without a new amendment, and each records its answer's location
so a later reader can check the answer rather than re-derive the question.

1. **Settled 2026-08-29 (`chore-0078`): the skill may run code and add temporary instrumentation, and
   that instrumentation lives only in a copy the run made for the purpose.** The answer is `S-014`,
   with `S-015` covering the target that offers no way to make such a copy, and the Constraints
   bullet on read-only posture pointing at both. Instrumenting the tracked files and cleaning up
   afterwards was the alternative and was rejected: it satisfies `S-005` on every run that completes,
   which means its failure is invisible until a run dies partway, and a safety property that only
   fails once something else has already gone wrong is the kind this kit keeps being bitten by. The
   cost of the answer is stated rather than discovered: it is `S-015`, and it is a real narrowing of
   what the skill can observe in a repository it cannot copy.

2. **Settled 2026-08-29 (`chore-0078`): the default investigation bound stays out of this contract,
   adopting the recommendation this question carried.** The number is a tuning value rather than a
   behavioral commitment, `S-004` already constrains that a bound exists, is declared, and terminates
   the run, and fixing a number here would make every future retune an amendment. Recorded as
   considered rather than deleted, so its absence reads as a decision and not as an oversight.
