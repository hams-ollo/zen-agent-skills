# Project status

This is a partner-facing status update on the Zen Starter Kit as of 2026-07-24.

## Where things stand

The kit is a working, cross-harness library of agent skills rather than a product prototype. Its core workflow is in place: project bootstrap, work tracking, task authoring, parallel agent execution, worktree reconciliation, review, documentation, handoffs, and pull request preparation.

The repository also uses its own tracking and validation process. That gives the project a practical test bed for the workflows it distributes.

## What changed

- The README was expanded into a complete adoption guide with installation, integration, validation, and troubleshooting instructions.
- An architecture guide now documents the single-source skill model, distribution tooling, governance, and release flow.
- Four skills have been used on real work and are now shipped: `doc-author`, `doc-revise`, `agent-handoff`, and `human-handoff`.
- The catalog and roadmap now distinguish shipped skills from the genuinely planned backlog.

## What is open

There is no immediate implementation blocker. The next roadmap items, `ci-scaffold` and `release-cut`, are intentionally on hold until they have been needed and used twice in real work. That keeps the library focused on proven workflows rather than speculative coverage.

The remaining decision is prioritization: choose the next recurring operational problem worth turning into a skill, then validate it through use before adding it to the shipped catalog.

## Next steps and ownership

The maintainer should keep dogfooding the shipped skills on real projects, record any friction as a task, and update the relevant skill before broadening its scope. Contributors should use the existing task workflow and validation commands before proposing new skills or integrations.

For technical detail, see the [architecture guide](ARCHITECTURE.md), [skill catalog](CATALOG.md), and [roadmap](../ROADMAP.md).
