---
id: feat-0040
title: Add an evidence gate and a stable finding signature to house-review and verifier-agent
type: feat
status: done
priority: P1
depends_on: []
parent: "ROADMAP Epic B #15: evidence gate and stable finding signature"
touched_files:
  - .agents/skills/house-review/SKILL.md
  - .agents/skills/verifier-agent/SKILL.md
  - .agents/rules/review-quality.md
  - docs/spec/house-review.md
  - docs/spec/house-review.conformance.md
created: 2026-08-05
---

## Problem

Rule 2 of [`review-quality.md`](../../.agents/rules/review-quality.md) says to validate every finding
against the real code before reporting it, and warns that a confident false positive costs more
trust than a missed nit. It is the right rule and it is entirely honor-system: nothing checks that
the `file:line` a finding cites resolves to anything, or that the quoted code is the code actually
there.

This is not a theoretical gap. `verifier-agent`'s own dogfood caught the exact failure it describes:
the conformance matrix for `validate-skills.py` carried correct classifications sitting on citations
that had drifted eight lines after the `chore-0003` refactor. Every finding read as authoritative.
None of the pointers landed. That was found because a human happened to look, which is precisely the
condition the rule is supposed to remove.

The second gap is that findings have no identity. [`house-review`](../../.agents/skills/house-review/SKILL.md)
emits prose findings, so two reviewers reporting the same defect produce two findings, and the same
defect reported across three runs is indistinguishable from three defects. That costs little today
because review is single-pass, and it will cost a lot as soon as review runs in parallel over zones,
which is the direction `fix-batch` already points.

Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT)
solves both in its Deep Review workflow with two mechanisms worth taking without taking the
workflow: an **evidence gate** that drops any finding whose evidence does not resolve to a real code
location, and a **stable signature** (severity, normalized path, summary, area id) that makes
findings deduplicable and countable across runs.

## Scope

**In scope:**

- Add to `review-quality.md` a required evidence shape for a finding: file path, line range, symbol
  where one applies, and an exact quote of the cited code.
- Add the evidence gate as an explicit step: before reporting, resolve each citation against the
  file on disk and drop any finding whose quote is not found at the cited location. A finding that
  cannot be grounded is not downgraded in severity, it is not reported.
- Define the stable signature and where it is emitted, so a later task can count repeats.
- Update [`house-review`](../../.agents/skills/house-review/SKILL.md) to apply both, and update its
  contract at [`docs/spec/house-review.md`](../../docs/spec/house-review.md) with the scenarios that
  cover them.
- Carry the same evidence shape into `verifier-agent`'s reporting, so a verification record and a
  review finding cite code the same way.

**Out of scope:**

- Repeat and futility classification. That consumes the signature and is `feat-0042`.
- Deep Review's zone-by-lens fan-out, its skeptic-refutation pass for contested findings, and its
  rule that a finding is `fixed` only when a fresh review no longer detects it. All three are worth
  considering later; none are needed to make citations trustworthy, and taking them together would
  be importing the workflow rather than the mechanism.
- Any change to the severity scheme or the eight rubric categories. The rubric is settled.
- `.agents/skills/verifier-agent/SKILL.md` edits beyond the evidence shape, so this stays disjoint
  from `feat-0041`.

## Implementation notes

**State of the files this task edits.** `chore-0024` (naming `house-review`'s explicit-range mode)
and `feat-0035` (`review-depth`) both changed `.agents/skills/house-review/SKILL.md` and
`docs/spec/house-review.md`, and both landed on `main` in `517c333`. So there is no collision to
sequence around: edit the shipped versions of those files, which already contain the explicit-range
mode and the review-depth composition.

Both task files read as unfinished when this was written, and both were closed out on 2026-08-05,
`chore-0024` as a missed closeout and `feat-0035` on author sign-off. Nothing here is blocked on
them.

`review-depth` selects how hard to look. This task governs what a finding must prove once the depth
is chosen. The two compose and neither subsumes the other, so read the shipped `review-depth`
SKILL.md before editing `house-review` to avoid restating its signal table.

The evidence gate is cheap to state and easy to write loosely. The test of whether it was written
well is whether it says what to do when the quote is found but at a different line, which is exactly
the drift case above. The answer should be to re-anchor and report, not to drop, since the finding
is real and only the pointer moved.

## Risks and rollback

Touches more than one module (a rules lens, a skill, and a spec), so the rule fires.

The risk is over-tightening: a gate strict enough to drop findings that are real but awkward to
quote, for example a finding about something absent rather than present, such as a missing test or
an unhandled branch. Those have no code to quote. The evidence shape must accommodate a finding
whose evidence is an absence, or the gate will quietly suppress the whole test-coverage category.
Handle it explicitly and cover it with a scenario.

Rollback is a revert of three documents; no code depends on this.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" -v

- [x] `review-quality.md` states the required evidence shape and the stable signature definition.
- [x] `house-review` applies the evidence gate as a named step, and states the re-anchor-do-not-drop
      rule for a quote found at a shifted line.
- [x] The evidence shape has a stated form for a finding whose evidence is an absence.
- [x] `docs/spec/house-review.md` gains scenarios covering the gate, the signature, and the
      absence case, and its conformance sibling from `chore-0025` is updated to match.
- [x] Dogfood evidence recorded in the task closeout: run the updated `house-review` over a real
      diff and state whether the gate dropped or re-anchored anything.

## Implementation record (2026-08-05)

Two files outside the original `touched_files` were edited and are now declared:
`.agents/skills/verifier-agent/SKILL.md`, which Scope required for the shared evidence shape and
which the frontmatter had omitted, and `docs/spec/house-review.conformance.md`, which the fourth
acceptance criterion requires and which was likewise undeclared.

The `verifier-agent` edit is bounded to the evidence shape exactly as Out of scope directs: it adds
the two-outcome drift rule to the existing stale-citation paragraph in Step 3, an evidence-shape
paragraph to Step 4, and an `evidence` field with its rule to the output format. Nothing about the
verdict rule, the `blocked` preconditions, or the conformance composition was touched, so this stays
disjoint from `feat-0041`.

The spec's `status: approved` was left alone. `approved` is deliberately non-terminal in this
repository (see `.agents/hooks/spec-conformance-gate.py`), and flipping it to `draft` would make
`verifier-agent` return `blocked` on the very run that verifies this task. Whether the amendment
needs a fresh sign-off is the author's call, and the amendment note says so rather than claiming a
re-approval nobody gave.

### Dogfood: the gate over a real diff

Ran the updated procedure over `b50cc76` (`fix: skip file:// links in all three link checkers`), a
committed range this agent did not write. The gate both re-anchored and dropped, one of each.

**Re-anchored, not dropped.** A candidate about the skip tuple was cited at `.tasks/validate.py:49`,
which is the natural citation when reading from the hunk header `@@ -46,7 +46,32 @@` rather than
from the file. Resolving the quote `LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:", "file://")`
against the revision under review (`git show b50cc76:.tasks/validate.py`) found it at line 74, not
49. Re-anchored 49 to 74 and reported. Line 49 at that revision holds the pre-image tuple, so this
is exactly the drift case the rule is written for, and dropping it would have discarded a real
finding over a pointer.

**Dropped.** A candidate claimed the third copy of the rule, the inline check in
`.github/workflows/checks.yml`, had not been kept in step and still skipped only the network
schemes. Its quote `startswith(("http://", "https://"))` resolves nowhere in that file; the line
present is `if not target or target.startswith(("http://", "https://", "mailto:", "file://"))`.
Dropped, not downgraded and not hedged. This is the case worth having the gate for: the candidate
was plausible, was about a real duplication the commit message itself flags, and was wrong.

**Survived, as an absence finding.** Nothing pins the three copies of the rule in step.
`git grep -n LINK_SKIP_PREFIXES -- tests/` returns no match, and the anchor
`LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:", "file://")` resolves at
`.tasks/validate.py:74` and at `.agents/skills/init-worktracking/templates/validate.py:68`. Under
the old rules this finding had nothing to quote and was the kind of finding a strict gate would have
suppressed; under the absence form it is citable. Signature:
`major|.tasks/validate.py|tests|no-test-pins-the-three-copies-of-link-skip-prefixes`.

Gate summary for the run: 3 candidates, 1 dropped, 1 re-anchored, 2 reported.

### Left for the central closeout

One `doc-sync` finding is identified and deliberately not applied here, because the reader-facing
documents are shared and this ran alongside sibling agents. `docs/CATALOG.md` line 19 describes
`house-review` as "House-style code review with an explicit rubric and severities, composing the
swappable `review-quality` lens (moonray's quality-lens pattern). Report-only." That is not false,
but it is now incomplete in the way AGENTS.md section 3 names: the evidence gate is the
user-visible change (every citation is now checkable and unresolvable findings are dropped) and no
reader-facing document mentions it. Nothing else scanned is made false: `README.md`, `ARCHITECTURE.md`,
`GETTING-STARTED.md`, and `CONTRIBUTING.md` describe the rubric, the lens, and the report-only
posture, all unchanged.

## Definition of done

- [x] Acceptance command(s) pass locally. 20 skills, 85 task files, 141 tests, zero errors.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
