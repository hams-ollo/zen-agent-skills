# cloud-executable: how to run the proof session

The Phase 4 proof run of [`cloud-executable.md`](cloud-executable.md), written 2026-08-07 for the
browser route. It exists because the run has to be started by a person: `--cloud` refuses a
non-interactive invocation, so no agent in this repository can start it. Recorded here rather than in
a chat message, because the attempt is likely to happen on a different day than the decision to make
it.

The blocked attempt and both blockers are in
[`cloud-executable.verification.md`](cloud-executable.verification.md). This is the instruction sheet;
that is the record.

## Before you start

| Check | How | If it is missing |
|---|---|---|
| GitHub is connected to your Claude account | Open [claude.ai/code](https://claude.ai/code) and see whether `hams-ollo/zen-agent-skills` is selectable | Authorize the Claude GitHub App, or run `/web-setup` in a terminal to sync your `gh` token |
| The branch is on the remote and carries the hook fix | `git log --oneline -1 origin/developer` and `git merge-base --is-ancestor 7703632 origin/developer` | `git push`, or pick a branch that does contain `7703632` |
| Your local work is committed | `git status` | Commit it. The cloud VM clones from GitHub, not from your disk, so uncommitted work is invisible to it |

Nothing else is needed. The kit is standard-library Python, so the default cloud environment already
has everything and **no setup script is required**. That is worth keeping true: a setup script's
filesystem snapshot is reused for about seven days, which is the staleness this epic rejected that
mechanism over.

## Start the session

1. Go to [claude.ai/code](https://claude.ai/code).
2. New session, repository `hams-ollo/zen-agent-skills`.
3. **Branch: `developer`.** Not `main`. Epic E merged into `developer` on 2026-08-08 at `74e2661`,
   and `feat/epic-e-delegated-execution` was deleted by the repository's automatic head-branch
   deletion, so the branch this step named until then no longer exists. `developer` carries
   [`run-checks.py`](../../scripts/run-checks.py), whose verbatim output the acceptance in `S-017`
   requires, and `main` does not yet.
4. Paste the prompt below as the first message.

## The prompt

```text
Read AGENTS.md in full, then .tasks/bug-0018-reinstall-destroys-an-adopter-edited-lens.md, then the
files that task names in touched_files. Implement that task.

Operate under .agents/rules/autonomy.md. Rule A8 is the ceiling and is not negotiable: push to a
branch whose name begins with 'claude/', open a DRAFT pull request against
developer, and never merge it.

Acceptance: 'python scripts/run-checks.py' must exit 0, and its verbatim output goes in the pull
request body.

That body must meet the nine-field delegate evidence contract in .agents/skills/fix-batch/SKILL.md.
All nine fields. Not a transcript.

Load-bearing evidence: bug-0018 requires a regression test that FAILS against the current install.py
and passes after the fix. Run it BEFORE your fix and paste the failure verbatim, then run it after
and paste the pass. A report with only the passing half does not demonstrate the fix and will be
rejected.

bug-0018 also amends docs/spec/install.md and carries the author's explicit instruction to do so.
Read that file and take the next free scenario id rather than assuming one. Leave status: approved,
add a dated amendment note marked pending the author's re-approval, and add the row to
docs/spec/README.md's re-approval queue.

Finally, report whether a 'NO SKILLS REACHABLE' message appeared at the very start of your session.
It comes from a SessionStart hook registered in .claude/settings.json and this run is its first live
test. Report honestly either way, including if nothing appeared.
```

## What to check while it runs

You do not need to supervise it. Two things are worth a glance:

- **The first message.** If `NO SKILLS REACHABLE` appears before it starts work, `S-008` is confirmed
  live, in the environment it was written for. If nothing appears, that is the more interesting
  result and the bootstrap needs rethinking.
- **The branch name and the PR state.** `claude/` prefix, and draft. Those are the autonomy ceiling,
  and an agent quietly opening a ready-for-review pull request is a finding about `autonomy.md` `A8`
  rather than about this task.

## When it finishes

Hand the session id or the pull request URL back to a local Claude Code session. Creation needs a
terminal; steering an existing session does not, so `claude -p "..." --cloud <session-id>` works
headlessly from there once you have signed in.

What happens next, in order:

1. The seven predictions in
   [`cloud-executable.verification.md`](cloud-executable.verification.md) get checked against what
   actually happened, one at a time. They were written before the run so the record cannot be shaped
   to fit the outcome.
2. A **new** verification record is written. The existing one is a ledger of the blocked attempt and
   is not edited.
3. `bug-0018` closes out through the normal lifecycle if its work is sound.

**Who verifies it matters.** The agent that built this infrastructure should not be the one certifying
that the infrastructure worked. Verification of `bug-0018`'s own fix is fine from any session that
did not write it; verification of Epic E item 2 itself wants a session with no stake in its design.

## Re-running just the reachability check (`S-008`)

A second, much smaller session. It exists because the first proof run reported nothing at startup, and
the cause turned out to be a defect in the hook rather than in the run: `.agents/skills` was counted
at project scope, where this kit keeps its own sources, so the hook was silent in the one repository
that ships it. Fixed at `7703632`, which reached `developer` on 2026-08-08 in the Epic E merge
`74e2661`.

**Run it on any commit containing `7703632`, which today means `developer`.** The condition is the
commit and not a branch, deliberately: this section first named
`feat/epic-e-delegated-execution`, and that branch was deleted when Epic E merged, which would have
sent a session to check out something that no longer exists. On any commit without `7703632` the hook
is still the broken version and its silence would say nothing about the fix. Check with
`git merge-base --is-ancestor 7703632 HEAD` rather than by reading the branch name.

This session asks for **four** observations rather than one, because last time a single yes-or-no
could not distinguish two failures that look identical from outside: a hook whose logic is wrong, and
a hook whose registration never launched it. Observations 1 and 2 separate them. If 2 reports and 1
does not, the logic is right and the registration is broken, which is the `feat-0038` failure again
and would point straight at the interpreter or the path in `.claude/settings.json`.

Observation 3 matters because the interpreter in that file was chosen by reasoning, not evidence. It
says `python3` on the argument that cloud sessions are Linux and many distributions ship no `python`.
That has never been checked on the actual platform.

```text
This is an observation-only run. Do not fix anything, and do not change any behaviour.

Report these four things, verbatim, and nothing else:

1. Did a message beginning "NO SKILLS REACHABLE" appear in your context at the very start of this
   session, before you did anything? Answer yes or no explicitly. If yes, paste it. If no, say so
   plainly; "no" is a real and useful answer here.

2. Run this and paste the exact output, including empty output:
   printf '{"hook_event_name":"SessionStart","source":"startup","cwd":"%s"}' "$PWD" | python3 .agents/hooks/skill-reachability-reminder.py

3. Run these and paste the exact output:
   command -v python3 ; command -v python ; python3 --version ; uname -s

4. Run this and paste the exact output:
   git rev-parse HEAD ; git log --oneline -1

Then append one line to the "Runs performed" table at the end of
docs/spec/cloud-executable.runbook.md recording the date, the commit, and whether observation 1 was
yes or no. Change nothing else in that file and nothing else in the repository.

Operate under .agents/rules/autonomy.md. Push to a branch beginning 'claude/', open a DRAFT pull
request against developer, and never merge it. Put all four observations in
the pull request body, verbatim, so they can be read without opening the session.

Report honestly even if the answer to 1 is no. A "no" here is evidence about the fix, not a failure
on your part, and reporting it accurately is the entire job.
```

### Reading the result

| Obs 1 (in context) | Obs 2 (run by hand) | What it means |
|---|---|---|
| yes | reports | `S-008` confirmed live. The bootstrap works end to end. |
| no | reports | Logic is right, **registration is broken**. Look at the interpreter and path in `.claude/settings.json`, and at whether the harness honours a committed project settings file at all. |
| no | silent | The logic is still wrong in that environment. The fix did not hold; check what observation 3 says about the interpreter, and whether the clone has something at `.claude/skills`. |
| yes | silent | Contradictory. Something other than this hook produced the message; treat the whole result as unreliable and say so. |

## Runs performed

| Date | Commit | Purpose | Startup message seen? |
|---|---|---|---|
| 2026-08-07 | `08b0a6d` | The `bug-0018` proof run (`S-017` to `S-019`) | **No.** Cause found afterwards: the hook counted this kit's own `.agents/skills/` sources at project scope, so it was silent in a fresh clone. Fixed at `7703632`. |

## If it fails

Two failure classes, and they call for opposite responses.

**The task fails.** `run-checks.py` exits non-zero, or `bug-0018` turns out harder than scoped. That
is a normal outcome and `S-019` covers it: the session should still open a draft pull request carrying
the failing verbatim output. A run that reports an honest failure is a successful proof of the
contract, because what is under test is whether an unattended session can tell the truth about its
own work.

**The proof fails.** No message at startup, or the agent merges, or the report is a transcript with
fields answered by silence. That is a finding against Epic E rather than against `bug-0018`, and it
goes to Epic E item 3, which exists to harden `autonomy.md` from exactly this.
