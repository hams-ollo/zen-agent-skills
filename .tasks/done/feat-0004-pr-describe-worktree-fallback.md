---
id: feat-0004
title: Iterate pr-describe to handle the uncommitted working-tree case
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #2 pr-describe"
depends_on: [feat-0003]
touched_files:
  - .agents/skills/pr-describe/SKILL.md
created: 2026-07-24
---

## Problem

Field-dogfooding `pr-describe` against this repo's own working tree exposed a dead-end. The
draft (`feat-0003`) computes the changeset as the committed range `<base>..HEAD` and, if that
range is empty, reports "nothing to describe" and stops. But on `main` (or any time the work
is not yet committed to a feature branch ahead of base), `HEAD` equals the merge-base, so the
range is empty even though a full changeset sits in the working tree. This is the common
"still on main / haven't branched yet / changes uncommitted" case, and the skill dead-ends on
exactly the changeset the user wants described.

## Scope

**In scope:** refine `pr-describe`'s Step 1 so that when the committed range is empty it falls
back to describing the working-tree changes (tracked `git diff HEAD` plus untracked
`git ls-files --others --exclude-standard`); document the fallback in the design choices; note
that intent must come from `.tasks/` files, the branch name, or the user when no commits exist
in range.

**Out of scope:** any GitHub side-effect; staged-only or last-commit ranges as new defaults
(the default stays branch-vs-merge-base, with the working-tree fallback); other skills.

## Implementation notes

- Choose the changeset: branch ahead of base -> committed range (note and offer to fold in any
  uncommitted changes); range empty -> working-tree changes; both empty -> genuinely nothing,
  stop. On the default branch, mention the work is not on a feature branch yet but still
  produce the description.
- `git log --oneline <base>..HEAD` only supplies intent when commits exist; for an uncommitted
  changeset there are no commit messages, so draw intent from matching `.tasks/` files, the
  branch name, or the user.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `pr-describe/SKILL.md` Step 1 describes the working-tree fallback and the both-empty stop.
- [ ] The design-choices section notes the fallback alongside the branch-vs-merge-base default.
- [ ] `scripts/validate-skills.py` exits 0; body stays under the 500-line guideline.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
