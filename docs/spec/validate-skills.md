---
title: validate-skills
status: approved
---

# validate-skills

Behavioral contract for [`scripts/validate-skills.py`](../../scripts/validate-skills.py), written
2026-07-24 to serve as the audit target for the first in-kit dogfood of the `spec-conformance`
lens. It captures the tool's intended contract from its module docstring and observable behavior.

## Problem

The kit ships skills as `SKILL.md` files. A malformed skill (missing frontmatter, a `name` that
does not match its directory, a thin description) should fail loudly before it is distributed. The
validator is the kit-level lint that enforces that bar.

## Goals

1. Fail (non-zero exit) when any skill is structurally invalid.
2. Warn without failing when a skill is well-formed but below a soft quality bar.
3. Report a summary of how many skills were checked and the error and warning counts.

## Non-Goals

- Judging skill prose quality beyond the structural and length proxies.
- Modifying or fixing any skill.

## Constraints

- Standard library only.
- A `SKILL.md` is YAML frontmatter (delimited by `---`) followed by a Markdown body.

## Scenarios

### Scenario S-001: skill directory without SKILL.md

- **Given** a directory under `.agents/skills/` that has no `SKILL.md`
- **When** the validator runs
- **Then** it records an error for that directory and exits non-zero.

### Scenario S-002: SKILL.md without frontmatter

- **Given** a `SKILL.md` whose first line is not `---`, or that has no closing `---`
- **When** the validator runs
- **Then** it records a "no YAML frontmatter" error and exits non-zero.

### Scenario S-003: name does not match directory

- **Given** a `SKILL.md` whose frontmatter `name` differs from its directory name
- **When** the validator runs
- **Then** it records a name-mismatch error and exits non-zero.

### Scenario S-004: missing name or description

- **Given** a `SKILL.md` missing the `name` or `description` key
- **When** the validator runs
- **Then** it records a missing-field error and exits non-zero.

### Scenario S-005: thin description warns but does not fail

- **Given** a `SKILL.md` with a `description` shorter than the soft minimum
- **When** the validator runs
- **Then** it records a warning, records no error for that description, and (absent other errors)
  exits zero.

### Scenario S-006: oversized body warns but does not fail

- **Given** a `SKILL.md` whose body exceeds the progressive-disclosure line guideline
- **When** the validator runs
- **Then** it records a warning and (absent other errors) exits zero.

### Scenario S-007: all skills valid

- **Given** a skills directory where every skill is well-formed
- **When** the validator runs
- **Then** it prints a summary line with the skill count and zero errors, and exits zero.

### Scenario S-008: description states what and when

- **Given** a `SKILL.md` whose description is long enough to pass the length check but does not
  actually state both what the skill does and when to use it
- **When** the validator runs
- **Then** the description is flagged as not meeting the "what and when" bar.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/validate-skills.py` |
| Exit code | non-zero when any error is recorded, zero otherwise (warnings do not fail) |
| Output | per-issue `WARN`/`ERROR` lines, then a `Checked N skill(s): E error(s), W warning(s).` summary |

## Open Questions

None.
