---
name: agent-handoff
description: >-
  Turns the current session's context into a self-contained, execution-ready brief that a
  fresh Claude Code session or a spawned subagent can run without seeing this conversation.
  Produces a single pasteable block: role and mode, an ordered file reading list, a dated
  statement of what is already proven, phased scope with explicit stop-and-check-in gates,
  and an out-of-scope list. Use this whenever the user wants to move work to another agent
  or a new session and wants the instructions written down first. Trigger on phrases like:
  "draft me a prompt to trigger a new session", "prompt optimized to trigger a new session",
  "craft a prompt I can paste into a new session", "prep this plan for the agents", "hand
  this off to a new session", "prepare this for handoff to some sonnet agents", "write a
  brief the next session can follow", "spin up an agent to do X, write the instructions
  first", or when the user is about to switch models or context windows and wants the work
  captured for a clean run. When the handoff target is a person (partner, client, teammate)
  rather than an agent, use human-handoff instead.
---

# Agent handoff

Write a brief that a downstream Claude Code session or subagent can execute on its own, with no access to the current conversation. The reader is a machine that will act on what you write, so the brief has to be self-contained, unambiguous about what not to touch, and precise about what is already true. When the handoff target is a person rather than an agent, use [`human-handoff`](../human-handoff/SKILL.md) instead.

## Why this shape

A fresh session starts cold. It cannot see what was decided here, what was already tried, or which files matter. Most bad handoffs fail in one of three ways: the agent re-does work that is already done, the agent wanders into files or decisions it should have left alone, or the agent acts on a stale assumption because the brief never pinned down what was actually proven and when. The five sections below exist to close those three gaps. Keep the whole thing tight; a brief the reader will not finish is worse than a short one.

## Before writing: gather the real state

Do not write the brief from memory of the conversation alone. Ground it in the repository as it actually is right now, because that is what the downstream agent will see.

1. If the repo has an `AGENTS.md` or `CLAUDE.md`, read it. Inherit its reading protocol, task lifecycle, and conventions rather than restating them. If it defines a task system (for example `.tasks/`), the brief should point the agent at the relevant task file instead of duplicating its content.
2. Check `git status` and recent changes so the "what is proven" section reflects the working tree, not your recollection.
3. Identify the exact files the work touches. Name them by path. If you are unsure a file is relevant, it probably is not; a shorter reading list is better than a padded one.

## Output structure

Produce one contiguous block the user can copy in a single action. Use this order. The section labels can be light; the content is what matters.

### 1. Role and mode

State who the agent is for this task and, critically, what mode it is in. The sharpest handoffs name the mode as a boundary: an analysis and recommendation task is not an implementation task, and saying so up front prevents the agent from writing code when you wanted a written plan. Example framing: "You are doing an architectural deep-dive, not implementation. The deliverable is a written analysis, nothing more."

### 2. Do-not-touch constraints

List what the agent must not modify or do. This is the single most valuable section for a machine reader, because a fresh agent's default is to be helpful and act broadly. Be concrete: name directories, files, or classes of action that are off limits, and say why in a few words so the agent can reason about edge cases rather than following a blind rule.

### 3. Read these first, in order

An ordered list of files or docs the agent must read before touching anything, most foundational first. Prefer pointing at durable repo files (`AGENTS.md`, a task file, an architecture doc) over pasting content inline, so the brief stays short and the agent reads the current version. If a task system exists, this list is usually short: the global rules file plus the one assigned task file.

### 4. Background: what is proven, and when

A dated, precise statement of the current state: what has been built, tested, decided, or ruled out. Date it (for example "as of 2026-07-20") so the agent can tell fresh facts from stale ones. State things that were tried and did not work, not just what succeeded, so the agent does not repeat a dead end. This is where you prevent the "acted on a stale assumption" failure.

### 5. Scope, in phases, with check-in gates

Break the work into ordered phases. For any step that is hard to reverse or that you want to review (a real account, a destructive migration, a public push, a large token spend), mark an explicit stop-and-check-in gate: "Stop and check in with me before Phase N." This mirrors how the user actually likes to drive multi-step work, one reviewable chunk at a time. Close with a short out-of-scope list so the agent knows where the edges are.

## Acceptance the downstream agent can self-check

Where the work has a mechanical finish line, state it as a command or a checkable condition (a passing test, a clean type-check, a file that exists). A machine reader can verify itself against a concrete criterion, which is far more reliable than "make sure it works." If the repo's task files already carry acceptance criteria, point at them rather than re-inventing.

## Conventions

Follow the target repo's `AGENTS.md` and its house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)): no em-dashes, Mermaid over ASCII for any diagram, sentence-case headings, clickable file links. The brief itself should model these, since the downstream agent will take its cues from it.

## Example skeleton

```
You are <role>. Mode: <analysis | implementation | review>. Deliverable: <what>.

Do not: <constraint 1; why>. <constraint 2; why>.

Read these first, in order:
1. AGENTS.md  (global rules, task lifecycle)
2. .tasks/<id>.md  (your assigned task)
3. <architecture or context doc, if the task cites it>

Background (as of <date>): <what is built/tested/decided>. <what was tried and rejected>.

Scope:
- Phase 1: <...>
- Phase 2: <...>  Stop and check in before Phase 3.
- Phase 3: <the irreversible or high-cost step>

Out of scope: <...>.

Done when: <command that must pass, or condition that must hold>.
```
