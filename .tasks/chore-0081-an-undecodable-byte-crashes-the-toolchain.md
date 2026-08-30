---
id: chore-0081
title: An undecodable byte crashes the distributed tooling with a traceback instead of a diagnosis
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/validate-skills.py
  - scripts/install.py
  - scripts/check-citations.py
  - scripts/build-adapters.py
  - .tasks/validate.py
  - tests/test_validate_skills.py
  - tests/test_tasks_validate.py
created: 2026-08-29
---

## Problem

Fourteen sites across the distributed tooling read text with `encoding="utf-8"`, no `errors=`, and no
enclosing `try`:

```bash
grep -rn "read_text(" scripts/*.py .tasks/validate.py | grep -v "errors="
```

[`validate-skills.py`](../scripts/validate-skills.py) at 392, 450, 584, 639;
[`validate.py`](validate.py) at 208, 325, 447; [`install.py`](../scripts/install.py) at 158, 189,
245; [`check-citations.py`](../scripts/check-citations.py) at 328;
[`build-adapters.py`](../scripts/build-adapters.py) at 488.

Any one of them meets a file with a stray byte and the tool dies on a traceback. Reproduced
2026-08-29 with a `SKILL.md` carrying a trailing `\xff\xfe`, run through
`validate-skills.main()` against a scratch tree:

```text
  invalid UTF-8 bytes    RAISED UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 254
```

The acceptance command then dies on a stack trace that reads as a defect in the tool rather than a
diagnosis of the file, and does not name which file it was reading.

This is the failure [`check-provenance.py`](../scripts/check-provenance.py) reasons about and avoids
at line 472, in a comment that states the general case:

> Degrade cleanly. A traceback here would read as a defect in this script rather than as the network
> being down, which is the common case by a wide margin.

The hooks module handles it too, with `errors="ignore"` in `_read_head()` and a bare `except OSError`
around every read. The distributed tooling is the inconsistent half, and it is the half an outside
contributor's file reaches first.

**It fails closed, which is why this is P2.** Tested whether one bad byte can leave a partial
install: a scratch tree of four real skills with one corrupted, installed to a scratch home with a
redirected manifest, produced `skills actually placed on disk: []` and `manifest written: False`. The
raise happens while descriptions are read, before any placement. Nothing is left half-done; the
report is just unusable.

## Scope

**In scope:** one helper that reads text and reports an undecodable file as an ordinary error naming
its path, used at all fourteen sites, plus tests at the two validators.

**Out of scope:**

- `errors="ignore"` or `errors="replace"` as the fix. Silently reading past a bad byte is worse
  than failing: a skill whose description was mangled would validate and install. The file should be
  reported as an error and skipped, and the run should end with the exit code an error earns.
- Encoding detection or any non-UTF-8 encoding support. UTF-8 is the contract; this is about how a
  violation of it is reported.
- The hooks, which already handle this.
- BOM handling. A UTF-8 BOM is already reported as an error by `validate-skills.py`, correctly, since
  it breaks the frontmatter fence. Verified in the same battery.

## Implementation notes

A small shared helper is the obvious shape and it is not available: the hooks contract forbids
importing from this repository, and `.tasks/validate.py` is a template that ships into adopter
repositories via `init-worktracking`, so it cannot import from `scripts/` either. So this is a
repeated four-line pattern rather than one function, and the tests are what keep the copies honest.
That is the same trade [`chore-0059`](chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md)
is open on for the link helpers, and this should follow whatever that task settles rather than
inventing a second answer. If `chore-0059` lands first, reuse its mechanism.

Within `scripts/`, where nothing forbids sharing, one helper is fine and preferred.

The error message is the deliverable, not the catch. It should name the path, say the file is not
valid UTF-8, and give the byte offset, because that is what turns a five-minute puzzle into a
one-line fix. Mirror `_validate_manifest()`'s docstring principle: "The message is half the fix."

## Risks and rollback

Touches five modules including a template that ships to adopters, so it meets the more-than-one-module
rule. The failure direction is a catch broad enough to swallow a genuine bug: catch
`UnicodeDecodeError` specifically, never `Exception`.

`.tasks/validate.py` is copied into adopter repositories by `init-worktracking`, so the change lands
in two places (the template under `.agents/skills/init-worktracking/templates/` and this
repository's own copy) or it drifts. Check both.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] `validate-skills.py` over a tree containing a `SKILL.md` with invalid UTF-8 exits non-zero with
      an error naming that file, and does not raise.
- [ ] `.tasks/validate.py` over a task file with invalid UTF-8 does the same.
- [ ] `install.py --dry-run` over such a tree reports the file and does not raise.
- [ ] A test asserts the undecodable file is reported as an error rather than skipped silently, so
      the fix cannot be an `errors="ignore"` in disguise.
- [ ] The template copy of `validate.py` under `init-worktracking/templates/` matches this
      repository's copy.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
