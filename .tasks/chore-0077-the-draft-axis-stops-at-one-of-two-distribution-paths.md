---
id: chore-0077
title: The draft axis stops at one of the two distribution paths, and the kit now has a draft skill
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - docs/spec/build-adapters.md
  - docs/spec/build-adapters.conformance.md
  - docs/spec/install.md
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
  - .agents/skills/agent-observatory/SKILL.md
created: 2026-08-29
---

## Problem

The kit has two paths that put a skill in front of an agent, and only one of them knows what a
draft is.

[`install.py`](../scripts/install.py) honours `metadata.status: draft` and places such a skill under
no profile, including `all`. [`build-adapters.py`](../scripts/build-adapters.py) does not: it has
its own `discover_skills()` (the third copy, per `bug-0027`) and generates for every skill it finds.
Run today:

    python scripts/build-adapters.py --dry-run
    [dry-run] cursor  agent-observatory -> .cursor\rules\agent-observatory.mdc
    [dry-run] vscode  agent-observatory -> .github\prompts\agent-observatory.prompt.md

**The divergence is recorded, deliberate, and was reasoned about.**
[`install.md`](../docs/spec/install.md) states it under Non-Goals, decided 2026-08-05 by
`feat-0036`, with three reasons: `build-adapters.py` has its own approved contract and extending
the axis is that contract's amendment to make; `install.py` writes into an adopter's global
discovery directory where an unblessed skill arrives looking blessed, while adapter generation
writes into one named project at the request of whoever runs it; and an adapter is a derived
artifact regenerated on demand rather than something a harness silently keeps loading. That
passage ends by naming this task: "The inconsistency is real and is worth its own task: a
maintainer who wants a draft withheld everywhere should amend `build-adapters.md` too."

**What changed is that the axis stopped being theoretical.** `feat-0060` added
`agent-observatory`, the kit's first draft skill, so there is now something for the two paths to
disagree about. Two consequences are checkable rather than hypothetical:

- `run-checks.py`'s adapter gate reports `42 adapter file(s) for 21 skill(s)`, the draft included,
  while its install gate reports `20 of 21`.
- [`agent-observatory`](../.agents/skills/agent-observatory/SKILL.md)'s own body says "It ships with
  no profile and reaches no adopter until it has been used on real work and blessed." That is true
  of one path and false of the other, in a sentence a reader has no reason to doubt.

## Scope

**In scope:** ending the silent disagreement, whichever way the author decides.

The decision is not this task's to make. [`build-adapters.md`](../docs/spec/build-adapters.md) is
`status: approved`, and AGENTS.md makes an approved contract human-owned, so the first step is to
put the question to the author with the three recorded reasons in front of them. Both outcomes are
legitimate and each has an artifact:

- **Carry the axis over.** Amend `build-adapters.md` for the draft behaviour, implement it, update
  `build-adapters.conformance.md`, and correct the `install.md` passage that currently says the axis
  stops at that boundary.
- **Keep the divergence.** Then it is stated where a reader would otherwise be misled: the skill
  body's "reaches no adopter" sentence is qualified to name the path it is true of, and
  `install.md`'s passage is updated to say the inconsistency was re-examined once a draft existed
  and deliberately kept.

**Out of scope:**

- **Deciding it without the author.** Implementing the amendment because it looks tidier is
  rewriting an approved contract to match a preference.
- **Unifying the three copies of `discover_skills()`.** `bug-0027` recorded copying rather than
  importing as a deliberate decision, and re-litigating it here would bury this question inside a
  larger refactor.
- **Any other axis of `install.py` that `build-adapters.py` lacks.** This is about the draft marker
  and nothing else.
- **Whether `agent-observatory` should stay a draft.** That is the contribution bar's question and
  the author's, answered by using the skill.

## Implementation notes

**Read the three recorded reasons before proposing either outcome.** They are the strongest
statement of the case for the status quo and they were written by someone who had the whole picture;
a proposal that does not engage with them is not a proposal. The second reason in particular still
holds: a global discovery directory and a named project someone asked for are different exposures.

**The fact that changes the balance is not that a draft now exists but where the adapter lands.**
Adapter output is generated into a target project on request, is not tracked by git here, and is not
in `.gitignore` either, so nothing is shipped today. Establish what an adapter for a draft actually
does in a target project before weighing it, rather than reasoning from the word "distribution".

**If the axis is carried over, mirror `install.py`'s reporting rather than only its filtering.** The
installer says what it withheld ("1 skill(s) marked a draft are excluded from every profile,
including 'all': agent-observatory"), which is what made this divergence visible at all. A silent
filter in the adapter builder would trade one invisible behaviour for another.

**`feat-0036`'s parser is the prior art**, including why only the block form
`metadata:\n  status: draft` is read: a bare top-level `status:` key is rejected by the skill
schema's allow-list, and the flow form trips `validate-skills.py`'s plain-scalar check.

## Decisions

- **A premise that turned out false: the divergence is wider than filed, and the baseline moved.**
  This task calls `agent-observatory` "the kit's first draft skill" and quotes
  `42 adapter file(s) for 21 skill(s)` beside an install gate reading `20 of 21`. At this base the kit
  holds 22 skills and two frontmatter drafts, `agent-observatory` and `systematic-debugging`, and
  `build-adapters.py --dry-run` reports `44 adapter file(s) for 22 skill(s)`. All three targets emit
  both drafts, the plugin tree included.

- **A premise that turned out false: the second of the three recorded reasons no longer covers every
  target.** [`install.md`](../docs/spec/install.md)'s Non-Goals passage weighs adapter generation as
  writing "into one named project at the request of whoever runs it", decided 2026-08-05 by
  `feat-0036`. `feat-0034` added the `plugin` target the following day, 2026-08-06, and a plugin tree
  carries a `.claude-plugin/marketplace.json` naming a published plugin with a homepage and a version.
  A draft emitted there reaches everyone who installs the plugin, which is the unbounded exposure that
  reason was drawn to exclude. The reason was sound when written; one of the three targets it now has
  to cover did not exist yet.

- **A rejected alternative: implementing either branch.** No author decision is recorded, here or
  anywhere in the repository, and this task's own Risks section says a run that comes back with the
  code changed and no recorded decision should be rejected whatever the tests say. Both branches amend
  an approved contract, so neither is the conservative one to take by default.

- **A rejected alternative: a characterization test pinning today's behaviour.** It changes nothing
  and would satisfy the letter of the third acceptance criterion, but a test asserting that a draft
  *is* emitted writes the unchosen branch into the suite, which is the "deciding it without the
  author" the Scope rules out.

- **A seam left open deliberately: there is no adapter-side analogue of `draft_conflicts()`.**
  `install.py` refuses the whole run when a placed skill references a draft sibling, because both
  silent resolutions are defects. Neither draft here is reachable that way today: nothing links either
  as `../<name>/SKILL.md`, and neither links a sibling. So the amend branch needs no conflict
  machinery now, and the first draft that is linked reopens the question.

## Risks and rollback

The task touches more than one module, so the deterministic rule fires on the first condition: an
approved specification, the adapter builder, its tests, its conformance matrix, and a skill body.

**The consequential risk is amending an approved contract on an agent's initiative.** That is the
failure the human-owned rule exists to prevent, and it is why the decision step is in scope and the
decision itself is not. A run that comes back with the code changed and no recorded author decision
should be rejected regardless of whether the tests pass.

The second risk is quieter: changing what the adapter builder emits changes the adapter gate's
counts in `run-checks.py`, and a test or a document asserting `42 adapter file(s) for 21 skill(s)`
will move with it. Find those before changing behaviour, not after.

Rollback is reverting one commit. No persisted format changes and no adopter has received anything,
since adapter output is generated on demand and tracked nowhere in this repository.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The author's decision is recorded in this task file, in their words, before any behaviour
      changed.
- [ ] The two paths no longer disagree silently: either `build-adapters.py --dry-run` withholds a
      draft skill and says which, or the skill body and `install.md` state the divergence in the
      places a reader meets it.
- [ ] A test pins whichever behaviour was chosen, so the next draft skill cannot re-open the
      question by accident.
- [ ] If the axis was carried over, `build-adapters.md` is amended and
      `build-adapters.conformance.md` is updated for the amended scenarios, with its arithmetic
      closing.
- [ ] `install.md`'s Non-Goals passage no longer describes a state that has changed.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
