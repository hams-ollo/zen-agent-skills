---
id: feat-0022
title: Wire verifier-agent into fix-batch and reconcile-worktrees
type: feat
status: done
priority: P1
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: [bug-0002]
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-07-25
---

## Problem

[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) was built to formalize the verification
pass that [`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) requires. Its own body says so:

> "It formalizes the verification pass that `fix-batch` requires but leaves to the agent running it,
> so depth and evidence stop varying between runs."

But the wiring was never done. `grep -c verifier-agent` returns **0** for both `fix-batch` and
`reconcile-worktrees`. So:

- `fix-batch` Step 6 remains a five-point hand-rolled checklist, which is exactly the varying-depth
  problem `verifier-agent` exists to remove.
- [`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md) line 15 sends the reader to
  "`fix-batch` Step 6" for verification, so the stale path is now load-bearing in two skills.

This was deliberately deferred. [`feat-0019`](feat-0019-draft-verifier-agent.md) listed it as out
of scope: "wiring the skill into `fix-batch`'s verification pass, which is a separate follow-up once
this skill has been used." It has since been used twice, on `scripts/validate-skills.py` and in the
`doc-sync` build. The follow-up is due.

## Scope

**In scope:** rewrite `fix-batch` Step 6 to compose `verifier-agent` **by reference** for the
per-agent verification pass, and repoint `reconcile-worktrees`'s verification reference at
`verifier-agent` rather than at `fix-batch` Step 6.

**Out of scope:** changing [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) itself.
Changing `fix-batch`'s other steps, its `Why this exists` incident narrative, or its
`Running this in Claude Code` section beyond what Step 6 requires. Any change to
`reconcile-worktrees` beyond the verification reference.

## Implementation notes

- **Compose by reference; do not restate.** This is the same discipline `verifier-agent` uses for
  `spec-conformance` and `doc-sync` uses for `doc-revise`. Step 6 should say what `verifier-agent`
  produces and what `fix-batch` does with the verdict, not re-list how to verify.
- **Do not lose what Step 6 knows that `verifier-agent` does not.** Step 6 carries hard-won,
  batch-specific checks that are not in `verifier-agent`'s scope and must survive the rewrite:
  - diffing the worktree against its base and treating anything outside the task's scope as a finding;
  - checking that task-file and changelog bookkeeping actually matches what the agent claimed;
  - treating "I recovered from an error" in an agent summary as a high-scrutiny flag;
  - the cross-worktree landmine check (identical unexpected diffs across worktrees implying a tooling
    or LFS issue rather than agent error).

  These are properties of *dispatching a batch*, not of verifying one implementation. Keep them in
  `fix-batch` and let `verifier-agent` own the per-implementation verdict.
- **Preserve the independence rule.** `fix-batch` Step 6 already says not to delegate verification
  back to the agent being verified; `verifier-agent` says the same. Keep one statement, not two.
- `verifier-agent` returns `pass | fail | blocked`. `fix-batch` Step 7 currently says "do not
  auto-merge". State what each verdict means for the batch: a `blocked` verdict is not a pass, and it
  is the branch neither skill has exercised on real work yet (see ROADMAP Epic A item 8).
- **Depends on `bug-0002`**, which also edits `fix-batch/SKILL.md`. Do not dispatch these two to
  parallel worktrees; `bug-0002` must be in `.tasks/done/` first.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `grep -c verifier-agent .agents/skills/fix-batch/SKILL.md` returns at least 1.
- [x] `grep -c verifier-agent .agents/skills/reconcile-worktrees/SKILL.md` returns at least 1.
- [x] `fix-batch` Step 6 composes `verifier-agent` by reference and does not restate its verdict rule
      or its output schema.
- [x] All four batch-specific checks listed in the implementation notes are still present in
      `fix-batch`.
- [x] `reconcile-worktrees` no longer directs the reader to `fix-batch` Step 6 as the verification
      procedure.
- [x] Every relative markdown link added resolves to a file that exists.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings (watch
      `fix-batch`'s body length, currently 182 lines).
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `bug-0002` confirmed in `.tasks/done/` before starting.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
