#!/usr/bin/env python3
"""Serve the observatory store as one page, on the loopback interface, with no build step.

    python scripts/observatory/serve.py [--store PATH] [--port N]

`ingest.py` fills the store and nothing reads it. This is the surface that reads it: a
`ThreadingHTTPServer` that renders `ui/index.html`, answers a small JSON API from the store,
and does nothing else. The page shell it serves is a deliverable in its own right, because the
four remaining reports (`feat-0055` to `feat-0058`) slot into it rather than each reinventing
layout, navigation, and the scope selector.

Three properties are load-bearing and are why this file is shaped the way it is.

**Loopback only.** `make_server` refuses any address that is not a loopback address, before it
binds rather than after. The contract forbids data leaving the machine (S-022), and a server on
all interfaces publishes one maintainer's whole session corpus to whatever network the machine
is on. Refusing is deliberate: a warning would be read once and a `--host 0.0.0.0` would go on
working.

**No third-party dependency and no external asset.** Standard library only, per the conventions
section of `AGENTS.md`. The page carries its own CSS and its own script inline and requests no
subresource at all, so it renders with the network unavailable and a chart is hand-rolled inline
SVG. A remote font or a chart library would also break the no-network property `S-022` sets.

**Reads only over HTTP, and the store is the one thing it writes.** Every route is a GET, and no
route writes anything. `S-019`'s enumeration fixes what a session-directed action may be, and the
three this offers are navigation or a command to copy. **What changed in `feat-0059`**: the live
watcher folds appended records into the store so an open report can reflect them, so the store now
has two writers rather than one. Nothing the *harness* owns is written by either, which is the
property `S-009` states: the corpus is opened `"rb"` and the store lives outside it.

**The live registry is read per request, not ingested.** `S-012` asks a question about now, so
an answer stored at the last ingest would be as old as that ingest. `live_sessions` reads the
harness's registry and checks each entry's process on every request, which is why the report is
correct as of when it was asked for and no more; keeping an open report current is `S-013`, and
that is `feat-0059`'s.

Exit codes, matching `run-checks.py` and `ingest.py`:

    0  the server ran and was stopped
    2  the server could not start (a non-loopback address, or a port already in use)

**Cost is derived and says so.** The corpus carries no cost field, so every monetary figure
here is an estimate against `pricing.json`, a local table with a recorded date that is read
from disk and never fetched. A model absent from that table is reported unpriced: its tokens
are counted, its cost is unknown rather than zero, and every total it would have contributed
to names it. Zero and unknown are different answers and `S-011` is the difference.

Contract: `docs/spec/agent-observatory.md`. Scenarios: S-001 to S-021, every scenario
this component claims.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import queue
import re
import socket
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# `install` is imported for one thing only: where the skills live. S-002 needs a roster the
# corpus cannot supply, and writing that path here would be a second source of truth that
# disagrees with the installer the first time the tree moves.
from scripts import install                     # noqa: E402
from scripts.observatory import db, ingest      # noqa: E402

DEFAULT_STORE = ingest.DEFAULT_STORE
DEFAULT_CORPUS = ingest.DEFAULT_CORPUS
DEFAULT_REGISTRY = ingest.DEFAULT_REGISTRY

UI_DIR = Path(__file__).resolve().parent / "ui"
INDEX = UI_DIR / "index.html"

# A rate period is bounded by ISO dates, and a message is dated by the corpus in the same
# shape, so both sides compare as plain strings. No parsing, no timezone, and above all no
# clock: `bug-0057` added dated rates precisely so the report keeps deriving everything from
# the corpus, and a date object here would be the first step toward comparing against today.
_ISO_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

# Every source the page needs is in the page. `default-src 'none'` then names the few it
# actually uses, rather than `'self'` admitting whatever else the origin might later serve.
# `connect-src 'self'` is the JSON routes and the event stream; `img-src data:` covers the
# inline SVG charts the page draws itself. No `script-src` host is listed at all, so a
# `javascript:` URI is blocked whatever else changes on the page.
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "img-src 'self' data:; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

# The five reports of the contract's Proposed Surface, in its order. This is the registry the
# page shell renders its navigation from, so a later task adds its report by adding an endpoint
# and a renderer rather than by editing the shell's markup. `owner` names the task that owns a
# report not built yet, so the page says who owes it instead of showing an empty panel.
REPORTS = (
    {"id": "fleet", "title": "Fleet",
     "question": "Which sessions exist, where, and which are running?",
     "scenarios": ["S-012", "S-018"], "endpoint": "/api/fleet", "owner": None},
    {"id": "skills", "title": "Skills",
     "question": "Which skills are used, how often, and which never are?",
     "scenarios": ["S-001", "S-002"], "endpoint": "/api/skills", "owner": None},
    {"id": "waves", "title": "Waves",
     "question": "What did a dispatched wave run, cost, and produce?",
     "scenarios": ["S-003", "S-004"], "endpoint": "/api/waves", "owner": None},
    {"id": "cost", "title": "Cost and pressure",
     "question": "What was consumed, and how close to a limit?",
     "scenarios": ["S-010", "S-011", "S-017", "S-021"], "endpoint": "/api/cost",
     "owner": None},
    {"id": "health", "title": "Health",
     "question": "What failed, and how often?",
     "scenarios": ["S-016"], "endpoint": "/api/health", "owner": None},
)

# Said in one place, and served to the page so the document and the surface cannot disagree
# about what "never used" was measured against. `docs/OBSERVATORY.md` states the same thing.
ROSTER_LABEL = "the skill directories under .agents/skills/, as install.py discovers them"

# The bucket a session lands in when nothing can attribute it to a project. It is a project
# in the report's arithmetic rather than a discard, because S-018 requires the per-project
# figures to sum to the unrestricted ones and a dropped session breaks that sum while every
# panel still renders.
UNATTRIBUTED = "(unattributed)"

# The staleness rule, in one sentence, served to the page for the same reason ROSTER_LABEL
# is: a registry entry can outlive the process that wrote it, so presence is evidence and
# not proof, and a reader must be told which of the two the report is showing them.
LIVENESS_POLICY = (
    "A session is reported running only where its registry entry's process is confirmed. "
    "An entry whose process is gone is reported ended and counted as a stale entry; one "
    "whose process cannot be checked is reported unverified, never running."
)

# Running first, then the ones that could not be established, then the settled past. The
# report exists to answer a question about now, so what is now goes at the top.
STATE_ORDER = ("running", "unverified", "ended")

# How long a session may go without dispatching before the next dispatch starts a new wave.
#
# **Calibrated against the corpus rather than chosen.** Measured 2026-08-29 over this
# maintainer's 278 dispatches. The population, stated exactly because "consecutive" has two
# readings that give different numbers: every pair adjacent in a session's own dispatch
# ordering whose both ends went into isolated worktrees. That is 60 gaps, of which 53 are 53.3
# seconds or less, the next is 152.5 seconds, and the one after that is 1,524.7 seconds. (The
# other reading, gaps between isolated dispatches with any ordinary ones between them ignored,
# gives 63 gaps and a 174.3-second gap between those last two. The valley survives either way,
# which is why the rule is unchanged and only the wording is.) The widest relative valley is the ten-fold
# jump between those last two, so 300 sits inside it with room on both sides: every observed
# `fix-batch` burst stays whole and every observed pause between bursts, all of them 25 minutes
# or longer, still separates.
WAVE_GAP_SECONDS = 300.0

# The rule, stated in the report rather than only in this file, because a reader who cannot tell
# a wave from a sequence of unrelated dispatches cannot use the grouping at all.
WAVE_RULE = (
    "A wave is a maximal run of dispatches from one session in which each dispatch begins "
    f"within {WAVE_GAP_SECONDS:g} seconds of the one before it. A longer pause starts a new "
    "wave, and a dispatch with nothing within that window on either side is a wave of one."
)

# What the rule above cannot do, said next to it. An honest heuristic that names its own
# population is usable; one that does not is a number a reader will over-trust.
WAVE_RULE_BOUND = (
    "It is a proximity rule, not a boundary the corpus draws. The corpus does draw one, the "
    "user turn, and the store cannot see it: only assistant records are stored, so the user "
    "record that ends a turn is not there to split on. Against dispatches into isolated "
    "worktrees the gaps are strongly bimodal and the rule reproduces every observed batch; "
    "against ordinary dispatches they are not, with observed gaps at 73, 137, 206 and 289 "
    "seconds either side of no gap at all, so a group of those is proximity and nothing more. "
    "The isolated count on each wave is what tells the two apart."
)

# Every outcome a run may be reported with, and there is deliberately no failure among them.
# `S-003` asks whether a run "completed or ended without completing", and the corpus answers the
# first half exactly and the second half only as an absence, so the absences are named
# separately rather than collapsed into one word that would read as failure.
RUN_OUTCOMES = (
    {"id": "completed", "label": "completed",
     "meaning": "The dispatching session recorded a completion record, so this run's duration, "
                "token total, and tool-call count are the harness's own figures."},
    {"id": "launched", "label": "launched, outcome unrecorded",
     "meaning": "The dispatch was acknowledged as a backgrounded launch and no completion "
                "record for it exists anywhere in the corpus. Whether it finished is not "
                "something the corpus can say, so this is neither a success nor a failure."},
    {"id": "unrecorded", "label": "no result record",
     "meaning": "Nothing acknowledged the dispatch at all: the run is known only from the "
                "sidecar written beside its transcript. Still in flight when the corpus was "
                "read is one way to reach this, and it is not a failure either."},
    {"id": "unrecognised", "label": "unrecognised status",
     "meaning": "The result record carries a status this report has no name for. Reported as "
                "itself rather than folded into one of the three above, so a status added "
                "upstream cannot arrive silently as something else."},
)

# The statuses the corpus actually writes, mapped to the outcomes above. Confirmed by counting
# on 2026-08-29 rather than recalled: of 343 agent-result records, 314 say `async_launched` and
# 29 say `completed`, and no third value appears.
OUTCOME_OF_STATUS = {"completed": "completed", "async_launched": "launched"}

OUTCOME_POLICY = (
    "No outcome here means the run failed. Of 343 agent-result records in this maintainer's "
    "corpus on 2026-08-29, 314 say async_launched and 29 say completed and no other status "
    "appears, so the corpus carries no vocabulary for a failed run and this report does not "
    "invent one. A run with no completion record is reported as launched or unrecorded, never "
    "as failed."
)

# Where each of the three per-run figures came from. Reporting the figure without its basis
# would mix an exact number from the harness with an approximation from the agent's own
# messages and leave a reader no way to tell which they were looking at.
FIGURE_BASES = (
    {"id": "reported", "meaning": "The harness's own figure, from the completion record. "
                                  "Exact."},
    {"id": "derived", "meaning": "Computed from the agent's own messages, because no "
                                 "completion record exists. Close, not exact: see the note."},
    {"id": "unknown", "meaning": "Neither available. Reported as unknown rather than as zero, "
                                 "which would be a figure nobody measured."},
)

# What "close, not exact" is worth, in numbers, from the 19 runs where both a completion record
# and the agent's own messages exist. Measured 2026-08-29.
DERIVATION_NOTE = (
    "Tool calls derived from the agent's own messages matched the harness's count exactly on "
    "all 19 runs where both exist. Durations ran 1 to 3 seconds short, because the derived "
    "span starts at the agent's first message rather than at the dispatch. Tokens are the "
    "agent's last message's own input, output, cache-read and cache-creation figures added up, "
    "which is what the harness's total turned out to be: exact on 17 of the 19 and within 9 "
    "percent on the other two. Summing every message instead would overstate it by 20 to 60 "
    "times, because each message's input and cache-read counts include the whole conversation "
    "before it again."
)

# Depth is carried on every run and never collapsed. An agent can dispatch an agent, and a
# report that flattened without saying so would show a nested run as a peer of the run that
# dispatched it.
NESTING_POLICY = (
    "Nested dispatch is flattened, not hidden: every run carries the spawn depth the harness "
    "recorded, a wave reports the deepest it holds, and a run deeper than 1 is counted. A "
    "nested run is grouped by the session it was recorded under, which is the dispatching "
    "session for every run in this corpus, where all 268 sidecars record depth 1."
)

# The health report's own statement of what it cannot see, served to the page rather than
# written into the page's markup, for the same reason `ROSTER_LABEL` and `LIVENESS_POLICY`
# are: the qualification belongs beside the figures, and a document and a surface that state
# it separately eventually disagree. `AGENTS.md` makes the same move about its own gate set,
# and for the same reason: a clean result over what was looked at is not a clean result over
# what happened.
HEALTH_BLIND_SPOT = (
    "Only failures that left a record are here. A hook that never ran, one that died before "
    "writing anything, and a session that ended without writing its last record leave "
    "nothing in the corpus to read, so an empty health report is not evidence that nothing "
    "failed."
)

# Why every count here is of events rather than of records. This is the same replay that
# makes the skills report count distinct messages rather than corpus lines, arriving at a
# table with no canonical-versus-occurrence split to lean on, so the grouping happens in the
# report instead of in the store. Measured over this maintainer's corpus on 2026-08-29: 428
# `health_event` rows carry 345 distinct events, and the 19 rows that look like hook failures
# are 14 real failures written under 19 session ids.
HEALTH_REPLAY_POLICY = (
    "An event is counted once however many transcripts carry it. A forked or resumed session "
    "replays earlier records verbatim under a new session id, so every session an event was "
    "seen in is reported and the counts are of events rather than of records."
)

# Everything about a health event except the session it was seen in. Two rows agreeing on all
# of these are one event written twice by a replay, not two failures. Kept as a tuple because
# it is the identity, the projection, and the field list of the event dict all at once, and
# three copies of it would drift.
HEALTH_EVENT_FIELDS = ("ts", "kind", "detail", "tool_use_id", "exit_code", "attempt",
                       "hook_name", "hook_event", "command", "duration_ms")

# The non-hook kinds `ingest.apply_record` can write, declared rather than discovered from the
# store, so a kind filtered to zero on a given corpus is still named in the ledger instead of
# vanishing from it. `stop_hook_summary` is the case that matters: `feat-0053`'s verification
# recorded that every one of the 1,287 such records carries empty `hookErrors` and false
# `preventedContinuation`, so the branch writes no row at all and
# `health_event.prevented_continuation` is NULL on every row in the store. **That is a bound,
# not a repair**, and a ledger built only from what the store holds would show it as nothing
# rather than as zero. Confirmed unchanged on 2026-08-29: 0 rows of that kind and 0 rows
# carrying a `prevented_continuation` value, out of 428.
DECLARED_HEALTH_KINDS = ("api_error", "compact_boundary", "stop_hook_summary")

# What the health report does with each kind it meets, said for a reader rather than left to
# be inferred from which rows appear in which table. A kind it does not count is still listed
# and labelled, because a record silently dropped from a report about failures is exactly the
# failure this report exists to stop.
HEALTH_KIND_ROLES = {
    "api_error": "counted as an API error, with the attempt it was",
    "compact_boundary": "not a failure: a compaction, which the cost and pressure report "
                        "covers under S-017",
    "stop_hook_summary": "counted as a hook failure. The ingester writes one only where the "
                         "summary carried a hook error or prevented a continuation, so the "
                         "row's existence is the failure and a zero here is a bound rather "
                         "than a repair",
}

# How often the watcher looks, and therefore the worst-case delay between a session
# writing a record and an open report showing it. S-014 requires that delay to be a stated
# number rather than "slower", so it is a constant here and a sentence in
# `docs/OBSERVATORY.md`, and the page says it too.
DEFAULT_POLL_SECONDS = 2.0

# A comment line every so often, so a client that has gone away is noticed on the next
# write rather than holding a thread until the process ends.
HEARTBEAT_SECONDS = 15.0

# Where the optional event source leaves its events. The hook appends here and the watcher
# tails it; nothing opens a socket in either direction, which is why the hook cannot hang
# inside somebody's session.
SPOOL_NAME = "events.jsonl"

# The reconciliation rule S-015 turns on, stated once because it is the whole defence
# against double counting: **an event is a hint to look, never a datum**. Figures are
# derived from the corpus and from nowhere else, so an event arriving by hook and the
# records it describes arriving in the corpus cannot both be counted. The optional source
# changes when a figure appears and never which figures exist.
EVENT_POLICY = (
    "An event is a hint to look, never a datum. Every figure is derived from the corpus, "
    "so the optional source changes when a figure appears and never which figures exist."
)

# The rate table, and the words that must travel with every figure derived from it. `S-010`
# requires the cost to be labelled an estimate and accompanied by the date the rates were
# recorded, so both are constants here, both are served to the page, and both appear beside the
# number rather than in a footnote. A stale table misstates every cost figure while the report
# looks exactly as correct as it did the day the rates were right, so the mitigation has to be
# where the number is read.
PRICING_PATH = Path(__file__).resolve().parent / "pricing.json"

ESTIMATE_LABEL = (
    "Estimated, not billed. Every cost below is derived from token counts against a local "
    "rate table. The corpus carries no cost field, so no figure here has ever been checked "
    "against an invoice."
)

HISTORICAL_RATES_NOTE = (
    "A message is priced at the rate in force on its own date, where the table records one. "
    "A model whose price never changed carries a single rate that applies to every date, so a "
    "session run when that model cost something else is still priced at the one figure "
    "recorded. The date compared is always the corpus's and never this machine's, so two runs "
    "a month apart over the same corpus produce identical figures."
)

# `S-011` in one sentence, served to the page for the same reason `LIVENESS_POLICY` is: the
# reader has to be told which of two answers they are looking at, and zero and unknown are
# different answers.
UNPRICED_POLICY = (
    "A model with no entry in the rate table is reported unpriced: its tokens are still "
    "counted and its cost is unknown, never zero. Every total it would have contributed to "
    "says so and names it, because a missing rate that yielded zero would be indistinguishable "
    "from a free model."
)

# The denominator, stated once. `S-021` asks for the cache-served proportion to be derivable
# from the four kinds, and derivable is only true if the reader knows what it was derived from:
# there are two defensible bases and they give different numbers.
CACHE_SHARE_BASIS = (
    "cache-read tokens over all input-side tokens, meaning input plus cache read plus cache "
    "creation. Output is excluded because no output token is served from cache."
)

# The optional quota source. `S-017` has two halves from two sources with different shapes, and
# the contract's Sources table marks this one not required, so its absence degrades the report
# to the context half rather than failing it.
QUOTA_NAME = "quota.jsonl"
QUOTA_FORMAT = (
    "JSON Lines, one sample per line, each an object carrying `ts` (an ISO-8601 timestamp), "
    "`window` (a name such as session or week), and `used_percent` (0 to 100). Unknown keys "
    "are ignored."
)
QUOTA_PROVENANCE = (
    "The format above is this component's own, and nothing writes it. Searched on 2026-08-29 "
    "across the harness's data directory and across the corpus: no file and no record carries "
    "a quota sample series, so the reader is the only producer and the shape is unverified "
    "against any other. The absence is the normal state, not an error."
)

# What a model row is keyed by when the corpus recorded no model at all. It is a name in the
# report rather than a dropped row, for the same reason `UNATTRIBUTED` is: dropping it would
# make the per-model figures quietly fail to add up to the totals beside them.
MODEL_UNRECORDED = "(model not recorded)"

# The two kinds of action this surface may offer against a session, and there is deliberately
# no third. `S-019` permits exactly these: an action referencing a session must "resolve to
# navigation or to a command presented for a person to run". Both are non-mutating by
# construction rather than by review: `navigate` opens something in the viewer's browser, and
# `copy-command` puts text on their clipboard. Neither can reach a session.
#
# Adding a kind here is the one edit that could make `S-019` false, which is why the set is a
# constant a test can read rather than a convention a reviewer has to remember.
ACTION_KINDS = ("navigate", "copy-command")

# Every action the surface offers. `S-019` is an enumeration claim, and that is what makes it
# testable: "nothing mutates a session" is untestable as prose and decidable as a list. The
# list lives here, the page renders from it and tags each element with `data-action`, and a
# test resolves the two against each other. A button added to the page without an entry here
# fails that test rather than quietly widening the surface.
#
# `field` names the session row's key that supplies the value, so an action whose field is
# empty on a given row is not offered for that row. `template` builds the text for a
# `copy-command`; a `navigate` action uses the field's value as the target.
ACTIONS = (
    {"id": "open-pr", "kind": "navigate", "label": "Pull request", "field": "pr_url",
     "template": None, "href_field": "pr_href",
     "note": "Opens the session's pull request. A link the viewer follows is a request their "
             "browser makes, not one this report makes, so S-022 is untouched. `field` carries "
             "what the corpus recorded and is always displayed; `href_field` carries the same "
             "value only when it is safe to point a browser at, and is None otherwise."},
    {"id": "copy-cwd", "kind": "copy-command", "label": "Copy path", "field": "cwd",
     "template": "{cwd}",
     "note": "Copies the working directory. A file:// link from an http:// page is blocked "
             "by browsers, so the path is offered as text rather than as a dead link."},
    {"id": "copy-resume", "kind": "copy-command", "label": "Copy resume command",
     "field": "session_id", "template": "claude --resume {session_id}",
     "note": "Copies the command that would resume this session. S-019 permits presenting a "
             "command for a person to run; running it is not this surface's to do. The flag "
             "is the CLI's own, confirmed against `claude --help` rather than assumed."},
)

# The only schemes a `navigate` action may point a viewer's browser at. Everything in the
# fleet report comes from a session transcript, which this repository did not write, and a
# `navigate` value is the one field that reaches an interpreted context rather than a text
# node. `javascript:` there is script execution in this surface's own origin, which can read
# every route on this server: that is the whole session corpus (`bug-0055`).
#
# A constant rather than a literal in the check, for the reason `ACTION_KINDS` is one: it is
# the edit that could make the guarantee false, so a test reads it instead of a reviewer
# remembering it.
ACTION_URL_SCHEMES = ("http:", "https:")


def followable_url(value):
    """`value` when a browser may be pointed at it, otherwise None.

    The decision is made here rather than on the page, and that placement is the point. The
    suite deliberately has no JavaScript runtime (a test asserts `node_modules` is never
    introduced), so a check written in the page could only ever be asserted by reading its
    source, while this one is executed by real tests against real ingested corpus values.
    The page consumes the answer and carries no security logic it cannot be tested on.

    Parsed rather than pattern-matched. `startswith("http")` admits `httpx://` and a
    denylist of `javascript:` misses `data:` and `vbscript:`, so this is an allow-list over
    the parsed scheme. `urlsplit` strips ASCII tab, carriage return and newline exactly as
    browsers do, so `java\\nscript:` normalises to `javascript:` here and refuses, rather
    than slipping past a naive prefix test and executing in the browser.

    A relative or protocol-relative value has no scheme and is refused, which is correct
    rather than incidental: this field records an absolute pull request URL, and `//evil/x`
    resolved against this origin is a navigation the corpus never asked for.

    Refusing returns None instead of raising, because a refused value is still displayed to
    the viewer as text. Nothing the corpus recorded is hidden; it is only not made clickable.
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        scheme = urlsplit(candidate).scheme.lower()
    except ValueError:
        # A value malformed enough that the parser refuses it is one no browser should be
        # pointed at either. Fail closed.
        return None
    return candidate if f"{scheme}:" in ACTION_URL_SCHEMES else None


class NotLoopback(ValueError):
    """The requested address is not a loopback address, so binding it would publish the
    corpus to the local network."""


def loopback_address(host: str) -> str:
    """The loopback address `host` names, or `NotLoopback`.

    `localhost` is resolved by table rather than by `socket.gethostbyname`, for two reasons:
    a name lookup is a network operation this contract would rather not perform at all, and a
    machine whose hosts file points `localhost` somewhere else must not be able to talk this
    server onto a routable interface.
    """
    # Lowered, agreeing with `host_is_loopback()` below. These two answer different
    # questions, what may this bind against what may this answer, and they were reading the
    # same name two ways: `--host LOCALHOST` was refused here and accepted there. It failed
    # closed, which is the right direction and not a reason to leave one name with two
    # readings (chore-0082).
    if host.rstrip(".").lower() == "localhost":
        return DEFAULT_HOST
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise NotLoopback(
            f"{host!r} is not an IP address. This server binds a loopback address only, "
            f"so the session corpus is never served to the local network."
        ) from None
    if not address.is_loopback:
        raise NotLoopback(
            f"{host!r} is not a loopback address. Binding it would serve the whole session "
            f"corpus to the local network, which the contract forbids. Use "
            f"{DEFAULT_HOST} or ::1."
        )
    return str(address)


def host_is_loopback(header) -> bool:
    """Whether a `Host` header names this machine's loopback interface.

    Binding a loopback address stops another machine reaching this server and does nothing
    about a browser on this one. The `Host` header is attacker-controlled, so a page on any
    origin can point a name it owns at 127.0.0.1, have the browser send that name here, and
    read every route. That is DNS rebinding, and what it reads is one maintainer's entire
    session history: session ids, project names, working directories, branches.

    `feat-0054` recorded this as a local-attacker concern outside `S-022`'s wording, which
    is about outbound connections, and left it to whichever task defined the surface's
    boundary. This is that task.

    An absent header is allowed. HTTP/1.0 clients and some command-line tools omit it, and
    no browser does, so refusing it would break the honest callers and stop none of the
    dishonest ones.
    """
    if header is None:
        return True
    host = str(header).strip()
    if host.startswith("["):                  # [::1] or [::1]:8787
        host = host[1:].split("]", 1)[0]
    elif host.count(":") == 1:                # 127.0.0.1:8787 or name:8787
        host = host.rsplit(":", 1)[0]
    if not host:
        return False
    if host.rstrip(".").lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def skill_roster(skills_dir: Path | None = None) -> list[str]:
    """Every skill the report counts against, whether or not the corpus mentions it.

    S-002 cannot be answered from the store: a skill that never appears in a transcript
    appears nowhere in the store either, so the set has to come from the skill directories
    themselves. It comes from `install.discover_skills()` rather than from a path spelled out
    here, so this and the installer can never disagree about what the installed set is.

    `skills_dir` overrides the location for a test that needs a roster it controls; it applies
    the same rule (a directory holding a `SKILL.md`) rather than a second one.
    """
    if skills_dir is None:
        return [directory.name for directory in install.discover_skills()]
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def projects(conn) -> list[str]:
    """Every project the store can report on, for the scope selector.

    The union of two tables rather than `message_occurrence` alone, because a session with no
    assistant message has no occurrence row and its project would therefore never appear in
    the selector while the fleet report counted it. Four of this maintainer's 155 sessions are
    in that position on 2026-08-28, so the gap is real rather than hypothetical.
    """
    return [row["project"] for row in conn.execute(
        "SELECT project FROM message_occurrence WHERE project IS NOT NULL "
        "UNION SELECT project FROM session WHERE project IS NOT NULL "
        "ORDER BY project"
    )]


def skills_report(conn, project: str | None = None,
                  roster: list[str] | None = None) -> dict:
    """The skills report: one row per skill, roster and corpus unioned.

    The count is **distinct messages carrying the attribution**, not lines in the corpus.
    `message` holds one canonical row per uuid, so a `COUNT(*)` over it is already the
    distinct-message figure; a forked or resumed session replays earlier history verbatim, so
    5,442 uuids in this maintainer's corpus appear in more than one transcript and counting
    occurrences would report every one of them twice. That is why the unscoped branch counts
    `message` and the scoped branch counts `DISTINCT m.uuid` rather than joined rows.

    Every roster skill appears, including one the corpus never mentions, which is reported at
    zero rather than left out (S-002). A skill the corpus carries that the roster does not is
    reported too, marked `installed: false`, because dropping it would overstate the roster's
    share of the total.
    """
    roster = skill_roster() if roster is None else list(roster)

    if project:
        rows = conn.execute(
            "SELECT m.attribution_skill AS skill, COUNT(DISTINCT m.uuid) AS uses "
            "FROM message m JOIN message_occurrence o ON o.uuid = m.uuid "
            "WHERE m.attribution_skill IS NOT NULL AND o.project = ? "
            "GROUP BY m.attribution_skill",
            (project,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT attribution_skill AS skill, COUNT(*) AS uses FROM message "
            "WHERE attribution_skill IS NOT NULL GROUP BY attribution_skill"
        ).fetchall()

    counted = {row["skill"]: row["uses"] for row in rows}
    names = sorted(set(roster) | set(counted))
    entries = [
        {"skill": name, "uses": counted.get(name, 0), "installed": name in roster}
        for name in names
    ]
    entries.sort(key=lambda entry: (-entry["uses"], entry["skill"]))

    installed = [entry for entry in entries if entry["installed"]]
    return {
        "report": "skills",
        "project": project,
        "roster_label": ROSTER_LABEL,
        "roster_size": len(roster),
        "installed_used": sum(1 for entry in installed if entry["uses"]),
        "installed_unused": sum(1 for entry in installed if not entry["uses"]),
        "total_uses": sum(entry["uses"] for entry in entries),
        "skills": entries,
    }


def scope_options(conn, registry=None, corpus=None) -> list[str]:
    """Every project any report can be restricted to, for the scope selector.

    `projects(conn)` plus whatever only the live registry knows about. A session that started
    minutes ago has no store row, so a project whose only session is that one would be counted
    by the fleet report and missing from the selector, which is the shape of gap where a
    reader sees a figure in one panel and cannot reach it from the other.
    """
    _, live = live_sessions(conn, registry, corpus)
    return sorted(set(projects(conn)) | {seen["project"] for seen in live.values()})


def _live_project(conn, session_id: str, corpus: Path) -> str:
    """The project a live session belongs to, asked of the two sources that actually know.

    The store first, which is authoritative for any session it has seen. Then the corpus,
    because a session that started minutes ago has a transcript and no store row yet, and the
    directory that transcript sits in *is* the project name.

    **The obvious third option, transforming `cwd` into a directory name, is deliberately
    absent.** It cannot work, and the reason is stronger than a bad hit rate: measured over
    this maintainer's corpus on 2026-08-28, the project directory is not a function of the
    recorded working directory at all, because two projects are each reached from more than
    one working directory. Six of twenty-six distinct `(cwd, project)` pairs disagree under
    the most permissive rule tried, every non-alphanumeric character to a dash, and a
    separator-only rule misses all twenty-six because project names also flatten spaces and
    underscores. The cause is that the working directory drifts within a session while the
    project directory does not: `D:\\hts-app\\docs` and `D:\\hts-app\\content-engine` both live
    under `D--hts-app`, and one worktree's sessions live under a different worktree's
    directory entirely. A transform would attribute those to projects that do not exist,
    which is worse than saying so.
    """
    row = conn.execute("SELECT project FROM session WHERE session_id = ?",
                       (session_id,)).fetchone()
    if row and row["project"]:
        return row["project"]
    try:
        for directory in sorted(corpus.iterdir()):
            if directory.is_dir() and (directory / f"{session_id}.jsonl").exists():
                return directory.name
    except OSError:
        pass
    return UNATTRIBUTED


def live_sessions(conn, registry=None, corpus=None) -> tuple:
    """`(what the registry held, {session_id: liveness})`, read at report time.

    Read per request rather than ingested into a table. Running-versus-ended is a question
    about now, and a stored answer would be as old as the last ingest; the contract's S-013,
    which makes an open report update itself, is `feat-0059`'s and is a different question
    from this one.

    Where two entries name one session, the stronger claim wins rather than whichever file
    sorted last, so the answer does not depend on a filename.
    """
    registry = ingest.DEFAULT_REGISTRY if registry is None else Path(registry)
    corpus = ingest.DEFAULT_CORPUS if corpus is None else Path(corpus)
    found = ingest.read_registry(registry)

    rank = {ingest.ALIVE: 0, ingest.UNKNOWN: 1, ingest.GONE: 2}
    live: dict = {}
    for entry in found["entries"]:
        session_id = entry["sessionId"]
        state, evidence = ingest.process_state(
            entry.get("pid"), entry.get("procStart"), entry.get("pidDomain"))
        held = live.get(session_id)
        if held and rank[held["process"]] <= rank[state]:
            continue
        live[session_id] = {
            "process": state, "evidence": evidence, "entry": entry,
            "project": _live_project(conn, session_id, corpus),
        }
    return found, live


def _started_at(entry: dict):
    """`startedAt` is epoch milliseconds in the registry. Rendered here rather than on the
    page, because the page's script is the one part of this surface with no execution
    coverage and a date it formats itself is a date nothing can check."""
    millis = entry.get("startedAt")
    if not isinstance(millis, (int, float)) or isinstance(millis, bool):
        return None
    try:
        return datetime.fromtimestamp(millis / 1000, timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def fleet_report(conn, project: str | None = None, registry=None, corpus=None) -> dict:
    """The fleet report: every session, where it is, and which are running (S-012, S-018).

    Two invariants are the point of the shape below, and both are arithmetic rather than
    visual because both can be false while every panel still renders.

    **Every session lands in exactly one project bucket**, including one nothing can
    attribute, which goes to `UNATTRIBUTED` rather than being dropped. That is what makes
    S-018's summing property hold: restrict to each project in turn, add the figures up, and
    the total is the unrestricted total.

    **Every session lands in exactly one state**, so `running + unverified + ended` equals
    `sessions`. A stale registry entry is `ended` with its entry marked `stale`, and is
    counted in `stale_entries` as well, so it is neither reported as running nor silent.
    """
    found, live = live_sessions(conn, registry, corpus)

    def row(session_id, project_name, branch, first, last, title, entrypoint, cwd,
            in_store, pr_url=None, pr_number=None):
        state, registry_state, evidence = "ended", "absent", "no entry in the live registry"
        entry = {}
        seen = live.get(session_id)
        if seen:
            entry = seen["entry"]
            evidence = seen["evidence"]
            state, registry_state = {
                ingest.ALIVE: ("running", "live"),
                ingest.GONE: ("ended", "stale"),
                ingest.UNKNOWN: ("unverified", "unchecked"),
            }[seen["process"]]
        return {
            "session_id": session_id, "project": project_name, "branch": branch,
            "first_activity": first, "last_activity": last, "title": title,
            "entrypoint": entrypoint, "cwd": cwd, "in_store": in_store,
            # `pr_url` is what the corpus recorded, unaltered, because this report is a
            # record of the corpus and rewriting it here would make the row disagree with
            # the transcript it summarises. `pr_href` is the same value only when a browser
            # may be pointed at it, and None otherwise, so the page never has to decide.
            "pr_url": pr_url, "pr_href": followable_url(pr_url), "pr_number": pr_number,
            "state": state, "registry": registry_state, "evidence": evidence,
            "pid": entry.get("pid"), "kind": entry.get("kind"),
            "name": entry.get("name"), "started_at": _started_at(entry),
        }

    rows = [
        row(stored["session_id"], stored["project"] or UNATTRIBUTED, stored["git_branch"],
            stored["first_ts"], stored["last_ts"], stored["title"], stored["entrypoint"],
            stored["cwd"], True, stored["pr_url"], stored["pr_number"])
        for stored in conn.execute(
            "SELECT session_id, project, cwd, git_branch, title, first_ts, last_ts, "
            "entrypoint, pr_url, pr_number FROM session")
    ]
    # A live session the store has never seen. It is not an edge case: a session that started
    # minutes ago has written a transcript and the ingester has not read it yet, and dropping
    # it would leave the one report that answers a question about now blind to the newest
    # thing on the machine.
    known = {entry["session_id"] for entry in rows}
    for session_id, seen in live.items():
        if session_id not in known:
            rows.append(row(session_id, seen["project"], None, None, None, None,
                            seen["entry"].get("entrypoint"), seen["entry"].get("cwd"),
                            False))

    if project:
        rows = [entry for entry in rows if entry["project"] == project]

    # Three stable sorts, dominant last: running before unverified before ended, then most
    # recent activity first, then the id so a tie is not decided by dictionary order.
    rows.sort(key=lambda entry: entry["session_id"])
    rows.sort(key=lambda entry: entry["last_activity"] or "", reverse=True)
    rows.sort(key=lambda entry: STATE_ORDER.index(entry["state"]))

    by_project: dict = {}
    for entry in rows:
        bucket = by_project.setdefault(
            entry["project"],
            {"project": entry["project"], "sessions": 0, "running": 0, "ended": 0,
             "unverified": 0, "stale_entries": 0})
        bucket["sessions"] += 1
        bucket[entry["state"]] += 1
        if entry["registry"] == "stale":
            bucket["stale_entries"] += 1
    breakdown = sorted(by_project.values(),
                       key=lambda bucket: (-bucket["sessions"], bucket["project"]))

    return {
        "report": "fleet",
        "project": project,
        "registry": {
            "path": found["path"], "present": found["present"],
            "entries": len(found["entries"]), "unreadable": found["unreadable"],
            "notes": found["notes"],
        },
        "liveness_check": ingest.liveness_check(),
        "liveness_policy": LIVENESS_POLICY,
        "unattributed_label": UNATTRIBUTED,
        "totals": {
            "sessions": len(rows),
            "running": sum(1 for entry in rows if entry["state"] == "running"),
            "ended": sum(1 for entry in rows if entry["state"] == "ended"),
            "unverified": sum(1 for entry in rows if entry["state"] == "unverified"),
            "stale_entries": sum(1 for entry in rows if entry["registry"] == "stale"),
            "not_yet_ingested": sum(1 for entry in rows if not entry["in_store"]),
        },
        "projects": breakdown,
        "sessions": rows,
    }


def _instant(ts):
    """A corpus timestamp as a datetime, or None when it is absent or unparseable.

    None rather than an exception, because a run whose time cannot be read still has a type,
    a model and an outcome worth reporting, and dropping the row to protect an arithmetic
    convenience is the failure `S-018`'s summing property exists to make visible.
    """
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _span_ms(start, end):
    """Milliseconds from `start` to `end`, or None when either end is missing."""
    first, last = _instant(start), _instant(end)
    if first is None or last is None:
        return None
    return int((last - first).total_seconds() * 1000)


# One row per dispatched agent, with the three figures `S-003` names taken from the harness
# where it recorded them and from the agent's own messages where it did not.
#
# The token subquery is the agent's **last** message rather than a sum over all of them, and
# that is not a shortcut. Checked against the 19 runs carrying both: the harness's total equals
# the last message's four token kinds added up, exactly on 17 and within 9 percent on the other
# two, while summing every message overstates it by 20 to 60 times because each message's input
# and cache-read counts include the whole conversation before it again.
#
# Tool calls join through `message.uuid` rather than `tool_call.session_id`, because a subagent
# transcript reuses its parent's `sessionId` and the session column therefore cannot tell an
# agent's tool calls from the dispatching session's own.
AGENT_RUN_QUERY = """
SELECT a.agent_id, a.session_id, a.agent_type, a.resolved_model, a.status,
       a.total_tokens, a.total_duration_ms, a.total_tool_use_count,
       a.description, a.worktree_path, a.worktree_branch, a.spawn_depth,
       s.project AS project,
       t.ts AS dispatched_at,
       (SELECT MIN(m.ts) FROM message m WHERE m.agent_id = a.agent_id) AS first_activity,
       (SELECT MAX(m.ts) FROM message m WHERE m.agent_id = a.agent_id) AS last_activity,
       (SELECT COUNT(*) FROM message m WHERE m.agent_id = a.agent_id) AS messages,
       (SELECT COUNT(*) FROM tool_call tc JOIN message m ON m.uuid = tc.message_uuid
          WHERE m.agent_id = a.agent_id) AS derived_tool_calls,
       (SELECT m.input_tokens + m.output_tokens + m.cache_read_tokens
               + m.cache_creation_tokens
          FROM message m WHERE m.agent_id = a.agent_id
          ORDER BY m.ts DESC, m.uuid DESC LIMIT 1) AS derived_tokens
FROM agent_run a
LEFT JOIN tool_call t ON t.tool_use_id = a.tool_use_id
LEFT JOIN session s ON s.session_id = a.session_id
"""


def _outcome_of(status):
    """The outcome name for a result record's status. Never a failure: see `OUTCOME_POLICY`."""
    if status is None:
        return "unrecorded"
    return OUTCOME_OF_STATUS.get(status, "unrecognised")


def agent_runs(conn, project: str | None = None) -> list[dict]:
    """Every dispatched agent, with its type, model, duration, tokens, tool calls and outcome.

    This is `S-003` on its own. Each of the three figures carries the basis it came from, so a
    reader is never shown an exact figure and an approximation side by side without being told
    which is which.

    A run whose session carries no project lands in `UNATTRIBUTED` rather than being dropped,
    for the reason the fleet report gives: restricting to each project in turn has to add back
    up to the unrestricted figures, and a dropped row breaks that while every panel still
    renders.
    """
    runs = []
    for row in conn.execute(AGENT_RUN_QUERY):
        if row["total_tokens"] is not None:
            tokens, tokens_basis = row["total_tokens"], "reported"
        elif row["derived_tokens"] is not None:
            tokens, tokens_basis = row["derived_tokens"], "derived"
        else:
            tokens, tokens_basis = None, "unknown"

        if row["total_tool_use_count"] is not None:
            tool_calls, tool_calls_basis = row["total_tool_use_count"], "reported"
        elif row["messages"]:
            # Zero here is a measured zero: the agent wrote messages and called no tool.
            tool_calls, tool_calls_basis = row["derived_tool_calls"], "derived"
        else:
            tool_calls, tool_calls_basis = None, "unknown"

        derived_span = _span_ms(row["first_activity"], row["last_activity"])
        if row["total_duration_ms"] is not None:
            duration_ms, duration_basis = row["total_duration_ms"], "reported"
        elif derived_span is not None:
            duration_ms, duration_basis = derived_span, "derived"
        else:
            duration_ms, duration_basis = None, "unknown"

        if row["dispatched_at"]:
            started, started_basis = row["dispatched_at"], "dispatch record"
        elif row["first_activity"]:
            started, started_basis = row["first_activity"], "first message"
        else:
            started, started_basis = None, "unknown"

        runs.append({
            "agent_id": row["agent_id"],
            "session_id": row["session_id"],
            "project": row["project"] or UNATTRIBUTED,
            "agent_type": row["agent_type"],
            "resolved_model": row["resolved_model"],
            "description": row["description"],
            "status": row["status"],
            "outcome": _outcome_of(row["status"]),
            "started": started, "started_basis": started_basis,
            "ended": row["last_activity"],
            "ended_basis": "last message" if row["last_activity"] else "unknown",
            "dispatched_at": row["dispatched_at"],
            "duration_ms": duration_ms, "duration_basis": duration_basis,
            "tokens": tokens, "tokens_basis": tokens_basis,
            "tool_calls": tool_calls, "tool_calls_basis": tool_calls_basis,
            "messages": row["messages"],
            "worktree_path": row["worktree_path"],
            "worktree_branch": row["worktree_branch"],
            "spawn_depth": row["spawn_depth"],
        })

    if project:
        runs = [run for run in runs if run["project"] == project]
    # A run with no start time sorts last within its session rather than first, so it cannot
    # anchor a wave it has no time to belong to.
    runs.sort(key=lambda run: (run["session_id"], run["started"] is None,
                               run["started"] or "", run["agent_id"]))
    return runs


def group_waves(runs: list[dict], gap_seconds: float = WAVE_GAP_SECONDS) -> list[dict]:
    """Group runs into waves by the rule `WAVE_RULE` states, one wave per burst.

    `runs` must already be ordered by session and then by start, which `agent_runs` does. A run
    with no start time cannot be placed in time, so it breaks the run it would otherwise have
    joined and becomes a wave of its own rather than being silently attached to a neighbour.
    """
    waves: list[dict] = []
    current: list[dict] = []
    previous = None

    def close(members):
        if members:
            waves.append(_wave_of(members))

    for run in runs:
        at = _instant(run["started"])
        same_session = previous is not None and previous["session_id"] == run["session_id"]
        within = (same_session and at is not None and previous["at"] is not None
                  and (at - previous["at"]).total_seconds() <= gap_seconds)
        if not within:
            close(current)
            current = []
        current.append(run)
        previous = {"session_id": run["session_id"], "at": at}
    close(current)

    waves.sort(key=lambda wave: (wave["started"] or "", wave["session_id"]), reverse=True)
    return waves


def _bar(started, ended, wave_started, span_ms):
    """Where a member's own span sits inside its wave's, as two fractions of the wave.

    Computed here rather than on the page for one reason: the page's script has no execution
    coverage in this repository, and arithmetic nothing can run is arithmetic nobody can check.
    Two numbers the page multiplies by a width are checkable; the same sums written in
    JavaScript are not.

    `None` when the member has no start time, which is what tells the page to draw nothing
    rather than to draw a bar at an invented position. A wave with no span at all, one dispatch
    or several inside the same instant, gives every member the full width, because a zero-width
    wave has no inside to place anything in.

    **There is deliberately no clamp holding the bar inside its wave.** The wave's start is the
    earliest member start and its end the latest member end, so `offset + width` is at most one
    by construction, and a clamp would be a branch no input can reach: unreachable code that
    reads as a safeguard is the "check that cannot fail" the conventions section of `AGENTS.md`
    warns about. The invariant is asserted by a test instead. The one comparison that is
    reachable stays: a run whose last message predates its dispatch record yields a negative
    length, and that becomes a zero-width mark rather than a bar drawn backwards.
    """
    if not started:
        return None
    if not span_ms or span_ms <= 0:
        return {"offset": 0.0, "width": 1.0}
    offset_ms = _span_ms(wave_started, started)
    if offset_ms is None:
        return None
    length_ms = _span_ms(started, ended) if ended else 0
    if length_ms is None or length_ms < 0:
        length_ms = 0
    return {"offset": round(offset_ms / span_ms, 6),
            "width": round(length_ms / span_ms, 6)}


def _last_moment(member: dict):
    """The last moment a member is known to have reached: its end, or its start when that is
    later or when it has no end at all.

    Taking the later of the two is what keeps a wave's window around all of its members. A run
    dispatched after every other member's last message, or one whose own last message predates
    its dispatch record, would otherwise sit outside the window the timeline is drawn in.
    """
    stamps = [stamp for stamp in (member["started"], member["ended"]) if stamp]
    return max(stamps) if stamps else None


def _sum_basis(members: list[dict], field: str) -> str:
    """The basis of a sum, which is the weakest basis among the figures that went into it.

    Exactness does not survive addition. A total assembled from four reported figures and one
    derived one is derived, because the derived one's error is in the total, so this reports
    the whole sum at the weaker basis rather than letting four exact figures launder a fifth.
    `unknown` members are excluded before this runs (they contribute nothing to the sum), so a
    sum over none of them is itself unknown.
    """
    bases = {member[f"{field}_basis"] for member in members
             if member[field] is not None}
    if not bases:
        return "unknown"
    return "reported" if bases == {"reported"} else "derived"


def _wave_of(members: list[dict]) -> dict:
    """One wave, summarised from its members. Every member keeps its own fields."""
    started = min((m["started"] for m in members if m["started"]), default=None)
    ended = max((moment for moment in map(_last_moment, members) if moment), default=None)
    span = _span_ms(started, ended)
    for member in members:
        member["bar"] = _bar(member["started"], member["ended"], started, span)
    outcomes = {entry["id"]: 0 for entry in RUN_OUTCOMES}
    for member in members:
        outcomes[member["outcome"]] += 1
    depths = [m["spawn_depth"] for m in members if m["spawn_depth"] is not None]
    tokens = [m["tokens"] for m in members if m["tokens"] is not None]
    tool_calls = [m["tool_calls"] for m in members if m["tool_calls"] is not None]
    isolated = [m for m in members if m["worktree_path"]]
    # A sum is only as exact as the least exact figure in it. A wave whose members are all
    # reported is reported; one derived member makes the whole total derived, because the
    # error it carries is in the sum too. Without this the wave tables render bare numbers
    # under a legend promising a tilde, which is the one thing the run rows already avoid.
    tokens_basis = _sum_basis(members, "tokens")
    tool_calls_basis = _sum_basis(members, "tool_calls")
    return {
        "wave_id": f"{members[0]['session_id']}@{started or members[0]['agent_id']}",
        "session_id": members[0]["session_id"],
        "project": members[0]["project"],
        "started": started,
        "ended": ended,
        "span_ms": span,
        "size": len(members),
        "isolated": len(isolated),
        "workspaces": len({m["worktree_path"] for m in isolated}),
        "branches": len({m["worktree_branch"] for m in isolated if m["worktree_branch"]}),
        "outcomes": outcomes,
        # Counted separately from the sums, so a total assembled over half its members is not
        # read as the wave's whole cost. Both reach the page: the count as "n of m", the basis
        # as the same tilde the run rows carry.
        "tokens": sum(tokens) if tokens else None,
        "tokens_known": len(tokens),
        "tokens_basis": tokens_basis,
        "tool_calls": sum(tool_calls) if tool_calls else None,
        "tool_calls_known": len(tool_calls),
        "tool_calls_basis": tool_calls_basis,
        # The span is bounded by the members' own endpoints, and an end time is only ever the
        # last message. So this is derived whenever it exists, and says so rather than looking
        # like a figure the harness reported.
        "span_basis": "derived" if span is not None else "unknown",
        "max_depth": max(depths) if depths else None,
        "nested": sum(1 for depth in depths if depth > 1),
        "types": sorted({m["agent_type"] for m in members if m["agent_type"]}),
        "models": sorted({m["resolved_model"] for m in members if m["resolved_model"]}),
        "members": members,
    }


def waves_report(conn, project: str | None = None,
                 gap_seconds: float = WAVE_GAP_SECONDS) -> dict:
    """The waves report: what each dispatched agent cost, and the wave it belonged to.

    `S-003` is the run rows and `S-004` is the grouping. Both are served from one payload
    because they are two readings of the same set: a wave is exactly the runs it holds, so
    reporting them apart would let the two disagree about how many runs exist.

    The rule that decides a wave, and the bound on that rule, travel in the payload rather than
    living only here. The task's acceptance criterion asks for it in the report surface, and
    the reason is the same one `LIVENESS_POLICY` exists for: a grouping a reader cannot check
    the meaning of is a grouping they will over-trust.
    """
    dispatched = agent_runs(conn, project)
    waves = group_waves(dispatched, gap_seconds)
    # Re-laid in wave order, so the run table and the wave table above it read the same way
    # round. Grouping needs session-then-time order and a reader wants most recent first.
    runs = [member for wave in waves for member in wave["members"]]

    # Counted from what came out of the store, not from what came out of the grouping. Deriving
    # this from `runs` would make "the wave sizes add up to the runs" true by construction: a
    # grouping that dropped a member would drop it from both sides of the identity and the
    # arithmetic would still balance. Found by mutation, after an earlier version did exactly
    # that.
    total_runs = len(dispatched)

    outcomes = {entry["id"]: 0 for entry in RUN_OUTCOMES}
    bases = {entry["id"]: 0 for entry in FIGURE_BASES}
    for run in dispatched:
        outcomes[run["outcome"]] += 1
        bases[run["tokens_basis"]] += 1

    by_project: dict = {}
    for wave in waves:
        bucket = by_project.setdefault(
            wave["project"],
            {"project": wave["project"], "runs": 0, "waves": 0, "isolated": 0})
        bucket["waves"] += 1
        bucket["runs"] += wave["size"]
        bucket["isolated"] += wave["isolated"]
    breakdown = sorted(by_project.values(),
                       key=lambda bucket: (-bucket["runs"], bucket["project"]))

    tokens = [run["tokens"] for run in dispatched if run["tokens"] is not None]
    depths = [run["spawn_depth"] for run in dispatched
              if run["spawn_depth"] is not None]
    return {
        "report": "waves",
        "project": project,
        "wave_gap_seconds": gap_seconds,
        "wave_rule": WAVE_RULE,
        "wave_rule_bound": WAVE_RULE_BOUND,
        "outcome_policy": OUTCOME_POLICY,
        "outcomes_legend": list(RUN_OUTCOMES),
        "bases_legend": list(FIGURE_BASES),
        "derivation_note": DERIVATION_NOTE,
        "nesting_policy": NESTING_POLICY,
        "unattributed_label": UNATTRIBUTED,
        "totals": {
            "runs": total_runs,
            "waves": len(waves),
            "waves_of_several": sum(1 for wave in waves if wave["size"] > 1),
            "single_dispatches": sum(1 for wave in waves if wave["size"] == 1),
            "sessions": len({run["session_id"] for run in dispatched}),
            "isolated_runs": sum(1 for run in dispatched if run["worktree_path"]),
            "nested_runs": sum(1 for depth in depths if depth > 1),
            "max_depth": max(depths) if depths else None,
            "tokens": sum(tokens) if tokens else None,
            "tokens_known": len(tokens),
            "outcomes": outcomes,
            "token_bases": bases,
        },
        "projects": breakdown,
        "waves": waves,
        "runs": runs,
    }


def _rate(value):
    """A rate, or None. A rate has to be a non-negative number and nothing else.

    `True` is an `int` in Python, so the `bool` guard is load-bearing: without it a hand-edited
    `"input": true` would price a model at one dollar per million tokens and look deliberate.
    """
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value >= 0 else None


def _boundary(value):
    """An ISO date bounding a rate period, or None for unbounded on that side.

    Anything that is not a `YYYY-MM-DD` string is None, which reads as unbounded. That is the
    permissive direction and it is the right one here: the alternative is a typo in a hand-
    edited table silently narrowing a period so some dates fall in no range and their tokens
    go unpriced, which looks like a corpus fact rather than an editing mistake.
    """
    return value if isinstance(value, str) and _ISO_DATE_RE.match(value) else None


def _rate_periods(entry, read_multiplier, creation_multiplier):
    """Every dated rate an entry declares, oldest bound first. Empty when it declares none.

    Two shapes, and the flat one is not deprecated (`bug-0057`). A model whose price has never
    changed carries `input` and `output` at the top level and gets one unbounded period, which
    is most of the table and would be noise as a one-element array. A model whose price has
    changed carries a `rates` list, each element bounded by `from` and `until` inclusive, either
    of which may be absent for unbounded on that side. Both may appear: `rates` wins, and the
    flat pair is then the fallback for a date no period covers, which is how a half-migrated
    table stays readable.

    Cache rates are derived per period from that period's own input rate, not from the entry's,
    because the multipliers are ratios against whatever input cost at the time.
    """
    periods = []
    declared = entry.get("rates")
    for raw in declared if isinstance(declared, list) else []:
        if not isinstance(raw, dict):
            continue
        base_input, base_output = _rate(raw.get("input")), _rate(raw.get("output"))
        if base_input is None or base_output is None:
            continue                          # half a rate is not a rate
        note = raw.get("note")
        periods.append({
            "from": _boundary(raw.get("from")),
            "until": _boundary(raw.get("until")),
            "input": base_input,
            "output": base_output,
            "cache_read": base_input * read_multiplier,
            "cache_creation": base_input * creation_multiplier,
            "note": note.strip() if isinstance(note, str) and note.strip() else None,
        })

    flat_input, flat_output = _rate(entry.get("input")), _rate(entry.get("output"))
    if flat_input is not None and flat_output is not None:
        note = entry.get("note")
        periods.append({
            # Unbounded on both sides, so it covers any date no declared period does. On an
            # unmigrated entry that is every date, which is the whole of the old behaviour.
            "from": None,
            "until": None,
            "input": flat_input,
            "output": flat_output,
            "cache_read": flat_input * read_multiplier,
            "cache_creation": flat_input * creation_multiplier,
            "note": note.strip() if isinstance(note, str) and note.strip() else None,
        })

    # Bounded periods first, so `rate_in_force` finds a specific answer before the catch-all.
    # `from` sorted descending inside that, so the latest applicable period wins where two
    # overlap, which is what a hand-edited table with a sloppy boundary most likely meant.
    periods.sort(key=lambda p: (p["from"] is None and p["until"] is None,
                                p["from"] is None, _neg_date(p["from"])))
    return periods


def _neg_date(value):
    """A sort key putting later dates first, with None last. Strings do not negate."""
    return "" if value is None else "".join(chr(255 - ord(c)) for c in value)


def rate_in_force(periods, when):
    """The rate covering `when`, or None when no period does.

    `when` is a date the corpus recorded, never today. That distinction is the whole design
    constraint here and it is stated in `pricing.json`'s own notes: the report derives
    everything it says from the corpus, so introducing a clock would make two runs over the
    same corpus disagree. A session's timestamp is corpus data; the system date is not.

    A date matching no period is unpriced rather than priced at the nearest guess, which is
    `S-011`'s rule applied one level down: a model with rates that do not cover a message is
    exactly as unpriceable as a model with no rates at all, and inventing a figure is the one
    thing that scenario forbids.
    """
    if not when:
        return None
    day = when[:10]
    if not _ISO_DATE_RE.match(day):
        return None
    for period in periods:
        if period["from"] is not None and day < period["from"]:
            continue
        if period["until"] is not None and day > period["until"]:
            continue
        return period
    return None


def load_pricing(path=None) -> dict:
    """The rate table, read from a local file. Never fetched, at any point (`S-022`).

    Three properties are why this returns a table rather than raising.

    **A model is priced only when all four of its rates resolve.** Input and output come from
    the table; cache read and cache creation come from the table's multipliers against the
    model's own input rate. A half-resolved model would be worse than an unpriced one, because
    its cost would look like a figure while quietly omitting whichever kind had no rate, and
    cache reads are the largest kind in this corpus by a wide margin.

    **A missing or unparseable table is a normal state.** It makes every model unpriced, which
    is exactly the path `S-011` describes, so the report still carries every token figure and
    says the cost is unknown. Raising here would take the token halves of the report down with
    the cost half over a bad edit to one JSON file.

    **Nothing here normalises a model name.** A key is present or the model is unpriced. A
    prefix match would silently price a model nobody has a rate for, which is the failure the
    whole table is arranged around.
    """
    path = PRICING_PATH if path is None else Path(path)
    table = {
        "path": str(path), "present": False, "as_of": None, "transcribed": None,
        "currency": None, "unit": None, "source": None, "source_author": None,
        "models": {}, "cache_multipliers": {}, "note": "", "rate_notes": [],
    }

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        table["note"] = (f"No rate table at {path}. Every model is therefore unpriced and "
                         f"every cost is unknown rather than zero.")
        return table
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        table["note"] = (f"The rate table at {path} does not parse ({exc}). Every model is "
                         f"therefore unpriced and every cost is unknown rather than zero.")
        return table
    if not isinstance(raw, dict):
        table["note"] = (f"The rate table at {path} is not an object. Every model is therefore "
                         f"unpriced and every cost is unknown rather than zero.")
        return table

    table["present"] = True
    for key in ("as_of", "transcribed", "currency", "unit", "source", "source_author"):
        value = raw.get(key)
        table[key] = value if isinstance(value, str) else None

    multipliers = raw.get("cache_multipliers")
    multipliers = multipliers if isinstance(multipliers, dict) else {}
    read_multiplier = _rate(multipliers.get("cache_read"))
    creation_multiplier = _rate(multipliers.get("cache_creation"))
    table["cache_multipliers"] = {"cache_read": read_multiplier,
                                  "cache_creation": creation_multiplier}

    if read_multiplier is None or creation_multiplier is None:
        table["note"] = (f"The rate table at {path} carries no usable cache multipliers, so no "
                         f"model can be priced across all four token kinds. Every model is "
                         f"therefore unpriced and every cost is unknown rather than zero.")
        return table

    models = raw.get("models")
    for name, entry in (models if isinstance(models, dict) else {}).items():
        if not isinstance(entry, dict):
            continue
        periods = _rate_periods(entry, read_multiplier, creation_multiplier)
        if not periods:
            continue                          # half a rate is not a rate, and neither is none
        table["models"][name] = periods
        # A rate can be correct and temporary at once, and the number alone cannot say so.
        # Carried to the report and never priced with: a note is for the reader, and letting
        # it reach the arithmetic would be a second rate table nobody declared.
        for period in periods:
            if period["note"]:
                table["rate_notes"].append({
                    "model": name,
                    "note": period["note"],
                    "from": period["from"],
                    "until": period["until"],
                })

    if not table["models"]:
        table["note"] = (f"The rate table at {path} names no model with a usable rate. Every "
                         f"model is therefore unpriced and every cost is unknown rather than "
                         f"zero.")
    else:
        table["note"] = (f"{len(table['models'])} model(s) priced from {path}, recorded "
                         f"{table['as_of']}.")
    return table


def load_quota(path=None) -> dict:
    """The optional quota sample series, or a stated absence.

    The contract's Sources table marks this source not required, and `S-017`'s implementation
    note says its absence degrades the report to the context half rather than failing it. That
    is the path this machine actually takes: nothing the harness ships writes such a file, so
    absent is the normal outcome and is reported as a state rather than as an error.
    """
    result = {
        "path": None if path is None else str(path), "available": False,
        "reason": "", "format": QUOTA_FORMAT, "provenance": QUOTA_PROVENANCE,
        "samples": 0, "unreadable": 0, "windows": [], "series": [],
    }
    if path is None:
        # No "above" or "below" here: the same sentence is printed to the terminal at startup,
        # where the page's layout does not exist and a direction refers to nothing.
        result["reason"] = ("No quota source configured. Point --quota at a sample series to "
                            "report the quota half. The context half of pressure is "
                            "unaffected and is reported in full.")
        return result

    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        result["reason"] = (f"No quota sample series at {path}, so only the context half of "
                            f"pressure is reported. That is the expected state: nothing on "
                            f"this machine writes one.")
        return result

    series = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            result["unreadable"] += 1
            continue
        if not isinstance(record, dict):
            result["unreadable"] += 1
            continue
        ts = record.get("ts")
        used = _rate(record.get("used_percent"))
        if not isinstance(ts, str) or used is None:
            result["unreadable"] += 1
            continue
        window = record.get("window")
        series.append({"ts": ts, "used_percent": used,
                       "window": window if isinstance(window, str) else "(unnamed)"})

    series.sort(key=lambda sample: (sample["window"], sample["ts"]))
    result["series"] = series
    result["samples"] = len(series)
    result["available"] = bool(series)
    if not series:
        result["reason"] = (f"The quota sample series at {path} holds no readable sample, so "
                            f"only the context half of pressure is reported.")
        return result

    windows: dict = {}
    for sample in series:
        bucket = windows.setdefault(sample["window"], {
            "window": sample["window"], "samples": 0, "first_ts": sample["ts"],
            "last_ts": sample["ts"], "peak_used_percent": sample["used_percent"],
            "latest_used_percent": sample["used_percent"],
        })
        bucket["samples"] += 1
        bucket["first_ts"] = min(bucket["first_ts"], sample["ts"])
        if sample["ts"] >= bucket["last_ts"]:
            bucket["last_ts"] = sample["ts"]
            bucket["latest_used_percent"] = sample["used_percent"]
        bucket["peak_used_percent"] = max(bucket["peak_used_percent"],
                                          sample["used_percent"])
    result["windows"] = sorted(windows.values(), key=lambda w: w["window"])
    result["reason"] = (f"{len(series)} sample(s) across {len(result['windows'])} window(s) "
                        f"from {path}.")
    return result


def context_pressure(conn, project: str | None = None) -> dict:
    """The context half of `S-017`: the budget series, and the compactions in it.

    The series is bucketed by day for the chart and reported raw in two other shapes, because
    a daily mean answers "how has pressure trended" and hides "how close did anything actually
    get". `lowest` answers the second, and `compactions` answers the scenario's own clause
    about occasions being identifiable, from the only record in the corpus that marks one.
    """
    # Built as a bare predicate and joined by each caller, rather than as a clause carrying its
    # own `WHERE`. The clause form was written first and was wrong: it holds a second `WHERE`
    # inside its subquery, and rewriting `WHERE` to `AND` to reuse it rewrote both.
    scope, params = "", ()
    if project:
        # `session` is the only table carrying a project for a context sample, so a session the
        # store has no row for is out of scope here. Said in the payload rather than assumed.
        scope = "session_id IN (SELECT session_id FROM session WHERE project = ?)"
        params = (project,)

    samples = conn.execute(
        "SELECT session_id, ts, tokens_left FROM context_sample"
        + (f" WHERE {scope}" if scope else "") + " ORDER BY ts", params).fetchall()
    compactions = conn.execute(
        "SELECT session_id, ts, detail FROM health_event WHERE kind = 'compact_boundary'"
        + (f" AND {scope}" if scope else "") + " ORDER BY ts", params).fetchall()

    daily: dict = {}
    for row in samples:
        left = row["tokens_left"]
        if left is None:
            continue
        day = (row["ts"] or "")[:10]
        bucket = daily.setdefault(day, {"day": day, "samples": 0,
                                        "min_tokens_left": left, "max_tokens_left": left})
        bucket["samples"] += 1
        bucket["min_tokens_left"] = min(bucket["min_tokens_left"], left)
        bucket["max_tokens_left"] = max(bucket["max_tokens_left"], left)

    readings = [row for row in samples if row["tokens_left"] is not None]
    lowest = sorted(readings, key=lambda row: row["tokens_left"])[:10]

    return {
        "available": bool(samples),
        "samples": len(samples),
        "sessions": len({row["session_id"] for row in samples}),
        "source": "the corpus's `total_tokens_reminder` attachments, one per turn",
        "daily": sorted(daily.values(), key=lambda bucket: bucket["day"]),
        "lowest": [{"session_id": row["session_id"], "ts": row["ts"],
                    "tokens_left": row["tokens_left"]} for row in lowest],
        "compactions": [{"session_id": row["session_id"], "ts": row["ts"]}
                        for row in compactions],
        "compaction_count": len(compactions),
        "reason": ("" if samples else
                   "No context-budget records in scope, so there is no series to report."),
    }


def cost_report(conn, project: str | None = None, pricing=None, quota=None) -> dict:
    """Tokens by kind, an estimated cost that never invents a figure, and pressure over time.

    Scenarios `S-010`, `S-011`, `S-017` and `S-021`. Three things about the shape are the point.

    **Tokens are counted over canonical message rows, never over joined occurrences.** A forked
    or resumed session replays earlier history verbatim, so one uuid legitimately appears in
    more than one transcript, and `SUM` over a join to `message_occurrence` would add that
    message's tokens once per replay. The scoped branch therefore selects the uuid set first and
    sums `message` itself, which is the same trap the skills report answers with
    `COUNT(DISTINCT uuid)` and the reason `message` holds one row per uuid at all.

    **An unpriced model is unknown, not zero, and the unknown reaches the total** (`S-011`). Its
    tokens are reported, its `cost_usd` is `None`, and the total carries `complete: false` with
    the offending models named, so a figure covering unpriced sessions cannot read as a
    complete one.

    **Thinking tokens are a memo, not a fifth kind.** They arrive from `output_tokens_details`
    and are already inside `output_tokens`, so they are reported beside the four and are absent
    from every cost figure. Adding them would double-count output.
    """
    table = load_pricing() if pricing is None else pricing
    quota = load_quota(None) if quota is None else quota

    kinds = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
    columns = kinds + ("thinking_tokens",)
    sums = ", ".join(f"COALESCE(SUM({column}), 0) AS {column}" for column in columns)

    # Grouped by day as well as by model since `bug-0057`, because a rate can change under a
    # corpus that does not. The day comes from the message's own timestamp, which is corpus
    # data: pricing each message against the rate in force on its own date leaves two runs a
    # month apart producing identical output, which is the property `pricing.json`'s own notes
    # protect and which a comparison against today would destroy. Cheap at this shape: 90
    # (model, day) rows over 59,447 messages on the maintainer's corpus, measured 2026-08-30.
    if project:
        rows = conn.execute(
            f"SELECT model, substr(ts, 1, 10) AS day, COUNT(*) AS messages, {sums} FROM message "
            f"WHERE uuid IN (SELECT uuid FROM message_occurrence WHERE project = ?) "
            f"GROUP BY model, day", (project,)).fetchall()
    else:
        rows = conn.execute(
            f"SELECT model, substr(ts, 1, 10) AS day, COUNT(*) AS messages, {sums} FROM message "
            f"GROUP BY model, day").fetchall()

    gathered = {}
    for row in rows:
        name = row["model"] or MODEL_UNRECORDED
        bucket = gathered.setdefault(name, {
            "messages": 0,
            "counts": {column: 0 for column in columns},
            "by_period": {},        # id(period) -> {"period":.., "counts":..}
            "undated": [],          # days no declared period covers
        })
        bucket["messages"] += row["messages"]
        for column in columns:
            bucket["counts"][column] += row[column]

        period = rate_in_force(table["models"].get(name) or [], row["day"])
        if period is None:
            bucket["undated"].append(row["day"] or "(no timestamp)")
            continue
        slot = bucket["by_period"].setdefault(
            id(period), {"period": period, "counts": {column: 0 for column in columns}})
        for column in columns:
            slot["counts"][column] += row[column]

    def _cost(counts, rates):
        return sum(counts[kind] / 1_000_000 * rates[kind[: -len("_tokens")]] for kind in kinds)

    models = []
    for name, bucket in gathered.items():
        counts = bucket["counts"]
        # All or nothing per model, matching how a half-resolved rate is already treated one
        # level up: "A half-resolved model would be worse than an unpriced one, because its
        # cost would look like a figure while quietly omitting whichever kind had no rate."
        # A day the table does not cover is the same shape across time rather than across
        # token kinds, so a model with any such day is unpriced and says which days (`S-011`).
        priced = bool(bucket["by_period"]) and not bucket["undated"]
        applied = [
            {"from": slot["period"]["from"], "until": slot["period"]["until"],
             "note": slot["period"]["note"],
             **{kind[: -len("_tokens")]: slot["period"][kind[: -len("_tokens")]]
                for kind in kinds},
             "tokens": sum(slot["counts"][kind] for kind in kinds),
             "cost_usd": round(_cost(slot["counts"], slot["period"]), 6)}
            for slot in bucket["by_period"].values()
        ]
        applied.sort(key=lambda a: (a["from"] or "", a["until"] or ""))
        entry = {
            "model": name,
            "messages": bucket["messages"],
            "tokens": sum(counts[kind] for kind in kinds),
            "priced": priced,
            # The four rates when exactly one period priced this model, which is every model
            # whose price never changed and is what a reader means by "the rate". None when
            # two applied, because there is no single answer and inventing one would be a
            # figure nobody could reconcile against the breakdown below it.
            "rate": ({kind[: -len("_tokens")]: applied[0][kind[: -len("_tokens")]]
                      for kind in kinds} if priced and len(applied) == 1 else None),
            "rates_applied": applied if priced else [],
            "unpriced_days": sorted(set(bucket["undated"])),
            "cost_usd": round(sum(a["cost_usd"] for a in applied), 6) if priced else None,
        }
        entry.update(counts)
        models.append(entry)

    # Priced first, then by what each cost, then by tokens so an unpriced row with real
    # consumption is not buried under one with none.
    models.sort(key=lambda entry: (not entry["priced"], -(entry["cost_usd"] or 0),
                                   -entry["tokens"], entry["model"]))

    totals = {column: sum(entry[column] for entry in models) for column in columns}
    input_side = (totals["input_tokens"] + totals["cache_read_tokens"]
                  + totals["cache_creation_tokens"])
    unpriced = [entry for entry in models if not entry["priced"]]
    unpriced_tokens = sum(entry["tokens"] for entry in unpriced)

    if not models:
        completeness = "No messages in scope, so there is nothing to price."
    elif unpriced:
        completeness = (
            f"Incomplete. This total covers {len(models) - len(unpriced)} of {len(models)} "
            f"model(s) and excludes {unpriced_tokens} token(s) across "
            f"{sum(entry['messages'] for entry in unpriced)} message(s) from "
            f"{len(unpriced)} unpriced model(s): "
            f"{', '.join(entry['model'] for entry in unpriced)}. Their cost is unknown, not "
            f"zero.")
    else:
        completeness = "Complete: every model in scope has a rate in the table."

    return {
        "report": "cost",
        "project": project,
        "estimate_label": ESTIMATE_LABEL,
        "historical_note": HISTORICAL_RATES_NOTE,
        "unpriced_policy": UNPRICED_POLICY,
        "rates": {
            "path": table["path"], "present": table["present"], "as_of": table["as_of"],
            "transcribed": table["transcribed"], "currency": table["currency"],
            "unit": table["unit"], "source": table["source"],
            "source_author": table["source_author"], "priced_models": len(table["models"]),
            "cache_multipliers": table["cache_multipliers"], "note": table["note"],
            "rate_notes": table["rate_notes"],
        },
        "tokens": {
            "input": totals["input_tokens"],
            "output": totals["output_tokens"],
            "cache_read": totals["cache_read_tokens"],
            "cache_creation": totals["cache_creation_tokens"],
            "total": sum(totals[kind] for kind in kinds),
            "thinking_within_output": totals["thinking_tokens"],
            "messages": sum(entry["messages"] for entry in models),
        },
        "cache": {
            "basis": CACHE_SHARE_BASIS,
            "input_side_tokens": input_side,
            "served_share": (round(totals["cache_read_tokens"] / input_side, 6)
                             if input_side else None),
        },
        "cost": {
            # `None` when nothing in scope could be priced at all, rather than the sum of an
            # empty set. Zero dollars over 14 million tokens is the confident zero `S-011`
            # exists to prevent, and it is no less confident for having a true sentence under
            # it: `usd()` already prints `unknown` for a null, so the state has a rendering.
            "estimated_usd": (
                round(sum(entry["cost_usd"] for entry in models
                          if entry["cost_usd"] is not None), 6)
                if any(entry["cost_usd"] is not None for entry in models) else None),
            "complete": not unpriced,
            "priced_models": len(models) - len(unpriced),
            "unpriced_models": len(unpriced),
            "unpriced_model_names": [entry["model"] for entry in unpriced],
            "unpriced_tokens": unpriced_tokens,
            "unpriced_messages": sum(entry["messages"] for entry in unpriced),
            "note": completeness,
        },
        "models": models,
        "pressure": {
            "context": context_pressure(conn, project),
            "quota": quota,
        },
    }


def is_hook_event(kind: str) -> bool:
    """Whether a health event records a hook running at all, failed or not.

    Hook outcomes arrive as `attachment` records whose kind is the attachment's own type, so
    the set is open-ended and matched by prefix rather than enumerated: this maintainer's
    corpus carries `hook_additional_context`, `hook_success`, and `hook_non_blocking_error`
    on 2026-08-29, and nothing promises a fourth will not appear. `stop_hook_summary` is a
    `system` record rather than an attachment and is the one hook outcome not spelled that
    way, so it is named.
    """
    kind = kind or ""
    return kind.startswith("hook_") or kind == "stop_hook_summary"


def hook_failed(kind: str, exit_code) -> bool:
    """Whether a health event records a hook that failed.

    Both halves of the rule are load-bearing and neither alone is right. **An exit status
    decides it where there is one**: 126 `hook_success` records carry 0 and 19
    `hook_non_blocking_error` records carry 49. **The kind decides it where there is not**:
    all 205 `hook_additional_context` records carry no exit status at all, so an exit-code
    rule alone would read every one of them as a success it never established, and a kind
    rule alone would miss a non-zero exit on a kind nobody has met yet.

    A `stop_hook_summary` row is a failure by construction, because the ingester writes one
    only where the summary carried a hook error or prevented a continuation.
    """
    kind = kind or ""
    if kind == "stop_hook_summary":
        return True
    if not is_hook_event(kind):
        return False
    if exit_code is not None and exit_code != 0:
        return True
    return "error" in kind


def health_kind_role(kind: str) -> str:
    """One line saying what the health report does with a kind of record."""
    if kind in HEALTH_KIND_ROLES:
        return HEALTH_KIND_ROLES[kind]
    if is_hook_event(kind):
        return ("counted as a hook failure where its exit status is non-zero or its kind "
                "names an error, and as a hook that ran otherwise")
    return "not counted: this report does not classify this kind"


def _session_context(conn) -> tuple:
    """`(project, sort key, title)` per session, for placing and ordering a health event.

    The sort key is `(first_ts, session_id)` and the tie-break carries the real weight. A fork
    replays the parent's earliest record too, so both sessions report the same `first_ts` and
    the id is what actually decides: every one of the forked pairs carrying a health event in
    this maintainer's corpus is in exactly that position on 2026-08-29. **The corpus does not
    record which session originally produced a replayed record**, so the choice of which to
    name first is deterministic rather than meaningful, and that is why every session an event
    was seen in is reported beside it rather than only the chosen one.
    """
    projects, order, titles = {}, {}, {}
    for row in conn.execute(
            "SELECT session_id, project, first_ts, title FROM session"):
        projects[row["session_id"]] = row["project"] or UNATTRIBUTED
        order[row["session_id"]] = (row["first_ts"] or "", row["session_id"])
        titles[row["session_id"]] = row["title"]
    return projects, order, titles


def health_events(conn) -> list:
    """Every health event once, carrying every session it was observed in.

    The grouping is the whole of `HEALTH_REPLAY_POLICY` made mechanical. `health_event` has no
    canonical-versus-occurrence split of the kind `message` and `message_occurrence` have, so
    a replayed failure is a second row in the store and a `COUNT(*)` over it overstates by
    however much history has been replayed.
    """
    projects, order, titles = _session_context(conn)

    # The field list is projected from the identity tuple rather than spelled out again, so
    # the two cannot come to disagree about what makes one event distinct from another. The
    # names are this module's own constant, never anything a request supplies.
    columns = ", ".join(HEALTH_EVENT_FIELDS)
    grouped: dict = {}
    for row in conn.execute(f"SELECT session_id, {columns} FROM health_event"):
        key = tuple(row[field] for field in HEALTH_EVENT_FIELDS)
        grouped.setdefault(key, set()).add(row["session_id"])

    events = []
    for key, sessions in grouped.items():
        seen = sorted(sessions, key=lambda s: order.get(s, ("", s)))
        event = dict(zip(HEALTH_EVENT_FIELDS, key))
        event["session_id"] = seen[0]
        event["session_title"] = titles.get(seen[0])
        event["sessions"] = seen
        event["replays"] = len(seen) - 1
        event["project"] = projects.get(seen[0], UNATTRIBUTED)
        event["projects"] = sorted({projects.get(s, UNATTRIBUTED) for s in seen})
        events.append(event)

    events.sort(key=lambda event: (event["ts"] or "", event["session_id"]), reverse=True)
    return events


def abnormal_runs(conn) -> list:
    """Runs the corpus marks as having ended abnormally, once each.

    S-016's third part. The markers sit on assistant records rather than in `health_event`,
    which is why this reads `message`: `isApiErrorMessage` with its status, and
    `isAbortedMidStream`. A record may carry both, so the markers are a list rather than a
    kind.

    `message` already holds one canonical row per uuid, so this is a distinct-run count before
    anything is done to it; `message_occurrence` supplies every session the record appeared
    in, which is the same split the skills report uses and for the same reason.
    """
    projects, order, titles = _session_context(conn)

    seen: dict = {}
    for row in conn.execute(
            "SELECT o.uuid AS uuid, o.session_id AS session_id FROM message_occurrence o "
            "JOIN message m ON m.uuid = o.uuid "
            "WHERE m.is_api_error = 1 OR m.is_aborted_mid_stream = 1"):
        seen.setdefault(row["uuid"], set()).add(row["session_id"])

    runs = []
    for row in conn.execute(
            "SELECT uuid, session_id, ts, model, api_error_status, error, is_api_error, "
            "is_aborted_mid_stream FROM message "
            "WHERE is_api_error = 1 OR is_aborted_mid_stream = 1"):
        # The canonical row's own session is the fallback, for a record whose occurrence row
        # is absent. Only assistant records get one, and these are assistant records, so the
        # fallback is a belt rather than a path anything is known to take.
        sessions = sorted(seen.get(row["uuid"]) or {row["session_id"]},
                          key=lambda s: order.get(s, ("", s)))
        markers = []
        if row["is_api_error"]:
            markers.append("API error")
        if row["is_aborted_mid_stream"]:
            markers.append("aborted mid stream")
        runs.append({
            "uuid": row["uuid"], "session_id": sessions[0],
            "session_title": titles.get(sessions[0]), "sessions": sessions,
            "replays": len(sessions) - 1,
            "project": projects.get(sessions[0], UNATTRIBUTED),
            "projects": sorted({projects.get(s, UNATTRIBUTED) for s in sessions}),
            "ts": row["ts"], "model": row["model"], "status": row["api_error_status"],
            "detail": row["error"], "markers": markers,
        })

    runs.sort(key=lambda run: (run["ts"] or "", run["session_id"]), reverse=True)
    return runs


def retry_episodes(events) -> list:
    """Consecutive retries of one request, grouped into the episode they belong to.

    The corpus writes one `api_error` record per attempt carrying `retryAttempt`, which counts
    up within a request and restarts at 1 for the next one, so an episode ends where the count
    stops rising. Measured on 2026-08-29, the longest run on this machine reached 10.

    **Grouped rather than listed one attempt at a time**, because the signal this task names is
    a session quietly taking ten attempts per request, and ten rows each reading "attempt 1"
    through "attempt 10" state that only to a reader who adds them up. The episode is reported
    whatever it ended in: this report says how many attempts a request took and never whether
    it eventually succeeded, because the corpus records the retries and not the verdict, and
    collapsing an episode to success or failure would throw away the figure that matters.

    An event with no recorded attempt starts its own episode rather than joining the previous
    one, since nothing says it belongs there.
    """
    by_session: dict = {}
    for event in sorted(events, key=lambda event: (event["session_id"], event["ts"] or "")):
        by_session.setdefault(event["session_id"], []).append(event)

    episodes = []
    for session_id, series in by_session.items():
        current = None
        for event in series:
            attempt = event["attempt"]
            if current is None or attempt is None or attempt <= current["attempts"]:
                current = {
                    "session_id": session_id, "session_title": event["session_title"],
                    "sessions": event["sessions"], "project": event["project"],
                    "projects": event["projects"], "first_ts": event["ts"],
                    "last_ts": event["ts"], "attempts": attempt or 1, "events": 1,
                    "detail": event["detail"],
                }
                episodes.append(current)
            else:
                current["attempts"] = attempt
                current["last_ts"] = event["ts"]
                current["events"] += 1

    episodes.sort(key=lambda episode: (episode["last_ts"] or "", episode["session_id"]),
                  reverse=True)
    return episodes


def _kind_ledger(events) -> list:
    """Every kind of health record in scope, what it counted for, and what it did not.

    Built over the events rather than filtered out of them, so a kind this report does not
    treat as a failure is visible as a labelled zero rather than as an absence. That is what
    makes the `stop_hook_summary` branch reading nothing legible as the bound it is.
    """
    ledger: dict = {}
    for event in events:
        bucket = ledger.setdefault(
            event["kind"], {"kind": event["kind"], "events": 0, "records": 0})
        bucket["events"] += 1
        bucket["records"] += 1 + event["replays"]
    for kind in DECLARED_HEALTH_KINDS:
        ledger.setdefault(kind, {"kind": kind, "events": 0, "records": 0})

    rows = list(ledger.values())
    for row in rows:
        row["role"] = health_kind_role(row["kind"])
        # Whether this report counts the kind toward any figure at all, which is a different
        # question from whether it is a failure: a hook that succeeded is counted as a hook
        # that ran, and that is what makes the failure count a proportion rather than a number
        # floating free.
        row["counted"] = is_hook_event(row["kind"]) or row["kind"] == "api_error"
    rows.sort(key=lambda row: (-row["events"], row["kind"]))
    return rows


def health_report(conn, project: str | None = None) -> dict:
    """The health report: what failed, and how often (S-016).

    Three kinds of thing, each with the session it occurred in, when it occurred, and what it
    reported: a hook that failed, carrying its exit status; an API error, carrying the number
    of attempts the request took; and a run the corpus marks as having ended abnormally.

    Three properties are the shape of this function, and none of them is visible from the
    figures alone.

    **A count here is of events, not of records** (`HEALTH_REPLAY_POLICY`). See
    `health_events`, which is where the grouping happens and where the reason is.

    **A kind this report does not count is still listed**, in `kinds`, rather than filtered
    where nobody can see it went.

    **The report states what it cannot see** (`HEALTH_BLIND_SPOT`), because a hook that never
    ran leaves nothing to read and an empty result would otherwise be mistaken for a clean
    one. That qualification is served with the figures rather than left in a code comment, for
    the reason the task states: it is the same claim `AGENTS.md` makes about a passing gate
    set being necessary and not sufficient.
    """
    events = health_events(conn)
    runs = abnormal_runs(conn)

    # Scoped before anything is counted, so every figure below is the scoped figure and the
    # per-project sums are the unrestricted ones. An event is in a project when any session it
    # was seen in is, which is the same bound the skills report states: an event that spanned
    # two projects would be counted in each. It does not occur on this corpus, where 0 of 345
    # events and 0 of 28 abnormal runs span more than one project as of 2026-08-29.
    if project:
        events = [event for event in events if project in event["projects"]]
        runs = [run for run in runs if project in run["projects"]]

    hook_events = [event for event in events if is_hook_event(event["kind"])]
    hook_failures = [event for event in hook_events
                     if hook_failed(event["kind"], event["exit_code"])]
    api_errors = [event for event in events if event["kind"] == "api_error"]
    episodes = retry_episodes(api_errors)

    totals = {
        "events": len(events),
        # What those events were written as, so the gap between the two is on the page rather
        # than only in the policy sentence explaining it.
        "records": sum(1 + event["replays"] for event in events),
        "hook_events": len(hook_events),
        "hook_failures": len(hook_failures),
        "api_errors": len(api_errors),
        "retry_episodes": len(episodes),
        "worst_attempts": max((episode["attempts"] for episode in episodes), default=0),
        "abnormal_runs": len(runs),
        "sessions_affected": len(
            {session for event in events for session in event["sessions"]}
            | {session for run in runs for session in run["sessions"]}),
    }

    return {
        "report": "health",
        "project": project,
        "blind_spot": HEALTH_BLIND_SPOT,
        "replay_policy": HEALTH_REPLAY_POLICY,
        # Not `totals["events"] == 0`: a corpus can carry health records of which none is a
        # failure, and that is still an empty health report rather than a populated one.
        "empty": not (hook_failures or episodes or runs),
        "totals": totals,
        "hook_failures": hook_failures,
        "retry_episodes": episodes,
        "abnormal_runs": runs,
        "kinds": _kind_ledger(events),
    }


def corpus_fingerprint(corpus: Path, spool: Path | None = None) -> dict:
    """A cheap snapshot of what the corpus and the spool look like right now.

    Deliberately not an ingest. Measured over this maintainer's corpus on 2026-08-29: a
    full incremental ingest costs 167 ms even when nothing changed, almost all of it 410
    per-transcript lookups against the store, while this walk and stat costs 38 ms. At a
    two-second poll that is the difference between burning eight percent of a core and one,
    for a watcher that exists to notice something that usually has not happened.

    Size and modification time together, because either alone misses a case: a rewritten
    transcript can keep its size, and a same-second append can keep its timestamp.
    """
    marks = {}
    try:
        for path in corpus.rglob("*.jsonl"):
            try:
                stat = path.stat()
            except OSError:
                continue                     # vanished between the walk and the stat
            marks[str(path)] = (stat.st_size, stat.st_mtime_ns)
    except OSError:
        pass                                 # no corpus is a normal state, not an error
    if spool is not None:
        try:
            stat = spool.stat()
            marks["\x00spool"] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            pass
    return marks


class LiveWatcher:
    """Notice appended records, fold them in, and tell every open report.

    Three properties are the reason this is shaped the way it is.

    **It runs only while somebody is watching.** The thread starts on the first subscriber
    and stops after the last one goes, so a server nobody has a page open against does no
    polling at all. A background loop that runs regardless is a cost with no reader.

    **It reuses the incremental read rather than adding a second mechanism.** The byte
    offset bookkeeping `feat-0053` built is what makes a re-read cost work proportional to
    what changed, and a watcher with its own idea of what is new would be a second source
    of truth about the same question.

    **An event is a hint to look, never a datum** (`EVENT_POLICY`). Both the corpus probe
    and the optional spool do the same thing: cause a re-read. Neither contributes a
    figure, which is how S-015's no-double-counting holds by construction rather than by
    a rule somebody has to remember.
    """

    def __init__(self, store: Path, corpus: Path, spool: Path | None = None,
                 poll_seconds: float = DEFAULT_POLL_SECONDS):
        self.store = Path(store)
        self.corpus = Path(corpus)
        self.spool = None if spool is None else Path(spool)
        self.poll_seconds = poll_seconds
        self._lock = threading.Lock()
        self._listeners: list = []
        self._thread = None
        self._stop = threading.Event()
        self._spool_offset = 0
        self._fingerprint = None

    # -- subscription -------------------------------------------------------------

    def subscribe(self) -> "queue.Queue":
        channel: queue.Queue = queue.Queue(maxsize=32)
        with self._lock:
            self._listeners.append(channel)
            start = self._thread is None or not self._thread.is_alive()
            if start:
                self._stop.clear()
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
        return channel

    def unsubscribe(self, channel) -> None:
        with self._lock:
            if channel in self._listeners:
                self._listeners.remove(channel)
            if not self._listeners:
                self._stop.set()

    def listeners(self) -> int:
        with self._lock:
            return len(self._listeners)

    def publish(self, event: dict) -> None:
        with self._lock:
            channels = list(self._listeners)
        for channel in channels:
            try:
                channel.put_nowait(event)
            except queue.Full:
                pass     # a page too slow to drain misses a nudge, not a figure

    # -- the loop -----------------------------------------------------------------

    def _drain_spool(self) -> list:
        """Every event appended to the spool since the last look.

        Tolerates a half-written final line the same way the corpus reader does, by
        consuming only up to the last newline, because the hook that writes here is
        running inside somebody else's session and may be mid-append.
        """
        if self.spool is None or not self.spool.exists():
            return []
        try:
            with self.spool.open("rb") as handle:
                handle.seek(self._spool_offset)
                buf = handle.read()
        except OSError:
            return []
        if not buf:
            return []
        cut = buf.rfind(b"\n")
        if cut < 0:
            return []
        self._spool_offset += cut + 1
        events = []
        for line in buf[:cut].splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except (json.JSONDecodeError, UnicodeDecodeError):
                events.append({"unreadable": True})
        return events

    def poll_once(self) -> dict | None:
        """One look. Returns the event published, or None when nothing changed."""
        spooled = self._drain_spool()
        marks = corpus_fingerprint(self.corpus, self.spool)
        first = self._fingerprint is None
        changed = not first and marks != self._fingerprint
        self._fingerprint = marks
        # The first look reads rather than only taking a baseline. A server started against
        # a store that has fallen behind should catch up when someone opens a page, not sit
        # on a stale figure until a session happens to write again.
        if not (first or changed or spooled):
            return None

        summary = {"transcripts": 0, "records": 0, "files_read": 0}
        try:
            summary = ingest.ingest(self.corpus, self.store)
        except db.StoreUnusable:
            return None                      # a store this code cannot read is not an event
        except OSError:
            return None

        # Nothing folded in and nothing spooled means nothing to say. An event per tick
        # would make an open page re-fetch forever and would tell its reader nothing.
        if not summary.get("records") and not spooled:
            return None

        event = {
            "type": "change",
            # Which source caused this look. S-015 asks for events to be attributed to the
            # source they arrived from, and there are exactly two.
            "source": "hook" if spooled else "corpus",
            "hook_events": len(spooled),
            "files_read": summary.get("files_read", 0),
            "records": summary.get("records", 0),
            "policy": EVENT_POLICY,
        }
        self.publish(event)
        return event

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:                # noqa: BLE001
                # A watcher that dies takes live updates with it and leaves the page
                # looking correct, so it survives anything the corpus throws at it.
                pass
            self._stop.wait(self.poll_seconds)


class ObservatoryServer(ThreadingHTTPServer):
    """The server, carrying the store path and the roster the handler answers from."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, store: Path, roster=None, quiet: bool = False,
                 family=socket.AF_INET, registry=None, corpus=None, spool=None,
                 poll_seconds: float = DEFAULT_POLL_SECONDS, pricing=None, quota=None):
        self.store = Path(store)
        self.roster = roster
        # Both are paths rather than loaded tables, and both are read per request. Editing the
        # rate table and pressing Refresh is the documented way to correct a stale rate, and a
        # table loaded once at startup would make that quietly not work.
        self.pricing = PRICING_PATH if pricing is None else Path(pricing)
        self.quota = None if quota is None else Path(quota)
        # Carried rather than read from the module defaults at the point of use, so a test
        # drives the fleet report against a registry and a corpus it controls.
        self.registry = ingest.DEFAULT_REGISTRY if registry is None else Path(registry)
        self.corpus = ingest.DEFAULT_CORPUS if corpus is None else Path(corpus)
        self.quiet = quiet
        # The spool defaults beside the store rather than inside the corpus, because the
        # corpus belongs to the harness and S-009 forbids adding a file to it.
        self.spool = (self.store.parent / SPOOL_NAME) if spool is None else Path(spool)
        self.watcher = LiveWatcher(self.store, self.corpus, self.spool, poll_seconds)
        # Read from the instance by `socketserver.TCPServer.__init__`, so it must be set
        # before the call. Set per instance rather than on the class, because ::1 and
        # 127.0.0.1 are both legal here and a class attribute would make the last caller win.
        self.address_family = family
        super().__init__(address, handler)


class ObservatoryHandler(BaseHTTPRequestHandler):
    """One GET-only handler. Every route reads; none of them writes anything, anywhere."""

    server_version = "observatory"
    sys_version = ""

    # -- plumbing ---------------------------------------------------------------------

    def log_message(self, fmt, *args):     # noqa: A003 (BaseHTTPRequestHandler's name)
        if not getattr(self.server, "quiet", False):
            super().log_message(fmt, *args)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The page is a view of a store that changes under it, so a cached answer is a wrong
        # answer rather than a stale nicety.
        self.send_header("Cache-Control", "no-store")
        # Defence in depth rather than a fix for anything live: the page uses no `innerHTML`
        # anywhere and `bug-0055` closed the one sink where a corpus value reached an
        # interpreted context. This is the layer that would have contained that defect
        # instead of letting it reach the network, on a surface serving one maintainer's
        # whole session history.
        #
        # `'unsafe-inline'` is required and is not an oversight. Every style and every line
        # of script in `ui/index.html` is inline, deliberately, because `S-022` forbids
        # fetching a subresource and the page must render with the network unavailable.
        # Extracting them would trade one contract property for another. Even with it,
        # `script-src` blocks a `javascript:` URI, which is the containment this is for.
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(status, json.dumps(payload, indent=1).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _refuse(self) -> None:
        """Anything that is not a GET or a HEAD. The surface is a report, so a method that
        exists to change something has no route here to decline politely."""
        self._json({"error": f"{self.command} is not served. This surface reads only."}, 405)

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    # -- routes -----------------------------------------------------------------------

    def do_GET(self) -> None:               # noqa: N802 (BaseHTTPRequestHandler's name)
        # Before routing, not after: a rebound request must not reach a report at all.
        if not host_is_loopback(self.headers.get("Host")):
            return self._json({
                "error": f"Host {self.headers.get('Host')!r} is not this machine's loopback "
                         f"interface. This surface answers only to a loopback name, because "
                         f"the Host header is attacker-controlled and what it would return "
                         f"is the whole session corpus."
            }, 403)
        parts = urlsplit(self.path)
        query = parse_qs(parts.query)
        project = (query.get("project") or [None])[0] or None
        route = parts.path

        if route in ("/", "/index.html"):
            return self._index()
        if route == "/api/reports":
            return self._json({"reports": list(REPORTS)})
        if route == "/api/meta":
            return self._with_store(lambda conn: {
                "store": str(self.server.store),
                "projects": scope_options(conn, self.server.registry, self.server.corpus),
                "roster_label": ROSTER_LABEL,
                "reports": list(REPORTS),
                "actions": list(ACTIONS),
                "action_kinds": list(ACTION_KINDS),
            })
        if route == "/api/skills":
            return self._with_store(
                lambda conn: skills_report(conn, project, self.server.roster))
        if route == "/api/fleet":
            return self._with_store(
                lambda conn: fleet_report(conn, project, self.server.registry,
                                          self.server.corpus))
        if route == "/api/waves":
            return self._with_store(lambda conn: waves_report(conn, project))
        if route == "/api/cost":
            return self._with_store(
                lambda conn: cost_report(conn, project,
                                         load_pricing(self.server.pricing),
                                         load_quota(self.server.quota)))
        if route == "/api/health":
            return self._with_store(lambda conn: health_report(conn, project))
        if route == "/api/events":
            return self._events()
        self._json({"error": f"no route for {route}"}, 404)

    do_HEAD = do_GET

    def _events(self) -> None:
        """The live channel: server-sent events, and no dependency on either side.

        `text/event-stream` is a handful of bytes on the wire and `EventSource` is built
        into every browser, so `S-013` costs no library here and none on the page. A
        WebSocket would need a handshake implementation for no gain: this direction is
        server to page and never the other way.

        A HEAD is answered with the headers and nothing else. Without that, `do_HEAD` is
        `do_GET` and a HEAD against this route would block a thread until the process ended.
        """
        watcher = self.server.watcher
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        if self.command == "HEAD":
            return

        channel = watcher.subscribe()
        try:
            self._write_event({"type": "open", "poll_seconds": watcher.poll_seconds,
                               "policy": EVENT_POLICY})
            last = time.monotonic()
            while True:
                try:
                    event = channel.get(timeout=1.0)
                except queue.Empty:
                    if time.monotonic() - last >= HEARTBEAT_SECONDS:
                        # A comment line. The client ignores it; the write is what tells
                        # us the client is gone.
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        last = time.monotonic()
                    continue
                self._write_event(event)
                last = time.monotonic()
        except (BrokenPipeError, ConnectionResetError, OSError, ValueError):
            pass                             # the page closed, which is the normal exit
        finally:
            watcher.unsubscribe(channel)

    def _write_event(self, event: dict) -> None:
        body = json.dumps(event)
        self.wfile.write(f"event: {event.get('type', 'message')}\n"
                         f"data: {body}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _index(self) -> None:
        try:
            body = INDEX.read_bytes()
        except OSError as exc:
            return self._json({"error": f"the page is missing: {exc}"}, 500)
        self._send(200, body, "text/html; charset=utf-8")

    def _with_store(self, build) -> None:
        """Answer from the store, saying plainly when there is not one yet.

        A missing store is not an error and not an empty report: it means the ingester has not
        run, which is a different thing from a corpus with nothing in it, and the page says
        which. Opening it here would create one as a side effect of a GET.
        """
        store = self.server.store
        if not store.exists():
            return self._json({
                "store": str(store), "store_present": False,
                "message": f"No store at {store}. Run scripts/observatory/ingest.py first.",
            })
        # Two failure classes, and only one of them used to be caught (`bug-0052`).
        # `StoreUnusable` is a `RuntimeError` this module raises on purpose and it carries a
        # readable remedy, so it keeps its own message. A `sqlite3.Error` is anything the
        # driver itself refuses: a locked database, a missing table, a corrupt file. That is
        # not a `StoreUnusable`, so it passed straight through the `except` below and left
        # `do_GET` returning with nothing written. The client got a dropped connection rather
        # than a status and a body, which reads as the server being down.
        try:
            conn = db.connect(store)
        except db.StoreUnusable as exc:
            return self._json({"store": str(store), "store_present": True,
                               "error": str(exc)}, 500)
        except sqlite3.Error as exc:
            return self._json({"store": str(store), "store_present": True,
                               "error": f"the store could not be opened: {exc}"}, 500)
        try:
            payload = build(conn)
        except sqlite3.Error as exc:
            # The same gap one call further in, and the one nobody has seen fail. A query can
            # fail for every reason a connect can, and the `finally` below closes the
            # connection without answering, so this site was silent in exactly the same way.
            return self._json({"store": str(store), "store_present": True,
                               "error": f"the report could not be built: {exc}"}, 500)
        finally:
            conn.close()
        payload.setdefault("store", str(store))
        payload["store_present"] = True
        self._json(payload)


def make_server(store: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                roster=None, quiet: bool = False, registry=None, corpus=None,
                spool=None,
                poll_seconds: float = DEFAULT_POLL_SECONDS,
                pricing=None, quota=None) -> ObservatoryServer:
    """Build the server, refusing a non-loopback address before anything is bound."""
    address = loopback_address(host)
    family = (socket.AF_INET6 if ipaddress.ip_address(address).version == 6
              else socket.AF_INET)
    return ObservatoryServer((address, port), ObservatoryHandler, store=store,
                             roster=roster, quiet=quiet, family=family,
                             registry=registry, corpus=corpus, spool=spool,
                             poll_seconds=poll_seconds, pricing=pricing, quota=quota)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the observatory store as one local page."
    )
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE,
                        help=f"store path (default: {DEFAULT_STORE})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"loopback address to bind (default: {DEFAULT_HOST}). "
                             f"A non-loopback address is refused.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port (default: {DEFAULT_PORT})")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY,
                        help=f"the harness's live-session registry, read to tell a running "
                             f"session from an ended one (default: {DEFAULT_REGISTRY})")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS,
                        help=f"corpus root, read only to place a live session the store has "
                             f"not seen yet (default: {DEFAULT_CORPUS})")
    parser.add_argument("--spool", type=Path, default=None,
                        help="the optional event source's spool file, appended to by the "
                             "observatory hook (default: events.jsonl beside the store)")
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS,
                        help=f"how often to look for appended records, and so the worst-case "
                             f"delay before an open report shows them "
                             f"(default: {DEFAULT_POLL_SECONDS})")
    parser.add_argument("--pricing", type=Path, default=PRICING_PATH,
                        help=f"the local rate table behind every cost estimate. Read from "
                             f"disk on every request and never fetched "
                             f"(default: {PRICING_PATH})")
    parser.add_argument("--quota", type=Path, default=None,
                        help="an optional quota sample series, JSON Lines. Absent is the "
                             "normal state and is not an error: pressure then reports its "
                             "context half only.")
    parser.add_argument("--quiet", action="store_true", help="suppress the request log")
    args = parser.parse_args(argv)

    try:
        server = make_server(args.store, args.host, args.port, quiet=args.quiet,
                             registry=args.registry, corpus=args.corpus,
                             spool=args.spool, poll_seconds=args.poll_seconds,
                             pricing=args.pricing, quota=args.quota)
    except NotLoopback as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR could not bind {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 2

    host, port = server.server_address[0], server.server_address[1]
    print(f"Observatory on http://{host}:{port}/ over {args.store}")
    print(f"Roster for never-used skills: {ROSTER_LABEL}")
    print(f"Live registry: {args.registry}")
    print(f"Following the corpus: an open report shows appended records within about "
          f"{args.poll_seconds:g}s, with or without the optional event source.")
    print(f"Optional event spool: {server.spool} "
          f"({'present' if server.spool.exists() else 'absent, which is not an error'})")
    print(f"Liveness check: {ingest.liveness_check()}")
    rates = load_pricing(args.pricing)
    print(f"Rate table: {rates['note']} Costs are estimates and are never fetched.")
    quota = load_quota(args.quota)
    print(f"Quota source: {quota['reason']}")
    if not Path(args.registry).is_dir():
        print("No live registry there, so every session is reported ended.")
    if not Path(args.store).exists():
        print(f"No store at {args.store} yet. Run scripts/observatory/ingest.py first.")
    print("Loopback only. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
