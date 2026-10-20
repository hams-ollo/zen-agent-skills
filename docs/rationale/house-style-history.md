# House style module: history

The record behind two passages of the house-style module,
[`.agents/rules/house-style.md`](../../.agents/rules/house-style.md), moved here verbatim on
2026-10-20 by the kit refresh ([audit](../reviews/2026-10-kit-refresh-audit.md), finding 1.3). The
module keeps each rule; this file keeps the incidents that produced them.

## Why the row-count rule exists

Four instances in this repository, each invisible to every gate: `ROADMAP.md` claiming eight autonomy rules and three held candidates against nine and four, `chore-0036` inheriting a claim of ten templates out of nine, and two in `docs/spec/README.md`, one fixed by `chore-0056` and one still open as `chore-0057`. The same reasoning is why `bug-0037` moved conformance-matrix citations off line numbers: a pointer that encodes position drifts when anything above it moves.

## How the universal scope came to be enforced

**Scope: universal.** Every skill in this kit references this module, and `validate-skills.py` fails when one does not. A lens reaches an agent only through a skill that points at it, so a universal lens that some skills never name is silently inert for exactly those skills, and an adopter who rewrites it changes nothing there. The rule was stated in `AGENTS.md` and enforced by nothing until `feat-0064`; it held at 22 of 22 on inspection, which is discipline rather than a guarantee.
