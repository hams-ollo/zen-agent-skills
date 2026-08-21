---
id: chore-0050
title: new-task's Step 7 is phrased to route around a reference that has since been fixed
type: chore
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0039]
touched_files:
  - .agents/skills/new-task/SKILL.md
created: 2026-08-20
---

## Problem

[`bug-0039`](bug-0039-readme-spine-diagram-gates-the-decomposition-before-it-exists.md) corrected
the README spine diagram, which had run `spec-plan-readiness` before `new-task` even though that gate
takes a spec **and its task decomposition** as input. `new-task`'s Step 7 was written while the
diagram was wrong, and is phrased negatively to route around it.

`bug-0039` reported that the step can now be stated positively, and
[`chore-0048`](chore-0048-two-spine-edges-are-asserted-by-only-one-of-the-two-skills.md)
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

## Decisions

**The negative construction spanned two sentences, and both were rewritten.** The scope says one
sentence, and the named one ("the next step is not `fix-batch`") was the obvious half. The sentence
after it carried the same routing-around in "it runs before dispatch, not after", which was emphasis
against the old README order rather than content of its own. Leaving it would have restated the
defect in the next line, so it became "dispatch waits on its verdict". No third sentence was touched.

**The gate's input is now the reason for the ordering, not a bare assertion.** The positive sentence
says `spec-plan-readiness` takes the spec and its task decomposition together, so it runs on the set
this skill just wrote. That is the same fact `bug-0039` used to correct the README diagram, taken
from `spec-plan-readiness`'s own description and its Intent line, rather than a restatement of the
chain, which `chore-0040` reserves to each skill's own neighbours.

**The sibling link was kept exactly as found, deliberately.** Step 7 already linked
`../spec-plan-readiness/SKILL.md` and the rewrite keeps that one link, so the profile edge is
unchanged. Membership resolved through `install.py`'s own `partition_drafts` and `resolve_profile`
before and after: `core` 3, `spine` 18, `all` 20, with identical member lists in all three.

**No false premise found.** Step 7 still carried the negative phrasing at dispatch time, exactly as
`chore-0048` reported on 2026-08-20.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] Step 7 states what it does rather than what it is not, and names the gate's real input.
- [x] No other skill body is modified, and the README is untouched.
- [x] Profile membership is unchanged, or the change is stated and deliberate, checked against
      `bug-0038`'s assertions rather than assumed.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
