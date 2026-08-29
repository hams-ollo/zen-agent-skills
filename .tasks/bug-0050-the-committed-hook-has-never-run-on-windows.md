---
id: bug-0050
title: Register the committed hook through an interpreter that exists on Windows
type: bug
status: open
priority: P1
parent: "ROADMAP#7 agent-observatory"
depends_on: []
touched_files:
  - .claude/settings.json
  - scripts/install.py
  - tests/test_install.py
  - AGENTS.md
created: 2026-08-29
---

## Problem

The one hook this repository commits has never successfully run on this machine, and the
observatory's own health report is what found it.

`.claude/settings.json` registers `skill-reachability-reminder.py` on `SessionStart` with the
command `python3 .agents/hooks/skill-reachability-reminder.py`. On Windows `python3` is not the
interpreter: it is the Microsoft Store app-execution alias, a stub that prints an install message
and exits non-zero. The health report reads, over the maintainer's corpus on 2026-08-29:

    hook  = SessionStart:startup     exit = 49
    14 distinct failures, 18 stored rows
    first 2026-08-07, last 2026-08-29
    "Failed with non-blocking status code: Python was not found; run without arguments to
     install from the Microsoft Store, or disable this shortcut from Settings > Apps >
     Advanced app settings > App execution aliases."

Every session start since 2026-08-07. The failure is silent by construction: the reminder shape
requires a hook to exit cleanly whatever happens, so nothing surfaces it, and the exit status went
into the corpus where nothing read it until `feat-0058`.

**The cost was argued in prose and never counted.** The conventions section of
[`AGENTS.md`](../AGENTS.md) makes a specific case for committing this one hook: a cloud session
clones the repository, gets none of the user-scope skills, and would otherwise never be told the
kit's skills exist. That argument is sound and the hook has not been doing it. The number is now
known and it is 14.

**The fix already exists in this repository, in the other half of the distribution path.**
`hook_interpreter()` in [`scripts/install.py`](../scripts/install.py) exists precisely to avoid
this trap for the registrations `install.py` prints. The committed registration does not use it.
So the installer places a hook that works and the repository commits one that does not, and the
two have disagreed since the day `install.py` learned the difference.

## Scope

**In scope:** make the committed registration in `.claude/settings.json` resolve to a real
interpreter on Windows, macOS, and Linux, by the same rule `hook_interpreter()` already applies.
A test that would fail if the committed registration and the installer's rule ever diverge again.

**Out of scope:**

- Adding a second committed hook, or making any hook blocking. The conventions section of
  `AGENTS.md` records that either is a separate decision not covered by the existing exception,
  and `feat-0059` restated it as a hard boundary. This task changes how the one existing hook is
  invoked and nothing about which hooks exist.
- The observatory event hook, which is opt-in and placed by `install.py --with-hooks`.
- Backfilling or repairing the 14 recorded failures. They are corpus history and the health
  report is correct to show them.

## Implementation notes

`settings.json` is data with no place to run a resolver, so the interpreter has to be chosen
without executing anything at hook-registration time. Two shapes worth weighing before picking:

- **`python` rather than `python3`.** On Windows the launcher and every modern install provide
  `python`; on a system where `python` is Python 2 this would be worse than the current state, and
  that system is increasingly rare. Cheapest change, one token, and it needs a stated bound.
- **A shell shim** that tries `python3` then `python`. Portable, and it makes the committed hook
  a second file rather than a one-line command, which is closer to the boundary the scope above
  refuses.

Prefer whichever `hook_interpreter()` already resolves to, and make the test assert the two agree
rather than asserting a literal, so this cannot drift a second time. Verify against a real session
start rather than only in a test: the failure this task fixes is invisible to a passing suite, and
the health report is now the instrument that can confirm it, by showing no new failure after the
change.

## Risks and rollback

Touches the repository's own session-start behaviour, so a mistake here affects every session
opened in this checkout rather than only a test. A hook that exits non-zero is already tolerated
(that is the current state and the reminder is non-blocking), so the worst realistic outcome is
that it goes on not running. Reversible by reverting the one commit; nothing persists.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A test asserts the committed registration in `.claude/settings.json` uses the interpreter
      `install.hook_interpreter()` resolves to, and fails if the two diverge.
- [ ] The hook runs to a zero exit on this machine, confirmed by starting a session and reading
      the observatory's health report for a new `SessionStart:startup` failure. There must be none
      dated after the fix.
- [ ] Existing tests still pass.
- [ ] The bound of whichever interpreter rule is chosen is stated in `AGENTS.md` beside the
      existing argument for committing this hook at all.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
