---
id: feat-0071
title: Place the sitrep into Claude Code sessions with a session-start hook, the reporting rules, and its registration
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: [feat-0070]
spec: docs/spec/sitrep.md
scenarios: [S-027, S-029, S-030, S-031, S-032]
touched_files:
  - .agents/hooks/
  - .agents/hooks/README.md
  - .agents/rules/
  - .agents/skills/
  - .codex/hooks.json
  - .opencode/plugins/zen-hooks.mjs
  - scripts/install.py
  - docs/CATALOG.md
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

The board is only a sitrep when it is already in the session before the person asks. This task adds the
session-start hook that puts it there, carries the reporting rules with it, and registers the hook the
way the rest of the hooks module is registered: printed at user scope for the person to place.

## Scope

**In scope:** a reminder hook on `SessionStart` for every source (startup, resume, clear, compact) that
adds the sitrep and the reporting rules to the session's context and records which revision it
described; silence outside a git repository and when the skill is not installed; one line naming the
failure, and never a blocked session or a recorded hook failure, when the board cannot be produced.

Files this task creates, with their exact paths:

- `.agents/hooks/sitrep-session-start.py`: the hook.
- `.agents/rules/sitrep.md`: the swappable rules module restating the tier ladder, the status
  meanings, and the reporting rules for agents, with the spec's names.
- `docs/spec/sitrep.runbook.md`: how the author places the draft skill and pastes the registration for
  himself, since a draft is placed by no install profile.
- `tests/test_hooks_sitrep.py`: the hook's tests.

Files this task edits: `scripts/install.py` (one `HOOK_REGISTRATIONS` entry, with an empty matcher so
every source fires), `.codex/hooks.json` and `.opencode/plugins/zen-hooks.mjs` (every hook in the
module is wired into each harness it supports; the spec's Non-Goals say so since the author's
decision of 2026-09-11), `.agents/hooks/README.md` (its table), `docs/CATALOG.md` (the drafts table and the hooks
table), and `.agents/skills/sitrep/SKILL.md` (the session-start half).

**Out of scope:** committing a registration into any repository, which the spec forbids, and any cloud
session.

## Implementation notes

- The hook honours `.agents/hooks/README.md`: one JSON object or nothing on stdout, exit 0 on every
  path, standard library only, `main(stdin=None, stdout=None)`, and no import from this repository and
  no `sys.path` edit, which `tests/test_hooks.py` checks.
- It runs the skill as a separate program rather than importing it, and it looks for the skill only
  in the person's own user-scope install: `~/.claude/skills/sitrep/` for Claude Code, then
  `~/.agents/skills/sitrep/`, the base `install.py` uses for opencode. Absent means not installed,
  and the hook is silent. It deliberately does not look beside itself: in this repository the
  skill's source sits next to the hook, and a Codex or opencode session here would otherwise show a
  board to someone who never installed it, which `S-032` forbids.
- The interpreter the hook uses to run the skill is its own, `sys.executable`, so the `python3` trap
  (`bug-0050`) cannot recur inside it.
- Scenario layers: S-031 and S-032 are process-level tests that run the hook as the harness does, with
  a payload on stdin; S-027, S-029 and S-030 run it against a throwaway repository with the skill
  present or broken.

## Risks and rollback

Required: this touches more than one module (the hooks module, the installer, three harness wirings,
the rules modules, the catalog), and a `SessionStart` hook runs inside every session of whoever
registers it.

- **What could go wrong.** A hook that throws or hangs degrades every session start. Mitigation: the
  exit-0 contract, a timeout on the child process, and S-030's one-line fallback.
- **Rollback.** Revert the one commit. Anyone who pasted the printed registration removes that
  `SessionStart` entry from their own settings by hand, because `install.py` prints registrations and
  never edits settings; `install.py --uninstall` removes the placed hook file.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_hooks_sitrep.py" -v
    python -m unittest discover -s tests -p "test_hooks.py" -v
    python scripts/run-checks.py

- [ ] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [ ] `tests/test_hooks.py` passes unchanged, including the every-hook wiring rule.
- [ ] The rules module's tier names equal the spec's, checked by a test.
- [ ] `docs/spec/sitrep.conformance.md` classifies every scenario in the spec.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
