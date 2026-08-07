---
id: feat-0044
title: Consolidate the kit's unattended-work rules into a swappable autonomy module
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #1: autonomy.md v1"
depends_on: []
touched_files:
  - .agents/rules/autonomy.md
  - AGENTS.md
  - ROADMAP.md
created: 2026-08-07
---

## Problem

The kit had no written ceiling for what an agent may do when nobody is watching. Every rule that
governs unattended work existed as prose inside one skill, applying only to agents that happened to
read that skill, and the thing those rules had in common was never named anywhere.

That common thing is one principle, and it was already stated verbatim in the codebase without ever
being lifted out: [`install.py`](../../scripts/install.py)'s `check()` docstring reads "Detect and
report, never rewrite." The same rule is applied independently by
[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md), by
[`review-quality.md`](../../.agents/rules/review-quality.md) protocol rule 6, and by
[`check-provenance.py`](../../scripts/check-provenance.py), which reports drift and deliberately
declines upstream's in-place sync.

Four independent components reached the same rule. Nothing named it, so nothing could compose it,
and an agent dispatched to a cloud session inherited none of it.

## Scope

**In scope:** a fourth swappable module at [`autonomy.md`](../../.agents/rules/autonomy.md), beside
`house-style.md` and `review-quality.md`, organised around the one named principle with the rules as
its applications. Every rule carries a citation to where it was already exercised. Register the
module in the layout table in `AGENTS.md`, and annotate the roadmap item.

**Out of scope:**

- **Any rule that cannot be cited.** That is the whole gate, and it is what separates a consolidation
  from an invention. Rules wanted but held for want of a citation belong in a named section of the
  module, not in its rule list.
- Composing the module into any skill. Nothing references it yet by design; Epic E item 5
  (`fix-batch` cloud mode) is its first consumer.
- Any change to `install.py`. The rules directory travels whole, so the module ships with no
  installer change. Verified rather than assumed.
- Blessing it. The contribution bar requires a real run first, which is Epic E item 2.

## Implementation notes

**The implementation landed before this task file existed**, in commit `254c810`. That ordering is
backwards and is recorded rather than hidden: the module was authored directly during a planning
session, and this file exists so the work can close out through the normal lifecycle, since a
`CHANGELOG.md` entry references a task id and 104 existing lines follow that form.

What remains is closeout, not implementation: `doc-sync`, the changelog line, and the move to
`.tasks/done/`.

## Decisions

- **`A8` is the one rule whose specific form is not yet exercised**, and it says so in its own text
  rather than being presented as consolidated. The shape is cited to
  [`pr-describe`](../../.agents/skills/pr-describe/SKILL.md), which drafts and never touches GitHub, but
  the ceiling itself (a `claude/` branch and a draft pull request that is never merged) is a decision
  recorded in `ROADMAP.md` Epic E. Confirming or amending it against a real run is Epic E item 3's
  first job.
- **Three candidates were rejected for v1 for want of a citation**: retry limits, compute budgets,
  and escalation paths. They are named in the module's held section, because a gate that excludes
  nothing is not a gate.
- **Links to files outside the installed skill tree are named in prose, not linked.** The module
  ships to adopters without this repository around it, so a link that escapes the tree resolves here
  and dangles everywhere it actually runs, per the portability contract in `AGENTS.md`.

## Risks and rollback

Required: it touches more than one area (the rules module, `AGENTS.md`, and `ROADMAP.md`). The rule
is deterministic rather than a judgment about how risky the work feels, so it is applied even though
the change is entirely prose.

- **The real risk is the module being wrong rather than breaking anything.** It ships to adopters and
  states a ceiling in absolute terms, so a rule that is subtly overreaching constrains work in
  repositories nobody here can see. That is why v1 holds only cited rules and why Epic E item 3
  hardens it from a real run before it is blessed.
- A second risk is silent inertness: nothing composes the module yet, so a mistake in it surfaces
  only when Epic E item 5 first reads it. Accepted deliberately, and named in the module's own text.
- Rollback is one revert of commit `254c810` plus this file. The rules directory travels whole, so
  no installer change needs undoing.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py"

- [x] `.agents/rules/autonomy.md` exists, organised around one named principle with the rules as its
      applications.
- [x] Every rule carries a citation: a file, a task id, or a recorded incident.
- [x] At least one rule is named as not-yet-exercised rather than presented as consolidated.
- [x] A section names candidates held for want of a citation.
- [x] `AGENTS.md`'s layout table lists the module.
- [x] `install.py` places it and `--uninstall` reverses it, with no installer change.
- [ ] The roadmap item is annotated authored-not-blessed and left unstruck, per the contribution bar.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
