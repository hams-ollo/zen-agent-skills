---
id: chore-0061
title: The cloud-executable contract does not say what a passing gate must carry, which is why a report over nothing read as a clean run
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E: delegated execution"
depends_on: [bug-0045]
spec: "docs/spec/cloud-executable.md"
scenarios: []
touched_files:
  - docs/spec/cloud-executable.md
  - docs/spec/cloud-executable.conformance.md
  - docs/spec/README.md
created: 2026-08-22
---

## Problem

[`bug-0045`](bug-0045-run-checks-discards-every-gate-coverage-line-on-a-passing-run.md) made
`run-checks.py` carry each gate's coverage line on a passing run, so a gate that examined nothing now
says so. Before it, a repository with zero skills, zero tests and zero task files produced six `ok`
lines **byte-identical** to a full clean run.

**The contract permitted that.** `cloud-executable.md`'s `Output` surface row says one line per gate
naming it and its outcome, the failing gate's own output where one failed, then a summary. A passing
gate's coverage is not mentioned, so discarding it was conformant. The defect was in the contract
before it was in the code.

That matters more here than in most specs, because this is the command the whole kit rests on: every
task closes against it, every CI cell runs it, and both unattended cloud proof runs were verified by
it. A contract that lets the acceptance command emit an identical report over a full repository and
over an empty one is not describing an acceptance command.

`bug-0045` recorded the owed amendment as unreconciled in
[`cloud-executable.conformance.md`](../../docs/spec/cloud-executable.conformance.md) rather than writing
it, which was correct: amending an approved contract is not a delegated agent's call. This is that
amendment.

## Scope

**In scope:** state in the contract what a passing gate's output must carry.

- A scenario for it, taking the next free `S-NNN` read from the spec rather than assumed.
- The `Output` surface row widened to describe the coverage line.
- **State the property, not the implementation.** `bug-0045` selects the gate's last non-blank line
  carrying a digit, with fallbacks. That is a mechanism and it will change; what the contract should
  fix is the observable property, which is roughly that two passing runs over different scopes must
  not produce identical reports. Write what a reader can check from the output.
- The dated amendment note, `status:` left reading `approved` per the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md), and a row added to that file's re-approval queue.
- Reconcile the matrix rows the amendment closes, and restate the coverage-proof arithmetic with the
  numbers rather than asserting it.

**Out of scope:**

- `scripts/run-checks.py` and `tests/test_run_checks.py`. The implementation is `bug-0045`'s and is
  not reopened. **If writing the scenario reveals the behaviour is wrong, that is a finding to report,
  not a code change to make**, and it is the most valuable thing this task could produce.
- Making any gate fail on zero inputs. `bug-0045` rejected that with a measurement: a freshly
  scaffolded repository legitimately has no task files, and `init-worktracking` ships `validate.py`
  into exactly that state. Its `## Decisions` records the rejection and the third shape it also
  considered, a per-gate declared floor.
- [`chore-0032`](chore-0032-links-guard-fires-per-run-not-per-pattern.md), which is about
  `.tasks/validate.py`'s exit code rather than this report's content. `bug-0045`'s agent checked and
  reported that its change does not subsume it. It stays open.
- Granting the re-approval, which is the author's.

## Implementation notes

Read `bug-0045`'s `## Decisions` before writing. It weighed surfacing against failing and recorded why
a floor encoded in the aggregator would be a second source of truth about each gate's minimum input.
A scenario written without that reasoning will describe a stricter command than the one that shipped.

Check whether the queue already carries a `cloud-executable` row before adding one. It did as of
2026-08-21, from `chore-0051`. If so, extend it rather than adding a second, and the seven-spec count
may not move. Work that out from the file, and note that the count sentence and the "carry more than
one" sentence may both need attention. Per `house-style.md`, do not introduce a new count of the
table's rows anywhere in that document.

## Decisions

**Rejected: stating the property over each gate rather than over the whole report.** The scope's
"two passing runs over different scopes must not produce identical reports" reads naturally as a
per-gate rule, and a per-gate rule is falsified by what ships. Measured 2026-08-27: `lint skills`
prints a byte-identical coverage line over a tree of 20 skills and one of 21, because the rule reaches
`validate-skills.py`'s supporting-file line and not `Checked N skill(s)`. Writing the per-gate wording
would have put a divergence into an approved contract in a task forbidden from touching `scripts/`.
`S-020` therefore states the property over the report, and the matrix records both the alternative and
the measurement.

**Rejected: appending the clause to `S-001` instead of adding a scenario.** The matrix named `S-001`
as "the natural home" for it. A new id was taken instead, so the `S-001` row keeps auditing text
approved on 2026-08-07 and unchanged since, and so the new clause can be cited on its own by a task,
a test, or a later matrix.

**A premise that turned out false: `chore-0057` was not the last prose row-count in
[`docs/spec/README.md`](../../docs/spec/README.md).** Its commit message calls it "the last prose count
predating the rule", and `house-style.md` cites it as the one still open. The re-approval queue's own
lead sentence still counted that table's rows twice, "seven specs" and "Three of them carry more than
one", and this amendment falsified the second by giving `cloud-executable` a second amendment. Both
counts are removed and the rows named instead, which is what `chore-0056` and `chore-0057` did to the
paragraphs on either side of them.

**Seam left open deliberately: the `lint skills` coverage line is measured here and not fixed.**
`scripts/` is out of scope, and the line is a seam `bug-0045` disclosed rather than a defect it hid.
The measurement is recorded in the matrix's observations, and the remedy belongs in the gate, which
would print the line it most wants shown last.

## Risks and rollback

A contract plus two sibling documents, so this section is required.

The risk is writing the mechanism into the contract. `bug-0045` itself found that the task file's
premise about "the last non-blank line" was false for three of seven gates, and pinned a different
rule. A scenario naming that rule would need amending the next time a gate changes what it prints,
which is exactly the churn an amendment is supposed to prevent.

Reversible by reverting one commit. `status: approved` is left as the convention requires, so no
verification run is made unanswerable by the change.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `cloud-executable.md` carries a scenario for what a passing gate's output must include, with an
      id taken from the spec rather than assumed.
- [x] The `Output` surface element describes it.
- [x] The scenario states an observable property rather than naming `run-checks.py`'s selection rule,
      checked by reading it back and asking whether a different implementation could satisfy it.
- [x] A dated amendment note is added, `status:` still reads `approved`, and the re-approval queue
      reflects it without introducing a count of the table's rows.
- [x] The matrix's unreconciled entry for this amendment is closed and the coverage-proof arithmetic
      is restated with the numbers.
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
