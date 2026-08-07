---
id: feat-0046
title: Tell a session at startup when the kit's skills are not reachable
type: feat
status: open
priority: P1
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-008", "S-009", "S-010", "S-011", "S-012", "S-013", "S-014", "S-015", "S-016"]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - tests/test_hooks.py
  - .agents/hooks/README.md
  - .codex/hooks.json
  - .opencode/plugins/zen-hooks.mjs
  - AGENTS.md
created: 2026-08-07
---

## Problem

A session can start in this repository with none of the kit's skills loaded, do a full piece of work,
and never say so. Verified 2026-08-07: `git ls-files .claude` returns nothing, and
[`install.py`](../scripts/install.py) places skills at user scope (`~/.claude/skills`,
`~/.agents/skills`), which a fresh clone does not have. The repository that builds this kit is the
one place the kit is reliably absent.

The output of such a session looks exactly like output produced with the skills. Nothing distinguishes
them, which is the same silent-wrong-result shape as a stale installed skill (`chore-0031`) and an
inert hook (`feat-0038`).

Contract: [`cloud-executable.md`](../docs/spec/cloud-executable.md), `S-008` to `S-016`.

## Scope

**In scope:** a `SessionStart` reminder hook that reports when no kit skill is reachable at project or
user scope, its registration across the three harness wirings, and the `install.py` change that
registration needs.

Files this creates, deliberately absent from `touched_files` (see Implementation notes):

- `.agents/hooks/skill-reachability-reminder.py`
- `.claude/settings.json`

**Out of scope:**

- **Installing, copying, or repairing anything.** The hook reports. This is rule `A3` and the whole
  principle of [`autonomy.md`](../.agents/rules/autonomy.md).
- **Answering whether a reachable skill is current.** That is `install.py --check`. `S-011` states
  that the hook's silence means reachable and never means current, and the reason it is not consulted
  is that walking a digest of every installed file would sit in front of every session start.
- **Any environment or cloud detection** (`S-016`). There is no shared signal across the harnesses,
  so detection means one implementation per harness for a single question.
- **Committing `.claude/skills/` or the adapter trees.** `S-009` defines how project-scope skills are
  counted if present and requires none to be.
- Firing on `clear` (open question 1 in the contract recommends against it for v1).

## Implementation notes

**`touched_files` lists only files that already exist**, for the same reason and with the same
precedent as [`feat-0045`](feat-0045-committed-acceptance-command.md): `--strict` errors on a missing
path (`validate.py:456`) and CI runs it.

**`install.py`'s registration builder cannot express this hook today, and that is the load-bearing
finding.** `HOOK_REGISTRATIONS` at `install.py:329` is a list of `(script, matcher)` pairs with no
event, and `claude_registration()` hardcodes the event by dumping
`{"hooks": {"PostToolUse": entries}}` at `install.py:373`. Both existing hooks are `PostToolUse`. A
`SessionStart` hook added without widening that structure is **placed by `--with-hooks` and never
registered**, which is precisely the "installed, correct-looking, and doing nothing" failure that bit
`feat-0038` twice. Widen the table to carry an event, and keep the docstring's stated property: a hook
added to the module without an entry here shows up as a missing entry, not as a hook that never fires.

**The Claude Code registration is a committed `.claude/settings.json`, not the printed snippet**, and
this is a deliberate exception to a rule the kit states absolutely. `AGENTS.md` says hook installation
is opt-in and "activation is theirs". A committed project-scope settings file activates the hook for
every collaborator who opens this repository, nobody having opted in. Verified against Anthropic's
Claude Code documentation on 2026-08-07: a project `.claude/settings.json` is checked in and applies
to all collaborators, and a user-level one does not reach a cloud session, so there is no other
mechanism that works in the case this hook exists for. **Write the exception into `AGENTS.md` beside
the rule it bends.** An unstated exception is how a contract quietly stops meaning anything.

**Two facts verified against the same documentation on 2026-08-07**, so neither needs rediscovering:
`SessionStart` carries `source` with values `startup`, `resume`, `clear`, `compact`, and `fork`, and
those are valid matcher values; and `additionalContext` inside `hookSpecificOutput` is the context
injection field.

**The hook module contract is in [`.agents/hooks/README.md`](../.agents/hooks/README.md)** and is not optional:
always exit 0, at most one JSON object on stdout, never import from this repository, expose an
injectable `main(stdin, stdout)`, and use two-stage filtering because the harness matcher is the
coarse filter. Mirror `delegation-reminder.py`, which is the reminder-shape prior art.

**Tests are not optional here and must cover the silent path.** The README requires the fire path, the
silent path, and malformed input. `S-010` makes silence a contract clause rather than an
implementation choice, so a hook that reports on every start is a defect, and a test that only asserts
the fire path would pass on it.

**`feat-0045` also edits `AGENTS.md`.** These two tasks are **not parallel-safe** for that reason.
Dispatch them sequentially, or expect a collision on that one file.

## Risks and rollback

Required: this touches more than one module (the hooks module, `install.py`, three harness wirings,
and `AGENTS.md`), and it changes the shape of `HOOK_REGISTRATIONS`, which every `--with-hooks` run
reads.

- **The failure that costs most is a hook that is registered and never fires**, because it is
  indistinguishable from a hook that fired and found nothing wrong. That is the same failure twice
  over in `feat-0038`. Prove firing with a test, not by reading the registration.
- **The second-worst is widening `HOOK_REGISTRATIONS` in a way that breaks the two existing
  registrations.** They are `PostToolUse` and must stay exactly as they are; `tests/test_install.py`
  already pins the registration output, so extend those assertions rather than replacing them.
- **A committed `.claude/settings.json` runs for every collaborator.** Keep it to this one hook, and
  keep the hook a reminder that never blocks and never writes, so the blast radius of the exception is
  one injected paragraph.
- Rollback is one revert plus deleting `.claude/settings.json`. Nothing persisted changes format.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] With no kit skill at project or user scope, the hook injects context naming the unreachable
      state and the command that would place them (`S-008`).
- [ ] Skills at project scope count as reachable and the hook stays silent (`S-009`).
- [ ] Skills at user scope count as reachable and the hook stays silent (`S-010`).
- [ ] A test proves the silent path, so a hook that speaks on every start fails rather than passes.
- [ ] A reachable-but-stale install is silent, and the module documents that silence means reachable
      and never current (`S-011`).
- [ ] Skills present with no manifest are reachable to the hook, while `install.py --check` still
      exits 2 for the same home (`S-012`).
- [ ] Sources `resume`, `clear`, `compact`, and `fork` produce no output (`S-013`).
- [ ] No file anywhere is created, modified, or removed by any run, including a cache or marker of its
      own (`S-014`).
- [ ] Malformed or unparseable input emits nothing and exits 0 (`S-015`).
- [ ] Nothing in the hook inspects the environment it runs in (`S-016`).
- [ ] `HOOK_REGISTRATIONS` carries an event, `claude_registration()` no longer hardcodes
      `PostToolUse`, and the two existing registrations are unchanged in output.
- [ ] Registered in all three wirings and added to the table in `.agents/hooks/README.md`.
- [ ] `.claude/settings.json` is committed, and `AGENTS.md` records the opt-in exception beside the
      rule it bends.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
