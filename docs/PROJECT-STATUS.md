# Project status

This is a partner-facing status update on the Zen Starter Kit as of 2026-07-24.

## Where things stand

The kit is a working, cross-harness library of agent skills rather than a product prototype. Its core workflow is in place: project bootstrap, work tracking, specification authoring, task authoring, test authoring, parallel agent execution, specification conformance auditing, worktree reconciliation, review, documentation, handoffs, and pull request preparation.

The repository also uses its own tracking and validation process, and now maintains behavioral specifications under [`docs/spec/`](spec/) plus its first test suite under [`tests/`](../tests/). That gives the project a practical test bed for the workflows it distributes.

## What changed

The major development is the contract-driven delivery spine, six skills shipped on 2026-07-24 that move the kit from "agents write code" to "agents work against a written contract":

- `spec-author` drafts a persistent behavioral specification from a raw idea and stops for human approval before any decomposition.
- `spec-quality` is the report-only lens that keeps those specifications observable, grounded, and free of implementation planning.
- `spec-plan-readiness` is a deterministic go/no-go gate that blocks tests, code, and delegation until an approved specification and an ordered plan exist.
- `test-quality` is the report-only lens for choosing the lowest faithful test layer and a real observable assertion.
- `test-author` derives runnable tests from an approved specification's scenarios, each traceable to the scenario it protects.
- `spec-conformance` audits an implementation against its specification into a Conformed, Diverged, or Not-built matrix.

Each was dogfooded on real in-kit work before being blessed, per the kit's contribution bar. Four were folded in from `repoprompt-workflows` (Balarama Bosch, MIT) and house-styled; `spec-author` and `test-author` were authored in the kit.

Earlier in the same cycle, the README became a complete adoption guide, an architecture guide documented the single-source skill model, and `doc-author`, `doc-revise`, `agent-handoff`, and `human-handoff` shipped after real use.

## What is open

There is no immediate implementation blocker. The next roadmap item is `verifier-agent`: independent verification of an implementation against its approved specification and task acceptance criteria, composing `spec-conformance` and producing structured pass, fail, or blocked evidence before reconciliation. It is the last core skill of the delivery loop. After it, `user-testing` covers the user-facing work that automated tests and contract conformance miss, and `doc-sync` detects documentation drift.

`ci-scaffold` and `release-cut` remain intentionally on hold until they have been needed and used twice in real work. That keeps the library focused on proven workflows rather than speculative coverage.

The standing decision is prioritization: choose the next recurring operational problem worth turning into a skill, then validate it through use before adding it to the shipped catalog.

## Next steps and ownership

The maintainer should keep dogfooding the shipped skills on real projects, record any friction as a task, and update the relevant skill before broadening its scope. Contributors should use the existing task workflow and validation commands before proposing new skills or integrations.

For technical detail, see the [architecture guide](ARCHITECTURE.md), [skill catalog](CATALOG.md), and [roadmap](../ROADMAP.md).
