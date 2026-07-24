---
title: spec-author
status: draft
---

# spec-author

Behavioral contract for the planned `spec-author` skill (ROADMAP Epic B item 2). Drafted 2026-07-24
and reviewed with the `spec-quality` lens as the first in-kit dogfood of that skill.

## Problem

The kit can turn a rough idea into atomic task files with [`new-task`](../../.agents/skills/new-task/SKILL.md),
and it now has a [`spec-quality`](../../.agents/skills/spec-quality/SKILL.md) lens for reviewing
scenario-based specs. But nothing drafts the spec in the first place. Ideas jump straight to tasks
with no durable behavioral contract, so intent is not captured before decomposition and there is
nothing for `spec-quality` or a later conformance audit to check against. The contract-driven spine
has a lens but no author.

## Goals

1. Draft a persistent spec document from a raw idea, capturing problem, goals, non-goals,
   constraints, scenarios, proposed surface, and open questions.
2. Compose the `spec-quality` lens so the returned draft has a `spec-quality` verdict of `ready`.
3. Represent an explicit human approval state that downstream decomposition can gate on.

## Non-Goals

- Decomposing the spec into task files. That is `new-task`.
- Writing implementation code, tests, or architecture.
- Choosing implementation strategy or file layout.

## Constraints

- Specs are Markdown with YAML frontmatter and live under `docs/spec/<slug>.md`.
- The skill composes `spec-quality` rather than restating its rules inline.
- Specification work is read-only for implementation surfaces: a run creates or edits only the spec
  file, never implementation source.
- Frontmatter carries a `status` field whose value is one of `draft` or `approved`. `approved` is
  set only by a human; `spec-author` never sets `approved` itself.

## Scenarios

### Scenario S-001: draft from a raw idea

- **Given** a one-line feature idea and no existing spec
- **When** spec-author runs
- **Then** it writes a Markdown file at `docs/spec/<slug>.md` containing frontmatter with
  `status: draft` and all seven body sections (Problem, Goals, Non-Goals, Constraints, Scenarios,
  Proposed Surface, Open Questions), with at least one scenario carrying a stable `S-NNN` id.

### Scenario S-002: self-check with spec-quality

- **Given** a drafted spec that a first pass of the `spec-quality` lens would return as
  `needs_revision`
- **When** spec-author finishes drafting
- **Then** it revises the draft and re-checks until the `spec-quality` verdict is `ready`, and the
  file it writes is the `ready` version.

### Scenario S-003: approval gate before decomposition

- **Given** a spec whose frontmatter `status` is `draft`
- **When** `new-task` is asked to decompose it
- **Then** `new-task` refuses and reports that the spec is not `approved`.

### Scenario S-004: read-only for implementation surfaces

- **Given** any drafting run
- **When** spec-author completes
- **Then** the only file created or modified is the spec under `docs/spec/`, and no implementation
  source file is written.

### Scenario S-005: vague idea triggers one clarifying question

- **Given** an idea too vague to yield an observable contract (no discernible behavior change)
- **When** spec-author runs
- **Then** it asks the user exactly one clarifying question and writes no file until the answer
  arrives.

## Proposed Surface

| Element | Detail |
|---|---|
| Output file | `docs/spec/<slug>.md`, Markdown with YAML frontmatter |
| Frontmatter `status` | `draft` (author-set) or `approved` (human-set only) |
| Body sections | Problem, Goals, Non-Goals, Constraints, Scenarios, Proposed Surface, Open Questions |
| Scenario ids | stable `S-NNN`, never renumbered |

## Open Questions

None.
