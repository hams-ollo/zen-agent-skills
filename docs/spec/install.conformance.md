---
title: install conformance
spec: docs/spec/install.md
audited: 2026-07-27
re_audited: 2026-07-27 (chore-0017)
---

# install conformance matrix

Spec-vs-implementation audit of [`scripts/install.py`](../../scripts/install.py) against
[`install.md`](install.md). Evidence is by code location; this audit is independent of test
pass/fail.

Produced by `feat-0029`, completing the kit's contract coverage: every distribution script now has an
approved contract and a matrix.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 each requested tool receives every skill | Conformed | `install()` / the `for tool in tools` loop over `discover_skills()`, with `TOOL_SUBPATHS[tool]` | only requested tools are iterated, so an unrequested one receives nothing |
| Scenarios | S-002 the rules module lands where references resolve | Conformed | `install()` / `rules_target = base.parent / "rules"` | `base` is `<home>/<tool>/skills`, so the parent sibling is exactly what `../../rules/<file>` resolves to from an installed skill; confirmed by execution |
| Scenarios | S-003 a re-run recognises the tool's own targets | Conformed | `_place()` / the `is_managed(target, manifest)` branch returning `updated` or `relinked`, and the symlink branch comparing `points_to == src.resolve()` | symlink mode recognises its own links without the manifest, as the constraint states |
| Scenarios | S-004 an unmanaged target is refused | Conformed | `_place()` / both `return "CONFLICT"` paths, with `install()` counting them and returning 1 while the loop continues | the loop continues past a conflict, so free targets are still placed |
| Scenarios | S-005 a lost record makes previous copies unmanaged | Conformed | `load_manifest()` returning empty entries, feeding `is_managed()` | confirmed by execution: deleting the manifest and re-running yields exit 1 with a conflict per previously-copied target |
| Scenarios | S-006 a preview run writes nothing | Conformed | `_place()` / the `if not dry` guards, and `save_manifest()` / `if dry: return` | neither targets nor the record are created |
| Scenarios | S-007 reversing removes what was placed | Conformed | `uninstall()` / the loop over `manifest["entries"]` calling `_rm`, then `save_manifest([], dry)` | driven by the record, so nothing unrecorded is touched |
| Scenarios | S-008 reversing with nothing recorded is not an error | Conformed | `uninstall()` / the `if not manifest["entries"]` early return 0 | prints the nothing-recorded line |
| Scenarios | S-009 an unrecognised tool is rejected before anything is placed | Conformed | `main()` / the `bad` check returning 2 before `install()` is called | the check precedes any placement, so a valid tool in the same list does not save it |
| Scenarios | S-010 the default mode suits the platform | Conformed | `main()` / `default="copy" if os.name == "nt" else "symlink"` | |
| Scenarios | S-011 a refused link reports what to do instead | Conformed | `_link()` / the `except (OSError, NotImplementedError)` raising `SystemExit` with guidance | names Developer Mode and `--mode copy`; confirmed by execution |
| Proposed Surface | Invocation and its five flags | Conformed | `main()` / the `argparse` definitions | `--tools`, `--mode`, `--home`, `--dry-run`, `--uninstall` |
| Proposed Surface | Placed per tool | Conformed | `install()` / the per-skill `_place` and the rules placement | |
| Proposed Surface | Record | Conformed | `load_manifest()`, `save_manifest()`, `is_managed()` | |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2`, and `install()` / `return 1 if conflicts else 0` | |
| Proposed Surface | Output | Conformed | `install()` / the per-target print, the conflict summary, and the closing count | |

## Coverage proof

- **audited**: S-001 through S-011, and all five Proposed Surface elements. Every spec item was
  checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

## Test coverage of spec invariants

Against [`tests/test_install.py`](../../tests/test_install.py), promoted from a characterization suite
to an acceptance suite by this task:

| Scenario | Covering test | Note |
|---|---|---|
| S-001 through S-008 | present | one each, plus a supporting test for how the skill set is identified |
| S-011 | present | added here; asserts the message names both ways out, not merely that it raises |
| S-005 | present | added here; the surprising-but-correct case, which is why it is worth pinning |
| S-009 | present | added by `chore-0017`. Pairs a supported tool with an unsupported one, so it also proves the valid entry does not rescue the invocation, and asserts nothing was placed |
| S-010 | present, one branch | added by `chore-0017`. See the note below |

Every scenario now has a covering test. `chore-0017` gave `main()` the optional `argv` parameter that
`validate-skills.py` (`chore-0003`) and `build-adapters.py` (`feat-0026`) already had, which is what
made the CLI layer reachable at all. Both new tests were confirmed to fail against the pre-fix
`main()`.

**S-010 is covered on one branch only, and the reason is worth recording.** The rule reads `os.name`,
and faking that to exercise the other platform breaks `pathlib`, which selects `PosixPath` or
`WindowsPath` from the same attribute and raises on instantiation. The test therefore derives its
expectation from the running platform and asserts the wiring, so it fails if the default changes or
the flag stops feeding it, but the opposite platform's branch is exercised only by running the suite
there. A test that hardcoded `"copy"` would have passed everywhere and meant nothing off Windows,
which is the outcome this avoids. Closing the remaining half would mean extracting the default into
its own expression, a behaviour-preserving refactor deliberately left out of `chore-0017`'s scope.

## Observations

**S-001 presupposes a definition it does not state.** It says every skill is placed, without saying
what makes a directory a skill. The implementation answers "one holding a `SKILL.md`", which matches
`AGENTS.md` and is what `validate-skills.md` builds on, so nothing diverges. But a reader of this
contract alone cannot derive the rule, and the supporting test asserts it. Left as an observation
rather than a scenario, because the definition genuinely belongs to `AGENTS.md` and duplicating it
here would create a second place for it to drift.

**S-005 is the scenario most worth having written down.** That deleting the record turns the tool's
own past work into conflicts is surprising, looks like a bug, and is correct: a copied directory
carries nothing distinguishing it from a user's own, so the alternative is overwriting something the
tool cannot prove it created. The module docstring warned about it, the code implements it, and until
now no contract said it was intended. That is exactly the class of behavior a future editor would
"fix".

**Every audited item conforms, and the same caveat applies as to `build-adapters`.** This spec was
written by reading the implementation it audits, so a clean matrix largely confirms that two
documents agree. What makes this one stronger than a pure paper exercise is that the behavior was
pinned by tests **before** the contract was written, so the spec had to describe something already
fixed rather than something it could quietly reshape.
