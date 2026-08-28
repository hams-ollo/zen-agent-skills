---
id: feat-0056
title: Report what each dispatched subagent cost, and reconstruct a fix-batch wave as one unit of work
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-003, S-004]
touched_files:
  - scripts/
  - tests/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

[`fix-batch`](../.agents/skills/fix-batch/SKILL.md) dispatches a wave of isolated agents and
[`reconcile-worktrees`](../.agents/skills/reconcile-worktrees/SKILL.md) lands them, and no record
survives of what the wave cost, which agent took longest, or which returned nothing.

[`feat-0041`](done/feat-0041-delegate-evidence-contract-for-fix-batch.md) wrote a nine-field evidence
contract precisely because a delegated agent's own report is a claim rather than evidence. This task
supplies the part of that evidence a machine can produce without asking the agent, which is the part
an optimistic report is least able to distort.

Read [`docs/spec/agent-observatory.md`](../docs/spec/agent-observatory.md) for the contract. It is not
restated here.

## Scope

**In scope:** the waves report, covering `S-003` for individual runs and `S-004` for the wave.

- Per-agent reporting: type, resolved model, duration, tokens, tool-call count, and whether the run
  completed or ended without completing.
- Wave reconstruction: the agents one session dispatched, grouped, each with the isolated workspace
  and branch it was given and its own start and end time.

**Out of scope:**

- **Reading a subagent's transcript body.** The contract's Non-Goals exclude reconstructing
  conversation content. Counts, durations, and outcomes only.
- **Judging whether an agent's work was good.** That is evaluation, held under `feat-0051`.
- **Reconciliation state.** Whether a wave's branches landed is a question about git, not about the
  corpus, and no scenario asks for it.
- **Cost in currency.** `feat-0057` owns `S-010` and `S-011`. Report tokens here.

## Implementation notes

**Confirm the dispatch and result shapes against the corpus before writing code.** The tool's name,
the fields its result carries, and where a subagent's own transcript lives are all facts to read, not
to recall. A field name written from memory is the premise error `new-task` warns about, and this task
depends on more of them than any other.

**`S-003` requires an outcome for a run that did not complete**, which is the case least represented
in fixtures and most likely in practice: an agent that was interrupted, errored, or was still running
when the corpus was read. A run with no result record is not thereby a failed run, and reporting it as
one would be wrong. Decide what an in-flight run reports and cover it with a fixture.

**`S-004` needs the wave to be derivable, and the grouping is the design question.** Agents dispatched
in one batch share a dispatching session, but so do agents dispatched an hour apart for unrelated
work. Establish what actually distinguishes a wave from a sequence of unrelated dispatches, from the
corpus rather than from assumption, and state the rule in the report so a reader can tell what they
are looking at.

Nested dispatch exists: an agent can spawn an agent. Decide whether the report flattens or nests, and
make the choice visible rather than letting the depth silently disappear.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] New tests cover S-003 and S-004, each named so the scenario it proves is identifiable.
- [ ] Each dispatched agent is reported with type, resolved model, duration, token total, tool-call
      count, and completion outcome (S-003).
- [ ] A run with no result record is reported with its documented in-flight outcome, not as a failure.
- [ ] Agents dispatched as one wave are grouped, each carrying its workspace, branch, and its own start
      and end time (S-004).
- [ ] The rule distinguishing a wave from unrelated dispatches is stated in the report surface, not
      only in the code.
- [ ] A nested dispatch is reported without its depth being silently lost.
- [ ] No subagent transcript body is read into the report.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `agent-observatory` conformance matrix is updated for S-003 and S-004.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
