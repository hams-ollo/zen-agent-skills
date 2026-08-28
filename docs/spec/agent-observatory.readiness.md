---
title: agent-observatory readiness
spec: docs/spec/agent-observatory.md
task: .tasks/feat-0053-the-observatory-store-and-its-incremental-ingester.md
gated: 2026-08-28
verdict: implementable
---

# agent-observatory readiness gate record

A [`spec-plan-readiness`](../../.agents/skills/spec-plan-readiness/SKILL.md) run over
[`agent-observatory.md`](agent-observatory.md), approved 2026-08-28, plus the eight-task decomposition
`feat-0053` to `feat-0060` authored the same day.

**The first pass returned `blocked` and this record is of the re-run.** Recording only the passing
verdict would misrepresent what the gate did, so both are below. The two gaps are named, and each is a
real defect the gate exists to catch rather than a formality.

## First pass: blocked, two gaps

Both were the deterministic risk rule firing on a task that carried no `Risks and rollback` section.
The rule requires one when a task touches more than one module, changes a persisted data format or
protocol, or cannot be reversed by reverting one commit.

| Source | Task | Gap | Resolution |
|---|---|---|---|
| plan | `feat-0055` | Adds a live-session reader to the ingester **and** a report to the page shell, which is more than one module, and holding live-session state likely adds a table, which is the second condition as well. No section. | Section added, covering a registry entry outliving its process and the summing property `S-018` requires. |
| plan | `feat-0057` | Creates the rate table, reads the quota source, and renders a report, which is more than one module. No section. | Section added, covering a stale rate table misstating every figure and an unpriced model reading as zero. |

Two other tasks carry no section and correctly so. `feat-0056` and `feat-0058` are a query and a view
each against a schema `feat-0053` already commits to holding "enough for the later reports to be built
without a second ingest pass", so neither touches a second module.

## Re-run: implementable

```text
verdict: implementable
blocking_gaps: []
```

### Checklist

| # | Condition | Result |
|---|---|---|
| 1 | Spec and decomposition readable | met |
| 2 | Open questions resolved or explicitly non-blocking | met, see below |
| 3 | Every scenario has an observable Then | met |
| 4 | Proposed Surface sufficient to implement and test | met, with one note below |
| 5 | Tasks ordered and dependency-aware | met |
| 6 | Each task names its affected files | met |
| 7 | Validation, test strategy, success criteria | met |
| 8 | Risk and rollback notes where the rule fires | met after the two additions |
| 9 | Task-to-scenario traceability both ways | met, 22 of 22 |
| 10 | No spec-plan contradiction | met |
| 11 | Test layers from the repository's own taxonomy | met |
| 12 | First safe task dependency-satisfied and mappable | met |

**Condition 2, stated rather than assumed.** The spec carries three open questions and none blocks
implementation, because each carries a recommendation the decomposition adopts and none changes an
observable outcome. Rate-table currency is a maintenance process, and the behaviour it touches is
already pinned by `S-010`. Retention is recommended against and `feat-0053` puts it out of scope in
those words. The one-machine boundary is genuinely unresolved and no scenario or task depends on the
answer.

**Condition 4, with a note.** The Proposed Surface is deliberately contract-level and names no command,
endpoint, or stored shape, which is correct for a spec and leaves some realizations to the tasks.
`S-007` is the clearest case: it requires an empty corpus to be distinguishable and does not say by
what. `feat-0053` pins it to an exit code, mirroring `run-checks.py`, and makes it a criterion. That is
a task choosing among realizations the contract permits, not a task contradicting it, so it does not
block. A conformance audit should check distinguishability, not the exit code.

## Task-to-scenario map

| Task | Scenarios | Notes |
|---|---|---|
| `feat-0053` | S-005, S-006, S-007, S-008, S-009, S-022 | Foundation. No report surface. |
| `feat-0054` | S-001, S-002 | Ends the walking skeleton; the six below are then independent. |
| `feat-0055` | S-012, S-018 | Adds the live-session source. |
| `feat-0056` | S-003, S-004 | Query and view only. |
| `feat-0057` | S-010, S-011, S-017, S-021 | Adds the rate table and the quota source. |
| `feat-0058` | S-016 | Single scenario, kept whole rather than folded. |
| `feat-0059` | S-013, S-014, S-015 | Default path first, optional source behind it. |
| `feat-0060` | S-019, S-020 | Closes the contract at 22 of 22. |

Coverage was checked by counting rather than by reading: 22 scenarios in the spec, 22 mapped, none
mapped twice, none unmapped, and none mapped that the spec does not carry. No scenario is deliberately
unimplemented.

## Scenario-to-test map

The repository has one flat suite, `tests/test_*.py` run by `unittest discover`, and no unit and
integration split. Layers below are therefore named by what the test must actually stand up, which is
the distinction that matters here, and all of them land in that one suite.

| Scenario | Layer | Why |
|---|---|---|
| S-001, S-002 | derivation over a fixture corpus | Pure counting; needs no store on disk. |
| S-003, S-004 | derivation over a fixture corpus | Same, plus an in-flight run and a nested dispatch as fixtures. |
| S-005, S-006 | store on a temporary path | Idempotence and incremental reads are only observable across two real runs. |
| S-007, S-008 | store on a temporary path | Both are about what a run reports; `S-007` asserts an exit code. |
| S-009 | filesystem, hashed before and after | The claim is byte-level and cannot be faked at a lower layer. |
| S-010, S-011, S-021 | derivation with an injected rate table | Keeps the assertion off the shipped rates, which change. |
| S-012, S-018 | derivation with a fake registry | Liveness must be injectable; `S-018` is an arithmetic assertion. |
| S-013, S-014 | server plus a temporary corpus | Requires an open connection and an appended record. |
| S-015 | server, compared against a corpus-only run | The oracle is the corpus-only figures, so both paths must run. |
| S-016 | derivation over a fixture corpus | Fixtures must include a hook failure, a retried error, and an abnormal end. |
| S-017 | derivation with an absent quota source | The optional source's absence is half the scenario. |
| S-019 | enumeration over the surface | Must read the action set from the surface, not a hand-kept list. |
| S-020 | derivation with the capability absent | The declining path is the whole scenario. |

## First safe task

`first_safe_task: feat-0053`

Its `depends_on` is empty, its six scenarios are mapped, its affected files and created paths are
named, its validation command is the repository's own acceptance command, and every one of its
scenarios has a test layer above. Nothing else is dispatchable until it lands, since the other seven
depend on it directly or through `feat-0054`.
