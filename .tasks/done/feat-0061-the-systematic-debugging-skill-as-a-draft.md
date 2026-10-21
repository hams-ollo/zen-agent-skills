---
id: feat-0061
title: Build the systematic-debugging skill against its contract, shipped as a draft
type: feat
status: done
priority: P1
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: [chore-0078]
spec: docs/spec/systematic-debugging.md
scenarios: [S-001, S-002, S-003, S-004, S-005, S-006, S-007, S-008, S-009, S-010, S-011, S-012, S-013, S-014, S-015]
# Directories where this task creates files, exact paths where they already exist. The
# backlog gate runs `--strict`, so a path declared before it exists is an error; the
# precedent is `feat-0056` and `feat-0060`, which both created files this way.
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/
  - .agents/hooks/skill-reachability-reminder.py
created: 2026-08-29
---

## Problem

The kit bootstraps, specs, decomposes, dispatches, tests, verifies, reviews, reconciles and
documents, and has no skill for working out **why** something is broken. The 2026-08-18 review pass
called this the largest single hole in the workflow, and the reason it matters is upstream of every
other skill: today a defect report becomes a task file with no step in between that establishes the
cause, so `new-task` writes a premise that nobody checked and `fix-batch` dispatches an agent to
implement it.

That failure is not hypothetical here. `new-task`'s own skill body records two occasions where a task
file asserted something false about the code and the implementing agent had to catch it mid-batch.

[`systematic-debugging.md`](../../docs/spec/systematic-debugging.md) is the contract, approved
2026-08-19 and amended 2026-08-29 by `chore-0078`, fifteen scenarios. Nothing implements it.

## Scope

**In scope:** the skill, covering all fifteen scenarios, shipped as a draft.

- `.agents/skills/systematic-debugging/SKILL.md`, a workflow-shaped skill implementing the contract's
  three verdicts, its diagnosis record, and its four inputs.
- **Shipped as a draft.** `metadata: status: draft` in the block form `install.py` parses, so no
  profile places it, including `all`. Mirror
  [`agent-observatory`](../../.agents/skills/agent-observatory/SKILL.md), which is the kit's only other
  draft and the precedent for this exact shape.
- Structural tests in `tests/test_systematic_debugging.py`, one per scenario, named so the scenario
  is identifiable.
- The conformance matrix at `docs/spec/systematic-debugging.conformance.md`, with the coverage-proof
  arithmetic stated rather than asserted. The spec README already records this as "conformance owed
  at closeout" and this is that closeout.
- **The fold-in and its provenance.** ROADMAP Epic C #5 directs this to be folded in from the
  four-phase `systematic-debugging` skill in Jesse Vincent's `superpowers`
  (`github.com/obra/superpowers`, MIT) rather than written from scratch, under the provenance
  convention in `AGENTS.md`. Record the block with a re-fetchable raw URL and a sha256 of the
  retrieved bytes.
- The reachability hook's `KIT_SKILL_NAMES`, which diverges the moment a skill is added and whose own
  comment instructs an author to edit it.

**Out of scope:**

- **Fixing anything the skill diagnoses.** The contract's `S-005` refuses repair, and so does this
  task: a defect this work uncovers is a finding to report, not a diff to slip in.
- Promoting the skill out of draft. That is `feat-0062`, and the kit's contribution bar in
  `AGENTS.md` is that no skill ships cold.
- `feat-0042`, which consumes this contract's verdict vocabulary. It stays open and its dependency is
  retargeted to this task.
- Any second vocabulary for classifying a run's outcome. The three verdicts here are the kit's single
  classification vocabulary by decision of the 2026-08-18 review.

## Implementation notes

**The tests are structural over prose, and that is a real bound rather than an oversight.** A skill
body is instructions to a model, so a test can assert the declining instruction is present and cannot
assert a model obeyed it. `feat-0060` hit exactly this on `S-020` and stated it up front rather than
letting a verifier discover it; do the same. The precedent to mirror is
`TestTheCompanionSkillDeclines` in [`tests/test_observatory_serve.py`](../../tests/test_observatory_serve.py),
whose docstring states the bound in the class it applies to.

What a structural test can still decide, and should:

- The verdict vocabulary is **exactly** the three the contract names, with no fourth and none missing.
  A test that only checks the three are present passes against a skill that also invented a fourth.
- Every field in the record table appears, and each is stated with the condition the contract gives
  for when it is present. `implicated_files` and `regression_observable` being **absent** on `S-010`
  is as much a requirement as their presence on `S-006`.
- The instruction `S-005` turns on is present in the imperative, not merely the word "fix" somewhere
  in the body. **Assert on a form, not a bare phrase.** This kit has three recorded occasions where an
  assertion matching a bare word in source text was satisfied by a comment, broken by a comment, and
  once satisfied by the comment explaining the very fix. Strip prose before matching, or assert on a
  construct.

`S-009` and `S-013` are about the record's persistence and are the two most likely to be written as
intentions. `S-013` in particular has a checkable pair: no destination means no file created, a
destination means the same record written there.

`S-014` and `S-015` arrived from `chore-0078` and are the settled answer to Open Question 1. What a
structural test can decide about them: that `S-014`'s bound is **at no point during the run** rather
than at its end, since the whole reason instrument-in-place-then-clean-up was rejected is that it
satisfies the weaker phrasing on every run that completes; and that `S-015`'s no-copy path is
present as a stated behavior rather than as an omission, because a skill body that simply never
mentions the case reads exactly like one that handles it.

`validate-skills.py` enforces the schema, the description budget, and the link-escape rule, so no
link in the skill body may point outside the skill tree. The contract, which lives in `docs/spec/`,
therefore has to be named in prose rather than linked. `agent-observatory` does this and is the
example to copy.

## Risks and rollback

Touches three areas that fail differently: the skill tree, the test suite, and the documentation set,
plus a hook whose divergence breaks a gate rather than a test.

- **Adding a skill moves figures other things assert on.** `install.discover_skills()` returns every
  directory holding a `SKILL.md`, drafts included, so the roster goes 21 to 22 and the never-invoked
  count moves with it. `docs/OBSERVATORY.md` names both. `feat-0060` hit this and it broke two gates
  that wanted opposite fixes; expect it rather than debug it.
- **The description budget is per profile and a draft is placed by no profile.** `install.py` prints
  the budget over the shipped set on purpose. A test computing its expectation over every discovered
  skill is wrong in the way `feat-0060` found and corrected.
- Reversible by reverting one commit. Nothing here is persisted, generated, or written outside the
  repository, and the skill reaches no adopter tree while it is a draft.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test per scenario, `S-001` through `S-015`, named so the scenario it proves is identifiable.
- [x] The three verdicts are asserted as an exact set, so a fourth fails.
- [x] Every record field is asserted with its presence condition, including the two the contract
      requires to be **absent** on `S-010`.
- [x] `install.py --dry-run` proves the skill is placed by no profile, including `all`.
- [x] `validate-skills.py` passes, including the link-escape rule.
- [x] A provenance block records the fold-in source with a re-fetchable raw URL and a sha256 of the
      retrieved bytes, and `check-provenance.py` reports it.
- [x] `docs/spec/systematic-debugging.conformance.md` exists with the coverage arithmetic stated:
      conformed + diverged + not-built = 15.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Closeout, 2026-08-29

Acceptance run: `python scripts/run-checks.py`. Result, verbatim tail: `8 passed, 0 failed, 0 could
not run.` 914 tests, 22 skills, 191 task files.

The skill is [`systematic-debugging`](../../.agents/skills/systematic-debugging/SKILL.md), 310 lines,
shipped as a draft. Its contract carries fifteen scenarios rather than thirteen: `chore-0078` settled
both Open Questions on 2026-08-29 before this task started, which is why the frontmatter and two
acceptance criteria here read 15.

### What the independent verification changed

Recorded in full at
[`systematic-debugging.verification.md`](../../docs/spec/systematic-debugging.verification.md).
Verdict `pass`, with five findings, and **all five were reproduced here against the real tree before
being accepted**, on copies with the tracked file never edited. A sixth turned up while reproducing
them.

The finding behind the findings is one shape rather than five defects. **Every mutation this task's
author designed was a deletion or a replacement of asserted text, and a presence assertion cannot see
an addition that contradicts it.** An escape hatch appended to Procedure step 3, permitting in-place
instrumentation with a restore before exit, left every asserted sentence intact and passed all 31
tests, which is exactly the alternative `chore-0078` rejected. So did a fourth verdict instructed in
Procedure step 6 while the `## Verdicts` table stayed correct. Four new assertions close the class;
the suite went 31 to 35 tests, and all twenty mutations now fail it.

**The per-sentence exclusion is the part worth carrying forward.** Forbidding the word "restore" in
that section is the obvious fix and is wrong: the section legitimately uses "cleaning up afterwards"
in the sentence that rejects it, so a bare-word check would have been broken by the prose explaining
the rule. That is this kit's fourth recorded instance of an assertion matching a bare word in source
text. The assertion pairs a permission or an undo with a mention of the tracked files inside one
sentence, which the rejecting prose never produces.

### Two things the audit changed rather than recorded

**The skill gained two `When not to use` bullets.** Auditing the contract's Non-Goals found the skill
covered five of seven and was silent on two: that it does not diagnose the agent's own reasoning
failures, and that it does not decide whether a defect is worth fixing. Silence there is not neutral,
because that section is what a reader checks before invoking a skill.

**A reference to the autonomy lens was written and then removed.**
`test_autonomy_is_composed_by_exactly_the_five_skills_it_cites` pins a bidirectional invariant: a
skill references the lens if and only if the lens cites one of that skill's rules. Adding a sixth
reference without the lens citing back is what that test forbids, and amending the lens would breach
its own evidence gate, since nothing here has run unattended yet. The Notes bullet states the
principle in the skill's own words instead.

### Disclosed work beyond the files this task named

- **`tests/test_check_provenance.py`**, two pinned counts moved from 8 records across 7 files to 9
  across 8, and one test renamed to match. Both new numbers were recomputed from `cp.collect()`
  rather than incremented, and the verification recomputed them again independently. No assertion was
  weakened: both counts stay pinned in both directions and `assertEqual(unreadable, [])` is untouched.
- **`docs/spec/README.md`**, listed here because this task's `doc-sync` step initially missed it and
  the verification caught it. The index still said this matrix did not exist. Recomputing its
  arithmetic then falsified a figure the finding itself had accepted: the standing claim that
  `install`'s matrix "covers 15 of its 18 scenarios" does not survive a check, since that matrix cites
  17 of the 18 scenario ids. The derived count of classified scenarios is now **not stated** rather
  than restated at a new wrong value, with the reason written where the number was. `chore-0075` stays
  open and this is the second figure it would have caught.
- **`.tasks/.scaffold.json`**, chore high-water mark 78 to 79.

### Findings

**One, filed rather than fixed.** `docs/CATALOG.md` has no slot for a skill that is built but not
blessed, and two skills are now in that state: `agent-observatory` and this one. Its opening states a
binary, shipped or planned, and neither is true of a draft. Inventing a third status in a
reader-facing document is a documentation decision rather than a knock-on of adding a skill, so it is
[`chore-0079`](chore-0079-the-catalog-has-no-slot-for-a-skill-that-is-built-but-not-blessed.md)
rather than an edit made here.

### What is still owed

Everything the tests cannot decide. They assert the body contains an instruction; they cannot assert
a model followed one. `feat-0062` runs the skill on a real defect, which is the only thing that
closes it, and until then the skill stays a draft placed by no profile. That is the contribution bar
working rather than caution.
