---
id: feat-0040
title: Add an evidence gate and a stable finding signature to house-review and verifier-agent
type: feat
status: open
priority: P1
depends_on: []
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
touched_files:
  - .agents/skills/house-review/SKILL.md
  - .agents/rules/review-quality.md
  - docs/spec/house-review.md
created: 2026-08-05
---

## Problem

Rule 2 of [`review-quality.md`](../.agents/rules/review-quality.md) says to validate every finding
against the real code before reporting it, and warns that a confident false positive costs more
trust than a missed nit. It is the right rule and it is entirely honor-system: nothing checks that
the `file:line` a finding cites resolves to anything, or that the quoted code is the code actually
there.

This is not a theoretical gap. `verifier-agent`'s own dogfood caught the exact failure it describes:
the conformance matrix for `validate-skills.py` carried correct classifications sitting on citations
that had drifted eight lines after the `chore-0003` refactor. Every finding read as authoritative.
None of the pointers landed. That was found because a human happened to look, which is precisely the
condition the rule is supposed to remove.

The second gap is that findings have no identity. [`house-review`](../.agents/skills/house-review/SKILL.md)
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
- Update [`house-review`](../.agents/skills/house-review/SKILL.md) to apply both, and update its
  contract at [`docs/spec/house-review.md`](../docs/spec/house-review.md) with the scenarios that
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

Note that both task files are still `status: in_progress` in `.tasks/` even though their work
shipped, so the backlog reads as though they were unfinished. That is a closeout gap, not a blocker
for this task, and it is not this task's job to fix. If it is still true when this is picked up,
file it rather than absorbing it.

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

- [ ] `review-quality.md` states the required evidence shape and the stable signature definition.
- [ ] `house-review` applies the evidence gate as a named step, and states the re-anchor-do-not-drop
      rule for a quote found at a shifted line.
- [ ] The evidence shape has a stated form for a finding whose evidence is an absence.
- [ ] `docs/spec/house-review.md` gains scenarios covering the gate, the signature, and the
      absence case, and its conformance sibling from `chore-0025` is updated to match.
- [ ] Dogfood evidence recorded in the task closeout: run the updated `house-review` over a real
      diff and state whether the gate dropped or re-anchored anything.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
