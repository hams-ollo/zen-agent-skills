---
id: chore-0039
title: The validate-skills contract's S-009 says every unresolved link is an error, and the validator now excepts one
type: chore
status: open
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: []
spec: "docs/spec/validate-skills.md"
scenarios: ["S-009"]
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
created: 2026-08-10
---

## Problem

[`bug-0027`](done/bug-0027-skill-lint-fires-inside-fenced-blocks.md) taught `check_links()` that a
markdown link inside an inline code span or a fenced block is not a link, so it is neither resolved
nor reported. That is the right behaviour and it is not what the approved contract says.

`S-009` in [`validate-skills.md`](../docs/spec/validate-skills.md) reads:

> **Given** a `SKILL.md` containing a relative link whose target is not present on disk
> **When** the validator runs
> **Then** it records a link-target error naming the unresolved path, and exits non-zero.

No exception, for anything. The implementation now has one, and `bug-0027` recorded the divergence in
its `## Decisions` and deliberately left the spec alone, because every amendment in this repository
so far records the author's explicit instruction and that task carried none.

**A contract that under-describes its implementation is the failure [`chore-0027`](done/chore-0027-amend-two-contracts-the-implementations-outgrew.md)
closed for two other specs, and [`chore-0033`](chore-0033-amend-install-spec-for-check-and-with-hooks.md)
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

- `docs/spec/validate-skills.md`: state the exception. Whether that is a qualification on `S-009` or
  a new scenario beside it is the author's call, and the file's own amendment history shows both
  shapes being used.
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
  `build-adapters.py` is [`bug-0028`](done/bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md),
  which carries its own contract question about `S-003` through `S-008`.
- Re-auditing scenarios `bug-0027` did not touch. A partial audit stated as partial is correct here;
  a whole-spec re-run is `spec-conformance`'s job and a different task.

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

- [ ] `validate-skills.md` describes the code-span and fence exception, and a reader following the
      spec would predict what the validator actually does for a link inside a fence.
- [ ] The amendment is recorded in the file's header in the established shape, naming this task id
      and stating that re-approval is pending, with `status: approved` unchanged.
- [ ] `validate-skills.conformance.md`'s `S-009` row reflects the current implementation, including
      the new branch order.
- [ ] `docs/spec/README.md`'s scenario count for this spec still matches the file, whether or not the
      amendment changed it.
- [ ] No file under `scripts/` or `tests/` is modified.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
