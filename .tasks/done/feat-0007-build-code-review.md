---
id: feat-0007
title: Build the code-review skill with a composable review-quality lens
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #3 code-review"
depends_on: []
touched_files:
  - .agents/rules/review-quality.md
  - .agents/skills/code-review/SKILL.md
created: 2026-07-24
---

## Problem

The kit has no house-style code-review skill (ROADMAP Epic A #3). It is the biggest idea not yet
in the kit: a review with an explicit rubric and severities, built on moonray's composable
quality-lens pattern (`github.com/moonray/repoprompt-workflows`), where a reusable lens is
composed by a review workflow and findings are govern/revalidated before being reported.

## Scope

**In scope:** build two files. (1) `.agents/rules/review-quality.md`, a reusable, swappable
quality lens (rubric categories, severity scheme, and a review protocol that includes validating
each finding before reporting it), mirroring how `house-style.md` is a swappable module. (2)
`.agents/skills/code-review/SKILL.md`, a skill that composes the lens, reuses `pr-describe`'s
changeset logic (branch vs merge-base with the default branch, working-tree fallback) to pick the
review range, and emits a severity-ranked markdown review. First draft.

**Out of scope:** applying or committing fixes (review-only); sibling lenses such as
`test-quality` (defer to `test-author`); a multi-lens "deep-review" orchestration (note as a
future direction); blessing the skill (it stays a draft until dogfooded on real diffs and
iterated with the user).

## Implementation notes

Settled decisions (resolved with the user):

- **Rubric (8 categories):** correctness & bugs; security; error handling & resilience; tests &
  coverage; readability & maintainability; performance (only when it matters); API & interface
  design; docs & comments. Applied only where the diff warrants, so small changes get short reviews.
- **Severity:** `blocker` / `major` / `minor` / `nit`.
- **Output:** report-only, never edits or commits. Each finding carries a concrete suggested fix
  in text; changes are left to the human, `/simplify`, or `fix-batch`.
- **Reference fidelity (moonray):** the lens is a composable review "shot"; findings are
  govern/revalidated (validate each against the actual code before reporting, drop unsubstantiated
  ones) and reconciled with the author. The parallel multi-lens "Deep Review" orchestration is
  noted as a future direction only.

Shape:

- Reuse `pr-describe`'s changeset logic for the review range; state it is distinct from Claude
  Code's built-in `/code-review` command.
- Each finding: severity, `file:line`, the issue, why it matters, and a concrete fix.
- Gate any Claude-specific structured-findings tool (for example `ReportFindings`) behind a
  labeled optional section; the portable default is the markdown report.
- Keep the skill body under the 500-line guideline; push rubric detail into the lens file.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/rules/review-quality.md` and `.agents/skills/code-review/SKILL.md` both exist.
- [ ] `code-review/SKILL.md` has valid frontmatter (`name` matches directory, non-thin
      `description`) and `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] The skill composes the lens, uses the branch-vs-merge-base range with a working-tree
      fallback, and documents report-only behavior and the four settled decisions.
- [ ] Body under the 500-line guideline; no em-dashes in either file.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated `CHANGELOG.md` line referencing this id.
- [ ] Skill left as a draft; ROADMAP/CATALOG still mark `code-review` as planned/draft pending
      dogfooding and user sign-off.
