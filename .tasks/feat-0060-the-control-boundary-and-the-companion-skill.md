---
id: feat-0060
title: Prove the reporting surface mutates no session, and put the control actions where the harness actually exposes them
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-019, S-020]
touched_files:
  - scripts/
  - tests/
  - .agents/skills/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

The observatory reports on sessions belonging to a running program, and the natural next wish is to
act on one. `S-019` and `S-020` in
[`docs/spec/agent-observatory.md`](../docs/spec/agent-observatory.md) draw that boundary, and this
task makes it a proven property rather than a stated intention.

**The gap the design has to close is real.** The actions worth wanting (hand a message to a running
session, retitle one, archive a finished one) are reachable only through session-management tools the
harness exposes to an agent running inside it. A standalone local server cannot call them. So the
reporting surface stays read-only, and the control actions live in a skill that runs where those tools
exist.

Read the contract for what must be true. It is not restated here.

## Scope

**In scope:** the enumerated read-only boundary, and the companion skill.

- The navigation affordances `S-019` permits: opening the pull request, opening the working directory,
  and presenting a resume command for a person to run.
- A test that enumerates every action the surface offers and asserts none mutates a session.
- A new skill at `.agents/skills/agent-observatory/SKILL.md`, which reads the store and performs
  session-directed actions where the harness exposes them.
- The declining behavior `S-020` requires when it does not.

**Out of scope:**

- **Starting, resuming, interrupting, or ending a session.** The contract's Non-Goals exclude all
  four, and `S-020` forbids finding another route to the same effect.
- **Writing to the harness's session messaging channel directly.** See the notes.
- **Blessing the skill.** It ships as a draft. See the notes.
- **Any new report.** This task adds actions and a skill, not figures.

## Implementation notes

**The skill ships as a draft and is excluded from installs.** The contribution-bar section of
[`AGENTS.md`](../AGENTS.md) forbids shipping a skill cold, and
[`feat-0036`](done/feat-0036-installer-excludes-draft-skills.md) already gives `install.py` the
mechanism: a skill marked draft in its frontmatter metadata is not placed. Use it. Blessing is the
author's call after the skill has been used on real work.

**The harness-specific dependency goes in a clearly labelled optional section.** The portability
contract in `AGENTS.md` requires it: no other harness exposes these tools, and a skill body that
assumes one is not portable. The skill must degrade to the navigation affordances rather than fail.

**Do not drive the session messaging channel directly.** The harness's live registry exposes a
messaging path, and using it would be undocumented reverse engineering against a surface that can
change without notice. `S-020` requires that no alternative route to the same effect is attempted when
the supported one is absent, and this is the route it has in mind.

**`S-019` is an enumeration claim, which is what makes it testable.** "Nothing mutates a session" is
untestable as prose and testable as a list: enumerate the actions the surface offers, and assert the
set contains nothing that writes. Build the surface so that list can be produced by a test rather than
maintained by hand, or the assertion decays the first time someone adds a button.

**A skill body's links may not escape the shipped skill tree.** `validate-skills.py` fails on it, and
the store and server this skill reads about sit outside that tree, so name them in prose rather than
linking to them.

## Risks and rollback

The task touches more than one module: the reporting surface, its tests, and a new skill that ships to
adopters if the draft marking is wrong. The deterministic rule fires on the first condition.

The consequential risk is the draft marking. A skill that is not excluded is placed into user-scope
discovery locations by `install.py` and starts triggering in unrelated sessions before it has been
used once. That is a stated acceptance criterion, verified against a real install cycle rather than by
reading the frontmatter.

The second risk is the boundary decaying: `S-019` holds on the day it is written and is one added
button away from being false. The enumeration test is the guard, and it is worth more than the
scenario it proves.

Reversible by reverting one commit. No schema change, no persisted format, nothing an adopter received.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] New tests cover S-019 and S-020, each named so the scenario it proves is identifiable.
- [ ] A test enumerates every action the reporting surface offers and asserts none of them mutates a
      session (S-019).
- [ ] The enumeration is derived from the surface rather than hand-maintained, so a newly added action
      appears in it without the test being edited.
- [ ] With no session-management capability available, a session-directed request is declined with the
      reason stated, navigation actions still work, and no alternative route is attempted (S-020).
- [ ] `install.py --dry-run` does not place `agent-observatory`, proven against the real install cycle.
- [ ] `python scripts/validate-skills.py` passes on the new skill, including the link-escape rule.
- [ ] The harness-specific capability sits in a section labelled optional, and the skill degrades
      rather than failing without it.
- [ ] Nothing writes to the harness's session messaging channel, asserted by a test.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `agent-observatory` conformance matrix is updated for S-019 and S-020, completing all 22.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
