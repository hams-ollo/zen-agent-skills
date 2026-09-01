---
id: feat-0051
title: Twenty skills ship with no evaluation of whether any of them works, fires, or beats its own absence
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #6: fixture-based skill evaluation suite"
depends_on: []
touched_files:
  - tests/
created: 2026-08-27
---

## Problem

Anthropic's skill authoring guidance opens with evaluation, and its shipping checklist requires it:

```text
"Create evaluations BEFORE writing extensive documentation."
"[ ] At least three evaluations created"
"[ ] Tested with Haiku, Sonnet, and Opus"
```

This kit has **zero evaluation of whether a single skill works, fires when it should, or improves an
outcome versus its absence.** The contribution bar ("no skill ships cold") is currently satisfied by one
dogfood run per skill, which proves a skill worked once against no control at all.

Re-measured 2026-09-01, because this paragraph carried "twenty skills, 534 tests" and both had moved:
22 skills, 20 of which ship, and 1116 tests. The ratio is the part that has not moved. Every one of
those tests covers the Python tooling that distributes the kit; the only tests over a skill are in
`tests/test_systematic_debugging.py`, and that file states its own bound in its docstring, that a test
can assert an instruction is present and cannot assert a model obeyed it.

[ROADMAP Epic E item 6](../ROADMAP.md) already scoped this well, including the two things the 2026-08-18
external research added: measure a baseline without the skill, and address trigger disambiguation. **The
2026-08-27 field review adds three things that item does not have**, and they are why this task is
fileable now rather than a restatement of it.

**1. A published reference implementation exists.** Anthropic's `skill-creator` plugin ships the loop:
`evals.json` carrying `{id, prompt, expected_output, files}`; one isolated subagent per case so each run
has clean context; **every case run twice, with the skill and without it**; grading to `{text, passed,
evidence}`; an aggregator emitting pass rate, mean tokens and duration per configuration; and an
analyser that hunts for **non-discriminating assertions**, which it calls a "useless metric". For
triggering it builds roughly 20 queries, half positive and half near-miss negatives that share keywords
but need different tools, then splits 60/40 train/test and selects the best description **by test score
to avoid overfitting**.

**2. The acceptance bar in Epic E item 6 has a published operationalisation.** "The first run must catch
a real regression" is not a published phrase, but the `without_skill` baseline is exactly that test: an
assertion that passes with the skill removed has caught nothing and proven nothing.

**3. This kit already has the corpus the guidance asks for.** "20-50 simple tasks drawn from real
failures is a great start." There are 152 closed tasks here (**201 as of 2026-09-01**, 65 of them bugs,
which is a class carrying a known wrong answer), many recording a falsified premise, a silent-failure
incident, or a defect that survived every gate. That is a better seed than anything written from
imagination.

### Amended 2026-09-01 from Anthropic's AI-Native SDLC Playbook

Source: the "Continuous evals in CI" lesson of Anthropic's AI-Native SDLC Playbook
(`academy.claude.com/courses/ai-native-sdlc-playbook`), read 2026-09-01. It describes this loop as an
operated practice rather than an authoring step, and it supplies three things neither ROADMAP Epic E
item 6 nor the 2026-08-27 review had. **Two are folded into scope below and the third is named and
deferred**, which is the treatment this task already gives trigger disambiguation.

**A. A cadence, which this task had left as "on demand".** The Out-of-scope section below rules an eval
gate out of [`run-checks.py`](../scripts/run-checks.py), correctly, because the acceptance command is
offline and deterministic and everything here depends on it staying so. It then concludes "run on
demand", and the playbook's contribution is that this is the weak half of that pair rather than the safe
one. Upstream runs evals on **two triggers**: a pull request touching the agent configuration, and a
schedule. That is a third option between the two this task considered, and it **does not touch
`run-checks.py` at all**, so the rule above survives intact. It matters here for a reason the playbook
does not have to argue: `check-provenance.py` is this kit's own precedent for on-demand, and it is run
only when somebody remembers, which is the gap ROADMAP Epic B item 19 was filed for. Deciding the
cadence is now in scope. Building the schedule is not: that is
[`feat-0065`](feat-0065-a-scheduled-sensor-for-the-drift-checks-that-only-run-when-somebody-remembers.md).

**B. Gating a configuration change on the pass rate.** Upstream: "A skill change that drops the pass
rate gets reviewed before it merges." That is what would turn the contribution bar from a claim answered
from memory into one a command answers, and it is the first mechanism this kit has been offered for it.
In scope as a decision to make and record rather than as machinery to build, since a gate over three
skills would bind almost nothing.

**C. Incident-to-eval as a lifecycle step. Named and deferred, deliberately.** Upstream: "Each
production incident gets an eval, written by the team that owned the incident, and stays in the suite as
a regression test." This task already draws its cases from `.tasks/done/`, so the seeding half is
present; what is new is the ratchet, every future incident adding one, which would sit in the closeout
lifecycle in the work-altitude section of `AGENTS.md` beside the `doc-sync` and conformance steps. It is
**not folded in**, because it is a change to that lifecycle rather than to this harness, it is what
ROADMAP Epic E item 8 is held for want of a concrete artifact for, and a ratchet added before three
cases exist is ceremony. The closeout says whether the first pass earned it, and files it or declines it
with a reason.

## Scope

**In scope:** a paired evaluation harness, seeded from real failures, covering **three skills**.

- Three, not twenty. Anthropic's checklist asks for at least three evaluations, and the first pass exists
  to prove the harness rather than the library. **State which three and why they were chosen.**
- Every case runs **with and without the skill**, and the report shows both. A case whose assertions pass
  either way is reported as non-discriminating rather than counted.
- Cases drawn from `.tasks/done/`, citing the task each came from, so a reader can check that the failure
  was real.
- **Decide the cadence and record it**, per amendment A: on demand, a path-scoped trigger on a pull
  request touching `.agents/`, a schedule, or a combination. Decide it against what a non-deterministic
  check costs when it goes red on an unrelated change, which is the reason `check-provenance.py` sits
  where it does, rather than against preference.
- **Decide whether a pass-rate drop gates a skill change**, per amendment B, and record the answer
  either way. Three skills is a thin basis for a gate, so "not yet, and here is what would earn it" is a
  legitimate outcome and a silent omission is not.
- **Decide where evals live and record the rejection.** Epic E item 6 says `tests/`. `skill-creator` puts
  an `evals/` directory inside each skill. These are not compatible here: `install.py` copies whole skill
  directories, so a per-skill `evals/` ships the kit's own fixtures into every adopter's home. Work that
  out from `install.py`'s placement loop rather than from this sentence.

**Out of scope:**

- **Adding an eval gate to [`run-checks.py`](../scripts/run-checks.py).** Evals need model calls; the
  acceptance command is offline and deterministic and every task in this repository depends on it staying
  that way. The prior art is [`check-provenance.py`](../scripts/check-provenance.py), deliberately outside
  required CI because it needs network. **Unchanged by amendment A above**, which adds a separate
  workflow as a third option and touches this script not at all. What the amendment removes is only the
  inference that "not in `run-checks.py`" meant "on demand and nothing else".
- Trigger disambiguation across the whole library. It is the sharper half of Epic E item 6 and it needs a
  working harness first. **File it as a follow-up rather than folding it in.**
- LLM-as-judge calibration against human labels, and any `pass^k` repetition. Both are correct and both
  are premature before three cases exist.
- Telemetry, which is [`feat-0052`](feat-0052-turn-on-telemetry-capture-before-the-bounds-that-need-it.md).

## Implementation notes

**The trap that voids the whole exercise.** An evaluation whose grader reads a file the skill under test
can write is not an evaluation. `BenchJack` (Wang et al., UC Berkeley, arXiv:2605.12673) drove agents to
audit benchmarks and found 219 flaws, achieving near-perfect scores **without solving a single task**, the
canonical case being a nine-line `conftest.py` that PyTest auto-loads and which rewrites test outcomes.
**The grader must read from a location the agent under test cannot write**, and the closeout must say how
that is guaranteed.

**Budget for the first pass being wrong.** Shankar et al. (UC Berkeley, arXiv:2404.12272) name **criteria
drift**: "users need criteria to grade outputs, but grading outputs helps users define criteria." Some
criteria are only discoverable after reading transcripts, so first-pass assertions will be partly wrong.
Anthropic's own case is the caution: Claude Opus 4.5 scored 42% on CORE-Bench until rigid grading and
ambiguous specs were fixed, then 95%. **The eval was wrong, not the agent.** Do not treat a first-run
failure as automatically a real finding.

**One hazard specific to this kit.** Anthropic notes that shared state "can also artificially inflate
performance" when agents see git history from previous trials. This kit runs agents in worktrees; if eval
fixtures reuse a repository, trial N sees trial N-1's commits. Isolate per case.

Anthropic's guidance also says a skill fires "only for complex, multi-step, or specialized tasks", so a
one-step query may not trigger even with a perfect description. Write cases that are substantive.

## Risks and rollback

New files plus one document, no existing behaviour changed, so nothing can regress.

The real risk is a suite that passes on day one and proves only that it was written against today's
behaviour, which Epic E item 6 names as its own failure mode. The `without_skill` baseline is the guard:
if every assertion passes with the skill removed, the suite has measured nothing and the closeout must say
so rather than report a pass rate.

Reversible by deleting the added files.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Three skills carry at least one evaluation case each, every case citing the closed task its failure
      came from.
- [ ] Every case runs with and without the skill, and the recorded output shows both configurations.
- [ ] Any assertion that passes in both configurations is reported as non-discriminating rather than
      counted as a pass.
- [ ] The closeout records the verbatim output of one full run, including the pass rate for each
      configuration.
- [ ] The closeout states where evals live and why the other location was rejected, referring to
      `install.py`'s placement behaviour rather than to preference.
- [ ] The closeout states how the grader is protected from being written by the skill under test.
- [ ] The closeout states the chosen cadence and why, naming what a non-deterministic check costs on the
      trigger it was not given.
- [ ] The closeout states whether a pass-rate drop gates a skill change, with the reason either way.
- [ ] The closeout says whether the first pass earned the incident-to-eval ratchet of amendment C, and
      either files it as a follow-up or declines it with a reason. Silence is not one of the answers.
- [ ] `scripts/run-checks.py` is unchanged and still exits 0 with every gate passing.
      **Corrected 2026-08-28 at dispatch**: this criterion said "all seven gates" and
      `chore-0049` added an eighth on the same day, which made it unsatisfiable as written.
      It now states the property rather than the count, matching the amendment `chore-0049`
      made to the `Gate set` surface element for the same reason.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
