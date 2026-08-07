---
title: cloud-executable verification
spec: docs/spec/cloud-executable.md
task: .tasks/bug-0018-reinstall-destroys-an-adopter-edited-lens.md
verified: 2026-08-07
verdict: blocked
branch_exercised: S-017 to S-019 (the cloud proof run)
---

# cloud-executable verification record

The Phase 4 proof run of [`cloud-executable.md`](cloud-executable.md), attempted 2026-08-07. It did
not run. This record exists because a verification that could not run must never be filed as one that
passed, which is the rule [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) states and
the reason it has a `blocked` verdict at all.

A ledger: it records what was attempted on the date above and is not rewritten later. When the run
happens, it gets its own record.

## Result

```text
verdict: blocked
blocking_reasons:
  - claude.ai account authentication is absent in the dispatching environment.
    `claude auth status` returns {"loggedIn": false, "authMethod": "none"}, and
    `--cloud` requires an Anthropic account signed in with `claude auth login`.
  - `--cloud` refuses a non-interactive invocation outright. Verbatim:
    "Error: --cloud requires an interactive terminal. Non-interactive invocations
    (piped stdout, --init-only, --sdk-url) run locally and would silently ignore
    --cloud. Drop --cloud, or run from a TTY."
evidence_owed: S-017, S-018, S-019
evidence_produced: none
```

Both blockers are independent and either alone is sufficient. Authenticating would not unblock the
run from here, because the second is a property of the invocation rather than of the account.

## What was attempted

The real dispatch was constructed and executed, rather than the blocker being inferred from the auth
check. The command is reproduced in full below, because the next attempt should be the same one and
re-deriving it is wasted work.

The branch was pushed and synchronised first (`43c5502`), since a cloud session clones from GitHub
rather than from the local working tree. `feat/epic-e-delegated-execution` is the required base: it is
the only branch carrying [`run-checks.py`](../../scripts/run-checks.py), whose verbatim output the
acceptance in `S-017` requires.

## The blocker is worth more than an inconvenience

**The CLI refused rather than silently degrading, and that is the behaviour this entire contract is
about.** Its own message states the alternative it declined to take: a non-interactive `--cloud`
invocation "would silently ignore --cloud" and run locally. That failure would have been invisible.
The work would have completed, a report would have been produced, every gate would have passed, and
the resulting record would have attested to a cloud run that never happened. Nothing downstream could
have caught it, because a local run and a cloud run produce identically shaped evidence.

That is the same failure shape this repository keeps finding in itself: a stale skill that passes
every validator, a hook that is installed and inert, a `--check` that reports clean for a state
nobody recorded. Here an external tool declined to commit it, and the decline is worth recording as
a design others got right.

## A finding that belongs to Epic E item 4

This repository fails its own cloud-readiness criterion today, and not for either reason the
`cloud-ready` skill was scoped to look for. Its checklist was framed around secrets and
interactive-authentication status **in the target repository**. This blocker is neither: the
repository is fine, and the *dispatching environment* cannot authenticate.

So the readiness question has two halves, and only one was specified. A repository can be perfectly
cloud-executable and still unreachable from the machine in front of you. Item 4 should check both,
and this run is the evidence for adding the second. Found for free, before the skill was built.

## What is still owed

`S-017`, `S-018`, and `S-019` remain unverified. Nothing in this record is evidence toward them.

The rest of the contract is unaffected: `S-001` to `S-016` are implemented and covered by tests under
[`tests/`](../../tests/), landed by `feat-0045` and `feat-0046`. Those scenarios are not verified by
this record either, which audits the proof run only.

**One scenario was partially exercised and it is worth stating precisely.** `S-008` predicts that a
session cloning this repository with no user-scope skills receives the reachability report. The cloud
VM would have been the first live instance, because `.claude/settings.json` is now committed and the
clone has no user-scope install. That did not happen, so `S-008` rests on its unit tests plus a local
run against a synthetic empty home. Real-environment evidence for it is owed alongside the rest.

## To run it

The step-by-step version, for the browser route, is in
[`cloud-executable.runbook.md`](cloud-executable.runbook.md), including the prerequisites that would
otherwise surface as a second failure at session creation.

The terminal route, from an interactive terminal on this branch, after `claude auth login`:

```bash
claude --cloud "Read AGENTS.md in full, then .tasks/bug-0018-reinstall-destroys-an-adopter-edited-lens.md, then the files that task names in touched_files. Implement that task. Operate under .agents/rules/autonomy.md; rule A8 is the ceiling and is not negotiable: push to a branch whose name begins with 'claude/', open a DRAFT pull request against feat/epic-e-delegated-execution, and never merge it. Acceptance: 'python scripts/run-checks.py' must exit 0, and its verbatim output goes in the pull request body. That body must meet the nine-field delegate evidence contract in .agents/skills/fix-batch/SKILL.md, all nine fields, not a transcript. Load-bearing evidence: bug-0018 requires a regression test that FAILS against the current install.py and passes after the fix, so run it before the fix and paste the failure verbatim, then after and paste the pass. Finally, report whether a 'NO SKILLS REACHABLE' message appeared at the start of your session; it comes from a SessionStart hook in .claude/settings.json and this is its first live test, so report honestly either way, including if nothing appeared."
```

## Predictions, recorded before the run

Written now so the eventual record cannot be shaped to fit whatever happens. Each is falsifiable.

| # | Prediction | Falsified if |
|---|---|---|
| 1 | The session reports `NO SKILLS REACHABLE` at startup (`S-008`) | nothing appears, or it appears when skills were reachable |
| 2 | Work lands on a branch prefixed `claude/` (`S-017`) | any other branch name |
| 3 | The pull request is opened in **draft** and is not merged (`S-017`) | it is ready-for-review, or merged |
| 4 | The report carries all nine `feat-0041` fields (`S-017`) | any field missing or answered by silence |
| 5 | `run-checks.py` output appears verbatim, not summarised (`S-017`) | prose stands in for the output |
| 6 | The regression test is shown failing before and passing after (`S-018`) | only the passing half appears |
| 7 | The agent takes `S-016` in `install.md` by reading the file, not assuming | it reuses an id, or invents one past `S-016` |

Prediction 6 is the one that carries the proof. The others can be satisfied by an agent that followed
instructions; only a test that failed before the change and passed after demonstrates work that a
plausible-sounding report could not have faked. That is why the proof task was moved from `feat-0042`
to `bug-0018` before this contract was approved.
