---
id: chore-0017
title: Give install.py an injectable entry point so its CLI scenarios can be tested
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: docs/spec/install.md
scenarios: [S-009, S-010]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.conformance.md
created: 2026-07-27
---

## Problem

Two approved scenarios in [`docs/spec/install.md`](../docs/spec/install.md) have no test and cannot
get one. `S-009` (an unrecognised tool is rejected before anything is placed) and `S-010` (the
placement mode defaults to what the platform can do) both live in `main()`, which calls
`parse_args()` with no argv, so the CLI layer cannot be driven from a test.

Both [`validate-skills.py`](../scripts/validate-skills.py) and
[`build-adapters.py`](../scripts/build-adapters.py) were given injectable entry points when they were
brought under test (`chore-0003` and `feat-0026`). `install.py` was not, so it is the only kit script
whose argument handling is unreachable from the suite.

`feat-0027` first recorded this as a loose testability observation. `feat-0029`'s conformance matrix
converted it into a concrete one: it is now two named scenarios of an approved contract that cannot be
verified.

## Scope

**In scope:** give `main()` an optional `argv` parameter, matching the two sibling scripts, then add
tests for `S-009` and `S-010` and update the matrix's test-coverage table.

**Out of scope:** any behavior change. `main()` must behave identically when called with no argument,
which is how every existing caller invokes it. Moving `MANIFEST` off the module, which is a separate
question with a real design decision behind it: the manifest's location is intended contract per
`S-005`, and the tests work around it without difficulty.

## Implementation notes

- Mirror `build-adapters.py` exactly: `def main(argv=None)` and `ap.parse_args(argv)`. Same one-line
  shape, same docstring note about driving it from a test.
- `S-010` asserts a platform-dependent default, so the test must either check the default against
  `os.name` rather than hardcoding one answer, or set `os.name` and restore it. Prefer the former: a
  test that asserts "copy on Windows" and nothing else silently passes everywhere else.
- Tag both new tests with their scenario ids, as the rest of that suite now is.

## Risks and rollback

Not required: one module, no persisted format, reverts with one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] `main(argv=None)` accepts a list, and calling `main()` with no argument is unchanged.
- [ ] `S-009` and `S-010` each have a covering test tagged with their id.
- [ ] `docs/spec/install.conformance.md`'s test-coverage table records them as covered.
- [ ] No `install.py` behavior changed; the existing suite passes untouched.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
