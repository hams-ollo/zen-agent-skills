---
id: feat-0034
title: Add a Claude Code plugin manifest, once the lens-portability constraint is solved
type: feat
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0007]
touched_files:
  - README.md
created: 2026-07-28
---

## Problem

Claude Code distributes bundles of skills through a `.claude-plugin/marketplace.json` at a repository
root. The kit has no such manifest, so it cannot be installed as a plugin, which is the discovery path a
Claude Code user is most likely to reach for. `npx skills` also reads
`.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`, so the manifest would serve two
consumers rather than one.

## Scope

**In scope:** a `.claude-plugin/marketplace.json` and a plugin manifest describing this kit's skills, and
a README pointer to the plugin install path.

**Files this task creates**, named here rather than in `touched_files` because `validate.py --strict`
requires every declared path to exist and these do not exist yet. That is a real limitation of the check
for any task that creates files and stays open, and it is why the list lives in prose:

- `.claude-plugin/marketplace.json`
- `.claude-plugin/plugin.json`

If the recommendation below is taken, both become generated artifacts and the touched surface is
`scripts/build-adapters.py`, its spec, its tests, and its conformance matrix instead.

**Out of scope:** publishing or submitting the plugin anywhere, which is a public action and the
author's. Any change to `.agents/skills/` layout. Solving the lens problem, which this task must not
work around silently (see below).

## Implementation notes

**Solve this first or the manifest is not worth writing: installing a plugin copies its directory to a
cache location, so a plugin cannot reference files outside its own directory by relative path. All
nineteen skills reference `../../rules/<file>.md`, which is exactly that pattern.**

This is not a theoretical concern. The same constraint was verified from the other direction on
2026-07-28 by running `npx skills` against this repository: it copied only each skill's `SKILL.md`, and
`doc-sync`'s `](../../rules/house-style.md)` link resolved to a path that did not exist. A plugin build
that ships the skills without the rules module reproduces the 2026-07-27 blocker, where `house-review`
arrived with no rubric at all, and it reproduces it on the most visible distribution channel the kit has.

The options, none free, and the choice is the author's:

1. **Ship the rules module inside each skill directory** and rewrite each reference to a skill-local
   path. Every link resolves everywhere, at the cost of nineteen copies of a file whose entire purpose
   is that an adopter can swap it in one place. Swapping it would then mean editing nineteen copies,
   which destroys the property the module exists for.
2. **Ship the rules module as a plugin-root sibling** and rewrite references to whatever path resolves
   inside the plugin cache. One copy, and the swap point survives. Requires knowing the cache layout
   precisely, and pins the kit to it.
3. **Inline each lens into the skills that compose it.** No links to break, and `house-review` carries
   its own rubric. Costs swappability entirely, and contradicts the reason
   [`review-quality.md`](../.agents/rules/review-quality.md) was split out.
4. **Generate the plugin build** the way [`build-adapters.py`](../scripts/build-adapters.py) already
   generates adapters. It solves this exact problem for Cursor and VS Code today: it copies the shared
   material into the output tree and rewrites the three legal link classes to point at it. A plugin
   emitter would be a fourth target rather than a new mechanism.

**Recommendation: option 4.** The problem is already solved once in this repository, the solution is
specified in [`docs/spec/build-adapters.md`](../docs/spec/build-adapters.md), tested, and the rewriting
rules are exactly the ones a plugin needs. Writing a hand-maintained manifest that duplicates what a
generator could emit is the kind of parallel copy the portability contract exists to prevent, and this
repository has now been bitten three times by a hand-maintained second copy (`house-review`'s rubric,
`bug-0006`'s parser, and the three frontmatter readers in `scripts/`).

If option 4 is chosen, this task becomes "add a plugin target to `build-adapters.py`", which needs a
scenario in that contract and therefore the author's explicit instruction, and the manifest files above
become generated artifacts rather than hand-written ones. Re-scope the task before starting rather than
writing the manifest by hand and discovering this halfway.

Other notes:

- `bug-0007` is a dependency for a plain reason: eight descriptions are not valid YAML, and a plugin
  manifest describing skills a parser rejects is worse than no manifest.
- Verify against the real tool rather than the schema. `claude plugin validate` is the acceptance
  command, and the `claude` CLI is present on this machine.
- Whatever is produced, confirm on disk that a lens reference resolves **from the installed location**,
  not from this repository. That check is the whole point of the task, and it is the one a schema
  validator cannot perform.

## Risks and rollback

Required: this adds a distribution channel, and a broken one is worse than an absent one because it
looks supported.

The specific risk is shipping a manifest that validates and installs skills whose composed lens dangles,
which is silent: the skill loads and reads correctly, and only the absent rubric is missing. Do not treat
`claude plugin validate` passing as evidence the install is sound. Reverting is one commit, but an
installed plugin on someone else's machine is not something a revert reaches, which is why nothing here
is published without the author.

## Acceptance criteria (mechanically verifiable)

    claude plugin validate

- [ ] `claude plugin validate` passes against the manifest.
- [ ] A skill installed through the plugin path resolves its `../../rules/` lens reference on disk, verified from the installed location rather than from this repository.
- [ ] `house-review` in particular arrives with its rubric reachable, since it is the skill that fails most silently without one.
- [ ] The lens module has exactly one authoritative copy, or the decision to duplicate it is recorded with its reason.
- [ ] All four repository checks still pass.
- [ ] Nothing is published, submitted, or registered.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in the `AGENTS.md` conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
