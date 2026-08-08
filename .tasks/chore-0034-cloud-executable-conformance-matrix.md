---
id: chore-0034
title: cloud-executable is the one approved spec with no conformance matrix, and two tasks closed against it
type: chore
status: open
priority: P1
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: [bug-0021]
spec: "docs/spec/cloud-executable.md"
scenarios: []
touched_files:
  - docs/spec/README.md
created: 2026-08-08
---

## Problem

[`cloud-executable.md`](../docs/spec/cloud-executable.md) carries 19 scenarios and no
`cloud-executable.conformance.md`. It is the tenth of ten approved specs and the only one without a
matrix, which [`docs/spec/README.md`](../docs/spec/README.md) states honestly: "Nine carry 121 of
those scenarios and every one has a conformance matrix".

Two tasks closed against it anyway. `feat-0045` (`S-001` to `S-007`) and `feat-0046` (`S-008` to
`S-016`) both carry `status: done` and `spec: docs/spec/cloud-executable.md`, neither declares a
`conformance:` key, and no matrix existed at either closeout.

**The gate that exists to prevent this did not fire.** Replaying both task files through
`evaluate()` in [`spec-conformance-gate.py`](../.agents/hooks/spec-conformance-gate.py), 2026-08-08:

```text
feat-0045-committed-acceptance-command.md:    BLOCK
feat-0046-session-start-reachability-hook.md: BLOCK
```

The gate is registered in `.codex/hooks.json`, in the opencode plugin, and in the registration
`install.py` prints. It is not registered in [`.claude/settings.json`](../.claude/settings.json),
which is the only wiring that runs in a Claude Code session here, and that narrowness is deliberate:
the conventions section of [`AGENTS.md`](../AGENTS.md) grants the committed-settings exception to one
hook, in the reminder shape, and states that a second one "is a new decision and not covered by this
one". So the rule had no enforcement path in the harness this repository is actually developed in.

The lifecycle in `AGENTS.md` is the other half. Its closeout list names the acceptance command,
`depends_on`, `doc-sync`, the `done/` move, the changelog line, and the roadmap strike. It does not
name producing a conformance matrix, so nothing in the written procedure asked for one either.

## Scope

**In scope:** write `docs/spec/cloud-executable.conformance.md`, auditing all 19 scenarios and every
Proposed Surface row against what is implemented, and update the index counts in `docs/spec/README.md`
to match.

**Out of scope:**

- Registering the gate in `.claude/settings.json`. See the open question below; it is the author's
  call and not this task's.
- Re-opening `feat-0045` or `feat-0046`. The matrix records what is true now; it is not a
  reprimand, and editing a closed task file is what the ledger convention exists to prevent.
- The Phase 4 proof run. `S-017` to `S-019` are unverified and stay that way; the matrix records them
  as such rather than pretending otherwise.

## Implementation notes

Run [`spec-conformance`](../.agents/skills/spec-conformance/SKILL.md) over the contract. Its coverage
proof is the part that matters here: an empty unreconciled list is valid only alongside the audited
set, and the audited set must be all 19 scenarios and every surface row, stated with the arithmetic
rather than the claim.

Two things the matrix should be expected to find, so a clean result is a signal rather than a
formality:

- `S-017` to `S-019` are **unbuilt**, not conformed. The proof run did not happen, and
  [`cloud-executable.verification.md`](../docs/spec/cloud-executable.verification.md) records why with
  a `blocked` verdict.
- `S-008` and `S-010` are what [`bug-0021`](bug-0021-reachability-counts-any-skill-not-a-kit-skill.md)
  is fixing. `depends_on` is set to that task deliberately: auditing before the fix would record a
  divergence that is already understood and queued, and the matrix would be stale on the day it
  landed.

The evidence column should distinguish a scenario proved by a test from one proved by reading a
clause, which is the distinction `tracker-links.conformance.md` draws in its Observations section and
the reason that matrix is worth reading. Nine of these scenarios are code and are testable; the rest
are properties of a hook's silence or of a workflow file.

## Open question for the author, to record rather than decide

Should [`spec-conformance-gate.py`](../.agents/hooks/spec-conformance-gate.py) be registered in the
committed `.claude/settings.json`? It would enforce the rule in the harness this repository is
developed in, and it would widen an exception `AGENTS.md` deliberately drew narrow to one
non-blocking hook. There is a second cost worth weighing rather than discovering: the gate matches on
any edit to a matching file, so `feat-0045` and `feat-0046` in `.tasks/done/` would block every future
edit to them until a matrix exists, which is a permanent trip-wire on a historical record. Writing the
matrix removes that particular instance and does not answer the general question.

A cheaper alternative also exists and should be weighed alongside: add the conformance step to the
task closeout lifecycle in `AGENTS.md`, where `doc-sync` already sits, so the rule is written into the
procedure rather than enforced by a hook nobody registered.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `docs/spec/cloud-executable.conformance.md` exists, with the frontmatter shape the other
      matrices use.
- [ ] Every one of the 19 scenarios appears in the matrix with a status and named evidence.
- [ ] Every Proposed Surface row appears with a status and named evidence.
- [ ] The coverage proof states the audited set and the unreconciled set explicitly, with the
      arithmetic, and does not claim a range wider than the scenarios that exist.
- [ ] `S-017` to `S-019` are recorded as unbuilt, citing the blocked verification record.
- [ ] `docs/spec/README.md`'s counts are corrected: ten specs with a matrix, and the scenario totals
      recomputed rather than incremented.
- [ ] Every relative link in the new file resolves from `docs/spec/`.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
