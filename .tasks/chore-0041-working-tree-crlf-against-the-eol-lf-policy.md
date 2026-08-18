---
id: chore-0041
title: Thirty tracked files carry CRLF on disk against the repository's own eol=lf policy, invisibly to git status
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: []
touched_files:
  - .gitattributes
  - CONTRIBUTING.md
created: 2026-08-18
---

## Problem

Measured 2026-08-18 on `developer` at `3f5000c`, with a clean working tree:

```text
$ git ls-files --eol | awk '{print $1, $2}' | sort | uniq -c
    197 i/lf w/lf
     30 i/lf w/crlf
      2 i/none w/none

$ git config --get core.autocrlf
true
```

Thirty tracked files are CRLF on disk while stored LF in the index. `.gitattributes` sets
`* text=auto eol=lf` plus explicit `eol=lf` for `.py`, `.md`, `.tmpl`, `.json`, `.sh` and `.mdc`, and
`eol=lf` overrides `core.autocrlf` on checkout, so a fresh clone writes all of them LF. These thirty
were rewritten with CRLF **after** checkout, by tooling writing files on Windows.

Three things make it worth a task rather than a shrug:

- **It is invisible.** `text=auto` normalises on the way back in, so `git status` and `git diff` are
  both clean and nothing reports the drift. It surfaced only from `git ls-files --eol`.
- **Two comparators here read bytes off disk rather than through git.** `install.py --check` digests
  installed files against recorded SHA256 values, and `check-provenance.py` digests fetched upstream
  bytes. The same source file can digest differently on Windows and Linux, and `bug-0019` and
  `bug-0020` are both open against that machinery.
- **`core.autocrlf=true` is set at repository scope and contradicts the intent.** Nothing in the repo
  asks for it, no global value is set, and the `.gitattributes` comment ("Text files are stored as LF in
  the repo; Git converts on checkout per each contributor's `core.autocrlf`") describes a behaviour the
  `eol=lf` line directly below it overrides. The comment is what would lead a contributor to set the
  config in the first place.

## Scope

**In scope:**

- Renormalise the working tree so on-disk endings match the policy (`git add --renormalize .`, which is
  a no-op in the index here because the index is already uniformly LF).
- Correct the `.gitattributes` comment so it describes what the file actually does: endings are LF in
  the index *and* on checkout, because `eol=lf` is explicit and wins over `core.autocrlf`.
- Record in `CONTRIBUTING.md` that `core.autocrlf` should not be set for this repository, with the
  `git ls-files --eol` command that shows whether a checkout has drifted.

**Out of scope:**

- Changing any file's **content**. This is line endings only, and any commit that mixes the two is
  unreviewable.
- Unsetting `core.autocrlf` in the author's local config. That is a per-machine setting a repository
  cannot and should not change on someone's behalf; documenting it is the correct reach.
- A pre-commit hook or a CI gate on line endings. Tempting, and a separate decision: CI checks out
  fresh so it would never fail, which means such a gate would prove nothing about the machine where the
  drift happens. If it is worth doing it is worth doing as its own task with that objection answered.
- `install.py --check` and `check-provenance.py`. Their open defects are `bug-0020` and `bug-0019`; this
  task removes a confounder, it does not fix them.

## Implementation notes

Run the renormalise and confirm it produces **no** index change before committing anything, since the
index is already LF. If it does produce one, stop: that means a file's stored form disagrees with the
policy, which is a different and larger problem than this task describes.

The verification that matters is not the renormalise, which is easy, but that
`git ls-files --eol | grep -c 'w/crlf'` returns `0` afterwards **and still returns `0` after the tools
in this repository have written files again**. Reproduce that: run `python scripts/run-checks.py`, which
writes into `.tmp/`, then re-count. If the count climbs, the finding is not stale state but an active
writer, and the task should name which writer and say so rather than renormalising on a loop.

The known writer class is Python writing text without an explicit newline: `Path.write_text()` and
`open(..., "w")` both translate `\n` to `\r\n` on Windows unless `newline=""` or `newline="\n"` is
passed. If a script in `scripts/` or a template writer in a skill does that to a tracked file, name it
in `## Decisions` even if fixing it lands elsewhere.

## Risks and rollback

Touches thirty files' bytes, so the diff is large while the semantic change is nil, and that combination
is exactly what hides a real edit. Commit the renormalise alone, with no content change beside it, so
the diff is verifiable as endings-only (`git diff --stat` before and after, and
`git diff --ignore-all-space` empty).

Reversible by reverting one commit. Because the index is already LF, a revert restores the on-disk state
and nothing else.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `git ls-files --eol | grep -c 'w/crlf'` returns `0`.
- [ ] The renormalise produced no index change, confirmed before committing.
- [ ] The endings-only commit shows no content change: `git diff --ignore-all-space` against its parent
      is empty for every file in it.
- [ ] The count is still `0` after `python scripts/run-checks.py` has run, or the active writer is named
      in `## Decisions`.
- [ ] `.gitattributes`'s comment describes what `eol=lf` actually does rather than deferring to
      `core.autocrlf`.
- [ ] `CONTRIBUTING.md` says not to set `core.autocrlf` here and gives the command that detects drift.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
