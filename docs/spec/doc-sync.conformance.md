---
title: doc-sync conformance
spec: docs/spec/doc-sync.md
audited: 2026-08-05
---

# doc-sync conformance matrix

Spec-vs-implementation audit of [`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) against
[`doc-sync.md`](doc-sync.md). Produced by `chore-0025`. `doc-sync` shipped as `feat-0020` on
2026-07-25 and was iterated by `feat-0021` and `chore-0006`; none of those produced a matrix.

At fifteen scenarios this is the largest contract in the repository, and the one with the most
apply-path machinery, which is also the machinery that can damage a file. The rows about what
`doc-sync` refuses to edit are the ones worth reading closely.

## What this audit can and cannot establish

`doc-sync` is a prose skill, so evidence is a clause rather than a code path, and this establishes
that the skill **instructs** the specified behavior rather than that anything enforces it. Same
limit as [`verifier-agent.conformance.md`](verifier-agent.conformance.md).

Unlike the other three skills backfilled by `chore-0025`, `doc-sync` has a recorded real run: its
`feat-0020` dogfood audited 38 documents in this repository, skipped 29 as ledger, produced 12
findings, and modified nothing. Where a row is corroborated by that run, it is noted.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 a current-state document contradicts the code | Conformed | Step 3 / "**Current-state document.** The document is stale. Report the drifted claim, the fact that contradicts it, and the correction that would resolve it", with Step 4 / "A run with no approved findings changes no file" | all five obligations present: document, claim, contradicting fact, proposed correction, and no modification |
| Scenarios | S-002 reporting is the default | Conformed | Step 4 / "Dry run is the default, not a flag", and the output rule / "`mode: dry-run` is the default. An apply invocation with no approved findings makes no edits and reports as a dry run" | "not a flag" is the strong form: the default cannot be lost by omitting an argument. Corroborated by the `feat-0020` dogfood, which modified nothing across 38 documents |
| Scenarios | S-003 corrections reach only the approved findings | Conformed | Step 5 / "Applying requires explicit approval per finding, by id" and "**Edit only current-state documents**, and only those named by approved ids" | the unapproved-findings half is satisfied by the per-id scoping rather than stated separately |
| Scenarios | S-004 a contract document disagrees with the code | Conformed | Step 3 / "The *code* is the suspect, not the document ... Do not edit the document, in either mode, on any authority. This is the rule the skill exists to enforce" | "in either mode, on any authority" closes both loopholes the scenario implies. `proposed_correction` targeting the code is pinned again in the output rules |
| Scenarios | S-005 a ledger document sits inside the scanned path | Conformed | Step 3 / "**Ledger document.** Produce no finding, and list the document in the skipped set with its reason", and Step 1's ledger row | corroborated by the dogfood, which skipped 29 of 38 documents as ledger |
| Scenarios | S-006 the documentation set is clean | Conformed | Step 4 / "Report the audited set positively ... otherwise a clean verdict is indistinguishable from a run that did not look", and the output rule requiring a non-empty `audited` alongside `clean` | the output rule is what makes this mechanical rather than aspirational |
| Scenarios | S-007 a document names something that does not exist | Conformed | Step 3 / `grounded` definition, "A named file, skill, command, or path does not exist; a link resolves to nothing" | corroborated by the dogfood, which surfaced all three dangling references to a `document` skill that never existed in this repository |
| Scenarios | S-008 a claim is stale but the judgment is not mechanical | Conformed | Step 3 / `suspected` definition, "Name the fact, and state the reading under which the claim would still be true, so dismissing it takes one step" | the "reading under which the claim would still be true" clause matches the contract word for word, and is the part that makes one-step dismissal possible |
| Scenarios | S-009 the run is scoped to a change | Conformed | Step 0 / "**Narrow by what a change could have invalidated** when a change scope was supplied", and Step 4 / "Whenever the scope was narrowed ... say so and list what went unread in `not_audited`" | the audited set carries a `scope: full \| change-scoped` field, which is how the narrowing is recorded rather than implied |
| Scenarios | S-010 a document's kind cannot be determined | Conformed | Step 1 / "**An unclassifiable document is treated as a contract.** When you cannot confidently place a document, the fail-safe is report-only. The failure mode must be inaction, never an unauthorized edit" | the fail-safe direction is stated explicitly, which is the whole content of this scenario |
| Scenarios | S-011 an approved correction is written | **Diverged** | Step 5 composes [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) for the edit and states "do not restate its rules here" | **Spec side:** the edit changes only the drifted claim, leaves surrounding text and voice intact, **and every relative link in the edited document still resolves to a file that exists**. **Code side:** the first two obligations are delegated to `doc-revise`, which carries them. The link-resolution obligation is delegated nowhere and stated nowhere. Disposition below |
| Scenarios | S-012 a suspicion cannot be grounded | Conformed | Step 2 / "**A claim you cannot tie to a fact produces no finding at all.** Not a low-confidence finding, not a note: nothing" | the contract's "the report does not mention it" is matched exactly by "nothing", closing the tempting middle option |
| Scenarios | S-013 no report destination is supplied | Conformed | Step 4 / "Return the report inline unless a report destination was supplied", and the surface row for report delivery | |
| Scenarios | S-014 an applied change is auditable afterwards | Conformed | Step 5 / "Each applied entry names the finding id, the document, the claim corrected, the evidence, and the confidence it carried", with "Someone reading it later must be able to tell a mechanical correction from an applied judgment call ... without re-running the audit" | all five fields required by the contract are named, and the `applied` block in the output format carries each |
| Scenarios | S-015 a vendored document is named explicitly | Conformed | Step 1 / "**Vendored third-party material is never edited**, in any mode, even when a user names its path explicitly. Naming it brings it into the audit and no further", and the output rule that `applied` "never contains a contract, ledger, or vendored document" | stated in two places, one of them a mechanical output rule |
| Proposed Surface | Inputs (required): documentation scope, vendored named-but-not-editable | Conformed | "Inputs" section with Step 0's vendored exclusion and Step 1's vendored rule | |
| Proposed Surface | Inputs (optional): change scope, approved findings, report destination | Conformed | "Inputs", Step 0, Step 5, Step 4 respectively | |
| Proposed Surface | `mode`: `dry-run` default, `apply` requires non-empty approved list | Conformed | output rules / "`mode: dry-run` is the default. An apply invocation with no approved findings makes no edits and reports as a dry run" | |
| Proposed Surface | `audited`: every document read, with classification and scope | Conformed | output format `audited` block carrying `document`, `kind`, `scope` | |
| Proposed Surface | `skipped`: every document not audited, with reason | **Diverged** | output format carries **two** fields, `skipped` and `not_audited`, distinguished by an explicit rule | **Spec side:** one field, `skipped`, holding "every document not audited, with the reason (for example ledger history, or a narrowed change scope)". **Code side:** `skipped` means classified and deliberately excluded (a ledger); `not_audited` means nothing is known about it. Disposition below |
| Proposed Surface | `findings`: `id`, `document`, `kind`, `claim`, `evidence`, `confidence`, `proposed_correction` | Conformed | output format `findings` block | all seven fields present with the contract's names |
| Proposed Surface | `proposed_correction` targets document or code by kind | Conformed | output rules and Step 3 | |
| Proposed Surface | `kind`: `current-state`, `contract`, `ledger` | Conformed | Step 1 classification table | the three values match exactly |
| Proposed Surface | `confidence`: `grounded` or `suspected` | Conformed | Step 3 definitions | |
| Proposed Surface | `applied`: five-field audit trail, empty in a dry run | Conformed | output format `applied` block and its rule | |
| Proposed Surface | `verdict`: `clean` when findings empty, else `drift_found` | Conformed | output rules | strengthened beyond the contract: `clean` additionally requires a non-empty `audited` set |
| Proposed Surface | Report delivery: inline by default, file only on request | Conformed | Step 4 | |
| Open Questions | None | Conformed | spec states `None.`, both prior questions resolved into Goal 9 / S-014 and the vendored constraint / S-015 | nothing to reconcile |

## Coverage proof

**Audited** (28 items): scenarios S-001 through S-015 (all fifteen); the twelve Proposed Surface
rows; and the Open Questions section.

**Unreconciled** (2 items):

| Item | Disposition | Reasoning |
|---|---|---|
| S-011: the link-resolution obligation on an applied edit is stated nowhere | **to-fix** | The contract requires that after an applied correction, "every relative link in the edited document still resolves to a file that exists". `doc-sync` delegates the edit to `doc-revise` and correctly refuses to restate its rules, but this obligation is not one of `doc-revise`'s rules, so the delegation drops it. Nothing in either skill instructs the post-edit link check. **This is a real gap, not a wording quibble**: `bug-0011` found 101 broken links in this repository produced by exactly this class of unchecked edit, and `bug-0013` is open against the very checker that would catch it. The cheapest honest repair is one clause in `doc-sync`'s Step 5 requiring a link re-check on each edited document, since the tooling to do it already exists. Reported, not fixed: this lens never repairs. |
| Proposed Surface: one `skipped` field (spec) vs. `skipped` plus `not_audited` (implementation) | **accepted-with-reason** | The implementation splits one contract field into two, which is a divergence in shape but an improvement in truthfulness, and the skill argues the case in its own output rules: `skipped` means the document was classified and deliberately excluded, `not_audited` means nothing is known about it. Collapsing them, as the contract does, makes a document nobody read indistinguishable from a ledger deliberately passed over, which is precisely the "a partial audit read as a whole one" failure that Goal 6 and S-006 exist to prevent. Accepting the code side. **The correct repair is to amend the spec's Proposed Surface to carry both fields**, not to collapse the implementation. Not done here: the spec is `status: approved`, so amending it is a human's call. |

**Not-built**: none. Every scenario and every surface element has evidence.

## Note on what this matrix is worth

Fifteen scenarios produced one real defect (`S-011`) and one contract-lagging-implementation
divergence. That ratio is worth stating because it is the argument for doing these audits at all:
`doc-sync` had shipped, been iterated twice, and been dogfooded on 38 documents, and the missing
link-resolution obligation survived all of it. No test covers it, no validator sees it, and the
dogfood could not have caught it because that run applied nothing.
