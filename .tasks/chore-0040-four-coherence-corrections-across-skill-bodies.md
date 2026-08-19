---
id: chore-0040
title: Four prose claims across skill bodies that stopped being true, bundled because none carries a design question
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0030, bug-0032]
touched_files:
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/project-bootstrap/SKILL.md
  - .agents/skills/new-task/SKILL.md
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
  - .agents/skills/spec-conformance/SKILL.md
created: 2026-08-18
---

## Problem

Four claims found in the 2026-08-18 review pass, each a sentence or two, none with an interesting
design question behind it. They are bundled deliberately: authoring and verifying four task files would
cost more than the work. The bundling is the exception rather than the pattern, and the reason is
written here so a later reader does not take it as licence. `chore-0038` set the precedent.

**1. A tier justification names a skill that has never mentioned the file.**
[`init-worktracking`](../.agents/skills/init-worktracking/SKILL.md) ships `validate.py` at every tier
because "three sibling skills (`new-task`, `fix-batch`, `reconcile-worktrees`) instruct agents to run
it unconditionally. Withholding it at lite made those instructions dead references." Counted
2026-08-18:

```text
new-task             2
fix-batch            0
reconcile-worktrees  1
```

The decision is right and should stand. One third of its stated basis is fiction, and `doc-sync`,
which does reference the file, is not named.

**2. Four skills state four different versions of the kit spine, and none is the right one.**

| Where | States |
|---|---|
| `project-bootstrap` | bootstrap, init-worktracking, new-task, fix-batch, reconcile-worktrees |
| `new-task` | new-task, init-worktracking, fix-batch, reconcile-worktrees |
| `fix-batch` | new-task, fix-batch, reconcile-worktrees |
| `pr-describe` | bootstrap, init-worktracking, new-task |

Neither `spec-author` nor `verifier-agent` appears in any arrow chain in any skill body, so the
contract-driven half of the kit is unreachable by handoff from the front door. `pr-describe` is named by
nothing that precedes it, so the closing bookend is unreachable too. And `new-task`'s version puts
`init-worktracking` *downstream* of itself while its own Step 1 stops and points at `init-worktracking`
when `.tasks/` is absent, which is the reverse order.

The [`README.md`](../README.md) Mermaid diagram is the only correct full statement of the chain, and no
skill body agrees with it.

**3. `fix-batch` points worktree agents at a skill they usually cannot run.**
[`fix-batch`](../.agents/skills/fix-batch/SKILL.md) Step 3 tells a dispatched agent to use
[`test-author`](../.agents/skills/test-author/SKILL.md) for behavior with no test yet. `test-author`'s
acceptance mode requires an approved spec, which an agent holding a single bug task typically does not
have. Its characterization mode is the escape hatch and exists for exactly this, and
`grep -c "characterization"` over `fix-batch` returns `0`.

**4. `spec-conformance` writes a file that `verifier-agent` promises not to write.**
[`spec-conformance`](../.agents/skills/spec-conformance/SKILL.md): "Write the matrix and the coverage
proof, conventionally to `docs/spec/<spec>.conformance.md`".
[`verifier-agent`](../.agents/skills/verifier-agent/SKILL.md), which composes it: "By default the
report is returned inline and no file is created; write it to disk only when a report destination was
supplied." A `verifier-agent` run following the composed lens as written produces a file it just
promised not to produce.

## Scope

**In scope:** the four corrections above.

- Item 1: correct the list of skills to what it is, and keep the decision and its reason.
- Item 2: make the four spine statements agree with the README diagram, including `spec-author`,
  `verifier-agent` and `pr-describe`, and fix `new-task`'s ordering.
- Item 3: name characterization mode where `fix-batch` points at `test-author`.
- Item 4: make `spec-conformance`'s output instruction defer to the composing skill's destination, so
  standalone use still writes a file and composed use does not.

**Out of scope:**

- The README diagram, which is correct and is the reference for item 2.
- Adding a spine statement to skills that do not currently carry one. Four exist; make those four
  right rather than giving all twenty a chain to drift.
- `test-author`'s missing approval gate, which is
  [`bug-0032`](done/bug-0032-test-author-never-checks-the-spec-is-approved.md); this task depends on it so
  the characterization exemption is already written when item 3 points at it.
- The lite-tier `parent` problem in `init-worktracking` and `new-task`, which is
  [`bug-0030`](done/bug-0030-lite-tier-parent-field-has-no-roadmap-to-name.md); this task depends on it as a
  file-collision ordering, since both edit those two bodies.
- Any behaviour change. All four are statements of fact about the kit, and the facts are the fix.

## Implementation notes

For item 2, derive the canonical chain from the README diagram and quote it once, then have each of the
four skills state the part of it that concerns them rather than the whole thing. Four full copies of a
twelve-step chain is how these four drifted apart in the first place, and a skill only needs its own
neighbours.

For item 4, the wording to avoid is a second default. `spec-conformance` is a lens, so it should say
that the destination is the composing skill's to choose and name the `docs/spec/<spec>.conformance.md`
convention as what to use when run standalone. That leaves both callers correct without either
overriding the other.

Item 1 is one clause. Resist rewriting the surrounding paragraph, whose argument is load-bearing and
correct.

## Risks and rollback

Touches six skill bodies, so it meets the more-than-one-module rule, but every change is prose stating
a fact and none alters a procedure. The one item that can go wrong quietly is item 2: a spine statement
edited to match the README and then the README changing leaves the same class of drift behind. Prefer
each skill naming only its immediate neighbours, which is stable under insertion, over a full chain,
which is not.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `init-worktracking`'s tier justification names only skills that reference `validate.py`, verified
      by grep, and the decision and its reason are unchanged.
- [ ] The four spine statements are consistent with the README diagram, `spec-author`,
      `verifier-agent` and `pr-describe` each appear in at least one, and `new-task`'s ordering matches
      its own Step 1.
- [ ] `fix-batch` names `test-author`'s characterization mode where it points at that skill.
- [ ] `spec-conformance` defers its report destination to the composing skill and names the
      `docs/spec/` convention for standalone use; `verifier-agent`'s promise is no longer contradicted.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
