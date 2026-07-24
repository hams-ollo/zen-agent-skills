---
id: feat-0001
title: Draft the first version of the project-bootstrap skill
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #1 project-bootstrap"
depends_on: []
touched_files:
  - .agents/skills/project-bootstrap/SKILL.md
created: 2026-07-23
---

## Problem

The kit has a work-tracking scaffold (`init-worktracking`) and a task authoring skill (`new-task`), but no umbrella "fire up my harness" entry point. `project-bootstrap` is meant to be the front door: given a new or bare repository, it lays down the standard baseline (gitignore, editorconfig, linter/formatter config, license, README stub) matched to the detected stack, then calls `init-worktracking` to add work tracking. Without it, a user adopting the kit still has to assemble a project baseline by hand before the tracking system is useful.

## Scope

**In scope:** author `.agents/skills/project-bootstrap/SKILL.md` as a harness-agnostic, agent-executed procedure that detects the stack, generates the baseline files without clobbering, and hands off to `init-worktracking`. First draft only.

**Out of scope:** a large per-language template library (the procedure generates configs contextually or points at canonical defaults); actually shipping/blessing the skill (it stays a draft in `ROADMAP.md` until iterated on real projects); building `pr-describe`, `code-review`, or any later skill.

## Implementation notes

- Mirror the shape and rigor of the existing `init-worktracking/SKILL.md`: survey first, never clobber, tiered/opinionated choices surfaced to the user, cross-platform.
- The skill should call `init-worktracking` rather than reimplement tracking.
- Support Python and JavaScript/TypeScript as the first-class detected stacks; degrade gracefully (a clearly marked TODO) for others.
- Frontmatter `description` must be pushy and say both what and when, so `validate-skills.py` passes and the skill triggers reliably.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/project-bootstrap/SKILL.md` exists with valid frontmatter (`name` matches directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body is under the 500-line progressive-disclosure guideline.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
