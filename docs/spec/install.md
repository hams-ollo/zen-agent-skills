---
title: install
status: approved
---

# install

Behavioral contract for [`scripts/install.py`](../../scripts/install.py), written 2026-07-27
(`feat-0029`). A **retrospective** spec: the implementation exists and its behavior was pinned first by
[`install.characterization.md`](install.characterization.md), so this describes a contract that
already holds rather than proposing one. Approved by the author on 2026-07-27.

**Amended 2026-07-28 (`bug-0003`), pending author re-approval.** S-007 was scoped to the home it was
given and S-012 was added. The original wording, "remove the recorded targets and empty the record",
was satisfied by an implementation that removed every recorded target from every home ever installed
to from this checkout, which destroyed a working installation while reporting success. The contract
never said what `--uninstall` should do when the record spans more than one home, so the code was not
diverging from it. This amendment states it.

## Problem

The kit's skills are useless until a harness can find them. Claude Code and OpenCode both discover
skills from a directory, so placing the canonical directories is the whole job, and this is the tool
that does it.

Two things about that job are easy to get wrong and were both got wrong at some point. A skill is not
self-contained: twelve of them compose a swappable rules module through a relative reference, and
until 2026-07-27 the tool shipped the skills without it, so the most rubric-dependent skill in the kit
arrived with an empty reference where its severities should have been. And placing files into a
directory a user owns means every write is a chance to destroy something the user put there, so what
the tool refuses to touch matters more than what it places.

Neither property is asserted anywhere a reader can check. The rules module's location looks arbitrary
rather than derived from what the skills reference, and the rule that an unmanaged target is never
overwritten exists only as a branch.

## Goals

1. Place every skill where each requested harness discovers it, from the single canonical source.
2. Place the rules module where the skills' own references resolve to, so a composed lens is never
   dangling once installed.
3. Be safe to run repeatedly, recognising the tool's own previous targets rather than refusing them.
4. Never modify or remove anything the tool did not place.
5. Support previewing a run and reversing a completed one.
6. Fail clearly on an unusable invocation rather than placing part of it.
7. Work out of the box on Windows, macOS, and Linux, since a portability promise that starts with a
   failed install is not one.

## Non-Goals

- Generating project-level adapters for harnesses that read repository configuration. That is
  `build-adapters.py`.
- Judging whether a skill is well-formed. That is `validate-skills.py`.
- Installing dependencies, or changing any harness setting beyond placing directories where it looks.
- Managing, updating, or removing skills the tool did not place, including a user's own.

## Constraints

- Standard library only.
- A skill references the rules module relatively, from inside its own directory. The module's install
  location is therefore not a choice: it is wherever those existing references resolve to.
- Symlink creation requires privilege on Windows that a normal account may lack, so the two placement
  modes are not interchangeable and the default depends on the platform.
- Re-run recognition needs a record of what the tool created, because a copied directory is
  indistinguishable from a user's own. That record is the manifest, and its presence is therefore part
  of the observable contract rather than an internal detail. Symlink mode can recognise its own links
  directly and does not depend on it.

## Scenarios

### Scenario S-001: each requested tool receives every skill

- **Given** a set of skills and one or more requested tools
- **When** the tool runs against a home directory
- **Then** every skill is placed under that tool's discovery directory, one per skill, and no
  directory is placed for a tool that was not requested.

### Scenario S-002: the rules module lands where the skills' references resolve

- **Given** skills that reference the rules module relatively from their own directories
- **When** the tool runs
- **Then** the module is placed such that those existing references resolve on disk, without the
  skills being rewritten.

### Scenario S-003: a re-run recognises the tool's own targets

- **Given** a home directory holding targets this tool placed on a previous run
- **When** the tool runs again with the same arguments
- **Then** it replaces or relinks those targets and reports doing so, rather than reporting a conflict
  against its own work, and exits zero.

### Scenario S-004: an unmanaged target is refused, not overwritten

- **Given** a file or directory at a target path that this tool did not place
- **When** the tool runs
- **Then** that path is left byte-for-byte unchanged, the conflict is reported naming it, and the run
  exits non-zero while continuing to place the targets that are free.

### Scenario S-005: a lost record makes previous copies unmanaged

- **Given** targets previously placed by copying, and a record of them that has since been deleted
- **When** the tool runs again
- **Then** those targets are treated as unmanaged and refused per S-004, because a copied directory
  carries nothing distinguishing it from a user's own.

### Scenario S-006: a preview run writes nothing

- **Given** any invocation requested as a preview
- **When** it completes
- **Then** no target and no record exists that the run would have created, and the reported outcome
  describes what would have been placed.

### Scenario S-007: reversing a run removes what it placed beneath the given home

- **Given** a completed run whose targets are recorded
- **When** the tool is asked to reverse it against the same home
- **Then** each recorded target beneath that home is removed, those entries leave the record, and
  nothing the tool did not place is touched.

### Scenario S-008: reversing with nothing recorded is not an error

- **Given** no record of any previous run
- **When** the tool is asked to reverse one
- **Then** it reports that nothing is recorded and exits zero.

### Scenario S-012: reversing one home leaves another home's installation intact

- **Given** completed runs against two different homes, both recorded
- **When** the tool is asked to reverse one of them
- **Then** only that home's targets are removed, the other home's targets remain on disk and remain
  recorded, and a later reversal of the other home still finds them.

### Scenario S-009: an unrecognised tool is rejected before anything is placed

- **Given** a requested tool that is not supported, alone or alongside a supported one
- **When** the tool runs
- **Then** it names the unrecognised tool and the supported ones, places nothing, and exits non-zero.

### Scenario S-010: the placement mode defaults to what the platform can do

- **Given** no explicitly requested placement mode
- **When** the tool runs
- **Then** it copies on Windows and links elsewhere, because symlink creation there requires privilege
  a normal account may lack.

### Scenario S-011: a failed link reports what to do instead

- **Given** a requested link mode on a system that refuses to create symlinks
- **When** placement is attempted
- **Then** the run stops with a message naming the alternatives available to the user, rather than an
  unhandled error.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/install.py [--tools <list>] [--mode <symlink\|copy>] [--home <dir>] [--dry-run] [--uninstall]` |
| `--tools` | Comma-separated subset of the supported tools; defaults to all of them |
| `--mode` | `symlink` or `copy`; defaults to copy on Windows and symlink elsewhere |
| `--home` | Base directory to install beneath; defaults to the user's home |
| `--dry-run` | Preview: report what would be placed, write nothing |
| `--uninstall` | Remove the recorded targets beneath `--home` and drop those entries from the record, leaving entries for other homes |
| Placed per tool | Each skill's directory under that tool's discovery path, plus the rules module as their sibling |
| Record | A manifest of the targets this tool created, enabling re-run recognition in copy mode |
| Exit code | non-zero on an unrecognised tool or any unmanaged-target conflict, zero otherwise |
| Output | one line per target with its outcome, then a summary; conflicts additionally summarised |

## Open Questions

1. **Should the record live inside the kit repository?** It currently does, which means installing
   from a read-only or shared checkout cannot record what it placed, and a user who reclones loses
   re-run recognition for targets that still exist. Recommendation: leave it as is for now, since the
   failure is visible (targets become conflicts per S-005) rather than silent, and moving it into the
   home directory would make one manifest serve installs from several checkouts, which is a different
   and probably worse problem. Revisit if anyone installs from a shared checkout.
