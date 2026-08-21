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
thirteen scenarios this matrix first covered (`S-012`, `S-013`, and the `Modes` surface row) exist because someone audited
this skill by hand and found a real defect. This matrix is the first mechanical pass over the whole
contract.

**Re-audited 2026-08-05 (`feat-0040`)** after the evidence gate and the finding signature landed.
Five scenarios (`S-014` through `S-018`) and two surface rows (Evidence, Signature) are new and
audited below, the `Output` row was re-audited against its amended text, and the Step numbers in the
existing rows were corrected where the new Step 4 shifted them. The section below on the weakest row
is rewritten, because `S-007` was the row `feat-0040` was filed to strengthen.

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
| Scenarios | S-005 the reviewed code is never modified | Conformed | Step 5 / "Do not edit or commit anything", the skill preamble / "**report-only**: it never edits or commits", and Notes / "it reviews, it does not change code, and it never commits" | stated three times. The contract's hardest clause is that this holds "including one whose findings each carry a concrete suggested fix", and Step 5 satisfies it by placing the prohibition immediately after the fix-bearing finding format |
| Scenarios | S-006 findings ordered by severity and individually actionable | Conformed | Step 5 / "**Findings**, ordered `blocker` first, grouped by file within a severity", with the two quoted finding templates carrying a `file:line` location, the issue, why it matters, the evidence, the signature, and a suggested fix | the templates pin every required part by example rather than by description, and there are now two so the absence form is shown rather than described. The location is part of the template's own worked example, not a citation into this repository |
| Scenarios | S-007 an unsubstantiated candidate is dropped | Conformed | Step 3 / "**validate every candidate finding against the real code before it becomes a reported finding**, and drop anything you cannot substantiate", now backed by Step 4's gate / "**drop the finding.** Not at a lower severity, not with a hedge" | the contract's sharper requirement is that it not appear "with a hedge or a lowered severity", which Step 4 now states in those words. See the note below: this row was the reason `feat-0040` existed |
| Scenarios | S-008 a clean change is reported as clean | Conformed | Step 5 / "If nothing substantive survives validation, say the change looks clean and why, rather than manufacturing findings" | the added clause "A review whose findings were all dropped by the gate is a clean review with a drop count" closes the one way the gate could have turned a clean report into a misleading one |
| Scenarios | S-009 the severity scheme comes from the lens, not the skill | Conformed | Step 3 (works the lens's categories, severities, and protocol) and Notes / "the rubric and severities live in the swappable [`review-quality`](../../.agents/rules/review-quality.md) lens, not hardcoded here" | verified negatively as well: the skill body carries no independent list of severity names, so an adopter retuning the lens changes the skill's behavior with no edit here |
| Scenarios | S-010 a change too large to review reports its coverage | Conformed | Step 2 / "**When the change still does not fit, say so in the verdict line and name what you did not read**", and Step 5's verdict line / "No blocking issues found in the 14 of 31 files reviewed" | the worked example in the verdict line is what makes this checkable. The reasoning ("nothing in the output distinguishes them") is the strongest argument in the skill body |
| Scenarios | S-011 a structured findings channel changes the channel, not the findings | Conformed | "Running this in Claude Code" / "the evidence gate, and each finding's evidence and signature are identical either way; only the output channel changes" | the section is explicitly marked harness-specific and states that the portable markdown default works anywhere, which keeps it inside the portability contract. The added sentence about a channel with no field for the quote closes the obvious way a harness could have shed the new evidence |
| Scenarios | S-014 a finding whose quoted evidence resolves nowhere is dropped | Conformed | Step 4 / "**Quote found nowhere in the file, or the path does not resolve**: **drop the finding.** Not at a lower severity, not with a hedge", and "Report **how many candidates the gate dropped**, as one line in the output, without restating them" | both halves of the scenario are present: the drop, and the count without the content. The lens carries the same two rules, so an adopter retuning the lens moves both |
| Scenarios | S-015 a quote found at a shifted line is re-anchored, not dropped | Conformed | Step 4 / "**Quote found at a different line**: **re-anchor and report.** Correct the line number to where the text actually is and say the finding was re-anchored. Do not drop it. The code moved; the defect did not", plus the lens's "The line number is deliberately not in it" | the scenario's third obligation, that the signature is unchanged by re-anchoring, is satisfied by the signature having no line field rather than by a rule saying not to change it, which is the stronger form |
| Scenarios | S-016 a finding about something absent is citable | Conformed | The lens's absence evidence table (`absent` and `searched` fields), Step 3 / "Reaching for a quote of code that does not exist is the mistake here", Step 4's absence branch, and Step 5's second finding template with `Evidence (absence)` and `Searched:` | this is the row that would have silently failed: without the absence form the gate would drop every tests-and-coverage finding, and the skill states that consequence rather than leaving it to be discovered |
| Scenarios | S-017 every reported finding carries a stable signature | Conformed | The lens's signature section (`severity\|path\|category\|summary-slug`, with the slug rule stated deterministically) and Step 4 / "give every surviving finding the lens's **signature**", worked in both Step 5 templates | the category slugs are named rather than numbered, and the lens says why: `review-depth` already uses `R1` to `R7` for its selection rules |
| Scenarios | S-018 depth does not change what a finding must prove | Conformed | Step 4 / "**Depth does not touch this step.** ... A `quick` review is a smaller read, never a lower standard of proof", and [`review-depth`](../../.agents/skills/review-depth/SKILL.md) / "Validate before reporting. A `quick` review is a smaller read, never a lower standard of proof" | stated on both sides of the composition, in the same words, which is what stops one skill from being retuned into disagreement with the other without anyone noticing |
| Proposed Surface | Invocation | Conformed | Step 1 | |
| Proposed Surface | Modes (four, enumerated) | Conformed | Step 1's four branches | the fourth branch is what `chore-0024` added; before that the table and the body disagreed |
| Proposed Surface | Range resolution, and reporting supplied vs. resolved | Conformed | Step 1's numbered resolution and both the "supplied" and "resolved" statements | the precedence order matches the contract exactly: explicit range, then merge-base, then working tree, then nothing |
| Proposed Surface | Severities `blocker`, `major`, `minor`, `nit` defined by the lens | Conformed | [`review-quality.md`](../../.agents/rules/review-quality.md) severity scheme, referenced from Step 3 | the four names are defined in the lens, not the skill, which is S-009 holding at the surface level |
| Proposed Surface | Evidence: path, lines, symbol, quote, with an absence form | Conformed | The lens's two evidence tables, referenced from Step 3 and applied in Step 4 | the shape is defined in the lens and only applied in the skill, which is S-009's separation holding for the new material too |
| Proposed Surface | Signature: four fields, no line number | Conformed | The lens's signature section, emitted per finding in Step 4 and shown in both Step 5 templates | Notes / "The signature is emitted and never read here" records the deliberate seam: consuming signatures is separate work |
| Proposed Surface | Output: verdict line, gate drop count, then findings with `file:line`, evidence, signature, issue, why, fix | Conformed | Step 5's verdict line bullet, including "When the gate dropped anything, the count goes on its own line beneath", and the two finding templates | |
| Proposed Surface | Side effects: none | Conformed | Step 5 and Notes | same evidence as S-005. The gate reads files and runs searches, and writes nothing, so it does not disturb this row |
| Open Questions | One, on whether gate-dropped findings should be recoverable on request | Conformed | spec's Open Questions section, with the prior two recorded as resolved by `chore-0012` | the skill matches the contract's answer: it reports the count and not the content. Recording this as open rather than deciding it silently is the honest state |

## Coverage proof

**Audited** (27 items): scenarios S-001 through S-018 (all eighteen); the eight Proposed Surface
rows; and the Open Questions section.

**Unreconciled**: none.

**Not-built**: none. Every scenario and every surface element has evidence.

## The weakest row, named rather than buried

`S-007` was this matrix's weakest row and is the reason
[`feat-0040`](../../.tasks/done/feat-0040-evidence-gate-and-finding-signature.md) was filed. The original
audit put it this way: the skill instructed dropping any finding it could not substantiate, but
nothing checked that a reported finding *was* substantiated, and the failure mode is invisible by
construction, since a review full of confident, well-formatted, unverifiable findings looks exactly
like a good review. That was not hypothetical here: `verifier-agent`'s dogfood found a conformance
matrix whose classifications were correct but whose line citations had drifted eight lines after a
refactor, caught because a human looked.

The evidence gate is that instruction turned into a check with a defined outcome per branch, so the
row is now stronger than it was. It is worth being precise about how much stronger, because
overstating it would recreate the same problem one level up.

**What changed**: a finding now has to carry a quote, the quote has to be resolved against the file
at the revision under review, and each outcome has one stated disposition. A drifted citation is
re-anchored rather than dropped, and an unresolvable one is dropped rather than hedged. Those are
answers the skill did not have before, and the drop count makes a reviewer whose citations routinely
fail to resolve visible in the output.

**What did not change**: `house-review` is prose, so the gate is an instruction like everything else
in this matrix, and the limit stated at the top of this file still applies. Nothing executes the
gate, and a review that skipped it produces output that looks the same minus the evidence lines. The
gate is meaningfully more checkable than what it replaced, because a reader can now rerun any
citation themselves, which is the property `S-007` was missing. It is not enforcement.

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
