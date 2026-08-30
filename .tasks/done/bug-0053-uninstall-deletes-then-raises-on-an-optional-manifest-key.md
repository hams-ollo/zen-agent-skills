---
id: bug-0053
title: uninstall deletes the target, then raises on a manifest key the validator calls optional
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-29
---

## Problem

[`install.py`](../../scripts/install.py) lines 1037 and 1039, inside `uninstall()`, subscript two
manifest keys directly:

```python
            print(f"{tag}removed   {e['tool']:8} {e['name']}  ({target})")
```

`_validate_manifest()` does not require either of them. `tool` and `name` sit in
`_OPTIONAL_ENTRY_TYPES` and are faulted on only when present and of the wrong type. That leniency is
deliberate and is documented at line 293: "a validator strict enough to reject a record written by a
later version of this tool turns an upgrade into what looks like corruption."

So a manifest carrying `target` and not `tool` is a record the validator accepts and `uninstall()`
cannot print. Reproduced 2026-08-29 against a scratch home and a redirected `MANIFEST`:

```text
=== _validate_manifest verdict ===
ACCEPTED: the validator raises nothing for this entry.

=== uninstall(dry=True) ===
RAISED KeyError: 'tool'

victim exists before the real run: True
=== uninstall(dry=False) ===
RAISED KeyError: 'tool'
victim exists after: False
manifest still claims entries: 1
```

Three things are wrong in that trace, in increasing order of cost:

1. The command dies on an unhandled traceback rather than the stated exit-2 report that
   `report_unreadable_manifest()` exists to give.
2. `--dry-run` raises in the same place, so the preview a careful person takes first fails too.
3. **The file is deleted and the record still claims it is installed.** `_rm(target)` runs at line
   1035, the raise happens at 1037, and `save_manifest(others, dry)` at 1042 never runs. Disk and
   record disagree, in the direction where the record over-claims.

The comment block above `_OPTIONAL_ENTRY_TYPES` is what the optionality rests on, and it is
incomplete. Line 300 records `name` as read by "`check(): sort key, and the ADOPTED_ENTRY_NAMES
test`" and does not name `uninstall`. `check()` reads the same entry through `.get()` and classifies
it correctly, so two of the three manifest readers are safe and one is not.

## Scope

**In scope:** making `uninstall()` survive an entry the validator accepts, and making the record
consistent with the disk after any outcome.

**Out of scope:**

- Tightening `_validate_manifest()` into rejecting records from other versions. The leniency is a
  recorded decision (`bug-0024`) and this task does not reopen it. If the direct read is genuinely
  wanted, promoting the two keys to required is the alternative below, but it is a contract change
  and needs the `install` spec amended rather than a quiet edit.
- Pruning entries for homes that no longer exist. That is a separate finding, filed as
  [`chore-0082`](chore-0082-four-small-items-from-the-2026-08-29-pre-publication-review.md) item 2.
- The `_beneath()` containment rule, which was exercised against `..`, a relative path, an empty
  string, and the home itself, and holds in every case.

## Implementation notes

Two shapes, and the first is preferred:

- **Read through `.get()` with a placeholder**, matching what `check()` already does. `(unnamed
  entry)` is the wording the currency reminder hook uses for the same situation, so reuse it rather
  than inventing a second one.
- Promoting `tool` and `name` to required in `_validate_manifest()` is the alternative. It is more
  honest about what `uninstall()` needs and it costs an amendment to
  [`install.md`](../../docs/spec/install.md), whose `S-007` and `S-012` govern reversal.

Independently of which is chosen, **move `save_manifest()` so the record cannot outlive the
deletion.** Writing it once at the end is what makes a mid-loop failure lose the record of every
removal that already happened. Either write it inside the loop as each target goes, or wrap the loop
so the record is saved in a `finally`.

Correct the line 300 comment in the same change. It is the only statement of which keys are
dereferenced where, and a reader trusting it is how this shipped.

## Decisions

- **A premise that turned out false.** The finding was first held as "the manifest supplies deletion
  paths to `_place`", which would have been much worse. It does not: `is_managed()` is an allow-list
  consulted for a target the installer derived itself from `--home` and its own subpath table, never
  a source of paths. `uninstall()` is the one place a manifest value becomes a path acted on, and the
  containment check there holds.
- **A rejected alternative, chosen against during implementation.** `try`/`finally` around the loop
  rather than a `save_manifest()` per removal. Both make the record truthful; the `finally` writes
  once and keeps the existing single-write shape, and it keeps the failure visible. An
  `except OSError` was rejected outright: swallowing a failed `_rm` would report a successful
  uninstall over files still on disk, which is this defect inverted and is the direction the task's
  Risks section names.
- **A premise of this task's own test that turned out false, and the test was narrowed rather than
  the code changed.** The regression guard added here scans `install.py` for a bare subscript of any
  key `_OPTIONAL_ENTRY_TYPES` lists. Its first version scanned the whole file and failed, on
  `entry['name']` inside `_validate_manifest()`. That line is correct: it sits under an
  `isinstance(entry.get("name"), str)` guard, and the validator is definitionally the one function
  that inspects a shape before anything trusts it. Editing it to satisfy the assertion would have
  been the wrong repair, so the assertion now excludes the validator and separately asserts the
  guard it assumes is still there, which fails if that exclusion ever starts hiding something.
- **A seam left open deliberately.** `test_a_target_recorded_under_another_home_is_untouched_by_the_failure`
  passes against the unfixed code, because the old loop never reached `save_manifest()` at all and so
  could not damage another home's entries either. It is kept because it guards the fix rather than
  the defect: the `finally` now writes `others` back on every path, and that is the one way this
  change could break the `S-007` and `S-012` scoping. Four of the five tests here fail without the
  fix; this is the fifth and it is not evidence about the bug.

## Risks and rollback

Touches the installer's reversal path, which deletes files. The failure direction to avoid is a fix
that makes `uninstall()` quieter about an entry it cannot read: an entry with no `tool` should still
be removed and still be reported, with a placeholder, not skipped. Skipping would leave a file on
disk that the record stops claiming, which is this bug inverted.

Reversible by reverting one commit. Nothing persisted changes shape; the manifest is written by the
same `save_manifest()` either way.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test builds a manifest entry carrying `target` but no `tool` and no `name`, runs
      `uninstall()` against a temporary home, and asserts it returns rather than raising.
- [x] A test asserts that after a mid-loop failure the saved manifest no longer claims a target that
      was actually removed. Drive the failure through an entry the code cannot print, not through a
      patched `save_manifest`, so the test would still fail if the loop were restructured.
- [x] `--dry-run` over the same manifest completes and removes nothing.
- [x] The comment above `_OPTIONAL_ENTRY_TYPES` names every reader of every key it lists, including
      `uninstall()`.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
