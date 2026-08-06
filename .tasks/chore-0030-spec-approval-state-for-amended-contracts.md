---
id: chore-0030
title: An approved spec carrying an unapproved amendment has no machine-readable state
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - docs/spec/README.md
  - .agents/skills/spec-author/SKILL.md
created: 2026-08-06
---

## Problem

A spec's lifecycle is `draft -> approved`, and [`docs/spec/README.md`](../docs/spec/README.md) states
that a spec is not decomposed into tasks until `status: approved` is set, which `spec-author` never
sets itself. There is no state for the case that keeps occurring: **approved, then amended, with the
amendment not yet re-approved.**

Four specs on `main` are in exactly that state today, each reading `status: approved` with a dated
amendment note saying re-approval is pending:

| Spec | Amendment |
|---|---|
| [`install.md`](../docs/spec/install.md) | gained `S-015` (`feat-0036`) |
| [`spec-author.md`](../docs/spec/spec-author.md) | gained `S-006` and `S-007` (`chore-0027`) |
| [`doc-sync.md`](../docs/spec/doc-sync.md) | field split (`chore-0027`) |
| [`build-adapters.md`](../docs/spec/build-adapters.md) | gained `S-015` to `S-017` (`feat-0034`) |

**The convention arrived by accretion, not by design.** Each of the four was decided in its own task,
under time pressure, and each reached the same answer independently: keep `approved`, say "pending
re-approval" in prose. Four independent agents converging is evidence the answer is reasonable. It is
not evidence it is recorded, and nothing in the repository says a future author should do the same.

**Flipping to `draft` is not available, and the reason is mechanical.** `verifier-agent` composes
`spec-conformance` and returns `blocked` on an unapproved spec, so a task that amends a contract and
flips its status makes the verification run for that very task unanswerable. That is why every one of
the four kept `approved`, and it is a real constraint rather than a preference.

**What it costs.** The status field is the only machine-readable signal, and it now says the same
thing for a contract nobody has questioned and a contract with four unreviewed scenarios inside it. A
reader who trusts the field is misled, and the amendment notes that carry the real state are prose
that no check reads. The author's re-approval queue exists only as four sentences in four files.

## Scope

**In scope:** decide and record the convention. Either a distinct state that `verifier-agent` treats
as approved for conformance purposes, or an explicit statement in
[`docs/spec/README.md`](../docs/spec/README.md) that `approved` plus a dated pending-re-approval note
is the convention, with the reason it is not `draft`. Whichever is chosen, make it discoverable from
the spec lifecycle documentation and from `spec-author`, so the next author does not re-derive it.

**Out of scope:**

- Re-approving any of the four specs above. That is the author's and is not a task.
- Changing `verifier-agent`'s `blocked` behaviour on a genuinely unapproved spec, which is correct.
- Any change to a scenario in the four amended specs.
- Retrofitting whatever is decided onto the four. If the decision changes their frontmatter, that is
  a follow-up done in one pass with the author's re-approval, not smuggled into this task.

## Implementation notes

**Prefer the cheapest thing that removes the ambiguity.** A third status value costs every reader of
every spec a new concept, and costs `verifier-agent` a branch. Writing down the convention already in
use costs one paragraph and makes four existing files correct retroactively. Weigh that against the
fact that a prose note is still not machine-readable, which is the actual complaint.

If a machine-readable form is chosen, prefer one that does not widen the status vocabulary: a
separate frontmatter key naming the amendment's task id and date leaves `status` meaning exactly what
it means today, and lets a check answer "which approved specs have unreviewed amendments" without any
consumer of `status` changing behaviour.

**The count will keep growing.** Three of the four were amended in the last two waves, and the
pattern (a task that implements a feature also extends its contract) is the normal shape of work
here, not an exception. Whatever is decided should assume this state is permanent and common rather
than a backlog to be drained.

## Risks and rollback

The risk is choosing a mechanism that makes `verifier-agent` return `blocked` on an amended spec,
which would break exactly the workflow that produced all four cases and would be discovered only when
the next contract-amending task fails its own verification. If a new state is introduced, verify it
against a real run of `verifier-agent` over an amended spec before closing this task, rather than
reasoning about it.

Rollback is one revert; nothing persisted depends on the decision.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py"

- [ ] The convention is stated in `docs/spec/README.md`, including why `draft` is not used.
- [ ] `spec-author` points at it, so an author amending an approved contract finds the rule without
      reading four existing specs to infer it.
- [ ] If a machine-readable marker is introduced, a command can list the approved specs carrying an
      unreviewed amendment, and it reports the four named above against the current tree.
- [ ] If no marker is introduced, that decision is recorded with its reasoning rather than left as
      the absence of one.
- [ ] `verifier-agent` still returns a usable verdict against an amended spec, demonstrated by a real
      run rather than asserted.
- [ ] No spec's `status:` field is changed by this task.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
