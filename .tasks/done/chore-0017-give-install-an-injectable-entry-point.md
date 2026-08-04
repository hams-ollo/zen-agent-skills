---
id: chore-0017
title: Give install.py an injectable entry point so its CLI scenarios can be tested
type: chore
status: done
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

Two approved scenarios in [`docs/spec/install.md`](../../docs/spec/install.md) have no test and cannot
get one. `S-009` (an unrecognised tool is rejected before anything is placed) and `S-010` (the
placement mode defaults to what the platform can do) both live in `main()`, which calls
`parse_args()` with no argv, so the CLI layer cannot be driven from a test.

Both [`validate-skills.py`](../../scripts/validate-skills.py) and
[`build-adapters.py`](../../scripts/build-adapters.py) were given injectable entry points when they were
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

- [x] `main(argv=None)` accepts a list, and calling `main()` with no argument is unchanged.
- [x] `S-009` and `S-010` each have a covering test tagged with their id.
- [x] `docs/spec/install.conformance.md`'s test-coverage table records them as covered.
- [x] No `install.py` behavior changed; the existing suite passes untouched.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-27)

`main()` now takes an optional `argv`, matching `validate-skills.py` and `build-adapters.py`, and
calling it with no argument is unchanged: the CLI behaves identically for every real caller. Both new
tests were confirmed to fail against the pre-fix `main()`, so they test the change rather than
restating it. Suite 46 to 48, and every scenario in the contract now has a covering test.

**S-010 is covered on one branch only, which the task's own note anticipated and the run then
sharpened.** The note warned against a test that hardcodes `"copy"` and silently passes everywhere
else, and recommended deriving the expectation from `os.name`. The first attempt went further and
patched `os.name` to exercise both branches, which fails outright: `pathlib` selects `PosixPath` or
`WindowsPath` from that same attribute and raises `NotImplementedError` on instantiation. Faking the
platform is not available here.

So the test derives its expectation from the running platform and asserts the wiring end to end,
failing if the default changes or the flag stops feeding it, while the opposite branch is exercised
only by running the suite there. That is an honest partial result rather than a hollow assertion.
Closing the other half means extracting the default into its own expression, a behaviour-preserving
refactor that was deliberately out of this task's scope and is not obviously worth its own.
