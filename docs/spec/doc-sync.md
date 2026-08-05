---
title: doc-sync
status: approved
---

# doc-sync

Behavioral contract for the `doc-sync` skill (ROADMAP Epic B item 9). Drafted 2026-07-25 by the
`spec-author` skill and self-checked to `ready` with the `spec-quality` lens.

## Problem

The kit ships two documentation skills and neither answers the question that generates most
documentation work. [`doc-author`](../../.agents/skills/doc-author/SKILL.md) writes a document that
does not exist yet. [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) edits a document
someone has already decided is wrong. Nothing identifies *which* documents went wrong, and that is
the step that costs the time.

The evidence is in this repository's own history. Across the 2026-07-24 session, shipping a single
skill invalidated four to seven documents each time: workflow diagrams that no longer matched the
skill set, prose that still said "planned" about something that had shipped, catalog rows and
roadmap items lagging the code. Every instance was found by hand, by re-reading the whole
documentation set after each change. That does not scale with the size of the doc set, and it fails
silently, because a missed claim reads exactly like a correct one.

An agent that simply fixes what it finds makes this worse, because documentation is not one kind of
thing. Some documents are derived from the code, so when they disagree with it the document is
wrong. Others govern the code: an approved spec, a rules module, the repository's own agent
instructions. When one of those disagrees with the code, the code is wrong, and an agent that
"corrects" the document has quietly rewritten the contract to match the bug. A third kind is
history: an append-only ledger does not drift, because an entry describing a past state was never a
claim about the present.

The missing capability is therefore detection with a policy attached: find drift, ground every
reported claim in a repository fact, and know which documents may be corrected, which may only be
reported, and which must not be read as drift at all.

## Goals

1. Detect documentation drift by comparing claims in prose against facts in the repository, and
   report every finding together with the specific fact that grounds it.
2. Classify each document in scope as current-state, contract, or ledger, and let that
   classification govern what may be done with the document.
3. Default to reporting only, so that detecting drift never changes a file.
4. Update current-state documentation only after explicit approval, and only for the findings that
   were approved.
5. Never modify a contract document, and report a contract disagreement as a possible defect in the
   code rather than a defect in the document.
6. Skip ledger documents, and make the skip visible rather than silent.
7. Return a positive result when nothing has drifted, so a clean run is distinguishable from a run
   that did not look.
8. Separate mechanically proven findings from judgment calls, so dismissing a false positive costs
   the user one identifier.
9. Leave an audit trail for every applied change, recording what was changed, the claim it
   corrected, the evidence behind it, and the confidence it carried, so a later reader can judge the
   change without re-running the audit.

## Non-Goals

- Creating a document that does not exist yet. That is `doc-author`.
- Editing a document the user has already decided to change. That is `doc-revise`.
- Judging documentation quality, structure, reading level, or voice.
- Enforcing writing or formatting conventions. A house-style violation is not drift.
- Auditing an implementation against a spec. That is `spec-conformance`.
- Deciding whether a disagreement in a contract document should be resolved by changing the code.
  It reports the disagreement; a human decides.
- Repairing code, tests, or configuration found to be wrong while auditing.

## Constraints

- A document's kind is decided by property rather than by a filename list, so the classification
  travels to repositories this kit has never seen:
  - **current-state**: derived from the code or repository state, checkable against it, carrying no
    human-owned approval marker.
  - **contract**: human-owned and authoritative over the code, including any document carrying an
    approval or status field, the repository's canonical agent instruction file, and its rules
    modules.
  - **ledger**: append-only history whose entries describe past states.
- A document whose kind cannot be determined is treated as a contract document, so the failure mode
  is inaction rather than an unauthorized edit.
- Every reported finding names the repository fact that grounds it. A claim that no fact confirms or
  contradicts is not reported.
- An approved finding is applied only if it still reproduces against the repository as it stands at
  apply time, since the repository may have moved since the finding was reported.
- A finding of either confidence may be approved, but approval is requested per finding with its
  confidence and evidence shown, so a `suspected` finding is never applied without the human having
  seen that it is suspected. Confidence ranks findings for the reader; it does not gate them.
- Applying a correction composes the `doc-revise` skill for editing discipline rather than restating
  its rules.
- Detection is inexact. Prose-versus-code agreement has no exact oracle, so the report is built for
  cheap dismissal rather than presented as precise.
- The skill reads the repository it runs in, including the code its documents describe, and consults
  no external source.
- Vendored third-party material in the tree, meaning content the repository does not track or that
  carries its own upstream license, is out of the default documentation scope and is never edited,
  in any mode, even when a user names its path. Drift there belongs to its upstream.

## Scenarios

### Scenario S-001: a current-state document contradicts the code

- **Given** a current-state document whose prose states something the repository contradicts
- **When** doc-sync runs over the documentation set
- **Then** it returns `verdict: drift_found` with a finding naming the document, the drifted claim,
  the repository fact that contradicts it, and a proposed correction it does not perform, and no
  file on disk is modified.

### Scenario S-002: reporting is the default

- **Given** a doc-sync run invoked with no mode argument
- **When** the run completes
- **Then** the report states `mode: dry-run`, `applied` is empty, and every file in the
  documentation set is byte-for-byte unchanged.

### Scenario S-003: corrections reach only the approved findings

- **Given** a completed dry run reporting several findings against current-state documents, and a
  user who approves a subset of them by identifier
- **When** doc-sync is re-invoked in apply mode with that subset
- **Then** it edits only the documents named by the approved identifiers, records an applied entry
  for each, and leaves the unapproved findings reported and their documents unmodified.

### Scenario S-004: a contract document disagrees with the code

- **Given** a contract document whose stated requirement the implementation does not satisfy
- **When** doc-sync runs, in either mode
- **Then** it reports the disagreement as a possible defect in the code, records the document's kind
  as contract, and the document is byte-for-byte unchanged.

### Scenario S-005: a ledger document sits inside the scanned path

- **Given** an append-only ledger document within the documentation scope
- **When** doc-sync runs
- **Then** it produces no finding against that document and lists it in the skipped set with the
  reason that ledger history is not drift.

### Scenario S-006: the documentation set is clean

- **Given** a documentation set in which no claim contradicts a repository fact
- **When** doc-sync runs
- **Then** it returns `verdict: clean` with an audited set naming every document read and its
  classification, so the absence of findings is evidenced rather than assumed.

### Scenario S-007: a document names something that does not exist

- **Given** a document referencing a skill, file, command, or path absent from the repository
- **When** doc-sync runs
- **Then** it reports the finding with `confidence: grounded`, citing the absence of the named thing
  as the evidence.

### Scenario S-008: a claim is stale but the judgment is not mechanical

- **Given** a document whose narrative claim is contradicted by a repository fact that needs
  interpretation rather than a lookup, such as a count, a status label, or a described ordering
- **When** doc-sync runs
- **Then** it reports the finding with `confidence: suspected`, names the fact, and states the
  reading under which the claim would still be true, so the user can dismiss it in one step.

### Scenario S-009: the run is scoped to a change

- **Given** a documentation set and a git reference or commit range describing a change
- **When** doc-sync runs scoped to that change
- **Then** it audits only those documents in scope that reference the changed files or describe the
  behavior they implement, the audited set records the narrowed scope, and the documents left unread
  by the narrowing are listed in `not_audited` with that reason, rather than implying the whole set
  was checked.

### Scenario S-010: a document's kind cannot be determined

- **Given** a document in scope matching none of the three classification properties
- **When** doc-sync runs
- **Then** it records the document's kind as contract, reports any finding against it as report-only,
  and does not edit it even in an apply run.

### Scenario S-011: an approved correction is written

- **Given** an approved finding against a current-state document
- **When** doc-sync applies it
- **Then** the edit changes only the drifted claim, leaves the surrounding text and the document's
  voice intact, and every relative link in the edited document still resolves to a file that exists.

### Scenario S-012: a suspicion cannot be grounded

- **Given** a passage that reads as though it might be stale but that no repository fact confirms or
  contradicts
- **When** doc-sync runs
- **Then** the passage produces no finding and the report does not mention it.

### Scenario S-013: no report destination is supplied

- **Given** a doc-sync run invoked without a report destination
- **When** the run completes
- **Then** it returns the report inline and creates no file, so persisting a drift report is an
  explicit request rather than a side effect of auditing.

### Scenario S-014: an applied change is auditable afterwards

- **Given** an approved finding carrying `confidence: suspected`
- **When** doc-sync applies it
- **Then** the applied record names the finding, the document changed, the claim it corrected, the
  evidence, and the `suspected` confidence it carried, so a later reader can see that a judgment
  call was applied and on what basis, without re-running the audit.

### Scenario S-015: a vendored document is named explicitly

- **Given** a path scope naming vendored third-party material inside the tree
- **When** doc-sync runs in apply mode with a finding against that material approved
- **Then** it reports the finding and leaves the file byte-for-byte unchanged, because vendored
  material is never edited even when a user names its path.

## Proposed Surface

| Element | Detail |
|---|---|
| Inputs (required) | Documentation scope: by default every Markdown document the repository tracks, excluding vendored material; or an explicit list of paths. Naming a vendored path brings it into the audit but never makes it editable |
| Inputs (optional) | Change scope (a git reference or commit range); approved findings (a list of identifiers); report destination |
| `mode` | `dry-run` (the default) or `apply`. `apply` requires a non-empty approved-findings list; invoked without one it makes no edits and reports as a dry run |
| `audited` | Every document read, with its classification and the scope under which it was read |
| `skipped` | Every document that was classified and then deliberately excluded from the audit, with the reason (for example ledger history). A skipped document was read far enough to place it |
| `not_audited` | Every document that was in scope and never read at all, with the reason (for example a narrowed change scope, or a budget that ran out mid-run), so a partial audit is never reported as a whole one |
| `findings` | Per finding: `id` (`D-NNN`), `document`, `kind`, `claim`, `evidence`, `confidence`, `proposed_correction` |
| `proposed_correction` | The change that would resolve the drift: to the document for a `current-state` finding, to the code for a `contract` finding |
| `kind` | `current-state`, `contract`, or `ledger` |
| `confidence` | `grounded` (a mechanical check proved the contradiction) or `suspected` (a repository fact contradicts the claim under interpretation) |
| `applied` | Per applied finding, the audit trail: its identifier, the document changed, the claim corrected, the evidence, and the confidence it carried; empty in a dry run |
| `verdict` | `clean` when `findings` is empty, `drift_found` otherwise |
| Report delivery | Returned inline by default; written to a file only when a report destination is supplied |

## Open Questions

None. The two questions raised against the first draft were resolved by the maintainer on
2026-07-25 and now live in the contract: see Goal 9 with S-014 for approval and auditability, and
the vendored-material constraint with S-015.

Amended on 2026-08-05 by `chore-0027` and re-checked to `ready` with the `spec-quality` lens: the
Proposed Surface now carries `skipped` and `not_audited`
as two fields with distinct meanings, and `S-009` names `not_audited` as where a narrowed scope
records what went unread. This closes the single divergence recorded in
[`doc-sync.conformance.md`](doc-sync.conformance.md). The contract had lagged the skill rather than
the skill having erred: the field split emerged from the `feat-0020` dogfood, after this spec was
written, because collapsing the two makes a document nobody read indistinguishable from a ledger
deliberately passed over, which is the failure Goal 6 and `S-006` exist to prevent. The amendment
decided nothing new, and it needs a maintainer's re-approval.
