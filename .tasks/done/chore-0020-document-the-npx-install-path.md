---
id: chore-0020
title: Document npx skills as a second install path, with its limitation stated
type: chore
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0007]
touched_files:
  - README.md
  - docs/GETTING-STARTED.md
created: 2026-07-28
---

## Problem

`npx skills` (vercel-labs/skills, indexed at skills.sh) is the de facto cross-agent skill installer,
covering Claude Code, OpenCode, Codex, Cursor and many more. This repository is discoverable by it
today with no changes: `.agents/skills/` is one of the layouts it walks, so **no `.skills.json` or
other manifest is needed**, which was the open question when this was filed.

An adopter who already uses that tool has no reason to know the kit works with it, and the README
offers only the Python installer.

## Scope

**In scope:** document `npx skills` as a second install path in [`README.md`](../../README.md) and
[`docs/GETTING-STARTED.md`](../../docs/GETTING-STARTED.md), with its limitation stated plainly, keeping
`install.py` as the complete, offline, standard-library-only path. Do not delete or demote the existing
quick start.

**Out of scope:** fixing the limitation, which is `feat-0034`'s shared blocker (see below). Submitting
the kit to skills.sh or any registry, which is a public action and the author's. Fixing the eight
malformed descriptions, which is `bug-0007` and must land first.

## Implementation notes

**This task carries a decision, not just prose, and it should be made before writing.** Verified by
running the tool against this repository on 2026-07-28:

- **8 of 19 skills were rejected outright** as malformed YAML. `bug-0007` fixes that, hence the
  dependency. Documenting the path before that lands would advertise an install that silently drops
  eight skills.
- **All 11 that did install arrived with a dangling lens.** The install copies only the skill's
  `SKILL.md` into `<project>/.claude/skills/<name>/`, plus a `skills-lock.json` at the project root.
  Nothing outside the skill directory travels, so every skill's `../../rules/<file>.md` reference
  resolves to nothing. Confirmed concretely: `doc-sync` installed, and its
  `](../../rules/house-style.md)` link resolved to a path that does not exist.

All nineteen skills reference the rules module, so **after `bug-0007` lands, `npx skills` will install
nineteen skills of which nineteen have a dangling lens reference.** For most that costs the house-style
module. For `house-review` it costs the entire rubric and severity scheme, which is the exact failure
this kit shipped in 2026-07-27 and wrote a portability contract to prevent.

So the honest options, and this is the author's call:

1. **Document it with the limitation stated.** One sentence: this path installs the skill bodies, and
   the lens module they compose travels only via `install.py`, so use `install.py` if you want
   `house-review`'s rubric. Cheapest, honest, and leaves a known-degraded path documented.
2. **Do not document it until the lens problem is solved.** Defensible: the contribution bar's whole
   principle is that a path nobody has verified end to end does not ship, and "works except for the
   part that made it work" is thin.
3. **Solve the lens problem first**, then document without a caveat. The shared blocker below.

Recommendation: option 1, because the path already works for anyone who finds it and an undocumented
degraded path is worse than a documented one. But say the limitation in the same breath as the command,
not in a footnote.

**The lens problem is one problem with two consumers.** `feat-0034`'s plugin manifest hits the identical
constraint from the other direction, since installing a plugin copies its directory to a cache and a
plugin cannot reference files outside it. Decide the lens strategy once, for both. The options there
(ship the lens inside each skill directory, inline it, or accept the degradation) all have real costs,
and the swappability that makes the module worth having is what makes duplicating it into nineteen
directories unattractive. Worth a roadmap entry rather than being settled inside either task.

Other notes:

- Keep the README's existing numbered quick start as the primary path. Add the alternative after it, not
  before, and say in one clause why `install.py` remains the recommended one (it carries the lens, needs
  no Node, and works offline).
- `docs/GETTING-STARTED.md` is written for non-specialists, so it gets the command and the caveat in
  plain language, not the mechanism.
- Pin nothing. Do not document a version number for a third-party tool the kit does not control.

## Acceptance criteria (mechanically verifiable)

    python scripts/build-adapters.py --dry-run

- [x] `README.md` documents the `npx skills` path after the existing quick start, which is unchanged.
- [x] `docs/GETTING-STARTED.md` documents it in plain language.
- [x] Both state the lens limitation in the same passage as the command, not as a footnote.
- [x] Both state that `install.py` remains the complete path, and why in one clause.
- [x] No claim is made about a registry listing or a supported version.
- [x] Every relative link added resolves; CI's link check still reports zero broken links.
- [x] All four repository checks still pass.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

Option 1, on the author's decision: documented with the limitation stated in the same passage as the
command, not in a footnote. `README.md` gets a `3b` section after the existing quick start, which is
untouched. `docs/GETTING-STARTED.md` gets a `4a` section in plain language for a non-specialist reader,
naming the consequence rather than the mechanism ("those skills arrive with the pointer but not the thing
it points at. Nothing errors; the skill just quietly has less to work with").

Both say `install.py` remains the complete path and why in one clause: it places the rules module where
the skills' own references resolve, and needs no Node and no network. No version is pinned and no
registry listing is claimed, since neither is the kit's to promise.

**The honest state of this path, recorded so nobody has to rediscover it:** after `bug-0007`, all
nineteen skills install, and all nineteen arrive with a dangling lens reference. For most that costs the
house-style module. For `house-review` it costs the entire rubric and severity scheme, which is the
2026-07-27 blocker reproduced on a channel the kit does not control. The README says exactly that,
naming `house-review`, because a reader choosing between two installers deserves the specific
consequence rather than a general caution.

**The lens problem was not solved here and remains the shared blocker with `feat-0034`.** It is one
problem with two consumers, and the four options (duplicate the lens per skill, place it as a
plugin-root sibling, inline it, or accept the degradation) each cost something real. The recommendation
recorded in `feat-0034` is to extend `build-adapters.py` with a plugin target rather than hand-write a
manifest, since that generator already solves link rewriting for two other harnesses. Deciding it once,
for both consumers, is the point.
