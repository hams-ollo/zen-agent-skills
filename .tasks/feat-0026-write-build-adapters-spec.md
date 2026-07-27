---
id: feat-0026
title: Write the behavioral contract for build-adapters.py, the last untested-by-contract script
type: feat
status: open
priority: P2
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - docs/spec/build-adapters.md
  - tests/test_build_adapters.py
  - README.md
  - docs/ARCHITECTURE.md
created: 2026-07-27
---

## Problem

[`scripts/build-adapters.py`](../scripts/build-adapters.py) has tests but no spec. It is the only
kit script in that state: `validate-skills.py` has
[`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md), and `install.py` has neither but
is also not the subject of a test suite that claims spec provenance.

The 2026-07-27 `doc-sync` run made the gap visible rather than merely present. Three places in
`README.md` and `docs/ARCHITECTURE.md` claimed the test suite is "derived from the specifications
under `docs/spec/`". Adding [`tests/test_build_adapters.py`](../tests/test_build_adapters.py)
falsified that claim, and the honest short-term fix was to soften the prose (finding `D-007`,
applied 2026-07-27) rather than to close the gap. This task closes it, after which the original,
stronger wording can come back.

This matters beyond tidiness because the adapter script now carries real behavioral rules that exist
only as code and test assertions: which of three link classes gets rewritten to what, that an
existing `.agents/rules/` file is never overwritten, and that a build into the kit itself is a no-op.
Those are contract decisions. A future editor who does not know the rules-file rule can break an
adopter's swapped house style and every test will still pass, because no test asserts the *reason*.

## Scope

**In scope:** author `docs/spec/build-adapters.md` with `spec-author`, describing the contract the
script already implements. At minimum it must cover:

- the two emitted adapter shapes and where each lands;
- the three link classes and the rewrite each receives, plus the two that must travel unchanged
  (external URLs, same-page anchors), and the preservation of anchors and link titles;
- the emission of shared material under `.agents/`, and the never-overwrite rule for
  `.agents/rules/`, stated as the contract it is: a project's own copy of a swappable module
  outranks the kit's;
- the same-file no-op, so building into the kit is safe;
- `--dry-run` writing nothing, and `--target` rejecting an unknown target.

Then tag each test in `tests/test_build_adapters.py` with the `S-NNN` it covers, and restore the
un-softened wording in `README.md` and `docs/ARCHITECTURE.md`.

**Out of scope:** changing any adapter behavior. This documents what is already there and verified;
if writing the spec surfaces a behavior that looks wrong, file that separately rather than fixing it
here. Writing a spec for `install.py` (worth doing, but it is its own task and its own dogfood).

## Implementation notes

- Write it with `spec-author`, which composes `spec-quality` and will not return until the verdict is
  `ready`. It writes `status: draft`; a human sets `approved`. Do not self-approve.
- This is a **retrospective** spec: the implementation exists and is the source of truth for what the
  contract currently is. That is a legitimate but distinct mode from specifying ahead of code, and it
  has a specific failure: it is tempting to describe the implementation rather than the contract. Keep
  the scenarios at the what/why level. "The rules module is never overwritten" is contract; "the
  `dest.exists()` check short-circuits the copy" is not.
- The tests already exist and were confirmed to fail against the pre-fix behavior, so scenario-to-test
  mapping should be near mechanical. Where a scenario has no test, say so rather than inventing one.
- Once the spec is approved, run `spec-conformance` against it to produce
  `docs/spec/build-adapters.conformance.md`, which is what makes the coverage claim checkable.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [ ] `docs/spec/build-adapters.md` exists, `status: draft`, and `spec-quality` returns `ready`.
- [ ] Every scenario carries a stable `S-NNN` id; every goal and emitted surface has a scenario.
- [ ] Every test in `tests/test_build_adapters.py` is tagged with the scenario id it covers, or is
      explicitly recorded as covering none.
- [ ] `README.md` and `docs/ARCHITECTURE.md` no longer need the "where one exists" hedge, and the
      `D-007` softening is reverted.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
