---
id: chore-0084
title: The prescribed $CLAUDE_PROJECT_DIR hook registration is inert under cmd.exe, so item 3 of chore-0038 needs a different command shape
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .claude/settings.json
  - tests/test_hooks.py
created: 2026-08-31
---

## Problem

`chore-0038` item 3 asked for the committed hook registration in `.claude/settings.json` to be
made working-directory independent by prefixing the hook path with `$CLAUDE_PROJECT_DIR`. The
agent that worked `chore-0038` declined the item rather than applying it, and measurement confirms
the refusal was correct.

Windows resolves `shell=True` to `cmd.exe`, which does not expand `$NAME`. Measured on
2026-08-31, from this repository, with `CLAUDE_PROJECT_DIR` set:

```text
$VAR form   -> $CLAUDE_PROJECT_DIR/x.py     (passed through literally, unexpanded)
%VAR% form  -> D:/zen-starter-kit/x.py      (expanded)
```

So the prescribed form would register a command whose path is taken literally, which is precisely
the registered-and-inert failure `bug-0050` fixed and counted at fourteen silent session starts.
The item is not merely untested on Windows; as written it would reintroduce a closed bug on one of
the three operating systems this repository targets.

The item is also blocked by `touched_files`: any prefix form trips
`test_the_committed_claude_settings_names_a_hook_that_exists` in `tests/test_hooks.py`, which
`chore-0038` did not own.

## Scope

Choose and apply a command shape for the committed registration that is working-directory
independent **and** survives `cmd.exe`, then make `tests/test_hooks.py` assert that property
rather than merely tolerate the new form.

Out of scope: the interpreter fallback itself (`python3 <hook> || python <hook>`), which
`bug-0050` settled and which this task must preserve; and the `_comment` block, which only existed
to explain a path form and should be written to explain whichever form is chosen.

## Implementation notes

The candidate shapes each have a cost, and the task is to pick one with the reason recorded:

- **Leave the path relative**, as it is today, and document that hooks are invoked from the
  project root. Cheapest, and it is what currently works on all three platforms.
- **A form both shells expand.** No single literal expands under both `cmd.exe` and POSIX `sh`,
  so this means either two registrations or a launcher script.
- **A launcher** that resolves its own directory from `__file__` and needs no variable at all.
  This is the shape `bug-0050`'s fallback already gestures at.

Whatever is chosen, `TheCommittedRegistrationActuallyRuns` (added by `bug-0050`) must keep passing,
since it runs the committed command through the platform's default shell and is the test that
would have caught the original inert registration.

## Risks and rollback

The risk is the one `bug-0050` recorded: a registration that looks right, exits non-zero or
silently does nothing, and reports no error at session start. Any change here must be validated by
running the committed command through the platform default shell, not by reading it.

Rollback is reverting `.claude/settings.json` to the relative form, which is known-good on all
three platforms.

## Acceptance criteria (mechanically verifiable)

1. The committed registration in `.claude/settings.json` runs successfully through the platform's
   default shell from a working directory other than the repository root, proven by a test.
2. That test fails against a `$CLAUDE_PROJECT_DIR`-prefixed registration on Windows, so it
   demonstrably discriminates rather than passing vacuously.
3. `TheCommittedRegistrationActuallyRuns` still passes.
4. The chosen shape and the two rejected alternatives are recorded in this file's `## Decisions`.
5. `python scripts/run-checks.py` passes.

## Definition of done

Acceptance criteria met, `## Decisions` recorded, `CHANGELOG.md` line added, and this file moved
to `.tasks/done/`.
