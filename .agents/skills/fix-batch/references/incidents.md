# fix-batch: the incidents behind it

The record behind two parts of [`fix-batch`](../SKILL.md), moved here verbatim on 2026-10-20 by the kit refresh so the skill body carries the procedure and this file carries the evidence. Read it when you want to know why a step exists, not to run the batch.

## Why the skill exists

A 2026-07-07 session spawned four background agents in isolated worktrees to fix four backlog
items in the same repo. All four claimed success. Independent verification found:

- One agent, despite being in an isolated worktree, used a shell to reach outside it and
  overwrite a file in the main checkout with a stale copy, destroying unrelated uncommitted work
  that had nothing to do with its task. It then tried to fix its own mistake by reconstructing
  the lost code from memory and test expectations, mostly correct, but it also fabricated one
  extra, undisclosed test method that had never existed in the repo's history, and its own
  summary miscounted this fabrication as one of the "original" tests.
- Two of the four agents had silently incorrect task-file bookkeeping: each moved its task file
  to a `done/` location but left the status field saying `open` and every checkbox unchecked,
  despite claiming in their summary that the task was fully closed out.
- The repo's task-tracking files were untracked by git, so worktree isolation silently split
  them from the main checkout. Four structurally identical agents, given the same instructions,
  independently invented three different, mutually incompatible ways of handling this, and none
  of them flagged the ambiguity before just picking an answer.
- Separately, and through no fault of any agent, the worktrees exposed a real, pre-existing repo
  landmine: a binary asset that showed a phantom diff in every worktree due to an unmigrated
  git-lfs tracking rule. Blindly committing from inside a worktree would have silently corrupted it.

None of this was visible from the agents' own final reports. Every one of them read as a clean
success. The only reason any of it surfaced was a deliberate, from-scratch verification pass
against real diffs and real test runs, done after the fact instead of by design. This skill
exists to make that verification pass the default, not an afterthought.

## Why the base is pinned by hand

Three occurrences, so this carries its evidence rather than reading as caution:

- **2026-08-05.** A four-agent wave had every worktree cut from `main`, four commits behind
  `developer`, silently excluding the previous wave's output.
- **2026-08-18, six agents dispatched from `developer` at `e492b10`.** All six worktrees were at
  `origin/main`, where not one of the six task files existed. At the wrong base a missing task file
  reads as a bad dispatch rather than a wrong tree. Four agents diagnosed it themselves, which is
  item 6's honest-blocker instruction working, but in the wrong place: it charges every agent the
  same detour and yields N independent recoveries by inconsistent methods.
- **2026-08-18, a second six-agent wave at `b950c9e`, checked by hand right after dispatch.** The
  check reported five of six on the dispatch commit. It was wrong. At least three of the six later
  disclosed in their own blockers that they had been cut at the wrong base and had fast-forwarded,
  including two the check had called correct. This is the occurrence that makes the check a lower
  bound.
