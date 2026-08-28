---
id: feat-0059
title: Make the report follow a running session, and let an optional event source lower the latency without changing the figures
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-013, S-014, S-015]
touched_files:
  - scripts/
  - tests/
  - docs/
  - .agents/hooks/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

Every report built so far is a snapshot taken when it was requested. Goal 7 of
[`docs/spec/agent-observatory.md`](../docs/spec/agent-observatory.md) requires it to follow a session
that is still working, which is what makes the fleet report answer a question about now rather than
about a moment that has passed.

The contract splits this deliberately. `S-013` requires the report to update. `S-014` requires that to
work with no optional source configured, so the default path depends on nothing a user has to install.
`S-015` allows an optional source to lower the latency and forbids it from changing any figure.

That ordering is the point: the low-latency path is an enhancement, never a prerequisite.

Read the contract for what must be true. It is not restated here.

## Scope

**In scope:** the default live path, and the optional event source behind it.

- Tailing the corpus for appended records, reusing the incremental read
  [`feat-0053`](done/feat-0053-the-observatory-store-and-its-incremental-ingester.md) built rather than a
  second mechanism.
- Pushing updates to the open page, so `S-013` holds with no source configured.
- An opt-in event receiver on the server, and a hook that feeds it, placed under `.agents/hooks/`
  following that module's reminder shape.
- The stated latency characteristic `S-014` requires, in `docs/OBSERVATORY.md`.

**Out of scope:**

- **Registering the hook in [`.claude/settings.json`](../.claude/settings.json).** See the notes; this
  is a hard boundary, not a preference.
- **OpenTelemetry.** `S-015` is satisfied by the hook source alone. An OTel receiver is a later
  addition and needs ROADMAP Epic E item 7(a) to have landed first.
- **Any new figure.** This task changes when a number appears, never which numbers exist.
- **Reconnecting logic beyond the obvious.** A page whose connection drops may be reloaded.

## Implementation notes

**The committed hook registration stays at exactly one.** The conventions section of
[`AGENTS.md`](../AGENTS.md) records the single committed exception and states that adding a second
hook to that file, or any hook that blocks, is a new decision not covered by it. This task does not
make that decision. The hook is placed by `install.py --with-hooks`, its registration is printed for a
person to paste, and the file is not edited.

**The hook never blocks and never fails a session.** If the server is not running, the hook exits
cleanly and the session continues unaffected. A dashboard that can break a coding session is worse
than no dashboard, and this is the only part of the observatory that runs inside someone else's
process.

**`S-015` forbids double counting, which is the specific bug this design invites.** An event arriving
by hook describes work that will also appear in the corpus moments later. Decide the reconciliation
rule and pin it with a test that ingests both paths for the same work and asserts the figures match
the corpus-only run exactly.

**State the default path's latency as a number in `docs/OBSERVATORY.md`.** `S-014` requires the
absence of the optional source to be a stated characteristic rather than an error, and a reader
cannot judge "slower" without knowing by how much.

## Risks and rollback

The task touches more than one module, so the deterministic rule fires on the first condition. It also
ships a hook that runs inside a live session, which is the highest-consequence thing the observatory
does.

The failure that matters is a hook that blocks, slows, or crashes a real session. Mitigations are
stated as acceptance criteria rather than intentions: the reminder shape, a clean exit when the server
is absent, and a bounded timeout.

The second risk is double counting under `S-015`, which corrupts figures quietly rather than loudly. A
figure that silently drifts from the corpus is worse than a missing report, so the reconciliation rule
is tested against a corpus-only baseline.

Rollback is reverting one commit and not registering the hook. No schema changes, and the store can be
rebuilt from the corpus.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] New tests cover S-013, S-014, and S-015, each named so the scenario it proves is identifiable.
- [ ] With no optional source configured, an open report reflects newly appended records without being
      requested again (S-013, S-014).
- [ ] The absence of the optional source produces no error, and the default latency is stated as a
      number in `docs/OBSERVATORY.md` (S-014).
- [ ] With the event source active, reported figures are identical to a corpus-only run over the same
      work, asserted by comparing both (S-015).
- [ ] Each event records which source it arrived from (S-015).
- [ ] The hook exits cleanly and blocks nothing when the server is not running, asserted by a test.
- [ ] `git diff` shows no change to `.claude/settings.json`.
- [ ] `install.py --with-hooks` places the hook and prints its registration rather than applying it.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `agent-observatory` conformance matrix is updated for S-013, S-014, and S-015.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
