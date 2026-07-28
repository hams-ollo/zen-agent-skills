---
id: feat-0030
title: Accept and validate an optional external issue reference on task files
type: feat
status: done
priority: P1
parent: "ROADMAP#9 tracker-links"
depends_on: []
spec: "docs/spec/tracker-links.md"
scenarios: ["S-007", "S-008"]
touched_files:
  - .tasks/validate.py
  - .tasks/_TEMPLATE.md
  - .tasks/README.md
  - tests/test_tasks_validate.py
created: 2026-07-28
---

## Problem

`docs/spec/tracker-links.md` (approved) defines an optional `external` frontmatter field naming the
upstream GitHub issue a task serves. Nothing accepts or checks it yet.

S-007 requires a malformed value to fail validation before it can reach a pull request body, and
S-008 requires an absent value to stay valid. Without S-007 a typo travels silently into a pull
request description, where GitHub ignores it and the issue never closes, which is the exact
silent-failure class the spec exists to prevent.

[`.tasks/validate.py`](validate.py) currently checks that every `REQUIRED` field is present and does
not reject unknown keys, so an `external` value is tolerated today but unchecked.

## Scope

**In scope:** recognise `external` as an optional field, validate its form when present, document it
in the task template and the tasks README, and cover both scenarios with tests.

**Out of scope:** `pr-describe`'s emission behavior (that is `feat-0031`); any network call to
confirm the issue exists (a spec Non-Goal); Azure Boards `AB#` values, which the field is designed to
hold later but which nothing validates or emits yet.

## Implementation notes

The accepted forms are exactly two, per the spec's Proposed Surface: `#123` for this repository and
`owner/repo#123` for another. A bare number is not accepted, deliberately, so the stored value stays
identical to what GitHub itself expects.

`.tasks/validate.py` already has `OPTIONAL_SPEC_FIELDS` for `spec` and `scenarios`, which is the
pattern to follow rather than inventing a second one for optional fields.

This repository has no test file for `.tasks/validate.py`, so one is created here. Keep it to the two
scenarios this task owns rather than backfilling coverage for the whole validator, which is separate
work and would make this task non-atomic.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A test proves a malformed `external` value fails validation, naming the file and the value,
      with a non-zero exit (S-007).
- [ ] A test proves a task file with no `external` key validates cleanly (S-008).
- [ ] Both accepted forms, `#123` and `owner/repo#123`, are proven to pass.
- [ ] Each test is tagged with the scenario id it covers, per the convention in
      [`tests/test_install.py`](../tests/test_install.py).
- [ ] `python .tasks/validate.py --strict` still exits 0 over the existing backlog.
- [ ] `.tasks/_TEMPLATE.md` and `.tasks/README.md` document the field, its two accepted forms, and
      that it is optional.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
