---
id: feat-0037
title: Record agent decisions in the task file, and surface them in the PR description
type: feat
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - .tasks/_TEMPLATE.md
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
created: 2026-08-04
---

## Problem

When a worktree agent finishes, everything it *decided* is lost. The diff survives, the test result
survives, the conformance matrix survives. The reasoning does not: which alternative was rejected and
why, which seam was left open deliberately, which premise in the task file turned out to be false.

This is not hypothetical. Two of the three agents in the `feat-0025` batch found that their task
file's premise was factually wrong about the code, tested what was actually there, and reported it.
That surfaced only because a human was reading the reports. Nothing in the system captured it, and
[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) Step 3 item 6 asks only for a *blocker* report,
so a non-blocking premise correction has nowhere to go at all.

The cost lands on the next agent. It reads the task file and the diff, sees a seam left open, reads
it as an oversight, and helpfully closes it. Or it re-derives a rejected alternative from scratch.
The 2026-07-27 pass records the extreme version of this: `reconcile-worktrees` dropped every new file
an agent created, "and the worktree holding the only copy was then deleted."

**This task is the deliberately cheap half of a larger idea, scoped to test one assumption:** that
agents will write decision entries worth reading. The spec-sibling rollup
(`docs/spec/<name>.decisions.md`), consumed by `new-task` on the next task against the same spec, is
the expensive half and is **not** in this task. Build it only if this one proves the entries are any
good. See [Kill criterion](#kill-criterion).

## Scope

**In scope:**

1. **[`.tasks/_TEMPLATE.md`](../_TEMPLATE.md)**: add an optional `## Decisions` section, placed after
   `## Implementation notes`. Follow the `## Risks and rollback` precedent exactly, including its
   delete-when-empty rule and the stated reason for it. The section states the three admissible
   entry kinds and, more importantly, the exclusion list:

   - **Admissible:** a choice between live alternatives (what was rejected, and why); a seam left
     open deliberately (so the next agent does not "fix" it); a premise that turned out false.
   - **Not admissible, because something else already owns it:** what changed (git), whether tests
     passed (`<spec>.verification.md`), whether it matched the contract (`<spec>.conformance.md`),
     why the feature exists (the spec).

2. **[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md)**: add one item to the Step 3 hardened-prompt
   list instructing each agent to record decisions **in its own task file** before finishing. State
   why the task file specifically: it is the one file uniquely owned by that agent, so N agents
   writing to it is not a shared-file conflict, unlike the `done/` move, `CHANGELOG.md`, and
   `ROADMAP.md` edits that the existing "keep closeout bookkeeping out of every prompt" rule
   correctly forbids. This addition must not weaken that rule; say plainly that it is the exception
   that proves it.

3. **[`pr-describe`](../../.agents/skills/pr-describe/SKILL.md)**: in Step 2, when the task file(s) the
   branch completes carry a non-empty `## Decisions` section, fold those entries into the PR body's
   existing optional "Follow-ups / out of scope" section rather than adding a new heading. The skill
   already reads `.tasks/` and `.tasks/done/` for the `external` field, so this is a second read of a
   file it already opens.

**Out of scope:**

- **The spec-sibling rollup.** No `docs/spec/<name>.decisions.md`, no new record kind in `AGENTS.md`
  section 2, and no change to [`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md).
  The whole point of this task is to test the cheap half first.
- **[`new-task`](../../.agents/skills/new-task/SKILL.md).** It gains a read obligation only once a rollup
  file exists to be cited. Nothing to point at yet.
- **[`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) and its
  `templates/_TEMPLATE.md.tmpl`.** Propagating this to every scaffolded repository before it has been
  used here once is exactly the cold ship `AGENTS.md` section 7 forbids. This repository dogfoods it
  first.
- **Enforcement in [`validate.py`](../validate.py).** It checks frontmatter, not sections. Making the
  section mandatory would break every existing task file and would compel entries rather than earn
  them, which defeats the measurement this task exists to perform.
- Any change to the three verification record kinds, or to `AGENTS.md`.

## Implementation notes

**Mirror the `## Risks and rollback` precedent rather than inventing a shape.** That section already
solves the same problem in this template: optional, conditionally required, and explicitly deleted
when empty, with the reason stated in the template itself ("a heading every task carries and most
leave blank teaches authors to skip it"). That reasoning applies unchanged here. Do not add a
`## Decisions` heading to tasks that have nothing to record.

**Keep the entries short and the exclusion list prominent.** The failure mode is not that agents
write nothing, it is that they write a prose restatement of the diff. Git already does that better.
An entry that could be reconstructed from `git log` and the verification record is a defect in the
entry, not a bonus.

**Do not restate the exclusion list in three places.** The template owns the definition; `fix-batch`
and `pr-describe` point at it. Three copies will drift, which is the same reasoning that put
`test-quality`'s layer taxonomy behind a reference in `chore-0010` instead of inline.

**The `fix-batch` wording is the delicate part.** Step 3's closeout-bookkeeping rule exists because N
agents editing `CHANGELOG.md` in N worktrees is a guaranteed reconciliation conflict. An agent
editing its own task file is categorically different and the new item must say so, or a future reader
will read the two rules as contradictory and drop one.

## Decisions

First dogfood of this task's own feature.

- **Rejected alternative**: mirroring `## Risks and rollback` ordering exactly, with the
  delete-when-empty sentence closing the section. That would have pushed the literal phrase
  "delete this section" past the 900-character window the second acceptance command inspects
  (`t.partition('## Decisions')[2][:900]`). The sentence moved up into the exclusion paragraph
  instead, so the precedent's shape survives but its ordering does not.
- **Seam left open deliberately**: the closing paragraph of `fix-batch`'s "The delegate report
  contract" still points forward at "the decision log specified separately in this kit's
  `feat-0037`" rather than back at the Step 3 item that now exists. Left as provenance, and out of
  this task's stated scope of one new Step 3 item. Not an oversight to close.
- **Premise that turned out false (partly)**: the Problem section says a non-blocking premise
  correction "has nowhere to go at all". `feat-0041` overtook that between authoring and dispatch:
  the delegate report contract's **blockers and assumptions** field now explicitly requires
  "including a task premise it found false". The task's conclusion still holds, because that report
  is ephemeral and lands in no file the repository keeps, but its stated reason no longer does.
  Step 3 item 6 does still ask only for a blocker report, so that half of the claim is accurate.

## Risks and rollback

The deterministic rule fires on two of three counts, so this section is required.

- **Touches more than one module**: the `.tasks/` template and two skills under `.agents/skills/`.
- **Changes a format other tooling reads**: the task file shape is consumed by `validate.py`,
  `new-task`, `fix-batch`, and `pr-describe`. The change is additive and every existing task file
  stays valid, since `validate.py` checks frontmatter only and the section is optional. No migration.

**What could go wrong.** The realistic failure is not breakage, it is noise: agents writing diff
summaries into every task file, making task files longer without making them more useful, and costing
context on every read. That is what the kill criterion below is for.

**Rollback** is reverting one commit. Nothing persists outside these three files, no data format
migrates, and task files written with a `## Decisions` section stay valid after a revert because
`validate.py` never looked at sections.

## Kill criterion

Record this in the task's closeout note, and review after the next `fix-batch` run of three or more
agents:

- **Keep and consider the rollup** if a majority of dispatched agents wrote at least one entry that
  is genuinely unrecoverable from the diff, the verification record, or the spec.
- **Delete the feature** if the entries are predominantly diff restatements, or if agents skip the
  section entirely. A log that is written and never read is pure cost, and reverting one commit is
  cheaper than maintaining a convention nobody uses.

State the outcome explicitly rather than letting the feature persist by default.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict && python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

    python -c "import pathlib,sys; r=lambda p: pathlib.Path(p).read_text(encoding='utf-8'); t=r('.tasks/_TEMPLATE.md'); f=r('.agents/skills/fix-batch/SKILL.md'); p=r('.agents/skills/pr-describe/SKILL.md'); d=t.partition('## Decisions')[2][:900]; c=[('## Decisions' in t), ('delete this section' in d), ('Decisions' in f and 'own task file' in f), ('Decisions' in p)]; sys.exit(0 if all(c) else 'failed: ' + str(c))"

- [x] `.tasks/_TEMPLATE.md` carries a `## Decisions` section after `## Implementation notes`, listing
      the three admissible entry kinds and the four-item exclusion list, and stating the
      delete-when-empty rule in the manner of `## Risks and rollback`.
- [x] `fix-batch` Step 3's prompt list gains one item covering the decision record, which explicitly
      distinguishes the agent's own task file from the shared files the existing closeout-bookkeeping
      rule protects.
- [x] `pr-describe` Step 2 folds non-empty decision entries into the existing "Follow-ups / out of
      scope" section, and adds no new top-level PR heading.
- [x] The exclusion list is defined once, in the template; the two skills reference it and do not
      restate it.
- [ ] No file outside `touched_files` is modified. In particular `validate.py`,
      `reconcile-worktrees`, `new-task`, `AGENTS.md`, and
      `.agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl` are untouched.
- [x] Every existing task file still passes `python .tasks/validate.py --strict` unchanged.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
- [ ] Kill-criterion review scheduled against the next `fix-batch` run of three or more agents.
