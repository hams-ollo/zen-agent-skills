---
id: chore-0021
title: Release hygiene for v0.1.0, with the publish steps left to the human
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - README.md
  - CHANGELOG.md
created: 2026-07-28
---

## Problem

The repository is public with no tag, no release, and no topics. Three consequences:

- **Nothing is citable.** `SECURITY.md` says the kit is distributed from `main` and adopters pick up
  fixes by pulling, which is honest and also means nobody can say which version they are running or
  report a bug against one.
- **Nothing is discoverable.** GitHub topics are the search surface for a repository like this one, and
  there are none.
- **Nothing tells a reader how this differs from its neighbours.** The nearest projects by function are
  obra/superpowers (parallel subagent development lifecycle) and GitHub Spec Kit (specify, plan, tasks,
  implement). A reader who knows those two has no way to tell from this README what is different here,
  and the difference is real: neither ships an independent verification stage that can return a
  `blocked` verdict, and the standing critique of spec-driven tooling is that acceptance criteria do not
  run and specs drift from the implementation within hours. `verifier-agent` and `doc-sync` are the
  answers to both, and the README does not say so.

## Scope

**In scope:** prepare a `v0.1.0` release. That means: a short README section stating what the kit is and
is not relative to those two neighbours; a `CHANGELOG.md` release heading grouping what `v0.1.0`
contains; and a written, ordered list of the publish steps for the author to run.

**Out of scope, and human-owned:** creating or pushing the tag, cutting the GitHub release, and setting
the repository topics. A public tag on a public repository is effectively permanent and is the first
thing that looks like a release, so an agent prepares it and a person publishes it. Also out of scope:
the full README positioning rewrite, which is a larger roadmap item; this task adds one section, not a
restructure.

## Implementation notes

- **Do not restructure `CHANGELOG.md`.** It is an append-only ledger and its entries are correct as
  written. A release heading is added above the existing entries, not woven through them, and no
  existing line is edited. This is the constraint most likely to be violated by a well-meaning attempt
  to "organise for the release".
- Derive the release contents from the ledger rather than from memory. Every entry is dated and
  references its task id, so the `v0.1.0` set is what is already recorded.
- **The positioning section is three or four sentences, not a manifesto.** What it must say: this is a
  library of portable skills plus the tooling to distribute them, not a framework and not an agent
  runtime; the distinguishing property is evidence discipline (no skill ships without having been used
  on real work, verification is recorded with evidence, and coverage is stated honestly rather than
  implied); and the two capabilities that follow from it are an independent verification stage with a
  `blocked` verdict and documentation-drift detection. Name the neighbours plainly and factually. Do not
  disparage them, and do not claim a comparison that has not been tested: the claim is about what this
  kit ships, not about which is better.
- Version `0.1.0` and not `1.0.0`, because the kit is one maintainer's working library, three skills are
  explicitly held pending real use, and the install story has an open portability question
  (`chore-0020`, `feat-0034`). `0.1.0` says that accurately.
- **Confirm the version number with the author before writing it anywhere.** It appears in the changelog
  heading and the tag, and a published tag is not cheaply retracted.
- For the topics, propose a list rather than setting one: `agent-skills`, `claude-code`, `agents-md`,
  `ai-agents`, `developer-tools`, `spec-driven-development`. The author applies them.
- Write the publish steps as a numbered list in the task's outcome, in the order they must run, with the
  exact commands. That list is the deliverable an agent can produce and a human can execute.

## Risks and rollback

Required: this task's output leads to an irreversible public action, even though it performs none.

The risk is that the prepared material is treated as already published, or that a later session reads
the changelog heading and assumes the tag exists. Word the heading so it describes a prepared release
until the tag is pushed, and state in the task outcome that no tag was created. Everything this task
writes reverts with one commit; the tag it prepares does not, which is why it does not create one.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict

- [ ] `README.md` has a section, three or four sentences, naming obra/superpowers and GitHub Spec Kit and stating what this kit is and is not.
- [ ] That section makes no comparative quality claim, only claims about what this kit ships.
- [ ] `CHANGELOG.md` has a `v0.1.0` heading above the existing entries, and **no existing line is edited**, verified by the diff touching only added lines.
- [ ] The version number is confirmed with the author before it is written.
- [ ] The task outcome carries the ordered publish steps with exact commands, and a proposed topic list.
- [ ] No tag exists, no release exists, and no repository setting changed: `git tag --list` is empty and `gh release list` is empty.
- [ ] All four repository checks still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in the `AGENTS.md` conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
