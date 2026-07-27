---
title: build-adapters conformance
spec: docs/spec/build-adapters.md
audited: 2026-07-27
---

# build-adapters conformance matrix

Spec-vs-implementation audit of [`scripts/build-adapters.py`](../../scripts/build-adapters.py)
against [`build-adapters.md`](build-adapters.md). Evidence is by code location; this audit is
independent of test pass/fail.

First audit of this contract, produced immediately after its approval (`feat-0026`). Because the spec
is retrospective, written against an implementation that already existed and was verified, a clean
matrix here is weaker evidence than a clean matrix on a contract written first: the spec was authored
by reading the same code it audits. The audit's value is therefore concentrated in what it found
outside the scenarios, recorded below.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 one adapter per skill per requested target | Conformed | `main()` / the `for d in skills` loop over `targets`, with the summary print and `return 0` | only requested targets are dispatched, via `EMITTERS[t]` |
| Scenarios | S-002 harness frontmatter and do-not-edit banner | Conformed | `emit_cursor()` and `emit_vscode()` content strings, with `BANNER` | cursor gets `description` plus `alwaysApply: false`, vscode gets `mode: agent` plus `description`; both prepend the banner naming the source `SKILL.md` |
| Scenarios | S-003 sibling link points at the adapter beside it | Conformed | `rewrite_links()` / `SIBLING_RE` branch | emits `<sibling><ext>`, a same-directory reference |
| Scenarios | S-004 anchor survives the rewrite | Conformed | `rewrite_links()` / `SIBLING_RE` branch, `sibling.group(2)` | the captured anchor is reattached |
| Scenarios | S-005 link title survives the rewrite | Conformed | `rewrite_links()` / `LINK_RE` group 2, reattached by the inner `out()` | the title is carried through every rewrite path, not just the sibling one |
| Scenarios | S-006 rules-module link points at the shared location | Conformed | `rewrite_links()` / `RULES_RE` branch, with the `SHARED` prefix | |
| Scenarios | S-007 skill-local asset points at the shared location | Conformed | `rewrite_links()` / the final return, `SHARED/skills/<name>/<target>` | reached only after the external, anchor, sibling, rules and escaping branches |
| Scenarios | S-008 external and same-page links unchanged | Conformed | `rewrite_links()` / the `target.startswith("#")` and `EXTERNAL_PREFIXES` guard returning `m.group(0)` | returns the original match object's text, so the link is byte-for-byte preserved |
| Scenarios | S-009 the material the links point at is emitted | Conformed | `emit_shared_assets()` / both copy loops, called per skill from `main()` | rules module and each skill's non-`SKILL.md` files |
| Scenarios | S-010 an existing rules file is never overwritten | Conformed | `emit_shared_assets()` / `or dest.exists(): continue` in the rules loop | confirmed by execution: an edited rules file survives a re-run unchanged |
| Scenarios | S-011 generating into the kit is a no-op | Conformed | `emit_shared_assets()` / `dest.resolve() == src.resolve(): continue` in both loops | confirmed by execution: a run against the repo root reports `plus 0 shared asset file(s)` |
| Scenarios | S-012 a preview run writes nothing | Conformed | `_write()` / `if dry: return`, and the `if not dry` guards in `emit_shared_assets()` | confirmed by execution: zero files written into a temp root |
| Scenarios | S-013 an unrecognized target is rejected | Conformed | `main()` / the `bad` check returning 2 | the check precedes any emission, so nothing partial is written; confirmed by execution (exit 2, zero files) |
| Proposed Surface | Invocation and its three flags | Conformed | `main()` / the `argparse` definitions for `--target`, `--out`, `--dry-run` | `--target` defaults to all emitters, `--out` to the working directory |
| Proposed Surface | Emitted per-skill paths | Conformed | `emit_cursor()` and `emit_vscode()` `dest` expressions | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md` |
| Proposed Surface | Emitted shared paths | Conformed | `emit_shared_assets()` / both `dest` expressions | `.agents/rules/<file>`, `.agents/skills/<name>/<path>` |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2` for a bad target, `return 0` otherwise | |
| Proposed Surface | Output | Conformed | `main()` / the per-emission print and the closing summary | |

## Coverage proof

- **audited**: S-001 through S-013, and all five Proposed Surface elements. Every spec item was
  checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

## Behavior found outside the contract

Not a matrix row, because there is no spec item to diverge from. Recorded because implementation
behavior drifting past its contract is the exact pattern that went unnoticed twice in
[`validate-skills.md`](validate-skills.md), and catching the third instance during the audit rather
than two days later is the point of running one.

**The two shared-asset loops guard differently, and only one of them is specified.** The rules loop
skips a destination that already exists (`or dest.exists()`), which is S-010. The skill-asset loop
has no such guard, so a supporting file the target project has edited is silently overwritten on the
next run. Confirmed by execution: after editing both and re-running, the rules file kept its content
and the skill template was replaced.

This is defensible and probably intended, since a skill's templates are derived from the kit and
should track it, while the rules module is swappable by design and belongs to the adopter. But it is
an unstated contract decision sitting one line away from a stated one, and the asymmetry is invisible
to a reader of either the spec or the tests. Recommendation: state it, either as a scenario asserting
that skill assets are refreshed while rules files are preserved, or as a Constraint explaining why
the two are treated differently. Deciding that is a human call and is not made here.

## Test coverage of spec invariants

Flagged per `spec-conformance`'s non-goal: it does not write tests, but does say where an invariant
lacks one. Against [`tests/test_build_adapters.py`](../../tests/test_build_adapters.py):

| Scenario | Covering test | Note |
|---|---|---|
| S-001 | present | asserts the requested target's count, the other target's absence, exit zero, and the summary |
| S-002 | present | both harnesses' frontmatter keys and the banner |
| S-003 through S-008 | present | one unit test each on `rewrite_links` |
| S-003 through S-009 | present | plus one filesystem test resolving all 194 emitted links on disk, which is the layer the original defect lived at |
| S-010 | present | the contract rule with no other enforcement, so this test is the only thing holding it |
| S-011 | present | asserted through a preview run, so the test cannot write into the repository even if the no-op regressed |
| S-012, S-013 | present | each asserts both the exit code and that no file was written |

Every scenario has a covering test. The unspecified asymmetry above has none, which follows from it
having no scenario.
