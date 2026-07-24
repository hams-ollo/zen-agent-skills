---
id: chore-0003
title: Add test coverage for validate-skills.py and make its skills dir injectable
type: chore
status: open
priority: P2
parent: "Kit tooling hardening (surfaced by the test-quality dogfood, feat-0015)"
depends_on: []
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-07-24
---

## Problem

[`scripts/validate-skills.py`](../scripts/validate-skills.py) is the kit-level lint that gates
every shipped skill, but it has zero tests. The `test-quality` dogfood (`feat-0015`) named the
bug population precisely: `parse_frontmatter` ([`validate-skills.py:24`](../scripts/validate-skills.py))
mishandling malformed input (missing closing `---`, a folded-continuation line that matches
`word:` and gets misread as a new key, quoted values), and the `name`/`description`/body-length
error and warning branches in `main`. It also surfaced a real testability blocker: `main` binds
`SKILLS_DIR` at module level ([`validate-skills.py:18`](../scripts/validate-skills.py)), so the
scan cannot be pointed at a fixture directory without a subprocess. The tool's observable contract
is already written down at [`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md) (from
the `spec-conformance` dogfood), so the oracle already exists.

## Scope

**In scope:**
1. Make the scanned skills directory injectable: give `main` an optional `skills_dir` parameter
   (defaulting to the current module-level `SKILLS_DIR`) so it can run against a fixture directory.
   The default `python scripts/validate-skills.py` invocation and its output must stay byte-identical.
2. Add a standard-library `unittest` module at `tests/test_validate_skills.py` covering the bug
   population with exact `(errors, warnings, exit_code)` oracles drawn from
   `docs/spec/validate-skills.md`: scenarios S-001 (no SKILL.md), S-002 (no/ unterminated
   frontmatter), S-003 (name != directory), S-004 (missing name or description), S-005 (thin
   description warns, exit 0), S-006 (oversized body warns, exit 0), and S-007 (all valid, exit 0).
   Use table-driven cases and temp fixture directories (`tempfile`), never mutating any committed file.

**Out of scope:** changing the validator's behavior, output format, or exit-code contract (this is
a refactor-for-testability plus tests, not a behavior change); testing `.tasks/validate.py` or any
other script; adding a third-party test framework or runner; implementing the S-008 "what and when"
check that `docs/spec/validate-skills.conformance.md` accepted as a divergence.

## Implementation notes

- Standard library only, per [`AGENTS.md`](../AGENTS.md) section 6 (no third-party dependency).
  Use `unittest` and `tempfile`.
- `validate-skills.py` has a hyphen in its name, so it is not importable with a normal `import`.
  Load it in the test with `importlib.util.spec_from_file_location`, rather than renaming the
  shipped entry point.
- Reuse the contract in `docs/spec/validate-skills.md` as the source of truth for expected
  outcomes; the two must not drift. If the refactor changes any observable behavior, that is a bug
  in this task, not an accepted change.
- The kit has no `tests/` directory yet; this task establishes it. Keep it minimal.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] `tests/test_validate_skills.py` exists and the command above exits 0.
- [ ] Tests cover S-001 through S-007 with exact `(errors, warnings, exit_code)` assertions, not
      "does not crash" checks, using temp fixture directories.
- [ ] `main` accepts an optional `skills_dir`; `python scripts/validate-skills.py` on this repo
      still prints `Checked N skill(s): 0 error(s), 0 warning(s).` and exits 0.
- [ ] `python scripts/validate-skills.py` output is unchanged for the default invocation.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed (stdlib only, cross-platform `pathlib`/`tempfile`).
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
