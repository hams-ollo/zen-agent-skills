---
title: verifier-agent
status: approved
---

# verifier-agent

Behavioral contract for the `verifier-agent` skill (ROADMAP Epic B item 7). Drafted
2026-07-24 by the `spec-author` skill and self-checked to `ready` with the `spec-quality` lens.

Reopened to `draft` on 2026-07-27 and amended (`chore-0014`). The `feat-0024` run hit a state this
contract did not cover: both blocking preconditions true at once. S-005 and S-006 each said "returns
`blocked`" without saying what happens when both hold, while the plural `blocking_reasons` field
implied accumulation and the skill body read as short-circuit. S-011 settles it, and the decision was to
accumulate rather than short-circuit. Re-approved by the author on 2026-07-27.

## Problem

The spine can now write a contract, gate it, decompose it, implement it, derive tests from it, and
audit code against it, but nothing pulls those signals together into one answer to the question that
actually gates landing a change: is this implementation done and correct?

Today that judgment is scattered. [`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) requires an
independent verification pass but leaves its procedure to the agent running it, so the depth and the
evidence vary between runs. [`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md)
audits code against a spec but is explicitly independent of test pass/fail, so a clean matrix says
nothing about whether the suite runs. A task's acceptance criteria carry an exact command, but
nothing records that the command was actually executed or what it printed. The result is that
"verified" is asserted rather than evidenced, and the agent that wrote the code is usually the one
asserting it.

Two failures follow. An implementation can reach reconciliation with a green suite and a silent
contract divergence, because no step compares the two. And a verification that could not run at all,
because a command was missing or a spec was never approved, is indistinguishable in the record from
one that ran and passed.

## Goals

1. Emit one deterministic verdict of `pass`, `fail`, or `blocked` for an implementation, together
   with the evidence that produced it, so the decision to reconcile rests on a record rather than an
   assertion.
2. Execute the declared verification commands and record each command's exact observed outcome.
3. Compose the `spec-conformance` lens so that contract divergence, not only command failure, can
   withhold a passing verdict.
4. Check each task acceptance criterion against named evidence, so an unmet criterion is visible
   rather than absorbed into an overall impression.
5. Distinguish a verification that ran and failed from one that could not run, so an unrunnable
   verification is never recorded as a pass or a fail.

## Non-Goals

- Editing, fixing, refactoring, or reformatting the implementation, its tests, or its spec. This
  skill has no repair role of any kind.
- Authoring tests. That is `test-author`.
- Judging spec well-formedness (`spec-quality`) or gating a spec plus plan for readiness
  (`spec-plan-readiness`).
- Judging code quality, style, or design (`code-review`).
- Dispatching agents or managing worktrees (`fix-batch`), or landing changes
  (`reconcile-worktrees`).
- Deciding whether a recorded divergence is acceptable. It reports the disposition the conformance
  audit already recorded, and does not renegotiate it.

## Constraints

- The skill composes the `spec-conformance` lens rather than restating its rules or re-deriving its
  matrix.
- It is read-only for every file it verifies. Its only permitted side effects are executing the
  declared commands and writing its own verification report when asked to persist one.
- Verification commands come from the task's acceptance criteria or the repository's documented
  command. The skill does not invent, substitute, or relax a command.
- It runs after implementation and test authoring and before reconciliation, so its evidence is
  available at the moment the landing decision is made.
- The verdict follows a deterministic rule: the same evidence always yields the same verdict, and no
  verdict is reached by overall impression.
- A spec is only a valid contract to verify against when a human has marked it approved. A draft
  spec is not a contract.
- Verification may proceed against task acceptance criteria alone when no spec exists, provided the
  report states that contract conformance was not assessed.

## Scenarios

### Scenario S-001: everything passes

- **Given** an approved spec, a task whose acceptance criteria are all met, and declared commands
  that all exit successfully
- **When** verifier-agent runs
- **Then** it returns `verdict: pass` with each command's exact exit status, the conformance result,
  and each acceptance criterion mapped to the evidence that satisfies it.

### Scenario S-002: a declared command fails

- **Given** an implementation whose declared verification command exits non-zero
- **When** verifier-agent runs
- **Then** it returns `verdict: fail`, names the failing command, and reproduces the relevant portion
  of its output as the evidence.

### Scenario S-003: commands pass but the contract diverges

- **Given** declared commands that all pass, and a `spec-conformance` audit whose unreconciled set
  contains an item marked for fixing
- **When** verifier-agent runs
- **Then** it returns `verdict: fail` and names the diverged scenario or surface element, so a green
  suite alone cannot produce a passing verdict.

### Scenario S-004: a divergence already accepted with a reason

- **Given** declared commands that all pass, and a conformance audit whose only unreconciled item is
  recorded as accepted with a stated reason
- **When** verifier-agent runs
- **Then** it returns `verdict: pass` and lists the accepted divergence and its recorded reason in
  the report, rather than treating the acceptance as a hidden exception or reopening the decision.

### Scenario S-005: the spec was never approved

- **Given** a spec whose status is draft rather than approved
- **When** verifier-agent runs
- **Then** it returns `verdict: blocked` with a blocking reason stating that the contract is
  unapproved, and does not execute the verification or report a pass or a fail.

### Scenario S-006: no command is declared, or a declared command cannot run

- **Given** a task with no declared verification command, or a declared command whose runner is
  absent from the environment
- **When** verifier-agent runs
- **Then** it returns `verdict: blocked` with a blocking reason naming the missing command or
  runner, and does not substitute a command of its own choosing.

### Scenario S-011: both blocking preconditions hold at once

- **Given** a run whose spec is unapproved and which also has no runnable declared command
- **When** verifier-agent runs
- **Then** it returns `verdict: blocked` carrying **both** blocking reasons, the unapproved contract
  first and the missing command second, rather than only the first one found. The ordering is fixed,
  so the same state always produces the same record.

### Scenario S-007: an acceptance criterion has no evidence

- **Given** a task acceptance criterion for which no command result, code location, or test
  demonstrates the required behavior
- **When** verifier-agent runs
- **Then** it returns `verdict: fail`, names that criterion, and records it as `unmet` with evidence
  stating that none was found, rather than inferring it was satisfied.

### Scenario S-008: acceptance criteria only, with no spec

- **Given** a task with acceptance criteria and declared commands but no spec to verify against
- **When** verifier-agent runs
- **Then** it verifies the commands and criteria, returns `pass` or `fail` on that basis, and states
  in the report that contract conformance was not assessed because no spec was supplied.

### Scenario S-009: a repairable defect is found

- **Given** a verification run that surfaces a defect the verifier could plainly fix
- **When** verifier-agent completes
- **Then** the implementation, its tests, and its spec are byte-for-byte unchanged, and the defect
  appears in the report as a finding.

### Scenario S-010: no report destination is supplied

- **Given** a verification run invoked without a report destination
- **When** verifier-agent completes
- **Then** it returns the report inline and creates no file, so persisting evidence is an explicit
  request rather than a side effect of verifying.

## Proposed Surface

| Element | Detail |
|---|---|
| Inputs (required) | Task acceptance criteria, and at least one declared verification command |
| Inputs (optional) | Approved spec path, report destination |
| `verdict` | Exactly one of `pass`, `fail`, or `blocked` |
| `blocking_reasons` | Why the verdict is not `pass`, empty when it is; the only field consulted for the reason. Carries every reason that holds, in a fixed order, not just the first found |
| `commands` | Per command: the command as declared, its exit status, and the evidence excerpt from its output |
| `conformance` | The audited and unreconciled sets carried from `spec-conformance`, each unreconciled item with its recorded disposition, or an explicit note that conformance was not assessed |
| `criteria` | Per acceptance criterion: `met` or `unmet`, and the evidence naming a command result, code location, or test, or stating that no evidence was found |
| `findings` | Defects observed during verification and not repaired |
| Report delivery | Returned inline by default; written to `docs/spec/<spec>.verification.md` only when a report destination is supplied |

## Open Questions

None.
