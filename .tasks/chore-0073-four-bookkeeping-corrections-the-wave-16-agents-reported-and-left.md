---
id: chore-0073
title: Four bookkeeping corrections the wave-16 agents reported and correctly left alone, one of which their own task file got backwards
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [chore-0045]
touched_files:
  - .tasks/README.md
  - tests/test_validate_skills.py
  - docs/spec/validate-skills.conformance.md
  - .agents/rules/house-style.md
created: 2026-08-27
---

## Problem

Four items reported by the wave-16 agents, each outside the scope of the task that found it and each
correctly left alone rather than folded in. Bundled deliberately, following the precedent `chore-0038`
set and `chore-0045` reused: authoring and verifying four task files would cost more than the work.
The bundling is the exception rather than the pattern, and the reason is written here so a later
reader does not take it as licence.

**1. `.tasks/README.md` is missing the `title` row, and `chore-0045` asserted the opposite.**
That task added a `title` row to the scaffolded template's field table, and its Out of scope section
said the kit's own `.tasks/README.md` "is a different file from the template and is not missing the
row", telling the agent to check before assuming symmetry. The agent checked and found the asymmetry
runs the other way: both field tables carry the same eleven rows, `id` through `created`, and neither
names `title`, which both `_TEMPLATE.md` files carry as their second key. **The out-of-scope note was
the wrong half of a true observation**, which is worth recording because it is the second task in a
month whose premise inverted on contact.

**2. `bug-0027`'s neighbours are still tagged to refinements rather than to their ids.** `chore-0045`
retagged two sets, `S-018` and `S-022`, and left three: `S-023`'s nine tests, `S-024`'s thirteen, and
`S-025`'s fifteen. They were left because that task's scope named two, not because three are fine.

**3. `validate-skills.conformance.md` counts the outstanding retag at four sets, and it is three.**
The `S-025` row states the follow-up population, and `chore-0045` closed one of the four. That row
also sits in a passage `chore-0065` deliberately preserved, so the correction belongs to whichever
pass actually re-derives it, which is item 2 above rather than a standalone edit.

**4. `house-style.md` calls `chore-0057` "still open".** It closed 2026-08-22. The file is an
adopter-swappable module, which is exactly why a stale internal reference in it matters: an adopter
who keeps our copy inherits the claim.

## Scope

**In scope:** the four corrections above.

- Item 1: add a `title` row to `.tasks/README.md`'s field table, matching the surrounding rows' style
  and the key order `_TEMPLATE.md` uses. Check the row count rather than trusting the number in this
  file.
- Item 2: retag the three remaining sets to `S-023`, `S-024` and `S-025`, keeping whatever the
  docstrings say about behaviour and changing only the id references and any sentence describing a
  decision as pending. This is the same correction `chore-0045` made twice and its diff is the model.
- Item 3: correct the `S-025` row **in the same pass that re-derives it**, not before. Per the
  disposition `chore-0062`, `chore-0068` and `chore-0045` all recorded, a citation repaired without
  re-deriving the row asserts a freshness the repair did not establish. **Widened 2026-08-27 at
  authoring review, because the original wording said `count` and the retag falsifies more than a
  number.** Two rows in that matrix carry present-tense claims item 2 makes false, and only one of
  them was named. The `S-023` row says nine of its twelve tests "are tagged `feat-0048` rather than
  `S-023`" and that "the gap is narrower than it was and still open"; after the retag none of that
  holds. The `S-025` row says the follow-up "now covers four sets rather than three", and after this
  task it covers none, so the clause goes rather than its number. Re-derive both rows, and check the
  `S-024` row for the same shape rather than assuming it is clean.
- Item 4: correct the `chore-0057` reference.

**Out of scope:**

- **Any dated measurement.** `validate-skills.conformance.md` carries sentences stating what was
  measured on a named date, including the `chore-0055` reach measurement and the passage `chore-0065`
  preserved. Those are records. Rewriting one falsifies history rather than refreshing a citation, and
  telling them apart from present-tense claims is the whole skill this item needs.
- Both test files' module docstrings, which carry stale scenario ranges (`S-001 through S-017` and
  `S-009 through S-016`). `chore-0045` recorded them as a deliberate seam and they are a different
  population from the class tags: fixing them means deciding what a module docstring's range should
  mean, which is a question and not a correction.
- `build-adapters.conformance.md`'s `S-019` row, which says "the test is retagged to the scenario it
  actually holds" while `TestEmittedRulesModuleResolves`'s docstring still reads "Scenarios S-009 and
  S-016". The row means "mapped here" and reads as a code change that did not happen. Reported by
  `chore-0045` and left, because correcting it is either a wording fix or a retag and nobody has
  decided which.
- Any behaviour change. All four are statements of fact, and the facts are the fix.

## Implementation notes

Item 1 is the one that can be got wrong by trusting a sentence. Two task files in a row have now
asserted something about these two field tables that was false. Count the rows in both.

Items 2 and 3 are one job rather than two, and doing 3 without 2 is the move the scope forbids.

`depends_on: [chore-0045]` is logical rather than a file collision: three of these four exist only
because that task drew a line and reported what fell outside it.

## Risks and rollback

Four small corrections across four files, none of them behavioural, so this section is short.

The risk is the one item 3 names: repairing a count inside a row nobody re-derived. The guard is the
ordering, and it is stated in the scope rather than left to judgment.

Reversible by reverting one commit. No contract changes, so no re-approval is affected.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] `.tasks/README.md`'s field table has a `title` row, and the closeout states the row count in
      both that file and the scaffolded template.
- [ ] The `S-023`, `S-024` and `S-025` test sets cite their ids, and no docstring among them describes
      a decision as still open.
- [ ] The `S-025` row's outstanding-retag count matches what is actually outstanding, corrected in a
      pass that re-derived the row, and `re_audited` credits only this pass.
- [ ] The `S-023` and `S-025` rows no longer describe the retag as outstanding, both were re-derived
      rather than edited in place, and the closeout says what the `S-024` row was checked against.
- [ ] `house-style.md` no longer calls `chore-0057` open.
- [ ] No dated measurement in either matrix is rewritten, and the closeout names the ones it left alone.
- [ ] The line-number citation grep over `docs/spec/*.conformance.md` still returns nothing.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
