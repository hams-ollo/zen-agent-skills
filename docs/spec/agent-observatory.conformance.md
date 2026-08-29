---
title: agent-observatory conformance
spec: docs/spec/agent-observatory.md
audited: 2026-08-29
---

# agent-observatory conformance matrix

Spec-vs-implementation audit of `scripts/observatory/` against
[`agent-observatory.md`](agent-observatory.md), produced at `feat-0053`'s closeout and updated at
`feat-0054`'s, `feat-0055`'s, `feat-0060`'s, and `feat-0059`'s.

**Fifteen of twenty-two scenarios are built.** `feat-0053` scoped the store and the ingester;
`feat-0054` added the loopback server, the page shell, and the skills report, which is `S-001`
and `S-002`; `feat-0055` added the fleet report and the live-session registry behind it, which is
`S-012` and `S-018`; `feat-0060` added the control boundary and the companion skill, which is
`S-019` and `S-020`; `feat-0059` added the live path and the optional event source, which is
`S-013` to `S-015`. The remaining seven are `not-built` and that is the correct answer rather
than a gap. Each names the task that owns it, from the decomposition
[`feat-0053`](../../.tasks/done/feat-0053-the-observatory-store-and-its-incremental-ingester.md)
onward gated by [`agent-observatory.readiness.md`](agent-observatory.readiness.md).

Citations are by symbol and by test name, never by line number, per the convention `bug-0037`
established and `scripts/check-citations.py` enforces.

## Coverage proof

The spec carries **22** scenarios, `S-001` to `S-022`. This matrix has **22** rows: **15**
conformed, **0** diverged, **7** not-built. 15 + 0 + 7 = 22, and the arithmetic is stated
rather than the claim, per the incident `feat-0036` recorded and `chore-0033` named.

Nothing in the audited set is unreconciled. The audited set is the fifteen scenarios the five
closed tasks declare between them: the six in `feat-0053`'s `scenarios` frontmatter, the two in
`feat-0054`'s, the two in `feat-0055`'s, the two in `feat-0060`'s, and the three in `feat-0059`'s.
The seven not-built rows were established by confirming no code implements them, not by inspecting
an implementation. The three still owed belong to `feat-0056` (`S-003`, `S-004`), `feat-0057`
(`S-010`, `S-011`, `S-017`, `S-021`), and `feat-0058` (`S-016`).

**`feat-0060` ran second of the six remaining tasks rather than last**, so it does not complete
the contract and its own definition of done said it would. That criterion assumed an ordering
that did not happen, was corrected in the task file rather than satisfied against a different
claim, and is recorded here for the same reason `chore-0033` recorded the one it corrected on
`feat-0051`.

## Matrix

| Scenario | Status | Evidence |
|---|---|---|
| `S-001`: skill usage reported from attribution | **conformed** | `skills_report()` in `scripts/observatory/serve.py` groups `message` by `attribution_skill`, and that table holds one canonical row per uuid, so a use is one distinct message rather than one line in the corpus. Proven by `test_s001_a_skill_use_count_is_distinct_messages_not_corpus_lines`, whose fixture makes the two candidate oracles disagree (three lines, two messages), by `test_s001_the_reported_total_equals_the_attribution_in_the_corpus`, and by `test_s001_the_report_is_served_over_http_and_matches_the_store` through the real surface. Measured over the maintainer's corpus on 2026-08-28: 6,033 attributed messages across 21 names against 6,518 lines, and the served figure matched a count made independently of the store. |
| `S-002`: an unused skill reported as zero | **conformed** | `skill_roster()` in `scripts/observatory/serve.py` takes the roster from the installer's own discovery rather than from the corpus, and `skills_report()` unions it with what the corpus carries, so a roster skill the corpus never mentions appears at zero. Proven by `test_s002_an_installed_skill_absent_from_the_corpus_is_reported_as_zero`, by `test_s002_every_installed_skill_appears_even_when_the_corpus_is_empty` for the degenerate case, and by `test_s002_the_roster_is_the_installers_own_skill_directories` for the roster's source. Measured 2026-08-28: 8 of the 20 shipped skills have never been used, which is the figure the contribution-bar section of `AGENTS.md` asks for and nothing here could previously answer. |
| `S-003`: subagent runs reported with outcome and cost | not-built | Owned by `feat-0056`. The store now holds what it can: 260 of 270 `agent_run` rows carry `agent_type` and `spawn_depth`, sourced from the `agent-<id>.meta.json` sidecars, and 16,426 messages carry `agent_id` so per-agent token figures are derivable. **A bound remains and is the corpus's, not the store's**: only 19 rows carry `total_tokens`, `total_duration_ms`, and `total_tool_use_count`, because the other 251 are backgrounded launches with no completion record anywhere in the corpus. **Those three are still derivable in-store** for the 261 agents that have messages, from `message.agent_id`, `message.ts`, and `tool_call.message_uuid`; only a backgrounded agent's completion *outcome* is genuinely absent, and it lives outside the corpus entirely. `feat-0056` inherits that bound, not a blocked scenario. |
| `S-004`: a dispatched wave reported as one unit | not-built | Owned by `feat-0056`. |
| `S-005`: re-reporting an unchanged corpus changes nothing | **conformed** | `ingest` skips a transcript whose recorded size and offset both match the file on disk. Proven by `test_s005_reingesting_an_unchanged_corpus_adds_no_rows`, and by `test_a_shortened_transcript_is_re_read_without_duplicating_rows` for the path where the conflict clauses rather than the offset carry it. |
| `S-006`: new records picked up without re-reading the corpus | **conformed** | `scan_file` resumes from the recorded byte offset; `ingest` reports `bytes_read` as the difference. Proven by `test_s006_second_run_reads_only_what_was_appended`, which pins the figure to the exact appended byte count. Exercised on the real corpus: a second run read 9,822 bytes against 396 MB. |
| `S-007`: an empty corpus reported as empty | **conformed** | `main` returns 2 when no transcript is found and 0 otherwise, so the outcome is distinguishable by exit code and not only by wording. Proven by `test_s007_empty_corpus_is_distinguishable_by_exit_code` and `test_s007_a_missing_corpus_directory_is_also_empty_not_a_crash`. |
| `S-008`: an unreadable record reported, not silently dropped | **conformed** | `scan_file` stops before an unterminated final line and does not advance the offset past it, and counts a terminated line that fails to parse while stepping over it. Both notes carry the path and the byte offset. Proven by `test_s008_incomplete_final_record_is_reported_and_not_consumed` and `test_s008_terminated_but_unparseable_record_is_reported_and_stepped_over`. |
| `S-009`: nothing the harness owns is modified | **conformed** | Transcripts are opened `"rb"` in `scan_file` and nowhere else; the store defaults outside the corpus via `DEFAULT_STORE`. Proven by `test_s009_the_corpus_is_byte_for_byte_unchanged` and `test_s009_the_store_is_written_outside_the_corpus`. Independently established over the real corpus by an outside verification: 769 files hashed before and after with 0 changed, and every file open during a full ingest instrumented, giving 412 opens all in mode `rb` and none outside the corpus. |
| `S-010`: cost reported as a dated estimate | not-built | Owned by `feat-0057`. No rate table exists. |
| `S-011`: an unpriced model yields no invented cost | not-built | Owned by `feat-0057`. |
| `S-012`: a running session distinguished from an ended one | **conformed** | `fleet_report()` in `scripts/observatory/serve.py` reports every session with its project, its branch, and its last activity, and marks running the ones the harness's live-session registry accounts for. The registry is `~/.claude/sessions/`, read by `read_registry()` in `scripts/observatory/ingest.py` and checked per request by `live_sessions()`, not ingested, because the scenario asks a question about now. **Presence in the registry is evidence and never proof**: `process_state()` corroborates each entry against the operating system, and `LIVENESS_POLICY` states the rule the page shows a reader. On Windows the check is presence plus identity wherever the entry records one, comparing the pid's start time against the entry's `procStart`, so a reused pid is reported gone; an entry carrying no `procStart` is confirmed on presence alone, and `liveness_check()` says so rather than advertising identity unconditionally; `os.kill(pid, 0)` is unreachable from that branch because on Windows it terminates the process it was asked about. Proven by `test_s012_a_session_in_the_live_registry_is_reported_as_running`, `test_s012_a_session_absent_from_the_registry_is_reported_as_ended`, `test_s012_each_session_carries_its_project_its_branch_and_its_last_activity`, and through the real surface by `test_s012_the_report_is_served_over_http_and_matches_the_store`. The stale and unverifiable outcomes are pinned by `test_s012_a_stale_registry_entry_is_reported_ended_rather_than_running` and `test_s012_an_unverifiable_entry_is_reported_unverified_rather_than_running`, and the degenerate inputs by `test_s012_the_report_renders_with_the_registry_absent` and `test_s012_the_report_renders_with_the_registry_empty`. **A third bound, which `docs/OBSERVATORY.md` states and this row previously did not**: a session that started since the last ingest has no store row, so its branch and last activity are reported as not yet recorded rather than invented, and only its project is recovered, from the transcript beside it. The field is reported unknown rather than the session dropped, because dropping it would break `S-018`. Measured 2026-08-28 over the maintainer's corpus: 155 sessions, of which the 3 with a registry entry were reported running and matched the 3 running processes on the machine; after a reboot the same store reported 1 running and the two whose entries had gone as ended. |
| `S-013`: the report updates while a session is running | **conformed** | `LiveWatcher` in `scripts/observatory/serve.py` tails the corpus, folds appended records in through the same incremental read the ingester uses, and pushes to every open page over server-sent events; the page opens the channel in `live()`. Proven by `test_s013_appended_records_produce_an_event_without_anyone_asking`, which also asserts the store holds what the event announced, by `test_s013_an_unchanged_corpus_produces_no_event` for the silence that must accompany it, and end to end over the real channel by `test_s013_an_open_stream_is_told_about_work_it_did_not_ask_for`. **Exercised in a browser rather than only in tests** on 2026-08-29: with a page open against a watched corpus, appending one transcript took the fleet report from 155 sessions to 156 with the new row rendered, and nothing was requested again. |
| `S-014`: the optional event source is absent and all still works | **conformed** | The default path depends on nothing a user installs: `LiveWatcher` polls the corpus itself, and an absent spool is a normal state rather than an error. Proven by `test_s014_the_watcher_works_with_no_spool_present_and_reports_no_error`, which also asserts that looking for an absent spool does not create one. **The delay is stated as a number**, which the scenario requires in those words: `DEFAULT_POLL_SECONDS` is 2, `docs/OBSERVATORY.md` says newly appended records reach an open report within about 2 seconds, and the page repeats it from the same source. Pinned by `test_s014_the_stated_delay_is_a_number_and_the_page_and_document_agree`. The cheap probe that makes a two-second poll affordable is `corpus_fingerprint()`, measured at 38 ms against 167 ms for a full pass, and guarded by `test_an_unchanged_corpus_is_not_ingested_at_all`. |
| `S-015`: an optional event source changes no figure | **conformed** | The reconciliation rule is `EVENT_POLICY` and it makes the scenario true by construction rather than by care: **an event is a hint to look, never a datum**. Every figure is derived from the corpus, so an event arriving by hook and the records describing the same work cannot both be counted, because only one of them is ever counted at all. Proven as an equality by `test_s015_the_optional_source_changes_no_figure`, which compares a run with the source shouting about every record against a corpus-only run and requires the figures to match exactly. Attribution by `test_s015_an_event_from_the_spool_is_attributed_to_the_hook`: there are exactly two sources and each event names its own. The source is `.agents/hooks/observatory-event.py`, which appends to a spool file and opens no socket, so it cannot hang inside a live session; `test_the_hook_opens_no_socket_and_imports_nothing_from_this_repository` pins its import list. |
| `S-016`: run health is reported | not-built | Owned by `feat-0058`. `health_event` holds 392 rows across four kinds, of which 133 carry a hook exit status and 16 are real hook failures, so the "hook's exit status" the scenario names is present and unread rather than absent. The scenario's third part is also in-store: `message.is_api_error` (26), `api_error_status` (21), and `is_aborted_mid_stream` (2) record a run that ended abnormally. |
| `S-017`: context and quota pressure over time | not-built | Owned by `feat-0057`. The context half is in-store: `context_sample` holds 3,085 parsed remaining-token readings across 19 sessions, and compaction occasions are identifiable from the 2 `compact_boundary` rows in `health_event`. The quota half comes from a file outside the corpus and is `feat-0057`'s to bring in. |
| `S-018`: every project reported in one place | **conformed** | Both built reports cover the whole corpus by default and restrict to one project, and the scenario's third clause is arithmetic rather than visual: restricted to each project in turn, the figures sum to the unrestricted ones. `fleet_report()` in `scripts/observatory/serve.py` holds it by construction, because every session lands in exactly one project bucket, including one nothing can attribute, which goes to `UNATTRIBUTED` rather than being dropped. Proven by `test_s018_per_project_figures_sum_to_the_unrestricted_figures` over all four figures, by `test_s018_a_live_session_matching_no_known_project_is_counted_not_dropped` for the bucket, by `test_s018_the_state_counts_partition_the_sessions` for the second identity, and over HTTP by `test_s018_the_scoped_report_carries_only_that_projects_sessions`. `projects()` was widened to the union of `message_occurrence` and `session`, and `scope_options()` adds the projects only a live session knows about, so a project a report counts is one the selector can reach: `test_s018_a_project_whose_session_carries_no_message_is_still_offered` and `test_s018_the_scope_selector_offers_every_project_the_fleet_counts`. **One bound, stated rather than left to be found.** For the skills report the identity holds only where no message appears under two projects, which is what a fork replaying history into another project's directory would produce. It does not occur in this corpus: 0 of 54,222 messages, measured 2026-08-28. Both halves are pinned, by `test_s018_the_skills_report_identity_holds_when_no_message_spans_projects` and by `test_s018_a_message_replayed_into_another_project_is_the_stated_bound`, which asserts what the report actually does in that case rather than what it should. Measured 2026-08-28 on the real corpus: 155 sessions summed across 23 projects to 155. |
| `S-019`: the reporting surface offers no session mutation | **conformed** | The scenario is an enumeration claim, which is what makes it decidable: "nothing mutates a session" is untestable as prose and checkable as a list. `ACTIONS` in `scripts/observatory/serve.py` is that list, and `ACTION_KINDS` is the closed set of what an entry may be, holding exactly `navigate` and `copy-command`, which are the two things the scenario's Then permits. The three offered are opening the pull request, copying the working directory, and copying a resume command, and presenting a command is not running it. **The enumeration is derived rather than maintained**: `actionControl()` in `scripts/observatory/ui/index.html` is the only place an element is built and it tags every one with the action it came from, so an element built elsewhere fails `test_the_fleet_renderer_builds_no_interactive_element_of_its_own`, an untagged element fails `test_s019_every_element_the_construction_site_returns_is_tagged`, and a tag naming no declared action fails `test_s019_the_enumeration_is_derived_from_the_page_not_maintained_by_hand`. **The guard was first written narrower than its own purpose and an outside verification caught it**: it covered `actionControl()` and the fleet renderer, so an untagged control added to any of the other four renderers survived the whole suite, which matters because `feat-0056`'s waves report renders per-session rows. It now spans every named function in the page's script and names the offender, guarded by `test_s019_no_part_of_the_page_builds_a_control_outside_the_tagged_site`. Proven further by `test_s019_every_action_the_surface_offers_resolves_to_a_non_mutating_kind`, by `test_s019_the_construction_site_cannot_reach_a_session`, by `test_s019_a_navigate_action_targets_stored_data_rather_than_a_composed_url`, and, over the server rather than the page, by `test_s019_a_mutating_method_is_declined_on_every_route_the_handler_defines`, which reads the handler's own methods rather than restating them. Exercised on the real corpus 2026-08-29: 156 session rows carrying 365 interactive elements, of which 0 were untagged, across only the three declared ids, with no form or submit control anywhere on the page. |
| `S-020`: control available only where the harness exposes it | **conformed** | The page requests no session action at all, so the declining behaviour lives where a request is actually made: `.agents/skills/agent-observatory/SKILL.md`, which reads the store and acts only through session management the harness exposes. Its step 4 declines with the reason stated, names what is still available (the `S-019` affordances: the pull request, the working directory, and a resume command), and forbids every alternative route by name, including the messaging path the live registry records. Archiving is excluded although the harness offers it, because it stops the process and so is ending a session, which the contract's Non-Goals exclude. Proven by `test_s020_the_skill_declines_with_the_reason_stated`, `test_s020_the_navigation_actions_remain_available_when_control_does_not`, `test_s020_no_alternative_route_to_the_same_effect_is_attempted`, `test_s020_the_harness_dependent_half_sits_in_a_labelled_optional_section`, and `test_s020_the_skill_ends_no_session_and_says_so`. The skill is a draft placed by no profile, proven against the real installer by `test_the_companion_skill_is_a_draft_and_no_profile_places_it`. **These assertions are structural over prose and that is a real bound**: a skill body is instructions to a model, so a test can assert the declining instruction is present and cannot assert a model obeyed it. |
| `S-021`: token consumption reported by kind | not-built | Owned by `feat-0057`. The store splits the four kinds on `message`; nothing reports them. |
| `S-022`: no data leaves the machine | **conformed** | The surface also refuses a request whose `Host` names anything but a loopback address or `localhost`, checked by `host_is_loopback()` in `scripts/observatory/serve.py` before a route is resolved. That is **outside** this scenario's wording, which is about outbound connections, and is recorded here because `feat-0054` deferred it and `feat-0060` first missed it: an outside verification demonstrated `Host: evil.example.com` returning 155 sessions with their working directories, which is a DNS-rebinding read of everything the report knows. Proven by `test_a_foreign_host_header_is_refused_on_every_route`, `test_a_loopback_host_header_is_served`, `test_the_host_check_decides_the_header_without_a_server`, and `test_the_check_runs_before_the_route_is_resolved`. `db` and `ingest` import only `argparse`, `json`, `sys`, `datetime`, `pathlib`, and `sqlite3`. Proven by `test_s022_no_socket_is_opened_during_a_full_ingest`, which replaces `socket.socket` for the duration of a real ingest, and `test_s022_the_modules_import_nothing_network_capable`. The surface `feat-0054` added holds the property from both sides: the server binds a loopback address and refuses any other before binding, and serving the page plus both data routes connects only to loopback. Proven by `test_a_full_page_and_data_load_connects_only_to_loopback`, `test_a_non_loopback_address_is_refused_before_anything_is_bound`, and `test_the_page_requests_no_subresource_at_all`. |

## Two defects found by independent verification, and fixed before this matrix was written

Both were caught by a verification run that did not write the implementation, which is the
separation [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) exists to create.
Neither was visible to the implementing agent's own tests, and the second was actively hidden
by a fixture that agent had written.

**`agent_run.tool_use_id` was NULL on every row.** The ingester read `sourceToolUseID` from the
agent-result record. Counted over the corpus: of 338 records carrying `toolUseResult.agentId`,
**0** carry `sourceToolUseID` and **338** carry the id on their `tool_result` content block. The
join `agent_run` to `tool_call` returned 0 rows of 264, and that join is what `S-004` needs, so
`feat-0056` would have required the re-ingest `feat-0053`'s Risks section exists to prevent. The
committed fixture had been hand-written with both fields on one record, a combination that occurs
nowhere in 123,272 real records, so the test asserting against it passed. Fixed by reading the
`tool_result` block. Two separate things followed, and they are worth not conflating: the **store**
now carries the id on 265 of 265 rows with all 265 joining to `tool_call`, and the **fixture**, which
holds one such row, was resampled so its record shapes match ones the corpus actually produces.

**Cross-session attribution was last-writer-wins.** 5,442 uuids legitimately appear under more
than one `sessionId`, because a forked or resumed session replays earlier history verbatim into a
new transcript. `INSERT OR REPLACE` keyed on `uuid` kept one row and attributed it to whichever
transcript sorted last. Deduplicating the total is right; the attribution was arbitrary and
unrecorded, and would have made per-session figures wrong for `S-001`, `S-003`, `S-010`, and
`S-021`. Fixed by making `message` first-seen-wins and adding `message_occurrence`, which records
every session a message appeared in: 53,101 canonical messages against 59,712 occurrences.

## Five gaps closed by two independent verifications

Two independent verifications, neither by the implementing agent, passed the six scenarios and
found five places where the store would have forced the re-ingest this task's Risks section exists
to prevent, or where a guarantee held only by accident. Both were closed
before this matrix was finalised, and both are recorded because "the store holds enough for the
later reports" is the claim that would otherwise have been false while every gate stayed green.

**Hook outcomes were half-read.** `health_event` held 73 rows, all `api_error`, with `exit_code`
NULL on every one, while every hook attachment went unread. `S-016` requires "a hook's exit
status". The cause was reading only `system` records: hook outcomes arrive on `attachment`
records, and their `exitCode` and `durationMs` are strings there. Now 392 rows across four kinds,
133 carrying an exit status and 16 being genuine hook failures. **A `stop_hook_summary` branch was
added at the same time and contributes nothing on this corpus**, said plainly rather than counted
as a fix: all 1,287 such records carry empty `hookErrors` and false `preventedContinuation`, so
the branch is filtered to zero rows and `health_event.prevented_continuation` is NULL on every
row. It is a bound, not a repair.

**Subagent messages were unattributable.** A subagent transcript reuses its parent's `sessionId`,
so without `agent_id` the 16,426 subagent messages in the corpus are indistinguishable from the
parent session's own and no per-agent token figure is derivable. `agent_run` also carried no
workspace or branch, which `S-004` requires in those words and which no transcript record holds:
they live only in the `agent-<id>.meta.json` sidecars, which nothing read. Both are now ingested,
and `agent_type` went from 19 of 265 rows to 260 of 270.

## Three further gaps closed by a third verification

A third run, again by an agent that did not write the code, found two more classes of record in
the corpus and discarded, plus one guarantee that held only by accident.

**`S-006` was spelling-dependent.** `ingest_state` was keyed on the literal path string, so the
same corpus reached by a relative path, or by a differently-cased one on Windows, produced a
second row and was re-read from byte zero: reproduced as three rows for one transcript. On a
400 MB corpus that is a full re-read reported as an incremental run. Now keyed on the resolved,
case-normalised path.

**The only context-budget series was dropped.** 3,082 `total_tokens_reminder` attachments across
19 sessions, plus every compaction marker, were filtered out because the attachment branch
admitted only `hook_` types. `S-017` asks for pressure "as series over time" and nothing else in
the corpus carries it.

**Abnormal-termination markers were dropped.** `isApiErrorMessage`, `apiErrorStatus`, and
`isAbortedMidStream` sit on assistant records and had no column, so `S-016`'s third part, "a run
that ended abnormally", was unanswerable.

The same run also found ten behaviours that no test could fail on, including the transcript open
mode, project derivation, subagent-transcript discovery, and the migration path. Each now has a
test, and each test was confirmed by breaking the behaviour and watching it fail.

## What `feat-0054` added, and the bound it inherits

The server, the page shell, and the skills report. Three properties are asserted by tests rather
than by reading the source, because each is the kind of claim that reads as true either way:

- **The bound address is a loopback address**, checked with `ipaddress` against the socket the
  server actually bound, and a non-loopback address is refused before `bind` is called at all.
- **The page requests no subresource**, so there is nothing for an unavailable network to fail to
  deliver. Not "no external subresource": none at all.
- **The skills figure is distinct messages**, on a fixture built so the naive oracle and the
  correct one disagree. A count of corpus lines reports 3 there where the correct figure is 2.

The bound is the shell rather than the report. Four later tasks (`feat-0055` to `feat-0058`)
render into a layout, a navigation, and a scope selector this task fixed, and a shape that cannot
hold five reports would be discovered after four of them were written. The five slots exist now
and four are stubs naming their owner, so the shape has been exercised at the registry level and
not yet at the rendering level.

## What `feat-0055` added, and the two bounds it ships with

The fleet report, and the live-session source behind it. The design decision worth recording is
where the liveness answer comes from, because the task named the failure it was avoiding: a
registry entry can outlive the process that wrote it, so a report that treats presence as proof
shows a crashed session as live, and that is worse than one that says it cannot tell.

So the entry is corroborated rather than trusted, and the report says which check it ran. On Windows
that is presence plus identity: the pid must exist, and wherever the entry records a start time
it must equal the pid's. An entry with no recorded start time is confirmed on presence alone, an
overstatement in the first published wording that an automated review of pull request 76 caught
and that is corrected here in every place it appeared.
Confirmed against the machine before anything was built, rather than from documentation:
`134324400435518083` is 1787966443.6 epoch seconds, 3.7 seconds before that entry's own `startedAt`
and equal to the process start time the operating system reports, across all three live entries on
2026-08-28. The same check found the corpus's own shape unusable for a simpler route: the project directory
is not a function of the recorded working directory, since two projects are each reached from more
than one, and six of twenty-six distinct pairs disagree under the most permissive rule tried. So a
live session is placed by the store and then by the transcript beside it, and never by a transform.

**Pid reuse is undetected outside Windows.** `procStart`'s meaning on macOS and Linux is unverified
here, so those platforms check presence only, and `liveness_check()` says so on the page rather than
letting a reader assume the strong check everywhere. `test_a_pid_whose_start_time_disagrees_with_the_entry_is_reported_gone`
is the one test in this component that is skipped on five of the six CI cells.

**A session absent from the registry is reported ended**, which is right for a session that has
finished and unverified for one the registry never held. Every entry observed carried
`kind: "interactive"`; whether a background or cloud session registers at all is unverified, so a
running non-interactive session may be indistinguishable from an ended one. Stated here because the
report is otherwise silent about it.

Twenty-six mutations were run against the tests above and all twenty-six were killed, over a
baseline of twenty-eight green tests. They included the ones that matter most: treating registry
presence as liveness, dropping the pid-domain guard, no longer comparing `procStart`, reintroducing
`os.kill` on the Windows path, dropping the unattributed bucket, ignoring the project scope, and
filtering rows in the page's renderer while the API still returned them.

**That figure was true and read as more than it proved, which an independent verification then
demonstrated.** Mutating only the behaviours a test already claims to guard measures whether those
tests work; it says nothing about behaviour no test names. Asked the other question, the
verification found four such behaviours, three of them asserted in the code's own docstrings, each
surviving a fully green suite (the set now stands at thirty mutations, all thirty killed): the per-project `running`, `unverified`, and `ended` columns the page
renders beside the session count, which could all be forced to zero unnoticed; the duplicate-entry
tie-break in `live_sessions()`; the timestamp conversion in `_started_at()`, whose docstring gives
the reason it must not happen on the page; and the `UNATTRIBUTED` fallback on the stored-session
path, as opposed to the live one. All four were reproduced independently before being accepted, a
test was written for each, and all four now fail when the behaviour is broken. The first is the same
shape as the regression `feat-0054`'s verification found in the skills renderer: a figure correct in
the header and wrong in the table beside it.

## Bound worth stating

Every figure here was measured on Windows against one maintainer's corpus. CI runs three
operating systems by two Python versions, so five of six cells are unverified by any run behind
this matrix. `S-015`'s Given names an optional event source that does not exist yet, so `S-022`
is as strong as the current surface allows rather than as strong as the contract will eventually
require.
