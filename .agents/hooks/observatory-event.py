#!/usr/bin/env python3
"""Reminder hook: tell a local observatory that this session just did something.

Appends one line to a spool file and injects nothing. It is the weakest form of the
reminder shape in `.agents/hooks/README.md`: it never blocks, never writes to stdout, and
never fails a session. If nothing is watching the spool, the line sits there unread and
costs a few bytes.

This is the optional event source of `docs/spec/agent-observatory.md` S-015, and it is
optional in the strong sense: the observatory follows the corpus on its own and this only
lowers the delay. A machine that never installs this hook loses no figure and sees no
error, which is S-014.

Why a file and not a socket
---------------------------
This is the one part of the observatory that runs inside somebody else's process, and the
rule that matters is that it cannot slow a coding session down. A file append cannot block
on a connect, cannot wait on a read timeout, and cannot hang because a server went away
mid-request. There is no server to be away: the observatory tails this file when it is
running and ignores it when it is not.

It also keeps the reporting surface's own boundary intact. A hook that posted would need a
route that accepts a POST, and every route there is a GET by contract.

What it does NOT do
-------------------
It carries no figure. The observatory derives every number from the corpus, so a line here
is a hint to look and never a datum, which is what makes double counting impossible rather
than merely avoided: an event describing work and the records describing the same work
cannot both be counted, because only one of them is ever counted at all.

Where the spool goes
--------------------
`OBSERVATORY_SPOOL` if set, otherwise `.observatory/events.jsonl` under the session's own
working directory, which is where that project's store lives. **Never inside the harness's
own directories**: S-009 requires that everything the harness owns is byte-for-byte
unchanged, and a hook that dropped a file into the transcript tree would break it from the
one place with permission to.

Standard library only, and it imports nothing from the repository that ships it, per the
contract in `.agents/hooks/README.md`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SPOOL_ENV = "OBSERVATORY_SPOOL"
SPOOL_RELATIVE = (".observatory", "events.jsonl")

# A spool nobody drains would grow without bound inside a live session, so it is capped.
# The observatory consumes what it reads, and the cap is the backstop for the case where
# nothing is watching: past it, the file is truncated rather than appended to. Losing an
# old hint costs nothing, because a hint is not a datum.
MAX_SPOOL_BYTES = 1_000_000


def spool_path(payload: dict, env=None) -> Path:
    """Where this event belongs.

    The session's own working directory, so a session in one project does not write into
    another's store. The payload carries `cwd`; the process's own is the fallback.
    """
    env = os.environ if env is None else env
    override = env.get(SPOOL_ENV)
    if override:
        return Path(override)
    base = payload.get("cwd") or "."
    return Path(base).joinpath(*SPOOL_RELATIVE)


def event_for(payload: dict) -> dict:
    """The line to append. Identifiers and a timestamp, and nothing about the work itself.

    No prompt, no response, no tool input. The observatory's contract excludes
    reconstructing conversation content, and a hook that spooled any would put it in a file
    the contract never described.
    """
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": "hook",
        "session_id": payload.get("session_id"),
        "event": payload.get("hook_event_name"),
        "cwd": payload.get("cwd"),
    }


def append(path: Path, event: dict) -> bool:
    """Append one line. Returns whether it landed; never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_SPOOL_BYTES:
            path.write_text("", encoding="utf-8", newline="\n")
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event) + "\n")
        return True
    except (OSError, ValueError, TypeError):
        return False


def main(stdin=None, stdout=None) -> int:
    """Read one payload, append one line, emit nothing, exit 0.

    `stdin`/`stdout` are injectable so the behavior is reachable from a test without
    spawning a subprocess, per the hooks module contract.

    Every failure path returns 0. A dashboard that can break a coding session is worse than
    no dashboard, and this hook has nothing to say that is worth a single interrupted run.
    """
    stdin = sys.stdin if stdin is None else stdin
    # Bound although nothing is written to it, which is the point: the module's other four
    # hooks bind it and write through it, and taking the parameter without binding it made
    # every assertion about this hook's silence unfalsifiable.
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.load(stdin)
    except Exception:                                        # noqa: BLE001
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        append(spool_path(payload), event_for(payload))
    except Exception:                                        # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
