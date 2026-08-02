---
id: chore-0011
title: Document the two skill shapes in AGENTS.md and give every skill a house-style pointer
type: chore
status: done
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: [feat-0022, chore-0010]
touched_files:
  - AGENTS.md
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/new-task/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
  - .agents/skills/spec-plan-readiness/SKILL.md
created: 2026-07-25
---

## Problem

Two related gaps, one cosmetic and one functional. The 2026-07-25 review pass found that only 4 of
19 skills follow the full section shape (`When to use` / `When not to use` / `Inputs` / `Procedure` /
`Output format` / `Notes` / `Conventions`), and that `## Conventions` appears in only 8 of 19.

Nothing violates [`AGENTS.md`](../../AGENTS.md), which mandates only frontmatter plus a body. **The
inconsistency is not itself the defect.** Two shapes are in use and both are legitimate: workflow
skills carry a procedure, while lenses (`spec-quality`, `test-quality`, `review-quality`) carry an
`Intent` / `Workflow` / `Output format` shape because they are composed rather than run. The defect
is that this is nowhere written down, so the author of skill number 20 has to guess.

The functional half is narrower and more serious than the section count suggests. **Seven skills
carry no reference to the house-style module at all:**

| Skill | `## Conventions` | Any house-style pointer |
|---|---|---|
| `fix-batch` | no | **none** |
| `init-worktracking` | no | **none** |
| `new-task` | no | **none** |
| `pr-describe` | no | **none** |
| `reconcile-worktrees` | no | **none** |
| `spec-plan-readiness` | no | **none** |

`spec-conformance` was on this list until the 2026-07-27 review pass gave it a `## Conventions`
section, taking the set from seven to six.

`code-review`, `doc-author`, `project-bootstrap`, and `test-quality` lack the section but do point at
house style inline, so they are fine and are **not** in scope.

This matters because the house-style module is swappable by design. An adopter who replaces
[`.agents/rules/house-style.md`](../../.agents/rules/house-style.md) with their own voice is silently
ignored by any skill that never points at it, which breaks the promise the kit makes about that file.

## Scope

**In scope:** add a short section to `AGENTS.md` recording that both shapes are valid and when each
applies. Add a house-style pointer to the six skills that have none, in each skill's own voice.

**Out of scope:** retrofitting any skill to the full modern shape. That was considered and rejected:
it is a large diff for cosmetic gain and would flatten the deliberate brevity of `doc-author` (41
lines) and `doc-revise` (32 lines). Touching the four skills that already point at house style
inline. Changing the content of `house-style.md` itself.

## Implementation notes

- **Two of the six need different wording, and getting this wrong would be a real regression.**
  [`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) and
  [`new-task`](../../.agents/skills/new-task/SKILL.md) operate on a *target* repository, and
  `init-worktracking` explicitly warns against hardcoding this kit's voice into a scaffolded repo
  ("Do not invent house rules and do not import another project's voice"). For those two, the pointer
  must say to follow **the target repo's** conventions, and may mention this kit's module only as the
  default when the skill is run here. Do not paste the standard paragraph into them unchanged.
- The other four can follow the wording already used by `verifier-agent`, `doc-sync`, `spec-author`,
  `test-author`, and `spec-conformance`: a short `## Conventions` section naming the module as a swappable default that a
  downstream adopter may replace without touching the skill.
- Put the shape rule in `AGENTS.md` near the existing "How a skill is structured" section, which is
  where an author would look. Keep it to a few sentences; it is a convention, not a specification.
- `AGENTS.md` is a human-owned contract document, so `doc-sync` would never edit it on its own. This
  task edits it deliberately, on an explicit decision recorded on 2026-07-25.
- **Depended on `feat-0022`** (which edits `fix-batch` and `reconcile-worktrees`) and **`chore-0010`**
  (which edits `spec-plan-readiness`). Both are now in `.tasks/done/`, so this is unblocked. Note that
  the 2026-07-27 pass also edited `fix-batch`, `reconcile-worktrees`, and `new-task`, so re-read those
  three before editing rather than working from this task's original picture of them.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] Every skill under `.agents/skills/` contains at least one reference to `house-style`.
- [x] `AGENTS.md` documents both skill shapes and when each applies.
- [x] `init-worktracking` and `new-task` point at the **target repo's** conventions rather than
      instructing an agent to impose this kit's house style on a scaffolded repository.
- [x] No skill outside the seven listed in `touched_files` is modified.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings (it now also
      fails on unresolved links, so any new relative link must resolve).
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `feat-0022` and `chore-0010` confirmed in `.tasks/done/` before starting.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.

## Outcome (2026-07-27)

All 19 skills now reference the house-style module, and `AGENTS.md` documents both body shapes.

**This task's own premise was wrong, and the work corrected it.** The implementation notes above say
"two of the six need different wording", naming `init-worktracking` and `new-task`. Checking each of
the six against its actual text found **four**:

| Skill | Why it is target-repo-facing |
|---|---|
| `init-worktracking` | scaffolds into a target repo; already warns against importing another project's voice |
| `new-task` | writes task files an agent in that repo executes; already says "do not import another project's style" |
| `pr-describe` | its Notes already say "Do not hardcode this kit's own conventions into another repo" |
| `fix-batch` | dispatches prompts that point agents at the target repo's `AGENTS.md` |

`pr-describe` is the sharpest case: pasting the standard paragraph into it would have directly
contradicted a rule already stated in its own body, which is precisely the regression the task warned
about while under-counting the skills it applied to. Only `reconcile-worktrees` and
`spec-plan-readiness` were clean cases for the standard wording.

This is the `new-task` rule added on 2026-07-27 ("verify any claim you make *about* the code before
writing it into the task") failing against its own author, on a task filed two days before that rule
existed. The premise was written from a plausible reading rather than a check.

Each of the four now states **which conventions govern what**: the artifact written into the target
repository follows that repository's conventions, and the skill's own report follows the house-style
module. `AGENTS.md` records that split as the general rule, so skill number 20 does not have to
rediscover it.
