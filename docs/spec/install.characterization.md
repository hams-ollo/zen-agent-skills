---
title: install characterization
spec: none (this is the trigger)
task: .tasks/done/feat-0027-exercise-test-author-characterization.md
verified: 2026-07-27
verdict: characterized
branch_exercised: test-author characterization mode
---

# install.py characterization record

A [`test-author`](../../.agents/skills/test-author/SKILL.md) run in **characterization mode** against
[`scripts/install.py`](../../scripts/install.py), performed 2026-07-27 to exercise the second of the
three branches named in ROADMAP Epic A item 8.

Format reused from [`house-review.verification.md`](house-review.verification.md), which `feat-0024`
established.

## Why this trigger is real and not staged

`test-author`'s characterization mode is for "legacy code with no coverage that needs its current
behavior pinned before a change". `install.py` matched on every clause without arrangement: it was the
only script in the kit with **neither a contract nor a single test**, and it is not incidental code,
it is one of the two distribution paths the whole kit ships through.

It also had a change coming. The remaining work list already carried "a spec for `install.py`", and
writing a contract for code with no pinned behavior is how a spec quietly becomes a wish list rather
than a description. Characterizing first is the documented order, not a contrivance.

The absence of a spec is what selects the mode. Acceptance mode was unavailable, which is precisely
the condition characterization exists for.

## Result

Reported in `test-author`'s own terms, with `test-quality`'s reporting fields:

```text
mode: characterization (no spec exists, so no scenarios to derive from)
framework: stdlib unittest, matching tests/test_validate_skills.py and tests/test_build_adapters.py
layer: component, exercising install() and uninstall() against a temp home directory
oracle: exact observable outcomes, the placed tree, exit codes, printed status words,
        and manifest contents, never "does not raise"
tests written: 8, all passing
production code changed: none
fixtures: none committed; every run builds its tree in a TemporaryDirectory
```

Behavior pinned: discovery by presence of `SKILL.md`; one directory placed per skill with the rules
module as its sibling; the property that `../../rules/<file>` resolves from an installed skill;
idempotent re-runs reporting `updated` rather than `CONFLICT`; an unmanaged file at a target reported
and left byte-for-byte intact; a dry run writing neither targets nor manifest; uninstall driven by the
manifest and emptying it; and uninstall with no manifest exiting zero rather than erroring.

## Did the branch behave as its contract describes?

Yes, on the clauses that apply. `test-author`'s Modes section requires inferring the mode from the
inputs, which the absent spec settled; asserting current observable behavior rather than a desired
contract; and labeling the tests as characterization "in the name or an adjacent comment". The file is
labeled in its own docstring, its class name, and each test's comment, because one label in a suite a
future reader may open at any line is not enough.

Step 2's "discover the repository's test infrastructure and match it" was followed to stdlib
`unittest`, and Step 4's "never touch production code" held: `scripts/install.py` is unchanged.

The one clause that could not apply is Step 1's spec gate, which characterization mode explicitly
skips. That is the mode working, not a gap.

## Observations

**Characterization surfaced two testability defects without fixing either, which is the mode
behaving correctly.** `install.py` is the third kit script to be brought under test and the first
where the test had to work around the code rather than simply call it:

- `MANIFEST` is a module-level constant pointing at `scripts/.install-manifest.json`, so any test
  calling `install()` writes into the real repository. Each test redirects it and restores it
  afterwards. Verified that the redirect holds: a full run leaves `scripts/` clean.
- `main()` calls `parse_args()` with no argv, so the CLI layer cannot be driven from a test. Both
  `validate-skills.py` (`chore-0003`) and `build-adapters.py` (`feat-0026`) were given injectable
  entry points when they were brought under test; `install.py` has not been, so its argument parsing,
  its tool validation, and its `--home` handling remain uncovered.

Both are recorded rather than repaired, because a characterization pass that edits the code it is
pinning has destroyed its own baseline. They belong in whatever task writes the `install.py` spec.

**A characterization suite is a weaker artifact than it looks, and should be read as a diff detector.**
Every assertion here says "this is what it does today". None says "this is right". Three of the pinned
behaviors are load-bearing and almost certainly correct (never overwriting an unmanaged file, dry runs
writing nothing, the rules module resolving), but the suite cannot distinguish those from an accident
of implementation, because no contract exists to check them against. That distinction arrives with the
spec, not with these tests.

**The mode's real value showed up in sequencing, not in coverage.** The tests are unremarkable. What
the pass produced is a pinned baseline plus two named defects, both of which the forthcoming spec now
has to account for rather than describe around.
