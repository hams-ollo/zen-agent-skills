---
id: feat-0033
title: Give install.py a --profile axis that reports its description budget and never ships a dangling sibling
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: docs/spec/install.md
scenarios: [S-013, S-014]
touched_files:
  - docs/spec/install.md
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.conformance.md
created: 2026-07-28
---

## Problem

`python scripts/install.py` installs all nineteen skills, and there is no way to ask for fewer. The 19
descriptions total roughly 15,100 characters, and a `description` is loaded for every installed skill so
an agent can route to it. That budget is shared with every other skill an adopter has installed, so a
default install spends most of a routing budget on skills the adopter may never use, and the cost is
invisible: nothing in the install output says what was spent.

An adopter who wants only the work-tracking front door currently has no supported way to get it, and the
`--tools` axis does not help, since it changes *which harnesses* receive all nineteen.

## Scope

**In scope:** a `--profile` flag alongside `--tools`, with `core`, `spine`, and `all`; a default smaller
than all nineteen; per-profile description-character totals in the install summary; the sibling-closure
rule below. Amend [`docs/spec/install.md`](../../docs/spec/install.md) first, then implement, then test,
then update the conformance matrix.

**Out of scope:** reducing the coupling between skills, which is what actually limits how small a profile
can be (filed at the roadmap altitude, see below). Per-skill selection (`--skills a,b,c`), which is a
different flag with a different safety story. Any change to `--tools`, `--mode`, `--home`, `--dry-run`,
or `--uninstall` behavior. Changing what the manifest records per entry.

## Implementation notes

**Read this first: a naive profile filter reintroduces the defect that has already shipped twice here.**
Fourteen skills reference a sibling as `../<name>/SKILL.md`. Installing a subset that omits a referenced
sibling leaves exactly the dangling reference `validate-skills.py` S-011 raises as an error and
`AGENTS.md`'s portability contract calls a silent failure, and some of those references are load-bearing
rather than decorative: `doc-sync` composes `doc-revise`'s editing discipline by reference and
deliberately does not restate it, so shipping `doc-sync` without `doc-revise` reproduces the
`house-review`-without-its-rubric failure in a new place.

So a profile is **closure-complete**: expand the requested seed over sibling references until closed, and
install that. Compute the closure rather than hand-maintaining a list, or the list silently rots the next
time a skill gains a reference.

**The reference graph, measured 2026-07-28, dictates the profile boundaries.** It has one strongly
connected component of fourteen skills (`doc-author`, `doc-revise`, `doc-sync`, `fix-batch`,
`house-review`, `new-task`, `reconcile-worktrees`, `spec-author`, `spec-conformance`,
`spec-plan-readiness`, `spec-quality`, `test-author`, `test-quality`, `verifier-agent`). Every one of
those fourteen reaches seventeen skills. Separately: `agent-handoff` and `human-handoff` form a closed
pair, and `init-worktracking`, `pr-describe`, and `project-bootstrap` reference no sibling at all.

The consequence is the finding, and it should be stated in the spec rather than discovered by the next
person: **there is no useful middle size.** Any profile touching the fourteen is at least seventeen
skills; anything smaller is drawn only from the five separable ones. `new-task` is inside the component,
so a "just the work tracking" profile is not available at any size. The boundaries below are what the
graph permits, not what taste would choose:

- `core`: `project-bootstrap`, `init-worktracking`, `pr-describe`. Closed at three. Scaffold a project,
  track work in it, describe the change at the end.
- `spine`: the fourteen plus the three leaves they reach, seventeen in total. The delivery loop.
- `all`: nineteen. Adds the `agent-handoff` and `human-handoff` pair.

Default to `spine`. It is smaller than `all`, it is the coherent recommended set, and the two skills it
drops happen to be the two longest descriptions in the kit, so the default saves real budget rather than
a token amount.

Other notes:

- Report the character total for the profile being installed **and** for each profile, so the number is
  comparable rather than absolute. Report it as a count, not as a percentage of any harness's budget: the
  budget scales with the context window and is shared with skills this tool cannot see, so a percentage
  here would be a number the tool cannot honestly compute.
- Say when the closure expanded the request. An adopter who asks for `core` and gets three is informed;
  one who asks for a seed that silently became seventeen is not.
- `--profile` and an unrecognised value must be rejected the way `--tools` rejects one (S-009): name it,
  place nothing, exit non-zero. Reuse that shape rather than inventing a second error style.
- Two scenarios: **S-013** for profile selection with closure completion, **S-014** for the budget report.
- Leave `discover_skills()` returning everything and filter above it. It is used by the uninstall path
  reading the manifest, and narrowing it would scope reversal to the current profile, which is not what
  `--uninstall` promises.

## Risks and rollback

Required: this changes what a default `install.py` places, which is a change to the observable behavior
of the command every adopter runs.

The risk is an adopter who re-runs after this lands and finds two skills removed. It does not remove them:
`install` only places and updates, and reversal is `--uninstall`, so previously installed
`agent-handoff` and `human-handoff` directories stay on disk and stay in the manifest. They simply stop
being refreshed unless `--profile all` is passed. Say so in the spec, because "the default changed and
your existing install is now partly stale" is exactly the kind of quiet outcome this repository treats as
a defect. Reverting is one commit plus the spec amendment.

## Acceptance criteria (mechanically verifiable)

    python scripts/install.py --dry-run --home ./.tmp/zen-home

- [x] `--profile core|spine|all` is accepted; the default is `spine` and places fewer than nineteen skills.
- [x] An unrecognised profile names it, places nothing, and exits non-zero.
- [x] Every profile is closed over sibling references: no installed skill references a skill the same run did not place.
- [x] `core` resolves to exactly three skills, `spine` to seventeen, `all` to nineteen.
- [x] The summary reports the description-character total for the installed profile and for each profile.
- [x] A run that expanded the seed says so.
- [x] `--uninstall` still reverses every recorded target beneath `--home`, regardless of the profile that placed it.
- [x] `docs/spec/install.md` carries S-013 and S-014 and records the amendment and its authority.
- [x] `docs/spec/install.conformance.md` has a row per new scenario and lists both in its test-coverage table.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

`--profile core|spine|all`, defaulting to `spine`. Measured by execution:

| Profile | Skills | Description characters |
|---|---|---|
| `core` | 3 | 2,298 |
| `spine` (default) | 17 | 12,489 |
| `all` | 19 | 14,262 |

Every profile is closed over sibling references, verified by asserting zero references to an absent
skill for all three. The `spine` seed of 13 expands to 17 and says so on stdout. An unrecognised profile
exits 2 before placing anything. Ten tests added; the suite went 63 to 73.

**The honest headline is that the axis cannot deliver as much as the premise assumed, and the reason is
structural.** The sibling-reference graph has one strongly connected component of fourteen skills, and
every member of it reaches seventeen. So the available profile sizes are 3, 17, and 19: there is no
useful middle, and `core` cannot contain `new-task`, which is the skill a work-tracking kit would most
want in a minimal set. `core` is three leaf skills because those are the only ones that are separable,
not because three is the right number.

That was worth building anyway, on two grounds. The default now saves 1,773 description characters
(12,489 against 14,262) by dropping the one genuinely separable pair, and those two happen to be the
kit's two longest descriptions. More usefully, the tool now *measures and prints* the coupling cost that
was previously invisible, which converts an architectural opinion into a number an adopter and the
maintainer can both see.

**The alternative was rejected deliberately.** A profile that filters without closing would give any
subset size, at the cost of shipping skills whose composed siblings are absent. That is not a cosmetic
loss: `doc-sync` composes `doc-revise`'s editing discipline by reference and deliberately does not
restate it, so `doc-sync` without `doc-revise` is `house-review` without its rubric in a new place. The
kit has shipped that defect twice. Closure was the only option that violates no existing contract.

**One pre-existing test changed, which is the part to review most carefully.**
`test_install_places_every_skill_and_the_rules_module` asserted a default run places all nineteen, and
the new default broke it correctly. It now requests `--profile all` explicitly, so it still asserts what
S-001 means rather than being weakened to match the new behavior. Recorded in the conformance matrix as
well, because "a test was changed to pass" is exactly the thing a reader of that matrix should be able
to check.

The follow-up this argues for is at the roadmap altitude, not here: reducing the cross-references
between skills so a genuinely small profile becomes possible. Most of the fourteen edges are courtesy
redirects ("if you want X instead, use Y") rather than composition, and those could be prose naming the
sibling instead of a link, which the portability contract already recommends for anything outside the
shipped tree.
