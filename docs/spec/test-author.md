---
title: test-author
status: approved
---

# test-author

Behavioral contract for the planned `test-author` skill (ROADMAP Epic B item 5). Drafted 2026-07-24
by the `spec-author` skill as its first in-kit dogfood, and self-checked to `ready` with the
`spec-quality` lens.

## Problem

The spine has [`test-quality`](../../.agents/skills/test-quality/SKILL.md), a lens for judging whether
a test is worth keeping, but nothing that derives tests from an approved spec. After an agent
implements a feature there is no skill that turns the spec's scenarios into acceptance tests, or that
adds characterization tests to legacy code with no coverage before it is changed. Test evidence is not
part of the core workflow, so implementations reach reconciliation with no derived proof that they
satisfy the contract.

## Goals

1. Derive acceptance tests from an approved spec's scenarios and a task's acceptance criteria, one
   faithful test per behavior, each traceable to the scenario id it covers.
2. Compose the `test-quality` lens to choose the layer and oracle for each test and to avoid
   low-value tests.
3. Support characterization tests for legacy code with no coverage, pinning current observable
   behavior before a change.

## Non-Goals

- Judging test quality in the abstract. That is the `test-quality` lens.
- Implementing the feature under test or fixing the bug.
- Authoring the spec (`spec-author`) or gating readiness (`spec-plan-readiness`).
- Running the full CI suite or managing worktrees.

## Constraints

- The skill composes `test-quality` rather than restating its rules inline.
- It uses the repository's existing test framework and taxonomy; it does not impose a new one.
- Every derived test traces back to the spec scenario id it covers.
- In the spine, the skill runs after implementation and before reconciliation, so its test evidence
  is available when changes are reconciled.
- Mode is inferred from the inputs: an approved spec present means acceptance mode; legacy code with
  no spec means characterization mode. The user may override the inferred mode.
- Characterization tests live alongside the repository's existing tests and are labeled as
  characterization in the test name or an adjacent comment.

## Scenarios

### Scenario S-001: derive acceptance tests from an approved spec

- **Given** an approved spec with scenarios S-001..S-00N, the task's acceptance criteria, and an
  implementation to test
- **When** test-author runs in acceptance mode
- **Then** it produces at least one test per scenario, each tagged with the scenario id it covers,
  and emits a coverage report listing scenarios covered and scenarios omitted, each omission with a
  stated reason.

### Scenario S-002: choose layer and oracle via test-quality

- **Given** a single scenario to cover
- **When** test-author derives its test
- **Then** it selects the lowest faithful test layer per the `test-quality` lens and asserts an exact
  observable outcome (a return value, state change, error, or side effect), not a "does not crash"
  check, and records the layer and oracle it chose.

### Scenario S-003: characterization tests for uncovered legacy code

- **Given** a code area with no existing tests and no spec
- **When** test-author runs in characterization mode
- **Then** it writes tests that assert the current observable behavior and labels them as
  characterization tests.

### Scenario S-004: bug-fix regression proven to fail first

- **Given** a bug-fix task
- **When** test-author derives the regression test
- **Then** it confirms the test fails against the pre-fix behavior and reproduces the reported
  symptom before the test is treated as trustworthy.

### Scenario S-005: no faithful test possible

- **Given** a scenario that cannot be faithfully tested at any available layer (for example it needs
  live credentials or a rendered UI)
- **When** test-author runs
- **Then** it reports the gap and classifies it as smoke, diagnostic, or deferred, and does not write
  a low-value passing test in its place.

## Proposed Surface

| Element | Detail |
|---|---|
| Inputs | approved spec path, implementation scope, task acceptance criteria |
| Mode | `acceptance` (spec present) or `characterization` (legacy code, no spec), inferred with user override |
| Output | test files in the repository's own framework, each tagged with the covering scenario id |
| Coverage report | scenarios covered, and scenarios omitted each with a stated reason |

## Open Questions

None.
