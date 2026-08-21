---
id: bug-0024
title: A structurally invalid manifest crashes with a traceback at exit 1, the code that means diverged
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0022]
touched_files:
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-08
---

## Problem

`load_manifest()` in [`install.py`](../../scripts/install.py) catches `json.JSONDecodeError`, so a
manifest of corrupt bytes degrades cleanly to an empty record. A manifest that **parses** but has the
wrong shape does not. Four shapes, all reproduced 2026-08-08:

```text
# entry missing "target"
install     rc=1   KeyError: 'target'                                    install.py:445
# entry with "target": null
--check     rc=1   TypeError: expected str, bytes or os.PathLike, not NoneType
--uninstall rc=1   TypeError: expected str, bytes or os.PathLike, not NoneType
# manifest is a JSON list rather than an object
--check     rc=1   TypeError: list indices must be integers or slices, not str
```

**The exit code is the defect, not the traceback.** All four exit 1, which in this tool's own
vocabulary means "at least one installed target has diverged from its source". The true state is "the
check could not run", which is exit 2. That precedence is argued at length in three places, the
`check()` docstring here, [`check-provenance.py`](../../scripts/check-provenance.py), and
[`run-checks.py`](../../scripts/run-checks.py), each for the same reason: a reader who treats a
could-not-run as a clean "no" is reasoning from an answer nobody produced. A caller scripting around
`--check` gets a confident wrong answer.

**The raw traceback is the second half.** `feat-0043` held `check-provenance.py` to "2 with a clear
message and no traceback" for an unreachable network. The manifest path has never been held to the
same bar, so a damaged per-machine record reads as a defect in the tool.

The manifest is gitignored and per-machine, so an interrupted write, a full disk, or a partially
synced home produces exactly these shapes. This is not a hostile-input problem; it is the ordinary
one.

## Scope

**In scope:** validate the manifest's structure where it is loaded, degrade to a stated exit 2 with a
message naming the manifest and what is wrong with it, and cover the shapes above with tests.

**Out of scope:**

- Repairing or rewriting a damaged manifest. Detect and report, per rule `A3` in
  [`autonomy.md`](../../.agents/rules/autonomy.md). Re-installing is the documented route back and it is
  a person's decision.
- Changing the manifest format. Nothing about the record on disk changes; only how a bad one is read.
- Treating an unrecognised extra key as an error. A forward-compatible reader ignores what it does
  not know; only a **missing or wrong-typed** field it depends on is a fault.

## Implementation notes

`load_manifest()` is the one chokepoint and the natural place for the check, but it currently returns
a value with no way to say "this was unreadable", and its three callers (`install`, `uninstall`,
`check`) want different things from that answer. `check` and `uninstall` should stop at exit 2.
`install` has a real choice: refusing to place anything is the conservative read, and treating an
unreadable record as an empty one would make every existing target report `CONFLICT`, which is the
documented behaviour for a **deleted** manifest already. Pick one, state it, and make the printed
message say which happened.

Minimum a valid entry needs, from the readers rather than from taste: `target` present and a string,
and `source` a string wherever it is used. `digests` is already handled by falsiness, deliberately,
per the comment at `_check_entry()`.

The message matters as much as the code. Name the manifest path, name the entry index or its `name`,
and name the remedy, which is to re-install and establish a fresh record. A message that says only
"invalid manifest" leaves the reader the investigation the report exists to save.

## Decisions

- **`install` refuses rather than treating an unreadable record as empty.** Rejected the
  empty-record read: it is the documented answer for a *deleted* manifest, where the tool
  genuinely knows nothing, but here it knows a record exists and is damaged, and the run would
  end in `save_manifest` writing a fresh record over it. That discards every target recorded
  under a home this run never looked at, and it is the only irreversible outcome on the table.
- **`load_manifest()` raises rather than returning a sentinel.** Rejected a tuple or a
  `None` return: all three callers stop, but each stops with different words, and a value
  that cannot carry a reason has every caller re-deriving one.
- **The corrupt-bytes and wrong-shape paths are deliberately asymmetric.** Bytes that do not
  parse still degrade to `{"entries": []}`; a file that parses stops the run. Out of scope
  per the acceptance criteria, and defensible (unparseable bytes never named an install, so
  reading them as nothing is truthful), but it is a seam: a reader may reasonably expect both
  to report exit 2 naming the file. Left open rather than closed by a drive-by.
- **Validation covers `tool`, `name`, and `digests` as well as `target` and `source`.** The
  task named the last two. The other three are dereferenced too: `check()` sorts on `tool`
  and `name`, which raises on a mixed-type list, and `_compare` iterates `digests` as a
  mapping. Faulted on only when present and wrong-typed, so an absent optional key and an
  unrecognised key are both still fine.
- **A premise that held.** The task's four shapes were reproduced 2026-08-08; all four still
  reproduce at `6a1f194` after `bug-0022`, `feat-0049`, and `chore-0042` edited this file.
  One detail differs: `install` with a null `target` did not crash, it exited 0 having placed
  nothing, which is the same wrong answer wearing a cleaner code.

## Risks and rollback

The failure direction to design against is a validator strict enough to reject a record written by a
future version of this tool, which would make an upgrade look like corruption. Ignore unknown keys;
fault only on what is read.

Changes how a persisted record is read, so it meets the rollback rule. Reversible by reverting one
commit; no manifest is rewritten, so nothing needs migrating back.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test per shape (missing `target`, null `target`, top-level list, entry that is not an object)
      asserting exit 2 and no traceback on stderr. Each must fail against the current `install.py`.
- [x] The printed message names the manifest path and the offending entry.
- [x] A valid manifest carrying an unknown extra key is still accepted.
- [x] The existing corrupt-JSON behaviour is unchanged.
- [x] Whatever `install` does with an unreadable record is asserted by a test, not left implicit.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
