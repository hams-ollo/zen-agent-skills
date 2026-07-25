---
id: chore-0009
title: Make agent-handoff's description harness-neutral
type: chore
status: done
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .agents/skills/agent-handoff/SKILL.md
created: 2026-07-25
---

## Problem

[`agent-handoff`](../../.agents/skills/agent-handoff/SKILL.md) hardcodes one harness in its frontmatter
`description`, the most visible field in the kit:

> "Turns the current session's context into a self-contained, execution-ready brief that a fresh
> **Claude Code** session or a spawned subagent can run without seeing this conversation."

Its trigger list has the same problem: "prepare this for handoff to some **sonnet** agents". The body
repeats it at line 21, "a downstream **Claude Code** session or subagent".

This contradicts the portability contract in [`AGENTS.md`](../../AGENTS.md), which requires that a
skill's logic not depend on any one tool and that single-harness capability be gated behind a clearly
labeled optional section. Nothing in this skill is actually Claude Code specific: it writes a
Markdown brief. The procedure works for any agent runtime that can be handed a prompt.

The practical cost is triggering. An adopter running Cursor or Codex reads a description naming a
competitor's product and reasonably concludes the skill is not for them.

## Scope

**In scope:** reword the frontmatter `description` and the body's line 21 to describe the target
generically (for example "a fresh agent session or a spawned subagent"), and generalize the "sonnet
agents" trigger phrase. Keep every other trigger phrase, since they are what make the skill fire.

**Out of scope:** restructuring the skill. Its five-section output structure and example skeleton are
good and are not in question. Changing [`human-handoff`](../../.agents/skills/human-handoff/SKILL.md).
Adding a `Running this in Claude Code` gated section, since there is no harness-specific capability
here to gate; if you find one, report it rather than inventing the section.

## Implementation notes

- The `description` must stay above the 40-character floor and keep saying both what the skill does
  and when to use it. It is currently 1115 characters, so length is not a constraint; precision is.
- Keep the literal user phrasings in the trigger list where they are how people actually talk. "hand
  this off to a new session" is harness-neutral already; only the model-name one needs work. A
  generic replacement like "prepare this for handoff to another agent" preserves the trigger without
  naming a vendor.
- Line 21's "a downstream Claude Code session or subagent" is the same fix in the body.
- `validate-skills.py` reads the description as a folded YAML scalar (`>-`). Keep it valid: the
  parser in [`scripts/validate-skills.py`](../../scripts/validate-skills.py) joins continuation lines, so
  do not introduce a bare colon that would break the scalar.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `grep -in "claude code\|sonnet" .agents/skills/agent-handoff/SKILL.md` returns nothing.
- [x] The description still states what the skill does and when to use it, and is above 40 characters.
- [x] The trigger phrase list retains every phrase except the vendor-specific one, which is replaced
      rather than deleted.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
