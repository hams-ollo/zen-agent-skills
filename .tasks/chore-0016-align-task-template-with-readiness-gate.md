---
id: chore-0016
title: Align new-task and the task template with what spec-plan-readiness requires
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - .agents/skills/new-task/SKILL.md
  - .tasks/_TEMPLATE.md
  - .agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl
created: 2026-07-27
---

## Problem

The spine's front half and back half disagree about what a task file must carry, and the disagreement
has now surfaced twice.

[`spec-plan-readiness`](../.agents/skills/spec-plan-readiness/SKILL.md) Step 3 requires "risks,
rollback notes, or failure-handling expectations" for any task that touches more than one module,
changes a persisted format, or cannot be reversed by reverting one commit. Neither
[`new-task`](../.agents/skills/new-task/SKILL.md) nor [`_TEMPLATE.md`](_TEMPLATE.md) has any notion of
risk or rollback, so a task authored perfectly to the `new-task` bar fails the gate by construction
whenever the risk rule fires.

The `feat-0028` run demonstrated it on real work: `chore-0015`, authored to the bar hours earlier with
honest `touched_files`, a real parent, resolved `depends_on`, and a verifiable acceptance command,
still produced a `source: plan` gap for missing risk notes.

This is the second seam of the same kind. The first was task-to-scenario traceability, where the gate
required a mapping that `new-task` never produced and the template had no field for; `feat-0025` fixed
that by adding optional `spec` and `scenarios` frontmatter. The pattern is that
`spec-plan-readiness` was folded in from upstream against a different planning artifact, and its
requirements were never reconciled against the task format this kit actually authors.

## Scope

**In scope:** give the task format a place for risk and rollback notes, and teach `new-task` when to
fill it, using `spec-plan-readiness`'s own deterministic rule as the trigger so the two cannot drift
apart again. Update both template copies.

Then re-read the rest of Step 3's required list against `_TEMPLATE.md` and close any other mismatch
found, rather than fixing this one instance and waiting for the third.

**Out of scope:** changing `spec-plan-readiness`'s requirements. The gate is not wrong; the task
format is behind it. Making the section mandatory for every task, which would burden the majority that
do not trigger the rule.

## Implementation notes

- Prefer an optional `## Risks and rollback` section, present only when the deterministic rule fires,
  over a mandatory one. A section every task carries and most leave empty trains authors to skip it.
- `new-task` should state the trigger explicitly rather than saying "add risks where relevant", since
  the gate's rule is mechanical and a vague prompt will not match it.
- Check Step 3's full list while here: ordered work items, dependency order, expected files,
  validation commands, test strategy, success criteria, task-to-scenario mapping, and risk/rollback.
  The first six are covered; scenarios were added by `feat-0025`; this closes the last.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] `_TEMPLATE.md` and the scaffold's copy both carry the optional risk/rollback section.
- [ ] `new-task` names the deterministic trigger, matching `spec-plan-readiness`'s wording.
- [ ] A task that triggers the rule and one that does not are both expressible without ceremony.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
