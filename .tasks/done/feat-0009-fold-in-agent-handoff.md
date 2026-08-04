---
id: feat-0009
title: Fold the agent-handoff skill into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #7: fold in agent-handoff / human-handoff"
depends_on: []
touched_files:
  - .agents/skills/agent-handoff/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic A item 7 folds in `agent-handoff` / `human-handoff`, already portable by design.
`agent-handoff` turns the current session's context into a self-contained, execution-ready
brief a fresh session or subagent can run cold. It already exists and is battle-tested at
`~/.claude/skills/agent-handoff/SKILL.md` (byte-identical to the `zen-solutions-studio` copy,
verified 2026-07-24), and it produced the very handoff brief that scoped this fold-in work. It
is not yet a first-class kit skill. Unlike `fix-batch`, it is pure prose with no
harness-specific tool machinery, so this is the lightest possible port.

## Scope

**In scope:** copy `~/.claude/skills/agent-handoff/SKILL.md` into
`.agents/skills/agent-handoff/SKILL.md`, adapted with light kit-reference tightening only:
point the inline "no em-dashes" convention default at the kit's swappable module
[`.agents/rules/house-style.md`](../../.agents/rules/house-style.md) while keeping the portable intent
(a scaffolded target repo's own `AGENTS.md`/house-style still governs there), and make the
existing mention of `human-handoff` a clickable sibling link. Land as a draft; blessing waits
for its dogfood use (already satisfied by producing this fold-in's handoff brief) plus user
sign-off.

**Out of scope:** blessing the skill; any portability gating or "Running this in Claude Code"
section (this skill has no tool machinery); porting `human-handoff` (`feat-0010`) or the
doc skills (`feat-0011`/`feat-0012`); changing the source skill in `~/.claude/skills` or
anything in `D:\zen-solutions-studio`.

## Implementation notes

- Preserve the body verbatim except the two tightening edits above; the source is already
  house-styled (em-dash clean, sentence-case) and already references `AGENTS.md`/`.tasks/`.
- Keep the body well under the 500-line progressive-disclosure guideline (source is ~90 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/agent-handoff/SKILL.md` exists with valid frontmatter (`name` matches
      directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body contains no em-dashes and points the house-style default at
      `.agents/rules/house-style.md`.
- [ ] Body links `human-handoff` as a clickable sibling reference.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
