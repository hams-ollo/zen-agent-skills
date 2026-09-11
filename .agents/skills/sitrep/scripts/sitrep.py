#!/usr/bin/env python3
"""sitrep: a board for one repository, generated from its own tracked records.

    python sitrep.py

The behavioural contract is `docs/spec/sitrep.md` in the Zen Agent Skills repository. This file
implements it one task at a time, in the order that spec's readiness record sets: `feat-0066`
builds what waits on the person and what is blocked, and the tasks after it add in-flight work,
evidence tiers, the watermark, the renderings, and the session-start hook. Sections owed to a later
task are present in the board with an empty value, so the board's shape never changes under a
reader.

Standard library only, so it runs on a bare Python 3 wherever the skill is installed.

Three properties are load-bearing and shape everything below.

**Only tracked records are state.** Task files are found with `git ls-files`, never with a
directory listing, because an untracked file on one machine is not part of the repository. The
hts-app prototype this replaces met a simulator output in an untracked folder that reported 70
where a fresh run reported 74, and it looked exactly as authoritative as everything else.

**A decision answers only the questions above it.** A task routinely carries an answered
`## Decision` from one round and a new `## Open question` raised after it. Asking whether both
headings exist anywhere marked such a task answered and dropped the only P1 from the prototype's
queue, so the rule here is positional: the task waits while its last open question has no decision
below it.

**Nothing in the repository changes.** Every git call runs with optional locks off, so not even
`git status` refreshes the index behind the person's back.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = 1

# The evidence ladder, lowest first. The names are the spec's Proposed Surface, and the rules
# module that restates them for agents uses the same ones.
TIERS = ("white", "green", "blue", "purple", "gold")
TIER_NAMES = {tier: tier.capitalize() for tier in TIERS}

TASK_PATH_RE = re.compile(r"^\.tasks/(?:done/)?([a-z]+-\d{4})-[^/]+\.md$")
TASK_ID_RE = re.compile(r"\b[a-z]+-\d{4}\b")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
LIST_ITEM_RE = re.compile(r"^[ \t]+-[ \t]*(.*)$")

# A level-two heading whose text begins with these words. Matched in any letter case: a missed
# row on the person's queue is the worst failure this board can have, and a repository that
# writes "## Open Question" should not lose one for its capitalisation.
OPEN_QUESTION_RE = re.compile(r"^##[ \t]+open question", re.M | re.I)
DECISION_RE = re.compile(r"^##[ \t]+decision", re.M | re.I)
# Any heading, at any level, carrying the phrase bug-0126 in hts-app already used.
HUMAN_EYE_RE = re.compile(r"^#{1,6}[ \t]+.*held open for a human eye", re.M | re.I)
PRIORITY_RE = re.compile(r"^P(\d+)$", re.I)

NOTICE_NO_TASKS = "no task tracking"
REASON_OPEN_QUESTION = "open question"
REASON_HUMAN_EYE = "needs a human eye"


class SitrepError(Exception):
    """The board could not be produced, with a reason a person can act on."""


# ---------------------------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------------------------

def _git_env():
    env = dict(os.environ)
    # Without this, `git status` takes the index lock and rewrites its stat cache, which is a
    # change to the repository made by a tool that promises to make none.
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def git(repo, *args):
    """Run git in `repo` and return its stdout, or raise SitrepError naming what failed."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=_git_env(),
        )
    except FileNotFoundError:
        raise SitrepError("git is not installed or is not on PATH") from None
    if proc.returncode != 0:
        detail = proc.stderr.strip() or f"exit {proc.returncode}"
        raise SitrepError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def git_quiet(repo, *args):
    """Like `git`, but None instead of an error, for facts that may legitimately be absent."""
    try:
        return git(repo, *args)
    except SitrepError:
        return None


def repository_facts(repo):
    """The repository's top-level path, its origin URL if any, and the revision at HEAD."""
    top = git(repo, "rev-parse", "--show-toplevel").strip()
    origin = (git_quiet(top, "remote", "get-url", "origin") or "").strip() or None
    revision = (git_quiet(top, "rev-parse", "HEAD") or "").strip() or None
    return {"path": top, "origin": origin}, revision


# ---------------------------------------------------------------------------------------------
# Task files
# ---------------------------------------------------------------------------------------------

def parse_frontmatter(text):
    """Flat `key: value` fields and `- item` lists, by regex rather than a YAML parser.

    The same call `.tasks/validate.py` makes: the fields a task file carries are scalars and one
    list, which this reads correctly in both the inline `[a, b]` and the block form.
    Returns (fields, body).
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fields, current = {}, None
    for line in match.group(1).splitlines():
        field = FIELD_RE.match(line)
        if field:
            current = field.group(1)
            fields[current] = field.group(2).strip()
            continue
        item = LIST_ITEM_RE.match(line)
        if item and current is not None:
            fields[current] = (fields[current] + " " + item.group(1)).strip()
    return fields, text[match.end():]


def waiting_reasons(body):
    """Why a task's body puts it on the person's queue, in the order the spec lists them.

    Positional: an open question counts as answered only when a decision heading follows it, so
    the task waits while its last open question has no decision heading anywhere below it.
    """
    reasons = []
    last_question = max((m.start() for m in OPEN_QUESTION_RE.finditer(body)), default=-1)
    last_decision = max((m.start() for m in DECISION_RE.finditer(body)), default=-1)
    if last_question >= 0 and last_decision < last_question:
        reasons.append(REASON_OPEN_QUESTION)
    if HUMAN_EYE_RE.search(body):
        reasons.append(REASON_HUMAN_EYE)
    return reasons


def parse_task(rel, text):
    """One task file as the board needs it: identity, priority, dependencies, and its reasons."""
    fields, body = parse_frontmatter(text)

    def scalar(name):
        return fields.get(name, "").strip().strip("'\"")

    path_match = TASK_PATH_RE.match(rel)
    task_id = scalar("id") or (path_match.group(1) if path_match else rel)
    return {
        "id": task_id,
        "title": scalar("title") or task_id,
        "priority": scalar("priority") or "",
        "depends_on": TASK_ID_RE.findall(fields.get("depends_on", "")),
        "file": rel,
        "closed": rel.startswith(".tasks/done/"),
        "reasons": waiting_reasons(body),
    }


def load_tasks(top):
    """Every tracked task file, parsed, plus any notice the reading raised.

    A repository with nothing tracked under `.tasks/` has no task tracking, which is a notice and
    not an error: the board still reports what git can tell it (S-010).
    """
    listed = [p for p in git(top, "ls-files", "-z", "--", ".tasks").split("\0") if p]
    if not listed:
        return [], [NOTICE_NO_TASKS]
    tasks, notices = [], []
    for rel in sorted(listed):
        if not TASK_PATH_RE.match(rel):
            continue
        path = Path(top) / rel
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue  # tracked but deleted in the working tree: not a task any more
        except (OSError, UnicodeDecodeError) as exc:
            notices.append(f"task file could not be read: {rel} ({exc.__class__.__name__})")
            continue
        tasks.append(parse_task(rel, text))
    return tasks, notices


def priority_rank(priority):
    """P1 before P2 and so on; a missing or unrecognised priority after every known one."""
    match = PRIORITY_RE.match(priority or "")
    return int(match.group(1)) if match else 10_000


def by_priority(entries):
    return sorted(entries, key=lambda e: (priority_rank(e["priority"]), e["id"]))


def task_entry(task, **extra):
    """A task as it appears on the board. Read out of a task file, so its tier is Green (S-014)."""
    entry = {
        "id": task["id"],
        "title": task["title"],
        "priority": task["priority"],
        "file": task["file"],
        "tier": "green",
        "provenance": task["file"],
    }
    entry.update(extra)
    return entry


def classify(tasks):
    """Split open tasks into waiting on the person, blocked, and planned.

    A closed task is never waiting, whatever its body says (S-005). A task can be both waiting and
    blocked, and then it is listed under both, because each list answers a different question.
    """
    done_ids = {t["id"] for t in tasks if t["closed"]}
    waiting, blocked, planned = [], [], []
    for task in tasks:
        if task["closed"]:
            continue
        unfinished = [d for d in task["depends_on"] if d not in done_ids]
        if task["reasons"]:
            waiting.append(task_entry(task, reason=", ".join(task["reasons"])))
        if unfinished:
            blocked.append(task_entry(task, waits_on=unfinished))
        if not task["reasons"] and not unfinished:
            planned.append(task_entry(task))
    return by_priority(waiting), by_priority(blocked), by_priority(planned)


# ---------------------------------------------------------------------------------------------
# The board
# ---------------------------------------------------------------------------------------------

def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(moment):
    return moment.astimezone(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_board(repo=".", *, now=None):
    """Everything the sitrep derives for one repository, as one dictionary.

    Keys owed to later tasks are present and empty: `in_flight` and `changed` are `feat-0067`'s,
    `figures` is `feat-0068`'s, and `watermark` is `feat-0069`'s.
    """
    repository, revision = repository_facts(repo)
    tasks, notices = load_tasks(repository["path"])
    waiting, blocked, planned = classify(tasks)
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "revision": revision,
        "generated": _iso(now or _utc_now()),
        "watermark": {"revision": None, "kind": None},
        "waiting": waiting,
        "blocked": blocked,
        "planned": planned,
        "in_flight": [],
        "changed": {"commits": 0, "closed": [], "updated": []},
        "figures": [],
        "notices": notices,
    }


def main(argv=None):
    """Print the board plainly. `feat-0070` replaces this with the sitrep, the page and the document."""
    try:
        board = build_board(".")
    except SitrepError as exc:
        print(f"sitrep could not be produced: {exc}", file=sys.stderr)
        return 1
    for title, key in (("waiting on you", "waiting"), ("blocked", "blocked")):
        print(f"{title} ({len(board[key])})")
        for entry in board[key]:
            detail = entry.get("reason") or ", ".join(entry.get("waits_on", []))
            print(f"  {entry['priority'] or '-'} {entry['id']}  {entry['title']}  ({detail})")
    for notice in board["notices"]:
        print(f"notice: {notice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
