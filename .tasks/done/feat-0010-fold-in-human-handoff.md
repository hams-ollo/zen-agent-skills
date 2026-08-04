---
id: feat-0010
title: Fold the human-handoff skill into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #7: fold in agent-handoff / human-handoff"
depends_on: []
touched_files:
  - .agents/skills/human-handoff/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic A item 7 folds in `agent-handoff` / `human-handoff`, already portable by design.
`human-handoff` packages project state for a person (partner, client, or teammate) as a tuned
document or message, with client-facing redaction. It already exists and is battle-tested at
`D:\zen-solutions-studio\agents\skills\human-handoff\SKILL.md` (pure prose, no
harness-specific tool machinery), and is the human-reader counterpart to `agent-handoff`
(`feat-0009`). It is not yet a first-class kit skill.

## Scope

**In scope:** copy `D:\zen-solutions-studio\agents\skills\human-handoff\SKILL.md` into
`.agents/skills/human-handoff/SKILL.md`, adapted with light kit-reference tightening only:
point the inline "no em-dashes" convention default at the kit's swappable module
[`.agents/rules/house-style.md`](../../.agents/rules/house-style.md) while keeping the portable intent,
and make the existing mention of `agent-handoff` a clickable sibling link. Land as a draft;
blessing waits for a real in-kit dogfood use (a partner-style status update of the kit) plus
user sign-off.

**Out of scope:** blessing the skill; any portability gating or "Running this in Claude Code"
section (this skill has no tool machinery); porting `agent-handoff` (`feat-0009`) or the doc
skills (`feat-0011`/`feat-0012`); changing anything in `D:\zen-solutions-studio`.

## Implementation notes

- Preserve the body verbatim except the two tightening edits above; the source is already
  house-styled (em-dash clean, sentence-case) and already references `AGENTS.md`.
- Keep the body well under the 500-line progressive-disclosure guideline (source is ~60 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/human-handoff/SKILL.md` exists with valid frontmatter (`name` matches
      directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body contains no em-dashes and points the house-style default at
      `.agents/rules/house-style.md`.
- [ ] Body links `agent-handoff` as a clickable sibling reference.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
