# Project status

This is a partner-facing status update on the Zen Starter Kit as of 2026-07-27.

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

`user-testing` remains the main open thread, covering the user-facing work that automated tests and contract conformance both miss.

Separately, two kit-wide review passes have now run over all nineteen skills, and the second one
turned into the largest single day of work the kit has had.

The first pass, on 2026-07-25, reviewed structure and cross-references. It found a real
cross-repository portability defect, seven stale status claims including three skills that called
themselves both draft and shipped, and a linter blind to all of it. Those were fixed the same day by
parallel agents.

The second, on 2026-07-27, reviewed what each skill's procedure actually does when run, and found
two defects that would have cost an adopter real work. The installer was shipping the skills without
the rules module they compose, so the review skill arrived with no rubric at all. And the step that
brings parallel agents' work back into the main branch could not see files an agent had newly
created, so a batch whose output was new files would have landed nothing while reporting success.
Both are fixed, both now fail a command rather than waiting for someone to notice, and the second was
confirmed against a real three-agent run where all three patches were empty.

That day then closed everything the review surfaced. Every kit script now has an approved behavioral
contract and a conformance audit, where three days earlier only one did. The three hardest paths
through the delivery spine, which had never once run on real work, were each exercised against a
genuine trigger and recorded. The review skill was renamed to `house-review`, since its old name
collided with a command the harness itself ships. The test suite went from eighteen tests to
forty-eight. The backlog is empty.

The pattern worth carrying is unglamorous and consistent: the reading passes found structure
problems, and the running passes found the defects. Nothing that would actually have broken for a
user was found by review alone. Each was found by running the thing against reality, and in several
cases against conditions this repository cannot itself produce, which is why one of the day's runs
was deliberately staged against an unrelated project with real build dependencies.

`ci-scaffold` and `release-cut` remain intentionally on hold until they have been needed and used twice in real work. That keeps the library focused on proven workflows rather than speculative coverage.

The standing decision is prioritization: choose the next recurring operational problem worth turning into a skill, then validate it through use before adding it to the shipped catalog.

## Next steps and ownership

The maintainer should keep dogfooding the shipped skills on real projects, record any friction as a task, and update the relevant skill before broadening its scope. Contributors should use the existing task workflow and validation commands before proposing new skills or integrations.

For technical detail, see the [architecture guide](ARCHITECTURE.md), [skill catalog](CATALOG.md), and [roadmap](../ROADMAP.md).
