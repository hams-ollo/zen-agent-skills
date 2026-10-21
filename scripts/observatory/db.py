#!/usr/bin/env python3
"""The observatory's store: schema, forward-only migrations, and the connection helper.

The store is derived data. Its authoritative source is the session corpus on disk, so it is
always safe to delete and rebuild, and it is gitignored for that reason. Nothing here reads
the corpus; `ingest.py` does that and calls in here to write.

Standard library only, per the conventions section of `AGENTS.md`. `sqlite3` ships with
CPython, so this adds no dependency and needs no install step on any CI cell.

Schema shape is deliberately wider than the six scenarios `feat-0053` covers. The task states
the reason: later reports must be buildable "without a second ingest pass", so a column that
S-005 to S-009 and S-022 never read is still cheaper than a migration through work already
built on the store.

Contract: `docs/spec/agent-observatory.md`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Bumped only when the shape below changes. Migrations are forward-only: a store written by a
# newer version than this one is refused rather than misread, because silently reading a shape
# you do not understand produces wrong figures instead of an error.
SCHEMA_VERSION = 4

# How long a write path waits for the lock before giving up. Reached only by a fresh store or
# a forward migration since `bug-0051`: an open that merely reads takes no write lock at all,
# so the common case never waits and this bound never applies to it.
CONNECT_TIMEOUT_SECONDS = 30.0

# Every table holding derived corpus data. A version bump drops and re-derives all of them
# rather than backfilling: the corpus is authoritative and re-reading it costs seconds, while a
# partial backfill leaves rows that predate a column and are indistinguishable from rows where
# the corpus genuinely had nothing. `schema_meta` is excluded because it survives the rebuild.
DERIVED_TABLES = (
    "ingest_state", "message_occurrence", "message", "tool_call", "agent_run",
    "health_event", "session", "context_sample",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- The bookkeeping that makes S-005 (re-running changes nothing) and S-006 (only appended
-- records are read) true. `offset` is a byte offset into the transcript and is the load-bearing
-- column: it advances only past records that fully parsed, so a half-written final line is
-- re-read next run rather than skipped. See ingest.scan_file.
CREATE TABLE IF NOT EXISTS ingest_state (
    path          TEXT PRIMARY KEY,
    size          INTEGER NOT NULL,
    mtime_ns      INTEGER NOT NULL,
    offset        INTEGER NOT NULL,
    records       INTEGER NOT NULL DEFAULT 0,
    unreadable    INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS session (
    session_id  TEXT PRIMARY KEY,
    project     TEXT,
    cwd         TEXT,
    git_branch  TEXT,
    title       TEXT,
    slug        TEXT,
    version     TEXT,
    entrypoint  TEXT,
    first_ts    TEXT,
    last_ts     TEXT,
    pr_number   INTEGER,
    pr_url      TEXT
);

CREATE TABLE IF NOT EXISTS message (
    uuid                  TEXT PRIMARY KEY,
    session_id            TEXT,
    parent_uuid           TEXT,
    type                  TEXT,
    ts                    TEXT,
    model                 TEXT,
    effort                TEXT,
    is_sidechain          INTEGER,
    -- Subagent transcripts reuse the parent's sessionId, so without these two a subagent's
    -- 16,000-plus messages are indistinguishable from the parent session's own and no
    -- per-agent token figure can be derived. S-003 needs them.
    agent_id              TEXT,
    attribution_agent     TEXT,
    -- S-016's third part, "a run that ended abnormally". These sit on assistant records and
    -- have no other home in the corpus, so without them the health report can name hook
    -- failures and API retries but not a run that died.
    is_api_error          INTEGER,
    api_error_status      TEXT,
    is_aborted_mid_stream INTEGER,
    error                 TEXT,
    attribution_skill     TEXT,
    attribution_plugin    TEXT,
    attribution_mcp_server TEXT,
    attribution_mcp_tool  TEXT,
    input_tokens          INTEGER NOT NULL DEFAULT 0,
    output_tokens         INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    thinking_tokens       INTEGER NOT NULL DEFAULT 0
);

-- Every session a message was observed in. A forked or resumed session replays earlier history
-- verbatim into a new transcript, so one message legitimately appears under more than one
-- sessionId: 5,442 of them in this maintainer's corpus as of 2026-08-28. `message` holds one
-- canonical row per uuid, which keeps token totals honest, and this table holds the truth about
-- where it was seen, which is what per-session and per-project figures must be built from.
-- Collapsing both questions into one table is the defect an independent verification of
-- feat-0053 caught: totals were right and attribution was arbitrary.
CREATE TABLE IF NOT EXISTS message_occurrence (
    uuid       TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project    TEXT,
    PRIMARY KEY (uuid, session_id)
);

-- The only context-budget series the corpus carries: one `total_tokens_reminder` attachment
-- per turn, holding the remaining token count. S-017 asks for pressure "as series over time"
-- and this is the only source for it, so dropping these would force a second ingest pass over
-- 400 MB, which this task's Risks section exists to prevent.
CREATE TABLE IF NOT EXISTS context_sample (
    session_id  TEXT NOT NULL,
    ts          TEXT NOT NULL,
    tokens_left INTEGER,
    PRIMARY KEY (session_id, ts)
);

CREATE TABLE IF NOT EXISTS tool_call (
    tool_use_id  TEXT PRIMARY KEY,
    session_id   TEXT,
    message_uuid TEXT,
    ts           TEXT,
    name         TEXT,
    skill_name   TEXT,
    subagent_type TEXT
);

CREATE TABLE IF NOT EXISTS agent_run (
    agent_id            TEXT PRIMARY KEY,
    session_id          TEXT,
    tool_use_id         TEXT,
    agent_type          TEXT,
    resolved_model      TEXT,
    status              TEXT,
    total_tokens        INTEGER,
    total_duration_ms   INTEGER,
    total_tool_use_count INTEGER,
    -- From the `agent-<id>.meta.json` sidecar beside each subagent transcript, not from the
    -- transcript itself. S-004 requires each wave member to carry "the workspace and branch it
    -- was given", and nothing in the transcript records carries either.
    description         TEXT,
    worktree_path       TEXT,
    worktree_branch     TEXT,
    spawn_depth         INTEGER
);

-- Hook outcomes and API errors. Hook outcomes arrive on `attachment` records rather than
-- `system` ones, and their `exitCode` and `durationMs` are strings in the corpus, so both are
-- coerced on the way in. S-016 requires "a hook's exit status", which is why `exit_code` exists
-- at all; reading only `system` records left it NULL on every row.
CREATE TABLE IF NOT EXISTS health_event (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT,
    ts           TEXT,
    kind         TEXT,
    detail       TEXT,
    exit_code    INTEGER,
    attempt      INTEGER,
    hook_name    TEXT,
    hook_event   TEXT,
    command      TEXT,
    duration_ms  INTEGER,
    tool_use_id  TEXT,
    prevented_continuation INTEGER,
    UNIQUE (session_id, ts, kind, detail, tool_use_id)
);

CREATE INDEX IF NOT EXISTS idx_message_session ON message (session_id);
CREATE INDEX IF NOT EXISTS idx_occurrence_session ON message_occurrence (session_id);
CREATE INDEX IF NOT EXISTS idx_message_agent ON message (agent_id);
CREATE INDEX IF NOT EXISTS idx_context_session ON context_sample (session_id);
CREATE INDEX IF NOT EXISTS idx_message_skill   ON message (attribution_skill);
CREATE INDEX IF NOT EXISTS idx_tool_session    ON tool_call (session_id);
CREATE INDEX IF NOT EXISTS idx_agent_session   ON agent_run (session_id);
CREATE INDEX IF NOT EXISTS idx_health_session  ON health_event (session_id);
"""


class StoreUnusable(RuntimeError):
    """The store cannot be read safely. Callers turn this into "could not run", never into a
    silent empty result: a store this code does not understand yields wrong figures rather than
    an error if it is read anyway."""


class SchemaTooNew(StoreUnusable):
    """The store was written by a newer version of this package than the one reading it."""


class SchemaUnreadable(StoreUnusable):
    """The store's recorded version is not a version. A hand-edited or corrupted store reaches
    here, and it must exit as "could not run" rather than as an uncaught traceback."""


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if absent) the store at `path`, and bring its schema up to date.

    Raises `SchemaTooNew` when the store records a version this code does not know. Refusing
    is deliberate: a newer store may hold a shape whose columns mean something different, and
    reading it anyway produces plausible wrong numbers rather than a failure anyone notices.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # An explicit timeout, for the two occasions below that genuinely need the write lock: a
    # fresh store and a forward migration. The driver's default is five seconds, which is
    # short for a migration running beside an ingest of a real corpus.
    #
    # **This is the aggravating condition, not the cause**, and the distinction cost a whole
    # investigation to establish (`feat-0062`). That run first blamed the missing timeout on
    # an A/B where raising it inverted the outcome, which is consistent with the hypothesis
    # and does not test it: raising a timeout ends any wait, whatever is waiting. Converting
    # the store to WAL and changing nothing else failed identically, while guarding the
    # `schema_meta` upsert below fixed it at baseline speed. So the guard is the fix and this
    # is insurance, and saying which is which here is the point.
    conn = sqlite3.connect(str(path), timeout=CONNECT_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row

    # The version check runs before the schema script, because a stale store's tables have to be
    # dropped rather than left for `CREATE TABLE IF NOT EXISTS` to skip. Skipping is what makes a
    # schema change silently invisible: the table survives without its new columns.
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta ("
                 "key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        found = None
    else:
        try:
            found = int(row["value"])
        except (TypeError, ValueError):
            conn.close()
            raise SchemaUnreadable(
                f"store at {path} records schema version {row['value']!r}, which is not a "
                f"version. Delete the store and re-ingest."
            ) from None

    if found is not None and found > SCHEMA_VERSION:
        conn.close()
        raise SchemaTooNew(
            f"store at {path} records schema version {found}; this code knows "
            f"{SCHEMA_VERSION}. Delete the store and re-ingest, or use a newer version."
        )

    if found is not None and found < SCHEMA_VERSION:
        # Forward-only, by rebuild rather than by backfill. Every table below is derived from a
        # corpus that is still on disk, and re-reading it takes seconds. A backfill would leave
        # rows that predate a column holding NULL, which is indistinguishable from a row where
        # the corpus genuinely carried nothing, and that ambiguity outlives the migration.
        for table in DERIVED_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")

    conn.executescript(SCHEMA)
    if found != SCHEMA_VERSION:
        # Only when it would change something (`bug-0051`). This upsert ran on **every** open
        # and committed, so every read-only HTTP route took the write lock and contended with
        # any concurrent ingester, then gave up with `database is locked`.
        #
        # The guard is exactly this statement and nothing else, because measuring said so.
        # With a writer holding the lock: the `SELECT` above returns, the `CREATE TABLE IF
        # NOT EXISTS` returns, `executescript(SCHEMA)` returns, and only this upsert blocks.
        # So the schema script stays unguarded and keeps recreating a table somebody deleted,
        # which is a real safety property this fix had no need to trade away.
        #
        # `found` is None for a fresh store and lower for a migration, and both write here
        # and should: those are the two occasions the row is genuinely wrong.
        conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
    return conn
