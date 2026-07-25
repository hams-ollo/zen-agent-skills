# Project status

This is a partner-facing status update on the Zen Starter Kit as of 2026-07-25.

## Where things stand

The kit is a working, cross-harness library of agent skills rather than a product prototype. Its core workflow is in place: project bootstrap, work tracking, specification authoring, task authoring, test authoring, parallel agent execution, specification conformance auditing, worktree reconciliation, review, documentation, handoffs, and pull request preparation.

The repository also uses its own tracking and validation process, and now maintains behavioral specifications under [`docs/spec/`](spec/) plus its first test suite under [`tests/`](../tests/). That gives the project a practical test bed for the workflows it distributes.

## What changed

The major development is the contract-driven delivery spine, eight skills that move the kit from "agents write code" to "agents work against a written contract". Six shipped on 2026-07-24:

- `spec-author` drafts a persistent behavioral specification from a raw idea and stops for human approval before any decomposition.
- `spec-quality` is the report-only lens that keeps those specifications observable, grounded, and free of implementation planning.
- `spec-plan-readiness` is a deterministic go/no-go gate that blocks tests, code, and delegation until an approved specification and an ordered plan exist.
- `test-quality` is the report-only lens for choosing the lowest faithful test layer and a real observable assertion.
- `test-author` derives runnable tests from an approved specification's scenarios, each traceable to the scenario it protects.
- `spec-conformance` audits an implementation against its specification into a Conformed, Diverged, or Not-built matrix.

Two more followed. `verifier-agent` shipped on 2026-07-24 and combines those signals into one deterministic verdict before anything lands, and `doc-sync` shipped on 2026-07-25 and detects which documents a change invalidated.

Each was dogfooded on real in-kit work before being blessed, per the kit's contribution bar. Four were folded in from `repoprompt-workflows` (Balarama Bosch, MIT) and house-styled; `spec-author`, `test-author`, `verifier-agent`, and `doc-sync` were authored in the kit.

Earlier in the same cycle, the README became a complete adoption guide, an architecture guide documented the single-source skill model, and `doc-author`, `doc-revise`, `agent-handoff`, and `human-handoff` shipped after real use.

## What is open

There is no immediate implementation blocker. `verifier-agent` shipped on 2026-07-24, completing the core delivery loop: an idea becomes a specification, and nothing lands until an independent verification returns a verdict with evidence. Its dogfood found a real defect in an artifact the kit had already audited and tested, which is the clearest evidence so far that the spine catches things a green test suite does not.

`user-testing` remains the main open thread, covering the user-facing work that automated tests and contract conformance both miss. Separately, the first kit-wide review pass ran on 2026-07-25 and read all nineteen skills. It found a real cross-repository portability defect, seven stale status claims including three skills that called themselves both draft and shipped, and a linter blind to all of it. Those were fixed the same day by parallel agents, and the checks that catch them now run as a command. That pass deliberately reviewed structure and cross-references rather than exercising behavior, so the harder half is still open: every skill was blessed on a single real use, and whole branches remain unexercised.

`ci-scaffold` and `release-cut` remain intentionally on hold until they have been needed and used twice in real work. That keeps the library focused on proven workflows rather than speculative coverage.

The standing decision is prioritization: choose the next recurring operational problem worth turning into a skill, then validate it through use before adding it to the shipped catalog.

## Next steps and ownership

The maintainer should keep dogfooding the shipped skills on real projects, record any friction as a task, and update the relevant skill before broadening its scope. Contributors should use the existing task workflow and validation commands before proposing new skills or integrations.

For technical detail, see the [architecture guide](ARCHITECTURE.md), [skill catalog](CATALOG.md), and [roadmap](../ROADMAP.md).
