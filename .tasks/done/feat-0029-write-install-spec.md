---
id: feat-0029
title: Write the behavioral contract for install.py, the last uncontracted script
type: feat
status: done
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - docs/spec/install.md
  - tests/test_install.py
created: 2026-07-27
---

## Problem

[`scripts/install.py`](../scripts/install.py) is the last kit script with no contract. It is also the
one that matters most to an adopter, because it is how the skills reach a harness at all, and the
2026-07-27 pass found a blocker in exactly that path: it was shipping every skill without the rules
module they compose, so `house-review` arrived with no rubric.

`feat-0027` pinned its current behavior with eight characterization tests, which was the documented
order: characterizing before specifying keeps the spec a description rather than a wish list. Those
tests say "this is what it does" and cannot say "this is right", because no contract exists to check
them against. This closes that.

## Scope

**In scope:** author `docs/spec/install.md` with `spec-author`, covering the placement targets per
supported tool, the rules module's location, re-run recognition and the manifest that enables it, the
never-overwrite-an-unmanaged-target rule, dry run, uninstall, and invocation failure.

Then promote the characterization suite to an acceptance suite: tag each test with the `S-NNN` it
covers, and relabel the file, since a test derived from a contract is no longer pinning unexplained
behavior.

**Out of scope:** changing any `install.py` behavior. This documents a contract that already holds,
the way `feat-0026` did for `build-adapters.py`. The two testability findings `feat-0027` recorded
(`MANIFEST` as a module constant, `main()` taking no argv) are **not** contract items: the manifest
location is intended behavior that the module docstring already documents, and argv injection is a
property of the code rather than of what the tool does. They belong in their own chore.

## Implementation notes

- Retrospective spec, so the failure mode is describing the implementation rather than the contract.
  "The manifest records which targets this tool created" is contract; "`MANIFEST` is a module-level
  `Path`" is not.
- The manifest is genuinely contract-level, not an internal detail: deleting it changes observable
  behavior, turning previously-copied targets into `CONFLICT`s, and the module docstring already warns
  about this. That consequence deserves a scenario.
- `feat-0026` learned that a conformance matrix walks scenarios and surface elements and never the
  goals, so a wrong goal survives an audit. Write the goals carefully; nothing downstream will check
  them.

## Risks and rollback

Not required: this touches one module (the contract plus its own tests), changes no persisted format,
and reverts with one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [x] `docs/spec/install.md` exists, `spec-quality` returns `ready`, and a human set `status: approved`.
- [x] Every scenario carries a stable `S-NNN`; every goal and surface element has one.
- [x] Each test in `tests/test_install.py` is tagged with the scenario it covers, and the file no
      longer describes itself as characterization.
- [x] `scripts/install.py` is byte-for-byte unchanged.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-27)

Eleven scenarios, approved, with a conformance matrix and a promoted acceptance suite. Every kit
distribution script now has a contract and a matrix.

Two judgment calls decided what belonged in the contract. **The manifest is contract-level**, not an
internal detail: deleting it changes observable behavior, which `S-005` now states. **The two
`feat-0027` testability findings are not contract items** and were deliberately left out, since the
manifest's location is intended behavior and argv injection is a property of the code rather than of
what the tool does.

`S-002` states the rules module's location by derivation rather than by path: it goes wherever the
skills' existing references resolve to. That is the property the 2026-07-27 blocker violated, and
writing it as a literal path would have made it look arbitrary rather than forced.

`spec-quality` caught one gap before the draft was committed: `S-010` traced to no goal. That is the
fourth consecutive spec whose orphan was an invocation concern, after `validate-skills` S-015,
`build-adapters` S-013, and `house-review` S-011, so goal 7 now covers working out of the box per
platform.

The suite went 8 to 10 and became an acceptance suite: every test tagged with the scenario it covers,
plus new tests for `S-005` and `S-011`. `S-005` was worth adding for its own sake, since "deleting the
record turns the tool's own past work into conflicts" looks like a bug and is correct, and is exactly
what a future editor would try to fix.

**The matrix converted a loose observation into a concrete one.** `S-009` and `S-010` have no test and
cannot get one, because both live in `main()`, which takes no argv. That is not a contract defect and
not a divergence; it is a coverage gap caused by the code's shape, and it is now two named scenarios of
an approved contract that cannot be verified rather than a vague note about testability. Filed as
`chore-0017`.
