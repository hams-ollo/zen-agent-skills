---
title: sitrep conformance
spec: docs/spec/sitrep.md
audited: 2026-09-11
---

# sitrep conformance matrix

Spec-vs-implementation audit of `.agents/skills/sitrep/` against [`sitrep.md`](sitrep.md), produced
at `feat-0066`'s closeout. The decomposition is `feat-0066` to `feat-0071`, in that order, gated by
[`sitrep.readiness.md`](sitrep.readiness.md), and each task updates this matrix as it closes.

**Twenty-eight of the forty scenarios are built.** `feat-0066` built what waits on the person and
what is blocked, which is `S-001` to `S-007`, `S-010` and `S-014`; `feat-0067` added in-flight work
and changes from git, which is `S-008`, `S-009`, `S-011` and `S-039`; `feat-0068` added evidence
tiers and declared figures, which is `S-012`, `S-013` and `S-015` to `S-020`; `feat-0069` added the
person's watermark, which is `S-021` to `S-026` and `S-040`. Every other row is not-built and names
the task that owes it.

**Conformed is not unbounded.** The watermark rows rest on a transcript field, `origin`, that
Anthropic does not document as a contract; `chore-0093` measured it on every typed prompt from
version 2.1.197 to 2.1.266. If it is renamed or dropped, `S-040` keeps the watermark from moving
rather than letting it move wrongly. Their tests run on synthetic transcripts in that measured
shape, not on a live session; `feat-0071` is the first task to run one end to end.

Citations are by symbol and by test name, never by line number, per the convention `bug-0037`
established and `scripts/check-citations.py` enforces.

## Coverage proof

The spec carries **40** scenarios, `S-001` to `S-040`. This matrix has **40** rows: **28** conformed,
**0** diverged, **12** not-built. 28 + 0 + 12 = 40, and the arithmetic is stated rather than the
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
| `S-008`: uncommitted work in a worktree is in flight | **conformed** | `worktree_entries()` in `.agents/skills/sitrep/scripts/sitrep.py` reads the porcelain worktree listing and counts the lines git status reports for each worktree, untracked files included, and never reads task status. Proven by `test_s008_uncommitted_work_in_a_worktree_is_in_flight` and `test_s008_a_clean_worktree_is_not_in_flight`. |
| `S-009`: a branch with unmerged commits is in flight | **conformed** | `branch_entries()` in `.agents/skills/sitrep/scripts/sitrep.py` counts each local branch against the integration branch `resolve_integration()` chose. Proven by `test_s009_a_branch_with_unmerged_commits_is_in_flight`; `test_s009_the_default_branch_of_origin_is_the_integration_branch` and `test_s009_a_declared_branch_that_does_not_exist_is_reported` pin the surface's resolution order. |
| `S-010`: a repository without task tracking still gets a board | **conformed** | `load_tasks()` in `.agents/skills/sitrep/scripts/sitrep.py` raises `NOTICE_NO_TASKS` when nothing is tracked under `.tasks/`, and `build_board()` still returns every section. Proven by `test_s010_a_repository_without_task_tracking_still_gets_a_board`. `test_s010_a_board_without_task_tracking_carries_its_work_in_flight` proves the in-flight half. |
| `S-011`: changes since the watermark are summarised | **conformed** | `changes_since()` in `.agents/skills/sitrep/scripts/sitrep.py` counts the commits from the base to HEAD and reads the rename-aware name-status diff over the task directory. Proven by `test_s011_changes_since_a_revision_are_summarised`. The base is the watermark `resolve_since()` chose, or an explicit since. |
| `S-012`: a count over a tracked file is Purple | **conformed** | `declared_figure()` in `.agents/skills/sitrep/scripts/sitrep.py` reads a file the current revision holds with `held_at_head()` and counts what `select()` yields. Proven by `test_s012_a_count_over_a_tracked_file_is_purple_and_read_at_the_current_revision` and `test_s012_a_filter_matches_a_non_string_in_its_json_spelling`. |
| `S-013`: a value read from a tracked file is Blue | **conformed** | `declared_figure()` in `.agents/skills/sitrep/scripts/sitrep.py`. Proven by `test_s013_a_value_read_from_a_tracked_file_is_blue`. |
| `S-014`: a task entry is Green | **conformed** | `task_entry()` in `.agents/skills/sitrep/scripts/sitrep.py` sets the tier to Green and the provenance to the task file. Proven by `test_s014_a_task_entry_is_green_and_names_its_task_file`; `test_an_untracked_task_file_is_not_state` proves only tracked task files are read. |
| `S-015`: anything from an untracked file is White | **conformed** | `declared_figure()` in `.agents/skills/sitrep/scripts/sitrep.py` sets White and `LABEL_UNTRACKED` for a source the revision does not hold, and `figures_from_config()` never lifts it by a pin. Proven by `test_s015_anything_from_an_untracked_file_is_white_even_when_counted_and_pinned`. |
| `S-016`: a pinned figure whose test exists is Gold | **conformed** | `test_name_present()` in `.agents/skills/sitrep/scripts/sitrep.py` searches tracked test files at the current revision using `TEST_FILE_GLOBS`. Proven by `test_s016_a_pinned_figure_whose_test_exists_is_gold`. |
| `S-017`: a pinned figure whose test is missing is downgraded | **conformed** | `figures_from_config()` in `.agents/skills/sitrep/scripts/sitrep.py` keeps the source's tier and raises a notice. Proven by `test_s017_a_pinned_figure_whose_test_is_missing_is_downgraded_and_reported` and `test_s017_a_name_in_a_file_that_is_not_a_test_file_does_not_count`. |
| `S-018`: a hand-entered value is White | **conformed** | `figures_from_config()` in `.agents/skills/sitrep/scripts/sitrep.py` gives every manual value White and its stated source. Proven by `test_s018_a_hand_entered_value_is_white_and_shows_who_said_so`. |
| `S-019`: a count of entries carries the lowest tier | **conformed** | `count_figure()` and `lowest_tier()` in `.agents/skills/sitrep/scripts/sitrep.py`. Proven by `test_s019_a_count_carries_the_lowest_tier_among_what_it_counts` and `test_s019_the_board_counts_its_own_entries_by_that_rule`. |
| `S-020`: a figure that cannot be read is a notice | **conformed** | `figures_from_config()` in `.agents/skills/sitrep/scripts/sitrep.py` turns every `FigureError` into a notice and leaves the figure off the board. Proven by `test_s020_a_figure_that_cannot_be_read_is_a_notice_not_a_guess` and `test_s020_an_unreadable_configuration_is_a_notice`. |
| `S-021`: a first look covers seven days | **conformed** | `first_look_base()` in `.agents/skills/sitrep/scripts/sitrep.py` takes the newest commit older than the window, or the empty tree. Proven by `test_s021_a_first_look_covers_the_last_seven_days` and `test_s021_a_repository_younger_than_the_window_counts_its_whole_history`. |
| `S-022`: a reply moves the watermark to the revision shown | **conformed** | `record_shown()` remembers the revision a sitrep described, and `advance_watermark()` in `.agents/skills/sitrep/scripts/sitrep.py` moves to the newest one after which `human_prompt_after()` finds a typed prompt. Proven by `test_s022_a_reply_moves_the_watermark_to_the_revision_the_person_was_shown`, which also hashes every file in the repository before and after and finds the state under the person's home, and by `test_s022_the_most_recent_answered_sitrep_wins_across_sessions`. |
| `S-023`: a session with no typed prompt leaves the watermark | **conformed** | `human_prompt_after()` in `.agents/skills/sitrep/scripts/sitrep.py` counts only a main-thread prompt marked human and later than the sitrep. Proven by `test_s023_a_session_the_person_never_writes_in_leaves_the_watermark_alone`, `test_s023_prompts_typed_before_the_sitrep_was_shown_do_not_count`, `test_s023_a_side_chain_prompt_never_counts_even_carrying_a_human_mark` and `test_s023_a_missing_transcript_counts_as_no_prompt`. |
| `S-024`: a vanished watermark resets to a first look | **conformed** | `resolve_since()` in `.agents/skills/sitrep/scripts/sitrep.py` checks the watermark with `is_commit()` and raises `NOTICE_RESET`. Proven by `test_s024_a_watermark_on_a_vanished_commit_resets_to_a_first_look`. |
| `S-025`: each person has their own watermark | **conformed** | `state_path()` in `.agents/skills/sitrep/scripts/sitrep.py` places state under the person's own home directory, keyed by the repository's git common directory. Proven by `test_s025_each_person_has_their_own_watermark`. |
| `S-026`: an explicit since leaves the watermark alone | **conformed** | `resolve_since()` in `.agents/skills/sitrep/scripts/sitrep.py` returns an explicit revision before consulting any state. Proven by `test_s026_an_explicit_since_leaves_the_watermark_alone`, which leaves an answered sitrep pending and compares the stored state byte for byte. |
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
| `S-039`: no integration branch reports no branches | **conformed** | `resolve_integration()` in `.agents/skills/sitrep/scripts/sitrep.py` returns `NOTICE_NO_INTEGRATION`, and `build_board()` then lists no branches but still lists worktrees. Proven by `test_s039_a_repository_with_no_integration_branch_reports_no_branches_and_says_so`. |
| `S-040`: an unmarked prompt never moves the watermark | **conformed** | `human_prompt_after()` in `.agents/skills/sitrep/scripts/sitrep.py` requires the human origin mark. Proven by `test_s040_a_prompt_nobody_is_marked_as_typing_never_moves_the_watermark`. |
