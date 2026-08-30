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
again whenever you want a full pass over the corpus. **You do not have to run it to keep an open
page current**: the server follows the corpus while a page is open and folds in what appears, which
is the next section. The fleet report also reads the live-session registry on every request, so
running-versus-ended is correct as of the moment you asked.

| Option | Applies to | Default |
|---|---|---|
| `--corpus DIR` | both | `~/.claude/projects`. `serve.py` reads it for one thing only: placing a live session the store has not seen yet. |
| `--store PATH` | both | `.observatory/store.db`, gitignored |
| `--registry DIR` | `serve.py` | `~/.claude/sessions`, the harness's own list of running sessions |
| `--host ADDR` | `serve.py` | `127.0.0.1`. A non-loopback address is refused, and so is a request naming another origin's host. |
| `--port N` | `serve.py` | `8787` |
| `--poll-seconds N` | `serve.py` | `2`. How often the open page is brought up to date, and so the delay before new work shows. |
| `--spool PATH` | `serve.py` | `events.jsonl` beside the store, where the optional hook appends. Absent is not an error. |
| `--pricing PATH` | `serve.py` | [`scripts/observatory/pricing.json`](../scripts/observatory/pricing.json), the local rate table. Read from disk on every request and never fetched. |
| `--quota PATH` | `serve.py` | None. An optional quota sample series. Absent is the normal state and is not an error. |

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
| Waves | What did a dispatched wave run, cost, and produce? | Built |
| Cost and pressure | What was consumed, and how close to a limit? | Built |
| Health | What failed, and how often? | Built |

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

## What the waves report counts as one wave

A session dispatches agents for all sorts of reasons, and two dispatched an hour apart for
unrelated work are not a wave. The rule the report applies, and states on the page, is:

> A wave is a maximal run of dispatches from one session in which each dispatch begins within
> 300 seconds of the one before it. A longer pause starts a new wave, and a dispatch with
> nothing within that window on either side is a wave of one.

**The 300 is measured, not chosen.** Take every pair of dispatches adjacent in a session's own
dispatch ordering and keep the pairs whose both ends went into isolated worktrees: on this
maintainer's machine that is 60 gaps, of which 53 are 53.3 seconds or less, the next is 152.5
seconds, and the one after that is 1,524.7. (The population is worth stating, because the other
reading of "consecutive", gaps between isolated dispatches with any ordinary ones between them
ignored, is a different set of 63 gaps and puts a 174.3-second gap between the last two figures
here.) The threshold sits in that ten-fold valley, so every observed
`fix-batch` burst stays whole and every observed pause between bursts, all of them 25 minutes or
longer, still separates. Measured 2026-08-29 over 278 dispatches.

**It is a proximity rule, and the page says so.** The corpus does draw a real boundary, the user
turn, and the store cannot see it: only assistant records are stored, so the user record that
ends a turn is not there to split on. Against isolated dispatches the gaps are strongly bimodal
and the rule reproduces every batch that actually happened. Against ordinary ones they are not,
with observed gaps at 73, 137, 206 and 289 seconds sitting either side of nothing in particular.
Each wave reports how many of its members went into an isolated workspace, which is what tells a
reconstructed `fix-batch` wave from a run of unrelated dispatches that happened close together.

### What each run is reported with, and what it is not

Type, resolved model, duration, tokens, tool calls, spawn depth, workspace, branch, and an
outcome. **Never the prompt it was given or the report it came back with**: the contract's
Non-Goals exclude reconstructing conversation content, and the store has no column either could
arrive in.

Three outcomes, and none of them is a failure:

| Outcome | What it says |
|---|---|
| completed | The dispatching session recorded a completion record, so the figures are the harness's own. |
| launched, outcome unrecorded | The dispatch was acknowledged as a backgrounded launch and no completion record for it exists anywhere in the corpus. Whether it finished is not something the corpus can say. |
| no result record | Nothing acknowledged the dispatch at all. Still in flight when the corpus was read is one way to reach this. |

A fourth, `unrecognised status`, exists so that a status added upstream cannot arrive silently as
one of the three above. It matches nothing in this corpus today.

**The corpus records no failed run, so the report does not invent one.** Of 343 agent-result
records on 2026-08-29, 314 say `async_launched` and 29 say `completed`, and no other value
appears. That is also why most runs report a derived figure: only 19 of 278 carry the harness's
own duration, token total and tool-call count, and the other 259 are backgrounded launches whose
completion was never written down anywhere.

**A derived figure is marked with a tilde on the page**, because a close figure and an exact one
must not share a column in silence. Derived means computed from the agent's own messages:

- **Tool calls** matched the harness's count exactly on all 19 runs where both exist.
- **Duration** runs 1 to 3 seconds short, because the derived span starts at the agent's first
  message rather than at the dispatch.
- **Tokens** are the agent's last message's own input, output, cache-read and cache-creation
  figures added up, which is what the harness's total turns out to be: exact on 17 of the 19 and
  within 9 percent on the other two. Summing every message instead would overstate it by 20 to 60
  times, because each message's input and cache-read counts include the whole conversation before
  it again.

Where neither is available the figure is reported unknown rather than zero, which would be a
number nobody measured. Ten of the 278 runs are in that position.

**Nested dispatch is flattened, not hidden.** An agent can dispatch an agent. Every run carries
the spawn depth the harness recorded, each wave reports the deepest it holds, and a run deeper
than one is counted separately, so the depth cannot disappear into the flattening. All 268
sidecars in this corpus record depth 1.

## Following a running session

The page follows the corpus while it is open. A session that writes records appears without
anyone pressing anything, and the footer says whether the page is following or not.

**Newly appended records reach an open report within about 2 seconds.** That number is the
whole of the default path's latency, and it is stated because "slower" is not something a
reader can judge. It holds with nothing installed and nothing configured: the server looks
at the corpus on a timer, folds in whatever is new using the same incremental read the
ingester uses, and tells every open page. Change it with `--poll-seconds`.

Three properties are worth knowing:

- **It costs nothing when nobody is watching.** The watcher starts when a page opens the
  event stream and stops when the last one closes. A server sitting idle polls nothing.
- **The probe is cheaper than an ingest.** Looking costs about 38 milliseconds over this
  maintainer's corpus against 167 for a full incremental pass, so the timer walks and stats
  and only reads when something actually moved.
- **The store gains a second writer.** `ingest.py` is no longer the only thing that writes
  to it, because an open report cannot reflect new work unless something folds that work in.
  Nothing the harness owns is written by either: the corpus is opened read-only.

### The optional event source

There is a hook, [`observatory-event.py`](../.agents/hooks/observatory-event.py), that lowers
the delay. It is optional in the strong sense: **without it nothing is missing and nothing
reports an error**, you simply wait up to the poll interval instead of hearing immediately.

It appends one line to `.observatory/events.jsonl` and does nothing else. No socket, so it
cannot hang inside a session; no figure, so it cannot change one. The rule that makes that
last part true is worth stating plainly:

> An event is a hint to look, never a datum. Every figure is derived from the corpus, so the
> optional source changes when a figure appears and never which figures exist.

That is why running the hook and not running it produce identical numbers, which is asserted
by comparing both rather than reasoned about.

Install it with `python scripts/install.py --with-hooks`, which places the file and prints
the registration for you to paste. It is not registered for you, and this repository's own
[`.claude/settings.json`](../.claude/settings.json) is untouched.

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

The same identity holds for every report counting messages, which today is the skills report and
the cost report, with one bound they share: a message that appears under two projects is counted
once in the total and once in each project, so the per-project figures would sum to more than the
unrestricted one. That happens when a forked session replays history into a different project's
directory, and it does not occur in this maintainer's corpus, where 0 of 54,222 messages appear
under more than one project as of 2026-08-28.

The bound is inherent rather than introduced: a replayed message genuinely is in both projects,
and the alternative, attributing it to one of them, would make each project's own figures wrong
instead. It is named here for both reports rather than for whichever one happened to be built
first, because the next report to count messages inherits it too.

## What the cost figure is, and what it is not

**Every cost on the page is an estimate and nothing here has ever been checked against a bill.**
The corpus records what each message consumed and carries no cost field at all, so the figure is
derived: token counts multiplied by a rate table that lives on disk at
[`scripts/observatory/pricing.json`](../scripts/observatory/pricing.json). The table records the
date its rates were current, the page prints that date in the caption directly under the number,
and the estimate is labelled as one everywhere it appears rather than once in a footnote.

Three things about the arithmetic are worth knowing before you trust a number.

- **A message is priced at the rate in force on its own date, where the table records one.** A
  model whose price has never changed carries a single rate that applies to every date, which is
  most of the table, and a session run when that model cost something else is still priced at the
  one figure recorded. A model whose price has changed carries a dated list instead, and each
  message is priced against the period covering its own timestamp. **The date compared is always
  the corpus's and never the machine's**, so two runs a month apart over the same corpus produce
  identical figures; a report that changed with the calendar would answer two readers differently
  about the same sessions. Added by `bug-0057`, after `claude-sonnet-5` shipped at an introductory
  rate that lapsed on 2026-08-31 with the standard rate recorded in a note nothing applied: from
  2026-09-01 every figure using it would have understated by a third on input and a half on output,
  silently, beside a number that still looked exactly as right as the day it was true.
- **Cache tokens dominate, so they are priced.** Measured on 2026-08-29 over this maintainer's
  corpus, 96.7% of all input-side tokens were served from cache, and pricing only input and
  output would have produced $1,105.12 against $9,378.53 for the same work: a figure eight and a
  half times too small. A cost report that quietly omitted the largest kind would look entirely
  reasonable, which is why the four kinds are reported separately and all four are priced.
- **One shipped rate has a date on it.** `claude-sonnet-5` is priced at its introductory rate of
  $2.00 and $10.00, which the source table records as running through 2026-08-31; the standard
  rate behind it is $3.00 and $15.00. The intro figure is the one applied because every session
  in this corpus ran inside that window, so it is what those sessions were actually billed at.
  The table carries the expiry in the entry's own `expires` field and the page renders it under
  "Rates with a limited life", so a reader meets the date before they read the column. Nothing
  compares that date against a clock: the report derives everything it says from the corpus, and
  a report whose output depended on when it ran would answer two readers differently about the
  same sessions.
- **Thinking tokens are a memo, not a fifth kind.** They arrive as a breakdown of output tokens,
  so they are shown beside the four and are deliberately absent from every cost figure. Adding
  them would charge for the same tokens twice.

**Updating the table is a normal maintenance task.** Edit the file, press Refresh, and the figure
changes: the server reads it on every request and nothing is persisted. Open Question 1 of the
contract recommends exactly this over automating a fetch, and the no-network property forbids the
fetch anyway.

### A model with no rate is unknown, never zero

This is the part most likely to be quietly broken, so it is the part with the most machinery
behind it. A missing rate that yielded zero would be indistinguishable from a free model, and it
will happen every time a new model ships.

So an unpriced model is its own reported state. Its tokens are still counted and shown, its cost
cell says `unpriced: unknown, not zero` rather than showing a number, and the headline total is
marked incomplete and **names** the models it excluded along with how many tokens and messages
went with them. A model is priced only when all four of its rates resolve: a table entry with an
input rate and no output rate prices nothing, because a figure that silently omitted every output
token would read as a cost rather than as a gap.

There is no prefix matching and no normalisation. A key is present in the table or the model is
unpriced, which is why `claude-haiku-4-5-20251001` is its own entry beside `claude-haiku-4-5`
rather than a fuzzy match onto it. On this maintainer's corpus as of 2026-08-29 that leaves one
unpriced model, `<synthetic>`, which is the harness's marker on a locally generated message and
carries no tokens at all.

A missing or unparseable rate table follows the same rule rather than a different one: every
model becomes unpriced, every token figure is still reported, and the page says which. A fresh
clone with a deleted table shows an incomplete total, not a corpus that cost nothing.

### Context and quota pressure

Two halves from two sources, and only one of them exists on this machine.

**The context half comes from the corpus**, from the `total_tokens_reminder` attachment the
harness writes once per turn, which is the only context-budget series it carries. It is reported
as a daily series of the lowest remaining context seen, as the tightest individual readings, and
as the list of compaction occasions, which come from `compact_boundary` records because nothing
else in the corpus marks one. The chart draws a dashed tick on every day a session was compacted,
since a compaction is exactly what explains the line jumping back up.

**The quota half has no producer.** Searched on 2026-08-29 across the harness's data directory and
across the corpus: no file and no record carries a quota sample series. The contract's Sources
table marks that source not required, so its absence degrades this panel to its context half
rather than failing the report, and the page says so plainly instead of showing an empty chart.
Point `--quota` at a JSON Lines file of `{"ts": ..., "window": ..., "used_percent": ...}` samples
and the panel reports them per window; that format is this component's own and nothing else
writes it, which the page also says.

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
  out. As of 2026-08-29 that is ten of twenty-two, measured against the store rather than
  incremented: `agent-observatory`, `doc-author`, `doc-revise`, `house-review`,
  `project-bootstrap`, `review-depth`, `systematic-debugging`, `test-author`, `test-quality`, and
  `verifier-agent`. Two of those are drafts that have not been used yet, this component's own
  companion skill and `systematic-debugging`, so the report counting them at zero is the
  contribution bar working rather than a gap.
- **A skill in the corpus and absent from the roster is still reported**, marked as not in the
  roster. The harness also attributes messages to skills this kit does not ship, such as
  `code-review`, `claude-api`, and `anthropic-skills:brain-dump`. Dropping them would understate
  the total; counting them as roster skills would overstate the roster.

A use is **one message carrying that skill's attribution**, counted once. It is not a line in the
corpus: a forked or resumed session replays earlier history verbatim into a new transcript, so
5,442 message ids on this maintainer's machine appear in more than one transcript, and counting
lines would report every one of them twice.

## What the health report can and cannot see

Three kinds of thing, each with the session it happened in, when it happened, and what it
reported: a **hook that failed**, with the status it exited on; an **API error**, with the number
of attempts the request took; and a **run the corpus marks as having ended abnormally**.

**It reports what failed and decides nothing about it.** No threshold, no retry limit, no failure
budget, and no alert. Those are ROADMAP Epic E item 7(c) and stay held, which is why the retry
column says how many attempts a request took and never whether that was too many.

Three things are worth knowing before reading a figure off it.

- **A clean health report is not evidence that nothing failed.** A hook that never ran, one that
  died before writing anything, and a session that ended without writing its last record all
  leave nothing in the corpus to read. The page says so beside the figures rather than in a
  footnote, for the same reason [`AGENTS.md`](../AGENTS.md) says a passing gate set is necessary
  and not sufficient.
- **A failure is counted once however many transcripts carry it.** This is the same replay that
  makes the skills report count distinct messages rather than corpus lines, and it bites harder
  here: on this maintainer's machine on 2026-08-29, 428 stored health records are 345 distinct
  events, and the 19 records that look like hook failures are 14 real failures written under 19
  session ids. Every session an event was seen in is listed beside it, so nothing is hidden by
  the deduplication.
- **A retried error is reported whether or not it eventually succeeded.** One row per request
  that erred, carrying the attempts it took rather than a verdict, because the corpus records the
  retries and not the outcome, and the signal worth having is a session quietly taking ten
  attempts per request. Ten is the worst on this machine.

The report ends with a ledger of every kind of health record it read and what each counted for,
including the kinds it does not treat as a failure. A record dropped quietly from a report about
failures is the failure the report exists to stop, so a compaction marker (which belongs to the
cost and pressure report) is listed and labelled rather than filtered out, and so is a kind the
ingester can write that this corpus happens to have none of.

**What it found first was this repository's own hook, and the value is the measurement rather
than the discovery.** All 14 hook failures on this machine are the same one: the `SessionStart`
reminder that [`.claude/settings.json`](../.claude/settings.json) registers as `python3`, exiting
49 with "Python was not found" every time a session starts here on Windows, from 2026-08-07 to
2026-08-29.

That is a **known and deliberate trade, not a defect**. The comment in that file argues it at
length and `feat-0038` observed the same failure: `python3` is the portable default for the cloud
sessions the committed registration exists to reach, a static JSON file cannot probe for the right
interpreter, and a Windows developer who wants the hook locally overrides it in
`.claude/settings.local.json`. What was missing was the other half of the trade. The reminder shape
requires a hook to exit cleanly whatever happens, so the Windows cost was argued rather than
counted, and nobody could say how often it was actually being paid. Now it is 14 sessions.

## What it never does

- **It never reaches the network.** No rate lookup, no font, no chart library, no content delivery
  network. The page carries its own styles and its own script inline and requests no subresource at
  all, so it renders with the network unavailable, and every chart is hand-rolled inline SVG. The
  rate table behind every cost figure is a local file with a recorded date, read from disk and
  never fetched, which the contract's Constraints require and its Open Question 1 recommends.
- **It never binds beyond loopback, and never answers to another origin's name.** `serve.py`
  refuses any address that is not a loopback address, before it binds rather than after. A server
  on all interfaces would publish the whole session corpus to whatever network the machine is on,
  and that is the one failure here with a consequence outside this repository. Binding loopback
  stops another machine and does nothing about a browser on this one, so the `Host` header is
  checked too: a page on any origin can point a name it owns at `127.0.0.1` and have your browser
  send that name here, which is DNS rebinding. A request naming anything but a loopback address or
  `localhost` is refused with 403 before it reaches a report.
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
| [`scripts/observatory/serve.py`](../scripts/observatory/serve.py) | The loopback server, the report registry, and all five reports. |
| [`scripts/observatory/pricing.json`](../scripts/observatory/pricing.json) | The rate table: local data with a recorded date, edited by hand and never fetched. |
| [`scripts/observatory/ui/index.html`](../scripts/observatory/ui/index.html) | The page shell every report renders into. One file, no build step. |
| [`.agents/hooks/observatory-event.py`](../.agents/hooks/observatory-event.py) | The optional event source: appends one line and does nothing else. Opt-in, and placed by `install.py --with-hooks`. |
| [`tests/test_observatory.py`](../tests/test_observatory.py) | The store, ingester, and live-registry tests. |
| [`tests/test_observatory_serve.py`](../tests/test_observatory_serve.py) | The server, page shell, fleet, and skills report tests. |
| [`tests/test_observatory_waves.py`](../tests/test_observatory_waves.py) | The waves report tests. |
| [`tests/test_observatory_cost.py`](../tests/test_observatory_cost.py) | The cost, rate table, and pressure tests. |

A later report is added by serving a JSON endpoint from `serve.py`, registering it in that file's
`REPORTS`, and adding one function to `RENDERERS` in the page. The layout, the navigation, and the
scope selector are the shell's and should not need to change.
