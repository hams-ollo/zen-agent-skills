---
id: bug-0034
title: fix-batch tells you to record the dispatch commit and never to check the worktree was cut from it, which has now cost two batches
type: bug
status: done
priority: P1
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [chore-0040]
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-08-18
---

## Problem

[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) Step 3 says to record the dispatch sha first,
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

**A third occurrence, 2026-08-18, and it falsifies the obvious fix.** A six-agent wave dispatched
from `developer` at `b950c9e` was checked by hand from the main checkout immediately after dispatch.
The check reported five of six on the dispatch commit and one wrong. **That was wrong.** At least
three of the six later reported in their own blockers field that they had been cut at `a07286b` and
had fast-forwarded, including two the check had called correct. The check had raced the agents' own
recovery: an agent whose first instruction is to verify its base repairs itself within seconds, so
`git worktree list` a moment later reports the repaired state and says nothing about the cut.

That matters for the shape of the fix. **A post-dispatch check is not sufficient**, because its
result depends on who ran first, and its failure mode is the worst available: it reports clean while
the batch was mis-cut. It is still worth having, since it catches the slow agents and costs one
command, but it must be written as a lower bound rather than a verdict, and the durable answer is to
create the worktrees at an explicit sha so there is nothing to detect.

The skill already documents the mechanism that avoids it, under "Dispatch, batch against a
*different* repository": create the worktrees yourself at an explicit sha. It is filed there as a
cross-repository special case, so nobody reaches it for a same-repo batch, which is the common one.


**A second stale base, at the other end of the same run.** Added 2026-08-20 by the author's decision
to fold it here rather than file it separately, because it is the same family: a base that lags its
target lies to you, and the lie is invisible locally.

A wave branch cut from the last merge commit rather than from the target's tip cannot see any file
authored after the cut. So `python scripts/run-checks.py` passes on the branch while the merge result
fails, and the failure lands as a red CI build after the pull request is open. Twice now:

```text
wave 2  chore-0044 filed on developer after the cut, links to bug-0035, which the wave moved
        to done/. Branch green, pull_request run red on all six cells.
wave 4  bug-0037 filed on developer after the cut, links to chore-0046, same shape. Plus a real
        conflict in .tasks/.scaffold.json, both branches having bumped id_high_water.
```

Wave 4 is the sharper evidence, because its `pull_request` CI run never fired at all, so the only
signal available was the branch-alone run, which is green by construction in this case. The defect was
found by reproducing the merge locally. A check that only exists in CI is not a check when the trigger
can skip.

## Scope

**In scope:** a pre-dispatch verification step in Step 3, and the recovery when it fails.

- Make explicit-sha worktree creation the **primary** path for a same-repo batch, not the
  cross-repository special case it is filed as today. It is the only answer that does not race.
- Keep a post-dispatch comparison of every worktree's commit against the recorded sha, and write it
  as a lower bound rather than a verdict: a clean result does not prove the batch was cut correctly,
  because a fast agent repairs itself before the check runs. Say that in the skill, so a future
  reader does not draw the conclusion this session drew and had to retract.
- State the recovery for an already-running agent: `git merge --ff-only <dispatch-sha>`, valid only
  when the old base is a strict ancestor (`git merge-base --is-ancestor`) and the branch has no
  commits of its own, with `git reset --hard` named as the thing not to reach for by default because
  it discards uncommitted work.
- Say that the agent must disclose anything it read at the old base as possibly stale, because a
  file identical across both commits is fine and one the fast-forward touched is not.
- Point at the explicit-sha worktree creation the skill already documents as the durable fix, and
  stop filing it as cross-repository-only.
- In [`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md), state the branch rule
  for the other end of the run: cut the landing branch from the target's current tip, and merge the
  target in before opening the pull request rather than after CI objects. Its Step 1 already computes
  each worktree's real base and flags a mismatch, so this is the same check applied to the branch the
  worktrees land on, which that step does not currently mention.

**Out of scope:**

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

## Decisions

- **Rejected: keeping `isolation: "worktree"` as the documented same-repo dispatch path with the
  post-dispatch check bolted on.** That is the shape the 2026-08-18 `b950c9e` wave falsified. The
  check races agent self-repair, so it can only ever lower-bound the damage. The harness bullet now
  names explicit-sha creation as the same-repo path and demotes `isolation: "worktree"` to the
  convenience path with its failure record stated.
- **Rejected: adding a base check to the hardened prompt.** Explicitly out of scope, and it would
  put the same diagnosis in N places, which is what this task moves out of the prompts. The
  honest-blocker instruction (item 6) is left untouched and is now cited by the evidence list as
  working but in the wrong place.
- **Premise partly false: the `Out of scope` bullet "Any change to `reconcile-worktrees`" contradicts
  the newer in-scope bullet and acceptance criterion for that same file.** The 2026-08-20 fold-in
  added the branch rule without retiring the older exclusion. Resolved in favour of the in-scope
  bullet and the acceptance criteria, which are the mechanically checked ones.
- **Seam left open: no test.** Both changes are prose in skill bodies with no executable surface. A
  test here could only pin wording, which `chore-0040` and this task both demonstrate is churn.
  `validate-skills.py` and the docs link check already cover the mechanical properties (link
  resolution, frontmatter, lint), and they run inside the acceptance command.
- **Seam left open: the branch rule's merge command in `reconcile-worktrees` names `origin` and a
  `<target-branch>` placeholder rather than the kit's `developer`.** The skill is portable and its
  Conventions section defers to the target repo, so the incident evidence is described without
  naming this kit's task ids or its acceptance command.

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

- [x] Step 3 makes explicit-sha worktree creation the primary path for a same-repo batch.
- [x] Step 3 names the post-dispatch check against the recorded sha, with the command, and states
      that a clean result is a lower bound rather than proof, because it races agent self-repair.
- [x] The recovery names `git merge --ff-only`, both of its preconditions, and why `git reset --hard`
      is not the default.
- [x] The staleness disclosure an affected agent owes is stated.
- [x] The explicit-sha worktree creation is reachable from the same-repo path, not only from the
      cross-repository one.
- [x] Both dated worktree incidents are cited, so the instruction carries its evidence rather than
      reading as caution.
- [x] `reconcile-worktrees` states the branch rule, citing the two waves where a branch cut from a
      stale base passed locally and failed on merge.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
