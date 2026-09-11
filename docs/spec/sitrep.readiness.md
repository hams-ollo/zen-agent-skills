# sitrep: readiness

Go/no-go gate over [`sitrep.md`](sitrep.md) and its task decomposition, `feat-0066` to `feat-0071`,
run on 2026-09-11 with the `spec-plan-readiness` skill before any test or code was written. A ledger:
it records this run, and a later run is a new entry, not an edit.

## Run of 2026-09-11

```text
verdict: blocked
blocking_gaps:
  - source: both
    reason: >
      feat-0071 must wire .agents/hooks/sitrep-session-start.py into .codex/hooks.json and
      .opencode/plugins/zen-hooks.mjs, because tests/test_hooks.py
      (WiringConsistencyTests.test_every_hook_in_the_module_is_registered_everywhere) requires every
      hook in the module to be registered in all three distribution wirings. The spec's Non-Goals
      exclude "Session-start registration for any harness other than Claude Code". The two cannot
      both hold.
    required_resolution: >
      The author decides one of: (a) amend that Non-Goal to say the hook is wired into every harness
      the hooks module supports, as the module requires, while only Claude Code marks which prompts a
      person typed, so elsewhere the watermark never moves (S-040); or (b) amend the hooks module and
      tests/test_hooks.py to let a hook declare itself Claude Code only. Recommendation: (a). The
      Codex and opencode wirings are repository-scoped and reach only a repository that ships
      .agents/hooks/, which in practice is this kit, and the behaviour there degrades to a board with
      no watermark movement rather than to anything wrong.
scenario_to_test_map:
  - scenario: S-001, S-002, S-003, S-004, S-006
    recommended_layer: unit
    why: pure rules over task-file text and ordering.
  - scenario: S-005, S-007, S-010, S-014
    recommended_layer: integration (throwaway git repository)
    why: closed, tracked and dependency state are repository facts.
  - scenario: S-008, S-009, S-011, S-039
    recommended_layer: integration (throwaway git repository with worktrees and branches)
    why: every outcome is a fact about git state.
  - scenario: S-019
    recommended_layer: unit
    why: the lowest-tier rule is arithmetic over entries.
  - scenario: S-012, S-013, S-015, S-016, S-017, S-018, S-020
    recommended_layer: integration (throwaway git repository)
    why: tracked-ness and tracked test files are repository facts.
  - scenario: S-021, S-022, S-023, S-024, S-025, S-026, S-040
    recommended_layer: integration (temporary home, throwaway repository, synthetic transcripts)
    why: the watermark is state outside the repository read against transcripts.
  - scenario: S-028, S-033
    recommended_layer: unit
    why: truncation and the disjoint colour sets are pure functions.
  - scenario: S-034, S-035, S-036, S-037, S-038
    recommended_layer: integration (the command against a throwaway repository)
    why: outputs, writes, and the absence of network use are observable only by running it.
  - scenario: S-027, S-029, S-030, S-031, S-032
    recommended_layer: process (run the hook as the harness does, payload on stdin)
    why: the contract is what the harness receives, and tests/test_hooks.py already runs hooks this way.
task_to_scenario_map:
  - task: feat-0066
    scenarios: [S-001, S-002, S-003, S-004, S-005, S-006, S-007, S-010, S-014]
    notes: no dependency; the layer every other task reads.
  - task: feat-0067
    scenarios: [S-008, S-009, S-011, S-039]
    notes: base revision and integration branch are parameters here.
  - task: feat-0068
    scenarios: [S-012, S-013, S-015, S-016, S-017, S-018, S-019, S-020]
    notes: carries risk and rollback notes, for the .sitrep.json format.
  - task: feat-0069
    scenarios: [S-021, S-022, S-023, S-024, S-025, S-026, S-040]
    notes: carries risk and rollback notes, for the state format and the undocumented origin field.
  - task: feat-0070
    scenarios: [S-028, S-033, S-034, S-035, S-036, S-037, S-038]
    notes: carries risk and rollback notes, for the board document.
  - task: feat-0071
    scenarios: [S-027, S-029, S-030, S-031, S-032]
    notes: carries risk and rollback notes, and the blocking gap above.
```

**Coverage proof.** The six tasks list 9, 4, 8, 7, 7 and 5 scenarios, 40 in all, and the union is
`S-001` to `S-040` with no id listed twice, which is the spec's full set. The one gap is a contradiction
between the spec and the hooks module's own rule, not a missing mapping, so the scenario-to-test map is
given in full.

**What this authorises.** Nothing, until the gap is resolved and the gate is run again.
