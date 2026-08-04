---
id: feat-0027
title: Exercise test-author's characterization mode on real legacy code
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - tests/test_install.py
  - docs/spec/install.characterization.md
created: 2026-07-27
---

## Problem

The second of the three branches ROADMAP Epic A item 8 names as never having fired on real work.
`feat-0024` exercised the first (`verifier-agent`'s `blocked` verdict) and established the reusable
evaluation-record format; this reuses it.

## Scope

**In scope:** run `test-author` in characterization mode against `scripts/install.py`, the kit's only
script with neither a contract nor a test, and record the run.

**Out of scope:** writing a spec for `install.py`, which the run's findings should inform rather than
precede. Fixing the testability defects the run surfaces: a characterization pass that edits the code
it is pinning has destroyed its own baseline.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [x] Characterization tests exist for `scripts/install.py` and pass.
- [x] They are labeled as characterization, not as acceptance tests.
- [x] `scripts/install.py` is byte-for-byte unchanged.
- [x] The run is recorded in the `feat-0024` evaluation-record format.

## Outcome (2026-07-27)

Eight characterization tests, all passing, `scripts/install.py` unchanged. Recorded at
[`install.characterization.md`](../../docs/spec/install.characterization.md).

The mode behaved as specified: it inferred characterization from the absent spec, skipped the Step 1
spec gate (which is the mode working, not a gap), matched the repo's stdlib `unittest` convention, and
touched no production code.

**Its value was in sequencing rather than coverage.** The tests themselves are unremarkable. What the
pass produced is a pinned baseline plus two named testability defects the forthcoming `install.py`
spec now has to account for: `MANIFEST` is a module-level constant pointing into the repository, so
any test calling `install()` writes into the real tree, and `main()` takes no argv, so the CLI layer
is undrivable from a test. Both `validate-skills.py` and `build-adapters.py` were given injectable
entry points when they were brought under test; `install.py` has not been.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
