---
id: feat-0028
title: Exercise spec-plan-readiness's blocking paths on a real go/no-go question
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - docs/spec/build-adapters.readiness.md
  - .tasks/chore-0015-state-build-adapters-overwrite-asymmetry.md
created: 2026-07-27
---

## Problem

The last of the three branches ROADMAP Epic A item 8 names as never having fired on real work.

## Scope

**In scope:** ask the gate a real go/no-go question, over an approved spec and a genuinely-authored
task decomposition, and record the run.

**Out of scope:** resolving the gaps the gate reports. A blocked verdict authorizes no implementation,
and acting on it immediately would defeat the point of recording it. `chore-0015` stays open.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] The gate ran over a real approved spec and a real task, neither arranged to fail.
- [x] It returned `blocked` with specific gaps, and omitted `first_safe_task`.
- [x] The run is recorded in the `feat-0024` evaluation-record format.
- [x] No implementation was started on the blocked work.

## Outcome (2026-07-27)

`verdict: blocked` with three gaps across all three `source` values, recorded at
[`build-adapters.readiness.md`](../docs/spec/build-adapters.readiness.md). It reached the
non-short-circuit path, which is the branch worth exercising: both inputs were readable, so evaluation
proceeded through the spec, plan, and consistency checks rather than returning the cheap missing-input
blocker.

Two findings:

- **The most valuable gap needed two documents to see.** `chore-0015` reads as a complete task and
  `build-adapters.md` reads as a complete contract; only holding them together shows the work has no
  scenario to trace to. That is the gate's actual argument for existing.
- **A second seam between the spine's halves.** `chore-0015` was authored to the `new-task` bar hours
  earlier and still failed the deterministic risk rule, because `new-task` never prompts for risk or
  rollback notes and `_TEMPLATE.md` has no section for them, while `spec-plan-readiness` requires them
  for any task touching more than one module. The first such seam was task-to-scenario traceability
  (`feat-0025`). Filed as `chore-0016`.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
