# Roadmap

**Status:** living document | **Last updated:** 2026-07-24

The builder-facing execution plan: which skills get built and in what order. For the reader-facing narrative of what the kit offers, see [`docs/CATALOG.md`](docs/CATALOG.md). For atomic work in flight, see [`.tasks/`](.tasks/); for finished work, [`CHANGELOG.md`](CHANGELOG.md). Altitude model in [`AGENTS.md`](AGENTS.md) section 3.

Seeded 2026-07-23 from `docs/CATALOG.md`. Features here stay at the 10,000-foot layer until it is their turn; only then are they decomposed into `.tasks/` files.

---

## Current state

The kit exists and dogfoods itself. Shipped and verified:

- **`init-worktracking`** (hardened): tiered footprint, idempotent re-runs, seed-by-inspection, shipped `validate.py`, migration dry-run, decoupled house-style module.
- **`new-task`**: gold-standard task authoring, the upstream that feeds `fix-batch`.
- **`project-bootstrap`** (blessed 2026-07-24): the umbrella front door; stack-aware baseline (gitignore, editorconfig, linter/formatter from a swappable house code-style layer, license, README stub) that then calls `init-worktracking`.
- **`pr-describe`** (blessed 2026-07-24): the closing bookend; drafts a PR body and a changelog entry from a branch's diff (or the working tree), in the target repo's own format, without touching GitHub.
- **Tooling**: `scripts/install.py` (cross-platform installer), `build-adapters.py` (Cursor/VS Code adapters), `validate-skills.py` (kit-level lint).
- **This tracking system**: `AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`.

The parallel-execution back half of the spine has been folded in from the author's global skill set (`~/.claude/skills`):

- **`fix-batch`** and **`reconcile-worktrees`** (blessed 2026-07-24): ported into the kit (`feat-0005`, `feat-0006`), adapted to house style, portability-gated, and wired into the `.tasks/` spine. Blessed after a live in-kit run dispatched two parallel worktree agents (`chore-0001`, `chore-0002`) and reconciled them into main.

---

## Forward plan

Ordered by effort-to-value. Each item is one skill (a Feature). Strike through when shipped.

### Epic A: broadly shareable (the public kit)

1. ~~**`project-bootstrap`.** The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter, license, README stub) that then calls `init-worktracking`.~~ **Shipped** (`feat-0001` draft, `feat-0002` house code-style layer; blessed 2026-07-24).
2. ~~**`pr-describe`.** Draft a PR body and changelog entry from a branch's diff, in the target repo's own changelog format (draft-only, never touches GitHub).~~ **Shipped** (`feat-0003` draft, `feat-0004` working-tree fallback from field iteration; blessed 2026-07-24).
3. ~~**`code-review`.** House-style review with an explicit rubric and severities, composing the swappable [`review-quality`](.agents/rules/review-quality.md) lens (moonray's quality-lens pattern).~~ **Shipped** (`feat-0007`; blessed 2026-07-24 after dogfooding).
4. **`ci-scaffold`** (hold until used twice). Generate CI (lint + test + build + release) matched to the detected stack.
5. **`release-cut`** (hold until used twice). Version bump, changelog roll-up, tag, notes.
6. **Fold in `doc-author` / `doc-revise`** from `zen-solutions-studio`. **Draft (pending dogfood)** (`feat-0011`, `feat-0012`; ported and house-styled 2026-07-24; blessing awaits one real in-kit dogfood use each plus sign-off).
7. **Fold in `agent-handoff` / `human-handoff`** (already portable by design). **Draft (pending dogfood)** (`feat-0009`, `feat-0010`; ported and house-styled 2026-07-24; blessing awaits one real in-kit dogfood use each plus sign-off).

### Epic B: semi-scalable (teams and clients)

8. **`repo-explainer`.** A "start here" guided tour of an unfamiliar codebase.
9. **`sop-drafter`.** Turn a described workflow into a documented SOP.
10. **`security-audit`.** Repeatable dependency and secret scan with a written summary.
11. **`test-author`.** Characterization tests for legacy code with no coverage.
12. **`adr`.** Architecture decision records / decision log.

### Epic C: personal (stays OUT of the shared kit)

The Content OS pipeline (`produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`) stays in `zen-solutions-studio` as portfolio demos, not plug-and-play kit skills.

---

## Out of scope by design

- No database or service dependency anywhere in the kit. Everything is markdown, `SKILL.md`, and stdlib Python. Portability is the whole point.
- No skill ships to the kit cold. A skill is drafted, used on real work, iterated, then blessed. Speculative skills stay at this roadmap altitude, not in `.agents/skills/`.
