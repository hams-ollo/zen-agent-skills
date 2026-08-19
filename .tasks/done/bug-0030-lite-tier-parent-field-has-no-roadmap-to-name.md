---
id: bug-0030
title: The lite tier scaffolds a required parent field pointing at a ROADMAP the tier does not ship
type: bug
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0029]
touched_files:
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl
  - .agents/skills/new-task/SKILL.md
created: 2026-08-18
---

## Problem

At the **lite** tier, [`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) ships
`AGENTS.md`, `.tasks/` and a `CLAUDE.md` pointer, and deliberately no `ROADMAP.md` and no
`CHANGELOG.md`. Four things then disagree:

- `_TEMPLATE.md.tmpl` seeds `parent: "ROADMAP#N feature-slug"`.
- `parent` is a **required** field in the validator that ships alongside it, so it cannot simply be
  left blank.
- [`new-task`](../../.agents/skills/new-task/SKILL.md) demands "a real `parent`: the ROADMAP Feature/Epic
  it serves", and its Step 4 instructs the agent, when no Feature fits, to "draft a one-line Feature to
  add to `ROADMAP.md`".
- `new-task` never mentions the tier at all. `grep -c "tier"` over its body returns `0`.

So an adopter who scaffolds at lite and then uses `new-task`, which is the pairing
`init-worktracking`'s own closing section recommends, is instructed to write a Feature into a file the
tier decided not to create, and told the field is required either way.

`init-worktracking` already has a "Tier stripping at lite" section whose stated reason covers this
exactly: "a scaffold whose own files link to things that do not exist is worse than a smaller
scaffold". It lists the three files needing ROADMAP references struck. `_TEMPLATE.md.tmpl` is not one
of them, and it is the file every task in the adopter's repository is copied from.

## Scope

**In scope:** make `parent` answerable at lite. Two parts:

- Decide what a lite `parent` names, and say so in `_TEMPLATE.md.tmpl` and in the tier-stripping
  section. The natural answer is a free-text intent line rather than a `ROADMAP#N` reference, since the
  field's stated purpose is that "intent is traceable without reading the roadmap", which does not
  require a roadmap to exist.
- Teach `new-task` that the tier exists: when there is no `ROADMAP.md`, do not offer to add a Feature
  to one, and accept the tier's `parent` form.

**Out of scope:**

- Making `parent` optional in the validator. The field is load-bearing at every tier and
  `spec-plan-readiness` reads it; weakening the schema to fit one tier is the wrong direction and
  should be rejected explicitly rather than left unsaid.
- The `external` and `## Decisions` gaps in the same template, which are
  [`bug-0029`](bug-0029-shipped-task-template-lost-decisions-and-external.md). This task depends on it
  because they edit the same file.
- The lite tier's contents. Whether lite should ship a `ROADMAP.md` after all is a product question,
  and the answer this task assumes is no, because the tier exists precisely to avoid the ceremony.
- `new-task`'s spec-decomposition half, which is tier-independent.

## Implementation notes

Do not add a fourth tier or a new frontmatter field. The cheapest correct change is a sentence in the
template's `parent` comment giving both forms, plus one bullet in the tier-stripping list, plus one
conditional in `new-task` Step 4.

`new-task`'s existing Step 1 is the model for how to phrase the tier check: it already confirms
`.tasks/` exists and stops with a pointer when it does not, so confirming `ROADMAP.md` exists in the
same step costs nothing and keeps the two checks together.

Keep the tier-stripping section's reason intact when adding to its list. That reason is the argument
for this change and a later reader needs it more than the list.

## Decisions

- **Chosen: `parent` keeps a required field at every tier, and its *form* follows the tier.** With a
  `ROADMAP.md`, it names the Feature or Epic; at lite it is one line of free text naming the goal.
  The field's stated purpose is that intent be readable without the roadmap, which never required a
  roadmap to exist, so this costs the schema nothing and only makes the seed honest. The real cost is
  that `parent` values are no longer uniform across tiers, so anything that later wants to *parse*
  `parent` rather than read it has two shapes to handle. Accepted: nothing parses it today (the
  shipped validator checks presence only, not format), and a consumer that needs structure should
  read `spec`/`scenarios`, which exist for exactly that.

- **Rejected: make `parent` optional when there is no `ROADMAP.md`.** Named out of scope by this task
  and rejected here explicitly rather than by silence. An optional field is answered by nobody: the
  lite tier is where the roadmap altitude is missing, so it is the tier that most needs each task to
  say what it serves. Weakening the schema to fit the smallest tier would also split the shipped
  validator's contract by tier, which is the one thing that ships identically everywhere.

- **Rejected: leave the `ROADMAP#N` seed alone and fix this in prose only.** Cheapest diff, wrong
  place. The seed is the line every task in the adopter's repository is copied from, so prose in a
  skill body loses to a placeholder in a template every time. Prose was kept as well, not instead.

- **Rejected: ship a `ROADMAP.md` at lite after all.** Out of scope by the task, and it inverts the
  tier's reason for existing.

- **Seam left open deliberately: no permanent test was added.** `touched_files` names no test file,
  and `tests/test_tasks_validate.py` is the drift-test module other tasks in this wave are likely to
  be editing, so writing into it from an isolated worktree trades a real merge conflict for a small
  assurance gain. Acceptance criterion 4 was verified by running the shipped template validator over
  a lite-stripped, filled-in copy of `_TEMPLATE.md.tmpl` in a scratch directory (exit 0, 0 errors, 0
  warnings). A permanent `ScaffoldedTaskTemplateTests` case pinning the lite `parent` form is the
  natural follow-up.

## Risks and rollback

Touches two skill bodies and a template, so it meets the more-than-one-module rule. The failure mode to
avoid is teaching `new-task` a tier check that fires in this repository, which does have a `ROADMAP.md`
and where the ROADMAP parent form is correct; verify by authoring one task file here after the change
and confirming the parent still resolves to a real Feature.

Reversible by reverting one commit. Nothing already scaffolded changes until its owner re-runs
`init-worktracking`.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict && python scripts/run-checks.py

- [x] `_TEMPLATE.md.tmpl`'s `parent` comment names both an at-lite form and a with-ROADMAP form.
- [x] The "Tier stripping at lite" list includes `_TEMPLATE.md.tmpl` and says what to strike.
- [x] `new-task` names the tier: with no `ROADMAP.md` present it does not offer to add a Feature to
      one, and it accepts the lite `parent` form.
- [x] A task file authored against the lite form passes the shipped validator.
- [x] A task file authored in this repository still uses and resolves a ROADMAP parent, unchanged.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
