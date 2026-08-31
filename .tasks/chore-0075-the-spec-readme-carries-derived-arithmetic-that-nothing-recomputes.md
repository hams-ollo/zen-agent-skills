---
id: chore-0075
title: Five derived figures in the spec README go stale whenever a scenario lands, and four separate tasks have corrected them by hand
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0033]
touched_files:
  - docs/spec/README.md
  - scripts/check-citations.py
  - tests/test_check_citations.py
created: 2026-08-28
---

## Problem

[`docs/spec/README.md`](../docs/spec/README.md) carries at least five figures that are **derived from
other files** and maintained by hand:

| Figure | Derived from |
|---|---|
| The `Scenarios` column, one count per spec | the distinct `S-NNN` ids in that spec |
| "Eleven specs" | the number of rows in that table |
| "160 scenarios" | the sum of that column |
| "holding 147 of those scenarios ... 160 - 13 = 147" | the sum, minus the one spec with no matrix |
| "`install`'s matrix covers 15 of its 18 scenarios" | that matrix against that spec |

**Nothing recomputes any of them.** Confirmed 2026-08-28: no file under `scripts/`, under `tests/`, or
in `.tasks/validate.py` reads `docs/spec/README.md` at all. The `doc links` gate resolves its links and
never reads its numbers.

So every figure goes stale the moment any task adds a scenario, and the task that added it finds out
only if somebody thinks to look.

**Four tasks have now corrected these figures, and not one of them was told to.** Each discovered the
drift as a premise correction while there for another reason:

| Task | Date | What it found |
|---|---|---|
| `chore-0057` | 2026-08-22 | Two prose counts of a table's rows, removed rather than corrected under the house-style rule against them |
| `chore-0062` | 2026-08-27 | Its task named the re-approval queue alone; three further claims needed the edit, including the repository-wide arithmetic |
| `chore-0065` | 2026-08-27 | Four claims falsified by a twenty-fifth scenario, where the task named one |
| `chore-0033` | 2026-08-28 | Three figures wrong the moment five scenarios landed |

**The figures are correct today, and that is the argument rather than a reason to close this.** Every
per-spec count was checked against its spec on 2026-08-28 and all eleven agreed. They agree because
four separate agents corrected them by hand, each spending part of a task's budget on arithmetic
nobody asked them for. The next scenario to land breaks them again.

**The check is small.** Comparing the claimed count against the distinct `S-NNN` ids in each spec was
demonstrated in about ten lines while this task was being written, over all eleven specs, and it is
the same shape as the sum and the subtraction beneath it.

This is the third count-shaped claim in three days to be falsified by a change nobody connected to it:
`chore-0049` amended an approved contract that pinned the gate set by number, and `feat-0051`'s
acceptance criterion required "all seven gates" on the day an eighth landed. Both were fixed by
stating the property instead of the count. **That remedy is not available here**, because a table of
per-spec scenario counts is a count by construction. So this one has to be computed rather than
reworded, which is what makes it a checker rather than an edit.

## Scope

**In scope:** a check that recomputes what the spec README derives.

- The per-spec `Scenarios` column against the distinct `S-NNN` ids in each spec.
- The counts and arithmetic in the closing paragraph: the number of specs, the sum of the column, and
  the subtraction that yields the matrix-carrying subtotal.
- **A stated bound.** Say in the output what the check does not recompute, so a passing run is not
  read as "every number in this file is right". The qualifications paragraph and the re-approval
  queue's per-spec amendment counts are prose derived from history rather than from a file, and if
  they are out of reach that is worth saying rather than leaving a reader to assume otherwise. Follow
  the audited-and-unaudited habit `spec-conformance` uses and `chore-0049` already adopts.
- **Decide the host and record the rejection.** [`check-citations.py`](../scripts/check-citations.py)
  already walks `docs/spec/` on every run, which makes it the near neighbour, and `touched_files`
  assumes it. The alternative is a separate script, which is what `chore-0072` will need for
  `ROADMAP.md`. **Weigh whether these two are one checker or two**, since both recompute a claim
  against the repository, and say why rather than defaulting.

**Out of scope:**

- **Correcting any drift the check finds on its first run.** `chore-0033` corrected these figures on
  2026-08-28, so a find is either a real one or a false positive and both are worth reporting rather
  than quietly fixing.
- **`ROADMAP.md`**, which is [`chore-0072`](done/chore-0072-a-gate-for-the-roadmap-staleness-class-chore-0066-mapped.md).
  If the two checks merge, that task says so and one of them absorbs the other; do not build half of
  it here.
- Adding or removing any figure from `docs/spec/README.md`. Whether that document should carry derived
  arithmetic at all is a real question and it is the author's, not a side effect of writing a checker.
- The wider count-shaped-claim class in task files and skill bodies. Those are prose in files this
  check does not read.

## Implementation notes

**The false-positive risk is the design problem, as it was for `chore-0049`.** A parser reading counts
out of a markdown table will over-fire the first time someone reformats the table, and a check that
cries wolf gets switched off. Prefer failing only where a number is unambiguously parsed and
unambiguously wrong, and report anything it could not parse as unchecked rather than as passing.

Read `chore-0049`'s `## Decisions` before choosing the host. It records why a form that cannot be
checked reliably is reported unchecked, and its partition-once structure exists because the first
delivery printed a breakdown that did not sum. That failure is worth not repeating in a task whose
entire subject is arithmetic that does not add up.

`depends_on: [chore-0033]` is a file collision rather than a logical one: that task rewrites three of
these five figures, and building the check against the pre-`chore-0033` numbers would measure the
wrong thing.

If the check needs `docs/spec/README.md` to carry a machine-readable marker, that is a change to the
document's shape and belongs in the report as a proposal, not in the diff.

## Risks and rollback

A new check plus a possible gate, so this section is required.

The realistic failure is the one this repository keeps meeting: a checker that looks like coverage and
is not. Bound it by reporting what it declined to parse, and by running it over the current file
before wiring it into anything.

Adding a gate moves `run-checks.py`'s summary arithmetic, which `tests/test_run_checks.py` pins.
`chore-0049` updated that pin on 2026-08-28, so read what is there rather than what an older task
describes. The `Gate set` surface element no longer pins the number of gates, so no contract amendment
is needed for an added gate, which is what `chore-0049`'s amendment was for.

Reversible by reverting one commit. Nothing depends on the check existing.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A per-spec `Scenarios` count that disagrees with the distinct `S-NNN` ids in that spec is
      reported, proven by a test that fails against a fixture.
- [ ] The closing paragraph's sum and subtraction are recomputed, and a wrong one is reported.
- [ ] The run states what it recomputed and what it did not, with the arithmetic rather than the claim,
      and every printed breakdown sums to the total it sits under.
- [ ] Run over the current `docs/spec/README.md`, the output is recorded in the closeout, whether it is
      empty or not.
- [ ] The host decision is recorded with the rejected option, including whether this and `chore-0072`
      are one checker or two.
- [ ] No figure in `docs/spec/README.md` is added or removed by this task.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
