---
id: chore-0014
title: Decide whether verifier-agent's two blocked preconditions short-circuit or accumulate
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B #7: verifier-agent"
depends_on: []
spec: docs/spec/verifier-agent.md
scenarios: [S-005, S-006]
touched_files:
  - .agents/skills/verifier-agent/SKILL.md
  - docs/spec/verifier-agent.md
  - docs/spec/code-review.verification.md
created: 2026-07-27
---

## Problem

[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) has two preconditions that produce
`blocked`: an unapproved spec (`S-005`) and a missing or unrunnable verification command (`S-006`).
The contract does not say what happens when **both** are true at once, and its two halves point
different ways.

Step 1 of the skill body tells the run to "stop and return `blocked`" at each precondition, which
reads as short-circuit: report the first, never evaluate the second. But the output format defines
`blocking_reasons` as a **list**, which reads as accumulation. Both readings are defensible from the
text, and they produce different records for the same situation.

This is not hypothetical. The `feat-0024` run hit exactly that state: `docs/spec/code-review.md` was
`status: draft` **and** `code-review` had no declared verification command, so `S-005` and `S-006`
were satisfied simultaneously. The record at
[`code-review.verification.md`](../../docs/spec/house-review.verification.md) reports one blocking reason
because that is what the procedure literally produces, and flags the ambiguity rather than resolving
it on its own authority.

It matters because a partial blocking report is a slow round trip. A user who resolves the unapproved
spec, re-runs, and is then blocked again on a missing command has learned in two runs what one run
could have told them.

## Scope

**In scope:** decide between the two behaviors, then make the skill body and the spec agree, and
regenerate the conformance matrix.

- **Accumulate** (recommended): check both preconditions, report every one that holds. Fixes the
  round-trip problem, matches the plural `blocking_reasons` field, and costs nothing, because both
  checks are cheap and neither runs the implementation.
- **Short-circuit**: keep the current literal reading, and say so explicitly in both the skill and the
  spec so the plural field stops implying otherwise.

Either way, add or amend a scenario covering the both-true case, since its absence is what allowed
the ambiguity.

**Out of scope:** changing what either precondition detects, or the meaning of `blocked` itself. The
three-verdict scheme is settled. Exercising `S-006` on its own, which `feat-0024` observed but did not
record as its exercised branch.

## Implementation notes

- The spec is `status: approved`, so this follows the `chore-0013` procedure: reopen to `draft`,
  amend, self-check with `spec-quality`, a **human** sets `approved`, then regenerate the matrix.
- Prefer amending the existing `S-005` and `S-006` wording over adding a third scenario, if the
  both-true behavior can be stated as a clause on each. A scenario per combination does not scale.
- Whichever way this goes, the ordering of reported reasons should be deterministic, so two runs on
  the same state produce the same record.
- This task will also **create** `docs/spec/verifier-agent.conformance.md`, which does not exist yet:
  `verifier-agent` has an approved contract and has never been audited against it. That path is
  deliberately absent from `touched_files` because `.tasks/validate.py --strict` requires every listed
  path to exist already, so any create-a-file task fails strict mode by construction. That tension
  between `new-task`'s honest-write-surface rule and `--strict` is real and unresolved; noted here
  rather than worked around silently.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] The skill body and `docs/spec/verifier-agent.md` agree on the both-true behavior.
- [x] A scenario covers the case where both preconditions hold.
- [x] `spec-quality` returns `ready` on the amended spec, and a human set `status: approved`.
- [x] `docs/spec/verifier-agent.conformance.md` is regenerated against the amended contract.
- [x] `docs/spec/code-review.verification.md`'s observation is updated to point at the resolution.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-27)

**Decision: accumulate.** Both preconditions are checked before returning, and every reason that holds
is reported in a fixed order (unapproved contract first, missing command second). Neither check runs
the implementation, so evaluating both is free, while short-circuiting sends the reader away to fix
one blocker and straight back for the second. The plural `blocking_reasons` field was already the
right shape; the prose was what was wrong.

`S-011` covers the both-true case and traces to goals 1 and 5, so no new goal was needed. That broke a
three-spec run of `spec-quality` catching orphaned scenarios, and the difference is instructive: the
previous three orphans (`validate-skills` S-015, `build-adapters` S-013, `code-review` S-011) were all
invocation or channel concerns, while this one is core behavior.

`docs/spec/verifier-agent.conformance.md` now exists. Every scenario and surface element conforms, and
the matrix says why that is a weaker result than it looks: the contract and the skill were drafted the
same day from the same intent, so a clean matrix mostly confirms the two documents still agree. It
also states the limit that applies to auditing any prose skill, that conformance establishes the skill
**instructs** the specified behavior and not that anything **enforces** it. The `feat-0024` run
remains the stronger evidence.

The observation in `code-review.verification.md` now points at this resolution. Its single-reason
record was left as written, because a ledger entry describing a past run is not corrected to match a
later contract.
