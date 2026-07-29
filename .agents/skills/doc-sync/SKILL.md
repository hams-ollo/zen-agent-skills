---
name: doc-sync
description: Use when code has moved and the documentation may not have, or when a documentation set needs auditing for stale claims. Detects documentation drift by checking prose claims against repository facts, classifies every document as current-state (correctable), contract (report-only, human-owned) or ledger (skipped), and reports each finding with a stable id, the fact that grounds it, and a grounded or suspected confidence. Dry run is the default and detection never changes a file; updating a current-state document requires explicit per-finding approval and leaves an audit trail, and a contract document is never edited because a disagreement there means the code is wrong. Distinct from doc-author (writes documents that do not exist), doc-revise (edits a document you have already decided to change, and which this composes for editing discipline), and spec-conformance (audits code against a spec). It finds what drifted; it does not silently fix it.
license: MIT
---

# doc-sync

Find out which documents went wrong. The kit already has a skill for writing a document that does
not exist ([`doc-author`](../doc-author/SKILL.md)) and one for editing a document you have already
decided is wrong ([`doc-revise`](../doc-revise/SKILL.md)). Neither answers the question that
generates the work: after the code moved, *which* of these documents is now lying?

Finding out by hand does not scale and it fails silently, because a missed stale claim reads exactly
like a correct one. This skill makes the sweep systematic and grounds every claim it reports in a
specific repository fact.

**The classification is the whole idea.** A naive drift-fixer is worse than no drift-fixer, because
documentation is not one kind of thing. A document derived from the code is wrong when it disagrees
with the code. A document that *governs* the code (an approved spec, a rules module, the
repository's agent instructions) means the opposite: when it disagrees with the code, the code is
wrong, and an agent that "corrects" the document has quietly rewritten the contract to match a bug.
A ledger does not drift at all, because an entry describing a past state was never a claim about the
present. So this skill decides what a document *is* before it decides what may be done with it.

It composes [`doc-revise`](../doc-revise/SKILL.md) by reference for the editing half and does not
restate its rules, the same way [`verifier-agent`](../verifier-agent/SKILL.md) composes
[`spec-conformance`](../spec-conformance/SKILL.md).

## When to use

- A change has landed and you want to know which documents it invalidated.
- A documentation set has not been audited in a while and you suspect stale claims.
- Before a release, a handoff, or a status update, when documents are about to be trusted by someone
  who cannot check them.
- After a rename, a move, or a deletion, when cross-references may now point at nothing.

## When not to use

- The document does not exist yet: use [`doc-author`](../doc-author/SKILL.md).
- You already know what is wrong and just want it changed: use [`doc-revise`](../doc-revise/SKILL.md).
- You want to know whether an implementation matches its spec: use
  [`spec-conformance`](../spec-conformance/SKILL.md). That audits code against a contract; this
  audits prose against a repository.
- You want an opinion on how well a document is written, structured, or pitched. Quality is not
  drift, and neither is a house-style violation.

## Inputs

Required:

- **Documentation scope**: by default every Markdown document the repository tracks, excluding
  vendored third-party material. An explicit list of paths overrides the default.

Optional:

- **Change scope**: a git reference or commit range, to audit only what a change could have
  invalidated rather than the whole set.
- **Approved findings**: a list of finding ids to apply. Without this, the run is a dry run.
- **Report destination**: where to persist the report. Without it, the report is returned inline and
  no file is written.

## Procedure

### 0. Bound the scope before reading anything

The default scope is every tracked Markdown document, and on a real repository that is routinely
more than fits. An audit that runs out of budget partway through does not fail: it reports on the
documents it reached and says nothing about the rest, which reads exactly like a complete pass.
Since the entire value of this skill is that a clean verdict means something, an unbounded run can
produce the one output worse than not running at all.

So decide the scope first, and make it visible:

- **Count the scope before reading it.** If it does not fit, narrow it deliberately rather than
  discovering the limit mid-run.
- **Narrow by what a change could have invalidated** when a change scope was supplied, which is
  the cheapest and highest-yield cut available.
- **Otherwise narrow by blast radius**: the documents most read and most trusted first (the
  README, the getting-started and architecture documents, anything a newcomer or a release reads),
  then the rest.
- **Exclude vendored third-party trees from the count**, since they are never edited anyway.
- **Record what you did not reach** in `not_audited`, with the reason. A document that was in scope
  and never read is not a clean document, and the report must not let those two look alike.

### 1. Classify every document before reading it for drift

Decide what each document in scope *is*. Classify by property, not by filename, so the rule travels
to repositories this skill has never seen:

| Kind | Property | Typical examples | What may be done |
|---|---|---|---|
| current-state | derived from the code or repository state, checkable against it, carrying no human-owned approval marker | `README.md`, architecture and catalog documents, status pages, a roadmap's status claims | reported, and correctable with explicit approval |
| contract | human-owned and authoritative over the code: carries an approval or `status` field, or is the repository's canonical agent instruction file or a rules module | approved specs, `AGENTS.md`, a house-style module | reported only, never edited |
| ledger | append-only history whose entries describe past states | `CHANGELOG.md`, completed task files, audit and verification reports | skipped entirely |

Three rules protect this step:

- **An unclassifiable document is treated as a contract.** When you cannot confidently place a
  document, the fail-safe is report-only. The failure mode must be inaction, never an unauthorized
  edit.
- **A record of a past observation is a ledger, not a stale document.** A conformance matrix, a
  verification report, or any artifact quoting what a command printed on a given date is not drifting
  when the command would print something else today. It correctly records what happened then.
  Reporting it as drift is a false positive, and rewriting it destroys the record.
- **Vendored third-party material is never edited**, in any mode, even when a user names its path
  explicitly. Naming it brings it into the audit and no further. Drift there belongs to its
  upstream, and editing it means the next sync silently reverts you.

Record the classification for every document. It appears in the report, so a reader can see why a
given document was corrected, merely reported, or skipped.

### 2. Ground every claim in a repository fact

Read the documents, and for each factual claim find the fact that confirms or contradicts it: usually
a repository fact, but sometimes another passage in the same document. Claims worth checking are the
ones that go stale: what exists (files, skills, commands, directories), what something is called,
what state something is in, how a workflow is ordered, and where a link points.

Do not check state claims against a fixed vocabulary. Derive the staleness words from the document
set being audited: "planned", "shipped", "draft", "not built", "future", and "in progress" are all
staleness words when a document uses them, and a list carried over from a previous run or another
repository will miss whichever word this one actually uses. Widening the vocabulary widens what
counts as a stale word, not what counts as evidence: a document using "draft" still needs a
contradicting fact, in the repository or elsewhere in the document, before it becomes a finding.

A document can also drift against itself. When one passage asserts something and another passage in
the same document asserts the opposite (one section calling a skill a draft, a later one calling it
shipped), that is a contradiction the document supplies its own evidence for; no repository lookup is
needed to see it.

Check the code, not your memory of it. The whole value of the pass is that it looks.

Three habits decide whether this step actually finds anything:

- **Do not let formatting or line breaks define what counts as a claim.** A stale reference is just
  as likely to be a bare word in a sentence as a backticked token, and frontmatter, descriptions, and
  summary fields are prose that goes stale like any other. Prose wraps, so a qualifier and the
  subject it qualifies routinely land on different lines, and a claim can span a sentence or a
  paragraph. Search on the name, not on its decoration, and match the claim, not the line: a scan
  that only looks at marked-up tokens, or that only compares text within a single line, will miss the
  references that matter.
- **Verify a count by counting the thing, not by reading the sentence.** When a document says
  "all six" or "three lenses", go count the rows, the directories, or the entries. Tallies drift
  silently because nobody recounts them, and they are the cheapest claim in the document to check.
- **Confirm the referent, not just the token.** That a word is quoted or capitalized is no evidence
  it names a skill, a file, or a command. Establish what kind of thing the document is claiming
  exists before you go looking for it, or the report fills with dismissals.

**A claim you cannot tie to a fact produces no finding at all.** Not a low-confidence finding, not a
note: nothing. A report padded with ungrounded suspicion is one the reader stops trusting, and once
they stop reading it the skill has no value. Silence on an ungroundable passage is correct behavior.

### 3. Judge drift by the document's kind

The same disagreement means different things depending on what the document is.

- **Current-state document.** The document is stale. Report the drifted claim, the fact that
  contradicts it, and the correction that would resolve it.
- **Contract document.** The *code* is the suspect, not the document. Report the disagreement as a
  possible defect in the implementation, and propose the change to the code rather than to the
  document. Do not edit the document, in either mode, on any authority. This is the rule the skill
  exists to enforce: an agent that edits a contract to match the code has destroyed the contract.
- **Ledger document.** Produce no finding, and list the document in the skipped set with its reason.
  Make the skip visible, so a reader can tell a deliberate omission from an oversight.

Assign each finding a confidence:

- **`grounded`**: a mechanical check proved the contradiction. A named file, skill, command, or path
  does not exist; a link resolves to nothing; or two passages within the same document assert
  incompatible things, quoted side by side. The last of these needs no repository lookup, only the
  document itself, which makes it the cheapest high-confidence finding a pass can produce.
- **`suspected`**: a repository fact contradicts the claim, but only under interpretation. A count
  that no longer matches, a status label that looks stale, a described ordering that the code no
  longer follows. Name the fact, and state the reading under which the claim would still be true, so
  dismissing it takes one step.

Give every finding a stable `D-NNN` id. Ids are what make dismissal cheap: the user replies "drop
D-003" rather than re-describing the finding.

### 4. Report, and change nothing

Dry run is the default, not a flag. A run with no approved findings changes no file, and `applied`
is empty. Return the report inline unless a report destination was supplied.

Report the audited set positively: every document read, with its classification. "No drift found" is
only meaningful next to the list of what was actually checked, otherwise a clean verdict is
indistinguishable from a run that did not look. Whenever the scope was narrowed, by a change range,
by the Step 0 bounding, or by a budget that ran out mid-run, say so and list what went unread in
`not_audited`, so a partial audit is never read as a whole one.

### 5. Apply only what was approved, and leave a record

Applying requires explicit approval per finding, by id. Present each finding for approval with its
confidence and its evidence attached, so a `suspected` finding is never approved without the user
seeing that it is a judgment call. Confidence ranks findings for the reader; it does not gate them.
Either kind may be approved, because the human review is the gate.

Then:

- **Re-check before writing.** Apply an approved finding only if it still reproduces against the
  repository as it stands now. A finding reported before a later change may already be resolved, and
  applying it would reintroduce the drift.
- **Edit only current-state documents**, and only those named by approved ids. An approved id
  pointing at a contract, a ledger, or vendored material is reported as not applicable, not applied.
- **Compose [`doc-revise`](../doc-revise/SKILL.md)** for the edit itself. Its discipline governs:
  do not restate its rules here.
- **Record the audit trail.** Each applied entry names the finding id, the document, the claim
  corrected, the evidence, and the confidence it carried. Someone reading it later must be able to
  tell a mechanical correction from an applied judgment call, and see the basis for it, without
  re-running the audit.

## Output format

Return fields in this order:

```text
verdict: clean | drift_found
mode: dry-run | apply
audited:
  - document: ...
    kind: current-state | contract | ledger
    scope: full | change-scoped
skipped:
  - document: ...
    reason: ...
not_audited:
  - document: ...
    reason: ...
findings:
  - id: D-001
    document: ...
    kind: current-state | contract | ledger
    claim: ...
    evidence: ...
    confidence: grounded | suspected
    proposed_correction: ...
applied:
  - id: ...
    document: ...
    claim: ...
    evidence: ...
    confidence: ...
```

Rules:

- `verdict: clean` only when `findings` is empty, and only alongside a non-empty `audited` set that
  shows what was checked. `verdict: drift_found` otherwise.
- `not_audited` holds documents that were in scope and never read, whether the scope was bounded up
  front or the budget ran out mid-run. A non-empty `not_audited` never blocks a `clean` verdict, but
  it must appear next to it, so a partial pass is never mistaken for a whole one. `skipped` and
  `not_audited` are different claims: `skipped` means the document was classified and deliberately
  excluded (a ledger), `not_audited` means nothing is known about it.
- `mode: dry-run` is the default. An apply invocation with no approved findings makes no edits and
  reports as a dry run.
- `applied` is empty in a dry run, and never contains a contract, ledger, or vendored document.
- `proposed_correction` targets the document for a `current-state` finding and the code for a
  `contract` finding.
- Every finding carries `evidence` naming a specific repository fact. A finding without one is not
  reported.
- `skipped` states a reason per document, so an omission is always visible.

## Notes

- **There is no exact oracle for prose-versus-code drift.** Natural language does not compile, and
  whether a sentence still describes the code is often a judgment. This skill is a systematic sweep,
  not a proof. Expect false positives, design for cheap dismissal, and do not present the output as
  more precise than it is. The `grounded` split exists to keep the mechanical hits from being
  diluted by the judgment calls.
- The most valuable findings are usually the dullest: a reference to something that was renamed or
  deleted, a status label that outlived its state, a count that stopped matching. These are cheap to
  check mechanically and nearly invisible to a human re-reading familiar prose.
- **The ledger skip will suppress things that look actionable, and that is intended.** Archived task
  files and changelogs accumulate references that no longer resolve, because the file moved or the
  code did. Those are not drift: the entry still describes its moment correctly. If link integrity
  across the whole repository is what you want, that is a separate mechanical check, and running it
  through this skill would bury the real findings under archive noise.
- A contract finding is a bug report, not a documentation task. Route it accordingly: it likely
  belongs in the repository's task tracker, and possibly to
  [`spec-conformance`](../spec-conformance/SKILL.md) for a full audit of that contract against the
  implementation.
- Running this after each landed change costs less than running it before a release, because the
  drift is fresh and the cause is still obvious.

## Conventions

Follow the repo's house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)):
sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a
swappable default; a downstream adopter may replace it without touching this skill.
