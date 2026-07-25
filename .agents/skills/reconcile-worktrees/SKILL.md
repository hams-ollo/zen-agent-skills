---
name: reconcile-worktrees
description: Safely consolidate one or more isolated git worktrees (for example left behind by parallel background agents, or from the fix-batch skill) into the main working tree, without committing or merging blindly. Use whenever asked to "reconcile the worktrees", "merge these agent branches", "bring the worktree changes back into main", "clean up the worktrees", or when multiple agent worktree directories exist and their changes need to land in the primary checkout. It is the closing step of the kit spine: new-task authors, fix-batch dispatches to isolated agents, reconcile-worktrees lands the verified results. Also use it proactively after a fix-batch run once every spawned agent has been individually verified, as the natural next step.
---

# reconcile-worktrees

Bring the verified contents of one or more isolated git worktrees into the main working tree as a
clean, reviewable diff, without silently overwriting anything, without committing on the user's
behalf, and without trusting that "no conflicts reported" means "safe".

This is the closing step of the kit spine: [`new-task`](../new-task/SKILL.md) authors the task
files, [`fix-batch`](../fix-batch/SKILL.md) dispatches them to isolated worktree agents, and this
skill consolidates the results. It assumes each worktree has already been through its own
verification pass via [`verifier-agent`](../verifier-agent/SKILL.md) (`fix-batch`'s Step 6 is what
runs it against every worktree in a batch). This skill is about combining already-trusted changes,
not about trusting them in the first place. If a worktree has not been independently verified yet,
run [`verifier-agent`](../verifier-agent/SKILL.md) against it first.

## Why this exists

Reconciling several worktrees by hand after a batch of parallel agent fixes turned out to be its
own source of risk, separate from whatever the agents themselves did wrong. In the 2026-07-07
incident that motivated the `fix-batch` skill: task-file bookkeeping split three incompatible ways
across worktrees because some agents wrote directly to the main checkout and others did not; a
binary asset showed an identical phantom diff in every worktree due to an unmigrated git-lfs rule,
which would have silently corrupted the file if any worktree's changes were committed with a
blanket `git add -A`; and two worktrees both touched the same file in different, non-overlapping
regions, which is safe to combine but only if you actually check that before assuming it.

## Procedure

### Step 1: enumerate every worktree and its base commit

```
git worktree list
```

Note each worktree's path, branch, and the commit it is based on. If any worktree's base commit
differs from the main checkout's current `HEAD`, flag that explicitly. Changes made against a
since-moved base need extra care (the diff you are about to apply may no longer cleanly represent
"just this worktree's changes" if `main` has moved).

### Step 2: for each worktree, get a clean diff scoped to that worktree's own changes

```
cd <worktree-path>
git status --short
git diff --stat
git diff -- <path>   # per file, read the actual diff, do not just skim the stat
```

Do not skip straight to combining. Read every file's diff, even if you already reviewed it during
the earlier per-agent verification pass. Reconciliation is a second, independent checkpoint, not a
rubber stamp of the first one.

### Step 3: check every worktree for the untracked-file and binary-asset traps

- **Untracked files** (task-tracking files, config not covered by `.gitignore` exceptions, and so
  on) do not show up in `git diff` and will not travel with a normal patch or cherry-pick.
  Explicitly `ls` and diff these locations by hand across every worktree and the main checkout,
  since this is exactly where inconsistent agent behavior tends to surface (three worktrees might
  have handled the same untracked file three different ways).
- **Binary assets**, especially anything under an LFS `filter=` rule in `.gitattributes`: run
  `git status` and `git diff --stat` on these paths specifically. If any show as "modified"
  identically across multiple worktrees with no worktree's task ever touching that file, that is
  very likely a phantom diff from an environment or tooling quirk (for example an unmigrated LFS
  asset), not a real change. Confirm by comparing actual byte sizes (`ls -la`) and raw content
  (`git cat-file -s HEAD:<path>` versus the working file) before deciding whether to include or
  explicitly exclude the path from anything you bring into main.

### Step 4: check for real overlaps between worktrees before combining

If two or more worktrees touched the same file, diff those regions against each other directly
(not just "tests pass in isolation for each"). Confirm the changes are in genuinely separate,
non-conflicting regions, or that one is a strict superset or continuation of another. Do not assume
compatibility from green test suites alone. Two independently-passing changes to the same file can
still conflict or silently undo each other when combined.

### Step 5: apply changes to the main working tree deliberately, one worktree at a time

Prefer applying one worktree's diff at a time (for example `git -C <worktree> diff | git apply`
into the main checkout, or manually replicating the edits) rather than a bulk merge of all
worktrees at once, so that if something goes wrong you know immediately which worktree caused it.
After each one:

- Re-run the affected test suite in the main checkout, not just trust that it passed inside the
  worktree in isolation. The combination of multiple worktrees' changes together is a new state
  that has not actually been tested yet.
- Re-check `git status` for anything unexpected before moving to the next worktree.

### Step 6: normalize any split bookkeeping

If task-tracking files (or a changelog) ended up in inconsistent states across worktrees per Step
3, resolve them into one consistent, correct state in the main checkout now. Do not leave several
different partial versions lying around. In this kit that means one `.tasks/` file per item in its
correct final location with `status: done`, every acceptance checkbox honestly reflecting reality,
and one dated `CHANGELOG.md` line per task id. Verify each task's acceptance criteria are actually
met (re-run them, do not just check a box, and run `python .tasks/validate.py` on the consolidated
result) before marking anything as done.

### Step 7: present the final consolidated diff, do not commit automatically

Show the user (or state clearly in your own summary) exactly what is about to land in the main
working tree, file by file, and what you verified at each step. Do not run `git add`, `git commit`,
or `git push` unless explicitly asked to. This whole skill exists to produce a trustworthy diff for
a human decision, not to make that decision for them.

### Step 8: clean up worktrees only after their changes have safely landed

Once a worktree's changes are confirmed applied and verified in the main checkout, it is safe to
remove it (`git worktree remove <path>`). Do not remove a worktree before its changes are safely
elsewhere, it is your only copy until then.

## Note on where worktrees live

The worktree paths are harness-specific. When the worktrees were created by `fix-batch` under
Claude Code, they are the ones `git worktree list` reports for the background agents (commonly
under a `.claude/worktrees/` or similarly named directory). The git procedure above is identical
regardless of which harness created them, so no part of this skill depends on a particular tool.
