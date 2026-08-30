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
2   an error: a source could not be fetched, a file in scope could not be read, or a
    record is malformed

What it contacts, and under what limits
---------------------------------------
This is the only script in the kit that opens a network connection, so SECURITY.md names
it and the limits are stated here rather than left to be read out of the code. It contacts
exactly the URLs recorded in the repository's own provenance blocks, over `https://` only,
with a plain GET, and it digests what comes back. Nothing fetched is executed, stored, or
written anywhere. `--list` prints every URL a run would contact and fetches nothing, so the
set is reviewable before any connection is made. A response is read under MAX_FETCH_BYTES
and exceeding it is an error rather than a truncated digest.

`https://` only means at both ends, and it did not always. `validate()` has always rejected
an `http://` source, but `urlopen` follows redirects and the standard library's own
allow-list admits `http`, so an `https` source answering `302 Location: http://...` was
followed into plaintext, where a digest authenticates nothing (`bug-0054`). A redirect off
`https` is now refused by `HttpsOnlyRedirectHandler`, installed on the opener `fetch()` uses
rather than checked after the bytes have arrived. One that stays on `https` is followed,
because upstream repositories get renamed, and the URL that answered is reported when it
differs from the one recorded.

Drift and errors both name the offending source and the file that records it, because a
non-zero exit whose output does not say what moved costs the reader the whole investigation.

A file in scope that cannot be read is reported the same way and exits 2, rather than being
skipped. Skipping it dropped every record that file carried, named the file nowhere, and left
a smaller count that reads exactly like a clean result (bug-0019). On Windows the trigger is
ordinary: another process holding an exclusive handle, a scanner mid-scan, an editor lock.
The other files are still checked, because one unreadable file should not hide the state of
the rest.

A block sitting in one of the placements the convention names, and failing to parse into a
complete record, is reported the same way for the same reason. One mistyped field name used
to end the run after `source:` alone, which left too little to qualify as a record, so a
whole fold-in disappeared from the run at exit 0 (bug-0041). See parse_records for how a
declared placement is told apart from a `source:` line that was never provenance.

A placement that produced no record at all is reported the same way, because the scan used
to begin only at a `source:` line: a typo on the key itself (`sorce:`), or a fence nobody
ever put a source in, was examined by nothing and printed as nothing at exit 0 (bug-0042).
A placement that is *empty* is named rather than counted, because it records nothing to
re-fetch and is most often a fold-in in progress; see unsourced_placements for that call.

The convention itself, including the field list and where a block lives in each file type,
is in the conventions section of AGENTS.md. Standard library only, per that same section.
"""
import hashlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that hold shipped, adapted material. Everything else is deliberately out of
# scope: AGENTS.md, docs/, and tests/ all describe the convention or exercise it, so they
# contain illustrative blocks that are documentation rather than records of a real fold-in.
# Scanning them would make the script chase example URLs and fail on its own documentation.
SCAN_DIRS = (".agents", "scripts")
# The file kinds scanned inside those directories. Written lowercase and matched against a
# lowered suffix in `iter_provenance_files`, so do not add `.MD` or `.PY` here: the case an
# author typed is not a fact about whether a file carries a fold-in. Agreeing with
# `classify_supporting_file` in validate-skills.py, which lowers both sides (chore-0055).
SCAN_SUFFIXES = (".md", ".py")

# Recognised block fields. `origin` and `note` are prose and are never fetched; `status`
# marks a record whose source could not be located.
RECORD_KEYS = ("source", "author", "license", "retrieved", "sha256", "origin", "note", "status")
REQUIRED_KEYS = ("source", "author", "license", "retrieved", "sha256")
UNLOCATABLE_REQUIRED_KEYS = ("source", "author", "license", "status", "note")

_KEY_RE = re.compile(r"^[ \t]*([a-z0-9_]+):[ \t]*(.*?)[ \t]*$")
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

# The two placements the convention in AGENTS.md names, recognised positively rather than
# guessed at: a fenced block whose info string is `provenance` (markdown), and an underlined
# `Provenance` section of a module docstring (Python).
#
# Both markers are matched case-insensitively, and that agreement is the point. The fence's
# info string has always been lowered before comparison, so ```Provenance was a placement
# while a docstring headed `provenance` was not: one concept, two answers on the same input.
# The heading now carries IGNORECASE so the two spellings of the same marker are one marker
# (bug-0047), agreeing with `SCAN_SUFFIXES` one layer out in this file (bug-0046) and with
# `classify_supporting_file` in validate-skills.py (chore-0055) rather than inventing a third
# convention. Narrowing the fence instead would have been the other way to agree, and it was
# rejected: it removes coverage rather than adding it, so a malformed block inside a
# ```Provenance fence that is reported today would go back to being dropped at exit 0, which
# is the exact silence bug-0016, bug-0019, bug-0041, bug-0042 and bug-0046 were each filed for.
#
# Widening the heading stays small because the heading is only half of the marker: a
# placement also needs the underline below it, and it must not be inside an open fence. So a
# case variant of the bare word in prose is still not a placement, and the only shape this
# newly admits is an underlined heading spelled some other way.
_FENCE_RE = re.compile(r"^[ \t]*(?:`{3,}|~{3,})[ \t]*([A-Za-z0-9_+-]*)[ \t]*$")
_SECTION_RE = re.compile(r"^[ \t]*Provenance[ \t]*$", re.IGNORECASE)
_UNDERLINE_RE = re.compile(r"^[ \t]*[-=]{2,}[ \t]*$")

USER_AGENT = "zen-agent-skills-check-provenance"

# The most a single source may return. Every recorded source is one upstream text file, the
# largest in the tree today being a few tens of kilobytes, so 10 MiB could not plausibly
# refuse a real one. It exists so a hostile or merely enormous URL cannot be read into
# memory whole, and exceeding it is an error rather than a truncated digest, because a
# truncated digest would compare unequal and be reported as drift: the wrong word for the
# wrong reason, and an invitation to update a record that never moved.
MAX_FETCH_BYTES = 10 * 1024 * 1024


class ResponseTooLarge(ValueError):
    """A source returned more than MAX_FETCH_BYTES.

    A ValueError, because check_record() already treats that as an unfetchable source, which
    is what this is: the bytes exist but were never read, so there is nothing to digest.
    """


class InsecureRedirect(ValueError):
    """A redirect left `https`, so the bytes past that hop authenticate nothing.

    A ValueError for the same reason ResponseTooLarge is: check_record() already treats one
    as an unfetchable source, and that is exactly what this is.

    The rule this enforces is `validate()`'s, applied where it was missing. That function
    rejects an `http://` source and says why: over plaintext the digest authenticates
    nothing, so the record would read as verified provenance for bytes anyone on the path
    could have written. But the check ran against the recorded string only, and
    `urllib.request.urlopen` follows redirects by default, with the standard library's own
    allow-list in `HTTPRedirectHandler.http_error_302` reading

        if urlparts.scheme not in ('http', 'https', 'ftp', ''):

    so an `https://` source answering `302 Location: http://...` was followed into plaintext,
    which is the one thing that comment says must not happen (`bug-0054`).
    """


class HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only while it stays on `https`.

    Enforced here rather than after the fact, because after the fact is too late: the
    plaintext request has already been made and answered, and whatever was on the path has
    already seen it and had its chance to write the reply.

    Raising rather than returning `None`. Returning `None` is urllib's documented way to
    decline a redirect and it re-raises the original `HTTPError`, which reaches a reader as
    "HTTP Error 302: Found" and says nothing about why a checker refused. Raising a
    ValueError subclass reaches `check_record()`'s existing `except` and carries both URLs
    into the message.

    Only the scheme is judged. A redirect to a different `https` host is allowed and is
    reported by `check_record()` rather than refused, because upstream repositories are
    renamed and moved, and a checker that fails on a moved file is one that gets disabled
    inside a week.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        scheme = urllib.parse.urlsplit(newurl).scheme.lower()
        if scheme != "https":
            raise InsecureRedirect(
                f"refused a redirect off https: {req.full_url} -> {newurl}. Past that hop "
                f"the digest authenticates nothing, so this is reported rather than "
                f"followed."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Built once. `build_opener` drops its own default redirect handler when handed a subclass
# of it, so this replaces the default rather than stacking a second one in front.
_OPENER = urllib.request.build_opener(HttpsOnlyRedirectHandler)


class Fetched(NamedTuple):
    """What a fetch returned, and where it actually came from.

    `url` is the URL after every redirect, which is the one the digest belongs to. It is
    carried rather than discarded because a record whose `source:` no longer names what was
    retrieved has drifted in the thing it pins, even when the bytes are identical, and
    silently digesting the new location would let that record rot pointing at a redirect.
    """

    content: bytes
    url: str


def declared_lines(lines):
    """One bool per line: is this line inside a placement the convention declares?

    The convention in AGENTS.md says where a provenance block lives, and this reads that
    statement rather than inferring intent from the block's contents. A markdown fence
    tagged `provenance` opens a region and the matching close ends it; an underlined
    `Provenance` heading opens one and the first line that is neither blank nor a
    `key: value` line ends it, which in a module docstring is the docstring terminator.

    The opening marker itself counts as inside: the fence line, or the heading's underline.
    Nothing reads a field off it, and it is what makes a placement holding nothing at all
    still a region rather than nothing, which is the shape bug-0042 needed to see.

    Fences are tracked generically, not only the `provenance` ones, so a `source:` field in
    somebody else's fenced example is known to be inside a ```text block rather than merely
    failing to look like provenance.

    Neither marker's case is load-bearing: the fence's info string is lowered before it is
    compared and the heading is matched with IGNORECASE, so the same word in any spelling is
    the same marker (bug-0047). The heading's underline is not optional, though, and it is
    what keeps that widening narrow: a bare `provenance` line in prose opens nothing.
    """
    inside = [False] * len(lines)
    fence = None  # the info string of the currently open fence, or None
    section = False
    for index, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            # Markdown fences do not nest: the first one opens, the next one closes.
            fence = fence_match.group(1).lower() if fence is None else None
            # Closing sets `fence` back to None, so a closing line is outside and two
            # adjacent placements never run together into one region.
            inside[index] = fence == "provenance"
            section = False
            continue
        if fence is not None:
            inside[index] = fence == "provenance"
            continue
        if section:
            if line.strip() and not _KEY_RE.match(line):
                section = False
            else:
                inside[index] = True
                continue
        if index and _UNDERLINE_RE.match(line) and _SECTION_RE.match(lines[index - 1]):
            section = True
            inside[index] = True  # the underline opens the placement, as a fence line does
    return inside


def placement_regions(declared):
    """Every contiguous run of declared lines, as 0-based half-open (start, end) pairs.

    A regrouping of what declared_lines() already computed, not a second scan of the text.
    One region is one placement, because a placement's closing marker is not itself
    declared and so always separates it from the next.
    """
    regions = []
    start = None
    for index, flag in enumerate(declared):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            regions.append((start, index))
            start = None
    if start is not None:
        regions.append((start, len(declared)))
    return regions


def unsourced_placements(lines, declared, records):
    """A record for every declared placement that `records` never reached.

    parse_records() begins a run only at a line whose key is exactly `source`, so a
    placement that never produces that token was examined by nothing at all: a typo on the
    key itself (`sorce:`), and a fence carrying every other field but that one, both left
    the run reporting the clean empty state of a file with nothing folded in (bug-0042).
    This reads the placements bug-0041's declared_lines() already marks and asks the
    question from the other end, which of them yielded no record. Same scanner, regrouped.

    Two outcomes, because the two shapes are not the same mistake.

    **`no-source`**, a placement holding `key: value` lines but no `source:` one. Somebody
    wrote a block there, so a fold-in is claimed and nothing will ever re-fetch it. That is
    exactly the silence this file keeps producing, so it is a malformed record: reported by
    validate(), counted as an error, exit 2.

    **`empty`**, a placement holding nothing yet. Named in the output, and deliberately not
    counted and not fetched, so it does not change the exit code. An empty block claims no
    provenance and records no digest, so nothing can silently drift behind it, and the
    usual author is a skill that opened a fence it has not filled in. *Rejected: failing
    the run on it.* That reading is not free, because the run is also how an author checks
    the records that are finished, and it would stop on a file whose defect is already
    plain to anyone who opens it. Naming it keeps the property this family of bugs is
    actually about, that the tool never passes over part of its input without saying so.
    """
    started = {record["line"] - 1 for record in records}
    unsourced = []
    for start, end in placement_regions(declared):
        if any(start <= index < end for index in started):
            continue
        # The region's first line is its opening marker, which carries no field.
        content = [index for index in range(start + 1, end) if lines[index].strip()]
        if not content:
            unsourced.append({"line": start + 1, "placement": "empty"})
            continue
        keys = []
        for index in content:
            match = _KEY_RE.match(lines[index])
            if match:
                keys.append(match.group(1))
        unsourced.append({"line": content[0] + 1, "placement": "no-source", "keys": tuple(keys)})
    return unsourced


def parse_records(text):
    """Every provenance record in `text`, as dicts carrying a 1-based `line`.

    A record starts at a `source:` line and runs through the recognised `key: value` lines
    that follow it. A blank line inside the run is transparent: it carries no field, so it
    ends nothing. The run ends at the first line that is neither blank nor a recognised
    `key: value` line (a closing fence, a docstring terminator, a heading, prose, code), or
    at a repeated key, which means the next record has started. That is the whole grammar:
    one rule for every placement, so the same block is readable inside a Python docstring,
    a Markdown fenced block, and plain prose without three parsers.

    A blank line used to end the run, which meant one blank line after `source:` was enough
    to drop an otherwise valid block from the record set entirely, silently, at exit 0
    (bug-0016). Treating the blank as transparent guesses at nothing: every field collected
    is a field that was literally written, and any prose between two halves of a would-be
    block still ends the run rather than being read across.

    A run qualifies as a record in either of two ways.

    **Placement.** A run whose `source:` line sits inside a placement the convention in
    AGENTS.md declares, a markdown fence tagged `provenance` or an underlined `Provenance`
    docstring section, always qualifies, whatever it managed to collect. Somebody wrote the
    block down there on purpose, so the run is a fold-in record and any shortfall in it is
    the record's problem, reported by validate(), rather than a reason to disbelieve the
    block exists. The unrecognised `key: value` line that ended such a run is kept under
    `unrecognised`, because it is almost always the cause of everything else validate() is
    about to report and naming it saves the reader the diff.

    **Content, anywhere else.** A run outside any declared placement qualifies only if it
    carries at least one other recognised key, because `source:` is an ordinary word that
    other templates use: the `review-depth` skill's output block has a `source:` field
    meaning "detected or user", and an earlier draft of this parser reported it as a fold-in
    with a missing digest.

    Content alone used to be the whole rule, and it made a one-character typo silent: a
    misspelled field immediately after `source:` ended the run with only `source` collected,
    which failed the same content test that keeps review-depth out, so the entire block
    vanished from the run at exit 0 (bug-0041). Placement is what tells the two apart, and
    it is the convention's own answer: review-depth's field is inside a ```text fence, and
    every real block in this repository is inside one of the two declared placements.

    A declared placement that produced no run at all is a record too, carrying `placement`
    in place of any field, because the scan starts only at a `source:` line and so could not
    see one (bug-0042). unsourced_placements() builds those, off the same declared_lines()
    rather than a second scanner, and records how the two shapes differ.

    Near-miss detection on the key name was the alternative, and it was not taken: it would
    have judged `hash:` for `sha256:` to be a different field entirely while judging a
    template's genuine `notes:` field to be a typo of `note:`, on a threshold with nothing
    behind it. Placement asks where the block is, which the convention already answers.
    """
    records = []
    lines = (text or "").splitlines()
    declared = declared_lines(lines)
    index = 0
    while index < len(lines):
        match = _KEY_RE.match(lines[index])
        if not match or match.group(1) != "source":
            index += 1
            continue
        record = {"line": index + 1}
        placed = declared[index]
        cursor = index
        while cursor < len(lines):
            line = lines[cursor]
            if not line.strip():
                cursor += 1
                continue  # a blank line carries no field, so it terminates nothing
            match = _KEY_RE.match(line)
            if not match or match.group(1) not in RECORD_KEYS:
                if placed and match and declared[cursor]:
                    record["unrecognised"] = (match.group(1), cursor + 1)
                break
            key, value = match.group(1), match.group(2)
            if key in record:
                break  # a repeated key means the next record has started
            record[key] = value
            cursor += 1
        # The source line itself is always consumed, so cursor > index and the outer scan
        # always advances. It resumes on the terminator, which may itself start a record.
        index = cursor
        if placed or set(record) - {"line", "source"}:
            records.append(record)
    records.extend(unsourced_placements(lines, declared, records))
    records.sort(key=lambda record: record["line"])
    return records


def iter_provenance_files(root):
    """Every scannable file under `root`, sorted, so output order is stable.

    The suffix is lowered before the membership test. An exact match dropped a file named
    `.MD` or `.PY` out of the run entirely, taking every record it carried with it and
    naming it nowhere, which is the same silence as bug-0016, bug-0019, bug-0041 and
    bug-0042 one layer up: those lost a record inside a file that was read, this lost the
    file (bug-0046). Widening by case can only add a file to the scanned set, never remove
    one, since a name ending in `.md` in any case already lowers to `.md`.
    """
    for directory in SCAN_DIRS:
        base = Path(root) / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES:
                yield path


def collect(root):
    """The records recorded under `root`, and the files that could not be read.

    Returns `(found, unreadable)`: `found` is a list of (relative path, record) pairs, and
    `unreadable` a list of (relative path, reason) pairs for every file in scope whose read
    raised OSError.

    Both halves are returned rather than only the first, because this read used to be wrapped
    in a bare `except OSError: continue` (bug-0019). That dropped every record the file
    carried, named the file nowhere, and left the run reporting a smaller count that looks
    exactly like a clean result. Returning the failures alongside the records puts them where
    a caller cannot fail to see them, which a helper that swallowed them could not.

    Reading continues past a failure. One unreadable file must not hide the state of the
    others, so the caller reports them all and lets the exit code carry the verdict.
    """
    found = []
    unreadable = []
    for path in iter_provenance_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            unreadable.append((rel, str(exc)))
            continue
        for record in parse_records(text):
            found.append((rel, record))
    return found, unreadable


def validate(record):
    """The reason this record is malformed, or None when it is well formed.

    The unrecognised field is reported ahead of the missing ones, because it is what caused
    them: a block reported as missing four fields that are visibly written down reads as a
    defect in this script, and the field name that ended the run is the one thing a reader
    needs. Remaining shortfalls surface on the next run, which is how validate() already
    treats every other problem it finds.
    """
    placement = record.get("placement")
    if placement == "empty":
        return None  # nothing was claimed, so there is nothing to be short of
    if placement == "no-source":
        keys = record.get("keys") or ()
        held = f"it holds: {', '.join(keys)}" if keys else "it holds no 'key: value' line"
        return (
            f"declared provenance placement with no 'source:' line, {held}; "
            "a misspelled 'source' key is the usual cause"
        )
    unrecognised = record.get("unrecognised")
    if unrecognised:
        key, line = unrecognised
        return (
            f"unrecognised field '{key}' on line {line} ended the block early; "
            f"the recognised fields are: {', '.join(RECORD_KEYS)}"
        )
    if record.get("status", "").lower() == "unlocatable":
        missing = [k for k in UNLOCATABLE_REQUIRED_KEYS if not record.get(k)]
        if missing:
            return f"unlocatable record is missing: {', '.join(missing)}"
        return None
    missing = [k for k in REQUIRED_KEYS if not record.get(k)]
    if missing:
        return f"missing required field(s): {', '.join(missing)}"
    source = record["source"]
    if source.lower().startswith("http://"):
        # Rejected rather than silently upgraded: an upgrade would make the recorded
        # `source:` differ from what was fetched, and the record is meant to be
        # reproducible by hand. Over plaintext the digest authenticates nothing, so the
        # record would read as verified provenance for bytes anyone on the path could
        # have written.
        return f"source must be an https:// URL, not http://: {source}"
    if not source.lower().startswith("https://"):
        return f"source is not an absolute https:// URL: {source}"
    if not _SHA256_RE.match(record["sha256"]):
        return f"sha256 is not 64 lowercase hex characters: {record['sha256']}"
    if not _DATE_RE.match(record["retrieved"]):
        return f"retrieved is not an ISO date (YYYY-MM-DD): {record['retrieved']}"
    return None


def fetch(url, timeout=30, max_bytes=MAX_FETCH_BYTES):
    """The exact bytes a plain GET returns, up to `max_bytes`, and where they came from.

    Reads one byte past the bound rather than the whole body, so an enormous response is
    refused instead of held in memory, and raises ResponseTooLarge rather than returning
    what it managed to read.

    Opened through `_OPENER` rather than `urllib.request.urlopen`, so a redirect off `https`
    raises InsecureRedirect instead of being followed into plaintext (`bug-0054`). The
    returned `url` is the one that actually answered, after any redirect, because that is
    the URL the digest belongs to.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with _OPENER.open(request, timeout=timeout) as response:
        content = response.read(max_bytes + 1)
        landed = response.geturl()
    if len(content) > max_bytes:
        raise ResponseTooLarge(f"response exceeds the {max_bytes} byte read bound")
    return Fetched(content, landed)


def check_record(record, fetcher):
    """Classify one record. Returns (status, message).

    status is one of `ok`, `unlocatable`, `drift`, `error`, `empty`.
    """
    if record.get("placement") == "empty":
        return "empty", "declared provenance placement is empty, so nothing was checked"
    problem = validate(record)
    if problem:
        return "error", problem
    if record.get("status", "").lower() == "unlocatable":
        return "unlocatable", f"source not locatable: {record['source']}"
    url = record["source"]
    try:
        fetched = fetcher(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        # Degrade cleanly. A traceback here would read as a defect in this script rather
        # than as the network being down, which is the common case by a wide margin.
        # InsecureRedirect is a ValueError and arrives here, which is deliberate: a refused
        # redirect is a source this run could not honestly fetch, and that is what this
        # branch already means.
        return "error", f"could not fetch {url}: {exc}"
    # The seam takes either shape. `fetch()` returns a Fetched, carrying where the bytes
    # actually came from; an injected fetcher may return bare bytes, which means it is
    # answering as the recorded URL and has no redirect to report. Tolerated rather than
    # required, because the alternative is every test in this suite restating a field none
    # of them is about.
    if isinstance(fetched, Fetched):
        content, landed = fetched.content, fetched.url
    else:
        content, landed = fetched, url
    if not isinstance(content, (bytes, bytearray)):
        return "error", f"fetch of {url} returned {type(content).__name__}, expected bytes"
    if len(content) > MAX_FETCH_BYTES:
        # The bound is enforced again here rather than only in fetch(), because the fetcher
        # is an injected seam and the comparison is what must never see an unbounded body.
        return "error", (
            f"fetch of {url} returned {len(content)} bytes, over the "
            f"{MAX_FETCH_BYTES} byte read bound"
        )
    digest = hashlib.sha256(content).hexdigest()
    moved = landed != url
    if digest != record["sha256"]:
        # Content drift, and the landing URL is named when it differs so the reader knows
        # which bytes were digested rather than assuming the recorded source answered.
        where = f"\n      retrieved from: {landed}" if moved else ""
        return "drift", (
            f"DRIFT: {url}{where}\n"
            f"      recorded: {record['sha256']}\n"
            f"      upstream: {digest}"
        )
    if moved:
        # Location drift. The bytes are identical, so this is not a content problem, and it
        # is still drift in the thing the record pins: `source:` no longer names what
        # answered. Reporting `ok` would let a record sit on a redirect indefinitely, which
        # is the rot this script exists to surface. Named as a different kind of drift from
        # the one above rather than sharing its wording, because the remedy differs: repoint
        # the record, do not re-digest it.
        return "drift", (
            f"MOVED: {url}\n"
            f"      now answered by: {landed}\n"
            f"      content is unchanged ({digest[:12]}), so repoint the record's source "
            f"rather than re-taking the digest."
        )
    return "ok", f"up to date ({digest[:12]}) {url}"


def unreadable_note(count):
    """The paragraph that says what an unreadable file did to this run's counts."""
    noun = "file" if count == 1 else "files"
    return (
        f"{count} {noun} in scope could not be read, so every provenance record they\n"
        "carry went unchecked and the counts above are incomplete. This is reported\n"
        "rather than skipped because a narrowed count is indistinguishable from a clean\n"
        "one. A file held open by another process is the usual cause on Windows; re-run\n"
        "once it is readable.\n"
    )


def empty_placement_note(count):
    """The paragraph that names an empty placement without failing the run.

    It sits outside the four counted buckets on purpose. An empty block records no digest,
    so it can neither be up to date nor have drifted, and calling it an error would fail a
    whole run over a fence somebody had not finished writing. See unsourced_placements().
    """
    noun = "placement" if count == 1 else "placements"
    verb = "is" if count == 1 else "are"
    return (
        f"{count} declared provenance {noun} above {verb} empty, named rather than\n"
        "counted: an empty block records nothing to re-fetch, so it is most often a\n"
        "fold-in in progress rather than a defect. Fill it in per the convention in\n"
        "AGENTS.md, or remove the placement.\n"
    )


def main(argv=None, root=None, fetcher=None, out=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    out = sys.stdout if out is None else out
    root = REPO_ROOT if root is None else Path(root)
    fetcher = fetch if fetcher is None else fetcher

    records, unreadable = collect(root)
    if not records and not unreadable:
        out.write("No provenance records found. Nothing folded in is recorded, which is\n"
                  "either correct or a sign a fold-in skipped the convention in AGENTS.md.\n")
        return 0

    if "--list" in argv:
        for rel, record in records:
            state = record.get("placement") or record.get("status", "recorded")
            out.write(f"{rel}:{record['line']}  [{state}]  {record.get('source', '(no source)')}\n")
        for rel, reason in unreadable:
            out.write(f"{rel}  could not be read: {reason}\n")
        out.write(f"\n{len(records)} record(s).\n")
        if unreadable:
            # --list claims to print everything a run would contact. A file it could not
            # read may record a source that is now missing from that list.
            out.write(unreadable_note(len(unreadable)))
            return 2
        return 0

    counts = {"ok": 0, "unlocatable": 0, "drift": 0, "error": 0, "empty": 0}
    for rel, record in records:
        status, message = check_record(record, fetcher)
        counts[status] += 1
        out.write(f"{rel}:{record['line']}  {message}\n")

    # An unreadable file counts in the bucket that already means "this run could not answer
    # the question", which is what it produces, and which already exits 2.
    for rel, reason in unreadable:
        counts["error"] += 1
        out.write(f"{rel}  could not be read: {reason}\n")

    out.write(
        f"\n{counts['ok']} up to date, {counts['drift']} drifted, "
        f"{counts['unlocatable']} unlocatable, {counts['error']} error(s).\n"
    )
    if unreadable:
        out.write(unreadable_note(len(unreadable)))
    if counts["empty"]:
        out.write(empty_placement_note(counts["empty"]))
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
