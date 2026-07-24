---
name: code-review
description: Review a code change against an explicit house rubric and severities, and produce a structured, severity-ranked markdown review, without editing or committing anything. Determines the review range (the current branch against its merge-base with the default branch, with a working-tree fallback), applies the review-quality lens (correctness, security, error handling, tests, readability, performance, API design, docs), validates each finding against the real code before reporting it, and writes findings ordered blocker to nit with file:line, why it matters, and a concrete fix. Use when the user says "review this", "review my changes", "code review", "review this PR/branch/diff", "what's wrong with this change", or wants a second pair of eyes before merging. Report-only: it never changes code. Distinct from Claude Code's built-in /code-review command.
---

# code-review

A house-style code review with an explicit rubric and severities. It reads a change, applies the
[`review-quality`](../../rules/review-quality.md) lens, and writes a structured review. It is
**report-only**: it never edits or commits. Reconciling the findings is the author's call, handled
by the human, `/simplify`, or [`fix-batch`](../fix-batch/SKILL.md).

This is the kit's own review skill, distinct from Claude Code's built-in `/code-review` command.
It composes a swappable lens (the moonray pattern: a reusable review "shot" a workflow composes,
with findings validated before they are reported), so the review bar lives in one editable file
and future quality skills can reuse it.

## What it produces

A severity-ranked markdown review: a one-line verdict, then findings ordered `blocker` to `nit`,
each with a `file:line` anchor, the issue, why it matters, and a concrete suggested fix. When
nothing substantive survives validation, it says so plainly.

## Design choices

Settled decisions (resolved with the user); the skill overall is a draft pending field iteration,
but these are not up for re-litigation:

- **Rubric and severities live in the lens**, [`review-quality.md`](../../rules/review-quality.md):
  eight categories, and the `blocker` / `major` / `minor` / `nit` scheme. Edit the lens to retune
  the bar; it is swappable like `house-style.md`.
- **Report-only.** The skill never edits or commits. Each finding carries a concrete fix in text.
- **Findings are validated before reporting** (the lens's govern/revalidate step). A confident
  false positive costs more than a missed nit.
- **Two review modes**: an explicit path scope reviews named files in full; otherwise the default
  is the branch vs its merge-base with the default branch (with a working-tree fallback), reusing
  [`pr-describe`](../pr-describe/SKILL.md)'s changeset logic.

## Procedure

### Step 1: pick what to review

There are two modes. Decide which the request is.

**Explicit path scope (review named files or paths).** When the user points at specific files, a
directory, or a path glob ("review these scripts", "review `src/auth/`"), review those files as
they stand, in full. This is a review of existing code, not a diff, so there is no range to
compute; just read the named files. Honor an explicit base or commit range here too if one is given.

**Change review (the default when no scope is named).** Reuse `pr-describe`'s changeset logic so
"review this" means the same thing across the kit:

1. Confirm a git repo with at least one commit. Find the current branch and the default branch
   robustly (`git symbolic-ref --quiet refs/remotes/origin/HEAD`, else `origin/main` /
   `origin/master`, else local `main` / `master`).
2. Compute the base `git merge-base HEAD <default>` and pick the changeset:
   - Branch ahead of base: review the committed range `<base>..HEAD` (note and offer to include
     any uncommitted changes).
   - Range empty (on the default branch, or work uncommitted): review the working-tree changes
     (`git diff HEAD` plus untracked files). Do not dead-end.
   - Both empty: nothing to review, say so and stop.

### Step 2: survey what is under review

Read the real code, not a summary. For a change review, `git diff --stat <range>` for shape then
the actual `git diff <range>` for substance; for a path scope, read the named files in full. Either
way, read enough surrounding context to judge the lines fairly. Note the languages, the test files
involved, and anything security-sensitive.

### Step 3: apply the review-quality lens

Work the [`review-quality`](../../rules/review-quality.md) lens over the change: its eight rubric
categories (applied only where the diff warrants), its severity definitions, and its protocol.
Follow the protocol's key rule: **validate every candidate finding against the real code before it
becomes a reported finding**, and drop anything you cannot substantiate.

### Step 4: write the review (report-only)

Produce the review as markdown:

- **Verdict line**: a one-line summary, for example "3 findings: 1 blocker, 2 minor" or
  "No blocking issues found".
- **Findings**, ordered `blocker` first, grouped by file within a severity. Each finding:

  > **[severity]** `path/to/file.py:42`: the issue in a sentence or two. Why it matters.
  > Suggested fix: a concrete change.

- If nothing substantive survives validation, say the change looks clean and why, rather than
  manufacturing findings.

Do not edit or commit anything. If the user then wants the fixes applied, that is a separate
action (theirs, `/simplify`, or `fix-batch`).

## Running this in Claude Code

This section is Claude Code specific; the portable default above (a markdown review) works in any
harness. When running under Claude Code as part of a review workflow that expects structured
findings, the same validated findings may be emitted through the host's findings tool (for example
`ReportFindings`) instead of, or in addition to, the markdown. The rubric, severities, and the
validate-before-reporting rule are identical either way; only the output channel changes.

## Notes

- Report-only: it reviews, it does not change code, and it never commits.
- Portable by composition: the rubric and severities live in the swappable
  [`review-quality`](../../rules/review-quality.md) lens, not hardcoded here, so an adopter retunes
  the bar in one file and future skills reuse the same lens.
- Distinct from Claude Code's built-in `/code-review` command.
- Future direction (not built yet): a multi-lens "deep-review" that runs several lenses
  (`review-quality`, a future `test-quality`, and so on) and reconciles their findings, mirroring
  moonray's Deep Review orchestration.
- Shipped 2026-07-24, blessed after dogfooding on this kit's own change (`feat-0007`). Keep
  iterating in the field, especially against real code diffs beyond documentation changes.
