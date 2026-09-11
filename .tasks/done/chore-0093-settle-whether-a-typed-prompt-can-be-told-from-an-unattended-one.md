---
id: chore-0093
title: Settle whether a prompt a person typed can be told apart from one nobody typed
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: []
spec: docs/spec/sitrep.md
scenarios: [S-022, S-023, S-025, S-040]
touched_files:
  - docs/spec/sitrep.md
  - docs/spec/README.md
  - ROADMAP.md
created: 2026-09-11
---

## Problem

[`sitrep`](../../docs/spec/sitrep.md) moves a person's "since you caught up" watermark only when that
person replies (`S-022`), and never when a session nobody types in runs (`S-023`). Its second Open
Question asked whether the harness can tell those two apart at all, and recommended a spike before the
spec was decomposed. Nothing in this kit had checked, and two approved scenarios rested on the answer.

## Scope

**In scope:** measure what the harness exposes, decide whether `S-022` and `S-023` can be met, and
amend the spec to match what was found.

**Out of scope:** any implementation, and every other scenario.

## Implementation notes

Four measurements, taken 2026-09-11.

1. **The prompt hook's input carries no author.** Anthropic's hooks reference
   (`https://code.claude.com/docs/en/hooks.md`, fetched 2026-09-11) gives `UserPromptSubmit` the common
   fields (`session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`) plus
   `prompt`, and nothing that says who wrote it. The same page says the transcript is written
   asynchronously and may not yet hold the current turn when a hook fires.
2. **Two session kinds are marked in the hook's world.** A hook firing inside a sub-agent carries
   `agent_id`, and a remote web session sets `CLAUDE_CODE_REMOTE=true` (same page).
3. **The transcript marks every typed prompt.** Over 626 transcripts under `~/.claude/projects`, on
   main-thread prompts that are neither tool results nor meta records, typed prompts carry
   `origin.kind: human` (1,647 records), background-agent completions arrive in the main thread as
   `origin.kind: task-notification` (490), and sub-agent prompts sit in the side chain with no
   `origin` (468). The main-thread prompts with no `origin` are harness text: `[Request interrupted by
   user`, compaction summaries, and slash-command echoes. Every version from 2.1.197 to 2.1.266 marks
   typed prompts.
4. **A print-mode prompt carries no mark, and `entrypoint` does not help.** One `claude -p` run
   (v2.1.232) in a scratch directory produced a prompt with no `origin`, and its `entrypoint` read
   `claude-desktop`, the same value every interactive desktop session on this machine records.

## Decisions

- **A premise that turned out false.** The approved session-moments table assumed a hook on the
  person's message could tell who sent it. That hook's input cannot, and the transcript that can may
  lag it.
- **A rejected alternative.** An asynchronous prompt hook that waits and then reads the transcript. It
  depends on timing, and a slow write would silently drop a real reply.
- **Chosen.** The session-start hook records which revision each sitrep described, and the next board
  advances the watermark by reading those sessions' transcripts for a prompt marked as typed by a
  person after the sitrep. Anything unmarked counts as unattended (`S-040`), so a harness that stopped
  writing the mark would fail toward the watermark not moving, not toward a false catch-up.
- **A seam left open deliberately.** `origin` is a transcript field Anthropic does not document as a
  contract. If it is renamed or dropped, the watermark stops moving rather than moving wrongly;
  noticing that and saying so is left to the implementation.
- **A seam left open deliberately.** Whether `UserPromptSubmit` fires for a task notification was not
  checked, because the chosen design does not depend on it.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] The spec's second Open Question is settled, with the evidence above, in a dated header note that
      marks the amendment as pending the author's re-approval, and the spec states `status: approved`.
- [x] Scenario ids run gapless from `S-001` to `S-040`, and no approved scenario was renumbered.
- [x] [`docs/spec/README.md`](../../docs/spec/README.md) lists the amendment in the author's
      re-approval queue.
- [x] Existing tests still pass.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` not run, and the reason: this changes a spec, the spec index and one roadmap block,
      and no reader-facing document describes the sitrep yet. Its `docs/CATALOG.md` entry is owed when
      the skill itself lands as a draft.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing
      this task id.
