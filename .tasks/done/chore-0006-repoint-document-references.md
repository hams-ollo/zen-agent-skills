---
id: chore-0006
title: Repoint the three dangling `document` references at doc-sync (doc-sync apply run)
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B #9: doc-sync"
depends_on: [feat-0020]
touched_files:
  - .agents/skills/spec-conformance/SKILL.md
  - .agents/skills/spec-quality/SKILL.md
created: 2026-07-25
---

## Problem

Two shipped skills cross-reference a `document` skill that has never existed in this kit. The
[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) dry-run dogfood surfaced all three occurrences as
`grounded` findings, evidenced by the absence of any `.agents/skills/document/` directory:

| Finding | Location | Text |
|---|---|---|
| D-001 | `.agents/skills/spec-conformance/SKILL.md:45` | "Do not judge spec well-formedness (`spec-quality`) or doc drift (`document`)." |
| D-002 | `.agents/skills/spec-conformance/SKILL.md:3` | frontmatter description: "distinct from spec-quality (spec well-formedness) and document (doc-vs-code drift)" |
| D-003 | `.agents/skills/spec-quality/SKILL.md:51` | "use `spec-conformance` for that, or `document` for doc-vs-code drift." |

They were left in place deliberately through `feat-0020` so the dogfood had a known-answer target.
With `doc-sync` shipped, the referent now exists and the references should point at it.

This task doubles as the first exercise of `doc-sync`'s apply path (S-003, S-011, S-014), which was
specified but unexercised when the skill was blessed as a draft.

## Scope

**In scope:** apply findings D-001, D-002, and D-003 to the two named files, repointing each
`document` reference at `doc-sync`, composing [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md)
for the edit itself. Record the audit trail the apply path requires.

**Out of scope:** the other nine findings from the same dry run (D-004 through D-012), which stay
reported and unapplied; any other edit to the two files; changing `doc-author` or `doc-revise`.

## Implementation notes

- The three references are stylistically different: two are backticked inline, one is an unbackticked
  word inside a YAML frontmatter description. Match each file's existing voice rather than imposing a
  single phrasing, per `doc-revise`.
- D-002 sits in a `description` field that `scripts/validate-skills.py` reads. Keep it a valid single
  YAML scalar and keep it above the 40-character minimum.
- Both files are current-state documents, so this apply run is permitted. Neither is a contract or a
  ledger.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] No occurrence of `document` used as a skill name remains in `.agents/skills/`.
- [x] Both files reference `doc-sync` for doc-vs-code drift.
- [x] `scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] No other line in either file is changed.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
