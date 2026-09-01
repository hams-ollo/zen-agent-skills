---
id: feat-0065
title: Every drift sensor this kit owns fires only when somebody invokes it, so nothing watches the repository between changes
type: feat
status: open
priority: P2
parent: "ROADMAP Epic B #19: drift sensors that run outside the change lifecycle"
depends_on: []
touched_files:
  - .github/workflows/
  - SECURITY.md
  - AGENTS.md
created: 2026-09-01
---

## Problem

[ROADMAP Epic B item 19](../ROADMAP.md) states the gap and deliberately declines to name the artifact:
every sensor this kit owns fires only when something invokes it. `validate.py` and `validate-skills.py`
run in CI on a change, `doc-sync` runs when a human asks, and
[`check-provenance.py`](../scripts/check-provenance.py) is kept outside required CI because it needs
network. **Nothing watches for drift between changes.**

`check-provenance.py` is the sharpest case, because it is the one sensor with no other trigger at all.
It re-fetches every recorded upstream source and reports whether the material this kit adapted has
moved. Nothing schedules it, nothing reminds anyone, and a fold-in whose upstream changed is invisible
until somebody happens to type the command.

**The class is live rather than predicted, and it was measured this week.**
[`bug-0063`](done/bug-0063-the-security-policy-denies-the-prompt-injection-rule-the-kit-ships.md) found
`SECURITY.md` telling a security researcher the kit had no answer to prompt injection, five days after
`A10` landed and after all 22 skills were wired to the module carrying it. It sat wrong across a green
tree for five days because no gate reads a prose claim and nothing runs between changes. That is Epic B
item 19's own argument, with a date on it.

**A published two-trigger pattern exists**, in the "Continuous evals in CI" lesson of Anthropic's
AI-Native SDLC Playbook (`academy.claude.com/courses/ai-native-sdlc-playbook`), read 2026-09-01:
a path-scoped trigger on a pull request touching the agent configuration, plus a schedule. It is
recorded here as an external source rather than as a consolidation, in the form
[`autonomy.md`](../.agents/rules/autonomy.md) established for `A10`. What it settles is only the shape;
the contents below are this repository's own.

## Scope

**In scope:** one scheduled GitHub Actions workflow that runs the drift checks which have no other
trigger, reporting what it finds rather than failing the repository.

Three properties decide whether this is worth having at all:

1. **It reports, it does not go red on weather.** `AGENTS.md` already states the reason
   `check-provenance.py` is out of required CI: "a check that fails when GitHub is slow gets disabled
   within a week." A scheduled job with the same failure mode dies the same death. The exit codes make
   this decidable rather than a judgement: `check-provenance.py` returns 0 for match, **1 for drift**,
   and **2 for could-not-run**. Only 1 is a finding. A 2 is the network, and must not be reported as
   drift or as a red build.
2. **It detects and never rewrites**, per the principle in `autonomy.md`. The script already declines
   upstream's in-place sync for a stated reason; nothing here may reintroduce it.
3. **Its output reaches a person.** A scheduled job whose result nobody sees is the failure this task
   exists to close, one layer out. Decide the mechanism (a job summary, an issue opened or updated, a
   notification) and record what was rejected. **An issue-opening job needs `issues: write`, which is
   wider than the `contents: read` this repository currently grants**, so that is a decision with a cost
   rather than a default.

**Out of scope, each for a stated reason rather than for brevity:**

- **`install.py --check`.** It cannot answer anything in CI. The manifest it reads lives at
  `scripts/.install-manifest.json`, which is gitignored and per-machine, so a fresh clone has nothing
  recorded and the check exits 2 unconditionally. Measured 2026-09-01: `python scripts/install.py --check
  --home <empty>` prints "Nothing recorded as installed ... so nothing can be checked" and exits 2.
  Currency is a local question, and [`install-currency-reminder.py`](../.agents/hooks/install-currency-reminder.py)
  already answers it at session start on the machine where it is decidable. Putting it here would add a
  step that reports "could not run" on every scheduled run forever, which is noise that trains a reader
  to ignore the job.
- **Skill evaluations.** [`feat-0051`](feat-0051-a-paired-evaluation-harness-seeded-from-the-closed-task-corpus.md)
  decides its own cadence, and its amendment A points at this task rather than the other way around. If
  that task chooses a schedule, it joins this workflow then; it does not gate this one.
- **A trigger-collision or description-budget check.** Proposed in the 2026-09-01 review and filed
  nowhere. Do not build it here.
- **Any fix.** The job reports. Every finding it produces becomes a task the normal way.

## Implementation notes

**The document half is the load-bearing half, and skipping it repeats `bug-0063` exactly.** Two claims
in this repository become false the moment anything other than a person invokes `check-provenance.py`:

    SECURITY.md, "The one network call, and what it fetches":
      "**It runs only when you run it.** It is on-demand, deliberately kept out of the required CI
      gates, and no other script, skill, or hook invokes it."

    AGENTS.md, the provenance convention:
      "The check stays out of required CI: it needs network, and a check that fails when GitHub is
      slow gets disabled within a week. Run it on demand."

The `SECURITY.md` sentence is the serious one. It is a claim about network behaviour, in the security
policy, made to a reader deciding whether to trust the kit, and a scheduled workflow would make it a lie
of the same shape and in the same document that `bug-0063` just corrected. **Both sentences move in the
same change as the workflow, not in a follow-up.** The honest replacements say what is true: it is not
invoked by any script, skill, or hook, and one scheduled workflow in this repository runs it against
this repository's own recorded sources, on a stated cadence, fetching exactly what `--list` prints. The
`AGENTS.md` sentence keeps its reasoning, which is still correct, and gains the distinction between
required CI and a reporting schedule.

**A hazard specific to scheduled workflows, worth checking rather than assuming.** GitHub documents that
a scheduled workflow in a public repository is disabled automatically after a period of repository
inactivity. Verify the current rule and the current period against GitHub's own documentation at
implementation time rather than taking this sentence for it. If it holds, it is worth stating in the
workflow's own comment, because a sensor that switches itself off during exactly the quiet stretch it
was built to watch is this kit's recurring failure class wearing a new hat.

**Prior art for the shape** is [`checks.yml`](../.github/workflows/checks.yml): floating major action
tags with the reason recorded, no dependency install step because the kit is standard library only, and
a comment saying why each choice was made rather than what the step does.

## Decisions

- **A path-scoped pull-request trigger was considered and left out of v1.** The playbook pairs one with
  the schedule, and here the pull-request half is already covered: a change touching `.agents/` runs the
  full gate set through `run-checks.py`. What is uncovered is the passage of time, so the schedule is the
  half that closes the gap and the other half would add a trigger for work already gated.

## Risks and rollback

Adds one workflow file and edits two documents; no existing behaviour changes and nothing under
`scripts/` is touched, so `run-checks.py` and CI are unaffected. Reversible by deleting the workflow and
reverting the two document edits in one commit.

The real risk is the one Epic B item 19 names for itself: a sensor that finds nothing is ceremony, and a
sensor that cries wolf gets switched off. The exit-code discipline in property 1 above is what separates
them, and the acceptance bar below is what decides whether it was worth building.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A scheduled workflow exists and runs `check-provenance.py` against this repository.
- [ ] **It has run at least once on its schedule, and the run's verbatim output is recorded in the
      closeout.** A workflow that has only ever been triggered by hand has not been shown to do the one
      thing it was built for.
- [ ] A `check-provenance.py` exit of 2 does not fail the job and is not reported as drift; an exit of 1
      is reported as a finding. Both paths are demonstrated, by a real run or by a forced one, and the
      forcing is described.
- [ ] The workflow's output reaches a person by a stated mechanism, and the closeout names what was
      rejected and why.
- [ ] `SECURITY.md`'s "It runs only when you run it" claim and `AGENTS.md`'s "Run it on demand" claim are
      both corrected in the same change, and neither states anything the workflow falsifies.
- [ ] `grep -c "runs only when you run it" SECURITY.md` returns 0.
- [ ] `run-checks.py` still exits 0 with every gate passing, and the required CI matrix is unchanged.
- [ ] **The bar Epic B item 19 sets for itself: it finds something on a repository nobody has just
      reviewed.** If the first scheduled runs find nothing, record that plainly rather than counting the
      workflow's existence as the result, and say what would make it earn its place.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. This task changes when a network call happens, which is a claim several documents make, so
      the audited set includes `SECURITY.md`, `AGENTS.md`, and `README.md` at minimum.
- [ ] File moved to `.tasks/done/`, `status: done`, with its relative links re-anchored for the extra
      directory level; one dated line added to `CHANGELOG.md` referencing this task id.
