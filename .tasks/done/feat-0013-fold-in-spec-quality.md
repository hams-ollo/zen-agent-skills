---
id: feat-0013
title: Fold the spec-quality lens into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #1: spec-quality"
depends_on: []
touched_files:
  - .agents/skills/spec-quality/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 1 is `spec-quality`: a reusable quality gate for scenario-based
specifications that keeps contracts observable, non-redundant, grounded in repository context,
traceable through stable scenario IDs, and free of implementation planning. A finished,
standalone source already exists in the vendored upstream at
[`repoprompt-workflows-main/.agents/skills/spec-quality/SKILL.md`](../repoprompt-workflows-main/.agents/skills/spec-quality/SKILL.md)
(moonray's RepoPrompt Workflows, MIT, by Balarama Bosch). It is a report-only lens with no
harness-specific machinery, so this is a fold-in-and-adapt, the same move already proven on
`fix-batch`, `doc-author`, and the handoffs. It is not yet a first-class kit skill.

## Scope

**In scope:** create `.agents/skills/spec-quality/SKILL.md` by porting the upstream source and
adapting it to the kit:

1. Adapt to house style ([`.agents/rules/house-style.md`](../.agents/rules/house-style.md)):
   remove every em-dash (use commas, colons, or parentheses), convert Title-Case headings to
   sentence case, keep sources named, use relative markdown links. The upstream is em-dash-heavy
   and Title-Case, so this is real line-level editing, not a copy.
2. Keep the `name: spec-quality` frontmatter matching the directory; keep the `description`
   concise and trigger-word-front-loaded, and keep it distinct from the `spec-*` family by role
   word ("is a lens" / "well-formedness"), per the upstream distinctness guidance.
3. Add a clickable cross-link noting that `spec-author` (a planned kit skill) composes this lens.
4. Add a one-line provenance note in the body: "Adapted from repoprompt-workflows (Balarama
   Bosch), MIT."
5. Preserve the skill's logic and output format verbatim except the edits above.

**Out of scope:** blessing the skill (waits for a real dogfood use plus user sign-off); editing
`ROADMAP.md`, `docs/CATALOG.md`, or `NOTICE` (the orchestrator marks the skill draft and lists
provenance once, after reconciliation, to keep parallel worktrees collision-free); porting the
other Phase-1 lenses (`feat-0014`/`feat-0015`/`feat-0016`); authoring `spec-author`; changing
anything under `repoprompt-workflows-main/`.

## Implementation notes

- This lens is harness-agnostic; no "Running this in Claude Code" portability section is needed.
  If any `docs/spec/`-specific assumption surfaces, phrase it as a portable default, not a hard
  path requirement.
- Keep the body under the 500-line progressive-disclosure guideline (source is ~176 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/spec-quality/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body contains no em-dashes and all headings are sentence case.
- [x] Body carries the provenance note and a clickable `spec-author` cross-link.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft (orchestrator marks ROADMAP/CATALOG draft post-reconcile), not shipped.
