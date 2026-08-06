---
id: chore-0031
title: An installed skill goes stale against its source and nothing says so
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/install.py
  - docs/INSTALL.md
created: 2026-08-06
---

## Problem

On Windows, [`install.py`](../scripts/install.py) defaults to **copies** rather than symlinks, so an
installed skill is a snapshot taken at install time. Editing the skill in this repository does not
change the installed copy, and nothing reports the divergence. On POSIX the symlink default hides
the problem rather than solving it, since a copy-mode install there has the same property.

**Measured on this machine, 2026-08-06.** The globally installed `fix-batch` at
`C:\Users\hamsa\.claude\skills\fix-batch\SKILL.md` was missing Step 3 items 7 and 8 and the entire
**delegate report contract** section, all of which are present in this repository's
[`fix-batch`](../.agents/skills/fix-batch/SKILL.md). The installed copy was a wave-2-era snapshot; the
report contract shipped in `feat-0041` and the decision-log item in `feat-0037`, both merged in
[PR #19](https://github.com/hams-ollo/zen-agent-skills/pull/19). An agent invoking the skill by name
got the older procedure and would have dispatched a batch with no report contract at all.

**The failure is silent by construction.** The stale copy is a valid skill: it passes
`validate-skills.py`, it passes Anthropic's `quick_validate.py`, it reads correctly, and it does the
job it describes. Nothing distinguishes "the skill as it is today" from "the skill as it was three
weeks ago", so the only way to notice is to read both and compare, which nobody does.

**This is the kit's own portability lesson pointed inward.** `docs/ARCHITECTURE.md` records that
where a tool reimplements an external standard rather than calling it, conforming to the spec is not
evidence of conforming to the standard. The same shape applies here: a snapshot that once matched its
source is not evidence it still matches, and the kit currently has no way to ask.

**There is already a manifest to build on.** `install.py` writes
`scripts/.install-manifest.json` to know which targets it created, so re-run recognition works in
copy mode. It records what was placed, not what was placed *from*, so it cannot currently answer
whether a target is current.

## Scope

**In scope:** give an installed set a way to report staleness. The likely shape is a digest per
placed file recorded in the existing manifest at install time, plus a `--check` (or equivalent)
that re-reads the targets and names any that no longer match their source. Decide the shape and
record it.

**Out of scope:**

- Auto-updating or auto-reinstalling. Report the divergence and let a human decide, for the same
  reason `feat-0043` rejected upstream's automatic in-place sync: an adopter may have edited an
  installed file deliberately, and an overwrite destroys that without asking.
- Distinguishing "stale" from "locally edited". Both are divergence and both are worth reporting;
  telling them apart needs provenance the manifest does not have, and inventing it is a separate
  decision.
- Any change to the symlink-versus-copy defaults, which are settled and platform-driven.
- The plugin distribution path from `feat-0034`, which has its own cache semantics and is not
  installed by this script.

## Implementation notes

**`feat-0043` already built this mechanism, one target over.** `check-provenance.py` records a SHA256
of retrieved content and reports drift without rewriting anything, and the design question it
answered (detect and report, never overwrite an adaptation) is the same one here. Reuse the shape and
the reasoning rather than inventing a second vocabulary for the same idea; the difference is only
that the reference content is local rather than fetched, which makes this the easier case.

**A digest per file, not per skill.** A skill is a directory with supporting templates and
references, and a stale template is exactly as silent as a stale `SKILL.md`. The manifest already
enumerates targets individually.

**The rules module is the sharpest case and should be tested explicitly.** `install.py` places
`.agents/rules/` as the sibling of the installed skills, and a lens is the one file an adopter is
invited to rewrite, so an unconditional "differs from source" report there would be noise on
every run for anyone who accepted that invitation. That is the same adopted-versus-derived
distinction `build-adapters.md` already draws in its `S-014` and `S-010` scenarios, and this task
should follow it rather than re-litigate it.

## Risks and rollback

Required: this changes a persisted format, the install manifest, which older installs will not have.

- **A manifest without digests must not be treated as "everything is current".** That reads as a
  clean result and is the failure this task exists to prevent, one level up. An install predating
  the change should report "unknown, re-install to establish a baseline", not silence.
- Rollback is one revert plus deleting the manifest, which `install.py` already tolerates: its module
  docstring states that a deleted manifest degrades re-run recognition rather than breaking it.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] An install records enough per placed file to detect later divergence from its source.
- [ ] A check reports every installed file that no longer matches its source, naming each, and exits
      non-zero when any does.
- [ ] It exits zero on a freshly installed tree, demonstrated against a throwaway install home rather
      than asserted.
- [ ] A manifest written before this change reports "unknown" rather than "current".
- [ ] An adopter-owned rules file that has been deliberately edited does not produce a divergence
      report on every run, or the decision to report it anyway is recorded with its reasoning.
- [ ] `docs/INSTALL.md` tells a reader the check exists and when to run it.
- [ ] Tests cover the current, diverged, and no-baseline paths.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
