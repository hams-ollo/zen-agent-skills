---
id: feat-0055
title: Report every session across every project in one place, and say which are running now
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-012, S-018]
touched_files:
  - scripts/
  - tests/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

The harness shows one session at a time. Work now runs across many projects at once, and nothing says
which sessions exist, where, and which are still running.

This is the operational gap named third in the Problem section of
[`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md), and it is the report a person
opens first, because it is the only one that answers a question about right now rather than about the
past.

Read the contract for what must be true. It is not restated here.

## Scope

**In scope:** the fleet report, and the live-session source `S-012` needs.

- The report itself, in the page shell [`feat-0054`](feat-0054-the-local-server-the-page-shell-and-the-skills-report.md)
  establishes.
- A reader for the harness's live session registry, added to `scripts/observatory/ingest.py`.
- The project scoping that `S-018` requires, in the shell's scope selector, so every later report
  inherits it rather than each building its own.

**Out of scope:**

- **Any action on a session.** `feat-0060` owns `S-019` and `S-020` and defines what the surface may
  offer. Add no link, button, or command that targets a session before it lands.
- **Live refresh.** `feat-0059` owns `S-013`. Running-versus-ended here is correct as of when the
  report was requested.
- **Cost or token figures.** `feat-0057` owns those columns.
- **Inferring liveness from timestamps.** See the notes.

## Implementation notes

**`S-012` needs a real liveness source, not a heuristic.** A session whose last record is recent is
not thereby running, and one idle for an hour may still be. Read the harness's own registry of live
sessions rather than inferring from the corpus, and confirm what that registry actually contains
before depending on a field.

**A registry entry can outlive its process.** A crashed session may leave its entry behind, so
treating presence as proof of liveness will report dead sessions as running. Decide what the report
does about a stale entry and say so in the report itself rather than silently trusting the file.

**`S-018` is an arithmetic claim, not a filter.** The contract requires that per-project figures sum
to the unrestricted figures, which is what makes the scope selector trustworthy rather than merely
present. A session whose working directory sits outside every known project must therefore still be
counted somewhere, not dropped.

Project directory names encode path separators, and the working directories recorded in the corpus
are platform-native. Neither may be assumed POSIX, per the contract's Constraints.

## Risks and rollback

The task touches more than one module, the ingester and the page, so the deterministic rule fires on
the first condition. If holding live-session state needs a table, the second condition fires too, and
the migration must be forward-only per the schema discipline `feat-0053` establishes.

**The consequential risk is reporting a dead session as running.** A registry entry can outlive the
process that wrote it, so presence is evidence and not proof. A fleet report that confidently shows a
crashed session as live is worse than one that says it cannot tell, because the whole value of this
report is answering a question about now.

The second risk is quiet rather than loud: dropping a session whose working directory matches no known
project would leave `S-018`'s summing property false while every panel still rendered. That is why the
criterion below is arithmetic rather than visual.

Rollback is reverting one commit and rebuilding the store, which is derived data with an authoritative
source on disk. Nothing the harness owns is written to at any point.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] New tests cover S-012 and S-018, each named so the scenario it proves is identifiable.
- [x] A session present in the live registry is reported as running; one absent from it is reported as
      ended, with its project, branch, and last activity (S-012).
- [x] Per-project figures sum across all projects to the unrestricted figures, asserted arithmetically
      rather than by inspection (S-018).
- [x] A session whose working directory matches no known project is still counted, not dropped.
- [x] A stale registry entry produces the documented outcome rather than an unqualified "running".
- [x] The report renders with the live registry absent or empty, without error.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is updated for S-012 and S-018.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
