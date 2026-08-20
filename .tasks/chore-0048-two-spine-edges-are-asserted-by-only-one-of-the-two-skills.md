---
id: chore-0048
title: Two spine edges are asserted by only one of the two skills they connect, which is the condition that let a wrong edge survive a correction pass
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0039]
touched_files:
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-08-20
---

## Problem

[`bug-0039`](done/bug-0039-readme-spine-diagram-gates-the-decomposition-before-it-exists.md) re-derived all
eleven edges of the README spine diagram against the skills they connect. Nine are asserted by both
skills. Two are asserted by one:

```text
init-worktracking -> spec-author       grep -c 'spec-author' init-worktracking/SKILL.md  ->  0
reconcile-worktrees -> doc-sync        grep -c 'doc-sync'  reconcile-worktrees/SKILL.md  ->  0
```

Both edges are carried entirely by the other end: `project-bootstrap`'s Notes for the first,
`pr-describe`'s Notes for the second. Neither is wrong. Both are unverifiable from the skill a reader
would be holding when they need them.

**This is the condition that let a wrong edge survive a correction pass, which is the argument for
fixing it rather than noting it.** `chore-0040` was dispatched on 2026-08-19 specifically to make the
spine statements agree, and it checked each statement against the README diagram. That method cannot
catch a one-sided edge, because there is nothing on the other side to disagree with. The edge
`bug-0039` found genuinely wrong, `spec-plan-readiness` before `new-task`, was caught only because
both skills asserted it and both contradicted the diagram. Where only one skill speaks, a wrong
diagram and a silent skill agree by default.

It also falsifies a claim `project-bootstrap` makes about the kit. Its Notes state the invariant that
every skill along the spine names just its own neighbours, which is the design `chore-0040` adopted
deliberately, because a full chain restated in four places is what drifted in the first place. Two
skills do not hold up their end of it.

## Scope

**In scope:** give each of the two skills the neighbour statement its counterpart already has.

- `init-worktracking` names `spec-author` as the contract-driven path out of it. Its Step 8 currently
  offers `new-task` and mentions no spec, which is correct for the non-contract path and incomplete
  for the other.
- `reconcile-worktrees` names `doc-sync` as what follows it.
- Both in the immediate-neighbour form `chore-0040` established, not a restated chain.

**Out of scope:**

- The nine two-sided edges, which are correct and asserted from both ends.
- The README diagram, corrected by `bug-0039` and the reference here.
- Adding a spine statement to any skill that has no place in the chain. This closes two gaps in an
  existing invariant; it does not extend the invariant to skills it never covered.
- `new-task`'s Step 7 phrasing, which `bug-0039` reported can now be stated positively since the
  reference it was written to route around is fixed. Real, separate, and one sentence.

## Implementation notes

Write each statement from the skill's own point of view, naming what it hands to and what hands to
it, rather than copying the counterpart's sentence. The counterpart's phrasing is written from the
other direction and reads oddly transplanted.

`init-worktracking` is the harder of the two, because it has two legitimate downstreams. A repository
that adopts the spec spine goes to `spec-author`; one that does not goes to `new-task`. Say both,
briefly, rather than replacing one with the other, since Step 8's existing offer is not wrong.

Do not add a link where a mention will do. A relative link to a sibling `SKILL.md` is a profile edge
in `install.py`, which `bug-0038` documented on 2026-08-20, so a link written for readability changes
what the installer places. `init-worktracking` and `reconcile-worktrees` are both in `spine`, and
`spec-author` and `doc-sync` are too, so a link here is very likely free; check rather than assume,
and use the backtick form if it is not.

## Risks and rollback

Two skill bodies, prose only, so the more-than-one-module rule does not fire. The link-versus-backtick
point above is the one way a prose edit here reaches beyond prose, and `bug-0038`'s new membership
assertions will name any skill that moves.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `grep -c 'spec-author' .agents/skills/init-worktracking/SKILL.md` is non-zero, and the mention
      is a neighbour statement rather than an aside.
- [ ] `grep -c 'doc-sync' .agents/skills/reconcile-worktrees/SKILL.md` is non-zero, likewise.
- [ ] `init-worktracking` names both downstream paths, the spec spine and the direct one.
- [ ] Profile membership is unchanged, or the change is stated and deliberate, checked against
      `bug-0038`'s assertions rather than assumed.
- [ ] No other skill body is modified, and the README is untouched.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
