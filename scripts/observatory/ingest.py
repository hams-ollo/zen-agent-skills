#!/usr/bin/env python3
"""Read the session corpus into the observatory store, incrementally and without touching it.

    python scripts/observatory/ingest.py [--corpus DIR] [--store PATH]

Exit codes, mirroring `run-checks.py` in separating "ran and produced nothing" from "ran and
produced something", because S-007 requires an empty corpus to be distinguishable rather than
merely worded differently:

    0  transcripts were found and ingested
    2  no transcripts were found; nothing was reported
    1  the run could not proceed (for example a store written by a newer schema)

Two properties are load-bearing and are the reason this file is shaped the way it is.

**Nothing the corpus owns is written to (S-009).** Transcripts are opened `"rb"` and never in a
mode that can create, truncate, or append. The store lives outside the corpus by default, so a
run cannot add a file to the harness's tree either.

**The byte offset advances only past records that fully parsed (S-006 with S-008).** The corpus
belongs to a program that may be writing to it right now, so the last line of an active
transcript is routinely half-written. Recording an offset past a partial line would mean the
rest of that record is never read once it completes: silent data loss that no test of a
finished transcript would ever catch. `scan_file` therefore stops at the last newline and
reports the fragment as unread rather than consuming it.

No network access at any point (S-022). This module imports nothing that can open a socket.
`ctypes` is the one import that could reach outside Python, and it is used for exactly one
thing: reading this machine's own process table, to decide whether a registered session's
process is still alive. See the live-session registry section near the bottom.

That section is the second source this file reads and the only one the store does not hold.
It is read at report time rather than ingested, because it answers a question about now:
`serve.py` calls `read_registry` and `process_state` per request, and nothing here writes a
row for it.

Contract: `docs/spec/agent-observatory.md`. Scenarios: S-005 to S-009, S-022, and the live
half of S-012.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):  # invoked as a script rather than imported
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.observatory import db
else:
    from . import db

DEFAULT_CORPUS = Path.home() / ".claude" / "projects"
DEFAULT_STORE = Path(".observatory") / "store.db"


class ScanResult:
    """What one pass over one transcript found."""

    __slots__ = ("records", "unreadable", "offset", "notes")

    def __init__(self) -> None:
        self.records: list[dict] = []
        self.unreadable = 0
        self.offset = 0
        self.notes: list[str] = []


def scan_file(path: Path, start_offset: int) -> ScanResult:
    """Parse records from `start_offset`, returning a safe offset to resume from.

    A line is a candidate only once it is newline-terminated. The trailing fragment of an
    actively-written transcript has no newline yet, so it is counted as unread and the returned
    offset stops before it. A terminated line that fails to parse is genuinely corrupt rather
    than incomplete, so it is counted and stepped over, because it will never parse.
    """
    result = ScanResult()
    result.offset = start_offset

    with path.open("rb") as fh:          # "rb" only: S-009 forbids any writing mode
        fh.seek(start_offset)
        buf = fh.read()

    if not buf:
        return result

    consumed = 0
    for raw in buf.splitlines(keepends=True):
        if not raw.endswith((b"\n", b"\r\n")):
            # Trailing fragment: a record still being written. Report it, do not consume it.
            result.unreadable += 1
            result.notes.append(
                f"{path}: {len(raw)} byte(s) at offset {start_offset + consumed} "
                f"are an incomplete final record, left for the next run"
            )
            break
        consumed += len(raw)
        text = raw.strip()
        if not text:
            continue
        try:
            result.records.append(json.loads(text))
        except (json.JSONDecodeError, UnicodeDecodeError):
            result.unreadable += 1
            result.notes.append(
                f"{path}: record at offset {start_offset + consumed - len(raw)} "
                f"is terminated but does not parse, skipped"
            )

    result.offset = start_offset + consumed
    return result


def _int(value):
    """Coerce a corpus scalar to int, or None. `exitCode` and `durationMs` arrive as strings on
    hook attachment records, so storing them raw would make every numeric comparison a string
    comparison and `exit_code > 0` silently wrong."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _usage(rec: dict) -> dict:
    u = (rec.get("message") or {}).get("usage") or {}
    details = u.get("output_tokens_details") or {}
    return {
        "input_tokens": u.get("input_tokens") or 0,
        "output_tokens": u.get("output_tokens") or 0,
        "cache_read_tokens": u.get("cache_read_input_tokens") or 0,
        "cache_creation_tokens": u.get("cache_creation_input_tokens") or 0,
        "thinking_tokens": details.get("thinking_tokens") or 0,
    }


def apply_record(conn, project: str, rec: dict) -> None:
    """Fold one parsed record into the store.

    S-005 is carried by the offset bookkeeping in `ingest`, not by this function; the conflict
    clauses here are the second line of defence for the paths where a record is legitimately
    re-read (a transcript replaced in place, or history replayed into a forked session).

    Writes to `message` are first-seen-wins rather than last-writer-wins. Iteration order over
    the corpus is sorted, so which copy wins is deterministic, and `message_occurrence` records
    every session the message was actually seen in. That split is deliberate: one canonical row
    per uuid keeps token totals from double-counting replayed history, and the occurrence table
    is what per-session and per-project figures must be built from.
    """
    rtype = rec.get("type")
    sid = rec.get("sessionId")
    if not sid:
        return

    ts = rec.get("timestamp")
    if rtype in ("assistant", "user", "attachment", "system"):
        conn.execute(
            """INSERT INTO session (session_id, project, cwd, git_branch, slug, version,
                                    entrypoint, first_ts, last_ts)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET
                 project    = COALESCE(excluded.project, session.project),
                 cwd        = COALESCE(excluded.cwd, session.cwd),
                 git_branch = COALESCE(excluded.git_branch, session.git_branch),
                 slug       = COALESCE(excluded.slug, session.slug),
                 version    = COALESCE(excluded.version, session.version),
                 entrypoint = COALESCE(excluded.entrypoint, session.entrypoint),
                 first_ts   = MIN(COALESCE(session.first_ts, excluded.first_ts),
                                  COALESCE(excluded.first_ts, session.first_ts)),
                 last_ts    = MAX(COALESCE(session.last_ts, excluded.last_ts),
                                  COALESCE(excluded.last_ts, session.last_ts))""",
            (sid, project, rec.get("cwd"), rec.get("gitBranch"), rec.get("slug"),
             rec.get("version"), rec.get("entrypoint"), ts, ts),
        )

    if rtype == "ai-title" and rec.get("aiTitle"):
        conn.execute(
            "INSERT INTO session (session_id, project, title) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET title = excluded.title",
            (sid, project, rec["aiTitle"]),
        )
    elif rtype == "custom-title" and rec.get("customTitle"):
        conn.execute(
            "INSERT INTO session (session_id, project, title) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET title = excluded.title",
            (sid, project, rec["customTitle"]),
        )
    elif rtype == "pr-link":
        conn.execute(
            "INSERT INTO session (session_id, project, pr_number, pr_url) VALUES (?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET pr_number = excluded.pr_number, "
            "pr_url = excluded.pr_url",
            (sid, project, rec.get("prNumber"), rec.get("prUrl")),
        )
    elif rtype == "system" and rec.get("subtype") == "api_error":
        conn.execute(
            "INSERT OR IGNORE INTO health_event "
            "(session_id, ts, kind, detail, exit_code, attempt, tool_use_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (sid, ts, "api_error", str(rec.get("error"))[:500], None,
             _int(rec.get("retryAttempt")), rec.get("toolUseID")),
        )
    elif rtype == "system" and rec.get("subtype") == "compact_boundary":
        # S-017 requires compaction occasions to be identifiable. Two records in this corpus,
        # and nothing else marks one.
        meta = rec.get("compactMetadata") or {}
        conn.execute(
            "INSERT OR IGNORE INTO health_event "
            "(session_id, ts, kind, detail, tool_use_id) VALUES (?,?,?,?,?)",
            (sid, ts, "compact_boundary", json.dumps(meta)[:500], rec.get("uuid")),
        )
    elif rtype == "system" and rec.get("subtype") == "stop_hook_summary":
        # Only the summaries that reported something are worth a row. A summary with no errors
        # and no prevented continuation is the normal case and would otherwise bury the signal.
        if rec.get("hookErrors") or rec.get("preventedContinuation"):
            conn.execute(
                "INSERT OR IGNORE INTO health_event "
                "(session_id, ts, kind, detail, tool_use_id, prevented_continuation) "
                "VALUES (?,?,?,?,?,?)",
                (sid, ts, "stop_hook_summary",
                 json.dumps(rec.get("hookErrors"))[:500], rec.get("toolUseID"),
                 1 if rec.get("preventedContinuation") else 0),
            )
    elif rtype == "attachment":
        att = rec.get("attachment") or {}
        atype = att.get("type") or ""
        if atype == "total_tokens_reminder":
            # The only context-budget series in the corpus. The count is embedded in the text
            # as `<total_tokens>N tokens left</total_tokens>`, so it is parsed here rather than
            # stored as prose a later report would have to re-parse. S-017 needs it.
            text = str((att.get("text") or att.get("content") or ""))
            match = re.search(r"<total_tokens>\s*(\d+)", text)
            if match:
                conn.execute(
                    "INSERT OR IGNORE INTO context_sample (session_id, ts, tokens_left) "
                    "VALUES (?,?,?)",
                    (sid, ts, int(match.group(1))),
                )
        elif atype.startswith("hook_"):
            # Hook outcomes live here, not on `system` records. This is where `exitCode`,
            # `command`, and `durationMs` come from, and reading only `system` left `exit_code`
            # NULL on every row of the store.
            conn.execute(
                "INSERT OR IGNORE INTO health_event "
                "(session_id, ts, kind, detail, exit_code, hook_name, hook_event, command, "
                " duration_ms, tool_use_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sid, ts, atype, str(att.get("stderr") or "")[:500],
                 _int(att.get("exitCode")), att.get("hookName"), att.get("hookEvent"),
                 att.get("command"), _int(att.get("durationMs")), att.get("toolUseID")),
            )

    if rtype == "assistant":
        u = _usage(rec)
        msg = rec.get("message") or {}
        conn.execute(
            "INSERT OR IGNORE INTO message_occurrence (uuid, session_id, project) "
            "VALUES (?,?,?)",
            (rec.get("uuid"), sid, project),
        )
        conn.execute(
            """INSERT INTO message
               (uuid, session_id, parent_uuid, type, ts, model, effort, is_sidechain,
                agent_id, attribution_agent,
                is_api_error, api_error_status, is_aborted_mid_stream, error,
                attribution_skill, attribution_plugin, attribution_mcp_server,
                attribution_mcp_tool, input_tokens, output_tokens, cache_read_tokens,
                cache_creation_tokens, thinking_tokens)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uuid) DO NOTHING""",
            (rec.get("uuid"), sid, rec.get("parentUuid"), rtype, ts, msg.get("model"),
             rec.get("effort"), 1 if rec.get("isSidechain") else 0,
             rec.get("agentId"), rec.get("attributionAgent"),
             1 if rec.get("isApiErrorMessage") else None, rec.get("apiErrorStatus"),
             1 if rec.get("isAbortedMidStream") else None,
             str(rec.get("error"))[:500] if rec.get("error") else None,
             rec.get("attributionSkill"), rec.get("attributionPlugin"),
             rec.get("attributionMcpServer"), rec.get("attributionMcpTool"),
             u["input_tokens"], u["output_tokens"], u["cache_read_tokens"],
             u["cache_creation_tokens"], u["thinking_tokens"]),
        )
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                inp = block.get("input") or {}
                conn.execute(
                    """INSERT OR REPLACE INTO tool_call
                       (tool_use_id, session_id, message_uuid, ts, name, skill_name,
                        subagent_type)
                       VALUES (?,?,?,?,?,?,?)""",
                    (block.get("id"), sid, rec.get("uuid"), ts, block.get("name"),
                     inp.get("skill"), inp.get("subagent_type")),
                )

    elif rtype == "user":
        tur = rec.get("toolUseResult")
        if isinstance(tur, dict) and tur.get("agentId"):
            # The dispatching tool_use id lives on the tool_result block, not in
            # `sourceToolUseID`. Established by counting: of 338 agent-result records in the
            # maintainer's corpus, 0 carry `sourceToolUseID` and 338 carry this block. Reading
            # the wrong key left `agent_run.tool_use_id` NULL on every row and made the join
            # that S-004 needs return nothing, which an independent verification of feat-0053
            # caught. Confirm against the corpus, never from memory.
            tool_use_id = None
            for block in (rec.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_use_id = block.get("tool_use_id")
                    break
            # COALESCE rather than REPLACE: the launch and completion records for one agent
            # carry disjoint fields, so a later record must not null what an earlier one gave.
            conn.execute(
                """INSERT INTO agent_run
                   (agent_id, session_id, tool_use_id, agent_type, resolved_model, status,
                    total_tokens, total_duration_ms, total_tool_use_count)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(agent_id) DO UPDATE SET
                     session_id     = COALESCE(excluded.session_id, agent_run.session_id),
                     tool_use_id    = COALESCE(excluded.tool_use_id, agent_run.tool_use_id),
                     agent_type     = COALESCE(excluded.agent_type, agent_run.agent_type),
                     resolved_model = COALESCE(excluded.resolved_model,
                                               agent_run.resolved_model),
                     status         = COALESCE(excluded.status, agent_run.status),
                     total_tokens   = COALESCE(excluded.total_tokens, agent_run.total_tokens),
                     total_duration_ms = COALESCE(excluded.total_duration_ms,
                                                  agent_run.total_duration_ms),
                     total_tool_use_count = COALESCE(excluded.total_tool_use_count,
                                                     agent_run.total_tool_use_count)""",
                (tur.get("agentId"), sid, tool_use_id, tur.get("agentType"),
                 tur.get("resolvedModel"), tur.get("status"), tur.get("totalTokens"),
                 tur.get("totalDurationMs"), tur.get("totalToolUseCount")),
            )


def apply_sidecars(conn, corpus: Path) -> int:
    """Fold every `agent-<id>.meta.json` sidecar into `agent_run`.

    These sit beside a subagent's transcript and are the only place the isolated workspace and
    branch are recorded; no transcript record carries either, and `S-004` requires both. They
    are small, static, and few, so they are re-read in full each run rather than tracked in
    `ingest_state`; the write is an upsert, so re-reading changes nothing.
    """
    count = 0
    for meta in sorted(corpus.rglob("agent-*.meta.json")):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        agent_id = meta.name[len("agent-"):-len(".meta.json")]
        # <project>/<sessionId>/subagents/agent-<id>.meta.json
        session_id = meta.parent.parent.name if meta.parent.name == "subagents" else None
        conn.execute(
            """INSERT INTO agent_run
                 (agent_id, session_id, tool_use_id, agent_type, description,
                  worktree_path, worktree_branch, spawn_depth)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(agent_id) DO UPDATE SET
                 session_id     = COALESCE(agent_run.session_id, excluded.session_id),
                 tool_use_id    = COALESCE(agent_run.tool_use_id, excluded.tool_use_id),
                 agent_type     = COALESCE(agent_run.agent_type, excluded.agent_type),
                 description    = COALESCE(excluded.description, agent_run.description),
                 worktree_path  = COALESCE(excluded.worktree_path, agent_run.worktree_path),
                 worktree_branch= COALESCE(excluded.worktree_branch,
                                           agent_run.worktree_branch),
                 spawn_depth    = COALESCE(excluded.spawn_depth, agent_run.spawn_depth)""",
            (agent_id, session_id, data.get("toolUseId"), data.get("agentType"),
             data.get("description"), data.get("worktreePath"), data.get("worktreeBranch"),
             _int(data.get("spawnDepth"))),
        )
        count += 1
    return count


def transcripts(corpus: Path) -> list[Path]:
    """Every transcript under the corpus, sorted for a stable run order."""
    if not corpus.exists():
        return []
    return sorted(p for p in corpus.rglob("*.jsonl") if p.is_file())


def ingest(corpus: Path, store: Path) -> dict:
    """Ingest everything appended since the last run. Returns a summary of what happened."""
    files = transcripts(corpus)
    summary = {
        "transcripts": len(files),
        "files_read": 0,
        "records": 0,
        "unreadable": 0,
        "notes": [],
        "bytes_read": 0,
        "sidecars": 0,
    }
    if not files:
        return summary

    conn = db.connect(store)
    try:
        for path in files:
            stat = path.stat()
            # Identity is the resolved, case-normalised path, not how the caller spelled it.
            # Keying on the literal string makes S-006 spelling-dependent: the same corpus
            # reached by a relative path, or by a differently-cased one on Windows, gets a
            # second `ingest_state` row and is re-read from byte zero. On this corpus that is
            # a 400 MB re-read reported as an incremental run.
            key = os.path.normcase(str(path.resolve()))
            row = conn.execute(
                "SELECT offset, size, mtime_ns FROM ingest_state WHERE path = ?", (key,)
            ).fetchone()
            start = row["offset"] if row else 0
            # A transcript that shrank was replaced rather than appended to, so a recorded
            # offset into the old contents means nothing. Start over rather than reading from
            # the middle of a different file.
            if stat.st_size < start:
                start = 0
            # A replacement of the same byte count leaves the size nothing to disagree with,
            # so the modification marker is the only recorded field that moves. Same reasoning
            # as the shrink above, and the same answer: the offset points into content that is
            # no longer there, so start over (`bug-0059`).
            if row and stat.st_size == row["size"] and stat.st_mtime_ns != row["mtime_ns"]:
                start = 0
            if (row and stat.st_size == row["size"] and stat.st_mtime_ns == row["mtime_ns"]
                    and start == stat.st_size):
                continue  # unchanged since last run: S-005's cheap path

            result = scan_file(path, start)
            project = path.parent.name if path.parent != corpus else path.stem
            if path.parent.parent != corpus and path.parent.name == "subagents":
                project = path.parent.parent.parent.name

            for rec in result.records:
                apply_record(conn, project, rec)

            conn.execute(
                """INSERT INTO ingest_state
                     (path, size, mtime_ns, offset, records, unreadable, updated_at)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(path) DO UPDATE SET
                     size=excluded.size, mtime_ns=excluded.mtime_ns, offset=excluded.offset,
                     records=ingest_state.records + excluded.records,
                     unreadable=excluded.unreadable, updated_at=excluded.updated_at""",
                (key, stat.st_size, stat.st_mtime_ns, result.offset, len(result.records),
                 result.unreadable, datetime.now(timezone.utc).isoformat()),
            )
            summary["files_read"] += 1
            summary["records"] += len(result.records)
            summary["unreadable"] += result.unreadable
            summary["bytes_read"] += result.offset - start
            summary["notes"].extend(result.notes)
        summary["sidecars"] = apply_sidecars(conn, corpus)
        conn.commit()
    finally:
        conn.close()
    return summary


# ---------------------------------------------------------------------------------------
# The live-session registry
#
# S-012 needs a real liveness source. A session whose last record is recent is not thereby
# running, and one idle for an hour may still be, so nothing below infers liveness from a
# timestamp. The harness keeps its own registry at `~/.claude/sessions/<pid>.json`, one file
# per running session. Confirmed on 2026-08-28: three entries against exactly three running
# `claude-code` processes, the other fifteen `claude.exe` processes on that machine being the
# desktop app's Electron helpers rather than sessions.
#
# Nothing here writes. The registry belongs to the harness (S-009), so every file is opened
# for reading and the directory is never created.
# ---------------------------------------------------------------------------------------

DEFAULT_REGISTRY = Path.home() / ".claude" / "sessions"

# What a process lookup concluded. Deliberately not the report's own vocabulary (`running`,
# `ended`, `unverified`): this layer answers a question about a pid, and the mapping from
# that to a session's state belongs to the report.
ALIVE = "alive"
GONE = "gone"
UNKNOWN = "unknown"

# Windows. `PROCESS_QUERY_LIMITED_INFORMATION` is the least privilege that can read a
# process's creation time and exit code, and it succeeds against processes a fuller access
# mask is refused for.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_ERROR_INVALID_PARAMETER = 87
_ERROR_ACCESS_DENIED = 5

_POSIX_PLATFORMS = ("linux", "darwin", "freebsd", "openbsd", "netbsd", "aix", "sunos",
                    "cygwin")


class _FileTime(ctypes.Structure):
    """A Windows FILETIME, defined here rather than imported from `ctypes.wintypes`.

    Importing `ctypes.wintypes` raises on a non-Windows build, which would make this module
    unimportable on two of the three platforms the conventions section of `AGENTS.md`
    requires. A plain `Structure` is definable everywhere and is used only on Windows.
    """

    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

    @property
    def value(self) -> int:
        return (self.high << 32) | self.low


def read_registry(registry_dir=DEFAULT_REGISTRY) -> dict:
    """Every entry in the harness's live-session registry, and what could not be read.

    An absent directory is a normal answer rather than an error: a machine with no session
    running has no registry, and the report must still render. An entry that does not parse,
    or that carries no `sessionId`, is counted and named rather than dropped, which is the
    habit S-008 fixes for the corpus applied to this second source.

    The directory also holds `<pid>.<hash>.key` files. They are not entries and are not read.
    """
    registry_dir = Path(registry_dir)
    result = {"path": str(registry_dir), "present": registry_dir.is_dir(),
              "entries": [], "unreadable": 0, "notes": []}
    if not result["present"]:
        return result

    for path in sorted(registry_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            result["unreadable"] += 1
            result["notes"].append(
                f"{path.name}: could not be read ({exc.__class__.__name__})")
            continue
        if not isinstance(entry, dict) or not entry.get("sessionId"):
            result["unreadable"] += 1
            result["notes"].append(
                f"{path.name}: carries no sessionId, so it names no session")
            continue
        result["entries"].append(entry)
    return result


def _posix_process_state(pid: int):
    """Whether `pid` exists, against a POSIX process table.

    Presence only. `procStart`'s meaning outside Windows is unverified here, so a pid the
    operating system has since handed to a different program reads as alive. The report says
    which check it ran rather than implying the stronger one everywhere.
    """
    if os.name != "posix":
        return UNKNOWN, "this build has no POSIX process table to query"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return GONE, f"no process {pid} exists"
    except PermissionError:
        return ALIVE, f"process {pid} exists and belongs to another user"
    except OSError as exc:
        return UNKNOWN, f"process {pid} could not be queried: {exc}"
    return ALIVE, f"process {pid} exists"


def _windows_process_state(pid: int, proc_start=None):
    """Whether `pid` is still the process the entry recorded, on Windows.

    Presence always, and identity wherever the entry records a start time: the pid must
    exist, and where `procStart` is present its creation time must equal it, so a pid the
    operating system has reused is reported gone. **An entry carrying no `procStart` is
    therefore confirmed on presence alone**, which is the weaker claim and is why
    `liveness_check` says so rather than advertising identity unconditionally. Confirmed
    on 2026-08-28 that `procStart` is the creation FILETIME: `134324400435518083` is
    1787966443.6 epoch seconds, 3.7 seconds before that entry's own `startedAt` and equal to
    the process's start time as the operating system reports it.

    **`os.kill(pid, 0)` is never used here.** On Windows, CPython's `os.kill` calls
    `TerminateProcess` for every signal that is not a console control event, so the POSIX
    idiom for "does this pid exist" would kill the session it was asked about.
    """
    windll = getattr(ctypes, "windll", None)
    if windll is None or os.name != "nt":
        return UNKNOWN, "this build has no Windows process API to query"

    kernel32 = windll.kernel32
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)

    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        code = kernel32.GetLastError()
        if code == _ERROR_INVALID_PARAMETER:
            return GONE, f"no process {pid} exists"
        if code == _ERROR_ACCESS_DENIED:
            return UNKNOWN, f"process {pid} exists but could not be opened for querying"
        return UNKNOWN, f"process {pid} could not be opened (Windows error {code})"

    try:
        exit_code = ctypes.c_uint32()
        if not kernel32.GetExitCodeProcess(ctypes.c_void_p(handle),
                                           ctypes.byref(exit_code)):
            return UNKNOWN, f"process {pid} exists but its exit code could not be read"
        if exit_code.value != _STILL_ACTIVE:
            return GONE, f"process {pid} has exited"

        recorded = _int(proc_start)
        if recorded is None:
            return ALIVE, (f"process {pid} is running; the entry records no comparable "
                           f"start time, so the pid was not matched to it")

        created, exited = _FileTime(), _FileTime()
        kernel_time, user_time = _FileTime(), _FileTime()
        if not kernel32.GetProcessTimes(ctypes.c_void_p(handle), ctypes.byref(created),
                                        ctypes.byref(exited), ctypes.byref(kernel_time),
                                        ctypes.byref(user_time)):
            return UNKNOWN, f"process {pid} is running but its start time could not be read"
        if created.value != recorded:
            return GONE, (f"process {pid} exists but started at {created.value}, not the "
                          f"entry's {recorded}: the pid was reused")
        return ALIVE, f"process {pid} is running and its start time matches the entry"
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def process_state(pid, proc_start=None, pid_domain=None, platform=None):
    """`(state, evidence)` for one registry entry's process. Never raises.

    `platform` is a parameter rather than a read of `sys.platform` so a test can drive every
    branch from any operating system. Each branch refuses to act on a process table it is not
    running against, so driving the Windows branch from Linux reports `unknown` rather than
    reaching for an API that is not there, and driving the POSIX branch from Windows reports
    `unknown` rather than reaching `os.kill`, which on Windows terminates the process.
    """
    platform = sys.platform if platform is None else platform
    pid = _int(pid)
    if pid is None or pid <= 0:
        return UNKNOWN, "the entry records no usable pid"

    # `pidDomain` is `<platform>:<host>`, so an entry written by another machine names a pid
    # in a table this one cannot query. Open Question 3 of the contract scopes the whole
    # thing to one machine; this refuses to read a foreign pid as a local one.
    if pid_domain:
        domain = str(pid_domain).split(":", 1)[0]
        if domain and domain != platform:
            return UNKNOWN, (f"the entry's pid domain {domain!r} is not this machine's "
                             f"{platform!r}, so its pid names no process here")

    if platform == "win32":
        return _windows_process_state(pid, proc_start)
    if platform.startswith(_POSIX_PLATFORMS):
        return _posix_process_state(pid)
    return UNKNOWN, f"no process check is defined for {platform!r}"


def liveness_check(platform=None) -> str:
    """What `process_state` can actually establish on this build, in one phrase.

    Served to the page and printed by both entry points, so the surface says which check it
    ran rather than leaving a reader to assume the strong one. It is derived by asking
    `process_state` about this process rather than by restating the dispatch, so a platform
    whose branch cannot run says so instead of advertising a check it will not perform.
    """
    platform = sys.platform if platform is None else platform
    state, _ = process_state(os.getpid(), proc_start=None, pid_domain=None,
                             platform=platform)
    if state != ALIVE:
        return "none: this build cannot query the process table, so no entry is confirmed"
    if platform == "win32":
        return ("process presence, plus identity wherever the entry records a start "
                "time: a reused pid is caught only in that case")
    return "process presence: the pid exists, so a reused pid would read as running"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest the Claude Code session corpus into the observatory store."
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS,
                        help=f"corpus root (default: {DEFAULT_CORPUS})")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE,
                        help=f"store path (default: {DEFAULT_STORE})")
    parser.add_argument("--quiet", action="store_true", help="suppress the per-run summary")
    args = parser.parse_args(argv)

    try:
        summary = ingest(args.corpus, args.store)
    except db.StoreUnusable as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if summary["transcripts"] == 0:
        # S-007: distinguishable by exit code, not merely by wording. A caller that only reads
        # the exit status must still be able to tell this from a run that reported figures.
        if not args.quiet:
            print(f"No transcripts found under {args.corpus}. Nothing ingested.")
        return 2

    if not args.quiet:
        print(f"{summary['transcripts']} transcript(s) found, "
              f"{summary['files_read']} with new content.")
        print(f"{summary['records']} record(s) ingested, "
              f"{summary['bytes_read']} byte(s) read.")
        print(f"{summary['sidecars']} subagent sidecar(s) read.")
        if summary["unreadable"]:
            print(f"{summary['unreadable']} record(s) could not be read:")
            for note in summary["notes"]:
                print(f"  {note}")
        else:
            print("0 record(s) unreadable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
