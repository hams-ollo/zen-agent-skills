---
id: bug-0049
title: The citation gate skips a three-column matrix in silence, and four closed tasks reported it green
type: bug
status: done
priority: P1
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - scripts/check-citations.py
  - tests/test_check_citations.py
  - docs/spec/agent-observatory.conformance.md
created: 2026-08-29
---

## Problem

[`check-citations.py`](../../scripts/check-citations.py) audits nothing in
[`agent-observatory.conformance.md`](../../docs/spec/agent-observatory.conformance.md), reports `0
unresolved`, and exits 0. It has done so since that matrix was created, across four closed tasks
that each cited the gate as green over it: `feat-0053`, `feat-0054`, `feat-0055`, and `feat-0060`.

**The cause is one comparison.** `_is_body_row` requires `len(cells) >= 4`. Every other matrix uses
the house shape `| Section | Item | Status | Evidence | Note |`, which splits to five cells. That
one uses `| Scenario | Status | Evidence |`, which splits to three, so every row of it is rejected
as a body row and the file contributes zero citations.

**Reproduced rather than reasoned about.** Injecting into that matrix a test name that is defined
nowhere and a symbol that exists nowhere, then running the checker, produces:

    Matrix citations: 0 unresolved.
    396 audited + 186 unaudited = 582 extracted, over 11 matrix file(s) holding 10 with citations.

Byte-identical to the run without the injection, and exit 0. The 66 real citations in that file
(50 test names and 16 symbols) were verified by hand instead and all 66 resolve, so the matrix is
sound. The gate is what is broken.

**This is the defect the checker's own docstring says it was built not to have.** Its exit-code
contract already reserves 2 for "no matrix was found, so the question was never asked", and
explains it: "A checker that reports `ok` over a directory holding nothing is the exact defect this
task belongs to a group of, so this one is asked the degenerate question at birth." A matrix holding
nothing is the same question one level down, and the answer there is currently `ok`.

The one signal that exists is the summary's `holding 10 with citations` against `11 matrix
file(s)`. That line varies correctly and nobody read it, which is what makes this a reporting bug
rather than a missing measurement.

## Scope

**In scope:** making a matrix that yields no decidable citations impossible to mistake for a matrix
that passed.

- Report every matrix that contributed zero citations, by name, rather than leaving the fact to be
  inferred from two counts in one line.
- Decide and implement what such a matrix does to the exit code, given the contract already
  distinguishes "could not run" (2) from "a citation is dead" (1).
- Audit `agent-observatory.conformance.md`'s rows, whether by widening what counts as a body row or
  by another route the fix chooses.
- A test that fails if the gate ever again reports `ok` over a matrix it did not read.

**Out of scope:**

- **Reshaping `agent-observatory.conformance.md` to fit the parser.** Editing the document so the
  tool will look at it inverts the relationship: the checker exists to serve the matrices, and a
  three-column matrix is a legitimate shape. Fix the checker.
- **Widening what the checker decides.** The three decidable forms and the deliberate preference
  for few high-confidence failures are `chore-0049`'s design and stay as they are. This is about
  coverage reporting, not about deciding more.
- **The citations in any other matrix.** If the fix newly audits content, report what it finds;
  correcting another spec's rows is that spec's work.

## Implementation notes

**The likely fix is two changes, and the second matters more than the first.** Admitting three-cell
rows makes the citations visible. Reporting a zero-citation matrix by name is what stops the next
shape nobody anticipated from failing the same way silently. A fix that does only the first leaves
the class open.

**Check the blast radius before choosing the exit code.** Five matrices already contain three-cell
tables alongside their five-cell ones (`build-adapters`, `doc-sync`, `install`, `spec-author`,
`validate-skills`), and those three-cell tables are currently skipped too. Admitting them will
extract citations that have never been audited, and some may not resolve. That is the fix working,
but it lands as a red gate on documents this task did not set out to change, so measure it before
deciding whether zero-citation is exit 1, exit 2, or a reported line that does not change the code.

**`agent-observatory.conformance.md`'s 66 citations were verified by hand on 2026-08-29 and all 66
resolve**, so the newly audited totals for that file should come back clean. If they do not, the
hand check was wrong and that is worth knowing.

**The summary line is load-bearing and carries a comment saying so.** `run-checks.py` surfaces the
last line carrying a digit beneath this gate's status word, and `bug-0045` and `chore-0064` are
cited there for the rule that a line which cannot vary reports coverage it does not have. Whatever
is added has to keep that property rather than append a line that is constant.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test injects a citation that resolves nowhere into a three-column matrix and asserts the run
      reports it, rather than exiting 0 over it. This is the reproduction above, as a test.
- [x] A test asserts that a matrix contributing zero citations is named in the output, so the
      difference between "audited and clean" and "never read" is visible without arithmetic.
- [x] `agent-observatory.conformance.md`'s citations are audited: the run's audited total rises by
      the count that file contributes, and the arithmetic still closes.
- [x] The summary line still varies with what was examined, per the comment in `render`.
- [x] Existing tests still pass, unchanged in intent.
- [x] Any citation the fix newly audits and finds dead is reported in the task's closeout, whether
      or not it is corrected here.

## Decisions

- **Columns are located by their heading rather than by position**, so a matrix's layout is a
  property of the matrix instead of an assumption in the checker. Widening the fixed index from
  four cells to three was rejected: it fixes the one shape that exists and leaves the next one
  failing the same way.
- **A matrix with no recognisable evidence column exits 2 and is named. A matrix that is readable
  and cites nothing exits 0 and is named.** The split is deliberate. Failing the second would break
  a spec whose scenarios are all not-built, which has nothing to cite yet, and that false alarm is
  the failure this checker's whole design is arranged to avoid.
- **The blast radius the task warned about did not materialise, and it was measured rather than
  assumed.** Every one of the eleven matrices has exactly one table carrying an `Evidence` column;
  the secondary tables (`Scenario | Covering test | Note`, `Item | Disposition | Reasoning`) have
  none, so a header-driven parse skips them exactly as the old index-based one did. Body-row counts
  are identical for all ten five-column matrices and go from 0 to 22 for the three-column one.
- **A premise in this task was too pessimistic.** It said admitting three-cell rows "will extract
  citations that have never been audited, and some may not resolve", across five other matrices.
  Those five carry three-cell tables with no evidence column, so nothing in them changed at all.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
