---
title: spec-author conformance
spec: docs/spec/spec-author.md
audited: 2026-08-05
revised: 2026-08-05 (chore-0027, the two output-location rows, the new S-006 and S-007 rows, and the coverage proof; the audit itself was not re-run)
---

# spec-author conformance matrix

Spec-vs-implementation audit of [`spec-author`](../../.agents/skills/spec-author/SKILL.md) against
[`spec-author.md`](spec-author.md). Produced by `chore-0025`, which backfilled the four approved
specs that shipped without a matrix. `spec-author` shipped as `feat-0017` on 2026-07-24 and had
never been audited against its own contract.

## What this audit can and cannot establish

`spec-author` is a prose skill, not a program, so both sides are natural language and the evidence
column cites a clause rather than a code path. This establishes that the skill **instructs** the
specified behavior, not that anything **enforces** it. A prose skill can conform perfectly here and
still be ignored by the agent running it. The same limit is recorded in
[`verifier-agent.conformance.md`](verifier-agent.conformance.md) and it applies unchanged.

One scenario, `S-003`, specifies behavior in a **different** skill. It is audited against
[`new-task`](../../.agents/skills/new-task/SKILL.md), which is where the contract places it.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 draft from a raw idea | Conformed | "The spec format" section (the seven sections in fixed order, `status: draft` in the template) and Procedure step 4 | the seven body sections match the contract exactly and in the contract's order; step 4 pins `status: draft` on write. The file *location* half of this scenario is covered by the two output-location rows below, which `chore-0027` closed by amending the contract |
| Scenarios | S-002 self-check with spec-quality | Conformed | Procedure step 3 / "Repeat until the verdict is `ready`. The spec you return is the `ready` version, not the first draft" | the final sentence is what satisfies "the file it writes is the `ready` version", which is the part of S-002 a looser wording would miss |
| Scenarios | S-003 approval gate before decomposition | Conformed | [`new-task`](../../.agents/skills/new-task/SKILL.md) / "Refuse an unapproved spec. If `status` is not `approved`, stop and say so" | audited in `new-task` because that is where the scenario places the behavior. Recorded here as a cross-skill dependency: a future edit to `new-task` can silently break `spec-author`'s contract, and nothing relates the two documents |
| Scenarios | S-004 read-only for implementation surfaces | Conformed | Procedure step 4 / "The run creates or edits **only that spec file**: never an implementation source file, test, or config" | the skill additionally permits updating a spec-directory index (`README.md`). That is a widening of "only that spec file", but the index lives under the spec directory, so it stays inside the scenario's "only file ... is the spec in the repository's spec location" boundary. Called out because the widening is real and a stricter reading would call it a divergence. `chore-0027` re-worded this scenario's location clause and deliberately preserved the boundary's shape, so the reasoning here is unchanged |
| Scenarios | S-005 vague idea triggers one clarifying question | Conformed | Procedure step 1 / "ask the user exactly one clarifying question that would unblock the contract, and write no file until the answer arrives" | both halves are explicit: the count (`exactly one`) and the write barrier |
| Scenarios | S-006 the spec goes where the repository already keeps specs | Conformed | "Where the spec goes" / "Find the repository's spec location before writing, do not assume one ... Match what you find" | added by `chore-0027`, which is why it is `Conformed` on arrival: it states behavior the skill has instructed since it shipped, and which the contract previously contradicted. It exists because pinning the location in `S-001`'s Then made that scenario branch on repository state its Given never set up |
| Scenarios | S-007 a repository with no spec directory gets the documented fallback | Conformed | "Where the spec goes" / "Only when a repository has none of these does `docs/spec/<slug>.md` apply, as this kit's default" | the other half of the location rule, split out by `chore-0027` so each scenario's Given establishes the case its Then asserts. Keeping the fallback as a second clause inside `S-006` reintroduced the same Given/Then mismatch, and dropping it outright would have left the documented default with no scenario exercising it |
| Proposed Surface | Output file: existing spec location, `docs/spec/<slug>.md` as fallback | Conformed | "Where the spec goes" / "Find the repository's spec location before writing, do not assume one ... Only when a repository has none of these does `docs/spec/<slug>.md` apply, as this kit's default", against the amended Proposed Surface row | was **Diverged** when `chore-0025` ran this audit, against a contract that pinned `docs/spec/<slug>.md`. `chore-0027` amended the contract to state discovery with the documented fallback, which is what the skill has always instructed. The two sides now agree |
| Proposed Surface | Frontmatter `status`: `draft` author-set, `approved` human-set only | Conformed | "The spec format" / "**This skill only ever writes `status: draft`.** `approved` is a state a human sets" | stated twice, in the format section and again in step 5 |
| Proposed Surface | Body sections (seven, named) | Conformed | "The spec format" template | present, in order, with "add none others" pinning the set closed |
| Proposed Surface | Scenario ids stable `S-NNN`, never renumbered | Conformed | "The spec format" / "never renumbered or reused", and Notes / "Stable scenario ids are what make that traceability work, so never renumber them" | |
| Goals | 1. Draft a persistent spec with all seven parts | Conformed | Procedure steps 2 and 4 | covered by S-001 |
| Goals | 2. Compose `spec-quality` to reach a `ready` verdict | Conformed | Procedure step 3, and the skill preamble / "composes the `spec-quality` lens ... rather than restating its rules here" | the preamble's "point at the lens, not copying it" is what keeps the two from drifting |
| Goals | 3. Represent an explicit human approval state | Conformed | "The spec format" `status` rule plus step 5's handoff | |
| Constraints | Composes `spec-quality` rather than restating it | Conformed | skill preamble | |
| Constraints | Read-only for implementation surfaces | Conformed | Procedure step 4 | same evidence as S-004 |
| Constraints | `status` is one of `draft` or `approved`; never self-approves | Conformed | "The spec format" | |
| Constraints | Specs go to the repository's existing spec location, `docs/spec/<slug>.md` as fallback | Conformed | see the Proposed Surface row above | same clause, recorded once against each section it appears in so neither reads as unchecked. Amended and closed by `chore-0027` together with that row and `S-001` |
| Non-Goals | Does not decompose into tasks | Conformed | step 5 / "Do not decompose it yourself", and "When not to use" | |
| Non-Goals | Does not write code, tests, or architecture | Conformed | step 4, and step 2's "you have drifted into plan territory" guard | |
| Open Questions | None | Conformed | spec states `None.` | nothing to reconcile |

## Coverage proof

**Audited** (21 items): scenarios S-001 through S-007, two more than the nineteen at the original
audit because `chore-0027` added `S-006` and `S-007`; Proposed Surface rows for output file,
frontmatter `status`, body sections, and scenario ids; Goals 1 to 3; the four Constraints; the two
Non-Goals; and the Open Questions section.

**Unreconciled** (0 items): none. Every audited item is `Conformed`.

**Reconciled since the audit** (1 item):

| Item | Disposition | Reasoning |
|---|---|---|
| Output location: `docs/spec/<slug>.md` (spec) vs. discover-then-default (implementation) | **closed by amending the contract** (`chore-0027`, 2026-08-05) | `chore-0025` recorded this as **accepted-with-reason**: the implementation is deliberately broader than the contract, and the contract was the narrower document because it was written for this repository before the skill was generalised for adopters. Section 5 of `AGENTS.md` requires a skill to work in a repository that is not this one, and a skill that writes `docs/spec/` into a project already using `specs/` produces exactly the second spec directory nobody reads, which the skill body calls out by name. That disposition accepted the code side and named the repair: amend the spec. `chore-0027` did so, changing the Constraints, the Proposed Surface output-file row, and scenarios `S-001` and `S-004`, adding `S-006` and `S-007` to state the location rule and its documented fallback as observable behavior, renumbering nothing, and changing no skill body. The amended spec is still `status: approved` and needs a maintainer's re-approval. |

**Not-built**: none. Every scenario and every surface element has evidence.

## Note on the risk this matrix leaves open

With the output-location divergence closed, the `S-003` row is the more interesting long-term risk,
even though it is `Conformed`. It is the only scenario in this spec whose behavior lives in another
skill's body, so the two can drift with
nothing failing: `new-task` could lose its refusal clause and `spec-author`'s contract would be
quietly broken with no test, no validator, and no matrix row turning red until someone re-runs this
audit by hand. That is the class of gap the hooks module (`feat-0038`, `feat-0039`) exists to close,
and a spec-closeout gate does not reach it.
