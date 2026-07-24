---
id: feat-0005
title: Fold the fix-batch skill into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Current state: fold in the parallel-execution back half"
depends_on: []
touched_files:
  - .agents/skills/fix-batch/SKILL.md
created: 2026-07-24
---

## Problem

The kit's work spine ends at `pr-describe`, but the parallel-execution back half is missing.
`fix-batch` (dispatch independent task files to parallel worktree-isolated agents, then a
mandatory verification pass) already exists and is battle-tested at
`~/.claude/skills/fix-batch/SKILL.md`, born from a real 2026-07-07 multi-agent incident. It is
not yet a first-class kit skill: it uses em-dashes (against house style), hardcodes
Claude-Code-specific tool mechanics in its body (against the portability contract), and refers
to work tracking only generically rather than to the kit's `.tasks/` system.

## Scope

**In scope:** port `~/.claude/skills/fix-batch/SKILL.md` into
`.agents/skills/fix-batch/SKILL.md`, adapted to kit conventions: house style (no em-dashes),
portability gating (harness-agnostic body plus a labeled Claude Code section for the concrete
`Agent`/`isolation`/`SendMessage`/`run_in_background` mechanics), and integration with the
kit's `.tasks/` spine (`new-task` upstream, the `open -> in_progress -> done` lifecycle,
`validate.py`, CHANGELOG discipline, the AGENTS.md section 0 reading protocol). Land as a
draft; blessing waits for a live in-kit run (`feat` in Phase A2).

**Out of scope:** blessing the skill; the live parallel run; reconcile-worktrees (`feat-0006`);
building `code-review`; changing the source skill in `~/.claude/skills`.

## Implementation notes

- Preserve the incident-driven "why", the mandatory verification pass (the core value), the
  untracked-file and binary/LFS traps, and the independence precondition.
- Move the concrete tool mechanics into a `## Running this in Claude Code` optional section;
  the body must read correctly for a harness that has no such tools.
- State the spine position: `new-task` -> `fix-batch` -> `reconcile-worktrees`.
- Keep the body under the 500-line guideline (source is ~75 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/fix-batch/SKILL.md` exists with valid frontmatter (`name` matches
      directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body contains no em-dashes and a clearly-labeled Claude Code gated section.
- [ ] Body is under the 500-line progressive-disclosure guideline.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending live run), not shipped.
