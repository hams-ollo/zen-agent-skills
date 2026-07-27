---
title: code-review
status: draft
---

# code-review

Behavioral contract for the [`code-review`](../../.agents/skills/code-review/SKILL.md) skill, written
2026-07-27 (`feat-0024`). This is a **characterization** spec: it records the contract the shipped
skill already holds, drafted from its actual behavior rather than from what it arguably should do.
Where the skill is genuinely ambiguous, that ambiguity is recorded in Open Questions rather than
resolved by inventing behavior.

## Problem

`code-review` is shipped, load-bearing, and composes a swappable lens, and it has no contract. Three
things about it are load-bearing and currently unstated anywhere a reader can check them.

It is **report-only**, which is the property an adopter most needs to be able to rely on: a review
skill that edits code is a different and much more dangerous tool. It **delegates its entire rubric**
to [`review-quality`](../../.agents/rules/review-quality.md), so the severities and categories an
adopter retunes live outside the skill and the skill's behavior changes when they do. And it
**resolves what to review** through a fallback chain that must not dead-end, because the most common
invocation ("review this") arrives with no scope at all.

None of that is asserted by a test or a contract today. A future edit could make the skill review
only the diff it was given, or hardcode a severity scheme, and nothing would object.

## Goals

1. Produce a severity-ranked review of real code, grounded in the changed lines rather than a summary.
2. Resolve what to review from an ambiguous request without dead-ending on the common cases.
3. Keep the review bar in a swappable lens, so an adopter retunes it in one file.
4. Leave the reviewed code unchanged.
5. Report coverage honestly when the change is too large to review completely.
6. Stay portable across harnesses, so the same findings are produced whatever channel carries them.

## Non-Goals

- Applying, committing, or offering to apply the fixes it describes.
- Judging whether an implementation matches a spec, which is `spec-conformance`, or whether tests are
  well designed, which is `test-quality`.
- Creating or editing a pull request, which is `pr-describe`.
- Running the test suite or any build command as part of forming the review.

## Constraints

- The rubric, the severity scheme, and the validate-before-reporting protocol live in the swappable
  `review-quality` lens, not in the skill. The skill composes them by reference.
- Changeset resolution is shared with `pr-describe`, so "review this" and "describe this" resolve to
  the same range in the same repository state.
- The default output is Markdown, so the skill works in any harness. A harness may carry the same
  findings through its own structured findings channel instead.

## Scenarios

### Scenario S-001: an explicit path scope reviews the named files in full

- **Given** a request naming specific files, a directory, or a path glob
- **When** the skill runs
- **Then** it reviews those files as they currently stand, in full, computes no commit range, and does
  not widen the scope beyond what was named.

### Scenario S-002: with no scope named, the branch's own range is reviewed

- **Given** a git repository with at least one commit, on a branch ahead of its merge-base with the
  default branch, and a request naming no scope
- **When** the skill runs
- **Then** it reviews the committed range from that merge-base to `HEAD`, and notes any uncommitted
  changes as available to fold in rather than silently including or ignoring them.

### Scenario S-003: an empty committed range falls back to the working tree

- **Given** a request naming no scope where the committed range is empty, because the work sits on the
  default branch or is not yet committed
- **When** the skill runs
- **Then** it reviews the working-tree changes, tracked edits together with untracked files, rather
  than reporting that there is nothing to review.

### Scenario S-004: nothing to review is stated, not worked around

- **Given** a request naming no scope where both the committed range and the working tree are empty
- **When** the skill runs
- **Then** it states that there is nothing to review and stops, without selecting a substitute scope.

### Scenario S-005: the reviewed code is never modified

- **Given** any review, in any mode, including one whose findings each carry a concrete suggested fix
- **When** the skill finishes
- **Then** every reviewed file is byte-for-byte unchanged, no commit exists that the run created, and
  the suggested fixes appear only as text in the review.

### Scenario S-006: findings are ordered by severity and are individually actionable

- **Given** a review that produced findings at more than one severity
- **When** the review is written
- **Then** findings appear ordered from `blocker` to `nit`, grouped by file within a severity, and
  each carries a `file:line` anchor, the issue, why it matters, and a concrete suggested fix.

### Scenario S-007: a candidate finding that cannot be substantiated is dropped

- **Given** a candidate finding that the real code does not bear out, such as an unchecked input that
  is in fact validated elsewhere
- **When** the review is written
- **Then** that candidate does not appear in the review at any severity, rather than appearing with a
  hedge or a lowered severity.

### Scenario S-008: a clean change is reported as clean

- **Given** a review in which no candidate finding survives validation
- **When** the review is written
- **Then** it states plainly that the change looks clean and why, and reports no findings.

### Scenario S-009: the severity scheme comes from the lens, not the skill

- **Given** a `review-quality` lens whose severity names or rubric categories have been changed by an
  adopter
- **When** the skill runs
- **Then** the review uses the lens's current scheme, because the skill carries no independent copy of
  it.

### Scenario S-010: a change too large to review completely reports its coverage

- **Given** a change whose reviewable content exceeds what the run can read
- **When** the review is written
- **Then** the verdict line states how much was reviewed and the review names what was not read, so a
  partial review is never presented as a complete one.

### Scenario S-011: a structured findings channel changes the channel, not the findings

- **Given** a harness that provides its own structured findings output
- **When** the skill emits through that channel instead of Markdown
- **Then** the findings, their severities, and the validate-before-reporting rule are identical to the
  Markdown form; only the output channel differs.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | A request to review, optionally naming a path scope, a base, or a commit range |
| Modes | Explicit path scope (full-file review), or change review (default, no scope named) |
| Range resolution | Merge-base with the default branch, then working tree, then nothing to review |
| Severities | `blocker`, `major`, `minor`, `nit`, defined by the `review-quality` lens |
| Output | A verdict line, then findings ordered by severity, each with `file:line`, issue, why, and fix |
| Side effects | None. No file is written, no commit is made |

## Open Questions

1. **What does an explicit base or commit range mean inside an explicit path scope?** The skill says
   to honor one if given, but a path scope is defined as a full-file review while a range implies a
   diff. Recommendation: treat a range supplied alongside a path scope as narrowing a change review to
   those paths, rather than as a full-file review, since a user who names a range is asking about a
   change. This needs a decision before the two modes can be tested independently.
2. **Does the skill's name resolve unambiguously in a harness that ships its own review command?**
   Tracked separately as `chore-0012`. Recommendation: resolve that task first, since the answer
   changes the invocation row of the Proposed Surface.
