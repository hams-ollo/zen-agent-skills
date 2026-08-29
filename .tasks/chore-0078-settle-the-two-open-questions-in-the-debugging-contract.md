---
id: chore-0078
title: Settle both open questions in the systematic-debugging contract before anything is built against it
type: chore
status: open
priority: P1
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: []
spec: docs/spec/systematic-debugging.md
scenarios: []
touched_files:
  - docs/spec/systematic-debugging.md
  - docs/spec/README.md
created: 2026-08-29
---

## Problem

[`systematic-debugging.md`](../docs/spec/systematic-debugging.md) was approved on 2026-08-19 carrying
two questions its own Open Questions section declines to answer. The second is genuinely deferrable.
**The first blocks implementation and nothing has noticed yet**, because no task has been written
against this contract until now.

Open Question 1 asks whether the skill may run code and add temporary instrumentation, and where that
instrumentation may live. The contract already argues why it must be allowed to do something:
"Diagnosis without execution is reading, and reading is what produces the guesses this contract
exists to prevent."

It collides with `S-005`, whose Then is an observable rather than an intention:

> it returns the diagnosis, performs no repair, and no tracked file differs from its state at the
> start of the run

Those two are satisfiable together in more than one way, and the contract does not say which:

- **Instrument in place and clean up afterwards.** Satisfies `S-005` on every run that completes.
  Portable to any repository. Leaves the author's working tree carrying debug edits on any run that
  dies partway, and the test passes on every successful run, so the failure only ever appears when
  something else has already gone wrong.
- **Work only in a disposable copy.** Cannot leave a mess even on a crash, because no tracked file
  was ever the thing being edited. Costs portability, since not every target repository is a git
  repository with worktrees available.

An implementer handed this contract as it stands has to pick one, and picking it in an implementation
means the contract's most consequential safety property is decided by whoever writes the code first.
That is what a contract exists to prevent.

Open Question 2 asks for the default investigation bound `S-004` terminates on. The contract's own
recommendation is right and this task adopts it rather than reopening it: the number is a tuning
value, `S-004` already constrains that a bound exists, is declared, and terminates the run, and
fixing a number in a contract makes every future retune an amendment.

## Scope

**In scope:** answer both questions in the contract itself, so the answer is a commitment rather than
an implementation detail.

- **Open Question 1: the disposable-copy answer, decided by the author on 2026-08-29.** The skill may
  execute code and add instrumentation, and may do so only against a copy it made for the purpose,
  never against the tracked files in place. State it as a behavioral property a reader can check, not
  as a mechanism: naming `git worktree` in the contract would fix an implementation and would be
  false for a target repository that is not a git repository.
- **The portability cost, stated in the contract rather than discovered by an adopter.** A repository
  offering no way to make a working copy is a case this skill has to answer for, and the honest
  answer belongs in Constraints or in a scenario rather than in a task file nobody reads later.
- **Whether the answer needs its own scenario, or amends `S-005`.** Decide and say why. A new
  `S-014` makes the property independently checkable and grows the contract; folding it into `S-005`
  keeps the count at 13 and buries a second claim inside a scenario about refusing to fix. Prefer the
  new scenario unless the reason against it is better than this sentence.
- **Open Question 2: adopt the contract's own recommendation.** The number stays out. Record that it
  was considered and left to the skill, so a later reader does not reopen it as an oversight.
- **The amendment discipline `chore-0061` established**: a dated amendment note, `status:` left
  reading `approved` per the convention in [`docs/spec/README.md`](../docs/spec/README.md), and a row
  added to that file's re-approval queue. Update the scenario count in that file's table if a
  scenario was added.

**Out of scope:**

- Writing the skill. That is `feat-0061`, which depends on this.
- The conformance matrix. `systematic-debugging` has no matrix yet and the spec README already
  records it as "conformance owed at closeout", which is `feat-0061`'s closeout, not this one.
- Reopening any of the thirteen existing scenarios. This task answers questions the contract asked
  itself and changes nothing it already decided.

## Implementation notes

Read the Constraints section before writing, because the answer may already be half-stated there and
a second statement that disagrees with it is worse than none.

The phrasing worth aiming for is the one `S-005` already uses: an observable a reader can check
without knowing the implementation. "No tracked file differs from its state at the start of the run"
is that shape. "Uses a git worktree" is not.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Open Question 1 is answered in the contract, and the Open Questions section either no longer
      carries it or records it as settled with the answer's location.
- [ ] The answer is stated as a checkable property, and names no specific tool as required.
- [ ] The portability case, a repository offering no way to make a working copy, is answered
      somewhere a reader of the contract will find it.
- [ ] Open Question 2 is recorded as settled by adopting the contract's own recommendation, with the
      reason, so it is not reopened later as an oversight.
- [ ] A dated amendment note is present, `status:` still reads `approved`, and
      [`docs/spec/README.md`](../docs/spec/README.md) carries the re-approval queue row.
- [ ] The scenario count in the spec README's table matches the contract.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
