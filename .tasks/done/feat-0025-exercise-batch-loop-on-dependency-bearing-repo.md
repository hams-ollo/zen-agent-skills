---
id: feat-0025
title: Exercise the hardened batch loop on a repo that has real build dependencies
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
  - .agents/skills/verifier-agent/SKILL.md
created: 2026-07-27
---

## Problem

The 2026-07-27 review pass hardened three parts of the batch loop that had never met a repository
with a build environment:

1. [`fix-batch`](../.agents/skills/fix-batch/SKILL.md) Step 2 now requires resolving what git will
   not carry into a worktree (`node_modules/`, `.venv/`, `.env`, build caches) before dispatch,
   because the acceptance command cannot run without it, `verifier-agent` returns `blocked` for a
   runner it cannot find, and a `blocked` item is not reconciled. Unresolved, every item in a batch
   stalls at once and none of them look broken.
2. [`reconcile-worktrees`](../.agents/skills/reconcile-worktrees/SKILL.md) Steps 2, 5, and 8 now
   enumerate tracked edits, staged edits, and untracked files separately, apply the first via a
   patch file and the last via an explicit copy, and reconcile the landed paths against the
   worktree's `git status` list before any worktree is removed.
3. Both skills now read a worktree's base from the recorded dispatch sha rather than from
   `git worktree list`, which reports current `HEAD`.

The underlying git behaviors were verified directly (a staged change is invisible to bare
`git diff`; an untracked file is invisible to any diff; equal `rev-parse`/`hash-object` hashes prove
a phantom binary diff). What has **not** been exercised is the loop end to end on a repository where
these actually bite. This kit is documentation and stdlib Python with no dependency tree, which is
precisely why the environment trap survived to be found by reading rather than by running.

Per the contribution bar in the AGENTS.md contribution-bar section, no skill ships to the kit cold.
These changes are currently cold.

## Scope

**In scope:** run one real `fix-batch` batch of 2 or 3 independent items against a repository with a
genuine dependency install step (a Node or Python project, not this kit), all the way through
`verifier-agent` and `reconcile-worktrees`, then iterate the three skills from what the run finds.
Record which of the four environment strategies in Step 2 was chosen and what it actually cost.

At minimum the run must produce evidence for:

- an agent creating a **new file**, to prove Step 5's untracked copy lands it;
- an acceptance command that needs the dependency install, to prove the Step 2 resolution works and
  that `verifier-agent` reaches a real verdict instead of `blocked`;
- the Step 8 path-by-path reconciliation, on a batch where at least one path is deliberately
  excluded.

**Out of scope:** the `blocked` verdict branch itself, which is
[`feat-0024`](feat-0024-exercise-verifier-blocked-branch.md)'s subject. `test-author`'s
characterization mode. Any new skill.

## Implementation notes

Prefer a repository the author already works in over a synthetic fixture: the trap this closes is
specifically the one a synthetic repo would not have. A small Node project is the cheapest way to
get a real `node_modules/` and a real test runner.

If the run shows that per-worktree installs are too slow to be the sensible default, that is a
finding worth writing into Step 2's option list with the measured number attached, not a reason to
drop the step.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [x] One real batch run completed against a dependency-bearing repo, with the chosen environment
      strategy and its cost recorded.
- [x] A new file created by an agent is confirmed landed in the main checkout by Step 5.
- [x] `verifier-agent` returned a real `pass` or `fail` (not `blocked`) for at least one item.
- [~] Step 8's path-by-path reconciliation ran. **No deliberate exclusion occurred**, because no
      spurious path appeared: no phantom binary diff, no stray file, nothing to exclude. The
      criterion presumed a condition this batch did not produce. Recorded unmet rather than
      satisfied by manufacturing an exclusion, which would have tested nothing.
- [x] Each of the three skills either iterated from the run's findings or is recorded as confirmed
      unchanged, with the evidence.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-27)

Run against `gaudiya-vaishnava-knowledge-wiki`: three parallel worktree agents adding first test
coverage to three untested modules. Suite went 9 to 47, all three landed, every diff verified
independently before anything was applied.

**Environment strategy chosen:** install per worktree. `uv sync --extra dev` measured at **2 seconds
and 52MB** per worktree, so ~6s and 156MB for the batch. Effectively free with `uv`'s shared cache,
and the reason the four-option list now says to measure rather than assume.

**The reconciliation fix was load-bearing, not theoretical.** Every item's deliverable was a new
file, so all three `git diff` patches were 0 bytes. Under the pre-2026-07-27 mechanism
(`git diff | git apply`) the entire batch would have landed nothing, reported success, and been
deleted at cleanup.

**Six findings, all folded back into the skills:** the harness section assumed a same-repo batch;
"tracked" needed to be "committed", since a worktree checks out a commit and `git add` is not
enough; the pre-flight command check caught a genuinely broken acceptance command before dispatch;
strategy cost is toolchain-dependent and wants measuring; closeout bookkeeping needed to be
explicitly excluded from agent prompts; and two of three task files carried premise errors about the
code that the agents caught and reported rather than complied with, which is now a `new-task` rule.
