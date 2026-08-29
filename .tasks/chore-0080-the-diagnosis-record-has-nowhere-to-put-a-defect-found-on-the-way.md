---
id: chore-0080
title: The diagnosis record has nowhere to put a second defect the investigation uncovered
type: chore
status: open
priority: P2
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: [feat-0062]
spec: docs/spec/systematic-debugging.md
scenarios: []
touched_files:
  - docs/spec/systematic-debugging.md
  - docs/spec/README.md
  - .agents/skills/systematic-debugging/
  - tests/
created: 2026-08-29
---

## Problem

The diagnosis record in [`systematic-debugging.md`](../docs/spec/systematic-debugging.md)'s Proposed
Surface has ten fields, and every one of them is about **the defect the run was pointed at**:
`symptom`, `reproduction`, `hypotheses`, `root_cause`, `confirming_observation`, `implicated_files`,
`regression_observable`, `missing_input`, `bound_reached`, and the `verdict` itself.

**An investigation that is any good will find things it was not looking for, and the record has
nowhere to put them.** This is not hypothetical. `feat-0062`'s dogfood run, the contract's first real
use, named its cause and also established a second, independent defect on the way: in
[`serve.py`](../scripts/observatory/serve.py)'s `_report`, `db.connect` is wrapped in
`except db.StoreUnusable` and the `build(conn)` call below it is wrapped only in `try/finally`, so an
`OperationalError` raised inside `build` propagates out of `do_GET` with no response written and the
client gets a dropped connection rather than a 500. That is a different defect from the cause, it is
worth a task of its own, and it reached the record only because the author thought to write a prose
section for it.

**The autonomy lens already requires the disclosure that this shape makes structurally awkward.**
Rule A5 says opportunistic work is disclosed and that "`none` is a valid answer and is not the same
as silence." A record with no field for it cannot distinguish a run that found nothing incidental
from a run that found something and did not mention it, which is exactly the distinction A5 exists to
force. `fix-batch`'s delegate report has a findings field for the same reason and says so.

## Scope

**In scope:** decide whether the record gains a field, and amend the contract if it does.

- **The decision, with its reason.** A field is not obviously right. Against it: the record is
  deliberately about one defect, and a general findings bag invites a run to pad it. For it: A5
  already demands the disclosure, the fields are the record's only structured surface, and prose that
  an author has to think to add is the thing A5 calls silence.
- **If it gains one**, the amendment discipline `chore-0061` established: a dated note, `status:`
  left reading `approved`, a row added to [`docs/spec/README.md`](../docs/spec/README.md)'s
  re-approval queue, and the scenario count updated there if a scenario is added. Decide separately
  whether the field needs a scenario of its own or only a row in the Proposed Surface table;
  `chore-0078`'s reasoning about what a scenario buys over a table row applies directly.
- **The skill and its tests move with the contract.** `tests/test_systematic_debugging.py` asserts
  the record's field set as an **exact** set, so adding a field to the contract without adding it
  there fails, which is the gate working.

**Out of scope:**

- **Fixing the `serve.py` defect that prompted this.** It is a separate task and this one is about
  the record's shape, not about that bug.
- Any other change to the record's fields. This task answers one question.

## Implementation notes

Two shapes were considered while filing this and neither is obviously better, which is why the
decision is the deliverable rather than the edit.

A single `incidental_findings` field, present always, whose empty value is an explicit `none` rather
than an omission. That matches A5 exactly and matches `fix-batch`'s findings field, and it is the
only one of the ten fields that would be required to carry a word when it has nothing to say.

Or nothing in the record, and a sentence in the skill's procedure telling a run to report an
incidental defect separately and never to fold it into `root_cause`. Cheaper, keeps the record about
one defect, and gives back exactly the silence A5 forbids.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The contract says what a run does with a defect it uncovered but was not pointed at, either by
      carrying a field for it or by stating that it does not and why.
- [ ] If the record gained a field, the skill's record table and the exact-set assertion in
      `tests/test_systematic_debugging.py` both carry it, and the conformance matrix has a row.
- [ ] If it did not, the reason is recorded where a later reader meets the question, not only in this
      task file.
- [ ] Amendment discipline followed if the contract changed: dated note, `status: approved`, a
      re-approval queue row, and the spec README's scenario count matching the contract.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
