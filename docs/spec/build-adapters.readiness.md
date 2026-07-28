---
title: build-adapters readiness
spec: docs/spec/build-adapters.md
task: .tasks/done/feat-0028-exercise-spec-plan-readiness-blocking.md
gated: 2026-07-27
verdict: blocked
branch_exercised: spec-plan-readiness blocking paths
---

# build-adapters readiness gate record

A [`spec-plan-readiness`](../../.agents/skills/spec-plan-readiness/SKILL.md) run over
[`build-adapters.md`](build-adapters.md) plus its proposed task decomposition
([`chore-0015`](../../.tasks/done/chore-0015-state-build-adapters-overwrite-asymmetry.md)), performed
2026-07-27 to exercise the last of the three branches named in ROADMAP Epic A item 8.

Format reused from [`house-review.verification.md`](house-review.verification.md).

## Why this trigger is real and not staged

The question asked was the one the gate exists to answer, at the moment it is normally asked: work is
about to start on `chore-0015`, so may it? Both inputs are real and neither was arranged to fail. The
spec is approved, thirteen scenarios, `Open Questions: None`. The task was authored to the `new-task`
bar as an ordinary piece of work, with honest `touched_files`, a real parent, resolved `depends_on`,
and a mechanically-verifiable acceptance command.

The blocking condition is not a defect planted in either input. It is the genuine situation
`chore-0015` describes: the behavior it proposes to settle is **not in the contract at all**, which
the `feat-0026` audit recorded as "behavior found outside the contract". A task cannot trace to a
scenario that does not exist.

## Result

```text
verdict: blocked

blocking_gaps:
  - source: both
    reason: chore-0015 is not traceable to any spec scenario. It proposes to settle how shared
      assets are treated on a re-run, and none of S-001 through S-013 covers that. S-010 covers
      the rules half only ("a rules file already present is never overwritten") and is silent on
      skill assets, which is the half the task is about.
    required_resolution: add a scenario covering how each shared-asset kind is treated on a
      re-run, then map the task to it.

  - source: spec
    reason: the Proposed Surface lists the emitted shared paths but states nothing about
      re-run behavior for them, so the change cannot be mapped to a test layer or verified
      once made.
    required_resolution: state the re-run behavior for both shared-asset kinds, in a scenario
      and, if the two differ deliberately, in a Constraint saying why.

  - source: plan
    reason: chore-0015 carries no risk or rollback notes, and the deterministic rule requires
      them because it touches more than one module (docs/spec/build-adapters.md,
      build-adapters.conformance.md, and scripts/build-adapters.py).
    required_resolution: add risk and rollback notes, or narrow touched_files to a single
      module if the code change is not in fact needed.

scenario_to_test_map: []

task_to_scenario_map:
  - task: chore-0015
    scenarios: []
    notes: no scenario covers the behavior this task settles; see the source-both gap above.

# first_safe_task omitted: the verdict is blocked.
```

A blocked verdict authorizes no tests, no production code, and no implementation delegation.
`chore-0015` stays open and unstarted.

## Did the branch behave as its contract describes?

Yes, and on the more interesting path. The gate did **not** short-circuit: Step 1's inputs were both
readable, so evaluation proceeded through the spec, plan, and consistency checks rather than
returning the cheap missing-input blocker. All three output rules held: `blocking_gaps` is non-empty
with the verdict not `implementable`, `scenario_to_test_map` is empty because blockers prevented
reliable mapping, `task_to_scenario_map` lists the unmapped task which also appears as a
`source: both` gap, and `first_safe_task` is omitted.

The `source` classification behaved as specified too. The traceability failure is `both`, because
neither side alone is wrong: the task is well-formed and the spec is well-formed, and the defect is
that they do not meet. The missing risk notes are `plan`, because that is a property of the task
alone. Splitting those correctly is the distinction the field exists to make.

## Observations

**The most valuable gap was the one that needed two documents to see.** The `source: plan` gap
(missing risk notes) is the kind a checklist catches. The `source: both` gap is not visible from
either document: `chore-0015` reads as a complete task, `build-adapters.md` reads as a complete
contract, and only holding them together shows that the work has nothing to trace to. That is the
gate's actual argument for existing, and it only appears on the non-short-circuit path.

**The gate found a defect in a task written to the `new-task` bar hours earlier.** `chore-0015` has
honest `touched_files`, a real parent, and a verifiable acceptance command, and it still fails the
deterministic risk rule, because `new-task` never prompts for risk or rollback notes and its template
has no section for them. That is a genuine seam between the two skills, not a flaw in this task, and
it is the second time this session that the spine's front half and back half have disagreed about
what a task file must carry. The first was task-to-scenario traceability (`feat-0025`).

**Blocking on absent-from-contract is the correct and slightly uncomfortable answer.** The obvious
reading of `chore-0015` is "just add the scenario, it is a two-line change". The gate's answer is that
you cannot implement against a contract that does not describe the behavior, and the fix is to amend
the contract first, which is exactly what `chore-0015` says to do in its own scope section. The gate
and the task agree; the gate simply refuses to let the amendment and the implementation happen in one
undifferentiated step.
