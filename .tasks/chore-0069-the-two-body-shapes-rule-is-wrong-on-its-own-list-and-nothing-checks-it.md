---
id: chore-0069
title: The two-body-shapes rule names three lenses and is right about one, and validate-skills.py has no shape check at all
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - AGENTS.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-27
---

## Problem

`AGENTS.md` section 4, "Two body shapes, both valid", states a contract-level rule about how every skill
in this kit is built:

> **Lenses** carry `Intent`, `Workflow`, and `Output format` instead, because they are composed into
> another skill rather than run on their own. `spec-quality`, `test-quality`, and the `review-quality`
> rules module are lenses.

Measured 2026-08-27 against the actual top-level headings:

| Named a lens | Actual `##` headings | |
|---|---|---|
| `spec-quality` | Intent, When to use, Inputs, Non-goals, Workflow, Output format | conforms |
| `test-quality` | Goal, Decide before writing, Core rules, Layer selection, Trust-boundary focus | **does not** |
| `review-quality.md` | Severity scheme, Rubric categories, Evidence shape, The evidence gate | **does not** |

**And it fails in the other direction.** Two skills the rule does not name are shaped exactly as it
prescribes, and both are called lenses in other skill bodies:
[`spec-conformance`](../.agents/skills/spec-conformance/SKILL.md) (Intent, When to use, Inputs, Workflow,
Output, Non-goals) and
[`spec-plan-readiness`](../.agents/skills/spec-plan-readiness/SKILL.md) (Intent, Inputs, Non-goals,
Workflow, Output format, Readiness checklist).

So the rule is **one for three** on its own list, with two unlisted skills following it.

**Nothing has ever checked this.** `grep -ciE "intent|output format|body shape" scripts/validate-skills.py`
returns `0`. The one rule in this repository that governs the internal structure of every deliverable it
ships has no gate, which is why it could be wrong for months in the file every agent reads in full.

**The consequence is stated by the rule itself**, which is what makes this a defect rather than
bookkeeping: "Giving a lens a step-by-step procedure invites an agent to run it standalone, which is the
one thing it is not for." `test-quality` is composed by
[`test-author`](../.agents/skills/test-author/SKILL.md), is named a lens in three skill bodies, and is
shaped like something you run.

## Scope

**In scope:** make the rule true, and give it a check.

- **Correct the list in both directions.** Two questions have to be answered rather than assumed, and
  each has a defensible answer either way:
  - **Is `test-quality` reshaped, or reclassified?** Reshaping changes a skill that works; reclassifying
    admits the kit has a third thing that is neither a workflow nor a lens. Decide and record the
    rejected alternative.
  - **Does the rule apply to `review-quality.md` at all?** Section 4 opens "Each skill is a directory
    under `.agents/skills/<name>/`", and that file is a rules module at `.agents/rules/`. Naming it inside
    a skill-shape section may be a **scope error in the sentence** rather than a conformance failure in
    the file. Work that out from the section's own framing rather than forcing the module into a shape
    written for skills.
- **A shape check in `validate-skills.py`**, with the trap below solved rather than stepped in.
- Consider writing the undocumented pattern into the rule while it is open: the four lens-shaped or
  lens-named skills carry the four shortest descriptions in the kit (`spec-quality` 370, `test-quality`
  467, `spec-plan-readiness` 524, `spec-conformance` 542). A skill meant to be composed rather than
  triggered should be quiet in the trigger surface. That is a real principle operating with nothing
  stating it. **Adding it is optional; if it is added it needs its own evidence, not this sentence.**

**Out of scope:**

- **The progressive-disclosure question**, which is
  [`chore-0070`](chore-0070-adopt-the-published-disclosure-convention-and-decide-its-enforcement-level.md).
  **That task touches the same three files as this one, so the two cannot share a wave.**
- Reshaping any skill other than `test-quality`, and reshaping even that one only if this task decides to.
- The description ceiling and its headroom. Related surface, different question, not filed.
- `.agents/rules/house-style.md` and `.agents/rules/autonomy.md`. Whatever is decided about
  `review-quality.md` applies to the module class, but this task changes no lens content.

## Implementation notes

**The trap, and it is the whole design problem: a shape check that infers the intended shape from the
headings cannot fail.** If "has Intent and Workflow and Output format" is what makes a skill a lens, then
every skill conforms by construction and the check is theatre. That is precisely the pattern `chore-0063`
wrote into `AGENTS.md` on 2026-08-27: a check that cannot fail is unchecked, whatever it printed. The
checker needs a **declared** intent to compare the shape against.

Two candidate sources, neither obviously right:

- **A `metadata` key.** `ALLOWED_FRONTMATTER_KEYS` already permits `metadata`, so a marker there needs no
  widening of the schema, and `AGENTS.md`'s provenance section explicitly names `metadata` as the place
  for something that must not become a seventh key. Cost: every lens needs the marker, and a skill that
  forgets it is silently a workflow.
- **The composition graph.** A lens is defined by being composed rather than run, and this repository
  already models that: `check_lenses_are_composed` asks whether some skill names a rules file, and
  `SIBLING_REF_RE` in [`install.py`](../scripts/install.py) treats a sibling link as a profile edge. A
  skill that only ever appears as somebody else's reference is a lens by the rule's own definition. Cost:
  it infers intent from usage, so a lens nothing composes yet is invisible, which is exactly the state
  `autonomy.md` was in for ten days.

Prior art for the check's shape: `check_status_contradiction` in `validate-skills.py` is the closest
existing thing, a body-content rule expressed as a warning over parsed text.

## Risks and rollback

Three files including the canonical rules document, so this section is required.

**The first risk is the tautology above.** Guard it by writing a test that constructs a skill declared one
shape and built as the other, and asserting the run reports it. If that test is hard to write, the check
is inferring rather than checking.

The second risk is a check that fails the tree on landing. Two of five candidate lenses do not conform
today. Decide whether the check is an error or a warning **after** measuring how many skills it would fail,
and state both numbers.

The third is scope creep into reshaping skills. The rule being wrong is not evidence that the skills are.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `AGENTS.md`'s lens list names every skill that is one and no skill that is not, checked against the
      headings rather than against the previous list.
- [ ] The `test-quality` decision is recorded with its rejected alternative.
- [ ] The `review-quality.md` question is answered explicitly, including whether the shape rule reaches a
      rules module at all.
- [ ] `validate-skills.py` reports a skill whose declared shape and actual shape disagree, proven by a test
      that constructs exactly that disagreement and fails against the current code.
- [ ] The closeout states how the checker learns a skill's intended shape, and why the alternative source
      was rejected.
- [ ] The closeout states, as a number, how many skills the check reports on the tree as it stands.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
