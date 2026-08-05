---
title: house-review conformance
spec: docs/spec/house-review.md
audited: 2026-08-05
---

# house-review conformance matrix

Spec-vs-implementation audit of [`house-review`](../../.agents/skills/house-review/SKILL.md) against
[`house-review.md`](house-review.md). Produced by `chore-0025`.

This spec has a history worth knowing before reading the matrix. It was written by `feat-0024` to
exercise `verifier-agent`'s `blocked` branch against a real unapproved contract, amended by
`chore-0012` (which resolved a name collision by renaming the skill), and amended again by
`chore-0024` on 2026-08-03, which added `S-013` after finding the skill body contradicted itself
inside one step: Step 1 said there were two modes and then relied on a third. So three of the
thirteen scenarios (`S-012`, `S-013`, and the `Modes` surface row) exist because someone audited
this skill by hand and found a real defect. This matrix is the first mechanical pass over the whole
contract.

## What this audit can and cannot establish

`house-review` is a prose skill, so evidence is a clause rather than a code path, and this
establishes that the skill **instructs** the specified behavior rather than that anything enforces
it. Same limit as [`verifier-agent.conformance.md`](verifier-agent.conformance.md).

This spec also has a sibling [`house-review.verification.md`](house-review.verification.md), which
is a different artifact answering a different question. See the note at the end.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 explicit path scope reviews named files in full | Conformed | Step 1 / "**A path scope with no range (review the named files in full).**", and Step 2's closing line "An explicit path scope is the user pre-bounding the review for you; honor it and do not widen" | all three obligations present: full-file, no range computed, no widening. The no-widening half is stated in Step 2 rather than Step 1, which is where it operationally belongs |
| Scenarios | S-012 a range alongside a path scope narrows a change review | Conformed | Step 1 / "**A path scope alongside an explicit range narrows this mode; it does not turn it into a full-file review**" | the "because a request naming a range is asking about a change" reasoning is carried in the skill too, so the rule is not left as an unexplained special case |
| Scenarios | S-013 a bare explicit range is reviewed as given, not resolved | Conformed | Step 1 / "**An explicit range (review that range as given)**" with "**supplied rather than resolved**, since a range carries no record of which of the two produced it" | added by `chore-0024`. The `supplied` / `resolved` distinction is stated on both branches, which is what makes the reporting requirement checkable rather than aspirational |
| Scenarios | S-002 neither scope nor range: the branch's own range | Conformed | Step 1 / "Branch ahead of base: review the committed range `<base>..HEAD` (note and offer to include any uncommitted changes)" | the parenthetical is exactly the contract's "notes any uncommitted changes as available to fold in rather than silently including or ignoring them", which is the half most easily lost |
| Scenarios | S-003 an empty committed range falls back to the working tree | Conformed | Step 1 / "Range empty (on the default branch, or work uncommitted): review the working-tree changes (`git diff HEAD` plus untracked files). Do not dead-end" | "plus untracked files" satisfies the contract's "tracked edits together with untracked files". This is the same class of gap that made `reconcile-worktrees` drop new files, so the explicitness matters |
| Scenarios | S-004 nothing to review is stated, not worked around | Conformed | Step 1 / "Both empty: nothing to review, say so and stop" | |
| Scenarios | S-005 the reviewed code is never modified | Conformed | Step 4 / "Do not edit or commit anything", the skill preamble / "**report-only**: it never edits or commits", and Notes / "it reviews, it does not change code, and it never commits" | stated three times. The contract's hardest clause is that this holds "including one whose findings each carry a concrete suggested fix", and Step 4 satisfies it by placing the prohibition immediately after the fix-bearing finding format |
| Scenarios | S-006 findings ordered by severity and individually actionable | Conformed | Step 4 / "**Findings**, ordered `blocker` first, grouped by file within a severity", with the quoted finding template carrying `path/to/file.py:42`, the issue, why it matters, and a suggested fix | the template pins all four required parts by example rather than by description |
| Scenarios | S-007 an unsubstantiated candidate is dropped | Conformed | Step 3 / "**validate every candidate finding against the real code before it becomes a reported finding**, and drop anything you cannot substantiate" | the contract's sharper requirement is that it not appear "with a hedge or a lowered severity"; the skill says drop, and the lens's protocol rule 2 carries the reasoning. Scored `Conformed`, but see the note below on why this is the weakest enforcement in the matrix |
| Scenarios | S-008 a clean change is reported as clean | Conformed | Step 4 / "If nothing substantive survives validation, say the change looks clean and why, rather than manufacturing findings" | |
| Scenarios | S-009 the severity scheme comes from the lens, not the skill | Conformed | Step 3 (works the lens's categories, severities, and protocol) and Notes / "the rubric and severities live in the swappable [`review-quality`](../../.agents/rules/review-quality.md) lens, not hardcoded here" | verified negatively as well: the skill body carries no independent list of severity names, so an adopter retuning the lens changes the skill's behavior with no edit here |
| Scenarios | S-010 a change too large to review reports its coverage | Conformed | Step 2 / "**When the change still does not fit, say so in the verdict line and name what you did not read**", and Step 4's verdict line / "No blocking issues found in the 14 of 31 files reviewed" | the worked example in the verdict line is what makes this checkable. The reasoning ("nothing in the output distinguishes them") is the strongest argument in the skill body |
| Scenarios | S-011 a structured findings channel changes the channel, not the findings | Conformed | "Running this in Claude Code" / "The rubric, severities, and the validate-before-reporting rule are identical either way; only the output channel changes" | the section is explicitly marked harness-specific and states that the portable markdown default works anywhere, which keeps it inside the portability contract |
| Proposed Surface | Invocation | Conformed | Step 1 | |
| Proposed Surface | Modes (four, enumerated) | Conformed | Step 1's four branches | the fourth branch is what `chore-0024` added; before that the table and the body disagreed |
| Proposed Surface | Range resolution, and reporting supplied vs. resolved | Conformed | Step 1's numbered resolution and both the "supplied" and "resolved" statements | the precedence order matches the contract exactly: explicit range, then merge-base, then working tree, then nothing |
| Proposed Surface | Severities `blocker`, `major`, `minor`, `nit` defined by the lens | Conformed | [`review-quality.md`](../../.agents/rules/review-quality.md) severity scheme, referenced from Step 3 | the four names are defined in the lens, not the skill, which is S-009 holding at the surface level |
| Proposed Surface | Output: verdict line, then findings with `file:line`, issue, why, fix | Conformed | Step 4 | |
| Proposed Surface | Side effects: none | Conformed | Step 4 and Notes | same evidence as S-005 |
| Open Questions | None | Conformed | spec states `None.`, with both prior questions recorded as resolved | nothing to reconcile |

## Coverage proof

**Audited** (20 items): scenarios S-001 through S-013 (all thirteen); the six Proposed Surface rows;
and the Open Questions section.

**Unreconciled**: none.

**Not-built**: none. Every scenario and every surface element has evidence.

## The weakest row, named rather than buried

`S-007` is scored `Conformed` and is the one to watch. The skill instructs dropping any finding it
cannot substantiate, which is what the contract asks for, but nothing checks that a reported finding
was substantiated. The failure mode is invisible by construction: a review full of confident,
well-formatted, unverifiable findings looks exactly like a good review.

This is not hypothetical in this repository. `verifier-agent`'s dogfood found a conformance matrix
whose classifications were correct but whose line citations had drifted eight lines after a
refactor, and it was caught because a human looked. That is the same class of defect `S-007` governs.
[`feat-0040`](../../.tasks/feat-0040-evidence-gate-and-finding-signature.md) is the filed work that
would turn this instruction into a mechanical check by requiring each citation to resolve against
the file on disk. Until it lands, `S-007` conformance means the skill says the right thing.

## Why this file exists alongside `house-review.verification.md`

They answer different questions and neither replaces the other:

- **This file (`.conformance.md`)** asks *does the implementation match the contract?* It is
  produced by [`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md), covers every
  scenario and surface element, and classifies each `Conformed`, `Diverged`, or `Not-built`.
- **[`house-review.verification.md`](house-review.verification.md)** asks *was this run's work
  acceptable?* It is an evaluation record produced by `feat-0024` while exercising
  `verifier-agent`'s `blocked` branch, and it records a verdict with evidence for one run.

A spec can have one, both, or neither. The distinction is now stated in the layout table in
`AGENTS.md` and is what the spec-closeout gate in
[`feat-0039`](../../.tasks/done/feat-0039-spec-conformance-gate-hook.md) will look for: the gate accepts
a `<stem>.conformance.*` sibling, so a `.verification.md` alone does not satisfy it, and before this
task `house-review` would have blocked on exactly that.
