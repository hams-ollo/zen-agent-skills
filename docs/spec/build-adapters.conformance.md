---
title: build-adapters conformance
spec: docs/spec/build-adapters.md
audited: 2026-07-27
re_audited: 2026-07-27 (chore-0015)
---

# build-adapters conformance matrix

Spec-vs-implementation audit of [`scripts/build-adapters.py`](../../scripts/build-adapters.py)
against [`build-adapters.md`](build-adapters.md). Evidence is by code location; this audit is
independent of test pass/fail.

Re-audited after `chore-0015` amended the contract to classify the two kinds of emitted shared
material. The "behavior found outside the contract" section this matrix carried is **retired**: the
behavior it described is now S-014.

First audit of this contract, produced immediately after its approval (`feat-0026`). Because the spec
is retrospective, written against an implementation that already existed and was verified, a clean
matrix here is weaker evidence than a clean matrix on a contract written first: the spec was authored
by reading the same code it audits. Its value was therefore concentrated in what it found outside the
scenarios, which was the shared-asset re-run behavior: unstated at the time, and now S-014.

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
| Scenarios | S-014 a re-run refreshes derived assets and preserves adopted ones | Conformed | `emit_shared_assets()` / the rules loop's `or dest.exists(): continue`, contrasted with the skill-asset loop which has no such guard | added by `chore-0015`. Confirmed by execution: after editing both and re-running, the rules file kept its content and the skill template was replaced by the kit's version |
| Scenarios | S-011 generating into the kit is a no-op | Conformed | `emit_shared_assets()` / `dest.resolve() == src.resolve(): continue` in both loops | confirmed by execution: a run against the repo root reports `plus 0 shared asset file(s)` |
| Scenarios | S-012 a preview run writes nothing | Conformed | `_write()` / `if dry: return`, and the `if not dry` guards in `emit_shared_assets()` | confirmed by execution: zero files written into a temp root |
| Scenarios | S-013 an unrecognized target is rejected | Conformed | `main()` / the `bad` check returning 2 | the check precedes any emission, so nothing partial is written; confirmed by execution (exit 2, zero files) |
| Proposed Surface | Invocation and its three flags | Conformed | `main()` / the `argparse` definitions for `--target`, `--out`, `--dry-run` | `--target` defaults to all emitters, `--out` to the working directory |
| Proposed Surface | Emitted per-skill paths | Conformed | `emit_cursor()` and `emit_vscode()` `dest` expressions | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md` |
| Proposed Surface | Emitted shared paths | Conformed | `emit_shared_assets()` / both `dest` expressions | `.agents/rules/<file>`, `.agents/skills/<name>/<path>` |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2` for a bad target, `return 0` otherwise | |
| Proposed Surface | Output | Conformed | `main()` / the per-emission print and the closing summary | |

## Coverage proof

- **audited**: S-001 through S-014, and all five Proposed Surface elements. Every spec item was
  checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

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
| S-014 | present | added by `chore-0015`. Asserts both halves in one test, because the contrast is the requirement. Confirmed to fail against the rejected symmetric alternative, so it distinguishes the chosen contract rather than merely restating current behavior |

Every scenario has a covering test, including the shared-asset re-run behavior that had neither a
scenario nor a test when this matrix was first written.

One note on what the S-014 test is worth. It was confirmed to **fail** when the skill-asset loop is
guarded the way the rules loop is, which is the alternative `chore-0015` considered and rejected. That
makes it an oracle over the decision rather than a restatement of whatever the code happens to do: a
future editor who makes the two loops symmetric will see this test fail and be sent to the contract,
which is the entire point of writing the asymmetry down.
