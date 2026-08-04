---
name: house-review
description: >-
  Review a code change against an explicit house rubric and severities, and produce a structured,
  severity-ranked markdown review, without editing or committing anything. Determines the review
  range (the current branch against its merge-base with the default branch, with a working-tree
  fallback), applies the review-quality lens (correctness, security, error handling, tests,
  readability, performance, API design, docs), validates each finding against the real code before
  reporting it, and writes findings ordered blocker to nit with file:line, why it matters, and a
  concrete fix. Use when the user says "review this", "review my changes", "code review", "review
  this PR/branch/diff", "what's wrong with this change", or wants a second pair of eyes before
  merging. Report-only: it never changes code.
license: MIT
---

# house-review

A house-style code review with an explicit rubric and severities. It reads a change, applies the
[`review-quality`](../../rules/review-quality.md) lens, and writes a structured review. It is
**report-only**: it never edits or commits. Reconciling the findings is the author's call, handled
by the human, `/simplify`, or [`fix-batch`](../fix-batch/SKILL.md).

It is named for the house rubric it applies rather than for the act of reviewing, which also keeps it
clear of the review commands several harnesses ship built in: a skill cannot resolve a namespace
collision by asserting it is different, so the name avoids one instead.
It composes a swappable lens (the moonray pattern: a reusable review "shot" a workflow composes,
with findings validated before they are reported), so the review bar lives in one editable file
and future quality skills can reuse it.

## What it produces

A severity-ranked markdown review: a one-line verdict, then findings ordered `blocker` to `nit`,
each with a `file:line` anchor, the issue, why it matters, and a concrete suggested fix. When
nothing substantive survives validation, it says so plainly.

## Design choices

Settled decisions (resolved with the user); these are not up for re-litigation:

- **Rubric and severities live in the lens**, [`review-quality.md`](../../rules/review-quality.md):
  eight categories, and the `blocker` / `major` / `minor` / `nit` scheme. Edit the lens to retune
  the bar; it is swappable like `house-style.md`.
- **Report-only.** The skill never edits or commits. Each finding carries a concrete fix in text.
- **Findings are validated before reporting** (the lens's govern/revalidate step). A confident
  false positive costs more than a missed nit.
- **Three review modes**: an explicit path scope reviews named files in full; an explicit base or
  range reviews that range as given, winning over the default and reported as supplied rather than
  resolved; otherwise the default is the branch vs its merge-base with the default branch (with a
  working-tree fallback), reusing [`pr-describe`](../pr-describe/SKILL.md)'s changeset logic. A path
  scope and a range together narrow the second mode rather than producing a fourth.

## Procedure

### Step 1: pick what to review

There are three modes, decided by two things a request either names or does not: a **path scope**, and
an **explicit base or commit range**. Work out which of the two it named before reading any code.

**A path scope with no range (review the named files in full).** When the user points at specific
files, a directory, or a path glob ("review these scripts", "review `src/auth/`"), review those files
as they stand, in full. This is a review of existing code, not a diff, so there is no range to
compute; just read the named files.

**An explicit range (review that range as given).** When the user names a base or a commit range
("review `abc123`", "review this against `main`"), that range *is* the changeset. Do not compute a
merge-base range of your own: **the explicit range wins over the resolved default below**, because the
user has already answered the question resolution exists to answer. Report the changeset as
**supplied rather than resolved**, since a range carries no record of which of the two produced it and
that difference is not recoverable later from the range itself. When a skill composed with this one
hands a range across, review that same range instead of resolving a second one; two skills each
resolving "this change" independently is how a review ends up describing a different diff than the
decision that governed it.

**A path scope alongside an explicit range narrows this mode; it does not turn it into a full-file
review.** If the user names both ("review `src/auth/` on this branch"), review the range restricted to
the named paths. A request that names a range is asking about a change, so reviewing those files in
full would answer a question they did not ask.

**Neither named (change review of the resolved default).** Reuse `pr-describe`'s changeset logic so
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

Report a changeset reached this way as **resolved**, the counterpart to the supplied case above. Naming
which one it was costs a word and keeps a later reader from having to guess whether the diff under
review was chosen or computed.

### Step 2: survey what is under review, and bound it before reading

Read the real code, not a summary. For a change review, `git diff --stat <range>` for shape then
the actual `git diff <range>` for substance; for a path scope, read the named files in full. Either
way, read enough surrounding context to judge the lines fairly. Note the languages, the test files
involved, and anything security-sensitive.

**Bound the read against the stat before starting it.** A large change does not fit, and running
out of context partway through produces a review of whatever happened to come first, presented with
the same confidence as a complete one. That is a worse outcome than an honestly partial review,
because nothing in the output distinguishes them. So:

- **Subtract what is not worth reading.** Lockfiles, generated code, vendored trees, minified
  assets, and large fixture data routinely dominate a diff's line count and carry almost no review
  signal. Exclude them explicitly and say you did.
- **Order the remainder by risk, not by the order git prints it.** Anything crossing a trust
  boundary first (auth, input parsing, secrets, subprocess, serialization, persistence), then
  application logic, then tests, then documentation and formatting. If the budget runs out, it runs
  out on the material where a missed finding costs least.
- **When the change still does not fit, say so in the verdict line and name what you did not
  read.** "Reviewed 14 of 31 files, prioritized by risk; `src/legacy/` not reviewed" is a useful
  review. A silently truncated one is not. Offer to review the remainder as a second pass.

An explicit path scope is the user pre-bounding the review for you; honor it and do not widen.

### Step 3: apply the review-quality lens

Work the [`review-quality`](../../rules/review-quality.md) lens over the change: its eight rubric
categories (applied only where the diff warrants), its severity definitions, and its protocol.
Follow the protocol's key rule: **validate every candidate finding against the real code before it
becomes a reported finding**, and drop anything you cannot substantiate.

### Step 4: write the review (report-only)

Produce the review as markdown:

- **Verdict line**: a one-line summary, for example "3 findings: 1 blocker, 2 minor" or
  "No blocking issues found". When the review was bounded per Step 2, the coverage belongs here
  too: "No blocking issues found in the 14 of 31 files reviewed".
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
- Future direction (not built yet): a multi-lens "deep-review" that runs several lenses
  (`review-quality`, `test-quality`, and so on) and reconciles their findings, mirroring
  moonray's Deep Review orchestration.
