---
id: chore-0025
title: Backfill the four spec conformance matrices the kit is missing, and settle the sibling naming
type: chore
status: done
priority: P1
parent: "ROADMAP Epic B #6: spec-conformance"
depends_on: []
touched_files:
  - docs/spec/doc-sync.md
  - docs/spec/house-review.md
  - docs/spec/spec-author.md
  - docs/spec/test-author.md
created: 2026-08-05
---

## Problem

The kit adopted a convention during the Phase 1 fold-ins: an approved spec gets a sibling
`<stem>.conformance.md` recording, per scenario, whether the implementation conformed, diverged, or
was not built. Five specs have one (`build-adapters`, `install`, `tracker-links`, `validate-skills`,
`verifier-agent`). Four do not:

| Spec | Sibling present | Note |
|---|---|---|
| [`doc-sync.md`](../../docs/spec/doc-sync.md) | none | shipped as `feat-0020` |
| [`house-review.md`](../../docs/spec/house-review.md) | `house-review.verification.md` only | not a conformance matrix, and not the name the convention uses |
| [`spec-author.md`](../../docs/spec/spec-author.md) | none | shipped as `feat-0017` |
| [`test-author.md`](../../docs/spec/test-author.md) | none | shipped as `feat-0018` |

All four skills shipped. All four specs are `status: approved`. So the kit is carrying four approved
contracts with no recorded audit of whether the thing built actually matches them, which is the
precise gap [`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md) exists to close. A
convention followed five times out of nine is a convention held by memory, and this is what that
looks like after four months.

The `house-review` row is a second, smaller problem. `house-review.verification.md` was introduced
by `feat-0024` as a reusable evaluation-record format, which is a different artifact from a
conformance matrix. Two sibling naming patterns now exist for related-but-distinct records, and
nothing states which is which.

This blocks `feat-0039`. A conformance gate cannot be switched on in a repository that would
immediately fail it on four of its own files.

## Scope

**In scope:**

- Run `spec-conformance` over each of the four specs against its shipped implementation, producing
  `doc-sync.conformance.md`, `house-review.conformance.md`, `spec-author.conformance.md`, and
  `test-author.conformance.md`.
- Record honest results. A `Diverged` or `Not-built` row with a stated reason is the correct output
  when that is the truth; a matrix manufactured to be all-green defeats the point and would be
  caught by the next reader.
- State the distinction between a `.conformance.md` and a `.verification.md` sibling in one place,
  either `docs/spec/README.md` or the relevant `AGENTS.md` section, so the next author does not have
  to infer it.

**Out of scope:**

- Fixing any divergence the audit finds. `spec-conformance` reports and never repairs, by contract.
  File what it finds as its own task.
- Editing the four specs' contract text. If the audit shows the spec is wrong rather than the code,
  that is a finding to file, not an edit to make here.
- Renaming or restructuring the existing `.verification.md` files.
- The gate hook itself, which is `feat-0039`.

## Implementation notes

The four audits are independent and can be done in any order, but keep them in one task: the naming
decision has to be made once, and splitting them across agents would produce four different answers
to it.

`verifier-agent`'s dogfood is the cautionary precedent. It found that the conformance matrix for
`validate-skills.py` had correct classifications sitting on line citations that had drifted eight
lines after the `chore-0003` refactor. Anchor each citation to a symbol or a quoted line rather than
a bare line number where the format allows it, so these four do not rot the same way.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" -v

- [ ] Four new files exist: `docs/spec/{doc-sync,house-review,spec-author,test-author}.conformance.md`.
- [ ] Each maps every `S-NNN` in its spec to exactly one of `Conformed`, `Diverged`, or `Not-built`,
      with named evidence for each row.
- [ ] Each records an explicit unreconciled set, empty or not.
- [ ] The `.conformance.md` versus `.verification.md` distinction is written down in one place and
      linked from the specs' README.
- [ ] Any divergence found is filed as a new task rather than fixed here.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
