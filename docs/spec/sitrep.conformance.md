---
title: sitrep conformance
spec: docs/spec/sitrep.md
audited: 2026-09-11
---

# sitrep conformance matrix

Spec-vs-implementation audit of `.agents/skills/sitrep/` against [`sitrep.md`](sitrep.md), produced
at `feat-0066`'s closeout. The decomposition is `feat-0066` to `feat-0071`, in that order, gated by
[`sitrep.readiness.md`](sitrep.readiness.md), and each task updates this matrix as it closes.

**Nine of the forty scenarios are built.** `feat-0066` built what waits on the person and what is
blocked, which is `S-001` to `S-007`, `S-010` and `S-014`. Every other row is not-built and names the
task that owes it.

**Conformed is not unbounded.** `S-010`'s Then asks that a board with no task tracking still carry
in-flight work and changes since the watermark. Those sections are present and empty until
`feat-0067` fills them, and that task's tests run the scenario again against a repository with work
in flight.

Citations are by symbol and by test name, never by line number, per the convention `bug-0037`
established and `scripts/check-citations.py` enforces.

## Coverage proof

The spec carries **40** scenarios, `S-001` to `S-040`. This matrix has **40** rows: **9** conformed,
**0** diverged, **31** not-built. 9 + 0 + 31 = 40, and the arithmetic is stated rather than the
claim.

## Matrix

| Scenario | Status | Evidence |
|---|---|---|
| `S-001`: an open question with no decision below it waits | **conformed** | `waiting_reasons()` in `.agents/skills/sitrep/scripts/sitrep.py` compares the position of the last open-question heading with the last decision heading, using `OPEN_QUESTION_RE` and `DECISION_RE`. Proven by `test_s001_an_open_question_with_no_decision_below_it_waits_on_the_person`; `test_s001_a_level_three_heading_is_not_an_open_question` and `test_s001_the_heading_is_matched_in_any_letter_case` pin the surface's heading rule. |
| `S-002`: a decision above a newer question does not answer it | **conformed** | `waiting_reasons()` in `.agents/skills/sitrep/scripts/sitrep.py` takes the last question, not the first. Proven by `test_s002_a_decision_above_a_newer_question_does_not_answer_it` and `test_s002_the_last_question_decides_when_there_are_several`. |
| `S-003`: a decision below a question answers it | **conformed** | `waiting_reasons()` in `.agents/skills/sitrep/scripts/sitrep.py`. Proven by `test_s003_a_decision_below_a_question_answers_it` and `test_s003_one_decision_below_every_question_answers_them_all`. |
| `S-004`: work held for a human eye waits | **conformed** | `waiting_reasons()` in `.agents/skills/sitrep/scripts/sitrep.py` searches every heading level with `HUMAN_EYE_RE`, in any case. Proven by `test_s004_work_held_for_a_human_eye_waits_on_the_person` and `test_s004_the_phrase_in_prose_is_not_a_heading`. |
| `S-005`: a closed task never waits | **conformed** | `classify()` in `.agents/skills/sitrep/scripts/sitrep.py` skips every task `parse_task()` marks closed. Proven by `test_s005_a_closed_task_never_waits_on_the_person`. |
| `S-006`: waiting entries ordered by priority | **conformed** | `by_priority()` and `priority_rank()` in `.agents/skills/sitrep/scripts/sitrep.py`. Proven by `test_s006_waiting_entries_are_ordered_by_priority_then_id`. |
| `S-007`: a task with an unfinished dependency is blocked | **conformed** | `classify()` in `.agents/skills/sitrep/scripts/sitrep.py` names each dependency with no file under the done directory. Proven by `test_s007_a_task_with_an_unfinished_dependency_is_blocked` and `test_s007_a_task_whose_dependencies_are_all_done_is_not_blocked`. |
| `S-008`: uncommitted work in a worktree is in flight | not-built | Owed to `feat-0067`. |
| `S-009`: a branch with unmerged commits is in flight | not-built | Owed to `feat-0067`. |
| `S-010`: a repository without task tracking still gets a board | **conformed** | `load_tasks()` in `.agents/skills/sitrep/scripts/sitrep.py` raises `NOTICE_NO_TASKS` when nothing is tracked under `.tasks/`, and `build_board()` still returns every section. Proven by `test_s010_a_repository_without_task_tracking_still_gets_a_board`. Bound: the in-flight and changed sections are empty until `feat-0067`. |
| `S-011`: changes since the watermark are summarised | not-built | Owed to `feat-0067`. |
| `S-012`: a count over a tracked file is Purple | not-built | Owed to `feat-0068`. |
| `S-013`: a value read from a tracked file is Blue | not-built | Owed to `feat-0068`. |
| `S-014`: a task entry is Green | **conformed** | `task_entry()` in `.agents/skills/sitrep/scripts/sitrep.py` sets the tier to Green and the provenance to the task file. Proven by `test_s014_a_task_entry_is_green_and_names_its_task_file`; `test_an_untracked_task_file_is_not_state` proves only tracked task files are read. |
| `S-015`: anything from an untracked file is White | not-built | Owed to `feat-0068`. |
| `S-016`: a pinned figure whose test exists is Gold | not-built | Owed to `feat-0068`. |
| `S-017`: a pinned figure whose test is missing is downgraded | not-built | Owed to `feat-0068`. |
| `S-018`: a hand-entered value is White | not-built | Owed to `feat-0068`. |
| `S-019`: a count of entries carries the lowest tier | not-built | Owed to `feat-0068`. |
| `S-020`: a figure that cannot be read is a notice | not-built | Owed to `feat-0068`. |
| `S-021`: a first look covers seven days | not-built | Owed to `feat-0069`. |
| `S-022`: a reply moves the watermark to the revision shown | not-built | Owed to `feat-0069`. |
| `S-023`: a session with no typed prompt leaves the watermark | not-built | Owed to `feat-0069`. |
| `S-024`: a vanished watermark resets to a first look | not-built | Owed to `feat-0069`. |
| `S-025`: each person has their own watermark | not-built | Owed to `feat-0069`. |
| `S-026`: an explicit since leaves the watermark alone | not-built | Owed to `feat-0069`. |
| `S-027`: a session opens with the sitrep | not-built | Owed to `feat-0071`. |
| `S-028`: a long section is cut short | not-built | Owed to `feat-0070`. |
| `S-029`: the session gets the reporting rules | not-built | Owed to `feat-0071`. |
| `S-030`: a sitrep that cannot be produced never stops the session | not-built | Owed to `feat-0071`. |
| `S-031`: outside a git repository nothing is added | not-built | Owed to `feat-0071`. |
| `S-032`: a person who has not installed it sees nothing | not-built | Owed to `feat-0071`. |
| `S-033`: status and evidence never share a colour | not-built | Owed to `feat-0070`. |
| `S-034`: every figure on the page shows tier and provenance | not-built | Owed to `feat-0070`. |
| `S-035`: the page is written only where asked | not-built | Owed to `feat-0070`. |
| `S-036`: generating a board changes nothing in the repository | not-built | Owed to `feat-0070`. |
| `S-037`: the board needs no network | not-built | Owed to `feat-0070`. |
| `S-038`: the board is one versioned document | not-built | Owed to `feat-0070`. |
| `S-039`: no integration branch reports no branches | not-built | Owed to `feat-0067`. |
| `S-040`: an unmarked prompt never moves the watermark | not-built | Owed to `feat-0069`. |
