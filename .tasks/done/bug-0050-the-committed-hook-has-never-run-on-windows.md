---
id: bug-0050
title: Register the committed hook through an interpreter that exists on Windows
type: bug
status: done
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
[`AGENTS.md`](../../AGENTS.md) makes a specific case for committing this one hook: a cloud session
clones the repository, gets none of the user-scope skills, and would otherwise never be told the
kit's skills exist. That argument is sound and the hook has not been doing it. The number is now
known and it is 14.

**The fix already exists in this repository, in the other half of the distribution path.**
`hook_interpreter()` in [`scripts/install.py`](../../scripts/install.py) exists precisely to avoid
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

## Decisions

- **The premise both shapes rested on was false, and neither of the two the task weighed was
  taken.** The Implementation notes offer `python` instead of `python3`, or a shell shim as a second
  file. Both inherit the sentence `.claude/settings.json` argued at length: "A static JSON file
  cannot probe, so this cannot be right on both platforms at once." **It does not need to probe.** A
  shell fallback, `python3 <hook> || python <hook>`, is right on all three platforms in one line,
  with no second file and no per-platform choice. Measured on Windows 2026-08-31: `python3 <hook>`
  exits 9009 writing only to stderr, so stdout stays clean, and the fallback then runs the real
  interpreter with stdin intact and emits the hook's single JSON object.
- **The opencode wiring had the answer the whole time.** `zen-hooks.mjs` carries
  `const INTERPRETERS = ["python3", "python"]` and tries them in order, and has since it was
  written. One of the three wirings solved this in code while another argued in prose that it was
  impossible, and nothing compared them. That is the finding worth more than the fix.
- **An acceptance criterion of this task's own was unsatisfiable as written.** It asks for a test
  asserting the committed registration "uses the interpreter `install.hook_interpreter()` resolves
  to". That function returns `python` on Windows and `python3` elsewhere, and the settings file is
  static, so an equality assertion would pass here and fail on every Linux and macOS leg of CI. The
  assertion is **containment** instead: the command must name whatever `hook_interpreter()` resolves
  to on the platform running the test, which holds everywhere and still fails the moment the two
  halves of the distribution path disagree, which is what the criterion was for.
- **A rejected alternative, and the reason it is a separate task.** `.codex/hooks.json` registers all
  four hooks with a bare `python3` and has the identical defect, including on the spec-closeout
  **gate**, where a guardrail that never fires is worse than a reminder that never speaks. It is not
  fixed here. The fallback needs a shell, that was measured for Claude Code and only inferred for
  Codex, and applying an unverified shell-dependent change to a wiring nobody here can exercise
  turns a known failure on one platform into a possible failure on three. Filed with the inference
  and its evidence as [`bug-0058`](../bug-0058-the-codex-wiring-still-registers-every-hook-as-python3.md).
- **What every prior test asserted, and why none of them saw this.** Three tests already covered this
  file: that it names a hook that exists, on an event the module ships, matching what the wirings
  agree on. One asserted `command.startswith("python3 ")`, which pinned the half of the decision that
  was right and could not see the half that was wrong. All of them passed for three weeks while the
  command could not launch, because a structural assertion cannot see an interpreter that is not
  there. The new test runs the command.
- **Work beyond `touched_files`, disclosed.** `tests/test_hooks.py` and
  `tests/test_hooks_reachability.py`, whose registration tests both assumed a command naming the
  script once; and `docs/OBSERVATORY.md`, which recorded this as "a known and deliberate trade, not
  a defect" in a passage that is now history rather than current state.

## Risks and rollback

Touches the repository's own session-start behaviour, so a mistake here affects every session
opened in this checkout rather than only a test. A hook that exits non-zero is already tolerated
(that is the current state and the reminder is non-blocking), so the worst realistic outcome is
that it goes on not running. Reversible by reverting the one commit; nothing persists.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test asserts the committed registration in `.claude/settings.json` uses the interpreter
      `install.hook_interpreter()` resolves to, and fails if the two diverge.
- [ ] **Partially met, and the rest is owed to the next session start.** The committed command was
      run the way the harness runs it, through a shell with one JSON payload on stdin, and exits 0
      emitting nothing, which is correct here because the kit's skills are reachable. That is
      asserted permanently by `test_every_committed_command_launches_and_exits_zero`. What no
      session can verify from inside itself is the harness's own invocation, so the corpus check
      stands open with its baseline recorded: the last `exit=49` row is dated **2026-08-29**, 21
      rows from 2026-08-07. A session started after this fix that adds no new `exit=49` row closes
      it.
- [x] Existing tests still pass.
- [x] The bound of whichever interpreter rule is chosen is stated in `AGENTS.md` beside the
      existing argument for committing this hook at all.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
