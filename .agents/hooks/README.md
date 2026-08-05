# Hooks: the enforcement module

Every other rule in this kit is enforced by prose. A skill body tells an agent what to do, and the rule holds for exactly as long as the model keeps it in context. That works for rules an agent consults deliberately, like the rubric in [`review-quality.md`](../rules/review-quality.md). It fails for rules that must fire at a moment the agent is not thinking about them.

A hook is a small Python program the harness runs at a lifecycle event. It reads one JSON payload on stdin and writes at most one JSON object to stdout. That is the whole interface.

## The two shapes

A hook is one of exactly two things, and which one it is must be obvious from its docstring.

**A reminder** injects context and never blocks. Use this when the condition you care about cannot be decided from the payload alone. A reminder is cheap to be wrong about: the worst case is a line of text the agent did not need.

**A gate** blocks and states why. Use this **only** when the condition is decidable from the payload plus the files on disk, with no interpretation of prose. A gate that guesses is worse than no gate, because a false block stops real work for a reason the user cannot see, in their repository rather than ours.

The test for which shape you are writing: could a careful person disagree with the hook about whether the condition holds? If yes, it is a reminder.

## The contract every hook honors

| Rule | Why |
|---|---|
| stdin is one JSON object; stdout is one JSON object or nothing | The harness parses stdout. Two objects, or prose, corrupts the exchange. |
| **Always exit 0**, including on failure | A guardrail that breaks a session because it could not parse its own payload is worse than no guardrail. Wrap the body; swallow and exit. |
| Standard library only | Per the conventions section of `AGENTS.md`. A hook runs on a bare Python 3 wherever the adopter installed it. |
| Never import from this repository | A hook ships without this repository around it, the same portability contract skills carry. No relative imports, no shared helper module. |
| Two-stage filtering | The harness matcher is the coarse filter and may be broad. The precise check lives inside the hook, so a matcher wide enough to catch `Task` never fires on `TaskCreate`. |
| Expose `main(stdin=None, stdout=None)` | Injectable streams make the behavior reachable from a test without spawning a subprocess. |

## Output shapes

A reminder injects context:

```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}
```

A gate refuses, and its reason must name the way out:

```json
{"decision": "block", "reason": "... run <skill> first, or add <field> to declare it intentional."}
```

A block with no stated escape is a trap. Whoever hits it has to read the source to get unstuck, and will more likely just uninstall the hook.

## What is here

| Hook | Shape | Event | Fires when |
|---|---|---|---|
| [`delegation-reminder.py`](delegation-reminder.py) | reminder | `PostToolUse` | a delegated agent's report returns |
| [`spec-conformance-gate.py`](spec-conformance-gate.py) | **gate** | `PostToolUse` | work a contract governs is closed with no conformance matrix |

The gate recognises two closing shapes for one rule. A spec file reaching a terminal status is the portable shape, for repositories whose specs carry a closing status. A task file carrying a `spec:` reference being set to `status: done` is the shape this kit uses, and without it the gate would be inert here: this repository's spec lifecycle is `draft` then `approved` and stops. **A guardrail that cannot fire in the repository that ships it is one nobody has ever seen work.**

`approved` is deliberately not a terminal status, and a test pins that. Treating it as one blocks a human approving a brand-new spec and demands an audit of an implementation that does not exist yet, which is the normal workflow here.

## Wiring

One implementation, three thin adapters. The hook file is the single source of truth; each harness gets a registration that points at it rather than a copy of it.

- **Claude Code**: place the module at `~/.claude/hooks/` and register the event in `~/.claude/settings.json`. `scripts/install.py --with-hooks` places the files and prints the registration snippet; it does not edit your settings for you.
- **Codex**: repo-scoped via `.codex/hooks.json`.
- **opencode**: repo-scoped via `.opencode/plugins/zen-hooks.mjs`, which shells out to the same Python.

Installation is opt-in and reversible. These are the only artifacts in the kit that execute inside a user's session, so they are the only ones that require asking.

## Adding one

Before writing a hook, be able to answer three questions. If any answer is soft, the rule is not ready for enforcement and belongs in a skill body instead.

1. What rule does this enforce, and where is that rule already written down?
2. Is the condition decidable from the payload, or does it require reading prose? (This picks the shape.)
3. What does someone do who hits it and disagrees?

Then: write it, add tests to `tests/test_hooks.py` covering the fire path, the silent path, and malformed input, register it in all three wirings, and add a row to the table above.
