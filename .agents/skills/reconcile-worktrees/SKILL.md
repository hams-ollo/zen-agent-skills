---
name: reconcile-worktrees
description: >-
  Safely consolidate one or more isolated git worktrees (for example left behind by parallel
  background agents, or from the fix-batch skill) into the main working tree, without committing
  or merging blindly. Use whenever asked to "reconcile the worktrees", "merge these agent
  branches", "bring the worktree changes back into main", "clean up the worktrees", or when
  multiple agent worktree directories exist and their changes need to land in the primary
  checkout. It is the closing step of the kit spine: new-task authors, fix-batch dispatches to
  isolated agents, reconcile-worktrees lands the verified results. Also use it proactively after a
  fix-batch run once every spawned agent has been individually verified, as the natural next step.
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

### Step 1: enumerate every worktree and find its real base commit

```
git worktree list
```

Note each worktree's path and branch. Be careful with the commit in that output: it is the
worktree's **current `HEAD`**, not the commit it was created from. Those coincide only while the
worktree has no commits of its own, which is the state `fix-batch` asks for but not one you should
assume. Get the actual base per worktree:

```
git merge-base <worktree-branch> HEAD
```

or use the base sha `fix-batch` recorded at dispatch. If a worktree's base differs from the main
checkout's current `HEAD`, flag that explicitly. Changes made against a since-moved base need extra
care, because the diff you are about to apply may no longer cleanly represent "just this worktree's
changes" once `main` has moved.

### Step 2: enumerate all three kinds of change in each worktree, not just the tracked edits

A worktree's changes live in three places, and only one of them shows up in a bare `git diff`.
Missing any of the other two loses work silently, so enumerate all three explicitly:

```
git -C <worktree> status --short                          # the ground truth, everything at once
git -C <worktree> diff --binary HEAD                      # tracked edits, staged and unstaged
git -C <worktree> ls-files --others --exclude-standard    # new files git is not tracking yet
```

The distinctions matter and each has burned someone:

- **Bare `git diff` shows unstaged changes only.** If the agent ran `git add` at any point (nothing
  forbids staging, only committing), those edits are invisible to it. `git diff HEAD` covers both.
- **`git diff` never shows untracked files at all.** A new module or a new test file the agent
  created is untracked, because `fix-batch` tells agents to leave work uncommitted. This is the most
  expensive omission available here: it is usually the actual deliverable, and it produces no error,
  just an empty patch and a worktree you are about to delete. Measured on a real three-agent batch
  whose items were each "add a test file": all three `git diff` patches were **0 bytes**, so the
  whole batch would have landed nothing and reported success. Whenever the work is *new files*, which
  is a large fraction of real tasks, the tracked-diff half of this step returns nothing at all and
  the untracked half is the entire result.
- **`--binary` is required for any binary file**, or the patch is unappliable later.

Record the full `git status --short` file list per worktree now, not just its count. Step 8 checks
the landed result against it path by path.

Then read every file's diff, not just the stat, even if you already reviewed it during the earlier
per-agent verification pass. Reconciliation is a second, independent checkpoint, not a rubber stamp
of the first one.

### Step 3: check every worktree for the untracked-file and binary-asset traps

- **Untracked files** do not show up in `git diff` and will not travel with a normal patch or
  cherry-pick. Step 2's `ls-files --others` list is the enumeration; compare it across every
  worktree and the main checkout. Two different populations hide here and both matter: the agent's
  actual new source and test files (the deliverable), and bookkeeping files like task-tracking or
  config not covered by a `.gitignore` exception, which is exactly where inconsistent agent
  behavior surfaces (three worktrees might have handled the same untracked file three different
  ways). Use git's own commands rather than a shell listing, so the check behaves the same on
  Windows, macOS, and Linux.
- **Binary assets**, especially anything under an LFS `filter=` rule in `.gitattributes`: run
  `git status` and `git diff --stat` on these paths specifically. If any show as "modified"
  identically across multiple worktrees with no worktree's task ever touching that file, that is
  very likely a phantom diff from an environment or tooling quirk (for example an unmigrated LFS
  asset), not a real change. Confirm by comparing content hashes rather than trusting `git status`:
  `git -C <worktree> rev-parse HEAD:<path>` gives the committed blob and
  `git -C <worktree> hash-object <path>` gives the working file's. Equal hashes mean the content is
  byte-identical and the diff is phantom. Decide from that whether to include or explicitly exclude
  the path from anything you bring into main.

### Step 4: check for real overlaps between worktrees before combining

If two or more worktrees touched the same file, diff those regions against each other directly
(not just "tests pass in isolation for each"). Confirm the changes are in genuinely separate,
non-conflicting regions, or that one is a strict superset or continuation of another. Do not assume
compatibility from green test suites alone. Two independently-passing changes to the same file can
still conflict or silently undo each other when combined.

### Step 5: apply changes to the main working tree deliberately, one worktree at a time

Apply one worktree at a time rather than bulk-merging all of them, so that if something goes wrong
you know immediately which worktree caused it. Each worktree takes **two** operations, because the
tracked and untracked populations from Step 2 travel differently:

```
# 1. tracked edits: write the patch to a file, then apply it
git -C <worktree> diff --binary HEAD > <patch-file>
git apply --check <patch-file>     # dry run first; resolve any rejection before applying
git apply <patch-file>

# 2. untracked files: copy them across explicitly, one by one
git -C <worktree> ls-files --others --exclude-standard
```

Three rules about this, each earned:

- **Write the patch to a file rather than piping it.** A pipe is where encoding corruption happens
  (Windows PowerShell 5.1 pipes UTF-16 by default, which mangles a patch), and a file lets you read
  what you are about to apply and re-apply it after a failure.
- **`git apply --check` first.** A silent partial application is worse than a clean rejection.
- **The untracked copy is not optional and has no patch equivalent.** If you skip it, the files the
  agent actually created never land, `git apply` reports success, and Step 8 deletes the only copy.

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

### Step 8: reconcile the counts, then clean up

Before removing anything, prove the landing was complete. For each worktree, compare the file list
you recorded from `git status --short` in Step 2 against what `git status --short` now reports in
the main checkout for that worktree's paths. Every path the worktree changed must be accounted for:
landed, or deliberately excluded with a stated reason (a phantom binary diff from Step 3, a
bookkeeping file normalized in Step 6). A path in neither category is work that just went missing,
and this count is the only thing that catches it before the evidence is deleted.

Only then remove the worktree (`git worktree remove <path>`). Do not remove one before its changes
are safely elsewhere: it is your only copy until then.

Two cleanup cases that are not "changes landed":

- **A worktree whose agent failed, was killed, or returned `blocked`.** Its changes are not landing,
  but it is still the only copy of whatever it did produce. Leave it in place and say so in the
  Step 7 report rather than removing it, so the next run does not mistake an abandoned worktree for
  a reviewed one.
- **Orphans from an earlier run.** `git worktree list` shows every worktree, not only this batch's,
  so a previous failed run leaves candidates that look identical to live ones. Match the list
  against the batch you actually dispatched before touching anything, and run
  `git worktree prune` only for entries whose directory is already gone.

## Note on where worktrees live

The worktree paths are harness-specific. When the worktrees were created by `fix-batch` under
Claude Code, they are the ones `git worktree list` reports for the background agents (commonly
under a `.claude/worktrees/` or similarly named directory). The git procedure above is identical
regardless of which harness created them, so no part of this skill depends on a particular tool.

## Conventions

Follow the repo's house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)):
sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a
swappable default; a downstream adopter may replace it without touching this skill. This governs the
consolidated diff summary and the reports this skill writes, which are its only output: it never
edits the content it reconciles.
