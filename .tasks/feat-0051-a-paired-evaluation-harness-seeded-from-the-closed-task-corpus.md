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

This kit has twenty skills, 534 tests covering its Python tooling, and **zero evaluation of whether a
single skill works, fires when it should, or improves an outcome versus its absence.** The contribution
bar ("no skill ships cold") is currently satisfied by one dogfood run per skill, which proves a skill
worked once against no control at all.

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
failures is a great start." There are 152 closed tasks here, many recording a falsified premise, a
silent-failure incident, or a defect that survived every gate. That is a better seed than anything
written from imagination.

## Scope

**In scope:** a paired evaluation harness, seeded from real failures, covering **three skills**.

- Three, not twenty. Anthropic's checklist asks for at least three evaluations, and the first pass exists
  to prove the harness rather than the library. **State which three and why they were chosen.**
- Every case runs **with and without the skill**, and the report shows both. A case whose assertions pass
  either way is reported as non-discriminating rather than counted.
- Cases drawn from `.tasks/done/`, citing the task each came from, so a reader can check that the failure
  was real.
- **Decide where evals live and record the rejection.** Epic E item 6 says `tests/`. `skill-creator` puts
  an `evals/` directory inside each skill. These are not compatible here: `install.py` copies whole skill
  directories, so a per-skill `evals/` ships the kit's own fixtures into every adopter's home. Work that
  out from `install.py`'s placement loop rather than from this sentence.

**Out of scope:**

- **Adding an eval gate to [`run-checks.py`](../scripts/run-checks.py).** Evals need model calls; the
  acceptance command is offline and deterministic and every task in this repository depends on it staying
  that way. The prior art is [`check-provenance.py`](../scripts/check-provenance.py), deliberately outside
  required CI because it needs network. Evals are run on demand, for the same reason.
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
- [ ] `scripts/run-checks.py` is unchanged and still exits 0 with all seven gates.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
