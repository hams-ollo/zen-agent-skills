---
id: feat-0008
title: Make path-scoped whole-file review first-class in code-review
type: feat
status: done
priority: P2
parent: "ROADMAP Epic A #3 code-review"
depends_on: [feat-0007]
touched_files:
  - .agents/skills/code-review/SKILL.md
created: 2026-07-24
---

## Problem

Dogfooding `code-review` on the kit's Python scripts (a "review these files" request with no diff)
showed that its Step 1 is written diff-first: the branch-vs-merge-base range is the star, and a
path scope over existing files is only a parenthetical afterthought. Reviewing named files as they
stand is a common ask and the skill under-specifies it, the same shape of gap that `pr-describe`'s
working-tree fallback closed.

## Scope

**In scope:** revise `code-review`'s Step 1 (and a line in the design choices) so path-scoped,
whole-file review is a first-class mode: when the user names files or paths without a change to
review, review those files as they stand, applying the same `review-quality` lens. Keep the
change-review (range) path as the default when no scope is given.

**Out of scope:** the script fixes (`bug-0001`); any new lens; a multi-lens deep-review.

## Implementation notes

- Step 1 should branch clearly: (a) user named files/paths, review those files whole; (b) otherwise
  use the branch-vs-merge-base range with the working-tree fallback (unchanged).
- Reused across the kit: this mirrors `pr-describe`'s changeset logic for the range path; only the
  explicit-scope branch is new.
- Keep the body under the 500-line guideline; no em-dashes.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `code-review/SKILL.md` Step 1 describes whole-file review for an explicit path scope as a
      first-class branch, not a parenthetical.
- [ ] `scripts/validate-skills.py` exits 0; body under the guideline; no em-dashes.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated `CHANGELOG.md` line referencing this id.
