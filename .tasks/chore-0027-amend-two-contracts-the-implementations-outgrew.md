---
id: chore-0027
title: Amend the two approved contracts their shipped implementations deliberately outgrew
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - docs/spec/spec-author.md
  - docs/spec/doc-sync.md
  - docs/spec/spec-author.conformance.md
  - docs/spec/doc-sync.conformance.md
created: 2026-08-05
---

## Problem

The `chore-0025` conformance backfill audited four approved specs and found two places where the
implementation is deliberately better than its contract. Both were classified
`accepted-with-reason`, which records the judgment but leaves the contract wrong, and a wrong
contract is worse than a missing one: the next audit re-derives the same divergence, and a reader
trusting the spec is misled about how the skill behaves.

**1. [`spec-author.md`](../docs/spec/spec-author.md) pins the output location.** Its Constraints say
specs "live under `docs/spec/<slug>.md`", and the Proposed Surface repeats it. The shipped
[`spec-author`](../.agents/skills/spec-author/SKILL.md) instead looks for the repository's existing
spec directory (`docs/spec/`, `specs/`, `docs/rfcs/`, `design/`), matches what it finds, and falls
back to `docs/spec/<slug>.md` only when a repository has none. The skill is right: section 5 of
`AGENTS.md` requires it to work in a repository that is not this one, and writing `docs/spec/` into
a project already using `specs/` produces the second spec directory nobody reads, a failure the
skill body calls out by name.

**2. [`doc-sync.md`](../docs/spec/doc-sync.md) collapses two output fields into one.** Its Proposed
Surface has a single `skipped` field holding "every document not audited, with the reason (for
example ledger history, or a narrowed change scope)". The shipped
[`doc-sync`](../.agents/skills/doc-sync/SKILL.md) emits two, and argues the case in its own output
rules: `skipped` means the document was classified and deliberately excluded (a ledger),
`not_audited` means nothing is known about it. Collapsing them makes a document nobody read
indistinguishable from a ledger deliberately passed over, which is the exact "a partial audit read
as a whole one" failure that `doc-sync`'s own Goal 6 and `S-006` exist to prevent.

Neither is a code defect. Both are contracts that stopped describing what shipped.

## Scope

**In scope:**

- Amend `spec-author.md`'s Constraints and Proposed Surface to state discovery of the repository's
  existing spec location, with `docs/spec/<slug>.md` as the documented fallback. Check whether
  `S-001`'s "writes a Markdown file at `docs/spec/<slug>.md`" needs the same treatment; it probably
  does, and a scenario is the more load-bearing of the two.
- Amend `doc-sync.md`'s Proposed Surface to carry both `skipped` and `not_audited`, each with the
  meaning the implementation gives it. Check whether `S-005` and `S-009` reference the collapsed
  field and need adjusting with it.
- Update both conformance matrices: move the affected rows to `Conformed` and correct each
  unreconciled set and its count.
- Re-approval is a human step. Leave `status: approved` in place and say plainly in the handover
  that both contracts were amended and need a maintainer's re-read, following the precedent
  `house-review.md` set when `chore-0012` and `chore-0024` amended it and it was re-approved the
  same day.

**Out of scope:**

- Any change to `spec-author`'s or `doc-sync`'s skill bodies. The implementations are the correct
  side of both divergences; that is the whole premise of this task.
- The `S-011` link-check gap in the same matrix. That one is a real defect in the skill, not a
  stale contract, and is [`bug-0014`](done/bug-0014-doc-sync-applied-edit-has-no-link-check.md).
- Re-auditing the other two specs backfilled by `chore-0025`. `house-review` and `test-author` came
  back with no unreconciled items.
- Renumbering any scenario. Ids are stable and never reused, and both skills' own bodies say so.

## Implementation notes

Amend, do not rewrite. Both specs have amendment history in their Open Questions sections recording
what was resolved and when (`chore-0012` and `chore-0024` for `house-review`, the 2026-07-25
resolutions for `doc-sync`), and that convention is worth continuing: add a dated line saying what
this amendment closed and that it decided nothing new.

The honest framing for both is that the contract lagged, not that anyone erred. `spec-author`'s spec
was written for this repository before the skill was generalised for adopters, and `doc-sync`'s
field split emerged from the `feat-0020` dogfood. Say that, so a later reader does not read the
amendment as a correction of a mistake.

Run [`spec-quality`](../.agents/skills/spec-quality/SKILL.md) over both amended specs before
handing them back. An amendment is exactly where a contract picks up an ambiguity, and the lens is
cheap.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict && python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py" -v

- [ ] `spec-author.md` states location discovery with `docs/spec/` as the fallback, in Constraints,
      Proposed Surface, and `S-001` wherever each currently pins the fixed path.
- [ ] `doc-sync.md`'s Proposed Surface carries both `skipped` and `not_audited` with distinct stated
      meanings.
- [ ] Both conformance matrices show the affected rows as `Conformed`, with the amended clause cited.
- [ ] Each matrix's unreconciled set and count are corrected; `doc-sync`'s retains its `S-011`
      `to-fix` row unless `bug-0014` has landed first.
- [ ] Neither skill body changed (`git diff` over `.agents/skills/` is empty for both).
- [ ] `spec-quality` returns `ready` for both amended specs, and the handover states plainly that
      both need a maintainer's re-approval.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
