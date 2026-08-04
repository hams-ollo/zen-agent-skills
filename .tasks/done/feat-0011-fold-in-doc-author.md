---
id: feat-0011
title: Fold the doc-author skill into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #6: fold in doc-author / doc-revise"
depends_on: []
touched_files:
  - .agents/skills/doc-author/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic A item 6 folds in `doc-author` / `doc-revise` from `zen-solutions-studio` once
confirmed portable. `doc-author` writes new, code-grounded Markdown documentation (READMEs,
architecture docs with Mermaid, setup/deploy guides, ADRs) matched to a reader, and can
bootstrap a fresh repo's baseline doc set. It already exists at
`~/.claude/skills/doc-author/SKILL.md` (byte-identical to the `zen-solutions-studio` copy,
verified 2026-07-24), already defers to `init-worktracking` for tracking, and is pure prose
with no harness-specific tool machinery. It is not yet a first-class kit skill.

## Scope

**In scope:** copy `~/.claude/skills/doc-author/SKILL.md` into
`.agents/skills/doc-author/SKILL.md`, adapted with light kit-reference tightening only: point
the inline "no em-dashes" convention default at the kit's swappable module
[`.agents/rules/house-style.md`](../../.agents/rules/house-style.md) while keeping the portable intent;
make the existing mention of `doc-revise` a clickable sibling link; and in the bootstrap
section, link `init-worktracking` and add a pointer to `project-bootstrap` as the umbrella
front door this skill composes with. Land as a draft; blessing waits for a real in-kit dogfood
use (authoring `docs/ARCHITECTURE.md`) plus user sign-off.

**Out of scope:** blessing the skill; any portability gating or "Running this in Claude Code"
section (this skill has no tool machinery); porting `doc-revise` (`feat-0012`) or the handoff
skills (`feat-0009`/`feat-0010`); changing the source skill in `~/.claude/skills` or anything
in `D:\zen-solutions-studio`.

## Implementation notes

- Preserve the body verbatim except the tightening edits above; the source is already
  house-styled (em-dash clean, sentence-case) and already references `AGENTS.md`/`CLAUDE.md`.
- Keep the body well under the 500-line progressive-disclosure guideline (source is ~55 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/doc-author/SKILL.md` exists with valid frontmatter (`name` matches
      directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body contains no em-dashes and points the house-style default at
      `.agents/rules/house-style.md`.
- [ ] Body links `doc-revise` and `project-bootstrap` as clickable sibling references.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
