---
id: feat-0062
title: Use systematic-debugging on a real defect, then promote it out of draft or record why not
type: feat
status: done
priority: P2
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: [feat-0061]
spec: docs/spec/systematic-debugging.md
scenarios: []
# Directories rather than exact paths for everything `feat-0061` creates: this file is
# validated now and those paths do not exist until that task has run.
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/
  - ROADMAP.md
created: 2026-08-29
---

## Problem

`feat-0061` ships the skill as a draft, placed by no profile. That is deliberate: the contribution
bar in the contribution-bar section of `AGENTS.md` is that **no skill ships cold**, and a skill whose
only evidence is that its own structural tests pass has proven that its prose contains certain words.

The bound `feat-0061` states in as many words is that a skill body is instructions to a model, so its
tests can assert an instruction is present and cannot assert a model obeyed it. **This task is the
only thing that closes that gap**, and it closes it the one way available: run the skill against a
defect whose cause nobody knows yet, and see whether the procedure produced the answer or whether the
answer arrived some other way and the procedure was narrated over it afterwards.

There is precedent for the draft state outliving its usefulness. `agent-observatory` has been a draft
since 2026-08-29 for the same reason and has no promotion task, which is how a draft becomes
permanent by inattention rather than by decision.

## Scope

**In scope:** one real diagnosis, then a decision about the draft status.

- **Run the skill on a defect whose cause is genuinely unknown.** The recommended target is the
  `sqlite3.OperationalError: database is locked` that takes `scripts/observatory/serve.py`'s routes
  down while a concurrent session's ingester holds the store. It was observed live twice, on
  2026-08-28 and again on 2026-08-29 during reconciliation, and it is a good target for three
  reasons the contract cares about: it is **intermittent**, which is `S-012`; it **crosses
  components**, ingester and server, which is `S-008`; and its proximate cause is known while the
  right fix is not, which is exactly the gap between a symptom and a named cause.
- **Record the diagnosis in the contract's own record shape**, at whatever verdict it reaches.
  `not_reproducible` and `architectural` are results, not failures, and a run that reaches one of
  them is still evidence about the skill.
- **Report what the skill got wrong**, which is the actual deliverable. A dogfood that reports only
  that it worked has measured nothing. Name every place the procedure was unclear, produced a step
  that could not be followed, or was silently departed from.
- **Then decide the draft status**, and record the decision either way:
  - Promote: remove `metadata: status: draft`, and place it in the profiles it belongs to.
  - Keep it a draft: state what the run showed that the skill has to answer first, and file the task
    for it. A draft kept deliberately is a different thing from a draft nobody revisited.
- Any correction to the skill or its tests that the run's findings justify.

**Out of scope:**

- **Fixing the defect diagnosed.** The contract refuses repair, and this task inherits that. The
  diagnosis feeds `new-task`, which is the point of `S-006`. A fix here would also make the dogfood
  worthless, because the skill's value is the named cause and not the diff.
- Widening the contract. If the run reveals the contract is wrong, that is a finding and an
  amendment task, following `chore-0061`'s discipline; it is not an edit to make while holding a
  diagnosis.
- Promoting `agent-observatory` out of draft. Its dogfood is its own task and is not this one.

## Implementation notes

**The honest failure mode is a dogfood that confirms.** An agent running a procedure it has just read
and then reporting that the procedure worked is the weakest possible evidence, and it is what this
task will produce by default. Two things make it worth more:

- **Write down the answer's arrival time.** If the cause was obvious three minutes in and the record
  was filled out afterwards, that is the finding, and it means the skill added ceremony rather than
  method. Say so.
- **Have the diagnosis checked by someone who did not produce it.** The independence rule in the
  autonomy lens applies to a claim about a cause exactly as it applies to a claim about a test.

The second candidate target, if the first turns out to be already understood, is `bug-0050`, the
committed hook that has exited 49 on every session start since 2026-08-07. It is weaker on purpose:
its cause is known, so it exercises the record shape and not the investigation. Prefer it only as a
fallback and say which was used.

## Risks and rollback

Touches the skill tree and the documentation set, and promotion changes what `install.py` places.

- **Promotion is the risky half, not the diagnosis.** Removing `draft` moves the skill into profiles,
  which changes the description budget every profile is measured against and puts the skill in front
  of adopters. `feat-0060` recorded that the budget is printed over the shipped set rather than the
  discovered set, so a promotion moves a figure two tests read.
- Reversible by reverting one commit. Re-adding the `draft` block returns the skill to being placed
  by no profile, and nothing outside the repository has changed.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A diagnosis record exists for a real defect, carrying every field its verdict requires.
- [x] The record names which defect was used, and why, if it was not the recommended target.
- [x] The findings against the skill are recorded, and `none` is stated explicitly rather than
      reached by silence.
- [x] The diagnosis was checked by an agent that did not produce it.
- [x] The draft decision is recorded either way. If promoted, `install.py --dry-run` shows the skill
      placed in its profiles and the description budget still passes. If kept, the reason is stated
      and the task that would change it is filed.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Dogfood record, 2026-08-29

The run this task exists for. Recorded here rather than in a new `docs/spec/` sibling kind,
because [`docs/spec/README.md`](../../docs/spec/README.md) sets the bar for a new kind at "two
documents would otherwise have to drift apart to stay correct" and one dogfood does not clear it.
A task file in `.tasks/done/` is also the right shape for `S-009`, which requires a persisted
record never to be rewritten by a later run.

**Target: the recommended one.** The `sqlite3.OperationalError: database is locked` that takes
`scripts/observatory/serve.py`'s routes down while a concurrent ingester holds the store. Not the
`bug-0050` fallback, which was not needed.

### The diagnosis, in the contract's record shape

**`verdict`**: `root_cause_found`

**`symptom`**: while another process holds a write transaction on `.observatory/store.db`, a GET to
any store-reading observatory route does not return. The server logs
`sqlite3.OperationalError: database is locked` and the client gets a dropped connection or hangs
until its own timeout. Routes that never open the store are unaffected.

**`reproduction`**

Tree state: `d1c5eac` with a clean working tree, verified before the first attempt and again after
the last. Every run was against a copy of the store under the session scratchpad; the tracked
`.observatory/store.db` was read once, to make that copy, and never written.

| # | What was run | What it produced |
|---|---|---|
| 1 | server up, then `ingest.py` incrementally over an already-current store, 4 requests | no failure. The ingest finished in 0.7s |
| 2 | full ingest into a fresh store, cold corpus, server on the same file, requests throughout | ingest held for 22.8s; 4 requests took 22.5s between them; 1 connection reset; no `database is locked` seen at the client |
| 3 | same, warm corpus, 6 concurrent readers | ingest held 1.7s; all 6 requests took ~10.1s and finished within 0.3s of each other, including a 404 |
| 4 | instrumented copy, writer replaced by a transaction held for a known 12s, 3 concurrent readers | **reproduced**: `sqlite3.OperationalError: database is locked`, twice, at 5.5s |
| 5 | the A/B in the confirming observation below | as shipped 0 of 3 routes answered with 3 lock errors; one variable changed, 3 of 3 answered |

**Pinned, and this is the whole reason attempts 1 to 3 look flaky**: the writer's hold time. It is
not a property of the defect, it is a property of how much of the 425MB corpus was in the operating
system's page cache, which is why the same full ingest took 22.8s cold and 1.7s warm. Once the hold
was set deliberately to 12s the defect became **deterministic, 3 of 3 routes on every attempt**. No
rate is reported, because there is no rate to report once that variable is held still.

**Uncontrolled and stated as such**: the store's journal mode is `delete` on this machine, read
directly from the file. Whether a store in another mode behaves the same was not tested.

**`hypotheses`**

| # | Stated before its trial | Trial | Result |
|---|---|---|---|
| 1 | The ~10s in attempt 3 is server startup, not contention, because a `/api/agents` 404 that never opens the store took 10.03s | the identical six-route burst against the identical server with **no writer at all** | **disproved.** 0.31s for the whole burst, and the 404 returned in 0.01s. The writer does cause it |
| 2 | The block is the `CREATE TABLE IF NOT EXISTS schema_meta` that `db.connect` issues on every open, because that is a write statement and a reader issuing it needs the write lock | boundary probes in the copy around `sqlite3.connect`, around that statement, and either side of `do_GET` | **disproved.** `sqlite3.connect` returned in 0.000s and the `CREATE TABLE` returned in 0.000s. Both readers then spent 5.5s **inside the route** before raising. The 404 entered and left at the same timestamp, so the delay is not before routing either |
| 3 | The reader fails because `db.connect` calls `sqlite3.connect(str(path))` with no `timeout=`, inheriting SQLite's 5-second default busy timeout, so any writer holding longer than that fails every reading route | the A/B below | **confirmed** |

Two hypotheses disproved against a declared bound of five. Hypothesis 2 came from reading the code
and was wrong, which is the single most useful thing this run produced; see the findings.

**`root_cause`**: [`scripts/observatory/db.py`](../../scripts/observatory/db.py) line 215 opens
every connection as `sqlite3.connect(str(path))` with no `timeout=` argument, so every reader in the
component inherits SQLite's 5-second default busy timeout. It is the component's single connection
factory: no other `sqlite3.connect` exists anywhere under `scripts/`, so the server, the ingester
and every test share it. The store is in `delete` journal mode, where a reader must wait for a
writer, so any writer that holds the store for longer than five seconds makes every store-reading
route raise `database is locked`. Five seconds is well inside the normal range for this component's
own ingester: the same full pass measured 22.8s cold and 1.7s warm on this machine.

**`confirming_observation`**: with a write transaction held for a fixed 12 seconds and **one
variable changed**, the `timeout=` argument:

- as shipped: **0 of 3** routes answered, 3 `database is locked` errors in the server's output, one
  client disconnected at 5.55s and two hung until their own 45s timeout
- with `timeout=30`: **3 of 3** routes answered `200`, after 10.6 to 10.8 seconds, **0** lock errors

Had the cause been the journal mode, the statement being issued, or opening a connection at all,
raising only the timeout would have changed nothing. It inverted the outcome.

**`implicated_files`**

- [`scripts/observatory/db.py`](../../scripts/observatory/db.py), line 215, the cause.
- [`scripts/observatory/serve.py`](../../scripts/observatory/serve.py), the `_report` helper, for
  the second defect below rather than for the cause.

**`regression_observable`**: a connection returned by `db.connect` waits materially longer than
SQLite's 5-second default before giving up, which `PRAGMA busy_timeout` reports directly; and with a
writer holding the store for longer than that default, a store-reading route returns a response
rather than dropping the connection.

### A second defect, uncovered and not fixed

**The failure is worse than a 500, and that is a separate defect from the cause.** In
[`serve.py`](../../scripts/observatory/serve.py)'s `_report`, `db.connect` is wrapped in
`except db.StoreUnusable`, and the `build(conn)` call below it is wrapped only in `try/finally`. An
`OperationalError` raised inside `build` propagates out of `do_GET` with no response written, so the
client gets a dropped connection or hangs. That is why the reported symptom is routes going down
rather than routes returning an error.

**Not fixed here, deliberately.** `S-005` refuses repair and this task inherits that refusal. The
fix is a task, and this record carries what that task's bar demands.

### When the answer arrived

Asked because `feat-0062` asks for it, and the answer is the point rather than a formality.

**Not in the first three minutes, and the first cause the procedure produced was wrong.** Attempts 1
and 2 reproduced nothing usable. The first hypothesis came from a measurement that turned out to be
an artifact of the reproduction harness, and cost a trial. The second came from reading
`db.py` and was the obvious one, the `CREATE TABLE IF NOT EXISTS` on every open, and the boundary
probes killed it in one run by showing that statement returning in 0.000 seconds. The real cause was
not visible from reading at all: it is an **absent argument**, and what pointed at it was the number
5.5 appearing in a log, which is only suspicious next to SQLite's 5-second default.

So the procedure changed the answer rather than decorating one. A run that had stopped at reading
would have filed a task against `CREATE TABLE IF NOT EXISTS schema_meta`, which is not the cause, and
`new-task` would have written the premise nobody checked. That is precisely the failure this skill
was built to prevent, reproduced against the skill itself.

## The independent check refuted this diagnosis, and that is the result

Run by an agent that did not produce the diagnosis, which is this task's own acceptance criterion
and rule A7 of the autonomy rules module. Verdict: **partially confirmed**. Every claim it refuted, I
then reproduced myself before accepting, on scratchpad copies with no tracked file edited.

**The record above is left exactly as it was written.** It is not corrected in place and not
softened. `S-003` requires a disproved hypothesis to be retained with its disconfirming result, and a
refuted `root_cause` is the same object one level up; a record edited until it agrees with the answer
stops being evidence about how the answer was reached. What follows amends it.

### What survived

The defect, the reproduction, both disproved hypotheses, `db.py` line 215 carrying no `timeout=`,
that line being the only `sqlite3.connect` in the repository, the `delete` journal mode, the 5.5
second failure, the 0-of-3 against 3-of-3 A/B, and the 404 route being unaffected. All independently
re-run and all exact.

### What was refuted

**`verdict` stands at `root_cause_found`. `root_cause` does not.** It named a **sufficient
condition** and called it the cause.

| Cell, one variable each, 12s held writer | Store routes answering | Latency |
|---|---|---|
| as shipped | 0 of 3, locked | fails at 5.55s |
| `timeout=30`, the trial this record called confirming | 3 of 3 | 11.6s to 11.8s |
| **WAL journal mode, timeout untouched** | **0 of 3, locked** | fails at 5.51s |
| **the `schema_meta` upsert guarded, timeout untouched** | **3 of 3** | **0.01s to 0.19s** |

Three corrections follow from those four cells.

**1. The journal-mode clause is wrong.** The record says the store is in `delete` mode "where a
reader must wait for a writer", offering that as why a reader blocks. Converted to WAL with nothing
else changed, the failure is identical. Journal mode has no causal role here.

**2. The nearest cause is one statement, not an absent argument.**
[`db.py`](../../scripts/observatory/db.py) line 254 issues an unconditional
`INSERT INTO schema_meta ... ON CONFLICT DO UPDATE` followed by `conn.commit()` on **every** open,
including every read-only GET. So a route that only reads takes a write lock, in any journal mode,
and contends with any writer. Guarding that upsert behind `if found != SCHEMA_VERSION:` fixes the
defect **and returns readers to baseline latency**, where raising the timeout leaves every reader
waiting out the whole writer hold. The missing `timeout=` is real and is the aggravating condition:
it sets how long a reader tolerates the contention this statement creates.

**3. The second defect is at a different call site than reported, and the name was wrong.** The
`OperationalError` never reaches `build(conn)`. In 12 of 12 observed failures it is raised inside
`db.connect` at `db.py` line 254 and escapes `conn = db.connect(store)` at
[`serve.py`](../../scripts/observatory/serve.py) line 2171, whose `except db.StoreUnusable` does not
catch it, leaving `do_GET` with no response written. The helper is `_with_store` at `serve.py` line
2157; the record called it `_report`, and no `_report` exists in that file. A task written from the
original sentence would have guarded `build(conn)` and left the real escape open.

### The one that matters: the confirming observation did not discriminate

The record's stated counterfactual is that if the cause were the journal mode, the statement being
issued, or opening a connection at all, raising only the timeout would have changed nothing.

**That reasoning is invalid, and the invalidity is the finding.** Raising a timeout ends any wait,
whatever is waiting, so the trial could not have failed for a wrong hypothesis in this class. It was
consistent with the hypothesis and did not test it. The two cells that actually discriminate are the
WAL cell and the guarded-upsert cell, and neither was run until an agent that did not write the
diagnosis went looking.

This is the exact failure the skill exists to prevent, produced by the skill, and caught only by
independence. It is the strongest evidence this run generated, and it decides the draft question
below on its own.

### Corrected fields

**`root_cause`**: [`db.py`](../../scripts/observatory/db.py) line 254 commits an unconditional write to
`schema_meta` on every connection open, so every read-only route in the component takes a write lock
and contends with any concurrent writer. Line 215 opens that connection with no `timeout=`, so the
contention is given SQLite's 5-second default before it becomes
`sqlite3.OperationalError: database is locked`. The first is why a reader contends at all; the second
is how long it tolerates it. Journal mode is not involved.

**`confirming_observation`**: four cells, one variable each, against a writer holding for a fixed 12
seconds. As shipped, 0 of 3 routes answer. With the upsert guarded and nothing else changed, 3 of 3
answer in 0.01 to 0.19 seconds, which is baseline. With WAL and nothing else changed, 0 of 3 answer,
so the journal mode is excluded. With `timeout=30` and nothing else changed, 3 of 3 answer but only
after 11.7 seconds, which is the aggravating condition being widened rather than the contention being
removed. **A wrong hypothesis fails these:** had the write on open been irrelevant, guarding it would
have changed nothing.

**`implicated_files`**: [`db.py`](../../scripts/observatory/db.py) lines 215 and 254, the cause.
[`serve.py`](../../scripts/observatory/serve.py) line 2171 inside `_with_store`, for the second defect.

**`regression_observable`**: with a writer holding the store for longer than five seconds, a
store-reading route returns a response rather than dropping the connection. Deliberately **not**
`PRAGMA busy_timeout`, which the original record named: that pins a repair rather than a behavior,
and a test written to it fails against the better fix while the defect is gone.

### Findings against the record, from the check, and their disposition

| Finding | Disposition |
|---|---|
| The journal-mode clause is wrong (blocker) | corrected above |
| The second defect is at the wrong call site (blocker) | corrected above |
| The confirming observation does not discriminate (major) | corrected above, and the skill amended |
| A sufficient condition returned as the cause with no alternative tried (major) | corrected above, and the skill amended |
| Hypothesis 2's result asserts a location the probes do not support (major) | correct. The probe covered three statements of five and reported the function innocent. The skill is amended |
| `regression_observable` pins a repair rather than a behavior (minor) | corrected above |
| `implicated_files` names `_report`, which does not exist (minor) | corrected above |
| `reproduction` carries a prose table and no runnable command with verbatim output (minor) | accepted and not fixed here. It is `A4`, it is right, and the reproduction scripts live in a session scratchpad that does not survive. Recorded as a gap in this record rather than papered over |
| The 45s hangs could not be reproduced in four cells (nit) | accepted as harness-dependent. All three clients disconnected at 5.5s in the checker's runs |
| "clean working tree" is an adjective, not `git status --porcelain` output (nit) | accepted |
| "the real cause was not visible from reading at all" is overstated | accepted, and it is the fairest thing in the report. The blocking statement is nine lines below the one hypothesis 2 named, in the same function, and plainly a write. One more line of reading would have found it |

## The draft decision

**It stays a draft.** Recorded as a decision, with the bar for changing it, so it is not the state
`agent-observatory` is in.

The run did what a dogfood is for: it produced a real diagnosis of a real defect, and the procedure
demonstrably changed the answer, killing a wrong cause that reading alone had produced. It also
**produced a wrong root cause that passed the skill's own confirming-observation test**, and nothing
in the skill caught it. Five corrections have gone into the body as a result, two of them from the
refutation and three from the run, and all five are asserted so they cannot be silently deleted.

A skill whose first real use refuted its own output is not one to put in front of adopters on the
strength of that use. What would change it: **one run by a session that did not write it, on a defect
it did not choose, whose diagnosis survives an independent check.** That is
[`feat-0063`](../feat-0063-a-second-independent-run-of-systematic-debugging-before-it-ships.md), filed
rather than left as an intention.

**The contribution bar is doing its job here rather than being satisfied by a formality.** The skill
is better than it was this morning and it is not yet ready to ship.

## Closeout, 2026-08-29

Acceptance run: `python scripts/run-checks.py`. Result, verbatim tail: `8 passed, 0 failed, 0 could
not run.` 919 tests, 22 skills, 193 task files.

Every acceptance criterion is met, and the fourth is met in a way the task did not anticipate: the
diagnosis was checked by an agent that did not produce it, and **the check refuted it**. The
criterion asked for the check, not for a particular verdict, and a refutation is the criterion
working rather than the task failing.

**The record above is not rewritten.** The original diagnosis stands as written and the correction
sits below it, because `S-003` requires a disproved hypothesis to be retained with its disconfirming
result and a refuted `root_cause` is the same object one level up. Anyone reading this file can see
what was claimed, what refuted it, and what replaced it.

**Every refutation was reproduced here before it was accepted.** Four cells, one variable each,
against a writer holding for a fixed twelve seconds: as shipped 0 of 3 routes answer; with WAL and
nothing else changed 0 of 3, which excludes the journal mode the original record blamed; with the
`schema_meta` upsert guarded and nothing else changed 3 of 3 in 0.01 to 0.19 seconds, which is
baseline. A delegated report is a claim, and this one held up on every count.

### What the run cost, and what it bought

Five corrections to the skill, three from the run and two from the refutation, listed in the record
above. Each was a paragraph nothing was scoped to on arrival, which is the third time in two days
that class has appeared in this work's history, so each now carries an assertion. The full mutation
set was re-run in one pass rather than added up: **25 defined, 25 killed, 0 survived.**

Two tasks filed rather than folded in:
[`chore-0080`](../chore-0080-the-diagnosis-record-has-nowhere-to-put-a-defect-found-on-the-way.md),
because the record has no field for a defect found on the way and this run found one; and
[`feat-0063`](../feat-0063-a-second-independent-run-of-systematic-debugging-before-it-ships.md), the
promotion gate.

**The observatory defect is diagnosed and not fixed.** `S-005` refuses repair and this task inherits
it. The corrected record carries the cause, the implicated lines, and the regression observable,
which is what `new-task` needs and could not otherwise obtain, and writing that task is somebody's
next move rather than this one's.

### Findings against the skill

**Not `none`.** Five, all listed in the record above and all applied to the body. The one worth
carrying out of this task: **the contract's `confirming_observation` is satisfiable by a trial that
could not have failed**, and the skill said so only after this run got it wrong. `S-001` is not wrong
and the skill now states the missing half outright. Whether the contract should state it too is
recorded on the matrix row as a live question rather than settled here.
