---
id: chore-0046
title: A contract-governed task can close with no conformance audit, because the gate that would catch it is installed and unregistered
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - AGENTS.md
created: 2026-08-19
---

## Problem

Nothing requires a task that implements part of a contract to say whether the implementation matches
it. The closeout lifecycle in `AGENTS.md`'s work-altitude-model section names four obligations: the
acceptance command passing, `depends_on` all done, a `doc-sync` pass, and the `done/` move plus a
CHANGELOG line and a ROADMAP strikethrough. Conformance is not among them.

The kit ships a hook for exactly this. [`spec-conformance-gate.py`](../../.agents/hooks/spec-conformance-gate.py)
fires when work a contract governs is closed with no audit of whether the implementation matches it.
It is placed by `--with-hooks` and it is **not registered** in the committed `.claude/settings.json`,
which carries exactly one hook by a deliberate exception the conventions section documents. So the
guard exists, is installed, and never runs.

The consequence is observable rather than theoretical, and `chore-0034` found it:
`docs/spec/cloud-executable.md` was approved on 2026-08-07, `feat-0045` and `feat-0046` both closed
against it, and it reached 2026-08-19 as the only approved spec of eleven with no conformance matrix
at all. Two closeouts passed every stated obligation while leaving the contract unaudited, because no
stated obligation mentions the contract. `install`'s matrix has the same shape of gap at a smaller
scale, covering 15 of its 18 scenarios since `bug-0018` added three on 2026-08-07.

## Scope

**In scope:** add a conformance obligation to the closeout lifecycle in `AGENTS.md`, beside the
existing `doc-sync` step.

- It applies only when the task declares a `spec`, since most tasks do not and a blanket obligation
  would be noise on every chore.
- It says what satisfies it: the spec's matrix covers the scenarios this task's `scenarios` field
  claims, produced or updated with [`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md).
- It says what to do when the matrix is deliberately owed rather than produced, which is the honest
  state for a forward spec whose implementation does not exist yet, and which both `cloud-executable`
  and `systematic-debugging` have legitimately been in. An obligation with no legal way to defer
  invites a matrix written to satisfy it, which is worse than no matrix.

**Out of scope:**

- **Registering the hook in `.claude/settings.json`.** Decided by the author on 2026-08-19: the
  written rule is the cheaper answer and it does not spend the one-committed-hook exception that the
  conventions section of `AGENTS.md` draws narrow and explains at length. An adopter who wants
  mechanical enforcement installs the hook with `--with-hooks` and registers it themselves, which is
  what the hooks module is for.
- The hook's own behaviour, which is correct and tested.
- Producing the missing matrices. `chore-0034` produced `cloud-executable`'s; `install`'s three
  scenarios are owed at `bug-0018`'s closeout and that is recorded where it belongs.
- The template `AGENTS.md.tmpl` that `init-worktracking` scaffolds. Whether an adopter's tracker
  should carry this obligation depends on whether they adopt the spec spine at all, and that is a
  separate question with its own answer.

## Implementation notes

Put it beside the `doc-sync` clause rather than in a new list, because the two are the same kind of
obligation: a check that the change did not leave a written artefact saying something untrue. Both
clauses in that section carry the incident that produced them, `bug-0011` and `feat-0031`; this one
should carry `cloud-executable` reaching eleven-of-eleven approved with zero-of-one matrices, since
that is the case that argues for it.

Keep it to the shape of the surrounding clauses. That section is read by every agent that closes a
task here, and it is already dense.

## Decisions

- **Rejected: registering [`spec-conformance-gate.py`](../../.agents/hooks/spec-conformance-gate.py) in
  `.claude/settings.json`.** Decided by the author on 2026-08-19 and restated here: the written rule
  costs nothing and does not widen the one-committed-hook exception, which the conventions section of
  `AGENTS.md` draws narrow and explains at length. `.claude/settings.json` is untouched.
- **Rejected: a test pinning the new clause.** The change is prose in a rules document with no
  executable surface, and the only test shape available would assert the exact wording, which fails
  on any future rewording that preserves the meaning. The one sentence of `AGENTS.md` a test does
  read is the S-006 bound in the acceptance-command section, which this change does not touch.
- **Seam left open deliberately: the obligation names no frontmatter key of its own.** It keys off
  the task's existing `spec` and `scenarios` fields rather than introducing a `conformance:` key or
  asking `validate.py` to enforce one, so `.tasks/validate.py` still cannot tell a deferred matrix
  from a missing one. That check is a separate decision, and mechanical enforcement remains available
  to an adopter through the hook.
- **Seam left open deliberately: `AGENTS.md.tmpl` is unchanged.** Whether an adopter's scaffolded
  tracker carries this obligation depends on whether they adopt the spec spine at all, which this
  task rules out of scope.

## Risks and rollback

One file, prose only, so the more-than-one-module rule does not fire.

The way this goes wrong is by being written without a deferral path, which would make the honest
answer for a forward spec, that the matrix is owed until something exists to audit, into a rule
violation. Two specs are legitimately in that state right now. State the deferral explicitly rather
than leaving it to judgment.

Reversible by reverting one commit. It changes what agents are asked to do at closeout, not what any
tool enforces, so nothing breaks if it is removed.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] The closeout lifecycle in `AGENTS.md` names a conformance obligation for tasks that declare a
      `spec`, beside the `doc-sync` step.
- [x] It names `spec-conformance` as what satisfies it and states the legal deferral for a spec with
      nothing built to audit yet.
- [x] It carries the incident that produced it, as the two neighbouring clauses do.
- [x] `.claude/settings.json` is unchanged, and the one-committed-hook exception in the conventions
      section still reads as accurate.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
