---
title: install conformance
spec: docs/spec/install.md
audited: 2026-07-27
re_audited:
  - 2026-07-28 (bug-0003)
  - 2026-07-29 (bug-0009)
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
| Scenarios | S-007 reversing removes what was placed beneath the given home | Conformed | `uninstall()` / `mine = [... if _beneath(e["target"], home)]`, the loop calling `_rm`, then `save_manifest(others, dry)` | amended and re-audited by `bug-0003`. The pre-fix code ignored `home` entirely and emptied the whole record. Re-audited by `bug-0009`, which found the scoping check honouring `home` but comparing it as spelled, so an unresolved home matched no entry and reversal removed nothing while exiting zero. "The same home" in S-007 names a directory, not a spelling, so this was a divergence and not a contract gap; the spec is unamended |
| Scenarios | S-012 reversing one home leaves another intact | Conformed | `_beneath()` / `(t.parent.resolve() / t.name).is_relative_to(home.resolve())`, and `uninstall()` retaining `others` in the record | confirmed by execution against two throwaway homes and by a test proven to fail against the pre-fix code. Re-anchored by `bug-0009`, which replaced the bare `Path(target).is_relative_to(home)` this row previously quoted. The target's final component is deliberately left unresolved: in symlink mode every recorded target is a link back to its source in this checkout, so resolving it would place it beneath no home at all |
| Scenarios | S-008 reversing with nothing recorded is not an error | Conformed | `uninstall()` / the `if not manifest["entries"]` early return 0 | prints the nothing-recorded line |
| Scenarios | S-009 an unrecognised tool is rejected before anything is placed | Conformed | `main()` / the `bad` check returning 2 before `install()` is called | the check precedes any placement, so a valid tool in the same list does not save it |
| Scenarios | S-010 the default mode suits the platform | Conformed | `main()` / `default="copy" if os.name == "nt" else "symlink"` | |
| Scenarios | S-011 a refused link reports what to do instead | Conformed | `_link()` / the `except (OSError, NotImplementedError)` raising `SystemExit` with guidance | names Developer Mode and `--mode copy`; confirmed by execution |
| Scenarios | S-013 a profile places a closed subset and reports expansion | Conformed | `resolve_profile()` / the closure loop over `sibling_refs()`, `install()` / the expansion notice, and `main()` / the `args.profile not in PROFILE_SEEDS` check returning 2 | the closure is computed from each body's `../<name>/SKILL.md` references rather than listed, so a skill that gains a reference cannot leave a profile shipping a dangling one. Confirmed by execution: `core` resolves to 3 with no expansion, `spine` to 17 having added 4 (`doc-author`, `doc-revise`, `spec-quality`, `test-quality`), `all` to 19, and every profile has zero references to a skill it does not place. An unrecognised profile exits 2 before placement, matching S-009's shape |
| Scenarios | S-014 the run reports its description budget | Conformed | `profile_budgets()`, `description_of()`, and `install()` / the `Description budget:` print | reports the installed profile's total and every profile's, as counts. Confirmed by execution, re-measured 2026-07-29 with `--dry-run --home ./.tmp/zen-home`: `core=2298`, `spine=12489`, `all=14273`. Dated because the total moves whenever a `description` is edited: `all` was `14262` when first recorded, and the edits in `bug-0007`, `bug-0008`, and `chore-0022` moved it. `description_of()` strips a block-scalar indicator, without which the four skills using one would each inflate the figure by three |
| Proposed Surface | Invocation and its six flags | Conformed | `main()` / the `argparse` definitions | `--tools`, `--profile`, `--mode`, `--home`, `--dry-run`, `--uninstall` |
| Proposed Surface | Placed per tool | Conformed | `install()` / the per-skill `_place` and the rules placement | |
| Proposed Surface | Record | Conformed | `load_manifest()`, `save_manifest()`, `is_managed()` | |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2`, and `install()` / `return 1 if conflicts else 0` | |
| Proposed Surface | Output | Conformed | `install()` / the per-target print, the conflict summary, and the closing count | |

## Coverage proof

- **audited**: S-001 through S-014, and all Proposed Surface elements. Every spec item was
  checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

## Test coverage of spec invariants

Against [`tests/test_install.py`](../../tests/test_install.py), promoted from a characterization suite
to an acceptance suite by this task:

| Scenario | Covering test | Note |
|---|---|---|
| S-001 through S-008 | present | one each, plus a supporting test for how the skill set is identified |
| S-012 | present | added by `bug-0003`. Two tests: one installs to two homes and asserts reversing one leaves the other on disk and in the record, one asserts reversing an uninstalled home removes nothing. Both were run against the pre-fix `uninstall()` and failed |
| S-007 | strengthened | `bug-0009` added two. `test_uninstall_honours_a_home_the_caller_has_not_resolved` installs to a resolved home and reverses it under two spellings `main()` would never produce, a relative one and one carrying `..`; both subtests were run against the pre-fix `_beneath()` and failed. `test_uninstall_in_symlink_mode_removes_the_links_it_placed` covers the POSIX default mode, which had no test at all; it is a guard rather than a regression proof, since it passes on both sides of the fix and exists to fail against the plausible wrong one (resolving a recorded target through its own link). It is skipped where the platform or account cannot create a symlink, probed rather than inferred from `os.name` |
| S-011 | present | added here; asserts the message names both ways out, not merely that it raises |
| S-005 | present | added here; the surprising-but-correct case, which is why it is worth pinning |
| S-009 | present | added by `chore-0017`. Pairs a supported tool with an unsupported one, so it also proves the valid entry does not rescue the invocation, and asserts nothing was placed |
| S-010 | present, one branch | added by `chore-0017`. See the note below |
| S-013 | present | added by `feat-0033`. Five tests: closure holds for every profile (the load-bearing one, since a subset shipping a skill without its composed sibling fails silently), the default places fewer than all, the three profiles are strictly nested, an expanded seed is reported, and a closed seed is not reported as expanded. Plus a rejection test asserting exit 2 and that nothing was placed |
| S-014 | present | added by `feat-0033`. Three tests: the summary carries the installed profile's total and every profile's, a smaller profile costs strictly fewer characters, and a block-scalar description is measured without its indicator |

Every scenario now has a covering test. `chore-0017` gave `main()` the optional `argv` parameter that
`validate-skills.py` (`chore-0003`) and `build-adapters.py` (`feat-0026`) already had, which is what
made the CLI layer reachable at all. Both new tests were confirmed to fail against the pre-fix
`main()`.

**One pre-existing test was changed by `feat-0033`, and it is worth saying which and why.**
`test_install_places_every_skill_and_the_rules_module` asserted that a default run places all nineteen
skills. Once the default profile became `spine`, that assertion failed, correctly: the default no
longer places all of them. The test now requests `--profile all` explicitly, so it still asserts what
S-001 means (every skill in the requested set) rather than being weakened to match the new default.
The suite's other pre-existing scenarios were left asserting over the whole set for the same reason.

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
