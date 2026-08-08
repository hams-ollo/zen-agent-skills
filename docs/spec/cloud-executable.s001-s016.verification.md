---
title: cloud-executable verification (S-001 to S-016)
spec: docs/spec/cloud-executable.md
task: .tasks/done/feat-0045-committed-acceptance-command.md
verified: 2026-08-07
verdict: fail
branch_exercised: S-001 to S-016, by an independent session
---

# cloud-executable verification record: S-001 to S-016

An independent verification of [`feat-0045`](../../.tasks/done/feat-0045-committed-acceptance-command.md)
and [`feat-0046`](../../.tasks/done/feat-0046-session-start-reachability-hook.md) against
[`cloud-executable.md`](cloud-executable.md), run 2026-08-07 by a session that did not write the
implementation.

A ledger. **The verdict below is `fail` and stays `fail`.** The defects were fixed the same day, and
the fixes are recorded at the end rather than by editing the verdict, because a record rewritten to
match a later state stops being evidence of anything.

This is separate from [`cloud-executable.verification.md`](cloud-executable.verification.md), which
records the blocked cloud proof run (`S-017` to `S-019`). Different question, different date,
different verdict.

## Why it was run at all

The implementing agent verified its own work. That is what
[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) exists to prevent: "the agent that
verifies should not be the agent that wrote the implementation." The gap was real rather than
procedural, and closing it found two unmet acceptance criteria plus a defect more serious than
either.

## Result

```text
verdict: fail
scope: S-001 to S-016. S-017 to S-019 are the cloud proof run and were out of scope.
conformance: 16 of 16 in-scope scenarios Conformed as written
criteria: feat-0045 8 met / 2 unmet / 1 partial, feat-0046 14 met
```

All four declared commands passed. **The contract holds; two of its guards did not.** That gap is the
finding: an implementation can be correct while the tests claiming to protect it prove nothing.

## The two unmet criteria

Both belong to `feat-0045`, and both are about test strength rather than behaviour. Both were proven
by mutation, not by reading.

**1. The `S-005` restatement guard was vacuous for five of the seven gates.**
`test_ci_does_not_separately_restate_any_gate` built assertions of the form
`assertNotIn("run: python --strict", workflow)`, using each command's *last token*. A real restatement
reads `run: python .tasks/validate.py --strict`, so those strings could never appear and the
assertions could never fail. Four genuine restatements were reinserted into `checks.yml` and the suite
stayed green. Only two hardcoded lines did any work, while the test's own comment claimed it made the
`chore-0029` lesson "mechanical for all seven".

**2. The pinned gate list covered names and one trailing token, not commands.**
Dropping a whole gate was caught. Two narrowings were not: swapping a gate's script for a different
one sharing a trailing token, and **deleting the install cycle's second run**, which is the entire
idempotence proof. That is precisely the "silently narrowing what is checked" the criterion names.

## The finding that mattered more than the verdict

**The one registration written for cloud sessions named the interpreter this repository already
knows is wrong there.** `.claude/settings.json` hardcoded `python`. Every other wiring disagrees:
`install.py`'s `hook_interpreter()` returns `python3` off Windows, `.codex/hooks.json` uses `python3`,
and the opencode adapter probes both and says in a comment that most platforms ship `python3`.

Cloud sessions run on Linux, where many distributions ship no `python` at all, and macOS has not
since 12.3. The hook would not have launched, would have emitted nothing, and the session would have
continued looking exactly as it does when skills are reachable.

Three things make this worth recording beyond the fix:

- It is the `feat-0038` failure in mirror image. That one was `python3` resolving to the Windows Store
  alias; this one is `python` not existing on Linux. The same lesson, learned once, was not applied to
  the one file written after it.
- It would have struck **in the exact environment the committed-settings exception was granted for**,
  and `feat-0046`'s own Risks section names "registered and never fires" as the costliest failure
  available to it.
- **No test read `.claude/settings.json` at all.** The file was reviewed, documented in `AGENTS.md`,
  and unguarded.

## Weaker guards, found but not blocking

| # | Guard | Defeated by |
|---|---|---|
| 1 | `S-014` "writes nothing anywhere" | writes to `Path.home()`, to `tempfile.gettempdir()`, or from `main()` rather than `evaluate()`. The snapshot covered one directory through one entry point |
| 2 | `S-008` "names the way out" | replacing the placing command with "(ask your administrator)". `assertIn("install.py", ...)` still matched the currency caveat elsewhere in the same message |
| 3 | `S-016` no environment detection | `socket.gethostname()`, and `sys.platform ==` which contains no `platform.` substring |
| 4 | `FIRING_SOURCES` allowlist | inverting it to a denylist of the four continuing sources. Every source anyone thought to test was named in it |

## What held up

Recorded because a verification that only lists faults is not a verification.

- **Exit-code precedence proved end to end against real gates**, not stubs: a run with three failed
  gates and one unrunnable returned 2; the same run with only failures returned 1. `S-001`, `S-002`,
  and `S-003` all hold.
- **Thirteen hook mutations were caught**, including always-report, never-report, fire-on-every-source,
  ignoring either scope, and treating an empty discovery directory as reachable. `S-010`'s silent path
  is genuinely guarded by four separate tests.
- **`S-004` filesystem containment confirmed** by a before-and-after diff over a full copy. The only
  write outside the throwaway home was `scripts/.install-manifest.json`, which is gitignored, is the
  tool's own record, and was anticipated in the task's implementation notes.
- **The `.claude/settings.json` exception is documented where it belongs** and its stated scope matches
  the file: one hook, reminder shape, `startup` only.

## Not verified

- **macOS and Linux.** The standard-library claim was confirmed by reading imports and the run was
  confirmed on Windows only. No such host was available. **Closed 2026-08-07, see below.**
- **`S-017` to `S-019`.** Out of scope, and separately blocked.

### Cross-platform limitation closed, 2026-08-07

All six CI matrix cells passed on
[run 31213244638](https://github.com/hams-ollo/zen-agent-skills/actions/runs/31213244638):
`ubuntu-latest` and `macos-latest` and `windows-latest`, each on Python 3.11 and 3.14. Since
`checks.yml` now calls `run-checks.py` and nothing else, every one of those cells is a full run of
the acceptance command, so the `partial` criterion "standard library only; passes Windows, macOS, and
Linux" is now met rather than partially met.

The same run is the evidence `S-007` was waiting for. That scenario was recorded in the readiness
report as having no in-repo test layer by design, because a local test asserting that the matrix
catches what one local run cannot would be asserting its own premise. Six green cells against one
green local run is the observation itself.

## Disposition, applied the same day

Every item above was fixed, and each fix was confirmed by re-running the mutation that had defeated
the original guard. Eight mutations that previously survived are now caught:

| Mutation | Before | After |
|---|---|---|
| Restate the backlog gate in `checks.yml` | survived | caught |
| Drop the install cycle's idempotence run | survived | caught |
| Swap a gate's script, same trailing token | survived | caught |
| Hook writes a marker into home from `main()` | survived | caught |
| `socket.gethostname()` host detection | survived | caught |
| Report drops the placing command | survived | caught |
| `FIRING_SOURCES` inverted to a denylist | survived | caught |
| `settings.json` reverts to bare `python` | survived | caught |

Two changes are worth naming beyond the list.

**The two structural guards are parsed now, not substring-matched.** The first widened version of the
environment guard failed on the word "subprocess" inside a docstring that explains why the hook does
*not* spawn one. A guard that fires on its own documentation gets loosened until it catches nothing,
so both guards use `ast` to inspect imports, calls, and attribute chains.

**`.claude/settings.json` now says `python3`, and the trade is stated rather than hidden.** A static
JSON file cannot probe, so it cannot be right on both platforms at once. Cloud sessions are the reason
the file is committed, so they win; a Windows developer overrides it in the untracked
`.claude/settings.local.json`, which is Claude Code's own mechanism for exactly that. Six tests now
cover the file, including one asserting the interpreter and one asserting the `AGENTS.md` bound of one
hook.

## What would have made this a pass

The verifying session was asked to state this, and did: the `checks.yml` restatement guard rejecting a
restated gate, and the gate-set pin covering commands rather than a single trailing token. Everything
else held under adversarial mutation. Its own summary is the fair one: **the implementation is sound;
two of its guards were weaker than the task files claimed.**
