---
title: validate-skills
status: approved
---

# validate-skills

Behavioral contract for [`scripts/validate-skills.py`](../../scripts/validate-skills.py), written
2026-07-24 to serve as the audit target for the first in-kit dogfood of the `spec-conformance`
lens. It captures the tool's intended contract from its module docstring and observable behavior.

Reopened to `draft` on 2026-07-27 and amended (`chore-0013`). The implementation had twice grown
past this contract without it: `feat-0023` added link resolution, sibling-reference, and
status-contradiction checking on 2026-07-25, and the 2026-07-27 review pass added the portability
check now specified as S-011. Scenarios S-009 through S-016 close that gap. Re-approved by the
author on 2026-07-27.

**Amended 2026-07-28 (`feat-0032`) on the author's explicit instruction, and re-approved.** S-017 and
S-018 were added, along with Goal 6 and the field-limit constraint they serve. This contract had a soft
floor on the description and no ceiling, while both harnesses `install.py` targets cap the field at
1024 characters, so five shipped skills exceeded a hard distribution limit and the validator reported
nothing (`bug-0005`). S-018 exists because fixing S-017 alone would have been wrong: the parser counted
a YAML block-scalar indicator as description content, so the number the validator reported was three
characters higher than the number the harness measures, and a ceiling built on it would reject
descriptions the harness accepts.

## Problem

The kit ships skills as `SKILL.md` files. A malformed skill (missing frontmatter, a `name` that
does not match its directory, a thin description) should fail loudly before it is distributed. The
validator is the kit-level lint that enforces that bar.

## Goals

1. Fail (non-zero exit) when any skill is structurally invalid.
2. Warn without failing when a skill is well-formed but below a soft quality bar.
3. Report a summary of how many skills were checked and the error and warning counts.
4. Fail when a skill's cross-references are broken, or when they would break once the skill is
   distributed away from this repository.
5. Fail rather than report a vacuous success when the target skills directory cannot be read, so an
   absent check is never indistinguishable from a passing one.
6. Fail when a field exceeds a limit the distribution targets enforce, because a skill a harness
   rejects or truncates has not shipped, and it fails by simply never being selected.

## Non-Goals

- Judging skill prose quality beyond the structural and length proxies.
- Modifying or fixing any skill.
- Verifying that a link's target contains what the linking text claims about it.
- Resolving external URLs, which would require network access.

## Constraints

- Standard library only.
- A `SKILL.md` is YAML frontmatter (delimited by `---`) followed by a Markdown body.
- Both harnesses the kit installs to cap `description` at 1024 characters. That bound is external and
  not the kit's to choose, which is why exceeding it is an error rather than a matter of taste.
- Frontmatter is read by a small standard-library parser, not a YAML library. A field's value is
  therefore whatever that parser yields, so where YAML syntax and the parser could disagree about what
  the value is, the contract states which one the checks mean.
- A skill is distributed as a directory alongside its sibling skills and the swappable rules module,
  without the surrounding repository. A link is therefore legal only if it stays inside that
  distributed tree: the skill's own files, a sibling skill, or the rules module. A link above it
  resolves in this repository and dangles everywhere the skill is actually used.

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

### Scenario S-009: link to a target that does not exist

- **Given** a `SKILL.md` containing a relative link whose target is not present on disk
- **When** the validator runs
- **Then** it records a link-target error naming the unresolved path, and exits non-zero.

### Scenario S-010: reference to a sibling skill that does not exist

- **Given** a `SKILL.md` referencing a sibling skill that is not present in the kit
- **When** the validator runs
- **Then** it records an error naming that skill, and exits non-zero.

### Scenario S-011: link that escapes the distributed skill tree

- **Given** a `SKILL.md` containing a relative link that resolves above the distributed skill tree,
  and whose target does exist in this repository
- **When** the validator runs
- **Then** it records an error naming the link as non-portable, and exits non-zero. The target's
  existence in this repository does not satisfy the check, because the skill is not distributed with
  this repository around it.

### Scenario S-012: link to the rules module is legal

- **Given** a `SKILL.md` linking to a file in the sibling rules module
- **When** the validator runs
- **Then** it records no finding for that link, because the rules module travels with the skills.

### Scenario S-013: external and same-page links are not resolved

- **Given** a `SKILL.md` containing `http`, `https`, or `mailto` links, or links to an anchor on the
  same page
- **When** the validator runs
- **Then** it records no finding for any of them, and does not attempt to resolve them on disk.

### Scenario S-014: contradictory status claim warns but does not fail

- **Given** a `SKILL.md` that asserts it is a draft and also records that it shipped
- **When** the validator runs
- **Then** it records a warning naming the contradiction, and (absent other errors) exits zero.
  Either assertion alone is not a contradiction and produces no finding.

### Scenario S-015: skills directory does not exist

- **Given** an invocation whose target skills directory is not present
- **When** the validator runs
- **Then** it reports the missing directory and exits non-zero, rather than reporting zero skills
  checked and succeeding.

### Scenario S-016: skills directory exists but is empty

- **Given** an invocation whose target skills directory is present and contains no skill
- **When** the validator runs
- **Then** it reports that no skills were found and exits zero, because an empty directory is a
  legitimate zero-skill result rather than an unreadable one.

### Scenario S-017: description over the harness limit fails

- **Given** a `SKILL.md` whose `description` is longer than the 1024-character limit the distribution
  targets enforce
- **When** the validator runs
- **Then** it records an error naming the measured length and that limit, and exits non-zero. A
  description at or below the limit produces no finding from this check.

### Scenario S-018: a description is measured by its value, not its YAML syntax

- **Given** a `SKILL.md` whose `description` is written as a YAML block scalar, so the field line
  carries an indicator (`>`, `>-`, `>+`, `|`, `|-`, or `|+`) and the text follows on continuation lines
- **When** the validator measures that description
- **Then** the length is of the scalar's value, excluding the indicator, so the reported number is the
  one a harness reading the same file would measure. A plain single-line description is measured
  unchanged.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/validate-skills.py` |
| Exit code | non-zero when any error is recorded, zero otherwise (warnings do not fail) |
| Output | per-issue `WARN`/`ERROR` lines, then a `Checked N skill(s): E error(s), W warning(s).` summary. When the skills directory is absent, a missing-directory error instead of the summary; when it is present but empty, a no-skills-found line instead of the summary. |

## Open Questions

None.
