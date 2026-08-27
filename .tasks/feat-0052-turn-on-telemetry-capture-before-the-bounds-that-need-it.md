---
id: feat-0052
title: Every bound the roadmap defers needs a distribution to be set against, and capture costs one environment variable
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7: run telemetry and bounds"
depends_on: []
touched_files:
  - docs/
  - .gitignore
  - ROADMAP.md
created: 2026-08-27
---

## Problem

[ROADMAP Epic E item 7](../ROADMAP.md) holds run telemetry with a stated reason:

> "Held behind item 5 for the reason it was never built in the first place, telemetry has no consumer
> while a human is watching every run, and item 5 is what first produces runs nobody is watching."

**That reason is sound about dashboards and wrong about capture**, and the difference costs one
environment variable. Verified against Claude Code's monitoring documentation on 2026-08-27:

```text
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=console
export OTEL_LOGS_EXPORTER=console
```

No backend, no collector, no service. Console and file exporters are supported directly, and telemetry is
**off by default**, so nothing is captured until someone opts in. `OTEL_LOG_RAW_API_BODIES=file:<dir>`
writes to a directory.

**And the attribution this kit needs already exists.** The cost and token counters carry `skill.name`,
documented as "Skill active for the request, set by the Skill tool, a `/` command, or inherited by a
spawned subagent." Per-skill cost and token attribution is available today, unbuilt.

**The consumer is not a dashboard. It is the baseline for every bound this roadmap defers.** Item 7 itself
wants "retry and implementor/verifier-cycle limits, time or optional compute budgets, and a clear stop
signal on a bound violation." Not one of those numbers can be chosen honestly without knowing this kit's
own distribution. Capture-then-bound is the only order that works; bound-then-capture picks numbers out of
the air, which is exactly what `feat-0042` was filed to avoid and what `autonomy.md` refuses to do for
retry limits.

Two published results argue the hold is also weaker than it looks on its own terms. Anthropic's
`Scaling Managed Agents` names what the absence costs once nobody is watching: "a bug in the harness, a
packet drop in the event stream, or a container going offline all presented the same." And METR's
randomised trial of experienced developers found self-assessment wrong **in sign**, with participants
forecasting a 24% speedup and measuring a 19% slowdown. "A human is watching" is precisely the
measurement instrument that study found wanting.

## Scope

**In scope:** turn capture on, write down how, and make the output ignorable.

- A short document describing how to enable capture, which exporters need no infrastructure, what is
  captured, and where it lands.
- A `.gitignore` entry for the capture directory, so run data never enters version control.
- **Amend Epic E item 7 to split capture from bounds**, since the hold as written covers both and only one
  half survives. State that capture is unheld and bounds stay held behind item 5.
- **State the privacy position explicitly.** Prompts and tool parameters are redacted unless explicitly
  opted into, and `OTEL_LOG_RAW_API_BODIES` is the opt-in. Anyone reading this document is deciding
  whether to record their own prompts; say so plainly rather than leaving it to be discovered.

**Out of scope:**

- **Any bound.** No retry limit, no token budget, no futility threshold, no stop signal. Those are item 7's
  second half and they stay held. **A task that sets a number from a week of data has defeated its own
  purpose**, because the point is to have a distribution first.
- Any dashboard, collector, or backend. The whole argument is that capture needs none, and adding one
  would break the no-service-dependency constraint for no gain at this stage.
- Parsing, aggregating, or reporting on captured data. That is the natural follow-up and it needs data to
  exist first.
- Wiring telemetry into `run-checks.py` or CI. Capture is a local practice, not a gate.
- [`feat-0051`](feat-0051-a-paired-evaluation-harness-seeded-from-the-closed-task-corpus.md), which measures
  whether skills work. This measures what runs cost. They meet later and not in this task.

## Implementation notes

**The honest question this task has to answer: what does it actually change in the repository?** Telemetry
is enabled by environment variables in a developer's own shell, so there is no code to write. The
deliverable is a document, a `.gitignore` line, and a roadmap amendment. **If that feels thin, say so in
the closeout rather than padding it with a wrapper script**, because a script that exports three variables
is a worse interface than three lines a reader can paste, and it would be the kit's first piece of
tooling that exists to look like work.

Prior art for the document's shape and register: [`docs/INSTALL.md`](../docs/INSTALL.md), which explains a
procedure without restating what belongs elsewhere.

Worth recording while writing, because it is the reason this is worth doing at all: the metric names to
watch are `claude_code.cost.usage` and `claude_code.token.usage` (both carrying `skill.name`), and
`claude_code.active_time.total`. Events include `claude_code.tool_result` and `claude_code.tool_decision`.
Confirm each against the documentation rather than inheriting this list, since it was read once on
2026-08-27 and product surfaces move.

Adopting OpenTelemetry's `gen_ai.*` attribute **names** in anything this kit later writes costs nothing
now and keeps a future export portable. Note that essentially every `gen_ai.*` attribute is marked
Development rather than Stable, and the conventions moved to their own repository, so **do not build
anything that depends on them being stable.**

## Risks and rollback

One document, one ignore line, one roadmap paragraph. Nothing executes and nothing ships to an adopter.

The real risk is scope creep into the bounds, which is the interesting half and the one that must wait.
The guard is the acceptance criteria: this task is done when data can accumulate, not when anything is
decided from it.

A second risk is recording prompts by accident. `OTEL_LOG_RAW_API_BODIES` is opt-in and writes untruncated
request and response bodies. The document must say what that means before it says how to use it.

Reversible by reverting one commit; captured data is gitignored and local.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A document explains how to enable capture with no backend, naming the exact environment variables.
- [ ] The document states what is captured by default and what requires an explicit opt-in, with the
      privacy consequence stated before the instruction.
- [ ] The capture directory is gitignored, proven by `git status` staying clean after a capture run.
- [ ] Epic E item 7 distinguishes capture from bounds, and records that capture is unheld while bounds
      remain held behind item 5.
- [ ] **No bound, threshold, budget, or limit is set by this task.**
- [ ] The closeout records the verbatim first few lines of real captured output, including one line
      carrying `skill.name`.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
