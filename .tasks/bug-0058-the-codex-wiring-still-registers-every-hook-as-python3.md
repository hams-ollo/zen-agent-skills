---
id: bug-0058
title: The Codex wiring still registers every hook as python3, which is inert on Windows
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .codex/hooks.json
  - tests/test_hooks.py
created: 2026-08-31
---

## Problem

[`bug-0050`](done/bug-0050-the-committed-hook-has-never-run-on-windows.md) fixed the Claude Code
wiring, which had registered its one committed hook as `python3` and so had never run on Windows:
`python3` there is the Microsoft Store app-execution alias, a stub that prints an install
advertisement and exits without running anything. The observatory's health report counted the cost
at 21 stored rows from 2026-08-07 to 2026-08-29.

**The same spelling is still in the Codex wiring, for all four hooks.**
[`hooks.json`](../.codex/hooks.json) registers each of them as:

```json
"command": "python3 \"$(git rev-parse --show-toplevel)/.agents/hooks/skill-reachability-reminder.py\"",
```

`skill-reachability-reminder`, `install-currency-reminder`, `delegation-reminder` and
`spec-conformance-gate`, every one led by a bare `python3`. On Windows every one of them is inert
in exactly the way the Claude Code registration was, and inert in the silent way: three are
reminders, which the module contract requires to exit cleanly whatever happens, so nothing surfaces
it. The fourth is the spec-closeout **gate**, and a gate that never fires is a guardrail nobody has
seen work, which is the failure `.agents/hooks/README.md` names in those words.

**The opencode wiring is not affected and is worth reading first.**
[`zen-hooks.mjs`](../.opencode/plugins/zen-hooks.mjs) already does the right thing, in code, and has
since it was written:

```javascript
const INTERPRETERS = ["python3", "python"];
```

It tries them in order with `execFileSync`. So one of the three wirings had the answer all along,
while `.claude/settings.json` argued at length that a static file could not have it.

## Scope

**In scope:** making the four Codex registrations resolve to a real interpreter on Windows, macOS
and Linux, and extending `bug-0050`'s executable test to cover this wiring rather than only the
Claude Code one.

**Out of scope:**

- The opencode plugin, which already handles this.
- `.claude/settings.json`, fixed by `bug-0050`.
- Which hooks each wiring registers, or adding any. This changes how existing registrations are
  invoked and nothing else.

## Implementation notes

**The blocker is that nobody here can test Codex, and that is why `bug-0050` filed this rather than
fixing it in passing.** The shape that works for Claude Code is a shell fallback,
`python3 <hook> || python <hook>`, which is only correct if the harness runs the command through a
shell. For Claude Code that was measured. For Codex it is inferred, and the inference is stated here
so whoever picks this up can weigh it rather than inherit it:

> Every Codex command in that file already contains `$(git rev-parse --show-toplevel)`, which only a
> shell evaluates. If Codex did not run these through a shell, those commands would already be
> broken in a different and more visible way. So the wiring is very likely shell-interpreted and
> `||` is very likely available.

That is good evidence and it is not a measurement. Applying an unverified shell-dependent change to
a wiring nobody here can exercise would convert a failure on one platform into a possible failure on
all of them, which is a worse trade than the one it fixes. **Confirm it against a real Codex session
before changing the file**, the same way `bug-0050`'s fix was confirmed by running the committed
command the way the harness runs it.

If Codex turns out not to use a shell, the alternative is the shape opencode already uses: a small
launcher that tries the interpreters in order. That makes the wiring a second file rather than a
one-line command, which is a cost worth paying only once the shell question is answered.

## Risks and rollback

Touches a wiring for a harness this repository cannot exercise, so the failure direction is a change
that looks right and is inert, which is the exact class this task is about. The current state is a
known failure on one platform; a wrong fix is an unknown failure on three.

Reversible by reverting one commit. Nothing persists.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Whether Codex runs a hook command through a shell is established by observation and recorded
      in the task, not inferred from the file.
- [ ] Each of the four Codex registrations resolves to an interpreter that exists on Windows, macOS
      and Linux, by whichever shape that observation permits.
- [ ] `tests/test_hooks.py`'s executable registration test covers the Codex wiring as well as the
      Claude Code one, running each command the way its harness does and asserting exit 0 with
      stdout carrying nothing or exactly one JSON object.
- [ ] A test asserts every wiring names an interpreter that resolves on the platform running it, so
      the three wirings cannot drift apart on this again.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
