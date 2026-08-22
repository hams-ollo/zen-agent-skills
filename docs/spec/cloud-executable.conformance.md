---
title: cloud-executable conformance
spec: docs/spec/cloud-executable.md
audited: 2026-08-19
re_audited: 2026-08-20
---

# cloud-executable conformance matrix

Spec-vs-implementation audit of [`run-checks.py`](../../scripts/run-checks.py),
[`checks.yml`](../../.github/workflows/checks.yml), the acceptance-command section of
[`AGENTS.md`](../../AGENTS.md), and
[`skill-reachability-reminder.py`](../../.agents/hooks/skill-reachability-reminder.py) with its
committed registration, against [`cloud-executable.md`](cloud-executable.md). Evidence is by code
location or by a test that asserts the requirement; this audit is independent of test pass/fail.
A location is a symbol, a section heading, or a quoted phrase, never a line number, so an edit above
a citation cannot silently retarget it (`bug-0037`).

Written 2026-08-19 by `chore-0034`, which exists because this was the one approved spec of eleven
with no matrix while two tasks had already closed against it: `feat-0045` (S-001 to S-007) and
`feat-0046` (S-008 to S-016), both `status: done`, neither declaring a `conformance:` key. The matrix
records what is true now. It is not a reprimand and it does not reopen either task.

## The one thing to read before the rows

**Three of the nineteen scenarios are Not-built, and that is the honest state of this contract, not
a gap this audit could close.** S-017 to S-019 describe the Phase 4 cloud proof run. That run was
attempted on 2026-08-07 and did not happen; the attempt is recorded with a `blocked` verdict in
[`cloud-executable.verification.md`](cloud-executable.verification.md), and nothing since has
superseded it. Re-confirmed here against the repository's own history on 2026-08-19: no later
verification record exists, and `bug-0021`, closed 2026-08-08, states in its own body that the proof
run is still owed.

This spec is also unusual in being **forward**, written before any of it existed, which its own
header says. Every other retrospective matrix here audits code that predates its contract. This one
audits sixteen scenarios built to a contract, and three that the contract is still waiting for.

## Approval state

`status: approved`, granted 2026-08-07, with **no pending amendment**. This matters because the
convention in [`README.md`](README.md) requires a matrix to repeat any pending-re-approval note its
rows depend on, and [`build-adapters.conformance.md`](build-adapters.conformance.md) and
[`install.conformance.md`](install.conformance.md) both carry one. This one does not, and the reason
is worth recording: `bug-0021` fixed the reachability defect behind S-008 and S-010 by moving the
**code** to the contract rather than the contract to the code. The words "kit skill" were in the
approved text from the start, verified here against the approving commit. So every row below is
audited against text a human agreed to.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 one command runs every gate and answers with one exit code | Conformed | `run-checks.py` / `gates()`, the seven; `run_all()` writes one line per gate with its status; its closing `return 1 if counts["failed"] else 0`, so 0 only when neither counter is set | Tests `test_the_seven_gates_are_present_ordered_and_complete`, `test_every_gate_runs_and_all_passing_exits_zero`. The gate list is pinned in the test as a deliberate second source of truth, since S-005 removes the seven CI steps it could otherwise have been compared against |
| Scenarios | S-002 a failing gate is named, and the gates after it still run | Conformed | `run-checks.py` / `run_all()`'s `for gate in the_gates` loop reports each gate and continues rather than breaking; its `for name, status, output in notes` loop dumps every collected failure; the closing `return 1 if counts["failed"] else 0` | Tests `test_a_failing_gate_does_not_stop_the_ones_after_it`, `test_a_real_failure_exits_one_and_later_gates_still_run`. The second runs real subprocesses, so the non-fail-fast property is proved rather than stubbed |
| Scenarios | S-003 a gate that could not run outranks a gate that failed | Conformed | `run-checks.py` / `_run()`'s missing-script check, `if script is not None and not (REPO_ROOT / script).exists()`, ahead of the call; its `except OSError as exc` branch for an interpreter that cannot start; `run_all()`'s `if counts["unrunnable"]: return 2`, whatever else is set | Tests `test_a_gate_that_cannot_run_outranks_one_that_failed`, `test_an_unrunnable_gate_is_not_reported_as_failed`, `test_a_missing_script_is_unrunnable_not_failed`, `test_unrunnable_outranks_failed_for_real`. The missing-script check is load-bearing rather than belt-and-braces: `subprocess` does not raise for a missing script, so without it the whole could-not-run branch would be dead in the case it exists for |
| Scenarios | S-004 the run leaves no installation behind | Conformed | `run-checks.py` / the `THROWAWAY_HOME` constant; `gates()`'s `Gate("install cycle", ...)`, whose `cleanup` uninstall is scoped by `--home`; `run_gate()`'s `if gate.cleanup is not None` block, which runs whether the gate passed or failed | Tests `test_the_install_cycle_reverses_what_it_placed`, `test_cleanup_runs_even_when_the_gate_failed`, `test_only_the_install_cycle_cleans_up_after_itself`. Confirmed in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md) by a before-and-after diff over a full copy of the tree. The one write outside the throwaway home is `scripts/.install-manifest.json`, which is gitignored, is the tool's own record, and is not an installation |
| Scenarios | S-005 CI calls the command instead of restating the gates | Conformed | `checks.yml` / the one `Run every acceptance gate` step, `run: python scripts/run-checks.py`, and no other gate command anywhere in the file | Tests `test_ci_invokes_the_acceptance_command`, `test_ci_does_not_separately_restate_any_gate`, `test_the_marker_set_actually_covers_every_gate`. The restatement guard was **vacuous for five of the seven gates** when first written, matching on each command's last token, and was rebuilt after independent verification defeated it by reinserting four genuine restatements. The third test exists to keep the guard from going vacuous again |
| Scenarios | S-006 the bound of the answer is stated in both places it will be read | Conformed | `run-checks.py` / `run_all()`'s closing summary names `platform.system()` and `platform.python_version()` and the six-cell bound; `AGENTS.md` / "The acceptance command" states it in the spec's own words, "**Passing it is necessary but not sufficient**" | Tests `test_the_summary_names_the_platform_and_interpreter`, `test_the_summary_states_that_passing_is_not_sufficient`, `test_agents_md_states_the_bound_in_those_words`. Both halves are guarded, including the one that lives in a prose document rather than in code |
| Scenarios | S-007 passing the command does not make a Windows-only failure pass | Conformed | `checks.yml` / `strategy.matrix`, three operating systems by two Python versions with `fail-fast: false`; the Windows cells run the same `Run every acceptance gate` step; `run-checks.py` / `run_all()`'s closing summary claims nothing wider | Structural, and deliberately so: the readiness report records that no in-repo test layer is possible, since a local test asserting that the matrix catches what one local run cannot would be asserting its own premise. The positive observation is the all-six-cells run recorded in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md). **The scenario's antecedent, a change that fails only on Windows, has never actually occurred here**, so what is proved is that the mechanism is wired, not that it has caught one |
| Scenarios | S-008 a session with no reachable skills is told at the start | Conformed | `skill-reachability-reminder.py` / `evaluate()` returns the one `hookSpecificOutput.additionalContext` object; the `REPORT` constant names `python scripts/install.py`; the reporting path lies past `if reachable(project_root, home): return None`, so it is reached only when `reachable()` is false; nothing in the module opens a file for writing | Tests `test_no_skills_anywhere_is_reported`, the seven `ForeignLibraryTests`, `test_the_report_says_whose_skills_are_missing`. **Corrected by `bug-0021`, which is why this task depended on it**: `_has_skill()` counted any directory holding a `SKILL.md`, so a stock cloud container's own populated `~/.claude/skills` silenced the hook in the exact state this scenario requires it to speak. See the real-environment gap in the observations below |
| Scenarios | S-009 skills committed at project scope count as reachable | Conformed | `skill-reachability-reminder.py` / `PROJECT_SKILL_SUBPATHS`, `.claude/skills` and only that; `reachable()`'s `for sub in PROJECT_SKILL_SUBPATHS` loop | Tests `test_project_scope_skills_count_as_reachable`, `test_kit_skills_at_project_scope_only_are_silence`, `test_a_real_project_scope_install_here_is_reachable`, `test_the_opencode_path_does_NOT_count_at_project_scope`. The singular is load-bearing: an earlier version also checked `.agents/skills` at project scope, which is this kit's own committed source tree, so a fresh clone with nothing installed counted twenty skills and stayed silent |
| Scenarios | S-010 a session with reachable skills receives nothing | Conformed | `skill-reachability-reminder.py` / `evaluate()`'s `if reachable(project_root, home): return None`, and `main()` writes only when `evaluate()` returns non-`None` (`if out is not None`) | Tests `test_user_scope_skills_count_as_reachable`, `test_the_opencode_user_scope_counts_too`, `test_one_kit_skill_beside_a_foreign_library_is_silence`, `test_a_partial_install_is_reachable`. Independent verification confirmed thirteen hook mutations caught, including always-report and never-report, so neither direction passes vacuously |
| Scenarios | S-011 reachability is not currency | Conformed | `skill-reachability-reminder.py` / `_has_kit_skill()` tests directory name and `SKILL.md` presence only, never content; the module docstring's "What it does NOT answer" section states the limit; the `REPORT` constant repeats it and names `install.py --check` | Test `test_a_stale_install_is_still_reachable_and_still_silent`. The clause the scenario asks for, that silence means reachable and never current, is present in both the module and the injected message, so a reader of either finds it |
| Scenarios | S-012 a present install with no record is reachable, and separately unrecorded | Conformed | Hook half: `skill-reachability-reminder.py` / `reachable()` consults the filesystem and never a manifest. `--check` half: `install.py` / `check()`'s `if not scoped` branch prints "nothing can be checked" and returns 2 | Tests `test_skills_present_with_no_manifest_are_reachable` and `test_checking_a_home_with_nothing_recorded_does_not_report_it_as_current`. Both halves guarded, in two suites, which is what the scenario's "both correct and not in conflict" needs |
| Scenarios | S-013 only a started session fires the bootstrap | Conformed | `skill-reachability-reminder.py` / `FIRING_SOURCES = {"startup"}`; `evaluate()`'s `if payload.get("source") not in FIRING_SOURCES` check, ahead of any filesystem work | Tests `test_startup_fires`, `test_the_continuing_sources_do_not_fire`, `test_another_event_does_not_fire`, `test_only_the_listed_sources_fire`. The last is a structural guard added after verification defeated the original by inverting the allowlist into a denylist of the four continuing sources |
| Scenarios | S-014 the bootstrap writes nothing, in every case | Conformed | `skill-reachability-reminder.py` / no write call exists in the module; the bodies of `_has_kit_skill()` and `main()` are read-only, with `try`/`except` around them | Four tests: `test_the_reporting_path_writes_nothing`, `test_the_silent_path_writes_nothing`, `test_main_writes_nothing_including_into_the_home_it_resolves`, `test_the_source_performs_no_write_of_any_kind`. The fourth parses the source with `ast` rather than substring-matching it, after the first snapshot version was defeated by a write into `tempfile.gettempdir()` and by a write from `main()` rather than `evaluate()` |
| Scenarios | S-015 an unreadable payload leaves the session unchanged | Conformed | `skill-reachability-reminder.py` / `main()`'s first `try`, where a failed `json.load` returns 0 silently; its second `try`, where any exception inside `evaluate()` returns 0 silently; `evaluate()`'s `if not isinstance(payload, dict): return None` | Tests `test_malformed_json_is_silent_and_exits_zero`, `test_empty_stdin_is_silent_and_exits_zero`, `test_a_non_object_payload_is_silent`, `test_a_payload_missing_every_field_is_silent`, `test_main_emits_exactly_one_json_object_when_it_fires` |
| Scenarios | S-016 the bootstrap does not vary by where it runs | Conformed | Nothing in the module imports `os`, `platform`, `socket`, or reads an environment variable; the only inputs are the payload and two filesystem paths | Tests `test_output_is_byte_identical_across_differing_environments` and `test_the_source_reads_no_environment`, the second an `ast` walk over imports, calls, and attribute chains. It is parsed rather than substring-matched because the first widened version fired on the word "subprocess" inside a docstring explaining why the hook does not spawn one, and a guard that fires on its own documentation gets loosened until it catches nothing |
| Scenarios | S-017 the proof run lands as a draft pull request carrying its evidence | **Conformed** | The 2026-08-20 run of `bug-0020` (`chore-0051` repointed the Given to it): branch `claude/bug-0020-unknown-remedy-lcqb52`, pull request #41 opened **draft** against `developer` and not merged, body carrying all nine fields including `run-checks.py`'s verbatim output and exit 0. Independently verified by a session that did not write it, per `A7`: diff confined to the task's three `touched_files` (109+/3-), zero existing tests edited, `docs/spec/install.md` untouched, acceptance re-run. Superseded evidence: [`cloud-executable.verification.md`](cloud-executable.verification.md) records the 2026-08-07 attempt with verdict `blocked`, two independent blockers, and `evidence_produced: none` | The run has not happened as of 2026-08-19. What exists is the surrounding apparatus, not the scenario: rule **A8** in [`autonomy.md`](../../.agents/rules/autonomy.md) states the ceiling, [`cloud-executable.runbook.md`](cloud-executable.runbook.md) tells a person how to start it, and the verification record carries the exact dispatch command. See the observations below on why `bug-0018` having landed on a `claude/` branch is not evidence for this row, and on the 2026-08-20 repointing to `bug-0020` |
| Scenarios | S-018 the proof's evidence is a test that failed before the change | **Conformed** | `test_an_unrecorded_rules_entry_names_replace_adopted_rather_than_re_install` and `test_the_run_summary_names_both_remedies_when_the_unknown_entries_are_a_mix` fail against `developer`'s `install.py` and pass against the fixed one. **Reproduced independently rather than read from the report**: restoring `install.py` to `developer`'s copy with the new tests in place yields the same two failures with the same assertion text, and the third test is green in both directions by design as the scope guard. Superseded evidence: Same record, `evidence_owed: S-017, S-018, S-019` | This is the row that carries the actual proof, per prediction 6 in the verification record: the other predictions can be satisfied by an agent that followed instructions, and only a test failing before the change and passing after demonstrates work a plausible-sounding report could not have faked. Nothing has produced it |
| Scenarios | S-019 a proof run whose gates fail still reports | **Not-built** | None. Same record | Unreachable until S-017 runs at all, since its Given is the same dispatched session. Recorded separately rather than folded into S-017, because it specifies the failure path and a successful run would leave it still unproved |
| Proposed Surface | Acceptance command `python scripts/run-checks.py`, no flags | Conformed | `run-checks.py` / `main()` takes `argv` only in order to refuse it, returning 2 with a message | Test `test_any_argument_is_refused`. Exit 2 rather than 1 for a refused argument is consistent with the scenario's own precedence: the command did not run the gates, so it did not answer |
| Proposed Surface | Gate set, the seven from `checks.yml` | Conformed | `run-checks.py` / the list `gates()` returns: lint skills, test suite, backlog, adapters dry run, install dry run, install cycle, doc links | Test `test_the_seven_gates_are_present_ordered_and_complete`, plus `test_every_real_gate_names_a_script_that_exists`. The install cycle runs `install.py` twice, which is the idempotence proof; a test pins that after verification found deleting the second run went uncaught |
| Proposed Surface | Throwaway home `./.tmp/zen-home` | Conformed | `run-checks.py` / `THROWAWAY_HOME`, used through `gates()`'s `install_home` for all three install gates | The literal the spec names, matching what the CI steps already used, and gitignored via `.tmp/` |
| Proposed Surface | Exit code 0 / 1 / 2, with 2 outranking 1 | Conformed | `run-checks.py` / `run_all()`'s closing branches: the unrunnable counter is tested first and returns 2 unconditionally | Proved end to end against real gates in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md): three failed plus one unrunnable returned 2, and the same run with only failures returned 1 |
| Proposed Surface | Output: one line per gate, the failing gate's output, then a summary with counts and platform | Conformed | `run-checks.py` / `run_all()`: the per-gate line, then the `----- {name}: {status} -----` output block, then the counts followed by the platform and Python version | Mirrors `install.py`'s `check()` report shape rather than inventing a second format, as `feat-0045` required. A passing gate whose cleanup failed still gets its output shown (`run_all()`'s `if status != "ok" or not cleanup_ok` guard), so leftover files are never announced in one word and explained nowhere. **Still Conformed after `bug-0045`, and the contract now owes an amendment**: `run_all()` also writes one indented coverage line beneath every gate, which this row neither requires nor forbids. See "An amendment this contract owes" below |
| Proposed Surface | CI wiring: one step invoking the command | Conformed | `checks.yml` / a single `Run every acceptance gate` step | The seven steps it replaced are gone rather than commented out, which is what makes the S-005 restatement test meaningful |
| Proposed Surface | `AGENTS.md` names the command and states the bound | Conformed | `AGENTS.md` / the section "The acceptance command": the command in a fenced block, the exit codes in the `run-checks.py` paragraph below it, and the bound in the spec's exact words, "**Passing it is necessary but not sufficient**" | |
| Proposed Surface | Bootstrap hook: reminder shape, `SessionStart`, `startup` matcher | Conformed | `skill-reachability-reminder.py` / the module docstring declares the shape, and its "Contract" section states stdin, stdout, and exit; `FIRING_SOURCES` the matcher value; the injectable `main(stdin, stdout)`; listed in the module table in `.agents/hooks/README.md` | Satisfies the hooks module contract the spec's Constraints section imports: exit 0 always, at most one JSON object, no import from this repository, injectable entry point |
| Proposed Surface | Bootstrap registration committed in `.claude/settings.json` | Conformed | `.claude/settings.json`, `hooks.SessionStart` with `matcher: "startup"` and command `python3 .agents/hooks/skill-reachability-reminder.py` | Six tests in `CommittedRegistrationTests`, including one asserting the interpreter and one asserting the `AGENTS.md` bound of exactly one hook. **The interpreter is the finding this row exists to carry**: the first draft said `python`, disagreeing with every other interpreter wiring in the kit, and independent verification caught it before any cloud run. What this row does not carry is a counterfactual about what `python` would have done there. The observation "One claim the same run falsified" below reports both interpreters present in the 2026-08-21 cloud container, so on that platform, on that date, the first draft would have launched. `python3` stands as the portable default for the environments nobody here has measured, which is the weaker claim and the true one |
| Proposed Surface | Bootstrap output: nothing when reachable, else one context object | Conformed | `skill-reachability-reminder.py` / `evaluate()`'s two returns, `None` when reachable and the one context object otherwise; `main()` writes only a non-`None` result | Test `test_main_emits_exactly_one_json_object_when_it_fires`, plus the four silent-path tests. Both halves of the row are asserted, which matters because a test covering only the fire path would pass against a hook that speaks on every start |
| Proposed Surface | Reachable: one kit skill at the project-scope directory, or at any user-scope directory `install.py` targets | Conformed | `skill-reachability-reminder.py` / `PROJECT_SKILL_SUBPATHS` project scope, `USER_SKILL_SUBPATHS` user scope, `KIT_SKILL_NAMES`, `_has_kit_skill()` the name-and-`SKILL.md` test, `reachable()` the two-scope check | **Diverged until `bug-0021` landed 2026-08-08**, on both halves of the sentence: any `SKILL.md` counted rather than a kit skill's, and project scope was checked against `.agents/skills` as well. Both are now the sentence the spec wrote. `test_the_recognised_names_are_exactly_the_skills_this_kit_ships` asserts the name list equals what the kit ships in both directions, which is the only place a standalone hook forbidden from importing this repository can have the staleness objection answered |
| Proposed Surface | Unattended branch and pull request: `claude/` prefix, draft, nine-field report | **Conformed** | Pull request #41 and #43, both on `claude/` branches, both opened draft, neither merged by the session. #41's body carries the nine fields. Superseded: The governing rule exists in `autonomy.md` under "Landing: what you may do with the result" (rule **A8**) and the nine-field contract exists in `fix-batch`'s body | The rule is written; the artifact this row describes has never been produced by the run that would prove it. Classified with S-017 rather than separately, since it is that scenario's surface |

## Coverage proof

- **audited**: all 19 scenarios, S-001 through S-019, and all 12 Proposed Surface rows. 19 + 12 = **31
  items**, which is every auditable item the spec contains. Nothing was sampled and nothing was
  skipped.
- **unreconciled**: **1 of 31**, as re-audited 2026-08-20. S-019 alone, and it is **Not-built**;
  none is Diverged. It was 4 of 31 until the proof run of 2026-08-20 moved S-017, S-018, and the
  `Unattended branch and pull request` surface row to Conformed. The arithmetic: 4 minus 3 is 1.
- **conformed**: 30 of 31, being S-001 through S-018 and all 12 surface rows. 30 + 1 = 31.
- **disposition of the one unreconciled item**: accepted-with-reason. S-019's Given is a session whose
  acceptance command exits non-zero, and the 2026-08-20 run's exited 0 with all seven gates passing,
  so the failure path was never entered. It cannot be closed by wanting it: it needs a proof run that
  genuinely fails, which is not something to manufacture. **Not to-fix by an agent**, because the run
  has to be started by a person; [`cloud-executable.runbook.md`](cloud-executable.runbook.md) is the
  instruction sheet, now gated on the base per `bug-0043`.
- **audited but not closed by this run**: S-008 stays Conformed on tests and **unobserved in a real
  cloud session**, which is the same state it held before. The 2026-08-20 run reported no startup
  message, and that is not evidence against the hook, because the session was staged on a commit
  without the fix. See the observation below.

The audited range stops at S-019 and claims nothing wider. The spec has 19 scenarios and this matrix
has 19 scenario rows.

## An amendment this contract owes

**Unreconciled, and against the contract rather than against the code.** Recorded by `bug-0045` on
2026-08-22, which changed `run-checks.py` to write one indented coverage line beneath every gate's
status line, passing gates included. Before that change the aggregator captured each gate's output
and printed it only `if status != "ok"`, so seven gates passing over this repository and six gates
passing over a copy with the skills, the tests, and the task files removed produced byte-identical
reports.

**This is a debt of the spec, not a divergence in the implementation, and the arithmetic above is
deliberately unchanged.** Nothing the contract requires is missing: S-001 still gets every gate named
with its own outcome, S-002 still gets a failing gate named with its output, and the `Output` surface
row still gets its per-gate line, its failure block, and its summary. What is missing is the other
direction. The contract does not say what a **passing** gate carries, so the silence the defect
depended on was contract-compliant, and the coverage line the fix adds is contract-silent too. Both
states satisfy the same three items, which is the property worth amending away.

What the amendment owes, for whoever files it:

- **S-001** says each gate "is named in the output with its own outcome" and stops there. It is the
  natural home for a clause requiring a passing gate to carry its own account of what it covered.
- The **`Output`** surface row describes three elements and should describe four.
- The property to state is the falsifiable one `bug-0045` asserts in
  `tests/test_run_checks.py`, `CoverageReportTests`: a run over an empty scope must not be
  byte-identical to a run over a full one. Stating a required wording instead would pin the aggregator
  to whatever the gates print today.

Not filed here, deliberately. `docs/spec/cloud-executable.md` and
[`README.md`](README.md) are both untouched by `bug-0045`, whose `touched_files` are
`scripts/run-checks.py` and `tests/test_run_checks.py`, and two agents adding re-approval rows to one
shared file collided on 2026-08-19. The amendment is a separate task, in the shape of the one
`chore-0047` took.

**This section is a targeted note, not a re-audit.** Only the `Output` row and S-001 were re-read for
it. The frontmatter's `audited` and `re_audited` dates are left alone, and the coverage proof's 1 of
31 still refers to S-019 alone, which nothing here changes.

## Observations

**"Conformed" is stronger in this matrix than in most here, and it is worth saying why rather than
letting the word carry equal weight everywhere.** The limit stated at the foot of
[`README.md`](README.md) is that most of what this kit ships is prose, so a conformance row usually
cites a clause and establishes that a skill *instructs* the behavior, not that anything *enforces*
it. This contract is the exception: 15 of the 16 built scenarios are backed by executing tests
against executing code, and the sixteenth, S-007, is a property of a workflow file that no in-repo
test can honestly assert. The single prose citation in the whole matrix is the `AGENTS.md` bound, and even
that has a test reading the file.

**The guards were audited by an adversary before this matrix existed, and that changes what the rows
mean.** [The S-001 to S-016 verification](cloud-executable.s001-s016.verification.md) returned
`fail`, not on behavior but on test strength: the S-005 restatement guard was vacuous for five of
seven gates, the gate-set pin did not catch deleting the install cycle's idempotence run, and four
further guards fell to mutation. Every one was rebuilt and re-confirmed by re-running the mutation
that had defeated it. So the Conformed rows above rest on guards that have been attacked, which is a
different claim from guards that have merely passed.

**The real-environment gap on S-008, stated precisely.** S-008 is the scenario this whole contract
was written for, and it has still never been observed firing correctly on a real machine. The one
live observation, a cloud session on 2026-08-08, found the hook **silent** against a container's own
populated `~/.claude/skills`, which is the defect `bug-0021` then fixed. Post-fix, the evidence is
unit tests plus a run against a synthetic empty home. The Phase 4 run is what would close this, and
prediction 1 in the verification record is exactly that observation. Until then, S-008 is Conformed
against the contract and unobserved in the wild, and those are not the same statement.

**Closed 2026-08-21. The gap above is no longer a gap.** An observation-only cloud session on
`9bc32ac`, whose base gate printed `BASE_OK`, reported the message present in context at session
start before any tool call, and the hook run by hand in the same session returned the identical text.
`yes` plus `reports` is the top row of the runbook's reading table: **`S-008` confirmed live**, in a
real cloud container, fourteen days after the contract was written for exactly this. Prediction 1 in
the verification record is met. Independently checked here rather than read from the report: the same
hook run against a cloud-like home with none of the kit's skills produces output **byte-identical** to
what the session pasted, and the base claim resolves (`9bc32ac` was `developer`'s tip and carries
`7703632`). What this closes is the whole committed-registration exception in `AGENTS.md`: a
project-scope `.claude/settings.json` **does** reach a cloud session, the hook launches there, and it
speaks when it should. That was the argument for bending the opt-in rule, and it was reasoning until
this run.

**One claim the same run falsified, recorded because it was load-bearing (`chore-0052`).**
`.claude/settings.json` justifies its `python3` interpreter by asserting that the first draft's
`python` "would have failed to launch in the exact environment the exception was granted for".
Observation 3 of the 2026-08-21 run reports `/usr/local/bin/python3` **and** `/usr/local/bin/python`
both present on that platform, so `python` would have launched. The choice of `python3` stands, since
it is the safer default across environments and the `feat-0038` Store-alias hazard on Windows is real;
the counterfactual defending it does not. The comment closes "Found by independent verification before
any cloud run, not after", which is the tell: it was verified against reasoning rather than against
the environment, and this is the first evidence ever gathered on it.

**Why `bug-0018` landing on a `claude/` branch is not evidence for S-017.** It is the nearest thing
in the repository's history to the proof run, and it is not one. `bug-0018` is the task S-017 names,
it was implemented with agent authorship on `claude/bug-0018-preserve-adopter-edited-lens`, and it
merged as pull request #23 on 2026-08-08. But S-017's Given is that task **dispatched to a cloud
session**, and the verification record dated the day before shows the cloud dispatch was refused. The
work was then done another way. Nothing in the repository attests that the pull request was opened in
draft or that its body carried the nine-field report, and reaching outside the repository to check
would not change the classification, because S-018's proof, a test shown failing before and passing
after, is the load-bearing half and no record of it exists. This paragraph is here so the next
auditor does not re-derive the question and reach a different answer from the branch name alone.

**Extended 2026-08-20 (`chore-0051`): the paragraph above was correct and incomplete, and what it
left out made the scenario unrunnable.** Having established that `bug-0018`'s local landing is not
evidence for `S-017`, nothing followed the thought to its consequence: the task had **closed**, so the
scenario named a Given that no longer existed and no cloud session could ever satisfy it. The runbook
went on carrying a prompt that told a session to implement a finished task. This audit did not catch
it, and could not have with the question it was asking: every row here compares one document against
the code it describes, and the defect lived between three documents that were each individually
correct. `S-017` and `S-018` now name
[`bug-0020`](../../.tasks/done/bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md), which is
open, is a defect in `scripts/install.py` so `S-018`'s wording stays literally true, and whose first
acceptance criterion already requires a test failing against the current message. **The three rows
stay Not-built.** The amendment makes the run specifiable; only the run moves them.

**A small inconsistency found while grounding the S-008 rows, recorded rather than fixed.**
[`bug-0021`](../../.tasks/done/bug-0021-reachability-counts-any-skill-not-a-kit-skill.md) declares
`docs/spec/cloud-executable.md` in its `touched_files`, and the spec's git history shows it made no
edit to that file. That is the correct outcome, since the contract already asked the narrower
question and the code moved to it, and the task's own body says so. The stale frontmatter entry is
the residue of an amendment that turned out to be unnecessary. It is noted here because a reader
comparing `touched_files` against the spec's history would otherwise suspect an unrecorded amendment,
and there is none.

**The two closures that produced no matrix are a procedural finding, not a code one.** `feat-0045`
and `feat-0046` both closed against this spec with no `conformance:` key and no matrix in existence.
The closeout lifecycle in `AGENTS.md` names the acceptance command, `depends_on`, `doc-sync`, the
`done/` move, the changelog line, and the roadmap strike, and does not name producing a matrix. The
[spec-closeout gate](../../.agents/hooks/spec-conformance-gate.py) would have blocked both, and it is
not registered in the one settings file that runs in the harness this repository is developed in.
`chore-0034` records both options, registering the gate or writing the step into the lifecycle, as an
open question for the author and deliberately decides neither. This matrix removes the instance and
leaves the general question open.

**The 2026-08-20 proof run, and what it did and did not establish (`bug-0043`).** `S-017`, `S-018`,
and the unattended-branch surface row move to Conformed on this run. **`S-019` does not, and neither
does `S-008`.**

`S-019`'s Given is a session whose acceptance command exits non-zero. The run's exited 0 with all
seven gates passing, so the failure path was never entered. It stays **Not-built** rather than being
folded into `S-017`, which is exactly why it was recorded separately in the first place.

`S-008` stays **Conformed on tests and unobserved in a real cloud session**, unchanged by this run.
The session reported no startup message, and the cause is not the hook: it was staged on a branch cut
from `main`, 99 files behind `developer`, so the hook that would have fired was the pre-`bug-0021`
copy, which counts any `SKILL.md` and is silenced by a populated foreign `~/.claude/skills`.
Reproduced independently against both copies in the same environment: `main`'s runs, exits 0, and is
silent; `developer`'s reports. **A "no" from a stale base is not evidence against the fix**, and the
runbook's reading table would have read it as exactly that, which `bug-0043` fixed by gating the
table on the base.

One property of this audit is worth stating plainly, since it recurs: the run that produced the
Conformed rows above also produced a false finding, rediscovering `bug-0021` and offering it as new,
because it was reading superseded code. The rows above are Conformed on evidence re-derived after the
rebase and re-verified by a second session, not on the report as first written.
