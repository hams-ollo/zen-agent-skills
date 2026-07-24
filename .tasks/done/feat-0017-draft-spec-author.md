---
id: feat-0017
title: Draft the spec-author skill (composes spec-quality, from its own spec)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #2: spec-author"
depends_on: []
touched_files:
  - .agents/skills/spec-author/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 2 is `spec-author`: draft a persistent, executable spec from a raw idea before
task decomposition. The blessed `spec-quality` lens reviews specs but nothing drafts them; the spine
has a lens and no author. The behavioral contract is already written and passes `spec-quality` at
[`docs/spec/spec-author.md`](../docs/spec/spec-author.md), and `spec-plan-readiness` gated this build
as `implementable` with this task as the first safe task. The drafting discipline exists upstream
only inside the RPCE Spec workflow (gitignored `repoprompt-workflows-main/.agents/workflows/Spec.md`),
so it must be extracted into a portable `SKILL.md`, not folded in.

## Scope

**In scope:** author `.agents/skills/spec-author/SKILL.md`, harness-agnostic, delivering scenarios
S-001, S-002, S-004, and S-005 of the spec: draft the seven-section spec with stable `S-NNN`
scenario ids and frontmatter `status: draft`; compose the [`spec-quality`](../.agents/skills/spec-quality/SKILL.md)
lens to self-check and revise until its verdict is `ready` (do not restate the lens's rules inline);
keep the run read-only for implementation surfaces (write only the spec file); ask exactly one
clarifying question when the idea is too vague to yield an observable contract. Cross-link
`spec-quality` and `new-task`. Mark it a draft in `ROADMAP.md`/`docs/CATALOG.md`.

**Out of scope:** scenario S-003 (the `new-task` approval gate) — that edits `new-task` and is a
separate task (`feat-0018`, `depends_on: feat-0017`); blessing this skill (waits for a real dogfood,
writing the spec for `test-author`); implementing any spec; changing `spec-quality` or the spec file.

## Implementation notes

- Extract the durable discipline from the upstream Spec workflow; leave RPCE-only sequencing and
  index-file mechanics behind. No "Running this in Claude Code" section is needed (pure prose).
- The spec format and the `status` field semantics are fixed by `docs/spec/spec-author.md`
  Constraints and Proposed Surface; mirror them exactly. `spec-author` never sets `status: approved`.
- Keep the body under the 500-line progressive-disclosure guideline and follow
  [`.agents/rules/house-style.md`](../.agents/rules/house-style.md).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/spec-author/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body composes `spec-quality` by reference (no inline restatement of its checks) and cross-links
      `spec-quality` and `new-task`.
- [x] Body states the read-only rule, the one-clarifying-question behavior, and that a human, not the
      skill, sets `status: approved`.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
