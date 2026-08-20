---
id: bug-0039
title: The README spine diagram runs spec-plan-readiness before new-task, and that gate cannot run until new-task has produced what it gates
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0040]
touched_files:
  - README.md
created: 2026-08-20
---

## Problem

[`README.md`](../README.md)'s Mermaid flowchart has:

```text
C[spec-author] --> D[spec-plan-readiness]
D --> E                       # E is new-task
```

So the chain reads spec-author, then spec-plan-readiness, then new-task. That order cannot happen,
because of what `spec-plan-readiness` takes as input. Its own frontmatter: "Use before implementation
when a spec **and its task decomposition** must be checked for coding readiness." Its body, line 15:
"a readable behavioral spec **plus a readable ordered set of task files**". The decomposition is
`new-task`'s output, so gating before `new-task` gates something that does not exist yet.

`new-task` says the same thing from its own side, at line 126: when the tasks came from an approved
spec, "the next step is not `fix-batch`: it is `spec-plan-readiness` over the spec plus this task
set."

The diagram is the wrong one, not the skills. Both skills agree with each other and the diagram
disagrees with both.

**This matters more than a normal doc error because of what the diagram is used for.** It is the
statement of the chain this repository treats as canonical: `chore-0040` was dispatched on
2026-08-19 to make four skill bodies agree with it, and its task file asserted in as many words that
the README diagram "is correct and is the reference for item 2". That assertion was mine and it was
wrong. The agent found the contradiction, could not fix the diagram because it was out of scope, and
wrote `new-task`'s corrected statement so that it names `spec-plan-readiness` as the gate over the
set it produces, which is true under both skills' bodies and does not assert the disputed direction.
So one skill body is currently phrased to route around a defect in the reference it was corrected
against.

## Scope

**In scope:** correct the edge so the diagram matches what both skills say, and check the rest of the
chain against the same standard while the file is open.

- The `spec-plan-readiness` node moves after `new-task`, or gains an edge that shows it gating the
  produced set rather than preceding its production. Which of those reads better in a left-to-right
  flowchart is the implementer's call; both are true.
- Re-derive every other edge from the skills' own bodies rather than assuming only this one is wrong.
  The diagram has not been checked against the skills since the spine grew, and `chore-0040` only
  looked at the four edges its own items touched.

**Out of scope:**

- The four skill bodies `chore-0040` corrected. They are consistent with both skills' own statements
  and stay as they are; if the diagram's correction makes a crisper phrasing available for
  `new-task`, that is a follow-up rather than part of this fix.
- The prose around the diagram, unless a re-derived edge falsifies a sentence in it.
- `docs/ARCHITECTURE.md`, which carries its own diagrams and is a separate audit.

## Implementation notes

Derive each edge from the skills, not from this task file, which describes one edge and was written
by the same author who asserted the diagram was correct in the first place.

The cheapest grounding for each edge is the pair of skills' own handoff sentences: most skill bodies
now name their immediate neighbours after `chore-0040`, so the diagram can be checked against them
rather than against memory of the workflow.

Worth knowing: `spec-plan-readiness` returning `blocked` authorizes no tests, code, or delegation, so
its position is not decorative. A reader following the diagram literally would run the gate against a
spec alone, get an answer about an incomplete input, and treat it as permission.

## Risks and rollback

One file, no code, so the more-than-one-module rule does not fire.

The risk is fixing the named edge and leaving a sibling wrong, which would leave the diagram still
carrying the authority of being canonical while still being partly false. That is why the scope asks
for a re-derivation of every edge rather than the one this task found.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The diagram no longer places `spec-plan-readiness` before `new-task`.
- [ ] Every edge in the diagram is consistent with the two skills it connects, checked against their
      bodies, and the closeout states how many edges were re-derived and how many were found wrong.
- [ ] No skill body is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
