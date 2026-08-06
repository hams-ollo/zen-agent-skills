#!/usr/bin/env python3
"""Re-fetch every recorded provenance block and report upstream drift.

Material folded in from an external project carries a provenance block naming where it
came from, under what license, when it was retrieved, and the SHA256 of the bytes that
were retrieved. This script re-fetches each recorded URL and compares digests. It answers
exactly one question: has the thing we adapted *from* changed since we looked.

The digest is taken over the retrieved upstream bytes, never over the adapted local file.
The local file is expected to differ, because adaptation is the point, so digesting it
would make the check answer a question nobody asked.

Why this detects and does not sync
----------------------------------
Upstream's equivalent (`scripts/sync-maintainability-review.mjs` in RepoPrompt Workflows)
rewrites a marked region in place, which is correct there because upstream vendors that
region verbatim. This kit adapts instead: every fold-in was house-styled and retargeted,
so an automatic overwrite would destroy the adaptation. Detect drift, name it, and let a
human decide. That is the one place the upstream design is deliberately not copied.

Usage
-----
    python scripts/check-provenance.py            # re-fetch and compare every record
    python scripts/check-provenance.py --list     # print what is recorded, fetch nothing

Exit codes
----------
0   every fetchable record matches its recorded digest
1   at least one recorded source has drifted
2   an error: a source could not be fetched, or a record is malformed

Drift and errors both name the offending source and the file that records it, because a
non-zero exit whose output does not say what moved costs the reader the whole investigation.

The convention itself, including the field list and where a block lives in each file type,
is in the conventions section of AGENTS.md. Standard library only, per that same section.
"""
import hashlib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that hold shipped, adapted material. Everything else is deliberately out of
# scope: AGENTS.md, docs/, and tests/ all describe the convention or exercise it, so they
# contain illustrative blocks that are documentation rather than records of a real fold-in.
# Scanning them would make the script chase example URLs and fail on its own documentation.
SCAN_DIRS = (".agents", "scripts")
SCAN_SUFFIXES = (".md", ".py")

# Recognised block fields. `origin` and `note` are prose and are never fetched; `status`
# marks a record whose source could not be located.
RECORD_KEYS = ("source", "author", "license", "retrieved", "sha256", "origin", "note", "status")
REQUIRED_KEYS = ("source", "author", "license", "retrieved", "sha256")
UNLOCATABLE_REQUIRED_KEYS = ("source", "author", "license", "status", "note")

_KEY_RE = re.compile(r"^[ \t]*([a-z0-9_]+):[ \t]*(.*?)[ \t]*$")
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

USER_AGENT = "zen-agent-skills-check-provenance"


def parse_records(text):
    """Every provenance record in `text`, as dicts carrying a 1-based `line`.

    A record starts at a `source:` line and runs through the contiguous recognised
    `key: value` lines that follow it. That is the whole grammar: it needs no delimiters,
    so the same block is readable inside a Python docstring, a Markdown fenced block, and
    plain prose without three parsers.

    A bare `source:` line is not enough to qualify, because `source:` is an ordinary word
    that other templates use: the `review-depth` skill's output block has a `source:` field
    meaning "detected or user", and an earlier draft of this parser reported it as a fold-in
    with a missing digest. So a run qualifies only if it carries at least one other
    recognised key. A run that carries one but is missing a required field is still a
    record, and is reported as malformed rather than skipped, so a typo cannot hide a
    fold-in from the check.
    """
    records = []
    lines = (text or "").splitlines()
    index = 0
    while index < len(lines):
        match = _KEY_RE.match(lines[index])
        if not match or match.group(1) != "source":
            index += 1
            continue
        record = {"line": index + 1}
        while index < len(lines):
            match = _KEY_RE.match(lines[index])
            if not match or match.group(1) not in RECORD_KEYS:
                break
            key, value = match.group(1), match.group(2)
            if key in record:
                break  # a repeated key means the next record has started
            record[key] = value
            index += 1
        if set(record) - {"line", "source"}:
            records.append(record)
    return records


def iter_provenance_files(root):
    """Every scannable file under `root`, sorted, so output order is stable."""
    for directory in SCAN_DIRS:
        base = Path(root) / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in SCAN_SUFFIXES:
                yield path


def collect(root):
    """Every (relative path, record) pair recorded under `root`."""
    found = []
    for path in iter_provenance_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        for record in parse_records(text):
            found.append((rel, record))
    return found


def validate(record):
    """The reason this record is malformed, or None when it is well formed."""
    if record.get("status", "").lower() == "unlocatable":
        missing = [k for k in UNLOCATABLE_REQUIRED_KEYS if not record.get(k)]
        if missing:
            return f"unlocatable record is missing: {', '.join(missing)}"
        return None
    missing = [k for k in REQUIRED_KEYS if not record.get(k)]
    if missing:
        return f"missing required field(s): {', '.join(missing)}"
    if not record["source"].lower().startswith(("http://", "https://")):
        return f"source is not an absolute http(s) URL: {record['source']}"
    if not _SHA256_RE.match(record["sha256"]):
        return f"sha256 is not 64 lowercase hex characters: {record['sha256']}"
    if not _DATE_RE.match(record["retrieved"]):
        return f"retrieved is not an ISO date (YYYY-MM-DD): {record['retrieved']}"
    return None


def fetch(url, timeout=30):
    """The exact bytes a plain HTTP GET returns. Raises on any failure."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def check_record(record, fetcher):
    """Classify one record. Returns (status, message).

    status is one of `ok`, `unlocatable`, `drift`, `error`.
    """
    problem = validate(record)
    if problem:
        return "error", problem
    if record.get("status", "").lower() == "unlocatable":
        return "unlocatable", f"source not locatable: {record['source']}"
    url = record["source"]
    try:
        content = fetcher(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        # Degrade cleanly. A traceback here would read as a defect in this script rather
        # than as the network being down, which is the common case by a wide margin.
        return "error", f"could not fetch {url}: {exc}"
    if not isinstance(content, (bytes, bytearray)):
        return "error", f"fetch of {url} returned {type(content).__name__}, expected bytes"
    digest = hashlib.sha256(content).hexdigest()
    if digest == record["sha256"]:
        return "ok", f"up to date ({digest[:12]}) {url}"
    return "drift", (
        f"DRIFT: {url}\n"
        f"      recorded: {record['sha256']}\n"
        f"      upstream: {digest}"
    )


def main(argv=None, root=None, fetcher=None, out=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    out = sys.stdout if out is None else out
    root = REPO_ROOT if root is None else Path(root)
    fetcher = fetch if fetcher is None else fetcher

    records = collect(root)
    if not records:
        out.write("No provenance records found. Nothing folded in is recorded, which is\n"
                  "either correct or a sign a fold-in skipped the convention in AGENTS.md.\n")
        return 0

    if "--list" in argv:
        for rel, record in records:
            state = record.get("status", "recorded")
            out.write(f"{rel}:{record['line']}  [{state}]  {record.get('source', '(no source)')}\n")
        out.write(f"\n{len(records)} record(s).\n")
        return 0

    counts = {"ok": 0, "unlocatable": 0, "drift": 0, "error": 0}
    for rel, record in records:
        status, message = check_record(record, fetcher)
        counts[status] += 1
        out.write(f"{rel}:{record['line']}  {message}\n")

    out.write(
        f"\n{counts['ok']} up to date, {counts['drift']} drifted, "
        f"{counts['unlocatable']} unlocatable, {counts['error']} error(s).\n"
    )
    if counts["error"]:
        return 2
    if counts["drift"]:
        out.write("Upstream moved. Review the change and decide whether to re-adapt; this\n"
                  "script never rewrites an adapted file. Update the recorded sha256 and\n"
                  "retrieved date only once a human has reconciled the difference.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
