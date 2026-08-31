---
id: chore-0087
title: Amend the build-adapters spec so destination containment is a contract obligation rather than an unpinned guard
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0060]
spec: docs/spec/build-adapters.md
scenarios: []
touched_files:
  - docs/spec/build-adapters.md
  - docs/spec/build-adapters.conformance.md
  - docs/spec/README.md
created: 2026-08-31
---

## Problem

[`bug-0060`](bug-0060-a-frontmatter-name-can-write-outside-the-adapter-output-root.md) adds a guard
that refuses to write outside the resolved output root. Nothing in
[`build-adapters.md`](../docs/spec/build-adapters.md) requires it.

The nineteen scenarios there govern what is emitted and where links point. `S-016` is the closest,
and it is about links resolving inside a plugin tree rather than about where a write may land.
`S-010` protects a file the adopter owns from being overwritten, inside the root. `S-017` reasons
about writing into a project nobody intended, and does it at the level of the requested target, not
the skill name. Goal 6, "fail clearly on an unusable invocation rather than writing a partial
result", is the closest thing to a home for the new behavior and is a goal rather than a scenario.

So after `bug-0060` lands, the tool has a security guard that no conformance row can account for and
no contract requires. A later refactor that removes it leaves every gate green, and
`build-adapters.conformance.md` stays honest while describing a tool that no longer contains its
writes.

**Filed separately on purpose.** This is the shape
[`chore-0043`](done/chore-0043-amend-build-adapters-spec-for-the-code-span-exception.md) set for
[`bug-0028`](done/bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md): the code half is a defect fix
and the contract half is a decision about an approved spec, and merging them puts a contract change
inside a bug fix where nobody reviews it as one. `S-018` exists because that split was made.

## Scope

**In scope:** one new scenario pinning the containment obligation, and the bookkeeping that follows
an amendment here.

- Add `S-020` to [`build-adapters.md`](../docs/spec/build-adapters.md), stating the obligation in
  contract terms: given a skill whose frontmatter names a destination outside the output root, when
  a run is requested, then nothing is written outside the resolved root and the run fails clearly.
  Write it as an observable outcome, not as a description of the guard's implementation.
- Add the matching row to
  [`build-adapters.conformance.md`](../docs/spec/build-adapters.conformance.md), citing the tests
  `bug-0060` wrote, and update its coverage proof arithmetic.
- Update both build-adapters rows in [`docs/spec/README.md`](../docs/spec/README.md): the amendment
  ledger row, which names each added scenario and the task that added it, and the scenario count in
  the status table. That file's derived arithmetic is the subject of the open
  [`chore-0075`](chore-0075-the-spec-readme-carries-derived-arithmetic-that-nothing-recomputes.md);
  update it by hand here and do not attempt to solve that problem in passing.

**Out of scope:**

- The code and tests. They are `bug-0060`, which this depends on, and no line of
  `scripts/build-adapters.py` should change here.
- Whether the frontmatter `name` must equal the source directory name. That rule already lives in
  `validate-skills.py`, whose scope the Non-Goals section explicitly places outside this contract:
  "Judging whether a skill is well-formed. That is `validate-skills.py`." Do not import it into this
  spec.
- Any other scenario, goal, constraint, or non-goal in the file.
- `install.py`'s equivalent containment question, which has its own spec.

## Implementation notes

The spec's `status` is `approved`, and amending an approved spec is an established move here rather
than a violation: `chore-0043` added `S-018`, `chore-0062` added `S-019`, and `chore-0078` amended
`systematic-debugging` from 13 to 15. Follow the shape those used, which is a new id appended rather
than a renumbering, because task files, conformance rows and test names all cite the ids.

Place the scenario where the file groups related ones rather than at the end: `S-013`, an
unrecognized target is rejected, and `S-012`, a preview writes nothing, are its neighbours in
subject.

The scenario is worth writing so it also covers the preview path, since `bug-0060` makes `--dry-run`
refuse the same input a real run refuses and that is the behavior `run-checks.py`'s adapters gate
actually exercises.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `docs/spec/build-adapters.md` carries `S-020` with a Given/When/Then body and no renumbering of
      any existing scenario.
- [ ] `build-adapters.conformance.md` carries an `S-020` row citing a test that exists, and
      `python scripts/check-citations.py` resolves that citation.
- [ ] The conformance file's coverage proof states the audited set and its arithmetic, and the
      numbers add up against twenty scenarios.
- [ ] Both build-adapters rows in `docs/spec/README.md` are updated, the amendment ledger and the
      count.
- [ ] `bug-0060` is in `.tasks/done/` before this task closes.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
