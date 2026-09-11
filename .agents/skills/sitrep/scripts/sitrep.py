#!/usr/bin/env python3
"""sitrep: a board for one repository, generated from its own tracked records.

    python sitrep.py

The behavioural contract is `docs/spec/sitrep.md` in the Zen Agent Skills repository. This file
implements it one task at a time, in the order that spec's readiness record sets: `feat-0066`
built what waits on the person and what is blocked, `feat-0067` added in-flight work and what
changed since a revision, `feat-0068` adds evidence tiers and the figures a repository declares,
and the tasks after it add the watermark, the renderings, and the session-start hook. Sections owed
to a later task are present in the board with an empty value, so the board's shape never changes
under a reader.

Standard library only, so it runs on a bare Python 3 wherever the skill is installed.

Five properties are load-bearing and shape everything below.

**Only tracked records are state.** Task files are found with `git ls-files`, never with a
directory listing, because an untracked file on one machine is not part of the repository. The
hts-app prototype this replaces met a simulator output in an untracked folder that reported 70
where a fresh run reported 74, and it looked exactly as authoritative as everything else.

**A decision answers only the questions above it.** A task routinely carries an answered
`## Decision` from one round and a new `## Open question` raised after it. Asking whether both
headings exist anywhere marked such a task answered and dropped the only P1 from the prototype's
queue, so the rule here is positional: the task waits while its last open question has no decision
below it.

**In flight comes from git, not from task status.** No task file in any of the author's
repositories sets `status: in_progress`, and the prototype reported nothing in progress while a
worktree held uncommitted work. Worktrees and unmerged branches are what work in flight actually
looks like.

**A figure's tier is derived from where it came from, never asserted.** A page where every number
looks equally solid is how a wrong number survives, so each figure carries the tier its source
earns and no more: an untracked file cannot rise above White whatever it is declared as, and Gold
needs a named test this script can actually find.

**Nothing in the repository changes.** Every git call runs with optional locks off, so not even
`git status` refreshes the index behind the person's back.
"""

from __future__ import annotations

import datetime as _dt
import json
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

# The repository's own board configuration, committed at its top level.
CONFIG_FILE = ".sitrep.json"
# One `name` or `name[field=value]` per dotted segment.
SEGMENT_RE = re.compile(r"^([^\[\]]*)(?:\[([^=\[\]]+)=([^\[\]]*)\])?$")
# The spec's "tracked test file": a name starting `test_`, or containing `.test.` or `_test.`.
TEST_FILE_GLOBS = (":(glob)**/test_*", ":(glob)**/*.test.*", ":(glob)**/*_test.*")

NOTICE_NO_TASKS = "no task tracking"
NOTICE_NO_INTEGRATION = "no integration branch"
REASON_OPEN_QUESTION = "open question"
REASON_HUMAN_EYE = "needs a human eye"
LABEL_UNTRACKED = "untracked"


class SitrepError(Exception):
    """The board could not be produced, with a reason a person can act on."""


class FigureError(Exception):
    """One declared figure could not be read. The board reports it and carries on."""


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


def held_at_head(top, rel):
    """True when the current revision holds `rel`, which is the spec's meaning of tracked."""
    return git_quiet(top, "cat-file", "-e", f"HEAD:{rel}") is not None


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
# In flight and changed, from git
# ---------------------------------------------------------------------------------------------

def worktree_entries(top):
    """Every worktree of this clone with uncommitted changes, its branch, and how many paths.

    A path counts as changed when `git status --porcelain` lists it, untracked files included,
    because a new file nobody has added yet is exactly the work the prototype missed. A worktree
    whose directory is gone is skipped rather than reported, since there is nothing to look at.
    """
    entries = []
    for block in git(top, "worktree", "list", "--porcelain").strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        path = fields.get("worktree")
        if not path or "bare" in fields or not Path(path).is_dir():
            continue
        status = git_quiet(path, "status", "--porcelain")
        changed = len([line for line in (status or "").splitlines() if line.strip()])
        if not changed:
            continue
        branch = fields.get("branch", "")
        branch = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else "(detached)"
        entries.append({
            "kind": "worktree", "name": path, "branch": branch, "changed_paths": changed,
            "tier": "purple", "provenance": "git",
        })
    return entries


def resolve_integration(top, declared=None):
    """The branch finished work merges into, and a notice when there is none (S-039).

    The spec's surface order: the declared branch, else the default branch of remote `origin`,
    else `main`. A declared branch that does not resolve is reported rather than silently replaced
    by the default, because a board that quietly compares against the wrong branch reports the
    wrong work as in flight and nothing on it says so.
    """
    if declared:
        if git_quiet(top, "rev-parse", "--verify", "--quiet", f"{declared}^{{commit}}"):
            return declared, None
        return None, f"integration branch not found: {declared}"
    origin_head = (git_quiet(top, "symbolic-ref", "--quiet", "--short",
                             "refs/remotes/origin/HEAD") or "").strip()
    if origin_head:
        return origin_head, None
    if git_quiet(top, "rev-parse", "--verify", "--quiet", "refs/heads/main"):
        return "main", None
    return None, NOTICE_NO_INTEGRATION


def branch_entries(top, integration):
    """Local branches holding commits the integration branch does not, most recent first.

    Compared with the integration ref exactly as resolved, so when that is `origin/main`, a local
    `main` carrying unpushed commits is listed: work nobody else can see yet is in flight.
    """
    rows = []
    listing = git(top, "for-each-ref", "--format=%(refname:short)%09%(committerdate:unix)",
                  "refs/heads")
    for line in listing.splitlines():
        name, _, stamp = line.partition("\t")
        if not name or name == integration:
            continue
        count = (git_quiet(top, "rev-list", "--count", f"{integration}..{name}") or "0").strip()
        unmerged = int(count) if count.isdigit() else 0
        if unmerged:
            rows.append((int(stamp) if stamp.isdigit() else 0, name, unmerged))
    rows.sort(key=lambda row: (-row[0], row[1]))
    return [{"kind": "branch", "name": name, "unmerged_commits": unmerged,
             "tier": "purple", "provenance": "git"} for _, name, unmerged in rows]


def changes_since(top, base):
    """What changed between `base` and HEAD: how many commits, which tasks closed, which updated.

    A task is closed when its file arrives under `.tasks/done/` in the range, and updated when its
    file changed in place outside it. Ids come from the file names, which the kit's validator keeps
    equal to each file's `id`.
    """
    if not base:
        return {"commits": 0, "closed": [], "updated": []}
    commits = (git(top, "rev-list", "--count", f"{base}..HEAD") or "0").strip()
    closed, updated = set(), set()
    diff = git(top, "diff", "--name-status", "-M", base, "HEAD", "--", ".tasks")
    for line in diff.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code, path = parts[0][:1], parts[-1]
        match = TASK_PATH_RE.match(path)
        if not match:
            continue
        if path.startswith(".tasks/done/") and code in ("A", "R", "C"):
            closed.add(match.group(1))
        elif code == "M" and not path.startswith(".tasks/done/"):
            updated.add(match.group(1))
    return {"commits": int(commits) if commits.isdigit() else 0,
            "closed": sorted(closed), "updated": sorted(updated - closed)}


# ---------------------------------------------------------------------------------------------
# Figures and their tiers
# ---------------------------------------------------------------------------------------------

def tier_rank(tier):
    return TIERS.index(tier)


def lowest_tier(tiers, default):
    """The weakest tier among `tiers`, or `default` when there are none to compare."""
    known = [tier for tier in tiers if tier in TIERS]
    return min(known, key=tier_rank) if known else default


def count_figure(name, entries, default):
    """A count of board entries, carrying the lowest tier among what it counts (S-019).

    A count is only as good as the weakest thing in it: eight tasks read out of task files make a
    Green eight, however exactly they were counted. `default` is the tier of the source the list
    comes from, used when the list is empty and there is nothing to take the minimum over.
    """
    return {"name": name, "value": len(entries),
            "tier": lowest_tier([e.get("tier") for e in entries], default),
            "provenance": "count of board entries"}


def load_config(top):
    """The repository's `.sitrep.json`, or an empty configuration, plus any notice.

    Read from the working tree, so a person editing it sees the effect before committing it. The
    data files it points at are read at the current revision instead, because their tier depends on
    what the repository holds rather than on what one machine has edited.
    """
    path = Path(top) / CONFIG_FILE
    if not path.is_file():
        return {}, []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return {}, [f"configuration could not be read: {CONFIG_FILE} ({exc.__class__.__name__})"]
    if not isinstance(config, dict):
        return {}, [f"configuration could not be read: {CONFIG_FILE} is not an object"]
    return config, []


def select(data, path):
    """Follow a dotted path, with at most one `[field=value]` filter on an array.

    A filter compares a string field as it is and any other value in its JSON spelling, so
    `[released=true]` matches a JSON `true` rather than Python's `True`.
    """
    current, filtered = data, False
    for segment in (path or "").split("."):
        match = SEGMENT_RE.match(segment)
        if not match:
            raise FigureError(f"selection {path!r} is not a dotted path")
        key, field, value = match.groups()
        if key:
            if not isinstance(current, dict) or key not in current:
                raise FigureError(f"nothing at {key!r} in selection {path!r}")
            current = current[key]
        if field is not None:
            if filtered:
                raise FigureError(f"selection {path!r} has more than one filter")
            if not isinstance(current, list):
                raise FigureError(f"selection {path!r} filters something that is not an array")

            def keep(item):
                if not isinstance(item, dict) or field not in item:
                    return False
                found = item[field]
                return (found if isinstance(found, str) else json.dumps(found)) == value

            current, filtered = [item for item in current if keep(item)], True
    return current


def declared_figure(top, declaration):
    """One figure from `.sitrep.json`, with the tier its source earns (S-012, S-013, S-015)."""
    rel = str(declaration.get("file") or "").replace("\\", "/")
    kind = declaration.get("kind")
    if kind not in ("count", "value"):
        raise FigureError(f"kind must be count or value, not {kind!r}")
    if not rel:
        raise FigureError("no file is named")
    tracked = held_at_head(top, rel)
    if tracked:
        text = git(top, "show", f"HEAD:{rel}")
    else:
        try:
            text = (Path(top) / rel).read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FigureError(f"{rel} does not exist") from None
        except (OSError, UnicodeDecodeError) as exc:
            raise FigureError(f"{rel} could not be read ({exc.__class__.__name__})") from None
    try:
        data = json.loads(text)
    except ValueError:
        raise FigureError(f"{rel} is not JSON") from None
    selected = select(data, declaration.get("select", ""))
    if kind == "count":
        if not isinstance(selected, (list, dict)):
            raise FigureError(f"selection {declaration.get('select')!r} is not something to count")
        value, tier = len(selected), "purple"
    else:
        if isinstance(selected, (list, dict)):
            raise FigureError(f"selection {declaration.get('select')!r} is not a single value")
        value, tier = selected, "blue"
    figure = {"name": declaration.get("name"), "value": value, "tier": tier, "provenance": rel}
    if not tracked:
        figure["tier"], figure["label"] = "white", LABEL_UNTRACKED
    return figure


def test_name_present(top, name):
    """True when a tracked test file at the current revision contains `name`."""
    found = git_quiet(top, "grep", "-F", "-l", "-e", name, "HEAD", "--", *TEST_FILE_GLOBS)
    return bool(found and found.strip())


def figures_from_config(top, config):
    """Every declared, pinned and hand-entered figure, plus a notice for each one that failed."""
    figures, notices = [], []
    for declaration in config.get("figures") or []:
        name = (declaration or {}).get("name") or "(unnamed)"
        try:
            figures.append(declared_figure(top, declaration or {}))
        except FigureError as exc:
            notices.append(f"figure {name} could not be read: {exc}")
    by_name = {figure["name"]: figure for figure in figures}
    for pin in config.get("pins") or []:
        figure, test = by_name.get((pin or {}).get("figure")), (pin or {}).get("test")
        if figure is None:
            notices.append(f"pin names no figure: {(pin or {}).get('figure')}")
            continue
        if figure["tier"] not in ("blue", "purple"):
            continue  # an untracked source stays White whatever pins it (S-015)
        if test and test_name_present(top, test):
            figure["tier"], figure["pinned_by"] = "gold", test
        else:
            notices.append(f"pinned test not found: {test} (figure {figure['name']})")
    for entry in config.get("manual") or []:
        entry = entry or {}
        figures.append({"name": entry.get("name"), "value": entry.get("value"), "tier": "white",
                        "provenance": entry.get("source") or "no source given"})
    return figures, notices


# ---------------------------------------------------------------------------------------------
# The board
# ---------------------------------------------------------------------------------------------

def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(moment):
    return moment.astimezone(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_board(repo=".", *, base=None, integration=None, now=None):
    """Everything the sitrep derives for one repository, as one dictionary.

    `base` is the revision changed-since starts from, a parameter until `feat-0069` supplies the
    watermark. `integration` overrides the `integration_branch` a `.sitrep.json` declares.
    """
    repository, revision = repository_facts(repo)
    top = repository["path"]
    config, notices = load_config(top)
    tasks, task_notices = load_tasks(top)
    notices += task_notices
    waiting, blocked, planned = classify(tasks)
    in_flight = worktree_entries(top)
    branch, notice = resolve_integration(top, integration or config.get("integration_branch"))
    if notice:
        notices.append(notice)
    if branch:
        in_flight += branch_entries(top, branch)
    declared, figure_notices = figures_from_config(top, config)
    notices += figure_notices
    figures = [
        count_figure("waiting on you", waiting, "green"),
        count_figure("blocked", blocked, "green"),
        count_figure("in flight", in_flight, "purple"),
    ] + declared
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "revision": revision,
        "generated": _iso(now or _utc_now()),
        "watermark": {"revision": base, "kind": None},
        "waiting": waiting,
        "blocked": blocked,
        "planned": planned,
        "in_flight": in_flight,
        "changed": changes_since(top, base) if revision else changes_since(top, None),
        "figures": figures,
        "notices": notices,
    }


def _describe(entry):
    if entry.get("kind") == "worktree":
        return f"worktree {entry['name']} [{entry['branch']}]  {entry['changed_paths']} changed paths"
    if entry.get("kind") == "branch":
        return f"branch {entry['name']}  {entry['unmerged_commits']} unmerged commits"
    detail = entry.get("reason") or ", ".join(entry.get("waits_on", []))
    return f"{entry['priority'] or '-'} {entry['id']}  {entry['title']}  ({detail})"


def main(argv=None):
    """Print the board plainly. `feat-0070` replaces this with the sitrep, the page and the document."""
    try:
        board = build_board(".")
    except SitrepError as exc:
        print(f"sitrep could not be produced: {exc}", file=sys.stderr)
        return 1
    for title, key in (("waiting on you", "waiting"), ("in flight", "in_flight"),
                       ("blocked", "blocked")):
        print(f"{title} ({len(board[key])})")
        for entry in board[key]:
            print(f"  {_describe(entry)}")
    print("figures")
    for figure in board["figures"]:
        print(f"  {figure['name']}: {figure['value']}  [{TIER_NAMES[figure['tier']]}] "
              f"{figure['provenance']}")
    for notice in board["notices"]:
        print(f"notice: {notice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
