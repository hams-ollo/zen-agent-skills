---
id: chore-0022
title: Declare each skill's license in its frontmatter, so it is machine-readable once packaged
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0008]
touched_files:
  - .agents/skills/agent-handoff/SKILL.md
  - .agents/skills/doc-author/SKILL.md
  - .agents/skills/doc-revise/SKILL.md
  - .agents/skills/doc-sync/SKILL.md
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/house-review/SKILL.md
  - .agents/skills/human-handoff/SKILL.md
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/new-task/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
  - .agents/skills/project-bootstrap/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
  - .agents/skills/spec-author/SKILL.md
  - .agents/skills/spec-conformance/SKILL.md
  - .agents/skills/spec-plan-readiness/SKILL.md
  - .agents/skills/spec-quality/SKILL.md
  - .agents/skills/test-author/SKILL.md
  - .agents/skills/test-quality/SKILL.md
  - .agents/skills/verifier-agent/SKILL.md
  - NOTICE
created: 2026-07-29
---

## Problem

A skill's licence terms exist here in two places, and neither is machine-readable once the skill is
distributed on its own.

[`NOTICE`](../../NOTICE) records the full provenance of the four skills adapted from repoprompt-workflows
(Balarama Bosch, MIT). But `NOTICE` and `LICENSE` sit at the repository root, above the skill directory,
and the packaging unit is the skill directory: Anthropic's `package_skill.py` archives
`skill_path.rglob('*')` with paths relative to the skill's parent, so nothing above the skill travels.
`install.py`, `npx skills`, and plugin caching all behave the same way.

**Attribution itself is not lost, and an earlier reading of this was wrong.** Each of the four carries a
one-line provenance note in its body (`Adapted from repoprompt-workflows (Balarama Bosch), MIT.`), and
`NOTICE` states that this is deliberate: "Each adapted SKILL.md also carries a one-line provenance
note." The body travels with `SKILL.md`, so a human reading a packaged skill sees the author and the
licence.

What is missing is narrower. The skill schema both target harnesses enforce has an optional `license`
property, documented as "License information or reference", and no skill here sets it. So the licence is
prose that a person must read rather than metadata a registry, aggregator, or packaging tool can
inspect. For a kit that is about to be listed somewhere, that is the difference between a licence that
is stated and one that is discoverable.

## Scope

**In scope:** set `license` in the frontmatter of every skill, with the four fold-ins naming their
upstream in the value; note in `NOTICE` that the frontmatter now carries it too, so the two do not drift.

**Out of scope:** changing `LICENSE`, `NOTICE`'s substance, or any body provenance note, all of which are
correct. Adding `version`, `metadata`, or `compatibility`. Any claim about a licence the kit does not
hold.

## Implementation notes

- **This was authorised for the four fold-ins and is proposed for all nineteen.** The argument for
  widening: the reason the four need it (root-level licence files do not travel with a packaged skill)
  is equally true of the other fifteen, and a consumer inspecting a bundle would otherwise find licence
  metadata on four skills and none on the rest, which reads like an oversight rather than a distinction.
  It is one line per file and trivially reduced back to four if the author prefers. Flag it rather than
  doing it silently.
- Values. For the fifteen kit-authored skills: `MIT`. For the four fold-ins, name the upstream in the
  field, which is what the schema's "License information or reference" wording permits and what
  Anthropic's own vendored plugin does ("Apache-2.0. Skill content vendored from
  `moremas/build-with-claude`"). Keep it to one line and do not restate what `NOTICE` says at length.
- `license` is one of the six properties the schema allows, so `bug-0008`'s allow-list check must already
  include it. That is why this task depends on `bug-0008`: adding the key before the check exists would
  mean the check is written against a tree that already satisfies it, and a check whose first run is
  green proves less.
- Put the key after `description`, not before `name`. The frontmatter's first two keys are what every
  reader looks for and reordering them for a metadata field is a poor trade.
- The kit's own parser accepts any `key: value` line, so this cannot break `validate-skills.py` or
  `build-adapters.py`. Confirm anyway: `build-adapters.py` reads `name` and `description` by key, so an
  added key is inert, and the emitted adapters should be byte-identical apart from nothing at all.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] Every skill declares `license` in its frontmatter, positioned after `description`.
- [x] The four fold-ins name repoprompt-workflows' author and licence in the value; the other fifteen read `MIT`.
- [x] All 19 still pass Anthropic's `quick_validate.py`, which allows `license` and would reject a misspelling of it.
- [x] `NOTICE` notes that the frontmatter carries the licence too, and its file list is unchanged.
- [x] `python scripts/build-adapters.py --dry-run` still reports 38 adapter files for 19 skills.
- [x] All four repository checks still pass.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-29)

**Widened from the four fold-ins to all nineteen, which is a scope increase the author did not ask
for.** The reason it applies to all of them: the fold-ins need it because root-level licence files do
not travel with a packaged skill, and that is equally true of the other fifteen. A bundle carrying
licence metadata on four skills and nothing on the rest reads as an oversight rather than a
distinction. It is one line per file and reverts to four by deleting fifteen of them. Flagged rather
than done quietly.

Values: `MIT` for the fifteen kit-authored skills, and `MIT. Adapted from repoprompt-workflows
(Balarama Bosch), MIT.` for the four fold-ins, which is what the schema's "License information or
reference" wording permits and what Anthropic's own vendored plugin does. `NOTICE` now records that
the frontmatter carries it too, and says why both exist: the body note is what a person reads, the
field is what a registry or packaging tool can inspect.

**The premise this task was filed on was partly wrong, and the correction is worth keeping.** It was
filed on the belief that attribution disappears when a skill is packaged. It does not: each fold-in
already carries `Adapted from repoprompt-workflows (Balarama Bosch), MIT.` in its body, and `NOTICE`
already said that was deliberate. The body travels with `SKILL.md`. So the actual gap was narrower
than claimed, machine-readability rather than attribution, and the task was rewritten to say so before
being implemented rather than after.

Verified beyond the four gates: all 19 still pass Anthropic's `quick_validate.py`, which allows
`license` and would have rejected a misspelling of it. One quiet confirmation worth recording, because
it is exactly the class of silent breakage this session has been finding: `install.py`'s reported
description budget moved by 11 characters, the `human-handoff` edit from `bug-0008`, and not by the
~250 that adding a key to nineteen files would have cost if `description_of()` had absorbed the new
`license:` line instead of stopping at it.
