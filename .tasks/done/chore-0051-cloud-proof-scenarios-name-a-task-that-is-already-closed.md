---
id: chore-0051
title: The cloud proof scenarios and their runbook both dispatch bug-0018, which closed the day after they were written
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E: delegated execution"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-017", "S-018"]
touched_files:
  - docs/spec/cloud-executable.md
  - docs/spec/cloud-executable.runbook.md
  - docs/spec/cloud-executable.conformance.md
  - docs/spec/README.md
created: 2026-08-20
---

## Problem

`S-017` and `S-018` in [`cloud-executable.md`](../../docs/spec/cloud-executable.md) name
[`bug-0018`](bug-0018-reinstall-destroys-an-adopter-edited-lens.md) by name in their **Given**
clauses, and [`cloud-executable.runbook.md`](../../docs/spec/cloud-executable.runbook.md) carries a
paste-ready prompt that dispatches it.

**`bug-0018` is `status: done`.** It was implemented locally and merged as pull request #23 on
2026-08-08, the day after the runbook was written. So the contract specifies a proof run that cannot
be performed as written, and the instruction sheet hands a person a prompt that tells a cloud session
to implement a task that is already closed.

The conformance matrix already knows half of this. Its observation "Why `bug-0018` landing on a
`claude/` branch is not evidence for S-017" states correctly that `S-017`'s Given is that task
**dispatched to a cloud session**, and that a local implementation does not satisfy it. What nothing
recorded is the consequence: once the task closed, the scenario stopped being runnable at all.

**The failure signature is the one this repository names as its own enemy.** Nothing reported it and
nothing could. All seven gates pass, `validate.py --strict` passes because the runbook's link to
`bug-0018` correctly resolves into `done/`, and the link is *more* valid after the move, not less.
The matrix, the spec, and the runbook each read correctly on their own; only the three together are
wrong, and no check reads them as a set.

Found 2026-08-20 while preparing the Phase 4 cloud session, by reading `S-017`'s Given against the
backlog rather than trusting the runbook's preconditions section, which asserts its preconditions
still hold and does not mention the task's status.

## Scope

**In scope:** make the proof run specifiable and the runbook runnable, against a task that is
actually open.

- Reword `S-017` and `S-018`'s **Given** clauses to name
  [`bug-0020`](../bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md), chosen by the author
  on 2026-08-20 as the substitute. It is the closest available: a code defect in `scripts/install.py`,
  the exact file `S-018`'s "the unfixed `install.py`" names, so that clause stays literally true, and
  its first acceptance criterion already requires a test failing against the current message.
- Add the dated amendment note and leave `status: approved`, per the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md), and add the row to that file's re-approval queue.
- Replace the runbook's stale prompt with one that dispatches the substitute. The prompt given in
  chat on 2026-08-20 is the starting point, not a specification; re-derive it against the task file.
- Correct the runbook's "Before you start" table, which asserts preconditions without checking that
  the task it dispatches is open.

**Out of scope:**

- Running the proof session. That needs a person and is what this unblocks, not what it does.
- `S-019`, whose Given is "the same dispatched session" and which therefore follows `S-017` without
  naming a task itself. Confirm that reading rather than assuming it; if it does name one, it is in
  scope after all.
- Generalising the Given to a **class** of task rather than a named one. Considered and not chosen:
  `S-018`'s own body argues the proof task must be a code defect rather than a skill-body change,
  because a prose task's acceptance command passes whatever the prose says. That argument wants a
  named task whose failing-first test is real and checkable, and a class would reopen it. Record the
  rejection rather than silently narrowing.
- Reclassifying `S-017` to `S-019` in the conformance matrix. They stay **Not-built**: this task makes
  the run specifiable, and only the run itself can move them.
- `bug-0020`'s own content, which is correct as written and is not amended by being chosen.

## Implementation notes

Read the matrix's observation on `bug-0018` before touching the spec. It is the prior art for this
exact reasoning and the amendment should agree with it rather than restate it differently.

The runbook's second prompt, the observation-only reachability run for `S-008`, is **not** affected
and must not be edited. It names no task, its precondition is a commit rather than a branch
(`git merge-base --is-ancestor 7703632 HEAD`), and that precondition holds on `developer` today.
It is the one part of the runbook that survived the drift, because it was written to depend on a
commit rather than on a name.

Take the next free scenario id only if a new scenario is genuinely needed. This is expected to be a
reword of two existing Givens rather than an addition, and adding `S-020` for something that is an
edit would inflate the contract.

## Risks and rollback

Three documents and a contract, so this section is required.

The real risk is amending the contract twice. If the proof run happens before this lands, the run
will have been performed against a task the spec does not name, and this amendment would then be
describing history rather than specifying work. Sequence this **before** the cloud session, or accept
that the matrix records `S-017` and `S-018` as diverged and say so plainly.

Reversible by reverting one commit. `status: approved` is left as the convention requires, so no
verification run is made unanswerable by the change.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `S-017` and `S-018`'s Given clauses name an **open** task, verified by checking that task is not
      in `.tasks/done/` at the time of the edit.
- [x] `S-018`'s "the unfixed `install.py`" clause is still literally true of the named task's
      `touched_files`, checked rather than assumed.
- [x] The runbook's main prompt dispatches the same task the spec names, and the two agree word for
      word on the task id.
- [x] The runbook's observation-only reachability prompt is byte-identical to its current form.
- [x] A dated amendment note is added, `status:` still reads `approved`, and a row is added to
      `docs/spec/README.md`'s re-approval queue.
- [x] `S-017` to `S-019` remain **Not-built** in the conformance matrix, since no run has happened.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
