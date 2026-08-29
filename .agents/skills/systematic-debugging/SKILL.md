---
name: systematic-debugging
description: Use when a defect, test failure, flaky test, or unexpected behavior needs its cause established before anyone writes a task file or a fix. Reproduces the report first, localizes the failure to the boundary where behavior diverges, then tests one hypothesis at a time and returns a deterministic verdict, so a run that found nothing is never mistaken for one that did. It diagnoses and never repairs, and it never edits a tracked file, because instrumentation lives only in a copy it made for the purpose. The record it returns carries the facts a task file's bar demands and cannot otherwise obtain, so `new-task` writes a premise somebody checked. Trigger on "why is this failing", "find the root cause", "this test is flaky", "debug this", "the CI job broke and nobody knows why", or any defect that arrives without a cause. Distinct from `test-author`, which pins the observable this names, and from `fix-batch`, which dispatches the fix this refuses to write.
license: MIT
metadata:
  status: draft
---

# systematic-debugging

Turn a reported defect into a **named cause with the evidence that established it**, distinct from
the symptom that was reported, and stop there.

**This skill is a draft.** It ships with no profile and reaches no adopter until it has been used on
a real defect and blessed, per the contribution bar in the target repository's `AGENTS.md`.

## When to use

- A defect, test failure, build failure, or unexpected behavior arrives and nobody has established
  why it happens.
- A test passes sometimes and fails other times, and somebody is about to call it fixed.
- A failure surfaces in one component and may originate in another.
- An agent working a task in isolation meets a failure its task file does not describe, and needs to
  tell a defect it introduced from one it uncovered.
- A task file is about to be written about a symptom. This is the step that belongs in between.

## When not to use

- **You want the defect fixed.** This skill does not fix anything, and it will not be talked into it.
  The fix is a task, and `fix-batch` dispatches it.
- **You want the regression test written.** That is `test-author`. This names the observable that
  test must pin, and stops.
- **You want the task file written.** That is `new-task`, which this feeds.
- **You want to know whether a fix worked.** That is `verifier-agent`.
- **You want the code judged.** A cause sitting in ugly code is still just the cause; `house-review`
  owns quality.
- **You want to know whether the defect is worth fixing.** That is a priority call, it belongs to the
  author, and it is expressed on the task file rather than here.
- **The thing that went wrong is the agent rather than the repository.** This diagnoses defects in a
  repository under work, not misfires of the harness running it. A run that has been confused by its
  own context is a different problem with a different answer, and pointing this procedure at it
  produces a confident cause for a defect that is not in the code.
- The cause is already established and agreed. Skip to whichever skill acts on it.

## Inputs

| Input | Required | Content |
|---|---|---|
| Defect report | yes | The reported behavior, in whatever form it arrived. |
| Reproduction steps | no | Supplied steps, when the reporter had them. |
| Investigation bound | no | Maximum disproved hypotheses before the run ends `architectural`. Default below. |
| Record destination | no | Where to persist the record. Without one the record is returned inline. |

**The default bound is five disproved hypotheses**, and it is a tuning value rather than a
commitment: raise it for a system you know is layered, lower it when the answer is wanted fast and a
partial map is worth more than a late cause. Whatever it is, **declare it in the record before the
first trial**, because a bound chosen after the trials is not a bound.

## Verdicts

Exactly one per run. There is no fourth, and a run that ends without one of these has not ended.

| Verdict | Meaning |
|---|---|
| `root_cause_found` | A cause was named and confirmed by an observation that could have disconfirmed it. |
| `not_reproducible` | The reported behavior could not be produced. A result, not a failure of the run. |
| `architectural` | The bound was reached with no confirmed cause. The shape of the system, rather than any single defect, is the subject. |

## Procedure

### 1. Restate the symptom as an observable

Write down what was reported as something that can be observed: a command and its output, a request
and its response, a value and the value expected. Not "login is broken". "`POST /session` returns 500
where the contract says 401 for a bad password."

If the report cannot be turned into an observable at all, you are already at the third branch of
step 2.

Read the error text completely while you do it, including the stack trace and the exit code. This is
the cheapest evidence available and it is the most often skipped.

**A number your harness reported is a claim about your harness until something else agrees with it.**
Before forming a hypothesis from a measurement, check it against a second source: the system's own
log, a timestamp from inside the process, a run with the suspected cause absent. A figure that only
one instrument has ever produced is where an investigation goes wrong quietly, because it looks like
evidence and costs a trial to disprove.

### 2. Reproduce before you explain

Run the thing. **A cause inferred from reading code alone is a guess**, however good it looks, and
guesses are what this skill exists to replace.

Three outcomes, and each is an answer:

- **It reproduces.** Record the exact command, the tree state it ran against, and what it produced.
  Continue.
- **It does not reproduce.** Return `verdict: not_reproducible`. `reproduction` states what was
  attempted and what was observed instead, `missing_input` names what would change the answer, and
  **no `root_cause` is offered**. This is a result. Do not go looking for the cause of a thing you
  could not make happen.
- **There is no way to observe it.** When the repository's own tests and tooling supply no way to
  construct a reproduction, return `verdict: not_reproducible` with `missing_input` naming what is
  absent. **Do not infer a root cause from reading code alone.** A plausible cause offered here is
  the exact failure this skill exists to prevent, and it is more dangerous than an empty answer
  because it will be believed.

**Before calling anything intermittent, check whether you are the one varying it.** A reproduction
that fires sometimes usually has a condition nobody is holding still, and the fix is a knob rather
than a rate: find the quantity the symptom depends on, set it deliberately, and see whether the
symptom becomes reliable. A defect that is deterministic once one variable is pinned is not an
intermittent defect, and reporting a rate for it describes your harness rather than the system.
Record what you pinned and to what, in `reproduction`, alongside anything that stayed uncontrolled.

**When it is genuinely intermittent**, do not take a passing attempt as an answer. Repeat the
reproduction and record the **observed rate** in `reproduction`, as attempts and successes rather
than as an adjective. Then hunt for a condition that produces the behavior reliably, and record each
condition tried and its outcome in `hypotheses`. `root_cause_found` is available only once such a
condition is found. **An attempt that happened to pass is not evidence that anything was fixed.**

**When you are an agent working a task in isolation**, run the reproduction twice: against your
working tree, and against the unmodified base you started from. State both outcomes in
`reproduction`. Without that pair, the record cannot tell a defect you introduced from one that was
already there, and those two want opposite things done about them.

### 3. Work in a copy, and never in the tracked files

**Instrumentation goes in a copy this run made for the purpose. Never in the tracked files, not even
briefly.**

At no point during the run does any tracked source, test, or config file differ from its state at the
start, whether the run reaches a verdict, is interrupted, or fails partway. That bound is on every
moment of the run rather than only on its end, and the difference is the whole point: instrumenting
in place and cleaning up afterwards satisfies an end-of-run check on every run that completes, so its
failure is invisible until a run dies, which is to say until something has already gone wrong.

Make the copy however the target allows. Nothing here requires a particular tool, and naming one
would be false of a target that does not have it.

**Copy enough that the thing still runs, and no more.** For one file that is the file; for a component
it is whatever its imports, its package layout, and its data files need, which is usually less than
the whole repository and more than the directory you were looking at. Get it wrong in the small
direction and you debug your copy instead of the system, which is the same wasted trial as a bad
measurement.

**Where no working copy can be made at all**, say so, add no instrumentation, and continue read-only.
Record in `reproduction` that the observation was made without instrumentation, so a reader knows the
diagnosis was reached with a weaker instrument than usual. **The run still reaches a verdict** on the
evidence it could gather. A repository this skill cannot copy is one it observes from the outside,
not one it refuses.

Whatever you learn in the copy, the diagnosis is about the tracked code. Say so when the two could be
confused.

### 4. Localize before you explain

**Where a failure crosses components, find the boundary at which behavior first diverges before
proposing why it diverges.** An explanation offered before the boundary is known is an explanation of
the wrong component about half the time.

In the copy, log what enters and what leaves at each boundary, along with the environment and
configuration each side actually sees. Run once, then read. The output tells you which side of which
boundary is wrong, and that observation goes in `hypotheses` **before** any entry proposing a cause.

**Probe the whole of the region you are suspicious of, not the part you already suspect.** A probe
placed at the statements you had a theory about, and nowhere else, returns a clean bill of health for
everything you did not instrument, and reads exactly like a clean bill of health for the region. If
you are timing a function, time every statement in it; if you are timing a request, cover it end to
end. The gap in the instrumentation is where the answer will be, because that is the part you were
not thinking about.

Trace backwards from there. Where does the bad value originate, what handed it over, and what handed
it to that? Keep going up until the value is first wrong rather than first noticed. The place a bad
value is noticed is almost never the place it was made.

### 5. One hypothesis at a time

State the hypothesis before the trial, in the form "X is the cause, because Y", specifically enough
that a result could contradict it. Write it into `hypotheses` first. A hypothesis recorded after its
result is a description of the result.

**Vary one thing.** A trial that changes more than one thing cannot attribute its own outcome, so it
produces no evidence whichever way it comes out, and the time spent on it is gone.

Then:

- **The result contradicts the hypothesis.** Keep it. `hypotheses` retains the hypothesis, its trial,
  and the disconfirming result, and the next hypothesis is a **separate entry**, stated before its
  own trial. A disproved hypothesis is the map of where the cause is not, which is why it is recorded
  rather than discarded, and a record that keeps only the winner cannot be audited by anyone.
- **The result confirms it.** Return `verdict: root_cause_found`. `root_cause` states the cause as a
  claim about program behavior and where it originates, and `confirming_observation` states **what
  was observed that would have differed had the hypothesis been wrong**. If nothing would have
  differed, the trial confirmed nothing and the hypothesis is still open.

**A trial that is merely consistent with your hypothesis has confirmed nothing, and this is the one
that gets past people.** Before writing `root_cause_found`, ask what else would have produced the
same result. A change that makes the symptom go away is a **sufficient condition**, and a sufficient
condition is not the cause until you have looked for a second change that also makes it go away.
Look for one deliberately, and try it. If a second change works too, you have found a symptom's
neighbourhood rather than its origin: the cause is whatever they have in common, and the record says
which changes were trialled rather than naming the first one that worked.

The tell is a counterfactual that would hold whatever the answer turned out to be. "Raising the
timeout fixed it, so the timeout was the cause" is that shape: raising a timeout ends any wait, so
the trial cannot tell one waiting thing from another. A counterfactual worth writing down is one that
a wrong hypothesis would have failed.

When you do not understand something, say you do not understand it. An honest gap is cheaper than a
confident cause that has to be unwound later.

### 6. Stop at the bound

When the count of disproved hypotheses reaches the declared bound and no cause is confirmed, **stop
and return `verdict: architectural`**. Do not start another hypothesis.

`bound_reached` names the bound and the count. `hypotheses` carries every hypothesis tried and why
each was disproved. The record states that the shape of the system, rather than any single defect, is
the subject: repeated disproved hypotheses in different places, each revealing coupling somewhere
else, is what a wrong structure looks like from inside a debugging session.

This is a verdict, not a surrender, and it is more useful than a late cause. It says the next
conversation is about the design, and hands over the map that shows why.

### 7. When the report is the thing in error

Sometimes the reproduction behaves exactly as the system's stated contract says it should, and the
report is what is wrong.

Return `verdict: root_cause_found` with `root_cause` naming **the report** as the thing in error, and
cite the contract you checked it against. `implicated_files` and `regression_observable` are
**absent**, because there is no code defect to fix and nothing for a regression test to pin. Writing
either one here would send someone to change correct code.

### 8. Return the record, and do not repair

**A request to diagnose and then fix is answered with the diagnosis alone.** Return the record,
perform no repair, and leave every tracked file as you found it. Say plainly that the fix is out of
scope and name what takes it: the diagnosis feeds `new-task`, which writes the task, and `fix-batch`
dispatches it. **Do not apply the fix in a copy either and offer it as a patch.** The refusal is
about producing the change, not about where the change lands.

When the cause implicates code, the record has to carry what a task file's bar demands and cannot
otherwise obtain: `implicated_files` names the files the cause implicates, `reproduction` supplies
the basis for an acceptance command, and `regression_observable` names the observable a regression
test must pin. Those three are the reason this skill sits upstream of `new-task` rather than beside
it.

**With no destination supplied, return the record inline and create no file.** When a destination is
supplied, write the same record there and nowhere else. A run that persists a report nobody asked for
has written into a repository it promised only to read.

**A persisted record is never rewritten by a later run.** When a later run on the same defect reaches
a different verdict, the earlier record stays exactly as it was and the later run is persisted as a
separate record. A record revised to match a later state stops being evidence and becomes a summary
of the current opinion, which is the one thing a ledger must not be.

## The diagnosis record

| Field | Present when | Content |
|---|---|---|
| `verdict` | always | One of the three above, and exactly one. |
| `symptom` | always | The reported behavior, restated as an observable. |
| `reproduction` | always | The steps or command, what they produced, the tree state they ran against, and the observed rate when the symptom is intermittent. |
| `hypotheses` | always | Each hypothesis stated, its trial, and its result, in order, including disproved ones. |
| `root_cause` | `root_cause_found` | The cause as a claim about behavior, and where it originates. |
| `confirming_observation` | `root_cause_found` | What was observed that would have differed had the hypothesis been wrong. |
| `implicated_files` | `root_cause_found`, and the cause implicates code | Files the cause implicates, for a task file's `touched_files`. |
| `regression_observable` | `root_cause_found`, and the cause implicates code | The observable a regression test must pin. |
| `missing_input` | `not_reproducible` | What would make a reproduction possible. |
| `bound_reached` | `architectural` | The bound, and the count of disproved hypotheses. |

A field whose condition is not met is **omitted**, not filled with a placeholder. An empty
`root_cause` reads as a cause nobody could name; an absent one reads as a run that did not claim one.

## Red flags

Every one of these is the same move, and the move is guessing. If you catch yourself here, you are
between steps 2 and 5 and you have skipped one.

- "It is probably X, let me just check whether changing X helps."
- "Quick fix now, work out why later."
- "Let me change these three things and rerun."
- "It passed that time, so it is fine."
- "I do not fully understand it, but this might work."
- "The reference is long, I will adapt the pattern from the parts I read."
- Naming a cause before running anything.
- Proposing a fix before the boundary is known.
- A hypothesis written after its trial.

## Common rationalizations

| Excuse | Reality |
|---|---|
| "This one is simple, the process is overkill." | Simple defects have causes too, and the process is short for them. It is long only when the defect is. |
| "It is urgent, there is no time to investigate." | Guess-and-check is slower than it feels, and it is the reason this is urgent twice. |
| "I will investigate properly after this one fix." | The first fix sets the premise every later one is written against. |
| "Reading the code told me what is wrong." | Reading tells you what the code says. Running tells you what it does. |
| "Two changes at once saves a round trip." | It costs the round trip anyway, because neither result attributes. |
| "It reproduced once, that is enough." | Once is a data point about one attempt. An intermittent defect needs a rate. |
| "The cause is obvious, the record is ceremony." | Then the record costs a minute. Write down when the answer arrived, and whether the procedure produced it. |

## Notes

- **The verdict is the deliverable, not the cause.** `not_reproducible` and `architectural` are
  results. A run that reaches one of them and says so honestly is worth more than one that produces a
  plausible cause nobody can check, because the second is indistinguishable from a correct answer
  until someone acts on it.
- **A confirming observation that could not have failed confirms nothing.** This is the single
  question worth asking hardest before returning `root_cause_found`: what would I have seen if the
  hypothesis were wrong, and did I actually look for it?
- **This skill's three verdicts are the classification vocabulary.** Any skill here that has to
  classify what an investigation concluded calls this one and reports its verdict, rather than
  defining a parallel set that then needs translating.
- **Detect and report, never rewrite.** An investigation that changes something has stopped being
  admissible as evidence about what was there before it ran, so every refusal above is one rule seen
  from a different side rather than five separate cautions.

## Conventions

Follow the house style module in `.agents/rules/house-style.md`: sentence-case headings, no
em-dashes, named sources, relative markdown links, Mermaid for diagrams. That file is swappable; this
reference to it is not. Where this skill writes into a target repository, that repository's own
conventions govern what it writes, and this module is the fallback.

## Provenance

Adapted from the `systematic-debugging` skill in Jesse Vincent's `superpowers` (MIT). The digest
below is of the retrieved upstream file, not of this adapted one, which differs by design. Re-check
it by running `scripts/check-provenance.py` in the Zen Agent Skills repository.

Two departures are deliberate and are the reason this is an adaptation rather than a copy. Upstream's
fourth phase implements the fix and verifies it; this skill ends at the diagnosis and refuses to
repair, because every other skill in this kit's spine already has that job. And upstream is a gate,
stated as an iron law that no fix may precede investigation; this returns a deterministic verdict
instead, so a run that could not find a cause is a recorded result rather than a blocked one. What is
folded in largely intact: reproducing before explaining, instrumenting component boundaries to
localize a cross-component failure before proposing why it diverges, one hypothesis and one variable
per trial, tracing a bad value back to where it was made rather than where it was noticed, and the
red flags and rationalizations, which are the parts of the upstream skill that do the most work.

```provenance
source: https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md
author: Jesse Vincent
license: MIT
retrieved: 2026-08-29
sha256: 808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787
note: fetched with urllib and digested with hashlib on the retrieved date, at 9,465 bytes. The digest pins upstream as of that date; this file is an adaptation and is expected to differ.
```
