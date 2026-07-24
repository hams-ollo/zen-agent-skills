# Changelog

Completed work for the Zen Starter Kit, newest first. This is the append-only ledger for the spec-driven task workflow: when a task in [`.tasks/`](.tasks/) is finished, its file moves to `.tasks/done/` and one dated line is added here referencing the task id.

---

## Task log

- [x] (2026-07-24) Blessed `fix-batch` and `reconcile-worktrees` as **shipped** after a live in-kit run: dispatched two parallel worktree-isolated agents via `fix-batch`, verified each against real diffs, and reconciled both into main via `reconcile-worktrees`. Status updated in `ROADMAP.md` and `docs/CATALOG.md`.
- [x] (2026-07-24) Closed `chore-0002`: aligned `docs/CATALOG.md` Tier C Content OS names with `ROADMAP.md` Epic C (executed via the `fix-batch` live run).
- [x] (2026-07-24) Closed `chore-0001`: fixed the README workflow-spine diagram order, removed the stale installer note, and unlinked a broken placeholder link (executed via the `fix-batch` live run).
- [x] (2026-07-24) Closed `feat-0006`: folded `reconcile-worktrees` into the kit (ported from `~/.claude/skills`, house-styled, wired into the `.tasks/` spine). Draft pending a live in-kit run before blessing.
- [x] (2026-07-24) Closed `feat-0005`: folded `fix-batch` into the kit (ported from `~/.claude/skills`, house-styled, portability-gated with a labeled Claude Code section, wired into the `.tasks/` spine). Draft pending a live in-kit run before blessing.
- [x] (2026-07-24) Blessed `pr-describe` as **shipped** after a first field-iteration against this kit's own working tree; status updated in `ROADMAP.md` and `docs/CATALOG.md`.
- [x] (2026-07-24) Closed `feat-0004`: iterated `pr-describe` from dogfooding, added a working-tree fallback so it describes uncommitted work on the default branch instead of dead-ending when the branch is not ahead of base.
- [x] (2026-07-24) Closed `feat-0003`: drafted the first version of the `pr-describe` skill (PR body + changelog entry from a branch's diff; draft-only, never touches GitHub; changelog format by inspection; branch-vs-merge-base range). Lints clean via `scripts/validate-skills.py`. Marked draft in `ROADMAP.md`/`docs/CATALOG.md`, pending field iteration before it is blessed.
- [x] (2026-07-24) Blessed `project-bootstrap` as **shipped** after review; status updated in `ROADMAP.md` and `docs/CATALOG.md`.
- [x] (2026-07-24) Closed `feat-0002`: iterated `project-bootstrap` with a swappable house code-style layer under `templates/` (ruff, prettier, eslint, editorconfig + doc), folding in the four settled design decisions. Never-clobber preserved. Both validators green.
- [x] (2026-07-23) Closed `feat-0001`: drafted the first version of the `project-bootstrap` skill. Lints clean via `scripts/validate-skills.py`. Marked draft in `ROADMAP.md`, pending field iteration before it is blessed as shipped.

### Seeded provenance (predates this tracker)

The following shipped during the kit's initial build, before this tracking system existed. Recorded here for a complete ledger.

- (2026-07-23) Established the tracking system for this repo (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`), dogfooding `init-worktracking` at team tier.
- (2026-07-23) Shipped the installer and adapter tooling: `scripts/install.py`, `scripts/build-adapters.py`, `scripts/validate-skills.py`.
- (2026-07-23) Added the `new-task` authoring skill.
- (2026-07-23) Hardened `init-worktracking` (seven improvements) and stood up the kit repository.
