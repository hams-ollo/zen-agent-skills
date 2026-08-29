# Specifications

The behavioral contracts this kit builds and verifies against, plus the reports that sit beside
them. A spec says **what** should be true and **why**; it is not a plan, an architecture brief, or a
task list.

Specs are drafted by [`spec-author`](../../.agents/skills/spec-author/SKILL.md), reviewed by
[`spec-quality`](../../.agents/skills/spec-quality/SKILL.md), and approved by a human. Nothing is
decomposed into tasks until `status: approved` is set, and `spec-author` never sets it itself.

## Amending a spec that is already approved

The lifecycle is `draft` then `approved`, and it stops there. It carries no value for the state that
keeps recurring: **approved, then amended, with the amendment not yet re-approved.** A task that
implements a feature and extends its contract in the same pass is the normal shape of work here, so
this is a permanent, common state rather than a queue that will one day be empty.

The convention, in use since 2026-07-27 and written down here on 2026-08-06 (`chore-0030`):

1. **Leave `status: approved`.** The field records the last contract a human agreed to, which is
   still true of everything the amendment did not touch.
2. **Add a dated note to the spec's header**, under the existing approval line, naming the date, the
   amending task's id, and the scenarios or sections that changed. State the pending state in the
   words **pending the author's re-approval**, so the queue is at least findable with a search.
3. **Repeat it in any sibling report** whose rows audit the amended clauses, so a matrix is not read
   as auditing an approved contract in full.
   [`build-adapters.conformance.md`](build-adapters.conformance.md) and
   [`install.conformance.md`](install.conformance.md) both do this.
4. **Re-approval is the author's**, granted by editing the note. No agent grants it, and no agent
   changes `status`.

### Why an amended spec does not go back to `draft`

This is a mechanical constraint, not a preference.
[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) returns `blocked` on a spec whose
`status` is not `approved`, so a task that amends a contract and flips its status makes the
verification run for that very change unanswerable, and the amendment can never be verified into
place. [`new-task`](../../.agents/skills/new-task/SKILL.md) separately refuses to decompose an
unapproved spec, so one changed scenario would stall every other task waiting on the same contract.
Reopening to `draft` was tried once, on [`house-review`](house-review.md) (`chore-0012`), and the
note recording it is still in that spec's header.

### Why there is no third status value, and no marker key yet

Five things read a spec's `status`: `verifier-agent` blocks on anything but `approved`; `new-task`
refuses to decompose it; [`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) classifies a document
carrying one as a contract and therefore never edits it; the
[spec-closeout gate](../../.agents/hooks/spec-conformance-gate.py) tests it against a terminal-status
set that excludes `approved` on purpose, with a test pinning that; and the table below. Two of those
five would need a behavioural branch, `verifier-agent` and `new-task`, since both compare the value
against `approved` and stop when it differs; the other three read the field's presence, or a closed
terminal-status set a new value falls outside harmlessly, or display it. Two branches on the spine's
verification and decomposition gates, plus a new concept for every reader of every spec, in exchange
for a distinction the header note already carries where a reader is already looking.

A separate frontmatter key would be cheaper, and stays the preferred form if this is ever mechanised.
Frontmatter here is governed by nothing: the six-key allow-list in
[`validate-skills.py`](../../scripts/validate-skills.py) applies to `.agents/skills/*/SKILL.md` only.
A key naming the amending task's id and date would leave `status` meaning exactly what it means
today, and would let a check answer "which approved specs carry an unreviewed amendment" without any
consumer of `status` changing behaviour.

It is deliberately not introduced yet, for one reason. Such a key earns its keep only through that
check, and the check is honest only once every spec already in this state carries the key. Every spec
listed below is already in it, and each states its pending state in different words. Most say
*pending the author's re-approval*; `house-review` says its frontmatter is left at `approved` for the
author to confirm at closeout; `doc-sync` and `spec-author` say the amendment needs a maintainer's
re-approval, and those two keep the note at the foot of the document rather than in the header.
Retrofitting means editing every one of those approved contracts, which is the author's pass and not
an agent's. Until it happens, this state lives in prose, and prose is
not machine-readable: that is the known cost of this convention, not an oversight in it.

### The author's re-approval queue

Every spec listed below is approved and carries an amendment the author has not re-read. Some carry
more than one: `install` carries two, `build-adapters` three, since `chore-0043` and again since
`chore-0062`, `cloud-executable` three, since `chore-0061` and again since `chore-0049`, and
`validate-skills` four, since `chore-0047`, again since `chore-0054`, and again since `chore-0065`.

| Spec | Amendment | Amended |
|---|---|---|
| [`build-adapters`](build-adapters.md) | `S-015` to `S-017`, the `plugin` target (`feat-0034`); `S-018`, the code-span and fence exception (`chore-0043`); `S-019`, what a relative link inside an emitted lens must satisfy (`chore-0062`) | 2026-08-06, 2026-08-19, 2026-08-27 |
| [`cloud-executable`](cloud-executable.md) | `S-017` and `S-018` repointed from `bug-0018`, closed 2026-08-08, to the open `bug-0020` (`chore-0051`); `S-020` and the `Output` surface element, what a passing gate's entry carries (`chore-0061`); the `Gate set` surface element restated as a property rather than a count (`chore-0049`) | 2026-08-20, 2026-08-27, 2026-08-28 |
| [`doc-sync`](doc-sync.md) | `skipped` and `not_audited` split into two fields (`chore-0027`) | 2026-08-05 |
| [`house-review`](house-review.md) | `S-014` to `S-018`, the evidence gate and finding signature (`feat-0040`) | 2026-08-05 |
| [`install`](install.md) | `S-015`, the draft-skill axis (`feat-0036`); `S-016` to `S-018`, Goal 10 and `--replace-adopted`, the adopted-versus-derived axis (`bug-0018`) | 2026-08-05, 2026-08-07 |
| [`spec-author`](spec-author.md) | `S-006` and `S-007`, the spec location (`chore-0027`) | 2026-08-05 |
| [`systematic-debugging`](systematic-debugging.md) | `S-014` and `S-015`, where instrumentation may live and what happens where it cannot live anywhere, settling both Open Questions before anything was built against the contract (`chore-0078`) | 2026-08-29 |
| [`validate-skills`](validate-skills.md) | `S-022`, the code-span and fence exception (`chore-0039`); `S-023` and the "what it reads" surface entry, the lens-composition rule (`chore-0047`); `S-024` and the `Output` and "what it reads" surface entries, the supporting-file link rule (`chore-0054`); `S-025` and the same two surface entries again, the non-skill `.agents/` markdown link rule (`chore-0065`) | 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-27 |

The `house-review` row was missed when this table was first written, and how it was missed is the
argument for eventually replacing this table with a marker key. That spec's note says its
frontmatter is "left at `approved` for the author to confirm at closeout" rather than using the
words *pending* or *re-approval*, so it is invisible to the search that finds the rest of this
table. A convention carried in prose can only be found by a reader who already knows every
phrasing it has ever taken.

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
| `<spec>.runbook.md` | How does a person perform a step no agent here can? | a human, or an agent writing for one |

The runbook is the newest kind, added 2026-08-07, and only one spec has one. It exists because
[`cloud-executable`](cloud-executable.md) is the first contract here whose verification depends on an
action nothing in this repository can take: `claude --cloud` refuses a non-interactive invocation, so
the proof session has to be started by a person from a terminal or a browser. Putting those
instructions in the verification record was the obvious alternative and is wrong, because that record
is a ledger of one attempt on one date while the instructions are current-state and will be edited.
A kind is worth adding when two documents would otherwise have to drift apart to stay correct.

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
| [`agent-observatory`](agent-observatory.md) | approved | 22 | [conformance](agent-observatory.conformance.md) (22 of 22 built), [readiness](agent-observatory.readiness.md) |
| [`build-adapters`](build-adapters.md) | approved | 19 | [conformance](build-adapters.conformance.md), [readiness](build-adapters.readiness.md) |
| [`cloud-executable`](cloud-executable.md) | approved | 20 | [conformance](cloud-executable.conformance.md), [readiness](cloud-executable.readiness.md), [verification: S-001 to S-016](cloud-executable.s001-s016.verification.md) (**fail**, fixed same day), [verification: the proof run](cloud-executable.verification.md) (**blocked**), [runbook](cloud-executable.runbook.md) |
| [`doc-sync`](doc-sync.md) | approved | 15 | [conformance](doc-sync.conformance.md) |
| [`house-review`](house-review.md) | approved | 18 | [conformance](house-review.conformance.md), [verification](house-review.verification.md) |
| [`install`](install.md) | approved | 18 | [conformance](install.conformance.md), [characterization](install.characterization.md) |
| [`spec-author`](spec-author.md) | approved | 7 | [conformance](spec-author.conformance.md) |
| [`systematic-debugging`](systematic-debugging.md) | approved | 15 | [conformance](systematic-debugging.conformance.md) (15 of 15), [verification](systematic-debugging.verification.md) |
| [`test-author`](test-author.md) | approved | 5 | [conformance](test-author.conformance.md) |
| [`tracker-links`](tracker-links.md) | approved | 9 | [conformance](tracker-links.conformance.md), [verification](tracker-links.verification.md) |
| [`validate-skills`](validate-skills.md) | approved | 25 | [conformance](validate-skills.conformance.md), [verification](validate-skills.verification.md) |
| [`verifier-agent`](verifier-agent.md) | approved | 11 | [conformance](verifier-agent.conformance.md) |

Twelve specs, 184 scenarios, all approved. **All twelve now carry a conformance matrix**, holding
all 184 of those scenarios, recomputed from the files on 2026-08-29 rather than incremented: the
twelve counts in the column above sum to 184, and no spec is now without a matrix.
[`systematic-debugging`](systematic-debugging.md) was the last one, audited at `feat-0061`'s
closeout on 2026-08-29.

**Carrying a matrix is not the same as being fully audited, and 184 is the first figure rather than
the second.** It counts scenarios in specs that have a matrix, not scenarios a matrix has classified.
`install` is the spec where the two differ: `bug-0018` added S-016 to S-018 on 2026-08-07 and the
matrix update is owed at that task's closeout, so part of that contract has never been audited.

**The second figure is deliberately not stated here.** Deriving it needs a per-matrix count of
classified rows, which nothing computes and which this file has already carried wrong: the standing
claim that `install`'s matrix "covers 15 of its 18 scenarios" does not survive a check, since that
matrix cites 17 of the 18 scenario ids. Whether the other two are classified rows or prose recording
what is owed is the question a reader has to answer by opening the file, and a number asserted here
would be a guess wearing arithmetic. `chore-0075` is the open task that would make every figure on
this page computed rather than hand-maintained, and this is the second one it would have caught.

[`systematic-debugging`](systematic-debugging.md) was the second **forward** spec here, written
before an implementation rather than pinning one that already existed, so from 2026-08-19 until
2026-08-29 it was the only spec with nothing to audit. It carries 15 rather than the 13 it was
approved with, since `chore-0078` settled both of its Open Questions on 2026-08-29.

[`cloud-executable`](cloud-executable.md) was the first forward spec and stopped being the exception
on 2026-08-19, when `chore-0034` audited it. That matrix is worth reading for what it declined to
claim: when it was written, S-017 to S-019 and the unattended pull request surface were all recorded
**Not-built**, because the Phase 4 proof run they describe was still recorded `blocked` and had never
run. A matrix that reported them any other way would have been worse than no matrix. The proof run of
2026-08-20 moved all but S-019, whose Given is a run whose gates fail, and that run's did not.

## A limit worth knowing before reading any matrix

Most of what this kit ships is prose, not code. When a spec describes a skill, both sides of its
conformance audit are natural language and the evidence column cites a clause rather than a code
path. That establishes the skill **instructs** the specified behavior, not that anything
**enforces** it: a prose skill can conform perfectly and still be ignored by the agent running it.

Closing that gap is what the [hooks module](../../.agents/hooks/README.md) is for, and it reaches
only the rules that are mechanically decidable. The rest is closed by exercising a skill on real
work and recording what happened, which is what the verification records are.
