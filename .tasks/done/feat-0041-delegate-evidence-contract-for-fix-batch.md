---
id: feat-0041
title: Require a structured evidence contract from every fix-batch delegate report
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #16: delegate evidence contract for fix-batch"
depends_on: []
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-08-05
---

## Problem

[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) dispatches worktree-isolated agents and then has
to decide whether what came back is real. Its weakest seam is the shape of that return: an agent
reports in prose, and the orchestrator judges a narrative. `feat-0022` wired
[`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) into Step 6, which is a genuine
improvement, but verification runs against the work rather than against the report, so a report that
omits what it did not do still passes through unchallenged.

The observed failure is on record. Two of three agents in the `feat-0025` batch found their task
file's premise factually wrong about the code, and nothing in the system captured it. That produced
[`feat-0037`](../feat-0037-task-file-decision-log-v1.md), which has the agent write its decisions into
its own task file. That is the semantic half. The mechanical half is missing: there is no required
set of fields whose absence stops the report from being accepted.

Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT)
requires a compact evidence contract from every delegate before a gate may advance: lineage, task id,
covered scenarios, files changed, tests run, the validation command **and its result**, findings with
structured evidence, and a recommended next step. Transcript-style reports and missing fields block
advancement outright. The orchestrator's remedy when evidence is thin is a focused follow-up to the
same delegate, or reading the narrowest relevant file slice and recording why it had to.

The value is not the ceremony. It is that "the validation command and its result" cannot be answered
in prose without either running it or lying, which turns a soft claim into a checkable one.

## Scope

**In scope:**

- Define the delegate report contract in `fix-batch`: the required fields, the rule that a missing
  field blocks acceptance, and the explicit rejection of transcript-style reports.
- Require the validation command and its verbatim result as separate fields, not a summary of them.
- Define the orchestrator's remedy when a report is incomplete: request a focused follow-up from the
  same agent, or read the narrowest file slice needed, and record which was done and why.
- Add the equivalent acceptance check to
  [`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md), so a worktree cannot land
  on the strength of a report that would not have been accepted.

**Out of scope:**

- The decision log itself. `feat-0037` covers semantic continuity (rejected alternatives, falsified
  premises, deliberately open seams); this covers mechanical evidence. The ROADMAP already argues
  these must stay distinct and building them together would conflate them. Reference `feat-0037`
  from the contract rather than absorbing it.
- Budgets, retry ceilings, and lineage epochs. Upstream's contract carries them because its Loop
  workflow is a long-running orchestrator with a durable ledger; `fix-batch` is not, and importing
  the bookkeeping without the ledger buys nothing.
- Repeat and futility handling, which is `feat-0042`.
- `house-review` and `verifier-agent` edits, so this stays disjoint from `feat-0040`.

## Implementation notes

Read the delegate-report section of upstream's `Loop.md` at
`https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/workflows/Loop.md`
before writing, and take the field list rather than the surrounding machinery.

Keep the contract short enough that an agent will actually produce it. Upstream's version is tuned
for an orchestrator with a persistent ledger; the version that belongs here is the subset that a
single `fix-batch` run can check in one pass. If a field cannot be checked by the orchestrator, it
does not belong in a contract whose whole premise is that unmet fields block acceptance.

The findings field should use the evidence shape defined by `feat-0040` once that lands. The two
tasks are independent by file, so whichever lands second should align the wording rather than define
a second shape.

`fix-batch` runs agents that cannot see each other's work by design, so the contract must be
satisfiable from inside a single worktree. Nothing in it may require knowledge of the batch.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" -v

- [x] `fix-batch` states the required report fields and that a missing field blocks acceptance.
- [x] The validation command and its verbatim result are separate required fields.
- [x] The incomplete-report remedy is stated, including the requirement to record which remedy was
      used.
- [x] `reconcile-worktrees` refuses to land a worktree whose report does not meet the contract.
- [x] The contract references `feat-0037`'s decision log rather than restating it.
- [x] Dogfood evidence recorded in the closeout: a real dispatch produces a conforming report, and
      the closeout states whether any field was hard for the agent to produce.

## Implementation record

The dispatch that implemented this task is itself the first dogfood run, since the prompt was
written against the pre-contract `fix-batch` and hand-rolled its own report shape. That draft asked
for nine fields, seven of which survive into the contract verbatim. The two differences are the
evidence:

- The draft omitted **tests added, changed, or run** and **blockers and assumptions**. Both are
  checkable in one pass and both are places where an agent's silence is currently indistinguishable
  from a clean result, so the contract keeps them.
- The draft required a **decisions** field (rejected alternatives, falsified premises, open seams).
  That is `feat-0037`'s decision log, folded into the mechanical report by hand because no contract
  existed to point at. The contract names it as the composing semantic half instead of absorbing it,
  which is what the Out of scope section asks for.

No field was hard to produce from inside a single worktree. The one that cost anything was the
verbatim validation result, which is the point: it cost a real command run.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
