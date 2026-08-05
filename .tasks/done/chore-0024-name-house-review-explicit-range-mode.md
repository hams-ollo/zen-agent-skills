---
id: chore-0024
title: Name house-review's bare explicit-range mode in Step 1 and in its approved contract
type: chore
status: done
priority: P1
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
spec: docs/spec/house-review.md
scenarios: ["S-013"]
touched_files:
  - .agents/skills/house-review/SKILL.md
  - docs/spec/house-review.md
  - docs/spec/house-review.verification.md
created: 2026-08-03
---

## Problem

Reviewing a single historical commit is a real invocation of
[`house-review`](../../.agents/skills/house-review/SKILL.md), and the skill documents no mode that
produces it. Worse than an omission: the skill body already relies on that mode existing, one line
below the sentence that says there are only two.

**The skill body contradicts itself inside one step.** Step 1 is headed "pick what to review" and
opens with "There are two modes. Decide which the request is." It then names an explicit path scope
and a change review computed as branch against merge-base with a working-tree fallback. Nine lines
later, still inside Step 1, it says:

    **A path scope with an explicit base or range is a narrowed change review, not a full-file one.**

That sentence presumes an explicit range is a thing the skill accepts, which the two enumerated modes
never establish. An agent that reads the step in order is told the request is one of two things, then
told what to do when it is a third.

**The approved contract has the same gap, in a sharper form.**
[`docs/spec/house-review.md`](../../docs/spec/house-review.md) carries `status: approved`, and its
Proposed Surface disagrees with itself across three consecutive rows:

| Row | What it says today | Consistent? |
|---|---|---|
| Invocation | "A request to review, optionally naming a path scope, a base, or a commit range" | Permits a bare range |
| Modes | path scope, change review, or "a path scope plus a range" | No bare-range mode |
| Range resolution | "Merge-base with the default branch, then working tree, then nothing to review" | No explicit-range branch |

So the contract admits an input at Invocation that neither of the next two rows can account for. The
Scenarios have the matching hole: `S-001` covers a path scope, `S-012` covers a range **alongside** a
path scope, and `S-002` through `S-004` cover the no-scope resolution chain. **Nothing covers a bare
range with no path scope**, which is exactly the single-historical-commit case.

**This is now half of a live seam.** `review-depth` (Epic B #10, in flight on another branch when this
task was authored, merged into the same branch on 2026-08-03) has an `explicit range` input and a
`changeset_source: resolved | supplied` output field for precisely this distinction, and its Inputs
section recorded the `house-review` inconsistency as filed rather than resolved there until the merge
discharged it. `review-depth` hands a supplied range across to `house-review`; `house-review` has no
documented mode to receive it. The two halves of one handoff disagree.

Found by dogfooding the `review-depth` draft (`feat-0035`, finding 1), and re-verified against the
files on 2026-08-03 rather than taken on report. An earlier reading of the same finding placed the
presuming sentence in Step 2; that was wrong, and the corrected location makes the finding sharper,
because a contradiction inside one step is worse than a gap between two.

## Scope

**In scope:**

1. Amend [`docs/spec/house-review.md`](../../docs/spec/house-review.md): give Modes a bare
   explicit-range entry, give Range resolution an explicit-range branch that wins over the merge-base
   default, add one scenario for a bare range with no path scope, and record the amendment and
   re-approval inline and dated.
2. Fix `house-review` Step 1 so it names all three modes coherently, and state how an explicit range
   interacts with the merge-base default.
3. Whatever the new scenario forces elsewhere in the same file to avoid introducing a second
   contradiction while fixing the first. `S-002`, `S-003`, and `S-004` each open on "a request naming
   no scope", which a bare range satisfies, so `S-013` added on its own would fire simultaneously with
   `S-002` and prescribe a different outcome. Tightening those three preconditions to "neither a path
   scope nor a range" is in scope; it states what they meant before a bare range was contemplated and
   changes no behavior they describe.

**Out of scope:**

- **[`.agents/skills/review-depth/SKILL.md`](../../.agents/skills/review-depth/SKILL.md).** Was mid-flight
  on another branch while this task was authored, so it did not exist here and was named in prose
  rather than linked; the two branches were merged on 2026-08-03 and it is now present and linked.
  Match its vocabulary; do not edit it. Anything that would need changing there is reported as a
  finding below, not fixed.
- **[`.agents/skills/pr-describe/SKILL.md`](../../.agents/skills/pr-describe/SKILL.md).** Checked and
  clean: its Step 1 already honours "any explicit base/range the user gave" (line 51) and its Design
  choices already name the override (line 36). It is the model to match, not a file to change.
- Changing what any mode *does*. This is a contract and a skill body catching up to an input both
  already half-admit, not new behavior. In particular, `S-012`'s resolution (a range plus a path
  scope narrows a change review) stands exactly as `chore-0012` recorded it.
- Both rules modules, [`house-style.md`](../../.agents/rules/house-style.md) and
  [`review-quality.md`](../../.agents/rules/review-quality.md). Nothing here touches the rubric, the
  severities, or the house conventions.
- Any other `docs/spec/` contract. The gap is specific to this one.
- **The skill's frontmatter `description`.** It says the skill "determines the review range (the
  current branch against its merge-base with the default branch, with a working-tree fallback)", which
  describes the default and stays true as the default. Editing it would move `install.py`'s description
  budget, and the S-014 row of [`docs/spec/install.conformance.md`](../../docs/spec/install.conformance.md)
  records those figures as dated evidence, so a body fix should not silently invalidate them. Confirm
  after the change that the budget still reads `core=2298, spine=12489, all=14273`.

## Implementation notes

**The amendment is authorised, and the authorisation is the load-bearing part.** The author gave
explicit instruction to amend and re-approve on 2026-08-03. This repository's precedent is that an
approved contract is amended only on explicit author instruction, and that the amendment is recorded
inline with its date. Follow the shape at [`docs/spec/install.md`](../../docs/spec/install.md) line 13,
which `feat-0033` wrote: a bold dated line naming the task, the instruction, and the re-approval, then
a sentence on what moved and why.

**Frame it as repairing an internal inconsistency, not as expanding scope**, because that is what it
is. The Invocation row already permits a bare commit range. Modes and Range resolution are incomplete
relative to a row the same table already carries, so the amendment closes a self-contradiction rather
than adding a capability the contract never contemplated. That distinction is why this does not need a
fresh `spec-author` pass and a new approval cycle.

**Scenario id: use `S-013`.** `S-012` is the highest in the file today. Verify that before writing it;
ids are stable and never reused.

**Match `review-depth`'s vocabulary exactly, since this is the other half of its seam.** Its Inputs
section says an explicit range "wins over the resolved default, and it is reported as supplied rather
than resolved, because which one produced the changeset is not recoverable from the range itself", and
its output block carries `changeset_source: resolved | supplied`. So `house-review` Step 1 should say
the explicit range **wins** and is **reported as supplied rather than resolved**, in those words. Two
skills each inventing their own phrasing for one distinction is how the seam drifts.

**Do not restate `pr-describe`'s changeset logic; keep reusing it by reference.** Step 1 already says
it reuses that logic, and the contract's Constraints require the two skills to resolve to the same
range in the same repository state. The explicit-range branch is an override on that shared
resolution, so it belongs as a step above the merge-base computation, not as a fourth parallel mode
with its own procedure.

**Link discipline.** A relative link in a skill body must not escape the `.agents/` tree;
`validate-skills.py` fails on this and it is the check that caught the kit's worst shipping defect. If
Step 1 needs to name the contract, name it in prose rather than linking to it.

**[`docs/spec/house-review.verification.md`](../../docs/spec/house-review.verification.md) is expected to
need no change, but read it before concluding that.** It records a `blocked` verifier-agent run from
2026-07-27 whose entire subject is the approval precondition (the spec carried `status: draft` that
day), plus two observations about precondition ordering. It asserts nothing about Modes, Range
resolution, or the scenario set, so this amendment falsifies none of its claims. It is a ledger of a
past run, so if something in it does turn out to be affected, date or re-anchor it per the
`chore-0005` precedent rather than rewriting it, and never overwrite a figure that is already dated.

**No conformance matrix exists for this spec**, so there is no `house-review.conformance.md` row to
regenerate. Confirmed by listing `docs/spec/`: this contract has a verification record only. Do not
create one as a side effect; `house-review` is a prose procedure with no code to audit, and the
verification record already explains why exercising a skill branch means something weaker than
exercising a branch of a program.

**Cross-branch id collisions were live when this was authored.** `bug-0011` was on an open pull
request and `feat-0036` on another branch, so neither was free despite what `.tasks/.scaffold.json`
showed locally. `chore` high water was 23, hence `chore-0024`. Both have since landed, and the
counters were reconciled to the union `{bug: 12, feat: 37, chore: 24}` on 2026-08-03.

**This file's relative links resolve from `.tasks/`.** They break on the move to `.tasks/done/`, and
an open PR adds a validator check for exactly that, so expect the closeout to require re-anchoring
every `../` link to `../../`.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" && python scripts/build-adapters.py --dry-run && python scripts/install.py --dry-run --home ./.tmp/zen-home

- [x] `house-review` Step 1 names three modes, and the sentence about a path scope with an explicit
      base or range is no longer an orphan presumption.
- [x] Step 1 states that an explicit range wins over the merge-base default and is reported as
      supplied rather than resolved, in vocabulary matching `review-depth`'s `changeset_source` field.
- [x] The contract's Modes row carries a bare explicit-range entry and its Range resolution row
      carries an explicit-range branch, so both are consistent with the Invocation row.
- [x] One new scenario covers a bare range with no path scope, at a previously unused id (`S-013`).
- [x] The amendment and its re-approval are recorded inline in the spec, dated, following the
      `feat-0033` shape.
- [x] `S-002`, `S-003`, and `S-004` no longer fire on a bare range, so `S-013` does not contradict
      them.
- [x] `docs/spec/house-review.verification.md` is read, and either left unchanged with the reason
      stated or re-anchored rather than rewritten. **Left unchanged**: every claim in it concerns the
      2026-07-27 approval precondition and the precondition ordering that `chore-0014` resolved, and
      none concerns Modes, Range resolution, or the scenario set.
- [x] Both files in `.agents/rules/` are byte-identical to `HEAD`, and no file under
      `.agents/skills/review-depth/` is created or changed.
- [x] No em-dash appears in any file touched.
- [x] `house-review/SKILL.md` stays under the 500-line guideline.
- [x] `.tasks/.scaffold.json` `id_high_water.chore` is 24.

## Definition of done

- [x] Acceptance command(s) pass locally. **Run 2026-08-05**: validate-skills 20/0/0, validate.py --strict, 140 tests, build-adapters --dry-run, install --dry-run. All pass.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents. **2026-08-05: no finding.** The only reader-facing mention of `house-review` is `docs/GETTING-STARTED.md:372`, which describes it as report-only and says nothing about modes or range resolution, so this amendment leaves it true. The contract and its matrix are ledger and contract kinds, not current-state. Original text:
      `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Findings handed back, since discharged

1. **`review-depth`'s Inputs section needed one sentence re-anchored once both branches landed.** It
   said the `house-review` inconsistency "is filed against `house-review` and is not resolved here",
   which stopped being true the moment this task landed. It was not fixed from this branch, where
   `review-depth` was mid-flight elsewhere and editing it would have collided; it was handed to
   whoever reconciled the two. **Discharged on 2026-08-03 in the merge that joined them**, which is
   the only point at which the sentence could be made true. It now records that `house-review` names
   this as one of its three modes and reports the same `supplied` and `resolved` values, so the
   vocabulary is shared rather than parallel.
