---
id: chore-0083
title: No Codex session has ever exercised the Codex wiring, and two of its assumptions are unverified
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .codex/hooks.json
  - .agents/hooks/README.md
  - tests/test_hooks.py
created: 2026-08-31
---

## Problem

[`hooks.json`](../.codex/hooks.json) registers all five hooks for Codex, and
[`.agents/hooks/README.md`](../.agents/hooks/README.md) presents that wiring as one of three the
module ships. **Nothing has ever run it.**

Established 2026-08-31 while closing
[`bug-0058`](done/bug-0058-the-codex-wiring-still-registers-every-hook-as-python3.md), by looking
rather than by reasoning:

```text
71 Codex session files under ~/.codex/sessions, every one dated 2026-07-25
no file anywhere in ~/.codex newer than 2026-07-27
the hooks module landed 2026-08-06
```

So the wiring postdates every Codex session on this machine. That is not a criticism of it; it is
the reason two assumptions inside it have never been tested, and both are the kind this repository
keeps getting bitten by.

**1. Does Codex run a hook command through a shell?** `bug-0058` gave every command an interpreter
fallback, `python3 <hook> || python <hook>`, which is a shell operator. That change is safe either
way and the task records why: with no shell the tail arrives as argv and no hook reads `sys.argv`,
so it degrades to exactly the previous behaviour. But "safe either way" is not the same as "known",
and the next change to this file may not have that property.

**2. Can the path substitution work at all on Windows?** Every command contains
`$(git rev-parse --show-toplevel)`, which is POSIX substitution. `cmd.exe` passes it through as a
literal path. So if Codex spawns the platform default shell on Windows, **every hook in this wiring
is inert there for a reason that has nothing to do with the interpreter**, and `bug-0058`'s fix
would not help. This was found because the first version of that task's executable test used
`shell=True`, got `cmd.exe`, and failed on the path rather than on `python3`.

Assumption 2 is the older and the larger of the two, and it predates every task that has touched
this file.

## Scope

**In scope:** running the wiring against a real Codex session, on Windows and on one POSIX
platform, and recording what was observed. Then correcting whatever that shows, and stating in
`.agents/hooks/README.md` which of the three wirings have been exercised and which have not.

**Out of scope:**

- The interpreter fallback itself, which `bug-0058` settled and which is safe under both
  hypotheses.
- The Claude Code and opencode wirings. The first was measured by `bug-0050`; the second tries
  interpreters in order in its own code.
- Changing which hooks Codex registers.

## Implementation notes

**This needs a person with Codex installed, which is why it is filed rather than done.** No agent
in this repository can start a Codex session, and the absence of one is exactly what makes the
wiring unverifiable from here. The shape to follow is
[`cloud-executable.runbook.md`](../docs/spec/cloud-executable.runbook.md), which exists for the
same reason: a contract whose verification depends on an action nothing here can take.

What to record, so the result is evidence rather than an impression:

1. Whether the hooks fire at all, on each event, in a repository that ships `.agents/hooks/`.
2. The exact command Codex executed, if it is observable, and whether a shell was involved.
3. On Windows specifically, whether `$(git rev-parse --show-toplevel)` resolved.
4. Whether `spec-conformance-gate` can actually block, since a gate that has never fired is the
   failure `.agents/hooks/README.md` names in those words.

If the path substitution does not survive, the fix is the shape the opencode plugin already uses:
resolve the repository root in code rather than in the command. That would make the Codex wiring a
launcher plus a registration rather than five one-line commands, and it is worth that cost only
once the observation says so.

**Until then, say so where the claim is made.** `.agents/hooks/README.md`'s wiring section presents
three harnesses evenly. Two are exercised and one has never been, and a reader choosing a harness on
the strength of that table deserves to know which is which.

## Risks and rollback

Nothing to roll back until the observation is made. The risk is in the other direction: leaving a
wiring in the tree that reads as working, in a repository whose own README argues that an untested
guardrail is worse than none, because a reader trusts it and gets silence.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A real Codex session has run in a repository shipping `.agents/hooks/`, on Windows and on one
      POSIX platform, and what happened is recorded in this task with the four observations above.
- [ ] Whatever that shows is fixed, or recorded as working, in `.codex/hooks.json`.
- [ ] `.agents/hooks/README.md` states which wirings have been exercised and which have not, so the
      table stops presenting three harnesses as equally proven.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
