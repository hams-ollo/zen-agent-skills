---
id: bug-0034
title: fix-batch tells you to record the dispatch commit and never to check the worktree was cut from it, which has now cost two batches
type: bug
status: open
priority: P1
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [chore-0040]
touched_files:
  - .agents/skills/fix-batch/SKILL.md
created: 2026-08-18
---

## Problem

[`fix-batch`](../.agents/skills/fix-batch/SKILL.md) Step 3 says to record the dispatch sha first,
and gives the right reason: it is the one piece of state that cannot be recovered afterwards, since
`git worktree list` reports current `HEAD` rather than the creation point. It never says to check
that the worktrees were actually cut from it. That check is the whole value of having recorded it,
and it is missing.

**Measured twice.** On 2026-08-05 a four-agent wave had every worktree cut from `main`, four commits
behind `developer`, which silently excluded the previous wave's output. On 2026-08-18 a six-agent
batch dispatched from `developer` at `e492b10` had **all six** worktrees cut from `origin/main`
(`a07286b`), where not one of the six task files existed:

```text
git worktree list        # every agent worktree at a07286b, not e492b10
git rev-parse origin/main -> a07286b
```

Four of the six agents diagnosed it themselves and fast-forwarded, which is the hardened prompt's
honest-blocker instruction working. That is the wrong place for the fix. It costs every agent a
detour through the same diagnosis, it produces four independent recoveries by two different methods
(`git merge --ff-only` and `git reset --hard`, which are not equivalent when a branch has its own
commits), and it fails silently for any agent that does not notice: at the wrong base the task file
is simply absent, which reads as a bad dispatch rather than a wrong tree.

The skill already documents the mechanism that avoids it, under "Dispatch, batch against a
*different* repository": create the worktrees yourself at an explicit sha. It is filed there as a
cross-repository special case, so nobody reaches it for a same-repo batch, which is the common one.

## Scope

**In scope:** a pre-dispatch verification step in Step 3, and the recovery when it fails.

- After dispatching and **before trusting any agent**, compare every worktree's commit against the
  recorded dispatch sha, and say what to do when they differ.
- State the recovery for an already-running agent: `git merge --ff-only <dispatch-sha>`, valid only
  when the old base is a strict ancestor (`git merge-base --is-ancestor`) and the branch has no
  commits of its own, with `git reset --hard` named as the thing not to reach for by default because
  it discards uncommitted work.
- Say that the agent must disclose anything it read at the old base as possibly stale, because a
  file identical across both commits is fine and one the fast-forward touched is not.
- Point at the explicit-sha worktree creation the skill already documents as the durable fix, and
  stop filing it as cross-repository-only.

**Out of scope:**

- Any change to `reconcile-worktrees`. Its Step 1 already computes each worktree's real base and
  says to flag a mismatch, which is why this landed safely; the gap is at dispatch, not at landing.
- The hardened prompt in Step 3. The honest-blocker instruction worked and should not be weakened by
  adding a base check to every agent's prompt, which would put the same diagnosis in N places.
- Diagnosing why `isolation: "worktree"` ignores the requested base. That is harness behaviour, not
  this repository's, and the skill's job is to be correct in spite of it.
- The delegate report contract. A base mismatch is an environment fault, not a field an agent owes.

## Implementation notes

Put the check where the sha is recorded, not in a new step, so the record and its use sit together
and neither reads as optional.

Give the command rather than describing it, since this is a narrow-bridge instruction rather than a
judgment call:

```
git worktree list
```

and compare each line's commit against the dispatch sha. Two lines of prose about why
`git worktree list`'s commit is the current `HEAD` already exist in Step 3 and in
`reconcile-worktrees` Step 1; reference rather than restate.

Be explicit that the fast-forward is conditional. Both preconditions matter and one agent in the
2026-08-18 batch checked them before acting while another used `git reset --hard` without saying it
had checked. State them as a pair.

## Risks and rollback

One skill body, prose only, no procedure removed. It does not meet the more-than-one-module rule and
this section is kept only because the instruction it adds is one an agent will follow literally: a
wrong recovery command here destroys uncommitted work in a worktree, which is the one place in this
kit where the only copy of an agent's output lives. Order the two preconditions before the command,
not after it.

`depends_on: [chore-0040]` is a file collision, not a logical one. That task edits `fix-batch`'s
spine statement and its `test-author` pointer in the same body.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Step 3 names the post-dispatch check against the recorded sha, with the command, before any
      agent's output is trusted.
- [ ] The recovery names `git merge --ff-only`, both of its preconditions, and why `git reset --hard`
      is not the default.
- [ ] The staleness disclosure an affected agent owes is stated.
- [ ] The explicit-sha worktree creation is reachable from the same-repo path, not only from the
      cross-repository one.
- [ ] Both dated incidents are cited, so the instruction carries its evidence rather than reading as
      caution.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
