---
id: feat-0054
title: Serve the store as one dependency-free page, and answer the contribution-bar question with the skills report
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0053]
spec: docs/spec/agent-observatory.md
scenarios: [S-001, S-002]
touched_files:
  - scripts/
  - tests/
  - docs/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

[`feat-0053`](feat-0053-the-observatory-store-and-its-incremental-ingester.md) fills a store that
nothing reads. This task builds the surface that reads it, and the first report on it.

The skills report is first among the five for a reason the contribution-bar section of
[`AGENTS.md`](../../AGENTS.md) supplies: this kit asks of every skill whether it is genuinely used and
iterated on, and answers it from memory. `S-002` is the half that memory is worst at, because a skill
that quietly stopped being used produces no signal at all and looks exactly like one that is working.

Read [`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) for the contract. It is not
restated here.

**This task ends the walking skeleton.** After it, the remaining report tasks are independent
siblings and can be dispatched in parallel.

## Scope

**In scope:** the server, the page shell every later report renders into, and the skills report.

Files this task creates, with their exact paths:

- `scripts/observatory/serve.py`, a `ThreadingHTTPServer` with `main(argv)`
- `scripts/observatory/ui/index.html`, one page, no build step
- `docs/OBSERVATORY.md`, how to run it and what it never does

The page shell is a deliverable in its own right: later tasks add reports to it and must not each
reinvent layout, navigation, or the scope selector.

**Out of scope:**

- **Every other report.** Fleet is `feat-0055`, waves `feat-0056`, cost and pressure `feat-0057`,
  health `feat-0058`. Build the shell so they slot in; do not build them.
- **Live updating.** `feat-0059` owns it. This page renders what the store holds when it is requested.
- **Any control action.** `feat-0060` owns `S-019` and `S-020`. Add no action that references a
  session until that task defines the boundary.
- **A JavaScript toolchain.** No `package.json`, no bundler, no framework, no CDN. See the notes.
- **Changing the schema.** If a query cannot be answered, that is a finding against `feat-0053`, not
  a migration to slip in here.

## Implementation notes

**No third-party dependency, and this is the task most tempted to add one.** The scoped rule in the
"Out of scope by design" section of [`ROADMAP.md`](../../ROADMAP.md) narrowed the store and service
clauses and deliberately did not narrow this one. Charts are hand-rolled inline SVG. A chart library,
a CSS framework, and a font from a CDN are all out, and the last also breaks the no-network property
`S-022` establishes.

**`S-002` needs a roster the corpus cannot supply.** A skill that never appears in a transcript
appears nowhere in the store either, so the report cannot list it by reading the store alone. The
installed set has to come from the skill directories themselves. Read how
[`install.py`](../../scripts/install.py) resolves those locations rather than hardcoding a path, and
state in `docs/OBSERVATORY.md` which roster the report is counting against, because "never used" is
meaningless without it.

**Bind to the loopback interface only.** The contract forbids data leaving the machine, and a server
bound to all interfaces serves the corpus to the local network.

Prior art for the document's register: [`docs/INSTALL.md`](../../docs/INSTALL.md), which explains a
procedure without restating what belongs elsewhere.

## Risks and rollback

The task touches more than one module (the server, the page, and a new reader-facing document), so the
deterministic rule fires on the first condition.

The real risk is the page shell, because six later tasks inherit whatever it establishes and a shape
that cannot hold five reports is discovered after four of them are written. Sketch all five report
surfaces from the contract's Proposed Surface before committing to the layout, then implement one.

A server that binds beyond loopback would publish the corpus to the local network. That is the one
failure here with a consequence outside the repository, and it is a stated acceptance criterion rather
than an intention.

Reversible by reverting one commit. The store is untouched by this task and no data format changes.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] New tests cover S-001 and S-002, each named so the scenario it proves is identifiable.
- [x] Skill use counts equal the number of **distinct messages** carrying that attribution, not the
      number of lines in the corpus, asserted against a fixture rather than against the author's
      machine (S-001). Corrected 2026-08-28 at `feat-0053`'s closeout: a forked or resumed session
      replays earlier history verbatim, so 5,442 uuids appear in more than one transcript and a naive
      line count double-counts them. The store is right and the naive oracle is wrong; the criterion
      as first written was satisfiable only by adopting the double-count.
- [x] A skill present in the installed roster and absent from the corpus is reported with a count of
      zero rather than omitted (S-002).
- [x] The page loads and renders with the network unavailable, proving no external asset is fetched.
- [x] `grep -rniE "cdn|unpkg|jsdelivr|googleapis|<script src=\"http" scripts/observatory/ui/` returns
      nothing.
- [x] The server binds to loopback only, asserted by a test rather than by reading the source.
- [x] No `package.json`, lockfile, or `node_modules/` is introduced anywhere.
- [x] `docs/OBSERVATORY.md` states which installed-skill roster `S-002` counts against.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is updated for S-001 and S-002.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
