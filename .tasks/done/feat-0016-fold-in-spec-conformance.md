---
id: feat-0016
title: Fold the spec-conformance lens into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #6: spec-conformance"
depends_on: []
touched_files:
  - .agents/skills/spec-conformance/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 6 is `spec-conformance`: an audit of every approved scenario and
public-surface element against code and test evidence, producing a positive conformance matrix
of `Conformed`, `Diverged`, or `Not-built` items plus an explicit unreconciled set. It reports,
never repairs. A finished, standalone source exists in the vendored upstream at
`repoprompt-workflows-main/.agents/skills/spec-conformance/SKILL.md`
(moonray's RepoPrompt Workflows, MIT, by Balarama Bosch). It is a report-only lens with no
harness-specific machinery. It is not yet a first-class kit skill.

## Scope

**In scope:** create `.agents/skills/spec-conformance/SKILL.md` by porting the upstream source
and adapting it to the kit:

1. Adapt to house style ([`.agents/rules/house-style.md`](../../.agents/rules/house-style.md)):
   remove every em-dash, convert Title-Case headings to sentence case, keep sources named, use
   relative markdown links.
2. Keep `name: spec-conformance` matching the directory; keep the `description` concise and
   distinct from the other `spec-*` skills by role word ("spec-vs-implementation audit", vs
   `spec-quality` well-formedness and `doc-sync` doc-drift).
3. Add a clickable cross-link noting that `verifier-agent` (a planned kit skill) composes this
   lens, and that this lens is the report-only half of the kit's independent verification: it is
   meant to compose into `fix-batch`'s existing verification pass, not to duplicate it. State that
   boundary in one sentence so the folded skill does not read as a competing verifier.
4. Add the one-line provenance note: "Adapted from repoprompt-workflows (Balarama Bosch), MIT."
5. Preserve the skill's logic, matrix format, and coverage-proof rules verbatim except the edits
   above.

**Out of scope:** blessing the skill; editing `ROADMAP.md`, `docs/CATALOG.md`, `NOTICE`, or the
`fix-batch` SKILL.md (the compose-into-fix-batch wiring is a Phase-2 `verifier-agent` concern, not
this fold-in); porting the other Phase-1 lenses; authoring `verifier-agent`; changing anything
under `repoprompt-workflows-main/`.

## Implementation notes

- Harness-agnostic; no portability section needed. The upstream writes
  `docs/spec/<spec>.conformance.md`; keep that as the default output path but phrase it as a
  convention, not a hard requirement, so repos without `docs/spec/` are not blocked.
- Keep the body under the 500-line guideline (source is ~44 lines; this is the smallest fold-in).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/spec-conformance/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body contains no em-dashes and all headings are sentence case.
- [x] Body carries the provenance note, a `verifier-agent` cross-link, and the one-sentence
      "composes into fix-batch verification, does not duplicate it" boundary.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft (orchestrator marks ROADMAP/CATALOG draft post-reconcile), not shipped.
