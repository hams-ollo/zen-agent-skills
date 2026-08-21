---
id: chore-0039
title: The validate-skills contract's S-009 says every unresolved link is an error, and the validator now excepts one
type: chore
status: done
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: []
spec: "docs/spec/validate-skills.md"
scenarios: ["S-009"]
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
  - docs/spec/README.md
created: 2026-08-10
---

## Problem

[`bug-0027`](bug-0027-skill-lint-fires-inside-fenced-blocks.md) taught `check_links()` that a
markdown link inside an inline code span or a fenced block is not a link, so it is neither resolved
nor reported. That is the right behaviour and it is not what the approved contract says.

`S-009` in [`validate-skills.md`](../../docs/spec/validate-skills.md) reads:

> **Given** a `SKILL.md` containing a relative link whose target is not present on disk
> **When** the validator runs
> **Then** it records a link-target error naming the unresolved path, and exits non-zero.

No exception, for anything. The implementation now has one, and `bug-0027` recorded the divergence in
its `## Decisions` and deliberately left the spec alone, because every amendment in this repository
so far records the author's explicit instruction and that task carried none.

**A contract that under-describes its implementation is the failure [`chore-0027`](chore-0027-amend-two-contracts-the-implementations-outgrew.md)
closed for two other specs, and [`chore-0033`](../chore-0033-amend-install-spec-for-check-and-with-hooks.md)
is open against `install.md` for the same reason right now.** The reasoning is unchanged: a wrong
contract is worse than a missing one, because the next audit re-derives the same divergence and a
reader trusting the spec is misled. Here it is also a trap for a future implementer, who can read
`S-009`, see the exception in the code, and "fix" the code back to the contract, reintroducing a bug
two tasks were spent removing.

**The conformance matrix has drifted with it.** `validate-skills.conformance.md` audits `S-009` as
Conformed and describes the implementation as "reached only after the external, anchor, sibling and
portability branches have passed". There is now a branch in front of all four, and the row does not
know about it.

## Scope

**In scope:** amend the contract so it describes the validator that exists, and re-audit the affected
row. Two documents:

- `docs/spec/validate-skills.md`: state the exception as a **new scenario** beside `S-009`,
  settled by the author on 2026-08-18; see the decisions section. `chore-0043` carries the
  identical decision for `build-adapters.md`, so the two are one decision applied twice.
- `docs/spec/validate-skills.conformance.md`: re-audit `S-009` against the current code, correcting
  the implementation-site description.

Follow the convention in `docs/spec/README.md` for a spec amended after approval: keep `status:
approved`, record the amendment and the task that made it in the header, and say in prose that
re-approval is pending. `chore-0030` established that, and the reason is mechanical rather than
stylistic: `verifier-agent` returns `blocked` on an unapproved spec, so flipping the status makes the
verification run for this very task unanswerable.

**Out of scope:**

- **Any change to `scripts/validate-skills.py`.** The code is right and the contract is behind it.
  Editing the code to match the spec would revert `bug-0027`. This task moves prose only.
- The same class in the two other tools. `.tasks/validate.py` has no approved contract, and
  `build-adapters.py` is [`bug-0028`](bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md),
  which carries its own contract question about `S-003` through `S-008`.
- Re-auditing scenarios `bug-0027` did not touch. A partial audit stated as partial is correct here;
  a whole-spec re-run is `spec-conformance`'s job and a different task.

## Decisions

- **2026-08-18, author: the amendment takes the shape of a new scenario, not a qualification on an
  existing one.** Applies to both this task and its sibling, so the two read as one decision applied
  twice. A new `S-NNN` stating that a link inside an inline code span or a fenced block is emitted
  unchanged is traceable, is citable by a test, and gives `spec-conformance` a row of its own to
  audit. A qualification folded into an existing scenario would leave the exception with no id, so
  nothing could cite it and no matrix could report on it separately. The cost accepted is one more
  scenario per spec to maintain.

- **The new scenario is `S-022`, numbered after the last id and placed beside `S-013`.** The number
  goes at the end because ids here are permanent and renumbering would break every citation to
  `S-014` onward; the position goes beside the link block because the exception is what `S-009`
  through `S-013` are read against, and a reader meets it where it applies. This is the placement
  `chore-0043` chose for `S-018` in `build-adapters.md`, and the coverage proof in the matrix says so
  explicitly so the gap between id order and file order is not read as an error.

- **The conformance re-audit covers `S-009` through `S-013`, not `S-009` alone.** The scope section
  names `S-009`, and the guard sits in `_link_targets()` ahead of every branch, so all five link rows
  now describe an order that is wrong by the same one step. Re-auditing four more rows the same
  change moved is still the partial audit the scope asks for, and it is what `chore-0043` did for the
  six rewrite rows. No row outside that block was re-derived, and the matrix says so.

- **The reach of the rule is measured, not asserted.** 20 shipped bodies, 133 links matched by
  `LINK_RE`, 0 of them inside a code span or a fence, on 2026-08-19. The exception fires on nothing in
  this kit today, so it is a guard rather than a live exclusion, and a matrix row claiming
  `Conformed` without that number could not tell a working guard from a dead one. The same numbers
  back `S-018` in `build-adapters.conformance.md`, because the two tools carry character-identical
  copies of `code_span_ranges()` and `fenced_block_ranges()`.

- **The one place the two contracts honestly differ is stated rather than smoothed over.** This
  validator keys the guard to the link's opening bracket (`m.start()` of `LINK_RE`), where
  `build-adapters.py` keys it to the bracket closing the link text. Both leave the common
  `[`name`](../path)` form governed by the ordinary rules, which is the only consequence a reader needs,
  so `S-022` states the position it actually uses instead of copying the sibling's sentence.

- **`docs/spec/README.md`'s arithmetic was recomputed from the files, not incremented.** Counting
  `^### Scenario S-NNN` across the eleven spec files gives 155 scenarios after this amendment (154
  before), and 142 held by the ten specs carrying a matrix (141 before). The counts in the file
  agreed with that recount before the edit, so the only movement is this scenario.

- **The stale "Four do" line in `docs/spec/README.md` was deliberately left alone.** It sits two
  lines above a table this amendment grows from five rows to six, so it is now wrong by two rather
  than by one. It is `chore-0045`'s assigned item, and `chore-0043` and `chore-0034` already
  collided in this file once; a second hand editing the same paragraph is how that happened.

## Implementation notes

The amendment wants to state the boundary, not just the exception, because the boundary is what
`bug-0027` actually decided and it is easy to lose in a one-line edit:

- A link inside a code span or a fence is skipped by **every** branch of `check_links()`, the
  portability escape rule included, on the grounds that a link rendered as literal text strands no
  reader and that keeping the rule armed inside a fence would stop an author showing the very
  construct the rule exists to teach.
- Outside a span or a fence nothing changed: an absolute or `file://` link is still an error here,
  even though the backlog validator tolerates one.

`docs/spec/README.md` also carries an index line counting scenarios per spec. If the amendment adds a
scenario rather than qualifying `S-009`, that count moves, and stale counts in that index are a thing
`chore-0030` already had to correct once.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `validate-skills.md` describes the code-span and fence exception, and a reader following the
      spec would predict what the validator actually does for a link inside a fence.
- [x] The amendment is recorded in the file's header in the established shape, naming this task id
      and stating that re-approval is pending, with `status: approved` unchanged.
- [x] `validate-skills.conformance.md`'s `S-009` row reflects the current implementation, including
      the new branch order.
- [x] `docs/spec/README.md`'s scenario count for this spec still matches the file, whether or not the
      amendment changed it.
- [x] No file under `scripts/` or `tests/` is modified.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
