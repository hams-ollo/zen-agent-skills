---
id: chore-0004
title: Align the reader-facing docs with the shipped Epic B spec/verify spine
type: chore
status: done
priority: P1
parent: "ROADMAP Epic B: contract-driven delivery"
depends_on: []
touched_files:
  - README.md
  - AGENTS.md
  - docs/CATALOG.md
  - docs/PROJECT-STATUS.md
  - docs/PLATFORM-PITCH.md
  - docs/ARCHITECTURE.md
  - docs/GETTING-STARTED.md
created: 2026-07-24
---

## Problem

Six spine skills shipped on 2026-07-24 (`spec-quality`, `spec-author`, `spec-plan-readiness`,
`test-quality`, `spec-conformance`, `test-author`), and the kit introduced two new first-class
artifact directories along the way: [`docs/spec/`](../docs/spec/) for behavioral contracts and
[`tests/`](../tests/) for the kit's first test suite. [`ROADMAP.md`](../ROADMAP.md) and
[`CHANGELOG.md`](../CHANGELOG.md) record all of this correctly, but the reader-facing documentation
still describes a pre-Epic-B world, and in places contradicts itself:

- [`README.md`](../README.md) never mentions the spine. Its capability sentence omits specification,
  testing, and verification, and its "How the workflow fits together" Mermaid stops at the old
  six-skill chain (`project-bootstrap` through `pr-describe`), so the most visible architecture
  diagram in the repository is stale.
- [`docs/CATALOG.md`](../docs/CATALOG.md) contradicts itself: it lists `test-author` as shipped in the
  spine table and *again* as `planned` in Tier B; and two shipped skills are still described as being
  composed by "the planned `spec-author`" and "the planned `test-author`", both of which shipped.
- [`docs/PROJECT-STATUS.md`](../docs/PROJECT-STATUS.md) is dated the same day as the spine work yet
  reports the previous shipping wave and names `ci-scaffold`/`release-cut` as the next work.
- [`docs/PLATFORM-PITCH.md`](../docs/PLATFORM-PITCH.md) lists six shipped skills under "What is
  evolving next" and carries a disclaimer that they are "not claims that the current release already
  provides them", which is now inaccurate.
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) and [`AGENTS.md`](../AGENTS.md) do not mention
  `docs/spec/` or `tests/` as repository artifacts.

Documentation that misreports what shipped is worse than missing documentation: it teaches an adopter
(and any agent reading `AGENTS.md`) the wrong model of the kit.

## Scope

**In scope:** a documentation-only consistency pass across the seven `touched_files`, bringing each
into line with the shipped state recorded in `ROADMAP.md` and `CHANGELOG.md`:

- `README.md`: add specification/testing/verification to the capability sentence; extend the spine
  Mermaid with the spec and verify stages; add `docs/PROJECT-STATUS.md`, `docs/PLATFORM-PITCH.md`,
  and `docs/spec/` to "What's included" and the repository-layout table.
- `docs/CATALOG.md`: correct the "all four ... in progress" framing to match the six listed skills;
  drop the stale duplicate `test-author | planned` Tier B row; update the two "the planned X"
  cross-references now that both compose-partners shipped.
- `docs/PROJECT-STATUS.md`: rewrite "Where things stand", "What changed", and "What is open" to
  report the spine and to name `verifier-agent`/`user-testing` as the next work.
- `docs/PLATFORM-PITCH.md`: move the six shipped spine skills into "What is available today", narrow
  the roadmap disclaimer to what is genuinely still roadmap, and add the spec and verify stages to
  the delivery-spine diagram.
- `docs/ARCHITECTURE.md`: record `docs/spec/` and `tests/` as first-class artifacts.
- `docs/GETTING-STARTED.md`: surface the spine in the collaboration loop and the light-touch menu so
  a founder has an on-ramp to spec-first work.
- `AGENTS.md`: add `docs/spec/` and `tests/` to the section 2 layout table.

**Out of scope:** building `verifier-agent` (ROADMAP Epic B #7, its own feature task) and adding it
to any doc as shipped or draft; it is still unbuilt, so it stays at ROADMAP altitude in this pass.
No skill body under `.agents/skills/` changes. No change to `ROADMAP.md` or `CHANGELOG.md` beyond
this task's own closing line, since both are already current.

## Implementation notes

- Use the [`doc-revise`](../.agents/skills/doc-revise/SKILL.md) skill: revise in place, preserve each
  document's existing voice and audience, and ground every claim in the repository rather than
  restating the roadmap.
- Each document has a distinct audience and the rewrite should respect it: `README.md` is for
  adopters, `docs/GETTING-STARTED.md` is plain-language for founders, `docs/PLATFORM-PITCH.md` is a
  vision pitch, `docs/PROJECT-STATUS.md` is a partner-facing snapshot, and `AGENTS.md`/
  `docs/ARCHITECTURE.md` are for agents and maintainers.
- Follow [`.agents/rules/house-style.md`](../.agents/rules/house-style.md): sentence-case headings,
  no em-dashes, named sources, relative markdown links, Mermaid for diagrams.
- `ROADMAP.md` is authoritative when documents disagree (per `AGENTS.md` section 2).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `python scripts/validate-skills.py` exits 0 (no skill body was disturbed by the pass).
- [x] `python .tasks/validate.py --strict` exits 0 with this task present.
- [x] No document describes `spec-quality`, `spec-author`, `spec-plan-readiness`, `test-quality`,
      `spec-conformance`, or `test-author` as planned, evolving, or not yet provided.
- [x] `docs/CATALOG.md` lists `test-author` exactly once.
- [x] No document claims `verifier-agent` is shipped or drafted.
- [x] `README.md` and `docs/PLATFORM-PITCH.md` spine diagrams both include a specification stage and
      a verification stage.
- [x] `AGENTS.md` and `docs/ARCHITECTURE.md` both name `docs/spec/` and `tests/`.
- [x] Every relative link added in this pass resolves to a file that exists.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
