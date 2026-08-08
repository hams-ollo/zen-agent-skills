---
id: bug-0019
title: An unreadable file drops all its provenance records and the run still reports success
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: []
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-06
---

## Problem

`collect()` in [`check-provenance.py`](../scripts/check-provenance.py) wraps its read in
`except OSError: continue`:

```python
for path in iter_provenance_files(root):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
```

A file the process cannot read contributes **no records at all**, is named nowhere in the output, and
the run exits 0 with a smaller count that looks exactly like a clean result.

Demonstrated 2026-08-06 during `bug-0016`'s verification, by holding a Windows exclusive handle
(`dwShareMode=0`) on one provenance-carrying file:

```
with the file readable : 9 records
with the file locked   : 8 records
```

The dropped file is mentioned nowhere and the exit code is 0 either way. A reader has no signal that
the count moved, because the count is the only thing reported and nothing states what it should have
been.

**This is `bug-0016` again, one function over.** That task fixed a blank line deleting a record inside
`parse_records()`; this deletes every record in a file inside `collect()`. Both exit 0. It was found
while verifying that fix and judged genuinely out of scope for it, because the trigger is unrelated
to the blank line and the code is in a different function.

**On Windows the trigger is ordinary, not exotic.** A file open in another process with an exclusive
handle, a virus scanner mid-scan, or an editor holding a lock all raise `OSError` here. This does not
require a corrupt disk.

**The direction of failure is the one this repository keeps choosing against.** A check that cannot
read part of its input should say so, not quietly narrow its scope and report success.

## Scope

**In scope:** make an unreadable file a reported condition rather than a silent skip: name the path,
say it could not be read, and exit non-zero. Tests covering the unreadable path with a stubbed
failure rather than a real lock, since a real one is not portable across Windows, macOS, and Linux.

**Out of scope:**

- Recovering the records from an unreadable file, which is not possible.
- `iter_provenance_files()`'s scan scope, which is a named constant with a stated reason.
- Automatic retry. A lock that clears on retry is still worth reporting, and a retry loop turns a
  fast check into a slow one.
- The related first-field-typo seam described below, which has a different cause.

## Implementation notes

**`check-provenance.py` already has the right exit code and does not need a new one.** `2` means the
run could not answer the question, which is what an unreadable file produces. Reuse it, matching the
unreachable-source path that already exits 2 with a clear message and no traceback.

**Report and keep going, rather than aborting on the first bad file.** One unreadable file should not
hide the state of the other seven. Collect the failures, report them all, and let the exit code carry
the verdict, which is the shape the drift and unlocatable paths already use.

**A related seam sits in `parse_records()` and is deliberately not this task.** A typo on the **first**
field after `source:` drops the whole block silently, even when the remaining four fields are
perfect: `source:` plus `autor:` plus three valid fields yields zero records. `bug-0016`'s decision
log names this seam but bounds it as "all fields misspelled", which its verifier showed is wider than
the truth. The behaviour predates `bug-0016` and is unchanged by it. Fixing it is a separate task
about grammar; this one is about I/O. Correct the bound in `bug-0016`'s log if that task is taken.

## Risks and rollback

The risk is that a repository with a genuinely unreadable file in scope now fails a check that used
to pass, which is the intended change and should be stated plainly in the message rather than
discovered. Rollback is one revert; nothing persisted changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] A test proving an unreadable provenance file is **named** in the output, failing against the
      current `collect()`.
- [ ] A test proving the run exits non-zero when a file cannot be read.
- [ ] A test proving the other files are still checked and reported, so one unreadable file does not
      abort the run.
- [ ] The failure is a clear message, not a traceback, matching the unreachable-source path.
- [ ] The test uses a stubbed read failure rather than a real OS lock, so it passes on Windows,
      macOS, and Linux.
- [ ] `python scripts/check-provenance.py --list` still reports 8 records across 7 files on a clean
      tree, and the live run still exits 0.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
