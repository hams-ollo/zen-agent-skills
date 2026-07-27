---
title: build-adapters
status: draft
---

# build-adapters

Behavioral contract for [`scripts/build-adapters.py`](../../scripts/build-adapters.py), written
2026-07-27 (`feat-0026`). This is a **retrospective** spec: the implementation exists and is verified,
and this document states the contract it already holds so that the contract stops living only as code
and test assertions. Approved by the author on 2026-07-27.

Amended 2026-07-27 (`chore-0015`) to classify the two kinds of emitted shared material and state how
each is treated on a re-run, closing the gap the `feat-0026` audit recorded as "behavior found outside
the contract". Reopened to `draft` for that amendment; a human sets `status: approved`.

## Problem

Claude Code and OpenCode discover skills from a directory, so `install.py` can place a skill's own
directory and be done. Cursor and VS Code read project-level configuration instead, so the same
instructions have to be re-expressed in each harness's native file, per project.

Maintaining a second hand-edited copy per harness is the failure this tool prevents, and inlining the
body verbatim is the failure it has to avoid while doing so. A skill's links are written relative to
the skill directory, and an adapter does not sit in the skill directory. Emitted unchanged, every one
of those links resolves to nothing: measured against this kit, 97 dangling links per target. The
damage is silent, because the adapter renders correctly and only the agent reading it finds an empty
space where the review rubric was meant to be.

Rules for that rewriting currently exist only in code. A future editor who does not know that a
project's own copy of the swappable rules module must never be overwritten can break that and watch
every test still pass, because no test asserts the reason.

## Goals

1. Emit one native adapter per skill for each supported harness, from the single `SKILL.md` source.
2. Keep every link in an inlined body resolvable from the adapter's own location.
3. Emit the shared material those rewritten links point at, refreshing what the kit owns while
   never overwriting what the adopter owns.
4. Keep adapters safe to regenerate: derived artifacts, and a no-op when the output is the kit itself.
5. Support previewing a run without writing anything.
6. Fail clearly on an unusable invocation rather than writing a partial result.

## Non-Goals

- Installing skills for harnesses that discover them from a directory. That is `install.py`.
- Judging whether a skill is well-formed. That is `validate-skills.py`.
- Preserving hand edits in a previously generated adapter. Adapters are derived and overwritten.
- Resolving or validating external URLs, which would require network access.
- Emitting an adapter for any harness beyond the supported targets.

## Constraints

- Standard library only.
- Both adapter directories sit exactly two levels below the output root, so a single shared location
  is reachable as `../../` from either, rather than one copy per target.
- A skill body's relative links are written for the skill's own directory. An adapter is not there,
  so a link is correct in the emitted file only if it was rewritten for the adapter's location.
- The rules module is swappable by design, so a copy already present in the target project is the
  project's own choice and outranks the kit's.
- The two kinds of emitted shared material have different owners, which is what decides their
  treatment on a re-run. A skill's supporting files are **derived**: they exist in the target project
  only so an adapter's link resolves, and the adopter's own working configuration lives elsewhere in
  their repository, so replacing them loses nothing. The rules module is **adopted**: it is the file
  the kit invites a project to rewrite in its own voice.

## Scenarios

### Scenario S-001: an adapter is emitted per skill per requested target

- **Given** a kit containing N skills and a requested target
- **When** the tool runs against an output root
- **Then** it writes one adapter per skill for that target and no file for any target not requested:
  the Cursor adapter at `.cursor/rules/<name>.mdc`, the VS Code adapter at
  `.github/prompts/<name>.prompt.md`. It reports one line per emitted adapter and a closing summary
  of the adapter and shared-asset counts, and exits zero.

### Scenario S-002: each adapter carries its harness's own frontmatter and a do-not-edit banner

- **Given** a skill with a `name` and a `description`
- **When** an adapter is emitted
- **Then** the Cursor adapter opens with `description` and `alwaysApply: false`, the VS Code adapter
  opens with `mode: agent` and `description`, and both carry a banner naming the source `SKILL.md`
  and stating that the file is generated and must not be edited in place.

### Scenario S-003: a sibling-skill link points at the adapter generated beside it

- **Given** a skill body linking to `../<sibling>/SKILL.md`
- **When** the adapter is emitted
- **Then** the link becomes `<sibling>` plus the emitting target's adapter extension, resolving
  within the same directory as the adapter.

### Scenario S-004: an anchor on a sibling-skill link survives the rewrite

- **Given** a skill body linking to `../<sibling>/SKILL.md#<anchor>`
- **When** the adapter is emitted
- **Then** the rewritten link retains `#<anchor>`, so a link into a specific section still lands there.

### Scenario S-005: a link title survives the rewrite

- **Given** a link written with a quoted title after its target
- **When** the adapter is emitted
- **Then** the title is preserved unchanged alongside the rewritten target.

### Scenario S-006: a rules-module link points at the shared location

- **Given** a skill body linking to a file in the rules module
- **When** the adapter is emitted
- **Then** the link resolves to that file under the shared `.agents/rules/` location relative to the
  adapter.

### Scenario S-007: a skill-local supporting file points at the shared location

- **Given** a skill body linking to one of its own supporting files, such as a template
- **When** the adapter is emitted
- **Then** the link resolves to that file under the shared `.agents/skills/<name>/` location relative
  to the adapter.

### Scenario S-008: external and same-page links are emitted unchanged

- **Given** a skill body containing `http`, `https`, or `mailto` links, or links to an anchor on the
  same page
- **When** the adapter is emitted
- **Then** each appears in the adapter byte-for-byte as written.

### Scenario S-009: the material the rewritten links point at is emitted

- **Given** a run that emits any adapter
- **When** the run completes
- **Then** the rules module and each skill's supporting files exist under the output root at the
  shared locations S-006 and S-007 rewrite to, so every rewritten link resolves on disk.

### Scenario S-010: a rules file already present in the target project is never overwritten

- **Given** an output root already containing a rules-module file whose content differs from the kit's
- **When** the tool runs against that output root
- **Then** that file's content is unchanged, because a project's own copy of a swappable module
  outranks the kit's.

### Scenario S-014: a re-run refreshes derived assets and preserves adopted ones

- **Given** an output root from a previous run, in which both an emitted skill supporting file and an
  emitted rules-module file have been edited
- **When** the tool runs again against that output root
- **Then** the skill supporting file is replaced with the kit's current version and the rules-module
  file retains its edited content, because the first is derived from the kit and the second belongs to
  the adopter.

  The rules half restates S-010 deliberately. The contrast is the requirement: stating either half
  alone leaves a reader unable to tell a rule from an accident, which is exactly how the skill-asset
  behavior went unstated in the first place.

### Scenario S-011: generating into the kit itself changes nothing

- **Given** an output root that is the kit repository, where a shared file's source and destination
  are the same file
- **When** the tool runs
- **Then** no shared file is copied onto itself and the run reports zero shared assets written.

### Scenario S-012: a preview run writes nothing

- **Given** a run requested as a preview
- **When** it completes
- **Then** no file exists that the run would have written, and the reported counts describe what would
  have been produced.

### Scenario S-013: an unrecognized target is rejected

- **Given** a requested target that is not supported
- **When** the tool runs
- **Then** it names the unrecognized target and the supported ones, writes no file, and exits
  non-zero.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/build-adapters.py [--target <list>] [--out <dir>] [--dry-run]` |
| `--target` | Comma-separated subset of the supported targets; defaults to all of them |
| `--out` | Output project root; defaults to the working directory |
| `--dry-run` | Preview: report what would be written, write nothing |
| Emitted per skill | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md` |
| Emitted shared | `.agents/rules/<file>` (adopted, preserved on a re-run), `.agents/skills/<name>/<path>` (derived, refreshed on a re-run) |
| Exit code | non-zero for an unrecognized target, zero otherwise |
| Output | one line per emitted adapter, then a summary of adapter and shared-asset counts |

## Open Questions

None.
