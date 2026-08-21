---
name: test-author
description: Use after an implementation to derive runnable tests from an approved spec's Given/When/Then scenarios and a task's acceptance criteria, one faithful test per scenario tagged with its S-NNN id. Stops rather than deriving tests from a spec whose status is not approved. Discovers and matches the repo's existing test framework, composes the test-quality lens to choose the lowest faithful layer and an exact-outcome oracle, supports characterization tests for legacy code with no coverage, and reports coverage gaps instead of writing low-value passing tests. Distinct from test-quality (the lens it composes, which judges test design), spec-conformance (audits code against a spec), and fix-batch (runs tests). It writes tests; it never edits production code.
license: MIT
---

# test-author

Turn an approved spec into runnable, traceable tests. This is the only spine skill that actually
authors tests: [`test-quality`](../test-quality/SKILL.md) judges test design, [`spec-conformance`](../spec-conformance/SKILL.md)
audits whether code matches a spec, and [`fix-batch`](../fix-batch/SKILL.md) runs whatever tests
exist. `test-author` is what produces them, from the contract, so that a failing test points back to
the exact scenario it protects.

It runs after implementation and before reconciliation, so test evidence is available when changes
are verified and landed. It composes two lenses by reference and does not restate their rules:
[`spec-quality`](../spec-quality/SKILL.md) gates the input spec, and [`test-quality`](../test-quality/SKILL.md)
governs every layer and oracle choice.

## When to use

- An implementation exists (or a surface is defined) and its approved spec's scenarios need tests.
- Legacy code has no coverage and needs its current behavior pinned before a change (characterization).
- A bug fix needs a regression test that provably fails on the buggy behavior.

## When not to use

- You only need to judge whether an existing test is worth keeping: use [`test-quality`](../test-quality/SKILL.md).
- You need to check whether the code matches the spec by inspection, not by writing tests: use
  [`spec-conformance`](../spec-conformance/SKILL.md).
- No spec and no legacy code to characterize: there is nothing to derive tests from yet.

## Modes

- **Acceptance** (an approved spec is present): derive tests from the spec's scenarios.
- **Characterization** (legacy code, no spec): assert the current observable behavior to pin it
  before a change, and label the tests as characterization in the name or an adjacent comment.

Infer the mode from the inputs, and let the user override it.

## Inputs

Required (acceptance mode):

- **Approved spec**: a readable spec with `status: approved` and Given/When/Then scenarios
  carrying stable `S-NNN` ids.

Required (characterization mode):

- **Code scope**: the legacy area to pin.

Optional:

- **Task acceptance criteria**: the mechanical criteria of the task being verified.
- **Implementation scope**: what to test against; defaults to the working tree.

## Procedure

### 1. Read the spec, refuse it if it is not approved, and gate it with spec-quality

Read the spec. **Refuse an unapproved spec.** If `status` is not `approved`, stop and say so. Tests
are the most durable form an unapproved contract can take: a draft spec can still be edited or
abandoned, while a suite derived from it becomes what later work is measured against, and
[`spec-conformance`](../spec-conformance/SKILL.md) and [`verifier-agent`](../verifier-agent/SKILL.md)
will cite those tests as evidence. Well-formedness is not approval, so the next check does not stand
in for this one: `spec-quality` returns `ready` for a draft that is answerable, which is exactly the
state a spec sits in while it waits for a human.

Then apply the [`spec-quality`](../spec-quality/SKILL.md) lens to it. If the verdict would be
`needs_revision`, stop without writing tests and report the exact spec gaps that must be fixed
first: you cannot derive faithful tests from an untestable contract. Then extract every scenario
(each `S-NNN`), the Proposed Surface (what you test against), and the Constraints that affect test
design (data format, naming, thresholds). If the spec has no scenarios, stop and say so.

Both gates are acceptance-mode gates. Characterization mode is exempt from both, because it exists
for code with no contract at all: there is no spec to gate and none to approve, so skip to Step 2 and
derive the oracle from the code's current observable behavior instead.

### 2. Discover the repository's test infrastructure, and match it

Before writing anything, learn how this repo already tests, and match it. Do not invent a parallel
framework. Find:

- **Framework and runner**: what framework, and the exact command that runs the tests.
- **Layout and naming**: where tests live, how they mirror source, and the file, suite, and method
  naming patterns.
- **Assertion and fixture style**: the assertion API in use, and how test data and setup are built.
- **Prior art**: read two or three existing tests for style and copy it.

If the repo has no test infrastructure at all, do not build one silently. Recommend a framework that
fits the language, propose the minimal layout, write one bootstrap test to prove the runner works,
and only then continue. If you need a helper or fixture the repo lacks, suggest it rather than
building a competing harness.

### 3. Map each scenario to tests, composing test-quality

For each scenario, choose the test design by composing [`test-quality`](../test-quality/SKILL.md):
name the plausible defect, pick the **lowest faithful layer** that still reproduces the risk, and
define an **exact observable oracle** (a return value, state change, error, side effect, or persisted
format), never a "does not crash" or field-presence check. Record the layer and oracle you chose and
why.

Map Given to setup, When to the action, and Then to assertions. Produce at least one test per
scenario, splitting into multiple tests when a scenario covers independent behaviors. Tag every test
with the scenario id it covers (for example a comment `Scenario S-003: ...`), so coverage is
traceable back to the contract. Cover every Proposed Surface element and the edge and error paths the
scenarios describe, not only happy paths.

### 4. Write the tests, and never touch production code

Write the tests in the repo's discovered conventions: its imports, naming, assertion style, and
setup or teardown. Leave no `TODO` placeholders; write the real test or omit the scenario with a
reason. Do not modify production code to make a test pass. If a test reveals a real feature bug,
report it as a finding; do not paper over it.

Two special cases:

- **Bug fix**: before trusting a regression test, confirm it fails against the pre-fix behavior and
  reproduces the reported symptom. A test that passes on the buggy code protects nothing.
- **Characterization**: assert the behavior the code exhibits today, and label the tests as
  characterization so a later reader knows they pin current behavior rather than a desired contract.

### 5. Verify, then report coverage

Run the tests with the discovered command. Compile or collect them first, then run. If the feature is
not yet implemented, contract tests may fail at runtime: that is expected, document it. Fix failures
that stem from test bugs; report failures that stem from feature bugs.

Then summarize as evidence for reconciliation: scenarios in the spec, tests written, scenarios
covered, and scenarios omitted each with a stated reason. When a scenario cannot be faithfully tested
at any available layer (it needs live credentials, a rendered UI, or similar), do not write a
low-value passing test in its place: report the gap and classify it as smoke, diagnostic, or
deferred.

## Notes

- The stable scenario ids are what make the whole spine traceable: [`spec-plan-readiness`](../spec-plan-readiness/SKILL.md)
  maps scenarios to test layers, and [`spec-conformance`](../spec-conformance/SKILL.md) later audits
  the same ids. Keep the tags exact so those skills line up with your tests.
- Test evidence is the point. A green suite that asserts nothing observable is worse than an honest
  "this scenario is not faithfully testable here," because it hides the gap.

## Conventions

Follow the repo's house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)):
sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a
swappable default; a downstream adopter may replace it without touching this skill.
