---
id: feat-0045
title: Give the repository one committed command that answers whether a change is acceptable
type: feat
status: open
priority: P1
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"]
touched_files:
  - .github/workflows/checks.yml
  - AGENTS.md
created: 2026-08-07
---

## Problem

Nothing in this repository answers "is this change acceptable" in one step. The seven gates live only
as seven separate steps in [`checks.yml`](../.github/workflows/checks.yml), so the only ways to get
the answer are to push and read CI, or to run seven commands by hand and remember all seven.

Measured on 2026-08-07: the 97 acceptance chains across `.tasks/` and `.tasks/done/` run one, two,
three, or five commands, and **none of them runs the seven gates.** So a task file's own acceptance
command routinely passes on work that CI then fails.

For a person that is friction. For an agent working unattended it is disqualifying, because it cannot
push and wait for a human to read the result, and it has no way to know the three commands its task
named are not the seven that gate the merge.

Contract: [`cloud-executable.md`](../docs/spec/cloud-executable.md), `S-001` to `S-007`.

## Scope

**In scope:** one committed standard-library Python script that runs the seven gates and answers with
one exit code, and rewiring CI to call it instead of restating them.

Files this creates, which are deliberately absent from `touched_files` (see Implementation notes):

- `scripts/run-checks.py`
- `tests/test_run_checks.py`

**Out of scope:**

- **Changing which gates exist.** This wraps the seven in `checks.yml` as they are. Adding or
  removing one is a separate decision.
- **Reducing the CI matrix.** It stays three operating systems by two Python versions. The script
  answers for one cell and says so, per `S-006`.
- **Rewriting the backlog's acceptance chains** to call the new command. Open question 2 in the
  contract recommends against doing it here, and the chains stay valid because the command is a
  superset of them.
- Any flag. The contract's Proposed Surface says no flags, and a knob invites the divergence between
  callers that `chore-0029` closed.

## Implementation notes

**`touched_files` lists only files that already exist**, because `.tasks/validate.py --strict`
promotes a missing path to an error (`validate.py:456`) and CI runs `--strict`. This contradicts the
`new-task` skill, which says to list a test file at the path it should be created at.
[`feat-0038`](done/feat-0038-hooks-module-and-delegation-reminder.md) hit the same thing and resolved
it the same way, listing only pre-existing files while creating the whole hooks module. The
contradiction is real and is worth its own task; do not try to fix it here.

**Exit codes are 0, 1, and 2, and 2 outranks 1.** That is not a new convention: `install.py --check`
and `check-provenance.py` both already use it, and both put "could not answer" above "answered no",
because a run that could not ask the question must not read as having answered it.

**Every gate runs even after one fails** (`S-002`). Do not stop at the first failure. The reason is in
the contract: an unattended agent gets one round trip, and a report naming only the first failure
spends another.

**The install gate writes outside the throwaway home, and `S-004` is worded for that.** `install.py`
writes its manifest to `scripts/.install-manifest.json`, which is gitignored and is the tool's own
record. The property to preserve is that no *installation* outside `./.tmp/zen-home` is disturbed,
which is what `bug-0003` established when `--uninstall` was scoped to the home it was given.

**Prior art for the report shape** is `install.py`'s `check()`: one line per item with its status,
then a summary with counts. Mirror it rather than inventing a second format.

## Risks and rollback

Required: this touches more than one module (a new script, the CI workflow, and `AGENTS.md`).

- **The failure that costs most is a script that reports success while skipping a gate.** That is
  strictly worse than the status quo, because today nobody believes the short chains are complete,
  and afterwards everyone would believe this one is. `tests/test_run_checks.py` must assert the gate
  set is complete, not merely that the script exits zero.
- **CI is the only thing currently enforcing the seven gates.** Replacing seven steps with one means a
  bug in the script silently narrows what CI checks. Land the script and its tests first, confirm the
  wrapped run passes on all six matrix cells, and only then delete the seven steps.
- Rollback is one revert. Nothing persisted changes format, and restoring the seven steps restores
  the previous enforcement exactly.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] `scripts/run-checks.py` runs all seven gates, names each with its outcome, and exits zero only
      when every one passed (`S-001`).
- [ ] A failing gate is named with its output and the remaining gates still run; exit 1 (`S-002`).
- [ ] A gate that cannot execute is reported as unable to run rather than as passed or failed, and
      exits 2 regardless of the other gates (`S-003`).
- [ ] A test pins the seven gate names and their commands, so dropping one fails a test rather than
      silently narrowing what is checked. (Corrected 2026-08-07, before implementation began: this
      criterion first said the test should assert the gate set matches the steps in `checks.yml`,
      which cannot hold, because `S-005` removes those steps in the same change. The guard has to be
      a pinned list in the test, deliberately a second source of truth.)
- [ ] A test asserts `checks.yml` invokes the command and does not separately restate any gate, so a
      divergent copy cannot be reintroduced later (`S-005`).
- [ ] No installation outside `./.tmp/zen-home` is created, modified, or removed by a run (`S-004`).
- [ ] `checks.yml` invokes the command instead of listing the seven gates (`S-005`).
- [ ] The summary names the operating system and Python version the run used (`S-006`).
- [ ] `AGENTS.md` names the command and states in these words that passing it is **necessary but not
      sufficient** (`S-006`, `S-007`).
- [ ] Standard library only, and passes on Windows, macOS, and Linux.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
