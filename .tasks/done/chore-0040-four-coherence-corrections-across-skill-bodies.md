---
id: chore-0040
title: Four prose claims across skill bodies that stopped being true, bundled because none carries a design question
type: chore
status: done
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
[`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) ships `validate.py` at every tier
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

The [`README.md`](../../README.md) Mermaid diagram is the only correct full statement of the chain, and no
skill body agrees with it.

**3. `fix-batch` points worktree agents at a skill they usually cannot run.**
[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) Step 3 tells a dispatched agent to use
[`test-author`](../../.agents/skills/test-author/SKILL.md) for behavior with no test yet. `test-author`'s
acceptance mode requires an approved spec, which an agent holding a single bug task typically does not
have. Its characterization mode is the escape hatch and exists for exactly this, and
`grep -c "characterization"` over `fix-batch` returns `0`.

**4. `spec-conformance` writes a file that `verifier-agent` promises not to write.**
[`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md): "Write the matrix and the coverage
proof, conventionally to `docs/spec/<spec>.conformance.md`".
[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md), which composes it: "By default the
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
  [`bug-0032`](bug-0032-test-author-never-checks-the-spec-is-approved.md); this task depends on it so
  the characterization exemption is already written when item 3 points at it.
- The lite-tier `parent` problem in `init-worktracking` and `new-task`, which is
  [`bug-0030`](bug-0030-lite-tier-parent-field-has-no-roadmap-to-name.md); this task depends on it as a
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

- [x] `init-worktracking`'s tier justification names only skills that reference `validate.py`, verified
      by grep, and the decision and its reason are unchanged.
- [x] The four spine statements are consistent with the README diagram, `spec-author`,
      `verifier-agent` and `pr-describe` each appear in at least one, and `new-task`'s ordering matches
      its own Step 1.
- [x] `fix-batch` names `test-author`'s characterization mode where it points at that skill.
- [x] `spec-conformance` defers its report destination to the composing skill and names the
      `docs/spec/` convention for standalone use; `verifier-agent`'s promise is no longer contradicted.
- [x] Existing tests still pass, unchanged in intent.

## Decisions

**All four premises re-checked against the working tree before editing; all four still hold.**
`bug-0030`, `bug-0032` and `feat-0048` had all landed by the time this ran and each touched a file
here, so every count and quote was re-derived rather than inherited:

- Item 1: `validate.py` reference counts are unchanged (`new-task` 2, `fix-batch` 0,
  `reconcile-worktrees` 1, `doc-sync` 1). The correction is one clause and the count stays three,
  so the paragraph's argument needed no rewriting: `fix-batch` out, `doc-sync` in.
- Item 2: all four spine statements were still as tabulated. `pr-describe` carries **two** of them
  (the opening paragraph and a Notes bullet), not one; both were corrected.
- Item 3: `grep -c characterization` over `fix-batch` still returned `0`, and `bug-0032` has since
  written the exemption into `test-author` ("Both gates are acceptance-mode gates. Characterization
  mode is exempt from both"), so item 3 now points at text that exists.
- Item 4: `verifier-agent`'s promise is verbatim as quoted, at its Step 5.

**One premise held but rests on a README edge this task could not honour literally.** The README
diagram has `spec-plan-readiness -> new-task`, but `new-task`'s own body (its spec-decomposition
section and its Step 7) has `new-task -> spec-plan-readiness`, because that gate takes a spec *plus
its task decomposition* and so cannot run before the decomposition exists. The diagram is out of
scope here and the skill bodies are the deliverable, so `new-task`'s statement names
`spec-plan-readiness` as the gate over the set it produces, which is true under its own body and
does not assert the disputed direction. **The README edge is left for a follow-up**; it is reported
rather than silently reversed.

**Immediate neighbours, not full chains** (per the implementation notes and the risk section). No
body now restates the twelve-step chain: `project-bootstrap` states its own end
(`-> init-worktracking -> spec-author`), `pr-describe` states the other
(`reconcile-worktrees -> doc-sync -> pr-describe`), and each says explicitly that it names only its
own neighbours so a later editor does not helpfully re-expand it. `spec-author` lands in
`project-bootstrap`'s, `verifier-agent` in `fix-batch`'s, `pr-describe` in its own.

`fix-batch`'s frontmatter `description` carried a fifth copy of the spine, so it was corrected in
step with the body rather than left as a fresh source of drift.

**No skill gained a spine statement it did not already have**, and the README was not touched.

**A prose-only edit turned out to be able to change the install footprint, which is worth knowing.**
Writing `pr-describe`'s new neighbour as a markdown link, `[doc-sync](../../doc-sync/SKILL.md)`, broke
three `test_install.ProfileTests` cases. `SIBLING_REF_RE` in `scripts/install.py` treats any
`](../../<name>/SKILL.md)` as a profile edge and expands a profile over its sibling closure, and the
`core` seed is exactly `project-bootstrap`, `init-worktracking`, `pr-describe`. One new link put
`doc-sync` into `core`, `doc-sync` sits inside the fourteen-skill strongly connected component, and
`core` collapsed into `spine` (both 13501 description characters, so `core < spine` stopped holding).
Naming `doc-sync` in backticks instead keeps the reference graph, and therefore the profile
boundary, exactly as it was. This task forbids behaviour changes, and silently growing `core` from
three skills to eighteen is one.

The general lesson for anyone editing a skill body: **a cross-skill markdown link is a build input,
not just prose.** Link a sibling when the reader should actually go there; name it in backticks when
you are only stating where it sits in the chain. That distinction is why the two `test-author` and
`verifier-agent` links added to `fix-batch` were free (both already existed elsewhere in that body,
so its reference set is unchanged) while one link in `pr-describe` was not.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
