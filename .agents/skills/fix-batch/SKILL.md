---
name: fix-batch
description: Delegate a batch of independent, already-scoped task files (bugs, chores, small features) to parallel isolated agents, each sandboxed in its own git worktree, with a mandatory independent verification pass before anything is treated as mergeable. Use this whenever asked to "fix these bugs", "work through the backlog", "spin up agents to fix X, Y, Z", or "parallelize these fixes", especially when there are 2 or more distinct, independently-fixable items and the user wants them actioned rather than just discussed. It is the parallel-execution step of the kit spine: new-task authors the task files, fix-batch dispatches them, reconcile-worktrees lands them. Do not use it for a single fix (just do it directly) or for changes that are inherently sequential or interdependent (one agent's output feeds the next's input), since worktree isolation assumes the items do not need to see each other's work in progress.
---

# fix-batch

Spawn parallel worktree-isolated agents to work a batch of independent task files, then verify
every one of them yourself before calling any of it done. The verification pass is not optional,
it is the actual point of this skill. Parallel delegation without it is just parallel delegation.
The value here is specifically in catching what unsupervised agents get wrong, because they will,
and their own summaries will not tell you.

This is the parallel-execution step of the kit spine: [`new-task`](../new-task/SKILL.md) authors
the atomic task files, `fix-batch` dispatches them to isolated agents, and
[`reconcile-worktrees`](../reconcile-worktrees/SKILL.md) lands the verified results into the main
working tree. Read [`AGENTS.md`](../../../AGENTS.md)'s agent reading protocol section (section 0 in
both this kit's own `AGENTS.md` and the `init-worktracking` scaffold's numbering) and its task
lifecycle section before dispatching, so each spawned agent inherits the same rules.

## Why this exists

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

## When not to use this

- A single fix, or fixes with actual dependencies between them (one agent needs to see another's
  finished output before it can work). Worktree isolation is specifically for independent,
  parallelizable work. Sequential or interdependent changes belong in one agent or one worktree,
  not several.
- Throwaway exploratory changes with nothing to lose if something goes sideways. The overhead of
  hardened sandboxing plus a full verification pass is worth it when the target is a real, shared,
  or otherwise valuable working tree, not for disposable scratch work.

## Procedure

### Step 1: confirm the batch is genuinely independent

Before doing anything else, check that the items really do not depend on each other (no item
needs another item's finished code to make sense) and that they touch **disjoint files**. If they
depend on each other or overlap the same files, this is not the right shape for parallel
worktrees. Handle those sequentially instead, in one place.

### Step 2: file one task per item, and resolve any tracking ambiguity before spawning anyone

Each item needs a self-contained task file so the spawned agent can work from it cold. In this
kit that means one [`.tasks/`](../../../.tasks/) file per item, authored to the `new-task` bar
(honest `touched_files`, a real `parent`, resolved `depends_on`, a mechanically-verifiable
acceptance command). If the target repo uses a different convention, follow that convention
exactly instead.

Then check whether those task files are **tracked by git** (`git status` after creating them, or
inspect `.gitignore`). If they are untracked, a `git worktree add` checkout will not include
them, which is exactly the ambiguity that caused three incompatible agent behaviors in the
incident above. Decide now, once, how every spawned agent should handle this (for example: "the
task file is untracked, so it will not exist in your worktree, recreate it verbatim from the
content below and do not touch the main checkout's copy of it at all"), and bake that decision
into every agent's prompt. Do not leave it to each agent's judgment, they will not converge on
the same answer. In this kit the `.tasks/` files are normally committed, so this trap is usually
absent here, but confirm rather than assume.

### Step 3: dispatch one isolated agent per item, with hardened prompts

Dispatch one agent per item, each in its own isolated git worktree, all started together so they
run in parallel. The concrete tool mechanics are harness-specific, see
[Running this in Claude Code](#running-this-in-claude-code). Every prompt must include, in
substance:

1. **The scope**: exactly what to change, in which file(s), and what "done" (acceptance criteria)
   looks like, self-contained, since the agent starts cold with no memory of this conversation.
2. **The sandbox rule, stated explicitly, not implied by worktree isolation alone**: "Never read,
   write, or run any command against any path outside your assigned worktree, for any reason, not
   to sync your changes, not to work around a missing file, not to check something in the main
   checkout. If you believe you need to reach outside your worktree for any reason, stop and
   report that as a blocker instead of doing it." Worktree isolation is a starting-state
   guarantee, not a runtime sandbox. Nothing stops a shell call from going wherever it wants
   unless you say so directly.
3. **The untracked-file resolution from Step 2**, if applicable, spelled out concretely rather
   than left as a judgment call.
4. **An instruction not to commit**: leave all changes uncommitted in the worktree for review,
   unless the user has explicitly said otherwise.
5. **A request for an honest blocker report** over a confident-sounding improvisation: "If
   something about this task's premise turns out to be wrong, or you hit a blocker you are not
   sure how to resolve within your own worktree, stop and report it clearly rather than guessing."

### Step 4: while waiting, do not poll

Background agents notify you on completion. Do not sleep-loop or repeatedly check in. Continue
other work, or wait, until notifications arrive.

### Step 5: when a blocker looks like a false alarm, verify before dismissing it

An agent may report being blocked by something that looks like a conflict but is actually
unrelated (in the incident above, an agent found unrelated pre-existing uncommitted work in the
main checkout and assumed it was someone else's fix for its own task). Do not just take its word
that something is or is not relevant. Check the actual content yourself (what does the diff
actually touch, does it overlap the agent's own `touched_files`) before either dismissing the
concern or accepting it as a real conflict. If it is a false alarm, resume the agent with a
precise explanation of what it actually found and confirmation to proceed.

### Step 6: the mandatory verification pass, do this for every single agent, no exceptions

This is the step that actually matters. For each completed agent, before treating any of its work
as done, run [`verifier-agent`](../verifier-agent/SKILL.md) against that worktree. Independence is
the point, and it is stated once, here: run verifier-agent yourself, or dispatch a separate agent
to run it, never the agent whose own work is being verified.

verifier-agent runs the task's declared verification commands, checks the acceptance criteria
against named evidence, and, when a spec is supplied, composes `spec-conformance` for the contract
half, then returns `pass`, `fail`, or `blocked` with the evidence attached. What that verdict means
for the batch:

- **`pass`**: the criteria, commands, and (if applicable) spec conformance all check out. Move on
  to the batch-specific checks below before calling the item mergeable, a pass is evidence the
  implementation holds up, not a substitute for the checks that follow.
- **`fail`**: the item is not done. Do not reconcile it. Carry the blocking reasons and findings
  into your consolidated report so whoever owns the batch knows exactly what is still wrong.
- **`blocked`**: verifier-agent could not answer the question at all, an unapproved spec or a
  missing/unrunnable command, not a pass. Treat it as unresolved, same as you would treat not
  having verified at all: do not reconcile, and fix whatever made verification unrunnable before
  trying again. Neither this skill nor `verifier-agent` has yet exercised this branch on real batch
  work, so give a `blocked` verdict extra scrutiny the first few times it actually comes up.

verifier-agent verifies one implementation against its own spec and acceptance criteria; it has no
notion of a batch. The following checks are specific to dispatching several agents at once and are
not inside verifier-agent's scope, so they remain yours to run, for every agent, on top of its
verdict:

1. **Diff its worktree against its base commit** (`git diff` inside the worktree, or against the
   commit `git worktree list` shows as its base). Confirm the diff touches only the files the task
   scoped it to. Anything extra is a finding, not a bonus, investigate it, do not assume it is
   helpful just because tests pass. (In the incident, an "extra" test initially looked like
   fabrication and was nearly deleted for that reason, it turned out to be a real,
   previously-undiscovered bug fix the agent found opportunistically and never disclosed.
   Investigate anything unexpected against real ground truth, git history, the filesystem,
   actually running the code, before concluding either "fabricated" or "legitimate".)
2. **Check any task-file or changelog bookkeeping the agent claims to have done actually matches
   what it claims.** Open the file. Confirm the status field, every checkbox, and the changelog
   entry are actually present and actually correct, not just that a file got moved to the right
   directory.
3. **Treat "I recovered from an error" or "I reconstructed lost work" in an agent's summary as a
   high-scrutiny flag, not a reassurance.** This is exactly the situation where an agent is most
   likely to have introduced something undisclosed while trying to fix its own mistake. Give that
   diff extra attention, line by line if it is not large.
4. **Check for repo-specific landmines that would not be any single agent's fault**, especially
   around binary assets, LFS tracking, or generated files. If multiple independently-created
   worktrees show the identical unexpected diff on the same path, that is a systemic or tooling
   issue, not something any agent did. Investigate before assuming corruption (compare real byte
   sizes and content, not just `git status`'s verdict) and flag it clearly rather than either
   panicking or ignoring it.

### Step 7: report a consolidated, verified summary, do not auto-merge

Present, per item: what changed, what you personally verified (tests you ran yourself, diffs you
checked), and anything you found and corrected during verification. Do not commit or merge
anything automatically. Landing the verified worktrees into the main working tree is a separate,
deliberate step, see [`reconcile-worktrees`](../reconcile-worktrees/SKILL.md).

## Running this in Claude Code

This section is Claude Code specific. Other harnesses provide the same capability (parallel,
isolated, resumable agents) through their own mechanisms; the doctrine above is what matters, the
tool names below are the local implementation.

- **Dispatch (Step 3):** use the `Agent` tool with `isolation: "worktree"` and
  `run_in_background: true`, one call per item, all in the same message so they run in parallel.
  Each `Agent` call gets its own worktree; the `prompt` carries the hardened prompt from Step 3.
- **Do not poll (Step 4):** background agents re-invoke you on completion. There is no need to
  check in, just continue or wait for the notification.
- **Resume a false-alarm blocker (Step 5):** use `SendMessage` addressed to the agent's id (or
  name) to continue that specific agent with its context intact, rather than starting a fresh one.
- **Verification (Step 6):** dispatch `verifier-agent` (a separate `Agent` call from the one that
  did the work) or run its procedure yourself, then run the batch-specific checks with the `Bash`
  tool inside each worktree path. See Step 6 for the independence rule.

## The throughline

Parallel background agents are genuinely useful for independent, well-scoped work. They are not
trustworthy by default for anything where correctness matters and you are not watching closely.
Their self-reports are optimistic by construction, not because they are being dishonest, but
because they do not have the outside view needed to catch their own scope creep or their own
recovery-attempt side effects. The fix is not "do not delegate", it is "delegate, then verify
against reality before you believe it".
