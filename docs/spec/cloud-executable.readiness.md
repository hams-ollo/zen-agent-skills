# cloud-executable: readiness

Go/no-go gate over [`cloud-executable.md`](cloud-executable.md) (`status: approved`, 19 scenarios)
plus its task decomposition, run 2026-08-07 by `spec-plan-readiness` before any implementation began.

A ledger: it records what was true on the date it ran and is not rewritten when the code moves.

## What was gated

| Input | Value |
|---|---|
| Spec | [`cloud-executable.md`](cloud-executable.md), approved 2026-08-07, `S-001` to `S-019` |
| Decomposition | [`feat-0045`](../../.tasks/feat-0045-committed-acceptance-command.md), [`feat-0046`](../../.tasks/feat-0046-session-start-reachability-hook.md) |

[`feat-0044`](../../.tasks/feat-0044-autonomy-rules-module-v1.md) was deliberately **excluded**. It
serves Epic E item 1, carries no `spec` field, and is not decomposed from this contract. Including it
would have produced a task traceable to no scenario, which this gate blocks on, and forcing a mapping
to make the gate pass would have been the gate failing at its own job.

## An earlier run of this gate returned blocked

The first invocation, before the task files existed, short-circuited at step 1 with
`source: plan`: the decomposition had been described in prose rather than supplied as readable task
files, so nothing carried `touched_files`, `depends_on`, acceptance criteria, or risk notes.

Recorded because the outcome is the point. A readiness verdict computed over a decomposition that
did not exist would have been a gate that never ran, filed as a gate that passed. It also exposed an
inverted ordering in the plan this work came from, which had readiness running before authoring; a
gate over a decomposition needs the decomposition first.

## Verdict

```text
verdict: implementable
blocking_gaps: []
first_safe_task: feat-0045
```

## Scenario-to-test map

Layers use this repository's own taxonomy: `unittest` under `tests/`, run by
`python -m unittest discover -s tests -p "test_*.py"`.

| Scenario | Recommended layer | Why |
|---|---|---|
| `S-001` | unit, stubbed gate table | The behaviour is "every gate ran and the exit code aggregates them", which is decidable without executing seven real gates. |
| `S-002` | unit, stubbed gate table | Needs one gate to fail and later ones to still run. A stub makes the failure deterministic; a real gate would have to be broken on purpose. |
| `S-003` | unit, stubbed gate table | Same reason, with a gate whose command cannot execute. Also pins that 2 outranks 1. |
| `S-004` | integration, real install against a temp home | The claim is about filesystem side effects, so a stub would assert nothing. This is the one gate that must run for real. |
| `S-005` | unit, parsing `checks.yml` | "CI calls the command rather than restating the gates" is a property of a checked-in file, readable without running CI. |
| `S-006` | unit, on the summary string, plus a check that `AGENTS.md` carries the sentence | Both halves are string properties of committed artifacts. |
| `S-007` | **not unit-testable here**, and deliberately so | The claim is that the six-cell CI matrix catches what one local run cannot. Only the matrix can demonstrate it; a local test asserting it would be asserting its own premise. Evidence is a real CI run. |
| `S-008` | unit, `main(stdin, stdout)` with a crafted payload and a temp filesystem | The established shape in `tests/test_hooks.py`. Injectable streams make it reachable without a subprocess. |
| `S-009` | unit, as above, skills at project scope only | Distinguishes the two scopes. |
| `S-010` | unit, as above, skills at user scope only | **The silent path, and the one most likely to be skipped.** A suite testing only the fire path passes on a hook that speaks every time, which `S-010` makes a defect. |
| `S-011` | unit, as above, reachable but digest-diverged | Asserts silence, not a report. |
| `S-012` | unit for the hook, plus the existing `test_install.py:1079` for `--check` | Two tools answering two questions about one state. The `--check` half is already covered; assert the pairing rather than duplicating it. |
| `S-013` | unit, one case per `source` value | Four cases: `resume`, `clear`, `compact`, `fork`. |
| `S-014` | integration, tree snapshot before and after | "Writes nothing anywhere" is not provable by inspecting output. |
| `S-015` | unit, malformed and unparseable stdin | Required by the hooks module contract. |
| `S-016` | unit, two runs with differing environment, byte-compared | The observable form of "no environment detection". |
| `S-017` | **evidence, not a test** | A cloud session is a one-time event. Recorded in `cloud-executable.verification.md`. |
| `S-018` | **evidence, not a test** | As above. The discriminating artifact is `bug-0018`'s regression test failing before the change and passing after. |
| `S-019` | **evidence, not a test** | As above, for the failing-gate path. |

## Task-to-scenario map

| Task | Scenarios | Notes |
|---|---|---|
| `feat-0045` | `S-001` to `S-007` | Whole acceptance-command surface. `S-007` has no in-repo test layer by design; see above. |
| `feat-0046` | `S-008` to `S-016` | Whole bootstrap surface. Carries the `install.py` registration widening, without which the hook is placed and never fires. |
| none | `S-017`, `S-018`, `S-019` | **Deliberately not decomposed.** See below. |

## Why three scenarios map to no task

`S-017` to `S-019` describe the cloud proof run. They are not implementable work and are not withheld
by oversight:

1. **They specify an event, not an artifact.** Nothing is built to satisfy them. They are satisfied by
   running `bug-0018` through a cloud session and observing what happened.
2. **Their evidence is a verification record, not a test.** A cloud session happens once and cannot be
   re-run by a suite, so filing it under `tests/` would produce a test that either never runs or
   asserts nothing. It belongs in `cloud-executable.verification.md`.
3. **Decomposing them now would be speculative.** The work-altitude-model section of `AGENTS.md`
   permits decomposing a Feature only when it is about to be built, and the run is gated on an
   explicit human go-ahead that has not been given.

They are therefore mapped to a stated rationale rather than to a task, which is what this gate
requires instead of silence.

## Two things the gate passed that a reader should still know

Neither is a blocking gap. Both are recorded because they are invisible in the maps above.

**`feat-0045` and `feat-0046` are independent but not parallel-safe.** Both declare `depends_on: []`,
which is accurate: neither needs the other in `done/`. Both also edit `AGENTS.md`, so dispatching them
to simultaneous isolated agents collides on that one file. A `depends_on` edge was deliberately not
added, because it would misstate the relationship as sequencing when it is a shared-file conflict.
Dispatch them one after the other, or expect to reconcile that file.

**Both task files omit the files they create from `touched_files`, and that is a contradiction in the
kit rather than a defect in the tasks.** The `new-task` skill says to list a test file at the path it
should be created at; `.tasks/validate.py:456` promotes a missing path to an error under `--strict`,
and CI runs `--strict`. The two rules cannot both be satisfied.
[`feat-0038`](../../.tasks/done/feat-0038-hooks-module-and-delegation-reminder.md) met the same
conflict and resolved it the same way, listing only pre-existing files while creating an entire
module. The convention works, has never been written down, and is worth its own task.
