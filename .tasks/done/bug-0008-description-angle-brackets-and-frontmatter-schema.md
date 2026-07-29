---
id: bug-0008
title: A description with angle brackets fails Anthropic's skill schema, and nothing here checks it
type: bug
status: done
priority: P0
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: docs/spec/validate-skills.md
scenarios: [S-020, S-021]
touched_files:
  - .agents/skills/human-handoff/SKILL.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
created: 2026-07-29
---

## Problem

`human-handoff`'s description contains `<name>` twice, in the trigger phrases "draft a message to
`<name>` about where we are" and "what should I tell `<name>` about the open questions". Anthropic's own
skill validator rejects it outright:

    FAIL  human-handoff   Description cannot contain angle brackets (< or >)

Run on 2026-07-29 against `quick_validate.py` from the official `skill-creator` plugin, which is the
reference implementation of the skill schema. Eighteen of the nineteen pass; this one does not.

**This is the third defect in the `description` field found in two days**, after `bug-0005` (five over
the 1024-character limit) and `bug-0007` (eight unreadable by any YAML parser). Each was found by a
different external check and none by this repository's own. The pattern is the finding: the kit
validates its skills against its own expectations rather than against the schema its distribution
targets enforce.

Two rules from that schema are unchecked here, and both are hard failures at the consumer:

1. **No angle brackets in `description`** (`quick_validate.py:80`).
2. **Only six frontmatter properties are allowed**: `name`, `description`, `license`, `allowed-tools`,
   `metadata`, `compatibility`. Any other key is rejected (`quick_validate.py:42-50`). All nineteen
   skills currently use only `name` and `description`, so the kit passes today by accident rather than
   by check, and the first skill to add a plausible-looking key such as `version` or `tags` breaks
   silently. `version` is the likeliest, because Anthropic's own `example-skill` documents it as an
   optional field while their validator rejects it.

## Scope

**In scope:** remove the angle brackets from `human-handoff`'s description, preserving its trigger
reach; add both schema checks to [`validate-skills.py`](../../scripts/validate-skills.py) as errors; amend
[`docs/spec/validate-skills.md`](../../docs/spec/validate-skills.md) with S-020 and S-021 first; add
covering tests; update the conformance matrix.

**Out of scope:** adopting `allowed-tools` on the report-only skills, which is a behavior change with
its own design question and belongs at the roadmap altitude. Adding `license`, which is `chore-0022`.
Vendoring or re-implementing Anthropic's validator, which needs PyYAML and would break the
standard-library constraint.

## Implementation notes

- **The two replacement phrases must keep the trigger's shape, not just drop the brackets.** `<name>`
  was placeholder notation for a person, so a user's real phrasing is "draft a message to Priya about
  where we are". Replace with a natural noun that matches the same request shape ("a teammate", "a
  stakeholder") rather than deleting the clause, which would narrow what the skill fires on. Check the
  result is still at or under 1024 characters; it has roughly 100 characters of headroom.
- Check the **parsed** description, not the raw line. A block scalar's field line is literally
  `description: >-`, so a raw-text check would flag every one of the twelve skills that use one.
  `parse_frontmatter()` strips the indicator as of `feat-0032`, so the value it returns is the right
  input.
- For the allowed-key check, use the keys `parse_frontmatter()` already returns rather than re-scanning.
  Note that `allowed-tools` contains a hyphen and the existing key regex handles it.
- **Name the source in both messages.** "Angle brackets are not allowed" invites an argument; "the skill
  schema both target harnesses enforce rejects them" ends it. The same reasoning as the 1024 message.
- Amend the spec before the code, as `feat-0032` and `bug-0007` did. The author authorised this
  amendment on 2026-07-29.
- Do not add `version` to the allowed set even though Anthropic's example documents it. Their validator
  is the enforcing implementation and it rejects it; a kit that permitted it would produce skills that
  pass here and fail there, which is the exact failure mode of the last three bugs.

## Risks and rollback

Required: this adds two errors that every future skill must satisfy, and one is an allow-list.

The allow-list is the risk. If a harness later adds a legal property, this check rejects a valid skill
and the failure looks like a kit bug rather than a stale constant. Keep the allowed set in one named
module-level constant with a comment naming its source and the date it was read, so the next person can
see what it is derived from rather than inferring it. Reverting is one commit; the spec amendment
reverts with it.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `human-handoff`'s description contains no `<` or `>`, and still carries both trigger phrases in a form a user would plausibly type.
- [x] All 19 skills pass Anthropic's `quick_validate.py`, run from the installed `skill-creator` plugin.
- [x] `validate-skills.py` errors on a description containing an angle bracket, and on any frontmatter key outside the six-property set.
- [x] Neither check fires on the current 19 skills once `human-handoff` is fixed.
- [x] The allowed-property set is one module-level constant, commented with its source.
- [x] Both new tests fail against the pre-fix validator.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills, 0 errors, 0 warnings.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-29)

**All 19 skills now pass Anthropic's `quick_validate.py`, up from 18.** `human-handoff`'s two
`<name>` placeholders became "a teammate" and "a stakeholder", which keeps the request shape a user
would actually type rather than deleting the clauses and narrowing what the skill fires on. Its
description went 920 to 931 characters, still 93 under the limit.

Both checks are in and both are errors. The angle-bracket check reads the parsed value, so the twelve
block-scalar descriptions are not flagged for the `>` in their own indicator, which was the obvious
way to get this wrong. The allow-list is one commented constant naming `quick_validate.py` and the
date it was read, so the next person can see what it derives from instead of inferring it. `version`
is deliberately excluded: Anthropic's own `example-skill` documents it as optional and their validator
rejects it, and permitting it here would produce skills that pass in this repository and fail at the
consumer, which is precisely the failure mode of the last three bugs.

Five tests, of which two negative cases are load-bearing: a block-scalar description must pass, or
twelve valid skills break, and all six permitted properties together must pass, or the allow-list
fails a valid skill while looking like a kit bug. The three positive tests fail against the pre-fix
validator.

**The finding is the count, not the bracket.** Three defects in one field in two days: `bug-0005`
(five over the length limit), `bug-0007` (eight unreadable by any YAML parser), `bug-0008` (one with
forbidden characters). Every one passed nineteen skills, four gates, an approved contract, and a clean
conformance matrix. None was found from inside, because the kit's parser and the kit's spec agreed
with each other and both disagreed with the schema. Each was found by running an external
implementation over the real tree.

That is now written into the contract as a constraint rather than left as a lesson: the schema is
external, this validator's job includes conforming to it, and the reference implementation is named
with the date it was read. The standing recommendation that follows is to run
`quick_validate.py` across the tree as part of the release checks, since it is the only oracle that
has actually caught anything in this field. It cannot go in the four gates as-is, because it needs
PyYAML and the kit is standard-library only.
