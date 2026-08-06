---
id: feat-0034
title: Add a plugin target to build-adapters.py so the kit installs as a Claude Code plugin
type: feat
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0007]
touched_files:
  - scripts/build-adapters.py
  - docs/spec/build-adapters.md
  - tests/test_build_adapters.py
  - docs/spec/build-adapters.conformance.md
created: 2026-07-28
---

## Problem

Claude Code distributes bundles of skills through a `.claude-plugin/marketplace.json` at a repository
root. The kit has no such manifest, so it cannot be installed as a plugin, which is the discovery path
a Claude Code user is most likely to reach for. `npx skills` also reads
`.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`, so the manifest would serve two
consumers rather than one.

**The manifest is not the hard part, and writing it first is the trap.** Installing a plugin copies
its directory to a cache location, so a plugin cannot reference files outside its own directory by
relative path. All twenty skills reference `../../rules/<file>.md`, which is exactly that pattern.

This is not theoretical. It was verified from the other direction on 2026-07-28 by running
`npx skills` against this repository: it copied only each skill's `SKILL.md`, and `doc-sync`'s
`](../../rules/house-style.md)` link resolved to a path that did not exist. A plugin build that ships
the skills without the rules module reproduces the 2026-07-27 blocker, where `house-review` arrived
with no rubric at all, and it reproduces it on the most visible distribution channel the kit has.

## Scope

**Re-scoped 2026-08-05 by author decision, and the amendment below is authorized by the author on
that decision.** The four options this task originally presented are resolved: the manifest is a
generated artifact, emitted by a new plugin target in
[`scripts/build-adapters.py`](../scripts/build-adapters.py), not a hand-written file. The rejected
three are recorded under Decisions rather than deleted.

**In scope:**

- A `plugin` target in [`scripts/build-adapters.py`](../scripts/build-adapters.py), alongside the
  existing `cursor` and `vscode` emitters, that emits the plugin tree including
  `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`, and places the skills and the
  rules module at paths that resolve from the installed location.
- A scenario for that target in [`docs/spec/build-adapters.md`](../docs/spec/build-adapters.md), plus
  the Proposed Surface rows it changes.
- Tests in [`tests/test_build_adapters.py`](../tests/test_build_adapters.py) matching the shape of the
  existing per-scenario tests.
- A row per new scenario in
  [`docs/spec/build-adapters.conformance.md`](../docs/spec/build-adapters.conformance.md).

**The spec amendment, authorized explicitly, with one hard constraint:**

`build-adapters.md` is an approved contract, so it may not be extended silently. Add the new
scenario with the next free `S-NNN` id, extend the `--target` and `Emitted per skill` rows of the
Proposed Surface table, and add a dated amendment note in the header paragraph matching the form the
`chore-0015` amendment already uses.

**Leave `status: approved` exactly as it is.** Mark the new note as pending the author's
re-approval in its own text instead. The repository has no machine-readable way to say "approved,
with an unapproved amendment inside", and flipping the field to `draft` makes `verifier-agent`
return `blocked` on the run that verifies this very task. Re-approval is the author's and is not
granted here.

**Out of scope:**

- Publishing, submitting, or registering the plugin anywhere. That is a public action and the
  author's.
- Any change to the `.agents/skills/` layout, or to any `SKILL.md` body. The emitter rewrites links
  on the way out, exactly as it already does for Cursor and VS Code; it does not edit sources.
- Changing the `cursor` or `vscode` emitters, or any existing scenario's behaviour. This is a fourth
  target, not a redesign.
- Any change to `scripts/install.py` or `scripts/validate-skills.py`.

## Implementation notes

**The mechanism already exists; this is a fourth target, not a new idea.**
[`rewrite_links()`](../scripts/build-adapters.py) solves precisely this problem for Cursor and VS
Code today: it rewrites the three legal link classes (sibling skill, rules module, skill-local
supporting file) and `emit_shared_assets()` places the material those rewritten links point at.
`SHARED = "../../.agents"` is hardcoded on the assumption that both existing adapter directories sit
exactly two levels below the output root, which is stated as a constraint in the spec. **A plugin
tree may not have that depth**, so check it rather than assuming it, and if the depth differs, make
the shared prefix a property of the target instead of a module constant. That is the one place this
target is likely to need a real change rather than an addition.

**Verify from the installed location, not from this repository.** This is the whole point of the
task and it is the check a schema validator cannot perform. `claude plugin validate` passing is not
evidence the install is sound: the skill loads and reads correctly, and only the absent rubric is
missing. Confirm on disk that a rules-module reference resolves from wherever the plugin build puts
it. Do this for [`house-review`](../.agents/skills/house-review/SKILL.md) in particular, which is the
skill that fails most silently without its rubric.

**The acceptance command takes a path.** `claude plugin validate` with no argument exits non-zero on
usage; the CLI signature is `claude plugin validate [options] <path>`. Point it at the generated
tree, not at the repository root.

**Build into a throwaway directory, never into the repository root.** `--out` defaults to the working
directory, and `.tmp/` is gitignored for exactly this. Generating a `.claude-plugin/` into the repo
root would make the manifest a committed hand-maintained file again, which is the outcome this
re-scope exists to prevent.

`bug-0007` is a dependency for a plain reason: eight descriptions were not valid YAML, and a plugin
manifest describing skills a parser rejects is worse than no manifest. It is in `.tasks/done/`.

## Decisions

- **Rejected: ship the rules module inside each skill directory** and rewrite each reference to a
  skill-local path. Every link would resolve everywhere, at the cost of twenty copies of a file whose
  entire purpose is that an adopter can swap it in one place. Swapping would then mean editing twenty
  copies, destroying the property the module exists for.
- **Rejected: ship the rules module as a plugin-root sibling** and rewrite references to whatever
  path resolves inside the plugin cache. One copy and the swap point survives, but it requires
  knowing the cache layout precisely and pins the kit to it.
- **Rejected: inline each lens into the skills that compose it.** No links to break and
  `house-review` carries its own rubric, at the cost of swappability entirely, contradicting the
  reason [`review-quality.md`](../.agents/rules/review-quality.md) was split out.
- **Chosen: generate the plugin build**, because the problem is already solved once in this
  repository, the solution is specified and tested, and the rewriting rules are exactly the ones a
  plugin needs. A hand-maintained manifest duplicating what a generator could emit is the parallel
  copy the portability contract exists to prevent, and this repository has been bitten three times by
  a hand-maintained second copy (`house-review`'s rubric, `bug-0006`'s parser, and the three
  frontmatter readers in `scripts/`).

## Risks and rollback

Required: this touches more than one module (the generator, its contract, its tests, and its
conformance matrix), and it adds a distribution channel where a broken one is worse than an absent
one because it looks supported.

- **The specific risk is a manifest that validates and installs skills whose composed lens dangles**,
  which is silent. Mitigate with the on-disk check above, and do not treat `claude plugin validate`
  passing as evidence the install is sound.
- **The second risk is regressing the two existing targets** while touching shared code such as
  `SHARED` or `rewrite_links()`. Mitigate by keeping every existing test unchanged in intent and
  green.
- Reverting is one commit. Nothing is published, so no revert has to reach anyone else's machine.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] `python scripts/build-adapters.py --target plugin --out <throwaway>` emits the plugin tree,
      reports its counts, and exits zero.
- [ ] `claude plugin validate <throwaway>` passes against the generated manifest, with the command
      and its verbatim output recorded.
- [ ] A skill emitted through the plugin path resolves its rules-module reference **on disk from the
      installed location**, verified by resolving the path rather than by reading the link text.
- [ ] `house-review` in particular arrives with its rubric reachable.
- [ ] The rules module has exactly one authoritative copy in the emitted tree, or the decision to
      duplicate it is recorded with its reason.
- [ ] The new scenario exists in `docs/spec/build-adapters.md` with the next free `S-NNN` id, the
      Proposed Surface rows are updated, and a dated amendment note is present that states
      re-approval is pending.
- [ ] `docs/spec/build-adapters.md` still reads `status: approved`, unchanged.
- [ ] A test per new scenario in `tests/test_build_adapters.py`, tagged with its `S-NNN` id in the
      same style as the existing tests.
- [ ] A conformance row per new scenario in `docs/spec/build-adapters.conformance.md`, with evidence
      by code location.
- [ ] An unrecognized target is still rejected non-zero, and `cursor` and `vscode` still emit exactly
      what they did before.
- [ ] Existing tests still pass, unchanged in intent.
- [ ] Nothing is published, submitted, or registered, and no `.claude-plugin/` directory is written
      into the repository itself.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
