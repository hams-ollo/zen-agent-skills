---
name: fix-batch
description: >-
  Delegate a batch of independent, already-scoped task files (bugs, chores, small features) to
  parallel isolated agents, each sandboxed in its own git worktree, with a mandatory independent
  verification pass before anything is treated as mergeable. Use this whenever asked to "fix these
  bugs", "work through the backlog", "spin up agents to fix X, Y, Z", or "parallelize these
  fixes", especially when there are 2 or more distinct, independently-fixable items and the user
  wants them actioned rather than just discussed. It is the parallel-execution step of the kit
  spine: new-task authors the task files, fix-batch dispatches them, verifier-agent proves them,
  reconcile-worktrees lands them. Do not use it for a single fix (just do it directly) or for
  changes that are inherently sequential or interdependent (one agent's output feeds the next's
  input), since worktree
  isolation assumes the items do not need to see each other's work in progress.
license: MIT
---

# fix-batch

Spawn parallel worktree-isolated agents to work a batch of independent task files, then verify
every one of them yourself before calling any of it done. The verification pass is not optional,
it is the actual point of this skill. Parallel delegation without it is just parallel delegation.
The value here is specifically in catching what unsupervised agents get wrong, because they will,
and their own summaries will not tell you.

This is the parallel-execution step of the kit spine: [`new-task`](../new-task/SKILL.md) authors
the atomic task files, `fix-batch` dispatches them to isolated agents,
[`test-author`](../test-author/SKILL.md) and [`verifier-agent`](../verifier-agent/SKILL.md) prove
each result at Step 6, and [`reconcile-worktrees`](../reconcile-worktrees/SKILL.md) lands the
verified ones into the main working tree. Read the target repository's `AGENTS.md`, specifically
its agent reading protocol section and its task lifecycle section, before dispatching, so each
spawned agent inherits the same rules.

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

### Step 2: resolve everything git will not carry into a worktree, before spawning anyone

`git worktree add` gives an agent the **tracked** files and nothing else. Everything the work
depends on that git does not track has to be decided once, here, and written into every prompt.
Two populations, and the second is the one that actually stops batches.

**The task files.** Each item needs a self-contained task file so the spawned agent can work from
it cold. In this kit that means one `.tasks/` file per item, authored to the `new-task` bar
(honest `touched_files`, a real `parent`, resolved `depends_on`, a mechanically-verifiable
acceptance command). If the target repo uses a different convention, follow that convention
exactly instead.

Then check whether those task files are **committed**, not merely tracked. A worktree checks out a
**commit**, so a task file that is staged with `git add` but not committed is as absent from the
worktree as one that is gitignored. `git status` showing it as a staged addition looks like success
and is not. Commit the task files, then take the dispatch sha from *after* that commit. If they are
untracked by policy, a `git worktree add` checkout will not include them either, which is exactly
the ambiguity that caused three incompatible agent behaviors in the incident above. Decide now, once, how every spawned agent should handle this (for example: "the
task file is untracked, so it will not exist in your worktree, recreate it verbatim from the
content below and do not touch the main checkout's copy of it at all"), and bake that decision
into every agent's prompt. Do not leave it to each agent's judgment, they will not converge on
the same answer. In this kit the `.tasks/` files are normally committed, so this trap is usually
absent here, but confirm rather than assume.

**The build environment, which is gitignored by definition.** `node_modules/`, `.venv/`,
`target/`, `.env`, build caches, generated code, and downloaded fixtures are all absent from a
fresh worktree because they are all correctly gitignored. So the task's acceptance command, the
one thing that proves the item is done, cannot run there. Left unresolved this does not fail
loudly: `verifier-agent` returns `blocked` for a runner it cannot find, and Step 6 says a
`blocked` item does not get reconciled, so **every item in the batch stalls at once and none of
them look broken**. On a documentation-only repo like this kit the trap is absent, which is
exactly why it is easy to ship a batch workflow that has never met it.

Before dispatching, **actually run the acceptance command in a throwaway worktree.** Not read it,
run it. This costs one worktree and catches two different failures at once: what the command needs
that git is not carrying, and whether the command as written works at all. On a real batch this
step caught a command that was wrong in a way no amount of reading would have shown, `uv run pytest`
versus `uv run python -m pytest`, where the console script does not put the repo root on `sys.path`
and every import fails. Dispatched unchecked, that is three agents hitting the same wall and
reporting three confusing blockers.

Then pick one answer for the whole batch and put it in every prompt:

- **Install per worktree**: correct and hermetic. Measure the cost before assuming it is too high,
  because it varies by orders of magnitude across toolchains. A measured `uv sync` on a real Python
  project took 2 seconds and 52MB per worktree, which makes this choice free; the same decision
  against a cold `npm ci` is a different conversation. Tell the agent the exact command and that
  the install is expected, not a sign the task is wrong.
- **Share the store**: point the agent at a shared cache or package store where the toolchain
  supports it. Cheaper, but no longer fully isolated, so say so.
- **Copy in what git cannot carry**: for a small set of files, usually `.env` or a fixture,
  place them yourself before dispatching rather than asking the agent to reach outside its
  worktree, which rule 2 in Step 3 forbids for good reason.
- **Do not use worktree isolation for this batch**: a legitimate answer when the environment is
  too expensive or too stateful to replicate. Run the items sequentially in one checkout instead.

Never leave this to the agent. An agent that finds its test command broken and has been told not
to leave its worktree will either report a blocker (the good case, and it costs you a round trip)
or improvise something creative (the bad case).

### Step 3: dispatch one isolated agent per item, with hardened prompts

Dispatch one agent per item, each in its own isolated git worktree, all started together so they
run in parallel. The concrete tool mechanics are harness-specific, see
[Running this in Claude Code](#running-this-in-claude-code).

**Record the dispatch sha first** (`git rev-parse HEAD`), before any worktree is created. It is the
base every worktree's changes should be read against, and it is the one piece of state that cannot
be recovered afterwards: `git worktree list` reports current `HEAD`, not the creation point.

Keep the batch to a size you can actually verify. Every item costs a full verification pass in
Step 6, and that is your time, not the agents'. If a batch is large enough that verification will
be skimmed, it is too large, and skimmed verification is the exact failure this skill exists to
prevent. Dispatch in waves instead.

Every prompt must include, in substance:

1. **The scope**: exactly what to change, in which file(s), and what "done" (acceptance criteria)
   looks like, self-contained, since the agent starts cold with no memory of this conversation.
2. **The sandbox rule, stated explicitly, not implied by worktree isolation alone**: "Never read,
   write, or run any command against any path outside your assigned worktree, for any reason, not
   to sync your changes, not to work around a missing file, not to check something in the main
   checkout. If you believe you need to reach outside your worktree for any reason, stop and
   report that as a blocker instead of doing it." Worktree isolation is a starting-state
   guarantee, not a runtime sandbox. Nothing stops a shell call from going wherever it wants
   unless you say so directly.
3. **Both Step 2 resolutions**, spelled out concretely rather than left as judgment calls: how to
   handle the task file if it is untracked, and how to get the build environment the acceptance
   command needs.
4. **An instruction not to commit**: leave all changes uncommitted in the worktree for review,
   unless the user has explicitly said otherwise. Add: do not stage them either. Staged changes
   are invisible to a bare `git diff`, which is what reconciliation reads, so staging is a quiet
   way to lose work at the far end.
5. **How to produce the test the acceptance command runs**, when the task's criteria name a test
   that does not exist yet. Point the agent at [`test-author`](../test-author/SKILL.md): derive the
   test from the scenario it protects, tag it with that `S-NNN` id, and pick the layer and oracle
   through the [`test-quality`](../test-quality/SKILL.md) lens. **Say which of that skill's two
   modes the agent is in**, because the mode is not obvious from where it is standing: most
   dispatched agents hold a single bug or chore task and no approved spec, and `test-author`'s
   acceptance mode requires one. That case is its **characterization** mode, which is exempt from
   the spec gates and pins the code's current observable behavior instead. Only a task that
   actually carries an approved spec and `S-NNN` ids is the acceptance-mode case. Without this the
   agent writes whatever test makes its own change pass, which is the failure mode the whole
   verification stage exists to catch, arriving one step earlier than the stage that would catch
   it.
6. **A request for an honest blocker report** over a confident-sounding improvisation: "If
   something about this task's premise turns out to be wrong, or you hit a blocker you are not
   sure how to resolve within your own worktree, stop and report it clearly rather than guessing."
   This is not a formality. On a real batch, two of three agents reported that the task file's
   premise was factually wrong about the code (a function that did not contain the logic the task
   attributed to it, and a regex that did not handle a case the task asserted it handled). Both
   reported it and tested what was actually there instead of forcing a test onto a premise that did
   not hold. An agent that quietly "makes it work" hides a defect in your task authoring.
7. **The report contract, quoted into the prompt rather than summarized.** Give the agent the exact
   field list from [the delegate report contract](#the-delegate-report-contract) and tell it plainly
   that a missing field blocks acceptance. An agent that learns the required shape only when you
   reject its report has already lost the context that made the fields cheap to produce, and
   reconstructing them afterwards costs a round trip you did not need to spend.
8. **An instruction to record its decisions in its own task file** before it finishes, and to leave
   that file otherwise alone. The admissible entry kinds and the exclusion list are defined once, in
   the target repository's task template (in this kit, the `## Decisions` section of
   `.tasks/_TEMPLATE.md`). Point the agent at that definition instead of restating it, and tell it
   to delete the section when it has nothing of those kinds rather than pad it. This is the
   **exception that proves** the closeout-bookkeeping rule below, not a weakening of it: that rule
   holds because the `done/` move, `CHANGELOG.md`, and `ROADMAP.md` are the *same* files for every
   item in the batch, so N agents editing them in N worktrees collide by construction. An agent's
   own task file is the one file in the batch that exactly one agent owns, so no second agent can
   conflict with it. Everything shared still stays out. This item is also the semantic counterpart
   to [the delegate report contract](#the-delegate-report-contract), which asks what is checkably
   true about the change while this asks what the agent learned that the change does not show. It is
   not a tenth report field.

**Keep closeout bookkeeping out of every prompt.** Do not ask agents to move their own task file to
`done/`, update the changelog, or tick the roadmap. Those touch the same one or two files for every
item in the batch, so N agents editing them in N worktrees is a guaranteed conflict at
reconciliation, and it is the single easiest collision to avoid: you do it once, centrally, in Step
7 or during reconciliation. Bookkeeping is also exactly where unsupervised agents were caught
misreporting in the incident above, so doing it yourself removes the need to audit N copies of it.

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

**Start with the report, before you run anything.** Check it against
[the delegate report contract](#the-delegate-report-contract). A report missing a required field is
not accepted, and the item is not mergeable until that gap is closed by one of the two remedies the
contract names. This is a different question from the verdict below, and it is the one verification
cannot answer for you: `verifier-agent` runs against the work, so a report that omits what the agent
did not do still passes it.

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

1. **Diff its worktree against its base commit.** Use `git -C <worktree> diff --binary HEAD` for
   tracked edits (bare `git diff` misses anything staged) plus
   `git -C <worktree> ls-files --others --exclude-standard` for new files, which no diff shows at
   all. For the base, use the sha you recorded at dispatch: the commit in `git worktree list` is
   the worktree's current `HEAD`, not the commit it was created from, and those stop being the
   same the moment an agent commits. Confirm the changes touch only the files the task
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
checked), the report's contract status (conforming, or which field was missing and which remedy
closed it), and anything you found and corrected during verification. Do not commit or merge
anything automatically. Landing the verified worktrees into the main working tree is a separate,
deliberate step, see [`reconcile-worktrees`](../reconcile-worktrees/SKILL.md).

## The delegate report contract

Every agent this skill dispatches returns a report in a fixed shape. The shape is the point: an
agent reporting in free prose is asking you to judge a narrative, and a narrative can omit what it
did not do without ever saying anything false. Balarama Bosch's
[repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT) requires the same kind
of compact evidence contract from every delegate before a gate may advance; the field list below is
the subset of it that a single `fix-batch` run can actually check, with upstream's ledger, budget,
and lineage bookkeeping left out because there is no durable ledger here to carry it.

| Field | What it must contain | What you check it against |
|---|---|---|
| **task id** | The id of the task file it was dispatched with | your dispatch list |
| **covered criteria** | Which of the task's acceptance criteria (or spec scenario ids) the change covers, and which it deliberately does not | the task file |
| **files changed** | Every path it touched, new files included, one line each on what changed | `git diff --binary HEAD` plus `ls-files --others --exclude-standard` in that worktree |
| **tests added, changed, or run** | Each test file or case it wrote or modified, and which suite it ran, or `none` with a reason | the diff and the validation result |
| **validation command** | The command it ran, verbatim, exactly as typed | the acceptance command in the task file |
| **validation result** | The verbatim tail of that command's output, not a summary of it | re-running the command yourself |
| **findings** | Anything real it found that was not the assignment: a defect noticed in passing, an unexpected diff, an opportunistic fix. `none` is a valid answer and is not the same as silence | the diff |
| **blockers and assumptions** | What stopped it, and every assumption it had to make to proceed, including a task premise it found false | Step 5, which is where a blocker gets checked rather than believed |
| **recommended next step** | One of: ready to reconcile, needs a named follow-up, or blocked, and why | your own read of the item |

Findings carry the evidence shape the target repository's review lens defines (in this kit,
[`review-quality.md`](../../rules/review-quality.md)). Do not define a second shape here.

**A missing field blocks acceptance.** Not "note it and move on". Until every field is present, the
item is not mergeable, does not enter the Step 7 report as verified, and does not go to
`reconcile-worktrees`. Never close a gap by inference from the report's prose: "the tests presumably
passed, since it says the task is complete" is exactly the soft claim this contract exists to
delete. The load-bearing pair is the validation command and its verbatim result, kept as two fields
on purpose, because that pair cannot be answered without either running the command or lying, which
is the one property a prose summary can never have.

**Transcript-style reports do not satisfy it.** A narrative of what the agent did, a reasoning dump,
an unbounded log paste, or whole files pasted in are volume, not evidence, and they block acceptance
the same way a missing field does. Bound the verbatim result to the tail that shows the outcome.

**When a report is incomplete, there are exactly two remedies.** Ask the same agent for a focused
follow-up naming precisely the missing fields, which is the default because it costs one round trip
and leaves the evidence with the party that has it. Or get the field yourself from the narrowest
source that answers it: run the validation command in that worktree, read the one file slice.
Prefer the second when the agent is gone or unresponsive, and when the missing field is the
validation result, since running it yourself is stronger evidence than asking again.

**Record which remedy you used, per item**: what was missing, which move you made, and what it
produced. Without that record the batch report cannot distinguish a field the agent proved from one
you proved on its behalf, and that distinction is the entire reason for asking.

**Every field is answerable from inside one worktree.** That is a constraint on the contract, not a
convenience: `fix-batch` agents cannot see each other's work by design, so a field requiring
knowledge of the batch would be unanswerable for every agent at once. If you want something that
needs a cross-worktree view, it belongs in your own Step 6 checks, not in the contract.

This contract is the mechanical half only. The semantic half, where the agent writes its rejected
alternatives, falsified premises, and deliberately open seams into its own task file, is the
decision log that Step 3 item 8 asks every prompt to carry. The two compose and neither restates
the other: this one asks what is checkably true about the change, that one asks what the agent
learned that the change does not show.

## Running this in Claude Code

This section is Claude Code specific. Other harnesses provide the same capability (parallel,
isolated, resumable agents) through their own mechanisms; the doctrine above is what matters, the
tool names below are the local implementation.

- **Dispatch (Step 3), same-repo batch:** use the `Agent` tool with `isolation: "worktree"` and
  `run_in_background: true`, one call per item, all in the same message so they run in parallel.
  Each `Agent` call gets its own worktree; the `prompt` carries the hardened prompt from Step 3.
- **Dispatch, batch against a *different* repository:** `isolation: "worktree"` worktrees the
  **current** project, so it does nothing useful when the work lives in another repo. Create the
  worktrees yourself first (`git -C <target-repo> worktree add -b agent/<id> <path> <dispatch-sha>`),
  then dispatch ordinary background agents whose prompts name the absolute worktree path. The
  sandbox rule in Step 3 carries the full weight here, since there is no harness-level isolation at
  all, which is a difference worth stating in the prompt rather than assuming the agent infers it.
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

## Conventions

**The prompts you dispatch point agents at the target repository's conventions**, taken from that
repo's `AGENTS.md`, since the code they write belongs to that repo and not to this kit.

**Your own output**, the hardened prompts themselves and the consolidated verification report,
follows the repo's house-style module (in this kit,
[`.agents/rules/house-style.md`](../../rules/house-style.md)): sentence-case headings, clickable
relative links, named sources, no em-dashes. That file is a swappable default; a downstream adopter
may replace it without touching this skill.

**What a dispatched agent may do unattended** follows the repo's autonomy module (in this kit,
[`.agents/rules/autonomy.md`](../../rules/autonomy.md)), which consolidates four of the rules stated
above: `A1` sandbox containment, `A2` scope discipline, and `A4` and `A5`, the verbatim-result and
disclosure halves of the delegate evidence contract. That file is a swappable default too; a
downstream adopter may raise or lower the ceiling without touching this skill.
