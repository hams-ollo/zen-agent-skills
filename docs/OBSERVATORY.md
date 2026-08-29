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
when the request was made, and the fleet report additionally reads the live-session registry on each
request, so both are correct as of when you asked and no more. A report that updates while a session
is running is `feat-0059`'s.

| Option | Applies to | Default |
|---|---|---|
| `--corpus DIR` | both | `~/.claude/projects`. `serve.py` reads it for one thing only: placing a live session the store has not seen yet. |
| `--store PATH` | both | `.observatory/store.db`, gitignored |
| `--registry DIR` | `serve.py` | `~/.claude/sessions`, the harness's own list of running sessions |
| `--host ADDR` | `serve.py` | `127.0.0.1`. A non-loopback address is refused. |
| `--port N` | `serve.py` | `8787` |

The store is derived data with the corpus as its authoritative source, so it is always safe to
delete and rebuild. Deleting it is also the fix for the one error `ingest.py` refuses to work
around: a store written by a newer schema than the code reading it.

## What the page reports

Five reports, each answering one question over the whole corpus or one project. The tabs switch
between reports, and the scope selector in the header restricts whichever one is open to a single
project.

| Report | Question | Status |
|---|---|---|
| Fleet | Which sessions exist, where, and which are running? | Built |
| Skills | Which skills are used, how often, and which never are? | Built |
| Waves | What did a dispatched wave run, cost, and produce? | Owed by `feat-0056` |
| Cost and pressure | What was consumed, and how close to a limit? | Owed by `feat-0057` |
| Health | What failed, and how often? | Owed by `feat-0058` |

An owed report has a tab and says which task owes it rather than showing an empty panel. Fleet leads
the list and is what opens, because it is the only one that answers a question about now.

## How the fleet report knows a session is running

Not from the corpus. A session whose last record is recent is not thereby running, and one idle for
an hour may still be, so nothing here infers liveness from a timestamp. It reads the harness's own
list of running sessions at `~/.claude/sessions/`, one file per session, and reads it on every
request rather than at ingest time, because an answer stored at the last ingest would be as old as
that ingest.

**Presence in that list is evidence, not proof.** A crashed session can leave its entry behind, and a
report that confidently shows a dead session as live is worse than one that says it cannot tell,
since answering about now is the whole value of this report. So the entry is corroborated against the
operating system before anything is called running, and the page says which check it ran:

| Outcome | What was established |
|---|---|
| running | The entry's process is confirmed. On Windows the pid must exist, and **wherever the entry records a start time it must match**, so a pid the operating system has since handed to another program is not mistaken for the session. An entry carrying no start time is confirmed on presence alone. On macOS and Linux it is **presence** only, because the recorded start time's meaning there is unverified, and a reused pid would read as running. |
| ended | Either there is no entry, or there is one and its process is gone. The second case is counted separately as a stale entry rather than folded quietly into the first. |
| unverified | There is an entry and the check could not be run, for instance because it was written by another machine. Never reported as running. |

Two bounds are worth stating rather than leaving to be discovered. **A session absent from the list
is reported ended**, and every entry observed so far has been an interactive session, so whether a
background or cloud session registers at all is unverified here. And **a session that started since
the last ingest** has no store row yet, so it is reported running with its project taken from the
transcript beside it, and its branch and last activity shown as not yet ingested.

## What the page can do to a session, in full

Three things, and this list is the whole of it:

| Action | What it does | Why it cannot reach a session |
|---|---|---|
| Open the pull request | Follows a link to the session's pull request | A link you choose to follow is a request your browser makes, not one this page makes |
| Copy the working directory | Puts the path on your clipboard | A `file://` link from an `http://` page is blocked by browsers, so the path is offered as text |
| Copy a resume command | Puts `claude --resume <session>` on your clipboard | Presenting a command is not running it, and running it is yours to do |

**The list is enforced rather than promised.** The three live in a registry in the server, the page
builds every one of them in a single place and tags each with the action it came from, and a test
resolves the two against each other. A button added to the page without an entry in that registry
fails the suite; so does an entry whose kind is anything other than navigation or a command to copy.
That is what makes "this surface changes no session" a claim you can check instead of a promise you
have to trust.

Starting, resuming, interrupting, and ending a session are excluded by the contract itself, not by
this page's implementation. Where those are possible at all, they are the companion skill's, and it
runs inside a session rather than in this page.

## Every project, in one place

Every report covers the whole corpus by default and can be restricted to one project. The property
that makes the scope selector trustworthy rather than merely present is arithmetic: restrict the
fleet report to each project in turn, add the figures up, and you get the unrestricted figures.

That is why a session nothing can attribute to a project is counted under `(unattributed)` rather
than dropped. Dropping it would leave the sum quietly wrong while every panel still rendered.

The same identity holds for the skills report, with one bound: a message that appears under two
projects would be counted once in the total and once in each project. That happens when a forked
session replays history into a different project's directory, and it does not occur in this
maintainer's corpus, where 0 of 54,222 messages appear under more than one project as of 2026-08-28.

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
  out. As of 2026-08-29 that is nine of twenty-one: `agent-observatory`, `doc-author`,
  `doc-revise`, `house-review`, `project-bootstrap`, `review-depth`, `test-author`,
  `test-quality`, and `verifier-agent`. The first of those is this component's own companion
  skill, which is a draft and has not been used yet, so the report counting it at zero is the
  contribution bar working rather than a gap.
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
- **It never touches a session.** No start, resume, interrupt, or end. It offers exactly three
  actions against a session and every one of them is non-mutating: open the pull request, copy the
  working directory, and copy a resume command for you to run. See the section below, which is the
  enumeration rather than a summary of one.
- **It adds no dependency.** No package manager, no lockfile, no bundler, no framework. Standard
  library on the Python side and nothing at all on the page's.

## Where the code is

| File | Holds |
|---|---|
| [`scripts/observatory/db.py`](../scripts/observatory/db.py) | The store: schema, forward-only migrations, the connection helper. |
| [`scripts/observatory/ingest.py`](../scripts/observatory/ingest.py) | The incremental reader, from the corpus into the store, and the reader for the live-session registry. |
| [`scripts/observatory/serve.py`](../scripts/observatory/serve.py) | The loopback server, the report registry, and the fleet and skills reports. |
| [`scripts/observatory/ui/index.html`](../scripts/observatory/ui/index.html) | The page shell every report renders into. One file, no build step. |
| [`tests/test_observatory.py`](../tests/test_observatory.py) | The store, ingester, and live-registry tests. |
| [`tests/test_observatory_serve.py`](../tests/test_observatory_serve.py) | The server, page shell, and report tests. |

A later report is added by serving a JSON endpoint from `serve.py`, registering it in that file's
`REPORTS`, and adding one function to `RENDERERS` in the page. The layout, the navigation, and the
scope selector are the shell's and should not need to change.
