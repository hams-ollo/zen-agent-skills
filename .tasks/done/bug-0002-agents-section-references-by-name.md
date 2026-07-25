---
id: bug-0002
title: Reference AGENTS.md sections by name, not number (cross-repo portability defect)
type: bug
status: done
priority: P1
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .agents/skills/new-task/SKILL.md
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/spec-plan-readiness/SKILL.md
  - .tasks/_TEMPLATE.md
  - .tasks/README.md
created: 2026-07-25
---

## Problem

Several skills point agents at `AGENTS.md` **by section number**. The numbering is not stable across
repositories, so the same pointer resolves to a different section depending on where the skill runs.
This defeats the kit's central promise that a skill works unchanged in any repo.

The two numberings that exist today:

| | Scaffolded by `init-worktracking` ([`templates/AGENTS.md.tmpl`](../../.agents/skills/init-worktracking/templates/AGENTS.md.tmpl)) | This repository ([`AGENTS.md`](../../AGENTS.md)) |
|---|---|---|
| 0 | Agent reading protocol | Agent reading protocol |
| 1 | Work altitude model | What this repository is |
| 2 | Repository overview | Layout |
| 3 | Technical commands | Work altitude model and lifecycle |
| 4 | Conventions (edit freely) | How a skill is structured |
| 5 | Task lifecycle | Portability contract |
| 6 | Key file map | Conventions |
| 7 | (none) | Contribution bar |

Concrete breakage:

- [`new-task/SKILL.md:29`](../../.agents/skills/new-task/SKILL.md) tells the agent to read "sections 3
  (technical commands), 4 (conventions), and 1 (the altitude model)". Correct in a scaffolded repo,
  wrong here: section 3 here is the altitude model and section 4 is skill structure.
- [`new-task/SKILL.md:50`](../../.agents/skills/new-task/SKILL.md) sources the acceptance command from
  "section 3", and [`:71`](../../.agents/skills/new-task/SKILL.md) sources conventions from "section 4".
  Same split.
- [`spec-plan-readiness/SKILL.md:18`](../../.agents/skills/spec-plan-readiness/SKILL.md) cites "section 3
  (the work-altitude model)". Correct here, wrong in a scaffolded repo, where the altitude model is
  section 1.
- [`fix-batch/SKILL.md:17-18`](../../.agents/skills/fix-batch/SKILL.md) cites "section 0 (the agent
  reading protocol) and section 3 (the task lifecycle)". Section 0 is stable; section 3 is not, and
  the task lifecycle is section 5 in a scaffolded repo.
- [`init-worktracking/SKILL.md:64`](../../.agents/skills/init-worktracking/SKILL.md) and
  [`:141`](../../.agents/skills/init-worktracking/SKILL.md) cite "section 4" for conventions. Correct for
  what it scaffolds, wrong for the repo it lives in.
- [`.tasks/_TEMPLATE.md:40`](../_TEMPLATE.md) carries "Conventions in AGENTS.md section 4 followed" into
  **every task file authored from it**, so the defect propagates into the ledger. `feat-0019` says
  section 4 and `feat-0020` says section 6, and both are defensible readings.
- [`.tasks/README.md:29`](../README.md) cites "section 5" for the task lifecycle. Correct for a
  scaffolded repo, wrong here.

## Scope

**In scope:** replace every `AGENTS.md` section-number reference in the listed files with a
reference to the section **by name** (for example "the conventions section", "the task lifecycle
section", "the agent reading protocol"). Where a number genuinely aids navigation, keep the name as
the primary reference and the number as a parenthetical qualified by which numbering it refers to.
Update both the shipped `.tasks/` files and the `init-worktracking` templates they are generated
from, so a newly scaffolded repo inherits the fix.

**Out of scope:** renumbering or restructuring either `AGENTS.md` or the `AGENTS.md.tmpl` template to
make the two agree. That is a larger decision and would invalidate existing task files. Editing any
task file already in `.tasks/done/`, which is an append-only ledger. Any other change to the six
skills touched.

## Implementation notes

- Section headings are stable text in both numberings; the names are what agents can actually match
  on. Prefer wording that reads naturally if an adopter renumbers or renames again, for example "the
  section of `AGENTS.md` that lists the repo's test commands" over a bare title match.
- `init-worktracking/SKILL.md:64` and `:141` are describing the *scaffolded* template, so their
  "section 4" is correct in context. Reword them to name the section anyway, so the skill does not
  break when an adopter edits their own `AGENTS.md`.
- The `.tasks/_TEMPLATE.md` change is the highest-value one: it stops the defect propagating.
- Do not attempt to retro-fix task files already in `.tasks/done/`.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] `grep -rn "AGENTS.md section [0-9]\|section [0-9] (" .agents/ .tasks/_TEMPLATE.md .tasks/README.md`
      returns no bare number-only references (a number kept as a qualified parenthetical is allowed).
- [x] Each of the eight `touched_files` names its `AGENTS.md` sections by name.
- [x] `.tasks/_TEMPLATE.md` and `templates/_TEMPLATE.md.tmpl` agree with each other.
- [x] `.tasks/README.md` and `templates/tasks-README.md.tmpl` agree with each other.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
