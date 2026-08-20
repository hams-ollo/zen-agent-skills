---
id: chore-0050
title: new-task's Step 7 is phrased to route around a reference that has since been fixed
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0039]
touched_files:
  - .agents/skills/new-task/SKILL.md
created: 2026-08-20
---

## Problem

[`bug-0039`](done/bug-0039-readme-spine-diagram-gates-the-decomposition-before-it-exists.md) corrected
the README spine diagram, which had run `spec-plan-readiness` before `new-task` even though that gate
takes a spec **and its task decomposition** as input. `new-task`'s Step 7 was written while the
diagram was wrong, and is phrased negatively to route around it.

`bug-0039` reported that the step can now be stated positively, and
[`chore-0048`](done/chore-0048-two-spine-edges-are-asserted-by-only-one-of-the-two-skills.md)
confirmed on 2026-08-20 that the phrasing is still there. Neither task owned it: `bug-0039` was scoped
to the README, and `chore-0048` names it in its own out-of-scope list as real, separate, and one
sentence.

This is the smallest item in the backlog, and it is filed rather than done in passing for one reason.
A skill body is a deliverable of this kit, so an edit to one is a change to the product, and a
sentence rewritten opportunistically inside an unrelated task is exactly the undisclosed extra that
the autonomy module's `A2` is about.

## Scope

**In scope:** restate Step 7 positively, now that the reference it routed around is correct.

- One sentence, in the skill's own voice.
- Check the surrounding steps still read in sequence afterwards, since a negative phrasing sometimes
  carries a transition that the positive one drops.

**Out of scope:**

- The rest of `new-task`, and every other skill body.
- The README diagram, corrected by `bug-0039` and the reference here.
- Any change to the spine ordering itself. This describes the corrected order; it does not revisit it.
- Adding or removing a relative link to a sibling `SKILL.md`, which is a profile edge in `install.py`
  per `bug-0038`. If the rewrite wants one, that is a decision to state, and `chore-0048` measured what
  such a link can cost.

## Implementation notes

Read the corrected README section and `spec-plan-readiness`'s own description before rewriting, so the
positive statement describes what the gate actually takes as input rather than restating the chain.
`chore-0040` established that each skill names only its own neighbours, and this sentence stays inside
that invariant.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Step 7 states what it does rather than what it is not, and names the gate's real input.
- [ ] No other skill body is modified, and the README is untouched.
- [ ] Profile membership is unchanged, or the change is stated and deliberate, checked against
      `bug-0038`'s assertions rather than assumed.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
