---
id: chore-0070
title: Progressive disclosure is prescribed, never used, and guarded by a warning that cannot fail, so decide which of the two conventions this kit actually has
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - AGENTS.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-27
---

## Problem

`AGENTS.md` section 4 prescribes progressive disclosure twice: a skill should "Aim under ~500 lines; push
detail into referenced files", and it lists **`references/`** among the supporting directories a skill may
carry. [`validate-skills.py`](../scripts/validate-skills.py) carries `MAX_BODY_LINES = 500` to back it.

Measured 2026-08-27 across all twenty skills:

```text
skills with a references/ directory      0 of 20
single-file skills                       18 of 20   (the two exceptions ship templates/, not prose)
body size spread                         30 to 463 lines
fix-batch, the largest                   463 of 500
python scripts/validate-skills.py | grep -c WARN   ->  0
```

**And the rule that backs it cannot fail.** The body-length branch appends to `warnings`, not `errors`,
and the function ends `return 1 if errors else 0`, so a skill over 500 lines prints one line and passes
the gate. It has never fired.

That is exactly the pattern `chore-0063` wrote into `AGENTS.md` on the same day: a check that cannot fail
is unchecked, whatever it printed. Here it is one layer stranger, because the mechanism it guards has
never been used either. **The kit prescribes a convention, ships a non-failing guard for it, and has zero
instances of it.**

**This is a decision, not a defect.** Two answers are defensible and the current state is neither of them:

- **`references/` is the convention.** Then `fix-batch` at 463 lines is overdue for a split, the warning
  should be an error or a real threshold, and the tree should contain at least one worked example, because
  a convention with no instance is a convention nobody can copy.
- **Single-file skills are the convention.** Then the prescription and the warning are both describing a
  practice this kit does not have, and they should say what it does have. `AGENTS.md` would state that a
  skill body is self-contained, and the line limit would either go or become a real bound with a stated
  reason.

The cost of leaving it is not hypothetical. `fix-batch` is the skill most likely to grow, it has 37 lines
of headroom against a cap that would only whisper, and there is no example in the tree for it to grow
into.

## Scope

**In scope:** decide which convention this kit has, then make `AGENTS.md` and `validate-skills.py` agree
with the answer and with each other.

- **Decide, and record the rejected answer with its cost.** The deliverable is the decision. A task that
  adjusts the threshold without answering the question has restated the problem.
- Whichever answer wins, the guard follows it: an error, a warning with a stated reason for staying a
  warning, or removal. **A warning kept by default is the current state and is not an outcome.**
- If `references/` wins, produce **one** worked example rather than a policy. `fix-batch` is the obvious
  candidate and is not the only one; `review-depth` at 352 lines and `doc-sync` at 305 are the others
  above 300.

**Out of scope:**

- **The body-shape rule and the lens list**, which are
  [`chore-0069`](chore-0069-the-two-body-shapes-rule-is-wrong-on-its-own-list-and-nothing-checks-it.md).
  **That task touches the same three files as this one, so the two cannot share a wave.**
- The description ceiling and its headroom. Adjacent measurement, separate question, not filed.
- Splitting more than one skill. If `references/` wins, one example proves the shape; a sweep is a
  different task with its own evidence.
- `install.py` and `build-adapters.py`. Both already carry supporting files one level deep, so neither
  needs changing for either answer. **Confirm that against the code rather than inheriting it from this
  sentence**, because a `references/` directory that does not survive distribution would settle the
  question by itself.

## Implementation notes

The distribution question above is the one that could decide this without a judgment call, so check it
first. `chore-0036` added supporting-file link checking for markdown shipped beside a `SKILL.md`, and
`build-adapters.py` inlines a body for the cursor and vscode targets. **If an inlined adapter cannot carry
a `references/` file, then single-file is not a preference here, it is a constraint**, and the decision is
made by the distribution paths rather than by taste.

Anthropic's own skill-authoring guidance is the source of the progressive-disclosure prescription, and the
2026-08-18 external benchmark recorded this divergence and filed nothing. That benchmark is the reason
this is worth answering rather than leaving; it is not, on its own, an argument for either answer.

## Risks and rollback

Three files including the canonical rules document.

The risk is choosing the answer that is cheaper to implement rather than the one that is true. Splitting
`fix-batch` is real work; deleting a line limit takes a minute. **Decide from the distribution constraint
and the reader's experience, and if the cheap answer wins, say what evidence made it the right one.**

Reversible by reverting one commit. No skill body is split unless the decision requires it.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `AGENTS.md` states one convention, and the rejected one is recorded with its cost.
- [ ] `validate-skills.py`'s body-length rule matches the stated convention, and if it remains a warning
      the closeout says why a warning is the right level here.
- [ ] The closeout states whether a `references/` file survives all four distribution paths, checked by
      emitting them rather than by reading the code.
- [ ] If `references/` is chosen, exactly one skill demonstrates it and the run reports it.
- [ ] A test covers whichever level the body-length rule now sits at, failing against the current code.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
