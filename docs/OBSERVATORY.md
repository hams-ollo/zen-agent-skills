# Agent observatory

A local reporting surface over the session corpus this repository's own agent runs produce. It
answers what was used, what it cost, what it produced, and what is running, across every project
at once, and it changes nothing that it reads.

**This is maintainer tooling, not a deliverable.** [`install.py`](../scripts/install.py) never
places it and no adopter receives it, which is the scope `chore-0076` recorded in
[`AGENTS.md`](../AGENTS.md). The standard-library rule still governs it, so everything below runs
on a bare Python 3 with no install step.

The behavioral contract is [`docs/spec/agent-observatory.md`](spec/agent-observatory.md). This
document says how to run the thing and what it will not do; it does not restate the contract.

## Run it

Two steps, in order. The first reads the corpus into a local store; the second serves the store.

```bash
python scripts/observatory/ingest.py
python scripts/observatory/serve.py
```

Then open `http://127.0.0.1:8787/`.

`ingest.py` is incremental: the first run reads the whole corpus (401 MB and about two minutes on
this maintainer's machine), and every run after it reads only what has been appended since. Run it
again whenever you want the page to reflect newer work. The page renders whatever the store held
when the request was made; a report that updates while a session is running is `feat-0059`'s.

| Option | Applies to | Default |
|---|---|---|
| `--corpus DIR` | `ingest.py` | `~/.claude/projects` |
| `--store PATH` | both | `.observatory/store.db`, gitignored |
| `--host ADDR` | `serve.py` | `127.0.0.1`. A non-loopback address is refused. |
| `--port N` | `serve.py` | `8787` |

The store is derived data with the corpus as its authoritative source, so it is always safe to
delete and rebuild. Deleting it is also the fix for the one error `ingest.py` refuses to work
around: a store written by a newer schema than the code reading it.

## What the page reports

Five reports, each answering one question over the whole corpus or one project. The scope selector
in the header switches between them.

| Report | Question | Status |
|---|---|---|
| Fleet | Which sessions exist, where, and which are running? | Owed by `feat-0055` |
| Skills | Which skills are used, how often, and which never are? | Built |
| Waves | What did a dispatched wave run, cost, and produce? | Owed by `feat-0056` |
| Cost and pressure | What was consumed, and how close to a limit? | Owed by `feat-0057` |
| Health | What failed, and how often? | Owed by `feat-0058` |

An owed report has a tab and says which task owes it rather than showing an empty panel.

## Which roster the skills report counts against

The corpus cannot supply the set of skills that exist. A skill nobody has ever used appears in no
transcript, so it appears nowhere in the store either, and a report built from the store alone
would silently define "every skill" as "every skill somebody used". That makes the one figure the
report exists for, the count of skills never used, unreachable.

So the roster comes from the skill directories themselves, and specifically from
[`install.py`](../scripts/install.py)'s own `discover_skills()`: **every directory under
[`.agents/skills/`](../.agents/skills/) holding a `SKILL.md`.** That is the set this kit ships, and
it is the set the contribution-bar section of [`AGENTS.md`](../AGENTS.md) asks its question about.
Reading it through the installer rather than from a path written into the server means the two
cannot come to disagree about what the installed set is.

Two consequences worth stating plainly, because "never used" means nothing without them:

- **A skill in the roster and absent from the corpus is reported with a count of zero**, not left
  out. As of 2026-08-28 that is eight of twenty: `doc-author`, `doc-revise`, `house-review`,
  `project-bootstrap`, `review-depth`, `test-author`, `test-quality`, and `verifier-agent`.
- **A skill in the corpus and absent from the roster is still reported**, marked as not in the
  roster. The harness also attributes messages to skills this kit does not ship, such as
  `code-review`, `claude-api`, and `anthropic-skills:brain-dump`. Dropping them would understate
  the total; counting them as roster skills would overstate the roster.

A use is **one message carrying that skill's attribution**, counted once. It is not a line in the
corpus: a forked or resumed session replays earlier history verbatim into a new transcript, so
5,442 message ids on this maintainer's machine appear in more than one transcript, and counting
lines would report every one of them twice.

## What it never does

- **It never reaches the network.** No rate lookup, no font, no chart library, no content delivery
  network. The page carries its own styles and its own script inline and requests no subresource at
  all, so it renders with the network unavailable, and every chart is hand-rolled inline SVG.
- **It never binds beyond loopback.** `serve.py` refuses any address that is not a loopback
  address, before it binds rather than after. A server on all interfaces would publish the whole
  session corpus to whatever network the machine is on, and that is the one failure here with a
  consequence outside this repository.
- **It never writes to anything the harness owns.** Transcripts are opened read-only and the store
  lives outside the corpus. The page performs no write at all: every route is a read, and a request
  method that exists to change something is declined.
- **It never touches a session.** No start, resume, interrupt, or end. The surface offers no action
  against a session in any form; `feat-0060` is where a navigation action would be defined, and
  until then there is none.
- **It adds no dependency.** No package manager, no lockfile, no bundler, no framework. Standard
  library on the Python side and nothing at all on the page's.

## Where the code is

| File | Holds |
|---|---|
| [`scripts/observatory/db.py`](../scripts/observatory/db.py) | The store: schema, forward-only migrations, the connection helper. |
| [`scripts/observatory/ingest.py`](../scripts/observatory/ingest.py) | The incremental reader, from the corpus into the store. |
| [`scripts/observatory/serve.py`](../scripts/observatory/serve.py) | The loopback server, the report registry, and the skills report. |
| [`scripts/observatory/ui/index.html`](../scripts/observatory/ui/index.html) | The page shell every report renders into. One file, no build step. |
| [`tests/test_observatory.py`](../tests/test_observatory.py) | The store and ingester tests. |
| [`tests/test_observatory_serve.py`](../tests/test_observatory_serve.py) | The server, page shell, and skills report tests. |

A later report is added by serving a JSON endpoint from `serve.py`, registering it in that file's
`REPORTS`, and adding one function to `RENDERERS` in the page. The layout, the navigation, and the
scope selector are the shell's and should not need to change.
