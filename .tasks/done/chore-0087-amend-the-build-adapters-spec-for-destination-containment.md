---
id: chore-0087
title: Amend the build-adapters spec so destination containment is a contract obligation rather than an unpinned guard
type: chore
status: done
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
[`build-adapters.md`](../../docs/spec/build-adapters.md) requires it.

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
[`chore-0043`](chore-0043-amend-build-adapters-spec-for-the-code-span-exception.md) set for
[`bug-0028`](bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md): the code half is a defect fix
and the contract half is a decision about an approved spec, and merging them puts a contract change
inside a bug fix where nobody reviews it as one. `S-018` exists because that split was made.

## Scope

**In scope:** one new scenario pinning the containment obligation, and the bookkeeping that follows
an amendment here.

- Add `S-020` to [`build-adapters.md`](../../docs/spec/build-adapters.md), stating the obligation in
  contract terms: given a skill whose frontmatter names a destination outside the output root, when
  a run is requested, then nothing is written outside the resolved root and the run fails clearly.
  Write it as an observable outcome, not as a description of the guard's implementation.
- Add the matching row to
  [`build-adapters.conformance.md`](../../docs/spec/build-adapters.conformance.md), citing the tests
  `bug-0060` wrote, and update its coverage proof arithmetic.
- **Re-anchor the "Emitted per-skill paths" row of that same matrix.** It cites the `dest`
  expressions in `emit_cursor()` and `emit_vscode()` for the path shapes it asserts, and after
  `bug-0060` those functions read `dest` from a `NAME_DESTINATIONS` mapping, so a reader following
  the citation no longer sees the shapes it claims. The classification is still correct: the emitted
  paths were proven byte-identical across four target sets. This is the pointer drifting, which
  `review-quality`'s gate calls a re-anchor rather than a dropped finding, so name
  `NAME_DESTINATIONS` alongside the emitters instead of changing the verdict. The `matrix citations`
  gate does not catch it, because a citation of this shape falls in its unaudited set.
- Update both build-adapters rows in [`docs/spec/README.md`](../../docs/spec/README.md): the amendment
  ledger row, which names each added scenario and the task that added it, and the scenario count in
  the status table. That file's derived arithmetic is the subject of the open
  [`chore-0075`](../chore-0075-the-spec-readme-carries-derived-arithmetic-that-nothing-recomputes.md);
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

## Decisions

- **Chosen: `S-020` states containment only, and its matrix row reads `Conformed`.** The Then is
  "nothing exists outside the resolved root and the run fails clearly", which is the property
  `bug-0060` delivers today, so the row carries evidence rather than a promise.
- **Rejected: writing the Then to the stronger form now**, that a refused run writes nothing at all,
  with the row recorded `not-built` until `bug-0062` lands. It is legal for a forward contract, and it
  is wrong here: a `not-built` row leaves the shipped containment guard required by nothing and
  audited by nothing, so a refactor removing it would still pass every gate, which is the exact
  failure this task was filed to close. The stronger property is Goal 6's and is owed a scenario of
  its own once `bug-0062` makes it true; `S-020`'s third note says so in the contract rather than
  leaving a reader to infer it.
- **Rejected: leaving the `Exit code` surface row alone and reporting the contradiction.** That row
  read "non-zero for an unrecognized target, zero otherwise", which `bug-0060` had already made false
  and which `S-020` would have contradicted from inside the same document. One clause was changed, and
  the row was re-derived in the matrix rather than repointed. It is disclosed as work beyond the Scope
  bullets rather than folded in quietly.
- **A premise that turned out false, inside this task's own extra change: the first `Exit code`
  wording was still inaccurate.** It read "non-zero for an unrecognized target and for a destination
  refused under S-020, zero otherwise", and independent verification measured two reachable arms
  outside that: a frontmatter name refused whose destination lands *inside* the root, which the code
  itself distinguishes, and an undecodable `SKILL.md`. `zero otherwise` is a universal claim, so a
  matrix note disclaiming those arms could not save it.
- **Chosen: widen the element to name the class of refusal. Rejected: recording it `Diverged`.**
  The implementation never disagreed with the contract; only the sentence did, so a `Diverged` row
  would have entered the unreconciled set describing a gap no code change could close. The class
  wording, a run that refuses rather than proceeds, is also true of the landed combination rather
  than of today's file alone: `bug-0062`'s pre-pass refuses a whole run before anything is written
  and names every offending skill, which is still a refusal. Which refusals are *required* stays
  with the scenarios, so the name rule `validate-skills.py` owns is not imported here.
- **A second re-anchor, caused by a sibling task rather than by `bug-0060`.** The `S-001` row cited
  `for d in skills`, which is unique here and stops being unique once `bug-0062`'s frontmatter
  pre-pass lands carrying the same phrase, leaving a pointer that resolves ambiguously and a gate
  that stays green if the emit loop is later refactored away. Re-anchored on `dest = EMITTERS[t]`,
  the single dispatch site, which is inside the loop and independent of how the frontmatter reaches
  it.
- **Rejected: `fm, body = parsed[d]` as that anchor**, which the verifier suggested. It does not
  exist in this worktree, so `check-citations.py` would report it unresolved and the acceptance
  command would fail here. **Also rejected: leaving the row alone**, since the current phrase fails
  in the silent direction after `bug-0062` lands, where the chosen one, if that task does move the
  dispatch, dangles loudly at the gate instead.
- **Seam left open: the `bug-0060` tests still carry no `S-NNN` tag**, and the module docstring of
  `tests/test_build_adapters.py` still says why, naming this task. Both are stale as of `S-020` and
  neither is touched, because this task writes nothing under `tests/`. The retag is the follow-up
  `chore-0045` performed for `S-018` after `chore-0043` stated it, recorded as owed in the coverage
  proof.
- **Seam left open: `docs/spec/README.md` still says "184 is the first figure"** one paragraph below
  the total this task moved to 186. That figure was already stale before this change, it belongs to
  the derived arithmetic `chore-0075` is open against, and it is left rather than quietly corrected.
- **Seam left open: this task's `scenarios:` frontmatter still reads `[]`** while the task adds
  `S-020`. Left as authored, per the instruction to change nothing in this file outside this section.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `docs/spec/build-adapters.md` carries `S-020` with a Given/When/Then body and no renumbering of
      any existing scenario.
- [x] `build-adapters.conformance.md` carries an `S-020` row citing a test that exists, and
      `python scripts/check-citations.py` resolves that citation.
- [x] The conformance file's coverage proof states the audited set and its arithmetic, and the
      numbers add up against twenty scenarios.
- [x] Both build-adapters rows in `docs/spec/README.md` are updated, the amendment ledger and the
      count.
- [x] `bug-0060` is in `.tasks/done/` before this task closes.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
