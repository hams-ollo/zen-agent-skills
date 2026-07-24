# Changelog

Completed work for the Zen Starter Kit, newest first. This is the append-only ledger for the spec-driven task workflow: when a task in [`.tasks/`](.tasks/) is finished, its file moves to `.tasks/done/` and one dated line is added here referencing the task id.

---

## Task log

- [x] (2026-07-23) Closed `feat-0001`: drafted the first version of the `project-bootstrap` skill. Lints clean via `scripts/validate-skills.py`. Marked draft in `ROADMAP.md`, pending field iteration before it is blessed as shipped.

### Seeded provenance (predates this tracker)

The following shipped during the kit's initial build, before this tracking system existed. Recorded here for a complete ledger.

- (2026-07-23) Established the tracking system for this repo (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`), dogfooding `init-worktracking` at team tier.
- (2026-07-23) Shipped the installer and adapter tooling: `scripts/install.py`, `scripts/build-adapters.py`, `scripts/validate-skills.py`.
- (2026-07-23) Added the `new-task` authoring skill.
- (2026-07-23) Hardened `init-worktracking` (seven improvements) and stood up the kit repository.
