---
id: chore-0041
title: Thirty tracked files carry CRLF on disk against the repository's own eol=lf policy, invisibly to git status
type: chore
status: done
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

## Decisions

- **Premise that turned out false: `core.autocrlf=true` is not set at repository scope.** The Problem
  section infers scope from `git config --get core.autocrlf`, which reports the effective value and not
  where it came from. `git config --show-origin --get-all core.autocrlf` reports exactly one source,
  `file:C:/Program Files/Git/etc/gitconfig`, the Git for Windows installer default at **system** scope.
  There is no repository-scope and no global value. This changes the remedy rather than the finding:
  it is not a stray setting somebody added here that should be removed, it is the platform default that
  every Windows contributor will have and cannot reasonably be told to unset. `eol=lf` already
  neutralises it, so `CONTRIBUTING.md` says that plainly instead of asking anyone to change a config.

- **Seam left open deliberately: the renormalise was not performed.** Four of the seven acceptance
  criteria (the `w/crlf` count, the no-index-change confirmation, the endings-only commit, and the
  post-`run-checks.py` recount) describe a working-tree rewrite touching thirty files. Dispatch scoped
  this run to the two `touched_files` only, because a bulk rewrite collides with every branch in flight.
  Worth recording for whoever picks it up: in a **fresh** worktree the count is already `0`
  (`237 i/lf w/lf`, `2 i/none w/none`), before and after `python scripts/run-checks.py`. The thirty
  files are a property of the author's long-lived checkout, not of a clone, so the renormalise is a
  one-machine cleanup and not a repository defect.

- **Seam left open deliberately: no writer in `scripts/` writes a tracked file in text mode, so the
  active writer is still unnamed.** The Implementation notes ask for one. The only two text-mode write
  sites are `_write` in `../scripts/build-adapters.py` and the manifest write in `../scripts/install.py`,
  and both call `Path.write_text(content, encoding="utf-8")` with no `newline` argument, so both do emit
  CRLF on Windows. Neither writes a file tracked here: one writes generated adapters, the other writes
  `.install-manifest.json`. `install.py` copies payload files with `shutil` and digests
  `path.read_bytes()`, so the install path is byte-exact and inherits CRLF from the source file on disk
  rather than creating it. The thirty files were therefore rewritten by something outside `scripts/`,
  most likely an editor or an agent harness tool, which no change in this repository can prevent.
  `CONTRIBUTING.md` gains the `newline=""` rule as prevention for the two sites that do exist.

## Risks and rollback

Touches thirty files' bytes, so the diff is large while the semantic change is nil, and that combination
is exactly what hides a real edit. Commit the renormalise alone, with no content change beside it, so
the diff is verifiable as endings-only (`git diff --stat` before and after, and
`git diff --ignore-all-space` empty).

Reversible by reverting one commit. Because the index is already LF, a revert restores the on-disk state
and nothing else.

## Decisions

- **2026-08-18: split, rather than tick four criteria this run did not meet.** The task was written
  with seven criteria, four of which describe a bulk working-tree renormalise. The dispatch scoped
  that out (`touched_files` is two policy files), so closing with all seven ticked would be the
  false bookkeeping this repository has an incident on record about. The policy and documentation
  half is complete and verified; the renormalise half is now
  [`chore-0042`](../chore-0042-renormalise-the-authors-working-tree.md).
- **2026-08-18: the successor is re-scoped, because this run falsified the original premise.** The
  problem statement said `core.autocrlf=true` is set at repository scope with no global value.
  `git config --show-origin` shows it at **system** scope,
  `C:/Program Files/Git/etc/gitconfig`, the Git for Windows installer default, with no repository
  and no global value. The original read came from bare `git config --get`, which reports the
  effective value and not its origin. So there is nothing here to unset, and `eol=lf` already
  neutralises it. Measured the same day: a fresh worktree reports `0` files at `w/crlf` while the
  author's long-lived checkout reports `30`, so this is a one-machine cleanup and not a property of
  the repository.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] The four renormalise criteria that stood here were split out to [`chore-0042`](../chore-0042-renormalise-the-authors-working-tree.md) before this task closed, re-scoped from what the run measured. See the decisions section.
- [x] `.gitattributes`'s comment describes what `eol=lf` actually does rather than deferring to
      `core.autocrlf`.
- [x] `CONTRIBUTING.md` says not to set `core.autocrlf` here and gives the command that detects drift.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
