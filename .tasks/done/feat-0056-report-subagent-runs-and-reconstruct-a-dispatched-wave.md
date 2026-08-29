---
id: feat-0056
title: Report what each dispatched subagent cost, and reconstruct a fix-batch wave as one unit of work
type: feat
status: done
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

[`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) dispatches a wave of isolated agents and
[`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md) lands them, and no record
survives of what the wave cost, which agent took longest, or which returned nothing.

[`feat-0041`](feat-0041-delegate-evidence-contract-for-fix-batch.md) wrote a nine-field evidence
contract precisely because a delegated agent's own report is a claim rather than evidence. This task
supplies the part of that evidence a machine can produce without asking the agent, which is the part
an optimistic report is least able to distort.

Read [`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) for the contract. It is not
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

- [x] New tests cover S-003 and S-004, each named so the scenario it proves is identifiable.
- [x] Each dispatched agent is reported with type, resolved model, duration, token total, tool-call
      count, and completion outcome (S-003).
- [x] A run with no result record is reported with its documented in-flight outcome, not as a failure.
- [x] Agents dispatched as one wave are grouped, each carrying its workspace, branch, and its own start
      and end time (S-004).
- [x] The rule distinguishing a wave from unrelated dispatches is stated in the report surface, not
      only in the code.
- [x] A nested dispatch is reported without its depth being silently lost.
- [x] No subagent transcript body is read into the report.
- [x] Existing tests still pass, unchanged in intent.

## Decisions

- **A premise that turned out false: the conformance matrix says duration, tokens and tool calls
  are "still derivable in-store" from `message.agent_id`, `message.ts` and
  `tool_call.message_uuid`. Two of the three are; tokens are not, the naive way.** Summing every
  message's four token kinds overstates the harness's own total by 20 to 60 times, because each
  message's input and cache-read counts include the whole conversation before it again. Measured
  against the 19 runs carrying both figures: the harness's total is the **last** message's four
  kinds added up, exact on 17 and within 9 percent on the other two. Derived tool calls matched
  exactly on all 19; derived durations run 1 to 3 seconds short. Every figure now carries the
  basis it came from rather than being mixed silently.

- **A premise that turned out false: dispatches in one wave do not share a dispatching message.**
  The task's implementation notes ask what distinguishes a wave, and the obvious structural answer,
  several `Agent` tool_use blocks in one assistant record, occurs zero times. All 278 dispatches in
  the corpus are one block per record, so grouping had to be derived from time.

- **A rejected alternative: grouping by user turn, which is the boundary the corpus actually
  draws.** A turn ends at a `user` record whose content is text rather than a tool result, and the
  store holds only assistant records, so the splitting record is not there. Chose a calibrated
  proximity rule instead, with the threshold measured (53.3 seconds to 152.5 to 1,524.7 across the
  isolated-dispatch gap distribution, so 300 sits in the ten-fold valley) and both the rule and its
  bound stated in the report itself. **This is a finding against `feat-0053`'s store shape, not a
  migration slipped in here**: recording user records would answer the grouping question exactly,
  and it is a schema decision that belongs to whoever owns the store.

- **A seam left open deliberately: the waves report offers no action.** `S-019`'s `ACTIONS` registry
  could carry a "copy worktree path" entry for each run, and it does not. Widening that enumeration
  is `feat-0060`'s contract to change, not this report's, so the renderer builds no interactive
  element at all and the workspace path is rendered as selectable text.

- **A seam left open deliberately: outcome is reported, and whether a backgrounded agent actually
  finished is not.** The corpus records no completion for 259 of 278 runs and the subagent's own
  transcript says only when it last wrote. Corroborating against the live process table would be a
  second liveness check beside `S-012`'s, over a different subject, and no scenario asks for it.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is updated for S-003 and S-004.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
