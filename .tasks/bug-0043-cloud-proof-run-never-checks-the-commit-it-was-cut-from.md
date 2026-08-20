---
id: bug-0043
title: The cloud proof run states its base precondition only to the person staging it, so a session cut from the wrong commit reports a confident wrong answer
type: bug
status: open
priority: P1
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-008", "S-017", "S-018"]
touched_files:
  - docs/spec/cloud-executable.runbook.md
  - .agents/rules/autonomy.md
created: 2026-08-20
---

## Problem

[`cloud-executable.runbook.md`](../docs/spec/cloud-executable.runbook.md) is careful about the
commit a proof session runs on. Its "Before you start" table checks
`git merge-base --is-ancestor 7703632 origin/developer`, step 3 of "Start the session" says
**"Branch: `developer`. Not `main`"** and says why, and the `S-008` section states the condition as a
commit rather than a branch: *"On any commit without `7703632` the hook is still the broken version
and its silence would say nothing about the fix."*

**Every one of those safeguards is addressed to the person staging the run. None of it reaches the
agent.** Both paste-ready prompts operate under `autonomy.md` and neither asks the session to check
what it was cut from. The `S-008` prompt comes closest, asking for `git rev-parse HEAD` as
observation 4, but it asks for the sha without asking the one question the sha exists to answer, and
nothing downstream compares it to anything.

So when staging goes wrong the run does not fail. It proceeds, and it produces a report that is
internally consistent, fully evidenced, and wrong about the repository.

**Measured 2026-08-20, on a run of [`bug-0020`](bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md)
staged as the `S-017` to `S-019` proof.** The session was given branch
`claude/bug-0020-unknown-remedy-lcqb52`, cut from `origin/main` at `a07286b`:

```text
git rev-parse origin/main       -> a07286b3cff41f01f1c55189e92d4d65a097ee94
git rev-parse origin/developer  -> bc2726c0ddfee421b303563ee1f9c09f42384ef8
git diff --shortstat origin/main origin/developer
    99 files changed, 11296 insertions(+), 278 deletions(-)
```

All three of the task's `touched_files` differed across that gap (`scripts/install.py` by 218 lines,
`tests/test_install.py` by 482, `docs/INSTALL.md` by 40). The session implemented and validated the
task against `main`'s copies while its pull request targeted `developer`, and **GitHub reported the
pull request mergeable and clean throughout**, because the one function the change edits happens to
be byte-identical on both branches. Nothing in the run surfaced the gap.

The cost was a false finding in a shipped report. The session reported the reachability hook as
counting any `SKILL.md`, proposed a name-based fix, and offered it as new. That is
[`bug-0021`](done/bug-0021-reachability-counts-any-skill-not-a-kit-skill.md), which had already been
found, fixed in exactly that way, closed, and merged to `developer` before the run began. The session
was reading superseded code and reasoning correctly about it.

**The reading table gives the wrong answer for this case, and that is the sharpest part.** The
`S-008` section's "Reading the result" table maps observation 1 `no` with observation 2 `silent` to
*"The logic is still wrong in that environment. The fix did not hold."* That is precisely what this
run would have produced, and the conclusion would have been false in both halves: the logic is right
and the fix held. There is no row, and no preceding gate, for the session having been on a commit
without `7703632`. A person following the table lands on a hook bug that does not exist.

**It happened again while this task was being filed, in the sibling shape.** The branch carrying
this file was cut from `origin/developer` at `bc2726c`, correctly and deliberately. `chore-0051`
merged to `developer` twenty minutes later at `bc4f901`, moving its own task file into `done/`. This
file's link to it still resolved on the branch, so `python scripts/run-checks.py` passed locally and
`python .tasks/validate.py --strict` reported `0 error(s)`, and the merge result failed on all six CI
cells:

```text
ERROR .tasks/bug-0043-...md: relative link does not resolve:
      chore-0051-cloud-proof-scenarios-name-a-task-that-is-already-closed.md
Checked 143 task files: 1 error(s), 0 warning(s).
```

That exact shape is `bug-0034`'s second half, which is `done`: *"a wave branch cut from the last merge
commit rather than from the target's tip cannot see any file authored after the cut, so
`run-checks.py` passes on the branch while the merge result fails."* Its fix is a rule in
[`reconcile-worktrees`](../.agents/skills/reconcile-worktrees/SKILL.md) telling the batch's landing
step to merge the target in before opening the pull request. A lone cloud session never reads that
skill.

So the two occurrences an hour apart are the same sentence from opposite ends: **the rules for this
exist, they are correct, and not one of them is addressed to a single unattended session.** That is
the finding, and it is why the fix belongs in `autonomy.md` and in the prompts rather than in another
skill body.

**Why no existing rule covers it.**
[`bug-0034`](done/bug-0034-fix-batch-never-checks-the-worktree-base.md) is the same family and fixed
the two neighbouring cases: worktrees mis-cut at dispatch, and a landing branch cut from a stale tip.
It put a base check in the dispatcher's hands and **explicitly declined** to put one in the
per-agent prompt, on the ground that it would place the same diagnosis in N places. That reasoning is
right for a batch and does not transfer here: a cloud proof run has one agent and no dispatcher, so
there is no other end to put the check on, and the case falls between the two owners. Note also that
the mis-cut base in `bug-0034`'s 2026-08-18 batch was `a07286b`, the same commit this run was cut
from.

`autonomy.md` has no rule about the base at all. `A4` and `A6` govern what an agent may claim from
evidence it gathered; nothing governs whether the tree it gathered that evidence from is the one the
work targets.

## Scope

**In scope:** make the base a checked precondition of the run rather than an instruction to whoever
starts it.

- **Put the check in both prompts.** A first step that runs
  `git merge-base --is-ancestor <required-commit> HEAD` (and, for a task run, compares `HEAD` against
  the branch the pull request will target), reports the result in the pull request body, and stops
  with a blocker when it fails rather than proceeding. The command already exists in the runbook's
  prose; this moves it to where it executes.
- **Fix the "Reading the result" table** so the base is ruled out before any row is read. Either a
  gate sentence above the table or an added column; the requirement is that `no` plus `silent` can no
  longer be read as "the fix did not hold" while the base is unverified.
- **Add a rule to [`autonomy.md`](../.agents/rules/autonomy.md)**: an unattended agent verifies the
  commit it is working from against the branch its work targets before trusting what it reads, and
  discloses the result. It is citable now, which is the bar that module sets, and `A8`'s own honest
  qualification asks for exactly this kind of confirmation from a real unattended run.
- **Record this run** in the runbook's "Runs performed" table, with the cause, since that table
  currently has one row and this is the second occurrence of a startup `no` from a different cause.

**Out of scope:**

- **[`fix-batch`](../.agents/skills/fix-batch/SKILL.md) and
  [`reconcile-worktrees`](../.agents/skills/reconcile-worktrees/SKILL.md).** `bug-0034` owns those and
  its decisions stand, including its refusal to put a base check in a batch dispatch prompt. Do not
  reopen that.
- **How the cloud environment picks the branch it cuts.** That is harness behavior, not this
  repository's, and the fix here is to be correct in spite of it. This is `bug-0034`'s stance on the
  same question, restated for the same reason.
- **A gate in [`run-checks.py`](../scripts/run-checks.py) or CI.** It needs remote refs, which the
  acceptance command deliberately does not, and `bug-0034` already recorded that a check living only
  in CI is not a check when the trigger can skip.
- **Re-running the proof.** A person starts it, and
  [`chore-0051`](done/chore-0051-cloud-proof-scenarios-name-a-task-that-is-already-closed.md) has
  already repointed it at an open task.
- **The `bug-0020` change itself.** It is correct, it has been rebased onto `developer` and
  re-validated there, and the defect it fixes is genuinely unfixed on `developer`.

## Implementation notes

**`chore-0051` landed in this runbook on 2026-08-20 and the regions do not collide.** It reworded
`S-017` and `S-018`'s **Given** clauses, the preconditions table, and the `S-017` prompt's task; this
one changes what both prompts *check*, the `S-008` reading table, and the runs table. Every premise
above was re-read against the post-`chore-0051` runbook and all of them still hold: the precondition
is still stated only to the person, neither prompt carries a base check, and the reading table is
unchanged.

**Prefer stating the required commit as a commit, not a branch.** The runbook already made this
choice once, after naming `feat/epic-e-delegated-execution` in a section that outlived the branch, and
records why. A prompt that says "check you are on `developer`" inherits the bug the existing prose
already avoided.

**The failure has to be a blocker, not a note.** A prompt that asks the agent to report its base
without telling it to stop produces a run that discloses the problem in a field nobody reads until
after the work is done, which is this run exactly: the gap was found only because a later question
sent the session back to the remote.

**Keep the autonomy rule about reading, not about repair.** What went wrong was trusting a tree, not
failing to fix one. The recovery commands are `bug-0034`'s and are already written down there; cite
rather than restate, per the module's own convention.

## Decisions

- **A premise worth recording: the runbook was not wrong, it was unreachable.** The instinct on
  finding this was to add the missing precondition, and the precondition is already there and is
  well argued. The defect is the audience, so a fix that adds more prose to the person-facing sections
  is no fix at all.
- **Rejected: a `run-checks.py` gate.** Named above with its reason; recorded here because it is the
  first thing a reader will propose.
- **A seam left open deliberately:** nothing here makes a cloud session able to detect that its
  branch was cut wrongly *before* it reads anything, because the check needs `origin/developer`
  fetched and the session may start offline. The rule and the prompts both run the check after
  startup, which is late enough to have read `AGENTS.md` and early enough to have read nothing else.

## Risks and rollback

Touches two modules (a spec-adjacent runbook and the swappable autonomy lens), so it clears the
one-module bar. Both changes are prose, reversible by reverting one commit, and neither changes a
persisted format. The one real risk is the autonomy rule: it ships to adopters, and a rule that tells
every unattended agent to run a git command is wrong for an adopter whose agents do not use git.
State it as conditional on the run having a base to check, in the shape the module already uses for
`A8`'s qualification.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Both paste-ready prompts in the runbook carry a base check as their first step, naming a
      commit rather than a branch, and instruct the session to stop and report a blocker when it
      fails.
- [ ] The `S-008` "Reading the result" table cannot be read to blame the hook while the base is
      unverified: a base gate precedes it, or the table carries the base as an explicit dimension.
- [ ] `autonomy.md` carries a base-verification rule with a citation to this run, following the
      module's stated gate that a rule which cannot be cited does not belong in it.
- [ ] The "Runs performed" table has a row for the 2026-08-20 run recording the commit, the `no`, and
      the base as the cause.
- [ ] `python .tasks/validate.py --strict` passes, including every relative link in this file.
- [ ] No change to `fix-batch`, `reconcile-worktrees`, `run-checks.py`, or any `.github/workflows/`
      file, which are all named out of scope above.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
