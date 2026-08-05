---
id: feat-0038
title: Establish .agents/hooks/ as a portable module and seed it with delegation-reminder
type: feat
status: in_progress
priority: P1
parent: "ROADMAP Epic B #13: telemetry-guard (reframed as enforcement hooks)"
depends_on: []
touched_files:
  - scripts/install.py
  - AGENTS.md
  - docs/INSTALL.md
  - docs/CATALOG.md
created: 2026-08-05
---

## Problem

`.agents/hooks/` exists in this repository and is empty. Every rule the kit enforces today is
enforced by prose: a skill body tells an agent what to do, and the rule holds only for as long as
the model keeps it in context. That works for rules an agent consults deliberately, like the rubric
in [`review-quality.md`](../.agents/rules/review-quality.md). It fails for rules that must fire at a
moment the agent is not thinking about them.

The clearest case is delegated work. `AGENTS.md` and the user's own global rules both say that a
subagent's report is a claim rather than evidence, and that the delegating agent must verify against
a real diff, test run, or rendered behavior. Nothing enforces it. The failure is not hypothetical
here: two of three agents in the `feat-0025` batch worked from task files whose premise was
factually wrong about the code, and the system captured none of it. That is the observation that
produced [`feat-0037`](feat-0037-task-file-decision-log-v1.md), which records decisions after the
fact. It does not add a checkpoint at the hand-off itself.

Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT) ships
four hooks and the wiring for three harnesses. The transferable design is the split between two
shapes: a **reminder** injects context and never blocks, and a **gate** blocks only when the
condition is deterministically checkable from the payload. Upstream's `delegation-reminder.py` is
the reminder case, and its own docstring is explicit that a true gate here would require parsing the
report to learn which files were claimed, which is brittle and false-positive prone.

This task establishes the module and its distribution, and proves both with the lowest-risk hook in
the set. The blocking gate follows separately in `feat-0039`.

## Scope

**In scope:**

- Author `.agents/hooks/delegation-reminder.py`, adapted from upstream rather than copied verbatim:
  standard library only per the conventions section of `AGENTS.md`, `PostToolUse` on the delegation
  tool set, emitting `hookSpecificOutput.additionalContext`. Its reminder text must point at this
  kit's own rules module, not upstream's `rules/global.md`, which does not exist here.
- Author `.agents/hooks/README.md` stating the module's contract: the two hook shapes, the payload
  fields a hook may rely on, the JSON output contract for each shape, and the rule that a gate is
  permitted only when its condition is decidable from the payload alone.
- Wire the three harnesses, following upstream's pattern: a Claude Code registration merged into
  settings, a repo-scoped `.codex/hooks.json`, and an `.opencode/plugins/` adapter that shells out
  to the same Python. One implementation, three thin adapters.
- Teach [`install.py`](../scripts/install.py) to carry the hooks module, reusing its existing
  symlink/copy mode handling and CONFLICT detection rather than adding a second install path.
- Add unit tests under `tests/` driving each hook's `main()` with synthetic payloads.
- Document the module in `AGENTS.md` (layout table and conventions) and in `docs/CATALOG.md` and
  `docs/INSTALL.md`.

New files this task creates, named here because CI runs `.tasks/validate.py --strict` and that
promotes a not-yet-existing `touched_files` entry to an error: `.agents/hooks/delegation-reminder.py`,
`.agents/hooks/README.md`, `.codex/hooks.json`, `.opencode/plugins/zen-hooks.mjs`,
`tests/test_hooks.py`.

**Out of scope:**

- `spec-conformance-gate`, the blocking gate. It is `feat-0039` and depends on this module existing.
- `test-quality-reminder`. Upstream's version carries several hundred lines of shell-command parsing
  to decide whether a `Bash` call was a test run, with wrapper-word stripping, package-manager
  subcommand exclusion, and help-flag detection. The Stop-gate pattern it demonstrates is worth
  having; that specific heuristic pile is not worth importing before the module has proven itself.
  Deferred deliberately, recorded in `chore-0026`.
- Any telemetry, budget, or retry-limit mechanism. That is the other half of the reframed Epic B #13
  and is not needed to make a reminder fire.
- Changing what any existing skill says. Hooks add a checkpoint around the skills; they do not edit
  them.

## Implementation notes

Read the upstream sources before writing, at
`https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/hooks/`. Adapt, do not
copy: upstream's file targets RepoPrompt CE and references its own rules module and tool names. The
one detail worth preserving exactly is the two-stage filter, a broad matcher in the harness
registration plus a precise tool-name set inside the hook, so a matcher wide enough to catch
`Task` can never fire on the unrelated `TaskCreate` and `TaskUpdate` tools that merely contain the
word.

The delegation tool set upstream uses is `{Task, TaskOutput, mcp__RepoPromptCE__agent_run}`. Keep
the first two, drop the RepoPrompt-specific one, and decide from the harness registration whether
any others belong.

The portability contract in section 5 of `AGENTS.md` is the constraint that shapes this work. A
skill ships without this repository around it, and the same must hold for a hook: it cannot import
from `scripts/`, and it cannot assume a path that only exists here. Keep each hook a single
self-contained file that reads a JSON payload on stdin and writes at most one JSON object to stdout.

Attribution follows the pattern already used for the Phase 1 fold-ins: credit Balarama Bosch and the
MIT license in `NOTICE` and in the hook's own docstring.

## Risks and rollback

This touches more than one module (`.agents/`, `scripts/`, `docs/`, `tests/`, plus two new harness
directories), so the rule fires.

The real risk is not the code, it is the support surface. A hook is the kit's first artifact that
runs inside a user's session on someone else's machine, and a badly behaved one blocks work for
reasons the user cannot see. Three mitigations, all in scope:

- A hook that raises must exit 0 and emit nothing. Upstream's files already do this, wrapping the
  payload parse in a bare `except` and falling through to `sys.exit(0)`. Preserve that.
- Ship the reminder shape first precisely because it cannot block anything.
- Installing the hooks module must be opt-in, or at minimum reversible by re-running the installer.
  Verify with the existing `install.py --dry-run` CI step before landing.

Rollback is a single revert: the module is additive, and no existing skill's behavior changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" -v && python scripts/validate-skills.py && python scripts/install.py --dry-run --home ./.tmp/zen-home

- [ ] New tests in `tests/test_hooks.py` drive `delegation-reminder`'s `main()` with a synthetic
      `PostToolUse` payload and assert the reminder is emitted for each tool in the delegation set.
- [ ] A test asserts the hook emits nothing for a non-delegation tool whose name contains `Task`
      (for example `TaskCreate`), proving the precise filter and not just the matcher.
- [ ] A test asserts malformed stdin exits 0 and emits nothing.
- [ ] `install.py --dry-run` reports the hooks module in its plan, and re-running over an existing
      install does not report CONFLICT against its own output.
- [ ] Existing tests still pass.
- [ ] `NOTICE` credits Balarama Bosch (MIT) for the adapted hook.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
