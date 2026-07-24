---
id: feat-0006
title: Fold the reconcile-worktrees skill into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Current state: fold in the parallel-execution back half"
depends_on: []
touched_files:
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-07-24
---

## Problem

`reconcile-worktrees` (safely consolidate verified worktrees into the main working tree without
committing or merging blindly) is the natural downstream of `fix-batch` and the closing move of
the parallel-execution back half. It exists and is battle-tested at
`~/.claude/skills/reconcile-worktrees/SKILL.md` but is not yet a first-class kit skill: it uses
em-dashes and refers to work tracking only generically rather than to the kit's `.tasks/` system.
Unlike `fix-batch`, its procedure is plain git and needs little harness gating, but it should
still name the kit's spine and conventions.

## Scope

**In scope:** port `~/.claude/skills/reconcile-worktrees/SKILL.md` into
`.agents/skills/reconcile-worktrees/SKILL.md`, adapted to kit conventions: house style (no
em-dashes), integration with the kit's `.tasks/` spine (it consolidates worktrees produced by
`fix-batch`, normalizes task-file/CHANGELOG bookkeeping into one consistent state, references
`validate.py`), and any harness-specific mechanics (e.g. resuming an agent) gated in a labeled
Claude Code section if present. Land as a draft; blessing waits for the live in-kit run.

**Out of scope:** blessing the skill; the live run; `fix-batch` (`feat-0005`); `code-review`;
changing the source skill in `~/.claude/skills`.

## Implementation notes

- Preserve the incident-driven "why", the untracked-file and binary/LFS phantom-diff traps, the
  overlap check, the one-worktree-at-a-time application, and the never-auto-commit rule (the
  core value).
- Its git procedure is portable as-is; keep it harness-agnostic. Gate only genuinely
  harness-specific steps (if any) behind a labeled section.
- State the spine position: `new-task` -> `fix-batch` -> `reconcile-worktrees`.
- Keep the body under the 500-line guideline (source is ~63 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/reconcile-worktrees/SKILL.md` exists with valid frontmatter (`name`
      matches directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body contains no em-dashes.
- [ ] Body is under the 500-line progressive-disclosure guideline.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending live run), not shipped.
