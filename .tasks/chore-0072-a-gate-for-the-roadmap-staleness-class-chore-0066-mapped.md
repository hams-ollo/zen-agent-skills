---
id: chore-0072
title: The ROADMAP staleness class is now mapped to two mechanical shapes, and building the gate is the part chore-0066 was forbidden to do
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0066]
touched_files:
  - scripts/run-checks.py
  - tests/test_run_checks.py
created: 2026-08-27
---

## Problem

[`chore-0066`](done/chore-0066-the-roadmap-has-five-verified-staleness-defects-and-no-gate.md)
corrected nine staleness defects in [`ROADMAP.md`](../ROADMAP.md) and was explicitly forbidden to
build a gate for them, because that class is what ROADMAP Epic B item 19 holds and answering it
inside a correction pass would presuppose the artifact that item declines to presuppose. Its Scope
said the most valuable thing the work could produce beyond the corrections was a report on what the
gate should be. It produced one, and the finding is that **the class is smaller and more mechanical
than it looks**.

Every one of the nine corrections is one of exactly two shapes, and neither needs judgment:

- **An id whose prose state contradicts its directory.** Six of the nine were an id sitting in
  `.tasks/done/` inside a sentence reading "Scoped as", "filed rather than fixed", or "pending". A
  checker needs the id, the directory it is in, and a small vocabulary of open-state phrases in the
  same sentence.
- **A quoted shell command whose stated output is re-runnable.** `git ls-files .claude` was written
  into the file together with its result, so the check is to run it and diff. That one had been false
  since the day the epic introducing it was written, falsified by item 2(b) of the same epic.

The `Last updated:` header is a third shape and is the argument for deleting it rather than checking
it, since a date nothing derives is a claim nobody maintains.

**The bound matters as much as the coverage, and it is why this task exists rather than a bigger
one.** Nothing mechanical would have caught the defect that mattered most in that pass: Epic E item 2
restating an acceptance bar that `docs/spec/cloud-executable.md` had repointed to a different target
eight days earlier. Catching that needs reading the contract the roadmap restates, which is a
different capability. **A gate here can catch the bookkeeping class entirely and the
restated-contract class not at all**, and it has to say so, or a green run will be read as the file
being current.

This is the sixth member of the guard-that-does-not-guard group `chore-0049` names, and the pattern
behind the group is
[`chore-0063`](done/chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** a check that `ROADMAP.md`'s bookkeeping claims match the repository.

- The id-versus-directory shape, over every task id the file names. `chore-0066` measured the
  population: 77 unique ids as of its pass, and its sweep is the reference implementation to beat.
- The re-runnable-command shape, or an explicit decision not to build it. There is exactly one
  instance today, which is thin evidence for a general mechanism; deciding it is not worth building
  and saying why is a legitimate outcome.
- **A stated bound in the output**, naming what the check does not cover, so a passing run is not
  read as "the roadmap is current". Follow the audited-and-unaudited habit `spec-conformance` uses
  and `chore-0049` adopts.
- The `Last updated:` header decision: check it, derive it, or delete it. One of the three, with the
  rejected two recorded.

**Out of scope:**

- The restated-contract class, named above. If this work suggests how to catch it, that is a finding
  and a separate task; do not build half of it here.
- Correcting any staleness the checker finds on its first run. `chore-0066` did that pass. A find on
  a file it just cleaned is either a real one or a false positive, and both are worth reporting rather
  than quietly fixing.
- `CHANGELOG.md`, which is append-only and whose entries are records rather than claims about current
  state.
- Discharging any hold in `ROADMAP.md`. Item completion is the author's.

## Implementation notes

**Weigh where this belongs before writing it.** `.tasks/validate.py` already walks the task
directories and already resolves links, so it knows both halves of the id-versus-directory question
and is the cheaper host. `scripts/run-checks.py` is where a new gate gets wired either way, which is
what `touched_files` assumes. If the work chooses the `validate.py` host instead, correct
`touched_files` and record why.

**The false-positive risk is the design problem**, exactly as it was for `chore-0049`: a phrase-matching
check over prose will over-fire, and a check that cries wolf gets disabled within a week. Prefer a
small vocabulary of unambiguous open-state phrases over a general one, and report what it declined to
judge.

Note that `chore-0049` also declares `scripts/run-checks.py` and `tests/test_run_checks.py`. The two
cannot share a wave, and whichever lands second inherits the other's gate-count pin in
`tests/test_run_checks.py`.

## Risks and rollback

More than one module, since a check and a `run-checks.py` gate are both in play, so this section is
required.

The realistic failure is the one `chore-0049` names: a noisy checker a later task disables, which is
worse than no checker because it looks like coverage. Bound it by reporting what it declined to judge,
and by running it over the current `ROADMAP.md` before wiring it into any gate.

A new gate also moves `run-checks.py`'s own summary arithmetic, which `tests/test_run_checks.py`
pins. Expect to update that pin deliberately rather than discovering it.

Reversible by reverting one commit. Nothing depends on the check existing.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] An id named in `ROADMAP.md` in an open-state sentence while sitting in `.tasks/done/` is
      reported, proven by a test that fails against a fixture.
- [ ] The run states what it checked and what it declined to judge, with the arithmetic rather than
      the claim.
- [ ] The output or its documentation names the restated-contract class as out of the check's reach.
- [ ] Run over the current `ROADMAP.md`, the checker's output is recorded in the closeout, whether it
      is empty or not.
- [ ] The `Last updated:` header decision is recorded with its rejected alternatives.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
