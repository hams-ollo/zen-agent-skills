---
title: cloud-executable conformance
spec: docs/spec/cloud-executable.md
audited: 2026-08-19
---

# cloud-executable conformance matrix

Spec-vs-implementation audit of [`run-checks.py`](../../scripts/run-checks.py),
[`checks.yml`](../../.github/workflows/checks.yml), the acceptance-command section of
[`AGENTS.md`](../../AGENTS.md), and
[`skill-reachability-reminder.py`](../../.agents/hooks/skill-reachability-reminder.py) with its
committed registration, against [`cloud-executable.md`](cloud-executable.md). Evidence is by code
location or by a test that asserts the requirement; this audit is independent of test pass/fail.

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
| Scenarios | S-001 one command runs every gate and answers with one exit code | Conformed | `run-checks.py:74-102` `gates()`, the seven; `run-checks.py:189` writes one line per gate with its status; `run-checks.py:205-206` returns 0 only when neither counter is set | Tests `test_the_seven_gates_are_present_ordered_and_complete`, `test_every_gate_runs_and_all_passing_exits_zero`. The gate list is pinned in the test as a deliberate second source of truth, since S-005 removes the seven CI steps it could otherwise have been compared against |
| Scenarios | S-002 a failing gate is named, and the gates after it still run | Conformed | `run-checks.py:185-193` the loop reports each gate and continues rather than breaking; `run-checks.py:195-196` dumps every collected failure; `run-checks.py:206` returns 1 | Tests `test_a_failing_gate_does_not_stop_the_ones_after_it`, `test_a_real_failure_exits_one_and_later_gates_still_run`. The second runs real subprocesses, so the non-fail-fast property is proved rather than stubbed |
| Scenarios | S-003 a gate that could not run outranks a gate that failed | Conformed | `run-checks.py:131-132` missing-script check ahead of the call; `run-checks.py:136-139` the `OSError` branch for an interpreter that cannot start; `run-checks.py:204-205` returns 2 whatever else is set | Tests `test_a_gate_that_cannot_run_outranks_one_that_failed`, `test_an_unrunnable_gate_is_not_reported_as_failed`, `test_a_missing_script_is_unrunnable_not_failed`, `test_unrunnable_outranks_failed_for_real`. The missing-script check is load-bearing rather than belt-and-braces: `subprocess` does not raise for a missing script, so without it the whole could-not-run branch would be dead in the case it exists for |
| Scenarios | S-004 the run leaves no installation behind | Conformed | `run-checks.py:53` `THROWAWAY_HOME`; `run-checks.py:92-95` the install cycle's `cleanup` uninstall scoped by `--home`; `run-checks.py:164-169` cleanup runs whether the gate passed or failed | Tests `test_the_install_cycle_reverses_what_it_placed`, `test_cleanup_runs_even_when_the_gate_failed`, `test_only_the_install_cycle_cleans_up_after_itself`. Confirmed in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md) by a before-and-after diff over a full copy of the tree. The one write outside the throwaway home is `scripts/.install-manifest.json`, which is gitignored, is the tool's own record, and is not an installation |
| Scenarios | S-005 CI calls the command instead of restating the gates | Conformed | `checks.yml:66-67` one step, `run: python scripts/run-checks.py`, and no other gate command anywhere in the file | Tests `test_ci_invokes_the_acceptance_command`, `test_ci_does_not_separately_restate_any_gate`, `test_the_marker_set_actually_covers_every_gate`. The restatement guard was **vacuous for five of the seven gates** when first written, matching on each command's last token, and was rebuilt after independent verification defeated it by reinserting four genuine restatements. The third test exists to keep the guard from going vacuous again |
| Scenarios | S-006 the bound of the answer is stated in both places it will be read | Conformed | `run-checks.py:200-202` names `platform.system()` and `platform.python_version()` and the six-cell bound; `AGENTS.md:117` states it in the spec's own words, "**Passing it is necessary but not sufficient**" | Tests `test_the_summary_names_the_platform_and_interpreter`, `test_the_summary_states_that_passing_is_not_sufficient`, `test_agents_md_states_the_bound_in_those_words`. Both halves are guarded, including the one that lives in a prose document rather than in code |
| Scenarios | S-007 passing the command does not make a Windows-only failure pass | Conformed | `checks.yml:21-31` three operating systems by two Python versions with `fail-fast: false`; `checks.yml:67` the Windows cells run the same command; `run-checks.py:200-202` claims nothing wider | Structural, and deliberately so: the readiness report records that no in-repo test layer is possible, since a local test asserting that the matrix catches what one local run cannot would be asserting its own premise. The positive observation is the all-six-cells run recorded in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md). **The scenario's antecedent, a change that fails only on Windows, has never actually occurred here**, so what is proved is that the mechanism is wired, not that it has caught one |
| Scenarios | S-008 a session with no reachable skills is told at the start | Conformed | `skill-reachability-reminder.py:241-246` returns the one `hookSpecificOutput.additionalContext` object; `:169-180` `REPORT` names `python scripts/install.py`; `:236-239` the reporting path is reached only when `reachable()` is false; nothing in the module opens a file for writing | Tests `test_no_skills_anywhere_is_reported`, the seven `ForeignLibraryTests`, `test_the_report_says_whose_skills_are_missing`. **Corrected by `bug-0021`, which is why this task depended on it**: `_has_skill()` counted any directory holding a `SKILL.md`, so a stock cloud container's own populated `~/.claude/skills` silenced the hook in the exact state this scenario requires it to speak. See the real-environment gap in the observations below |
| Scenarios | S-009 skills committed at project scope count as reachable | Conformed | `skill-reachability-reminder.py:123-125` `PROJECT_SKILL_SUBPATHS`, `.claude/skills` and only that; `:214-216` the project-scope loop in `reachable()` | Tests `test_project_scope_skills_count_as_reachable`, `test_kit_skills_at_project_scope_only_are_silence`, `test_a_real_project_scope_install_here_is_reachable`, `test_the_opencode_path_does_NOT_count_at_project_scope`. The singular is load-bearing: an earlier version also checked `.agents/skills` at project scope, which is this kit's own committed source tree, so a fresh clone with nothing installed counted twenty skills and stayed silent |
| Scenarios | S-010 a session with reachable skills receives nothing | Conformed | `skill-reachability-reminder.py:236-239` returns `None`, and `main()` writes only when `evaluate()` returns non-`None` (`:259-261`) | Tests `test_user_scope_skills_count_as_reachable`, `test_the_opencode_user_scope_counts_too`, `test_one_kit_skill_beside_a_foreign_library_is_silence`, `test_a_partial_install_is_reachable`. Independent verification confirmed thirteen hook mutations caught, including always-report and never-report, so neither direction passes vacuously |
| Scenarios | S-011 reachability is not currency | Conformed | `skill-reachability-reminder.py:183-205` `_has_kit_skill()` tests directory name and `SKILL.md` presence only, never content; `:27-35` the docstring states the limit; `:177-179` the message repeats it and names `install.py --check` | Test `test_a_stale_install_is_still_reachable_and_still_silent`. The clause the scenario asks for, that silence means reachable and never current, is present in both the module and the injected message, so a reader of either finds it |
| Scenarios | S-012 a present install with no record is reachable, and separately unrecorded | Conformed | Hook half: `skill-reachability-reminder.py:208-220` `reachable()` consults the filesystem and never a manifest. `--check` half: `install.py:983-986` prints "nothing can be checked" and returns 2 | Tests `test_skills_present_with_no_manifest_are_reachable` and `test_checking_a_home_with_nothing_recorded_does_not_report_it_as_current`. Both halves guarded, in two suites, which is what the scenario's "both correct and not in conflict" needs |
| Scenarios | S-013 only a started session fires the bootstrap | Conformed | `skill-reachability-reminder.py:98` `FIRING_SOURCES = {"startup"}`; `:229-230` the source check ahead of any filesystem work | Tests `test_startup_fires`, `test_the_continuing_sources_do_not_fire`, `test_another_event_does_not_fire`, `test_only_the_listed_sources_fire`. The last is a structural guard added after verification defeated the original by inverting the allowlist into a denylist of the four continuing sources |
| Scenarios | S-014 the bootstrap writes nothing, in every case | Conformed | No write call exists in the module; `:196-205` and `:254-263` are read-only with `try`/`except` around them | Four tests: `test_the_reporting_path_writes_nothing`, `test_the_silent_path_writes_nothing`, `test_main_writes_nothing_including_into_the_home_it_resolves`, `test_the_source_performs_no_write_of_any_kind`. The fourth parses the source with `ast` rather than substring-matching it, after the first snapshot version was defeated by a write into `tempfile.gettempdir()` and by a write from `main()` rather than `evaluate()` |
| Scenarios | S-015 an unreadable payload leaves the session unchanged | Conformed | `skill-reachability-reminder.py:254-257` a failed `json.load` returns 0 silently; `:258-263` any exception inside `evaluate()` returns 0 silently; `:225-226` a non-dict payload returns `None` | Tests `test_malformed_json_is_silent_and_exits_zero`, `test_empty_stdin_is_silent_and_exits_zero`, `test_a_non_object_payload_is_silent`, `test_a_payload_missing_every_field_is_silent`, `test_main_emits_exactly_one_json_object_when_it_fires` |
| Scenarios | S-016 the bootstrap does not vary by where it runs | Conformed | Nothing in the module imports `os`, `platform`, `socket`, or reads an environment variable; the only inputs are the payload and two filesystem paths | Tests `test_output_is_byte_identical_across_differing_environments` and `test_the_source_reads_no_environment`, the second an `ast` walk over imports, calls, and attribute chains. It is parsed rather than substring-matched because the first widened version fired on the word "subprocess" inside a docstring explaining why the hook does not spawn one, and a guard that fires on its own documentation gets loosened until it catches nothing |
| Scenarios | S-017 the proof run lands as a draft pull request carrying its evidence | **Not-built** | None. [`cloud-executable.verification.md`](cloud-executable.verification.md) records the 2026-08-07 attempt with verdict `blocked`, two independent blockers, and `evidence_produced: none` | The run has not happened as of 2026-08-19. What exists is the surrounding apparatus, not the scenario: rule **A8** in [`autonomy.md`](../../.agents/rules/autonomy.md) states the ceiling, [`cloud-executable.runbook.md`](cloud-executable.runbook.md) tells a person how to start it, and the verification record carries the exact dispatch command. See the observation below on why `bug-0018` having landed on a `claude/` branch is not evidence for this row |
| Scenarios | S-018 the proof's evidence is a test that failed before the change | **Not-built** | None. Same record, `evidence_owed: S-017, S-018, S-019` | This is the row that carries the actual proof, per prediction 6 in the verification record: the other predictions can be satisfied by an agent that followed instructions, and only a test failing before the change and passing after demonstrates work a plausible-sounding report could not have faked. Nothing has produced it |
| Scenarios | S-019 a proof run whose gates fail still reports | **Not-built** | None. Same record | Unreachable until S-017 runs at all, since its Given is the same dispatched session. Recorded separately rather than folded into S-017, because it specifies the failure path and a successful run would leave it still unproved |
| Proposed Surface | Acceptance command `python scripts/run-checks.py`, no flags | Conformed | `run-checks.py:209-215` `main()` takes `argv` only in order to refuse it, returning 2 with a message | Test `test_any_argument_is_refused`. Exit 2 rather than 1 for a refused argument is consistent with the scenario's own precedence: the command did not run the gates, so it did not answer |
| Proposed Surface | Gate set, the seven from `checks.yml` | Conformed | `run-checks.py:83-101`: lint skills, test suite, backlog, adapters dry run, install dry run, install cycle, doc links | Test `test_the_seven_gates_are_present_ordered_and_complete`, plus `test_every_real_gate_names_a_script_that_exists`. The install cycle runs `install.py` twice, which is the idempotence proof; a test pins that after verification found deleting the second run went uncaught |
| Proposed Surface | Throwaway home `./.tmp/zen-home` | Conformed | `run-checks.py:53`, used at `:81` for all three install gates | The literal the spec names, matching what the CI steps already used, and gitignored via `.tmp/` |
| Proposed Surface | Exit code 0 / 1 / 2, with 2 outranking 1 | Conformed | `run-checks.py:204-206`: the unrunnable counter is tested first and returns 2 unconditionally | Proved end to end against real gates in [the S-001 to S-016 verification](cloud-executable.s001-s016.verification.md): three failed plus one unrunnable returned 2, and the same run with only failures returned 1 |
| Proposed Surface | Output: one line per gate, the failing gate's output, then a summary with counts and platform | Conformed | `run-checks.py:189` per-gate line; `:196` the per-gate output block; `:198-202` counts then the platform and Python version | Mirrors `install.py`'s `check()` report shape rather than inventing a second format, as `feat-0045` required. A passing gate whose cleanup failed still gets its output shown (`:188-193`), so leftover files are never announced in one word and explained nowhere |
| Proposed Surface | CI wiring: one step invoking the command | Conformed | `checks.yml:66-67`, a single `Run every acceptance gate` step | The seven steps it replaced are gone rather than commented out, which is what makes the S-005 restatement test meaningful |
| Proposed Surface | `AGENTS.md` names the command and states the bound | Conformed | `AGENTS.md:107-117`, the acceptance-command section: the command in a fenced block at `:110`, the exit codes at `:113`, the bound in the spec's exact words at `:117` | |
| Proposed Surface | Bootstrap hook: reminder shape, `SessionStart`, `startup` matcher | Conformed | `skill-reachability-reminder.py:1-89` docstring declares the shape and contract; `:98` the matcher value; `:249` the injectable `main(stdin, stdout)`; listed in the module table at `.agents/hooks/README.md:50` | Satisfies the hooks module contract the spec's Constraints section imports: exit 0 always, at most one JSON object, no import from this repository, injectable entry point |
| Proposed Surface | Bootstrap registration committed in `.claude/settings.json` | Conformed | `.claude/settings.json`, `hooks.SessionStart` with `matcher: "startup"` and command `python3 .agents/hooks/skill-reachability-reminder.py` | Six tests in `CommittedRegistrationTests`, including one asserting the interpreter and one asserting the `AGENTS.md` bound of exactly one hook. **The interpreter is the finding this row exists to carry**: the first draft said `python`, which does not exist on many Linux distributions or on macOS since 12.3, so the hook would not have launched in the exact environment the committed-settings exception was granted for. Caught by independent verification before any cloud run |
| Proposed Surface | Bootstrap output: nothing when reachable, else one context object | Conformed | `skill-reachability-reminder.py:236-246`; `main()` at `:259-261` writes only a non-`None` result | Test `test_main_emits_exactly_one_json_object_when_it_fires`, plus the four silent-path tests. Both halves of the row are asserted, which matters because a test covering only the fire path would pass against a hook that speaks on every start |
| Proposed Surface | Reachable: one kit skill at the project-scope directory, or at any user-scope directory `install.py` targets | Conformed | `skill-reachability-reminder.py:123-125` project scope, `:128-131` user scope, `:142-163` `KIT_SKILL_NAMES`, `:183-205` the name-and-`SKILL.md` test, `:208-220` the two-scope check | **Diverged until `bug-0021` landed 2026-08-08**, on both halves of the sentence: any `SKILL.md` counted rather than a kit skill's, and project scope was checked against `.agents/skills` as well. Both are now the sentence the spec wrote. `test_the_recognised_names_are_exactly_the_skills_this_kit_ships` asserts the name list equals what the kit ships in both directions, which is the only place a standalone hook forbidden from importing this repository can have the staleness objection answered |
| Proposed Surface | Unattended branch and pull request: `claude/` prefix, draft, nine-field report | **Not-built** | None produced by a proof run. The governing rule exists at `autonomy.md:133` (rule **A8**) and the nine-field contract exists in `fix-batch`'s body | The rule is written; the artifact this row describes has never been produced by the run that would prove it. Classified with S-017 rather than separately, since it is that scenario's surface |

## Coverage proof

- **audited**: all 19 scenarios, S-001 through S-019, and all 12 Proposed Surface rows. 19 + 12 = **31
  items**, which is every auditable item the spec contains. Nothing was sampled and nothing was
  skipped.
- **unreconciled**: **4 of 31**. S-017, S-018, S-019, and the `Unattended branch and pull request`
  surface row. All four are **Not-built**; none is Diverged.
- **conformed**: 27 of 31, being S-001 through S-016 and 11 of the 12 surface rows.
- **disposition of every unreconciled item**: accepted-with-reason, one reason for all four. They are
  the Phase 4 cloud proof run, recorded `blocked` in
  [`cloud-executable.verification.md`](cloud-executable.verification.md) for two independent reasons,
  either sufficient on its own, and neither fixable from inside this repository. `chore-0034` placed
  the proof run explicitly out of its own scope. **Nothing here is to-fix by an agent**, because the
  run has to be started by a person from an interactive terminal or a browser;
  [`cloud-executable.runbook.md`](cloud-executable.runbook.md) is the instruction sheet.

The audited range stops at S-019 and claims nothing wider. The spec has 19 scenarios and this matrix
has 19 scenario rows.

## Observations

**"Conformed" is stronger in this matrix than in most here, and it is worth saying why rather than
letting the word carry equal weight everywhere.** The limit stated at the foot of
[`README.md`](README.md) is that most of what this kit ships is prose, so a conformance row usually
cites a clause and establishes that a skill *instructs* the behavior, not that anything *enforces*
it. This contract is the exception: 15 of the 16 built scenarios are backed by executing tests
against executing code, and the sixteenth, S-007, is a property of a workflow file that no in-repo
test can honestly assert. The single prose citation in the whole matrix is `AGENTS.md:117`, and even
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
