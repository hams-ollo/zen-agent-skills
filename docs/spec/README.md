# Specifications

The behavioral contracts this kit builds and verifies against, plus the reports that sit beside
them. A spec says **what** should be true and **why**; it is not a plan, an architecture brief, or a
task list.

Specs are drafted by [`spec-author`](../../.agents/skills/spec-author/SKILL.md), reviewed by
[`spec-quality`](../../.agents/skills/spec-quality/SKILL.md), and approved by a human. Nothing is
decomposed into tasks until `status: approved` is set, and `spec-author` never sets it itself.

## One file kind per question asked

A spec accumulates sibling reports. Each answers a different question, and none replaces another. A
spec may have one, several, or none. This is the same list carried in the layout table in
[`AGENTS.md`](../../AGENTS.md); if the two ever disagree, `AGENTS.md` is authoritative.

| File | Question it answers | Produced by |
|---|---|---|
| `<spec>.md` | What should be true? | [`spec-author`](../../.agents/skills/spec-author/SKILL.md) |
| `<spec>.conformance.md` | Does the implementation match the contract? | [`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md) |
| `<spec>.verification.md` | Was this run's work acceptable? | [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) |
| `<spec>.readiness.md` | May implementation begin at all? | [`spec-plan-readiness`](../../.agents/skills/spec-plan-readiness/SKILL.md) |
| `<spec>.characterization.md` | What did this behave like before a contract existed? | [`test-author`](../../.agents/skills/test-author/SKILL.md) |

The distinction between the first two reports is the one most easily lost. **Conformance** is a
matrix over the whole contract: every scenario and surface element classified `Conformed`,
`Diverged`, or `Not-built`, with a coverage proof. **Verification** is a verdict on one run, with
evidence, recorded at the moment that run happened. A conformance matrix is re-derivable at any
time; a verification record is history and is never rewritten.

That difference has a mechanical consequence. The spec-closeout gate looks for a
`<stem>.conformance.*` sibling, so a `.verification.md` alone does not satisfy it. `house-review`
carried only a verification record until `chore-0025`, and would have blocked on exactly that.

Every report except `<spec>.md` is a **ledger**: it records what was observed on a given date.
[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) skips them rather than reporting them as drift,
because a matrix quoting what a command printed in July is not stale when the command prints
something else today.

## The specs

| Spec | Status | Scenarios | Siblings |
|---|---|---|---|
| [`build-adapters`](build-adapters.md) | approved | 14 | [conformance](build-adapters.conformance.md), [readiness](build-adapters.readiness.md) |
| [`doc-sync`](doc-sync.md) | approved | 15 | [conformance](doc-sync.conformance.md) |
| [`house-review`](house-review.md) | approved | 18 | [conformance](house-review.conformance.md), [verification](house-review.verification.md) |
| [`install`](install.md) | approved | 15 | [conformance](install.conformance.md), [characterization](install.characterization.md) |
| [`spec-author`](spec-author.md) | approved | 7 | [conformance](spec-author.conformance.md) |
| [`test-author`](test-author.md) | approved | 5 | [conformance](test-author.conformance.md) |
| [`tracker-links`](tracker-links.md) | approved | 9 | [conformance](tracker-links.conformance.md), [verification](tracker-links.verification.md) |
| [`validate-skills`](validate-skills.md) | approved | 21 | [conformance](validate-skills.conformance.md), [verification](validate-skills.verification.md) |
| [`verifier-agent`](verifier-agent.md) | approved | 11 | [conformance](verifier-agent.conformance.md) |

Nine specs, 115 scenarios, every one with a conformance matrix as of 2026-08-05.

## A limit worth knowing before reading any matrix

Most of what this kit ships is prose, not code. When a spec describes a skill, both sides of its
conformance audit are natural language and the evidence column cites a clause rather than a code
path. That establishes the skill **instructs** the specified behavior, not that anything
**enforces** it: a prose skill can conform perfectly and still be ignored by the agent running it.

Closing that gap is what the [hooks module](../../.agents/hooks/README.md) is for, and it reaches
only the rules that are mechanically decidable. The rest is closed by exercising a skill on real
work and recording what happened, which is what the verification records are.
