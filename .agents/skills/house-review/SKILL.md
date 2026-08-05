---
name: house-review
description: >-
  Review a code change against an explicit house rubric and severities, and produce a structured,
  severity-ranked markdown review, without editing or committing anything. Determines the review
  range (the current branch against its merge-base with the default branch, with a working-tree
  fallback), applies the review-quality lens (correctness, security, error handling, tests,
  readability, performance, API design, docs), resolves every finding's quoted evidence against the
  real file and drops any finding that does not resolve, and writes findings ordered blocker to nit
  with file:line, the quote, a stable signature, why it matters, and a concrete fix. Use when the
  user says "review this", "review my changes", "code review", "review
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
each with a `file:line` anchor, an exact quote of the cited code, a stable signature, the issue, why
it matters, and a concrete suggested fix. When nothing substantive survives validation, it says so
plainly.

## Design choices

Settled decisions (resolved with the user); these are not up for re-litigation:

- **Rubric and severities live in the lens**, [`review-quality.md`](../../rules/review-quality.md):
  eight categories, and the `blocker` / `major` / `minor` / `nit` scheme. Edit the lens to retune
  the bar; it is swappable like `house-style.md`.
- **Report-only.** The skill never edits or commits. Each finding carries a concrete fix in text.
- **Findings are validated before reporting** (the lens's govern/revalidate step). A confident
  false positive costs more than a missed nit.
- **Validation is checked, not trusted.** Every finding's quoted evidence is resolved against the
  file before the finding is reported, and one that resolves nowhere is dropped rather than hedged.
  The rule and its branches live in the lens; Step 4 below applies them.
- **Every reported finding carries a signature**, defined by the lens, so the same defect found by
  two reviewers or across three runs is one countable defect. This skill emits it and reads nothing
  from it.
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

Give each surviving candidate the lens's **evidence shape** as you form it, rather than back-filling
it afterwards. A defect in code that is there carries a path, a line range, the enclosing symbol
where there is one, and a verbatim quote. A defect in code that is *not* there, a missing test or an
unhandled branch, carries the lens's absence form instead: a quote of the nearest anchor, one line
naming what is absent, and the rerunnable search that established the absence. Reaching for a quote
of code that does not exist is the mistake here, and the absence form exists so the whole tests and
coverage category is not quietly suppressed by the next step.

### Step 4: run the evidence gate, then sign each finding

Every candidate now has evidence. Resolve it before any of it is reported, exactly as the lens's
evidence gate directs: read the cited file **at the revision under review** (`git show <rev>:<path>`
for a committed range, the file on disk for a working-tree or path-scope review) and look for the
quote.

- **Quote found where cited**: report it.
- **Quote found at a different line**: **re-anchor and report.** Correct the line number to where
  the text actually is and say the finding was re-anchored. Do not drop it. The code moved; the
  defect did not. Dropping here would throw away a real finding because a refactor shifted a
  pointer, which is the exact failure that produced this step, a conformance matrix in this
  repository whose classifications were right and whose every citation had drifted eight lines.
- **Quote found nowhere in the file, or the path does not resolve**: **drop the finding.** Not at a
  lower severity, not with a hedge. A citation a reader cannot follow is worse than a missed nit.
- **An absence finding**: rerun its stated search. If something now covers the claim, drop it. If
  the anchor quote no longer resolves, drop it. Otherwise report it.

Report **how many candidates the gate dropped**, as one line in the output, without restating them.
The count is what makes a reviewer whose citations routinely fail to resolve visible; the content is
what the gate just decided nobody should rely on.

Then give every surviving finding the lens's **signature**, `severity|path|category|summary-slug`.
It carries no line number on purpose, so a re-anchored finding keeps the identity it had before the
code moved.

**Depth does not touch this step.** [`review-depth`](../review-depth/SKILL.md) decides how much is
read and how exhaustively the rubric is swept; this step decides what a finding must prove to be
reported at all. A `quick` review is a smaller read, never a lower standard of proof.

### Step 5: write the review (report-only)

Produce the review as markdown:

- **Verdict line**: a one-line summary, for example "3 findings: 1 blocker, 2 minor" or
  "No blocking issues found". When the review was bounded per Step 2, the coverage belongs here
  too: "No blocking issues found in the 14 of 31 files reviewed". When the gate dropped anything,
  the count goes on its own line beneath: "2 candidate findings dropped by the evidence gate".
- **Findings**, ordered `blocker` first, grouped by file within a severity. A finding about code
  that is there:

  > **[major]** `scripts/install.py:42` (`copy_rules`): the issue in a sentence or two. Why it
  > matters.
  > Evidence: `if dest.exists() and not force:` (re-anchored from line 38)
  > Suggested fix: a concrete change.
  > `sig: major|scripts/install.py|correctness|existing-destination-is-skipped-without-a-message`

  A finding about something absent uses the same block with the lens's absence fields, so a missing
  test is as citable as a present bug:

  > **[major]** `tests/test_install.py` (`InstallRulesTests`): nothing covers the `--with-hooks`
  > path. Why it matters.
  > Evidence (absence): anchor `def test_copies_the_rules_module(self):` at line 88.
  > Searched: `git grep -n with_hooks tests/` returns no match.
  > Suggested fix: a concrete change.
  > `sig: major|tests/test_install.py|tests|no-test-covers-the-with-hooks-path`

- If nothing substantive survives validation, say the change looks clean and why, rather than
  manufacturing findings. A review whose findings were all dropped by the gate is a clean review
  with a drop count, not a review with nothing to say about why.

Do not edit or commit anything. If the user then wants the fixes applied, that is a separate
action (theirs, `/simplify`, or `fix-batch`).

## Running this in Claude Code

This section is Claude Code specific; the portable default above (a markdown review) works in any
harness. When running under Claude Code as part of a review workflow that expects structured
findings, the same validated findings may be emitted through the host's findings tool (for example
`ReportFindings`) instead of, or in addition to, the markdown. The rubric, severities, the
validate-before-reporting rule, the evidence gate, and each finding's evidence and signature are
identical either way; only the output channel changes. A structured channel with no field for the
quote or the signature carries them inside the fields it does have rather than dropping them, since
a finding that loses its evidence on the way out has lost the thing the gate was checking.

## Notes

- Report-only: it reviews, it does not change code, and it never commits.
- Portable by composition: the rubric, the severities, the evidence shape, the gate's branches, and
  the signature format all live in the swappable
  [`review-quality`](../../rules/review-quality.md) lens, not hardcoded here, so an adopter retunes
  the bar in one file and future skills reuse the same lens.
- The signature is emitted and never read here. Counting how often a finding repeats across runs,
  and deciding when a repeated finding is futile, is separate work that consumes this output.
- Future direction (not built yet): a multi-lens "deep-review" that runs several lenses
  (`review-quality`, `test-quality`, and so on) and reconciles their findings, mirroring
  moonray's Deep Review orchestration.
