---
title: house-review
status: approved
---

# house-review

Behavioral contract for the [`house-review`](../../.agents/skills/house-review/SKILL.md) skill, written
2026-07-27 (`feat-0024`). This is a **characterization** spec: it records the contract the shipped
skill already holds, drafted from its actual behavior rather than from what it arguably should do.
Where the skill is genuinely ambiguous, that ambiguity is recorded in Open Questions rather than
resolved by inventing behavior.

Amended 2026-07-27 (`chore-0012`): the skill was renamed from `code-review` to `house-review` to
resolve a collision with harness built-in review commands, and both Open Questions were resolved into
the contract. Reopened to `draft` for that amendment; a human sets `status: approved`.

**Amended 2026-08-03 (`chore-0024`) on the author's explicit instruction, and re-approved.** S-013 adds
a bare explicit range, and the Modes and Range resolution rows now account for it. This repairs an
internal inconsistency rather than expanding scope: the Invocation row already permitted "a base, or a
commit range", and the two rows beneath it enumerated no mode and no resolution branch that such an
input could reach, so the table contradicted itself across three consecutive rows. The amendment also
states which side wins when an explicit range meets the resolved default, and that the difference
between the two is reported, because a range does not say on its own whether it was resolved or handed
over.

Adding S-013 forced one further edit, recorded here rather than left to be noticed: S-002, S-003, and
S-004 each opened on "a request naming no scope", which a bare range satisfies, so on its own S-013
would have fired at the same time as S-002 with a different outcome. Their preconditions now read
"naming neither a path scope nor a range", which is what they meant when a bare range was not yet
contemplated. No behavior those three describe has changed.

## Problem

`house-review` is shipped, load-bearing, and composes a swappable lens, and it has no contract. Three
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

### Scenario S-012: a range supplied alongside a path scope narrows a change review

- **Given** a request naming both a path scope and an explicit base or commit range
- **When** the skill runs
- **Then** it reviews that range restricted to the named paths, as a change review rather than a
  full-file review, because a request naming a range is asking about a change.

### Scenario S-013: a bare explicit range is reviewed as given, not resolved

- **Given** a request naming an explicit base or commit range and no path scope, such as a single
  historical commit
- **When** the skill runs
- **Then** it reviews that range as a change review, without computing a merge-base range of its own,
  and reports the changeset as supplied rather than resolved, because a range does not carry any record
  of which of the two produced it.

### Scenario S-002: with neither a scope nor a range named, the branch's own range is reviewed

- **Given** a git repository with at least one commit, on a branch ahead of its merge-base with the
  default branch, and a request naming neither a path scope nor a range
- **When** the skill runs
- **Then** it reviews the committed range from that merge-base to `HEAD`, and notes any uncommitted
  changes as available to fold in rather than silently including or ignoring them.

### Scenario S-003: an empty committed range falls back to the working tree

- **Given** a request naming neither a path scope nor a range, where the committed range is empty,
  because the work sits on the default branch or is not yet committed
- **When** the skill runs
- **Then** it reviews the working-tree changes, tracked edits together with untracked files, rather
  than reporting that there is nothing to review.

### Scenario S-004: nothing to review is stated, not worked around

- **Given** a request naming neither a path scope nor a range, where both the committed range and the
  working tree are empty
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
| Modes | Explicit path scope (full-file review); explicit range with no path scope (change review over the range as given); a path scope plus a range (change review narrowed to those paths); or change review of the resolved default (when neither is named) |
| Range resolution | An explicit range if the request named one, else merge-base with the default branch, then working tree, then nothing to review. Which of the two produced the changeset is reported, as supplied or resolved |
| Severities | `blocker`, `major`, `minor`, `nit`, defined by the `review-quality` lens |
| Output | A verdict line, then findings ordered by severity, each with `file:line`, issue, why, and fix |
| Side effects | None. No file is written, no commit is made |

## Open Questions

None. Both questions this spec opened were resolved by `chore-0012` on 2026-07-27: a range supplied
alongside a path scope narrows a change review to those paths (now `S-012`), and the name collision
was resolved by renaming the skill rather than by asserting a distinction. Re-approved by the author on 2026-07-27.

The `chore-0024` amendment on 2026-08-03 opens none. It closes a contradiction the table already
carried rather than deciding anything new, and it was re-approved on the same day.
