---
id: chore-0037
title: The one committed hook registration sits outside every wiring test, so a rename would break it silently
type: chore
status: open
priority: P2
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
touched_files:
  - tests/test_hooks.py
created: 2026-08-08
---

## Problem

`WiringConsistencyTests` in [`test_hooks.py`](../tests/test_hooks.py) asserts that every hook in the
module is registered in three wirings: `.codex/hooks.json`, the block `claude_registration()` prints,
and the opencode adapter. There is a fourth, and it is the only one that runs in a Claude Code session
in this repository: [`.claude/settings.json`](../.claude/settings.json), committed as the deliberate
exception recorded in the conventions section of [`AGENTS.md`](../AGENTS.md).

Nothing asserts anything about it. Its command names the hook by a repository-relative path,
`python3 .agents/hooks/skill-reachability-reminder.py`, and no test confirms that path resolves.
Renaming or moving the hook would be caught in three places and would silently break the one wiring
that matters for the case the exception was granted for. The hook would then not run at all, and a
hook that does not run produces exactly the same output as a hook that ran and found skills reachable.

That is the failure this module has already been bitten by twice while being built, recorded in
[the hooks module contract](../.agents/hooks/README.md): "installed, correct-looking, and doing
nothing".

## Scope

**In scope:** assert, in the existing wiring tests, that every command path named in the committed
`.claude/settings.json` points at a file that exists, and that the file it names is a hook this module
ships.

**Out of scope:**

- Requiring every hook to appear in `.claude/settings.json`. It registers one hook on purpose, and
  extending the "every hook, everywhere" assertion to it would fail the moment it is correct. The new
  assertion runs the other way: whatever it names must exist.
- Registering a second hook there. That is a decision `AGENTS.md` reserves, and
  [`chore-0034`](chore-0034-cloud-executable-conformance-matrix.md) records it as an open question for
  the author.
- The interpreter name. `python3` versus `python` is a stated platform trade documented inside the
  settings file itself, and it is not this task's to reopen.

## Implementation notes

The existing `_entries()` helper already yields `(source name, [(command, matcher)])` pairs from two
JSON wirings, and `_flatten()` reads any lifecycle event rather than a hardcoded one, which is the
shape to reuse. `.claude/settings.json` has the same `hooks` structure, so it can be flattened by the
same helper.

The assertion is narrower than the existing ones and that is the point: for each command, extract the
script path it names and assert the file is present under `.agents/hooks/`. Extracting a path out of a
command string is the fiddly part, since the printed Claude registration quotes an absolute path while
this one is bare and relative. Match on the hook filename rather than parsing the command, which is
what `matcher_sources()` already does with `self.HOOK in cmd`.

Add the assertion to `WiringConsistencyTests` rather than a new class, and extend that class's
docstring to say there are four wirings and why only three carry the every-hook rule. A test whose
name claims a property it does not check is the defect `feat-0046` found in this very class.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test asserting every command in `.claude/settings.json` names a file that exists under
      `.agents/hooks/`.
- [ ] The test fails if the hook it names is renamed, demonstrated by pointing it at a non-existent
      name in a temporary copy rather than by assertion alone.
- [ ] The existing every-hook-everywhere assertion is unchanged and still covers exactly the three
      wirings it covers today.
- [ ] `WiringConsistencyTests`'s docstring names all four wirings and states which rule applies to
      which.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
