---
id: feat-0069
title: Keep the person's watermark, and move it only on a prompt a person typed
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: [feat-0068]
spec: docs/spec/sitrep.md
scenarios: [S-021, S-022, S-023, S-024, S-025, S-026, S-040]
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

The prototype cleared the person's "since you last looked" marker whenever any session started, which
several concurrent sessions do constantly. The spec keeps a watermark per person and per repository,
outside the repository, and moves it only when a session transcript shows the person typed a prompt
after being shown a sitrep. `chore-0093` settled that the transcript, and not the prompt hook's input,
is where that can be told.

## Scope

**In scope:** the first look over seven days; recording which revision a sitrep described, for which
session and transcript; advancing the watermark at the next board from transcripts, counting only a
main-thread prompt marked `origin.kind: human` after the sitrep; the `reset` fallback for a vanished
commit; one watermark per person; `since` as a one-run override that leaves the stored watermark alone;
an unmarked prompt never counting.

This task extends `.agents/skills/sitrep/scripts/sitrep.py` and creates
`tests/test_sitrep_watermark.py`, with synthetic transcripts as fixtures.

**Out of scope:** the hook that calls the recording function at session start (`feat-0071`), and the
`--since` command-line flag, which `feat-0070` wires to the parameter this task provides.

## Implementation notes

- The person's state lives under their home directory, in a Claude-owned folder, never inside a
  repository. Tests point the home directory at a temporary one through the environment, so no new
  user-facing surface is needed for isolation.
- The repository key is the resolved `git rev-parse --git-common-dir`, so every worktree of one clone
  shares one watermark, which is the spec's definition of a repository.
- A transcript record counts only when `type` is `user`, `isSidechain` is false, `origin.kind` is
  `human`, and its timestamp is later than when the sitrep was shown. The most recent qualifying
  sitrep wins. A transcript that is missing or unreadable counts as no prompt, never as one.
- Recorded sitreps older than the chosen watermark are pruned, so the state stays small.
- Scenario layer: integration, with a temporary home, throwaway repositories, and JSONL transcripts
  shaped like the records `chore-0093` measured.

## Decisions

- **A seam left open deliberately.** `build_board()`'s temporary `base` parameter from `feat-0067`
  became `since`, the one-run override the spec's command table names, and `feat-0067`'s `S-011`
  test now passes its base that way.
- **A seam left open deliberately.** The first look uses the newest commit older than seven days
  as its base, and the empty tree when there is none, so commit count and task closures come from
  one range and cannot disagree. With linear history that range is exactly the commits dated
  within the window; with merges it is the commits reachable since that base.
- **A seam left open deliberately.** An explicit `since` that does not resolve falls back to a
  first look and names the revision in a notice, rather than failing the board.
- **A seam left open deliberately.** A person's state remembers at most fifty shown sitreps, and
  forgets every one at or before the sitrep that last moved the watermark, since none of those can
  move it further. Running a board without any shown sitrep writes nothing at all, so tests and
  one-off runs never create state under a real home directory.
- **Proven by breaking it.** Nine deliberate breaks were made to a copy of the script, one at a
  time, and each failed at least one test in `tests/test_sitrep_watermark.py`: an unmarked prompt
  counting, a side-chain prompt counting, a prompt from before the sitrep counting, the oldest
  answered sitrep winning, an explicit `since` consulting the watermark, a vanished watermark being
  trusted, state kept inside the repository, a seventy-day first look, and one state shared by
  every person. Four of the nine are caught only by tests added or strengthened after the first
  draft passed: a resumed session's earlier prompts, a marked side-chain prompt, two answered
  sitreps, and an explicit `since` with an answered sitrep pending.

## Risks and rollback

Required: this introduces a persisted per-person state format, and it reads a transcript field that
Anthropic does not document as a contract.

- **What could go wrong.** Claude Code could rename or drop `origin`. By S-040 the watermark would then
  stop moving rather than move wrongly, and every board would drift towards a first look.
- **Rollback.** Revert the one commit, and delete the person's sitrep state folder. No repository holds
  any of this state, so nothing in a repository needs undoing.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_sitrep_watermark.py" -v
    python scripts/run-checks.py

- [x] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [x] A test proves no file inside the repository changes when the watermark moves.
- [x] `docs/spec/sitrep.conformance.md` classifies these scenarios.
- [x] Existing tests still pass.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` not run in full: this task changes the draft skill's own body and nothing a
      reader-facing document describes, and the skill is not listed anywhere until `feat-0071`.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
