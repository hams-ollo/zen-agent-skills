---
id: chore-0076
title: Five documents forbid a service the kit is about to build, and one open task already claims half the roadmap paragraph that has to change
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E #7: run telemetry and bounds"
depends_on: []
touched_files:
  - ROADMAP.md
  - AGENTS.md
  - README.md
  - CONTRIBUTING.md
  - docs/ARCHITECTURE.md
  - .tasks/feat-0052-turn-on-telemetry-capture-before-the-bounds-that-need-it.md
created: 2026-08-28
---

## Problem

[`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) was approved on 2026-08-28. It
contracts for a local reporting surface over the session corpus this kit's own agents produce, and it
requires two things this repository currently forbids in writing: a local store, and a process that
serves a report while sessions are running.

**The prohibition is stated in five documents, not one.** Any task that changes one and leaves the
other four is the exact failure `chore-0074` is open about, and the count is the reason this is a task
rather than a one-line edit:

| Document | The claim, verbatim |
|---|---|
| [`ROADMAP.md`](../../ROADMAP.md) | "No database or service dependency anywhere in the kit. Everything is markdown, `SKILL.md`, and stdlib Python. Portability is the whole point." |
| [`AGENTS.md`](../../AGENTS.md) | "A skills library, not an application. The deliverables are the skills under `.agents/skills/` and the tooling under `scripts/` that distributes them." |
| [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) | "The kit deliberately has no runtime application, database, service, or third-party Python dependency." |
| [`README.md`](../../README.md) | "There is no process your agent has to run inside, no database, no service, and no third-party Python dependency." |
| [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | "It has no runtime application, no database, no service, and no third-party Python dependency, and those absences are the point. Anything that adds one needs a strong argument." |

**They do not all say the same thing, and that matters.** `README.md` addresses the adopter ("your
agent"), so it is scoped correctly already and may need no edit. `CONTRIBUTING.md` and
`ROADMAP.md` speak about the kit as a whole and are falsified. `AGENTS.md` is falsified in its second
sentence only: tooling under `scripts/` that does not distribute skills is now a third thing.
Establishing which is which is the work, and a blanket rewrite of all five would be wrong.

**The argument for the amendment, which `CONTRIBUTING.md` explicitly asks for.** The stated reason for
the rule is portability, and portability is a property of what an adopter receives.
[`scripts/install.py`](../../scripts/install.py) places only `.agents/skills/`, `.agents/rules/`, and
`.agents/hooks/`. A store and a server that live outside those three reach no adopter tree, so no
adopter inherits a dependency and the portability contract is untouched. The rule as written also
forbids what the acceptance command already does, since `run-checks.py` starts subprocesses and writes
under `.tmp/`, so the sentence is already broader than the practice it describes.

**Separately, ROADMAP Epic E item 7 holds work that is not actually blocked.** Item 7 reads:

> "Held behind item 5 for the reason it was never built in the first place, telemetry has no consumer
> while a human is watching every run, and item 5 is what first produces runs nobody is watching."

[`feat-0052`](../feat-0052-turn-on-telemetry-capture-before-the-bounds-that-need-it.md) already argues
that hold is sound about bounds and wrong about capture. The approved spec adds a third part the hold
is also wrong about: **reporting over the corpus needs no capture and no cloud run at all**, because
the transcripts already exist. Item 7 is one paragraph carrying three items with three different hold
states, and it cannot say so as written.

**And `feat-0052` already claims half of that paragraph.** Its Scope says "**Amend Epic E item 7 to
split capture from bounds**". Two open tasks editing the same paragraph is a collision whichever runs
first, so one of them has to stop claiming it.

## Scope

**In scope:** scope the rule to what the kit ships, in each document on its own terms, and restructure
one roadmap paragraph.

- **`ROADMAP.md`, "Out of scope by design".** Amend the first bullet so the prohibition governs what
  `install.py` places in an adopter's tree, and state the reasoning in one clause rather than leaving
  a reader to reconstruct it. Keep the portability sentence: it is the reason, and it survives intact.
- **`ROADMAP.md`, Epic E item 7.** Restructure into three lettered parts, mirroring item 2's existing
  `(a)/(b)/(c)` shape in the same epic rather than inventing a new numbered item:
  - **7(a) capture**, unheld, owned by `feat-0052`.
  - **7(b) reporting**, unheld, naming `docs/spec/agent-observatory.md` as its approved contract and
    stating plainly why it is not held: it reads a corpus that already exists.
  - **7(c) bounds**, still held behind item 5, with the original sentence preserved for that half.
- **`ROADMAP.md`, the Epic E Mermaid graph.** The edge `E5 --> E7` is falsified by the split. Redraw so
  only the bounds half depends on item 5.
- **`AGENTS.md` section 1.** Amend the second sentence so tooling under `scripts/` that does not
  distribute skills is named, rather than reading as though every script is a distribution script.
- **`docs/ARCHITECTURE.md` and `CONTRIBUTING.md`.** Reconcile each to the amended rule, in that
  document's own register.
- **`README.md`.** Read it against the amended rule and **either edit it or record why it needs no
  edit.** Its wording is already adopter-scoped; silently skipping it is what this task exists to stop.
- **`feat-0052`.** Remove its "amend Epic E item 7" scope bullet and its matching acceptance
  criterion, and say in one line that `chore-0076` performs the split. Change nothing else in it.

**Out of scope:**

- **Any code.** No store, no server, no ingester, no skill. This task changes prose so that the
  spec's tasks can be written; it builds nothing the spec contracts for.
- **Any bound.** Item 7(c) stays held and its wording stays as it is, per `feat-0052`.
- **`.tasks/.scaffold.json`.** Its `id_high_water` is stale and
  [`chore-0060`](chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md) owns that.
  See Decisions.
- **Striking any Epic E item.** Whether a Feature is complete is the author's call, as item 2 already
  records for itself.
- **Decomposing the spec into implementation tasks.** That is the next step and needs this one landed.

## Implementation notes

Amend rather than delete. Each of these sentences was a deliberate decision, and a reader who finds a
constraint quietly gone learns less than one who finds it narrowed with its reason attached. The
pattern to mirror is the conventions section of `AGENTS.md` on the one committed hook registration,
which states the exception, its mechanical reason, and its bound, in that order.

Say what the amendment does **not** license, in the same breath as what it does. The rule still holds
for everything `install.py` places, and the acceptance command must still run with no install step on
all six CI cells. An adopter's tree gains nothing from this change, which is the whole argument for
making it.

`docs/ARCHITECTURE.md` line 9 is the one most likely to need real rewriting rather than a clause,
because it asserts the absence as a property of the kit with no scope qualifier at all.

## Decisions

- **Item 7 split three ways rather than two, and lettered rather than renumbered.** `feat-0052` argued
  for capture against bounds; the approved spec adds reporting, which neither of the other two covers.
  Lettering mirrors item 2 in the same epic, so the epic keeps one shape. Renumbering into a new item
  9 was rejected: every existing reference to "item 7" would have needed chasing, and the Mermaid
  graph and the two held-item tables all name items by number.
- **`.tasks/.scaffold.json` deliberately left stale.** The `new-task` procedure says to update
  `id_high_water` for the types consumed. Not done here, on purpose: `chore-0060` owns that file's
  staleness across all four types, and advancing `chore` from 48 to 75 while `bug` and `feat` stay
  behind converts an evenly stale manifest into an unevenly stale one, which is harder to reason about
  and would half-fix an open task without closing it.
- **`README.md` was read against the amended rule and deliberately left unchanged.** Recorded here
  because an untouched file in `touched_files` reads as an oversight. Its paragraph is adopter-scoped
  throughout: "This is a skills library, not a framework or an agent runtime. There is no process
  **your agent** has to run inside, no database, no service, and no third-party Python dependency."
  The subject is what the reader receives, and after this amendment the reader still receives none of
  those things, so every clause remains true. Editing it to add a maintainer-tooling caveat would put
  an internal distinction in front of a reader for whom it has no consequence.
- **The third-party-dependency half was not scoped, and each amended document says so.** Only the
  runtime, store, and service clauses were narrowed. This was deliberate: scoping all four together
  would have been one edit rather than four, and would have quietly licensed a dependency in tooling
  that the CI matrix runs with no install step.

## Risks and rollback

The task touches six files across the repository, so the deterministic rule fires on the first
condition.

The real risk is not a broken build, since nothing here executes. It is that a constraint gets loosened
further than the argument supports, and a later contributor reads the amended sentence as general
permission to add a dependency. The guard is that every amended sentence must name what it still
forbids, which is a stated acceptance criterion below rather than an intention.

The second risk is the collision this task exists partly to remove: if `feat-0052` is dispatched to an
agent while this one is in flight, both edit Epic E item 7. Do not run them in parallel.

Reversible by reverting one commit. No data format, protocol, or persisted state is involved.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `ROADMAP.md`'s "Out of scope by design" bullet scopes the prohibition to what `install.py`
      places in an adopter's tree, and still names what it forbids.
- [x] Epic E item 7 carries three lettered parts, with capture and reporting stated as unheld and
      bounds stated as still held behind item 5.
- [x] The Epic E Mermaid graph no longer shows item 5 blocking the whole of item 7.
- [x] Item 7(b) names `docs/spec/agent-observatory.md` and states why reporting is not held.
- [x] `AGENTS.md` section 1 no longer implies every script under `scripts/` distributes skills.
- [x] `docs/ARCHITECTURE.md` and `CONTRIBUTING.md` agree with the amended rule, checked by reading
      each against it rather than by pattern-matching the phrase.
- [x] `README.md` is either amended or its no-change outcome is recorded in the closeout with a reason.
- [x] `feat-0052` no longer claims the Epic E item 7 amendment, in either its Scope or its acceptance
      criteria.
- [x] Every amended sentence states what the rule still forbids, not only what it now permits.
- [x] `grep -rn "database or service" --include=*.md .` returns no claim that contradicts the amended
      rule.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
