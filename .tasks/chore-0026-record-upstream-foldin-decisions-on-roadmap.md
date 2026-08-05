---
id: chore-0026
title: Record the upstream fold-in decisions on the roadmap, including what was declined and why
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - ROADMAP.md
created: 2026-08-05
---

## Problem

A review on 2026-08-05 went through everything
[repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) still offers that this kit
has not taken, and produced decisions on all of it. Those decisions live in a conversation. The
roadmap does not reflect them, which means the next person to read the upstream repository will
re-derive the same conclusions from scratch, and may reach different ones.

Three specific mismatches between the roadmap and what was decided:

- **Epic B #13 (`telemetry-guard`) is scoped wrongly.** It is written as run-state telemetry:
  lifecycle events, retry and cycle limits, time and compute budgets, repeated-work detection. The
  upstream sources show the higher-leverage version is enforcement of the spine already built, which
  is what `feat-0038` and `feat-0039` now implement. The telemetry framing is not wrong, it is
  second in line, and the item currently reads as though it were the whole of it.
- **Epic B #11 (`maintainability-review`) holds for a reason that is no longer the binding one.**
  "Hold until used twice" has been overtaken by two better reasons: the lens is itself synced from
  `cursor/plugins`, so adopting it makes this kit a third-hand vendor, and `review-depth`
  (`feat-0035`, shipped on `main` in `517c333`) may absorb the need entirely now that its deep tier
  exists.
- **Nothing records what was declined.** `track-work`, the `Backlog` workflow, upstream's
  symlink-only installer model, and the `Spec` / `Test` / `Loop` / `Deep-Review` workflows as whole
  artifacts were all considered and rejected, each for a stated reason. An unrecorded rejection gets
  reconsidered, which is a cost paid repeatedly.

There is also a deferral with no home: `test-quality-reminder`, the Stop-gate hook, was deliberately
left out of `feat-0038` because upstream's version carries a large shell-command-parsing heuristic.
The pattern is worth having later; right now that decision exists only in a task's out-of-scope list.

## Scope

**In scope:**

- Reframe Epic B #13 to lead with enforcement hooks, referencing `feat-0038` and `feat-0039`, and
  keep the telemetry content as the explicitly second phase.
- Update Epic B #11's hold reasoning to the two current reasons, and state the re-evaluation trigger:
  `feat-0035` has landed, so check now whether `review-depth`'s deep tier needs a structural lens, and if it
  does, author one rather than vendor one.
- Confirm Epic B #8 (`user-testing`) still holds and state the reason in current terms: the
  transferable content is two ideas (throwaway data only, and marking a closeout blocked rather than
  silently skipping), which does not justify a skill for a kit whose users are mostly not building
  UI.
- Add the new items to Epic B: the evidence gate and finding signature (`feat-0040`), the delegate
  evidence contract (`feat-0041`), repeat and futility classification (`feat-0042`), and the
  provenance convention (`feat-0043`).
- Add a short declined-and-why list covering the four rejected items above, plus the
  `test-quality-reminder` deferral.

**Out of scope:**

- Any change to a skill, a hook, or a script. This is a bookkeeping task on one file.
- Re-litigating any of the decisions. If one turns out to be wrong, that is a new task.
- `CHANGELOG.md`. Nothing has shipped yet; these are forward-plan entries.

## Implementation notes

Keep the declined list short. Its job is to stop a question from being reopened, not to argue the
case again, so one line of reasoning per item is the right length.

Match the existing roadmap voice. Epic B's shipped entries carry their task id, the fold-in
provenance, and the dogfood that blessed them, and the held entries carry an explicit trigger for
when to revisit. Follow that shape rather than introducing a new one, and preserve the strikethrough
convention used for shipped items.

Do this before dispatching `feat-0040` through `feat-0043`, since each of those names a parent that
should exist on the roadmap by the time an agent reads it. All four currently point at the Epic B
heading rather than a numbered item, which is honest but coarse.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict && python scripts/validate-skills.py

- [ ] Epic B #13 leads with enforcement hooks and names `feat-0038` and `feat-0039`, with telemetry
      stated as the second phase.
- [ ] Epic B #11 states both current hold reasons and a concrete re-evaluation trigger.
- [ ] Epic B #8 states its hold reason in current terms.
- [ ] Four new Epic B items exist for `feat-0040` through `feat-0043`.
- [ ] A declined list names `track-work`, the `Backlog` workflow, the upstream installer model, the
      four workflows as whole artifacts, and the `test-quality-reminder` deferral, each with one
      line of reasoning.
- [ ] Every relative link in the edited file resolves, per `validate.py`'s link check.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
