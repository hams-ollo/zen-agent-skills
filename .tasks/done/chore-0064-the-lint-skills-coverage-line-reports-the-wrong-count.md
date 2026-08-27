---
id: chore-0064
title: The lint skills coverage line reports the supporting-file count instead of the skill count, so two passing runs over different trees are byte-identical
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0058]
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-27
---

## Problem

[`bug-0045`](bug-0045-run-checks-discards-every-gate-coverage-line-on-a-passing-run.md) made
[`run-checks.py`](../../scripts/run-checks.py) print one coverage line per passing gate, so a gate that
examined nothing says so. Its rule is the last non-blank line of the gate's output containing a digit.

[`validate-skills.py`](../../scripts/validate-skills.py) prints two summary lines, so the rule reaches the
second and discards the first:

```text
Checked 20 skill(s): 0 error(s), 0 warning(s).
Link-checked 1 supporting file(s) beside them; skipped 8 template(s) whose links are written for
another repository and 5 non-markdown file(s). Also link-checked 4 file(s) under .agents outside the
skills tree; skipped 0 template(s) and 5 non-markdown file(s).
```

Only the second reaches the acceptance command's report. Two consequences, both measured 2026-08-27
during the `chore-0058` and `chore-0061` wave, and each found independently by a different agent:

- **The line is not self-contained.** It opens `Link-checked 1 supporting file(s) beside them`, and
  `them` refers to the skills named on the line that was discarded. A reader of
  `python scripts/run-checks.py` has no antecedent.
- **It does not vary with the gate's own scope.** Two clean runs, one over a tree of 20 skills and one
  over the same tree plus a duplicated single-file skill with its frontmatter `name` corrected, both
  exit 0 and print a **byte-identical** coverage line, because a skill carrying no supporting file, no
  template and no non-markdown file moves none of the counts on it. Reproduced by calling
  `validate-skills.py`'s injectable `main(skills_dir=...)` against two prepared trees and applying
  `coverage_line()`'s rule to each output.

That is the exact failure `bug-0045` exists to remove, surviving inside the gate `bug-0045` fixed. It
is a seam that task **disclosed rather than hid**, in its `## Decisions`: "the rule shows a gate's last
count, not its best one." This task closes it.

**This task is one of the same class as** [`chore-0032`](../chore-0032-links-guard-fires-per-run-not-per-pattern.md),
[`chore-0049`](../chore-0049-a-checker-for-conformance-matrix-citations.md),
[`chore-0059`](../chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md) and
[`chore-0060`](../chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md): a guard that
does not guard. It was found by the method that grouping asks for, looking for the next member while
fixing one, and the pattern behind the class is
[`chore-0063`](chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** make the `lint skills` coverage line report what that gate actually covered.

- The line that reaches `run-checks.py`'s report must name the skill count, and must move when the
  number of skills moves.
- A test asserting the second property directly: two trees differing only in skill count must not
  produce the same selected line. Asserting the string alone would pass against a line that is
  self-contained and still frozen.

**Out of scope:**

- **`scripts/run-checks.py` and its `coverage_line()` rule.** The rule is deliberately per-gate-blind
  and needs no per-gate knowledge; `bug-0045` rejected a name-to-regex table as a second source of
  truth that drifts the first time a gate rewords its summary. Fix the gate, not the aggregator. If
  the work argues otherwise, that is a finding to report rather than a place to widen into.
- Making any gate fail on zero inputs, rejected by `bug-0045` with a measurement.
- The supporting-file and portable-tree counts themselves. They are correct and earned, by
  [`chore-0036`](chore-0036-link-check-skill-supporting-files.md) and
  [`chore-0058`](chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md)
  respectively. **Nothing this task does may drop a count that already reaches the report.**

## Implementation notes

**Read the contract before choosing the fix, because the obvious one violates it.** The `Output`
surface element of [`docs/spec/validate-skills.md`](../../docs/spec/validate-skills.md) fixes the order:
per-issue lines, "then a `Checked N skill(s): E error(s), W warning(s).` summary, then a second line
reporting how many supporting files were link-checked and how many were skipped, by reason (S-024)".
So simply swapping the two lines so the skill count prints last is a **divergence from an approved
contract**, not a fix. At least three shapes are available and none is obviously right:

1. Carry the skill count into the second line, so one line holds everything the report needs.
2. Merge both summaries into a single line, which changes the shape S-024 describes.
3. Amend the contract to stop fixing the order, and reorder.

The third needs the amendment convention in [`docs/spec/README.md`](../../docs/spec/README.md), and an
amendment is already owed against this same spec by
[`chore-0065`](chore-0065-amend-the-validate-skills-contract-for-the-non-skill-agents-markdown-rule.md).
**Decide which shape, and record the two you rejected.** If the chosen shape needs a contract change,
say so and stop rather than making one: that is `chore-0065`'s file to touch, and two tasks amending
one spec in parallel is the collision this repository has already had once.

## Decisions

**Chosen: shape 1, carry the skill count into the second line.** It now reads `Link-checked 1
supporting file(s) beside the 20 skill(s) checked; skipped ...`. It is the only one of the three
that leaves the approved contract alone. The `Output` surface element of
[`validate-skills.md`](../../docs/spec/validate-skills.md) fixes both the order of the two lines and
the verbatim text of the first, and shape 1 changes neither: the second line still opens on
`Link-checked` and still reports the supporting-file counts by reason, so the element's description
of it stays true. The skill count is added to that line, not moved into it.

**Rejected: shape 2, merging both summaries into one line.** It deletes the "second line" the
`Output` element names, so it needs the same contract amendment shape 3 does, and it buys nothing
shape 1 does not: `coverage_line()` shows one line either way, and what the report lacked was a
number, not a merge. It also costs the raw run its first line, which every existing test and the
conformance matrix cite verbatim.

**Rejected: shape 3, amending the contract and reordering.** Correct in principle, out of scope in
fact. `docs/spec/` is not this task's to touch, an amendment against this same spec is already owed
by [`chore-0065`](chore-0065-amend-the-validate-skills-contract-for-the-non-skill-agents-markdown-rule.md),
and two tasks amending one spec in parallel is the collision this repository has already had once.
It also aims at the wrong thing: the order of the two lines was never the defect, the content of the
surviving one was.

**A premise that turned out false: the line carried six counts, not four.** The section below says
"the line currently carries four numbers". Measured 2026-08-27 it carries six: one supporting file
link-checked, eight templates skipped and five non-markdown files skipped, then four files
link-checked under `.agents` outside the skills tree with zero templates and five non-markdown files
skipped. `test_the_selected_line_still_carries_every_count_it_carried_before` pins all six plus the
new skill count, each a different number in the fixture, so a transposition fails as loudly as a
drop.

**Seam left open deliberately: two conformance documents now quote wording that no longer exists.**
`docs/spec/validate-skills.conformance.md` and `docs/spec/cloud-executable.conformance.md` both
quote `Link-checked 1 supporting file(s) beside them`. Both sit under `docs/spec/`, which this
task's acceptance criteria forbid it to modify, and no gate resolves a conformance-matrix citation
against its source, so nothing fails and nothing reports it. Owed to whoever amends this spec next,
alongside `chore-0065`.

## Risks and rollback

One module and its test file, so this section is short.

The risk is dropping a count that already reaches the report while adding the one that does not. The
line currently carries four numbers; whatever replaces it must still carry them, and the guard is a
test that reads the selected line rather than the whole output.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] The line `coverage_line()` selects from `validate-skills.py`'s output names the skill count.
- [x] A test asserts that two trees differing only in the number of skills produce different selected
      lines, failing against the current code.
- [x] The selected line is self-contained: no pronoun referring to a line the reader cannot see.
- [x] Every count that reaches the report today still reaches it, asserted rather than eyeballed.
- [x] The closeout states which of the three shapes was chosen and why the other two were rejected.
- [x] No file under `scripts/run-checks.py` or `docs/spec/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
