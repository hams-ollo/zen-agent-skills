---
title: build-adapters
status: approved
---

# build-adapters

Behavioral contract for [`scripts/build-adapters.py`](../../scripts/build-adapters.py), written
2026-07-27 (`feat-0026`). This is a **retrospective** spec: the implementation exists and is verified,
and this document states the contract it already holds so that the contract stops living only as code
and test assertions. Approved by the author on 2026-07-27.

Amended 2026-07-27 (`chore-0015`) to classify the two kinds of emitted shared material and state how
each is treated on a re-run, closing the gap the `feat-0026` audit recorded as "behavior found outside
the contract". Re-approved by the author on 2026-07-27.

Amended 2026-08-06 (`feat-0034`) to add a third target, `plugin`, which emits a Claude Code plugin
tree instead of an inlined adapter: scenarios S-015 through S-017, and the Proposed Surface and
Constraints entries that change with them. **This amendment is pending the author's re-approval.**
The `status` field above is deliberately left reading `approved`, because it records the contract as
re-approved on 2026-07-27 and this repository has no machine-readable way to say "approved, with an
unapproved amendment inside"; re-approval of the paragraphs added by `feat-0034` is the author's and
is not granted here.

Amended 2026-08-19 (`chore-0043`) to state that a markdown link rendering as literal text is not a
link and is emitted unchanged: scenario S-018, an exception to the rewrite rules S-003 through S-008.
**This amendment is pending the author's re-approval.** It writes down the behaviour `bug-0028` gave
`rewrite_links()` on 2026-08-18, which the contract did not state at all; `status` is left reading
`approved` for the reason the paragraph above gives.

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
  is reachable as `../../` from either, rather than one copy per target. The plugin tree sits two
  levels below its root as well, but reaches a different shared location from there, so where the
  shared material lands is a property of the requested target and not a single value for all of them.
- A plugin is installed by copying its directory, so a path leaving that directory resolves to nothing
  at the installed location. Everything a plugin tree references must therefore live inside it.
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

### Scenario S-018: a link that renders as literal text is not a link

- **Given** a skill body containing a markdown link whose target sits inside an inline code span (a
  run of backticks of any length, closed on the same line by a run of the same length) or inside a
  fenced code block
- **When** the adapter is emitted
- **Then** that link appears byte-for-byte as written, in every target.

  This is an exception to S-003 through S-008 and takes precedence over all of them. Those scenarios
  sort a link by its *kind*; this one decides whether the text is a link at all. A link rendered as
  literal text is the body **showing** a link as an example rather than making one, so repointing it
  rewrites what the skill says instead of where it points, and the kit then reads one way while every
  generated adapter reads another. Nothing fails when that happens: the adapter renders, the run
  reports success, and the only reader who finds out is one following a documented example in another
  repository (`bug-0028`).

  A link whose *text* is wrapped in a code span, which is how nearly every link in this kit is
  written, is still rewritten. It is the link's target that has to fall inside the span or the fence
  for this scenario to apply.

  An unterminated opening fence yields no range and therefore suppresses nothing below it: the links
  after it are rewritten as usual. A detector that ran an unclosed fence to end of file would switch
  the rewrite off for the rest of the body while still reporting success, which is the one failure
  indistinguishable from success. An unmatched backtick run opens nothing for the same reason. That
  trade is the one `bug-0015`, `bug-0017`, `bug-0023` and `bug-0027` each settled in the other two
  tools carrying this rule, and this contract restates it rather than inheriting it silently.

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

### Scenario S-015: the plugin target emits an installable plugin tree

- **Given** a kit containing N skills, and the plugin target requested
- **When** the tool runs against an output root
- **Then** it writes each skill's `SKILL.md` to `skills/<name>/SKILL.md`, keeping the skill in its own
  directory rather than flattening it into one, and writes `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`, whose single listed plugin names the emitted root as its source
  and carries the same name and version as the plugin manifest beside it. It reports the emitted files
  and its counts, and exits zero.

### Scenario S-016: nothing in an emitted plugin tree points outside it

- **Given** a plugin tree emitted from a kit whose skills reference the rules module
- **When** the tree is read from the location it was installed to rather than from the kit
- **Then** every relative link in every emitted skill resolves to a file that exists and lies inside
  the plugin root, and the rules module is present in exactly one place, so a skill that composes a
  lens finds that lens.

  This is the scenario the target exists for, and a manifest validator cannot check it. Installing a
  plugin copies its directory, so a reference leaving that directory resolves to nothing once
  installed, and the failure is silent: the skill still loads and still reads correctly, and only the
  composed lens is absent. That is how `house-review` once shipped with no rubric at all.

### Scenario S-017: the plugin target is opt-in

- **Given** a run that does not name a target
- **When** it completes
- **Then** no plugin tree and no `.claude-plugin/` manifest directory exist under the output root,
  while the same run requested with the plugin target does write both.

  `--out` defaults to the working directory, so a default run writes into whatever project invoked it.
  A `.claude-plugin/` left there becomes a committed, hand-maintained manifest, which is the second
  copy this tool exists to prevent.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/build-adapters.py [--target <list>] [--out <dir>] [--dry-run]` |
| `--target` | Comma-separated subset of the supported targets `cursor`, `vscode`, `plugin`; defaults to the two inlining targets, `cursor,vscode`. `plugin` is opt-in, per S-017 |
| `--out` | Output project root; defaults to the working directory |
| `--dry-run` | Preview: report what would be written, write nothing |
| Emitted per skill | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md`, `skills/<name>/SKILL.md` (plugin) |
| Emitted per plugin run | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, once per run rather than per skill |
| Emitted shared | Under `.agents/` for the inlining targets and at the plugin root for the plugin target: `<shared>/rules/<file>` (adopted, preserved on a re-run), `<shared>/skills/<name>/<path>` (derived, refreshed on a re-run). Targets sharing a location share one copy |
| Exit code | non-zero for an unrecognized target, zero otherwise |
| Output | one line per emitted adapter and per emitted manifest, then a summary of adapter and shared-asset counts, naming the shared locations written, and a manifest count when the plugin target ran |

## Open Questions

None.
