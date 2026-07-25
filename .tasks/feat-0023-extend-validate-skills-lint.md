---
id: feat-0023
title: Extend validate-skills.py to catch the defects the 2026-07-25 review found by hand
type: feat
status: open
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-07-25
---

## Problem

[`scripts/validate-skills.py`](../scripts/validate-skills.py) checks four things: a `SKILL.md`
exists, its frontmatter parses, `name` matches the directory, and `description` is not trivially
short, plus a body-length warning. Every defect the 2026-07-25 kit-wide review found was invisible to
it, and all of them are mechanically detectable:

- **Dangling sibling references.** A skill links to `../<name>/SKILL.md` for a skill that does not
  exist. This is what `chore-0006` fixed by hand, and the linter would have failed on it since the
  day the reference was written.
- **Unresolved relative links.** Any inline markdown link in a `SKILL.md` whose relative target does
  not exist on disk.
- **Self-contradictory status.** A skill asserting it is a draft while also asserting it shipped
  (`chore-0007` covers three instances).

The kit's own contribution bar says a skill is verified by a command. The command exists but is
nearly blind, so verification has been landing on human reads instead, which is exactly what the
review demonstrated does not scale.

## Scope

**In scope:** add checks to `validate-skills.py` for unresolved relative links (error) and dangling
sibling-skill references (error), plus a warning for a skill that asserts both draft and shipped
status. Extend [`tests/test_validate_skills.py`](../tests/test_validate_skills.py) with a case per new
check, following the existing scenario-tagged style. Keep the script standard-library only and
cross-platform, per the conventions section of [`AGENTS.md`](../AGENTS.md).

**Out of scope:** amending [`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md). It is an
**approved contract** carrying scenarios `S-001` through `S-007` plus an accepted `S-008` divergence,
and this task adds behavior beyond it. **Stop and report** if you conclude the spec must be extended;
only a human sets a spec's status, and the correct order is spec first, then implementation. Filing
that spec amendment is a follow-up, not part of this task. Fixing any of the defects the new checks
find, which belong to `bug-0002`, `chore-0007`, and `chore-0008`. Any check requiring a network call
or a third-party dependency.

## Implementation notes

- The existing script separates `errors` (exit 1) from `warnings` (printed, exit 0). Put link and
  reference failures in `errors`, since they are unambiguous, and the draft/shipped contradiction in
  `warnings`, since the phrasing is a judgment call and a false positive should not break a build.
- Resolve links relative to the `SKILL.md`'s own directory, and skip `http`, `https`, and `mailto`.
  Anchors (`#section`) should be stripped before resolving the path.
- A "sibling-skill reference" is a link matching `../<name>/SKILL.md`; check `<name>` against the
  directory listing already computed in `main()`. This catches the exact `document` defect
  retroactively.
- `main()` already takes `skills_dir` as a parameter, which is what makes it testable; preserve that.
  See `docs/spec/validate-skills.md` `S-008` for why that parameter exists.
- Mirror the existing test style: [`tests/test_validate_skills.py`](../tests/test_validate_skills.py)
  builds temporary skill directories and asserts on exit code and captured output. Tag each new test
  with the behavior it protects, as the existing ones tag scenarios.
- Compose [`test-quality`](../.agents/skills/test-quality/SKILL.md) for layer and oracle: these are
  filesystem-shaped checks, so a temp-directory fixture at the existing layer is the lowest faithful
  one. Assert exact exit codes and specific message content, not "does not crash".

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A `SKILL.md` linking to a nonexistent relative path produces an error and exit 1.
- [ ] A `SKILL.md` linking to `../<name>/SKILL.md` for a nonexistent skill produces an error and
      exit 1.
- [ ] A `SKILL.md` asserting both draft and shipped status produces a warning and exit 0.
- [ ] `http`, `https`, and `mailto` links, and anchors, are not reported.
- [ ] A new test covers each of the three checks above, plus the skip cases.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` exits 0 with more tests than the current 11.
- [ ] `python scripts/validate-skills.py` still exits 0 against the real `.agents/skills/` tree, or,
      if it now legitimately fails, the failures are reported and **not** fixed here (they belong to
      the sibling tasks).
- [ ] `python .tasks/validate.py --strict` exits 0.
- [ ] `docs/spec/validate-skills.md` is byte-for-byte unchanged.
- [ ] Standard library only; no new dependency. PEP 8.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in the `AGENTS.md` conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
