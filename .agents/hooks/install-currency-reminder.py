#!/usr/bin/env python3
"""Reminder hook: tell a session when this repository's recorded install has fallen behind it.

Fires on SessionStart with source `startup`, and only in a session whose project root is a
repository holding `scripts/.install-manifest.json`. When the record says the installed
copies still match this working tree, it emits nothing at all. When they have fallen
behind, when the record carries no digest baseline to compare against, or when a shipped
skill was never recorded as installed, it says so once and names the way out. It never
blocks and it never writes.

Why this exists
---------------
Measured on the author's own machine on 2026-08-18, after ten days away: eighteen
installed skills were stale, one had never been installed at all, two placed files were
absent from both homes, and `install.py --check` reported `42 unknown`, meaning its own
currency sensor had nothing to compare against. That state had persisted for an unknown
period and nothing reported it. It was found because a review pass happened to diff two
files by hand.

Every gate stayed green throughout, correctly, because none of them looks at an install.
`run-checks.py` runs `install.py --dry-run` against a throwaway home, which proves the
installer works and says nothing about the real one. `install.py --check` decides currency
correctly but only when a person thinks to run it, and nothing prompts them. The one thing
that already runs automatically, `skill-reachability-reminder.py`, deliberately disclaims
this question in its own message and hands it back to the human. So the kit owned the
answer and could not reach it.

What it deliberately does NOT answer
------------------------------------
**The general adopter case**, where the source repository is not present. Currency is
decidable only from a machine that has the repository, because that is the only place the
comparison material exists: `install.py` records the manifest at
`scripts/.install-manifest.json` INSIDE the source checkout, and a manifest entry carries
`tool`, `name`, `target`, `mode`, `source` and `digests` with no timestamp, so an installed
skill has no back-pointer to where it came from. A session in some unrelated repository
cannot answer this at any price. Fixing that needs a new install-time surface, which is
ROADMAP Epic B item 19's question and not this hook's. The boundary is stated here because
this is the file someone would otherwise quietly widen.

Which comparison it makes, and why that one
-------------------------------------------
The recorded digests against THIS WORKING TREE, never against the installed copy. The
manifest's `digests` are a snapshot of the kit's source taken at install time, so comparing
them against the source now answers "has the kit moved since you installed", which is
exactly the staleness that went unreported for ten days. It also needs nothing but the
repository the session is already sitting in: no install home is opened and no installed
file is read.

That is a narrower question than `install.py --check`'s derived path asks, and the
difference is worth stating rather than blurring. `--check` compares the INSTALLED tree
against the source, so it also catches a file the adopter edited after installing. This
hook cannot see that, and does not claim to. The two agree whenever the installed copy is
untouched, which is the case the ten-day gap was made of.

Cost, which is the thing to get right
-------------------------------------
This runs at every session start, so the manifest is read first and its absence ends the
run. That is the common case, since most sessions are not in this repository, and it costs
one `is_file()` per ancestor directory and nothing else: no skill is enumerated, no
frontmatter is parsed, and nothing is digested. Only once a manifest is present is any
digesting justified, and even then the comparison is recorded-against-source rather than
re-deriving both sides.

Vocabulary
----------
The six verdicts in `VERDICTS` are `install.py --check`'s, not a second set invented for
the same idea, and `tests/test_hooks_currency.py` fails if either side gains a word the
other lacks. Only three of them are worth waking a session for, in `REPORTING_VERDICTS`.
`ok` and `linked` mean there is nothing to say. `revised` is the adopted rules lens whose
upstream moved, and `--check` already treats that as exit 0 with the adopter's copy left
alone, so firing on it every session would be crying wolf about a file the adopter was
invited to own.

Why a new hook rather than an extension of the reachability one
---------------------------------------------------------------
The module contract is one hook, one job, obvious from the docstring, and the reachability
hook's published message explicitly disclaims currency. Folding this in would make that
message wrong, and would give one file two firing conditions with very different costs:
reachability is a directory-name match, currency reads and digests files. Both fire on
SessionStart and stay separate.

Why a reminder and not a gate
-----------------------------
A stale install is a condition a person should see, not one that should stop their work.
An adopter may be deliberately running an older copy, and blocking that would be a false
refusal in their repository rather than ours. This reports and leaves the decision alone,
which is the principle the autonomy rules module names: detect and report, never rewrite.
Re-installing is the human's call; this hook never runs the installer.

Contract
--------
stdin   a JSON object with `hook_event_name`, `source`, and optionally `cwd`
stdout  one JSON object, or nothing
exit    always 0

Any malformed input, and any unexpected failure, exits 0 silently. A guardrail that breaks
a session because it could not parse its own payload is worse than no guardrail.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

# Only a genuinely new session. `resume`, `clear`, `compact`, and `fork` all continue a
# session whose agent has already been told. The harness matcher filters this too; this is
# the precise check, per the module's two-stage filtering rule.
FIRING_SOURCES = {"startup"}

# Where install.py keeps the record, relative to the repository root. Mirrored rather than
# imported, because the hooks contract forbids importing from this repository.
MANIFEST_SUBPATH = Path("scripts") / ".install-manifest.json"

# Where this kit's skill sources live, for the never-installed question below.
SKILLS_SUBPATH = Path(".agents") / "skills"

# The one placed module an adopter is invited to rewrite, matched by the entry name
# install.py records for it. Mirrors `ADOPTED_ENTRY_NAMES` there.
ADOPTED_ENTRY_NAMES = frozenset({"rules"})

# install.py --check's vocabulary, borrowed whole rather than reinvented. A test pins this
# against the counts install.py's `check()` prints, in both directions.
VERDICTS = frozenset({"ok", "linked", "revised", "diverged", "unknown", "error"})

# The subset worth waking a session for. See the docstring for why `revised` is not here.
REPORTING_VERDICTS = ("diverged", "unknown", "error")

# Mirrors install.py's frontmatter reading for `metadata.status`. A draft skill is
# deliberately not installed, so counting one as never-installed would make this hook fire
# on a perfectly correct install, and a reminder that does that is uninstalled within a
# week. `tests/test_hooks_currency.py` asserts the two readers agree on every skill this
# repository ships, rather than trusting that they do.
DRAFT_STATUS = "draft"
METADATA_KEY_RE = re.compile(r"^metadata:\s*$")
STATUS_FIELD_RE = re.compile(r"^\s+status:\s*(\S.*?)\s*$")

# What this hook will digest before declining. A recorded `source` is a path read out of a
# manifest, not one this hook derived, and this runs at every session start, so an entry
# naming a large directory would turn every start into a full recursive read of it. Set far
# above any module the kit ships (the largest is the hooks directory) so a correct install
# can never reach them: the failure direction that costs more is a cap firing on a real
# install, since `error` is a reporting verdict.
MAX_DIGEST_FILES = 2000
MAX_DIGEST_BYTES = 64 * 1024 * 1024

# How many names to spell out before summarising. A reminder long enough to scroll is one
# an agent learns to skip, and then says nothing on the start that mattered.
MAX_NAMED = 6

# The banner leads every firing case and is true in all of them: stale, no baseline,
# unreadable source, and never installed all mean the same thing to the reader, which is
# that the copies they are working with are not known to match this tree.
BANNER = "INSTALLED COPIES OF THIS KIT ARE NOT KNOWN TO BE CURRENT"

REMEDY = (
    "Run `python scripts/install.py --check` for the full per-entry report, then "
    "`python scripts/install.py` to refresh. Nothing here rewrites anything, and nothing "
    "else will mention this again."
)


def _digestable(rel: Path, path: Path) -> bool:
    """Whether a file beneath a placed module is part of that module.

    Mirrors the ignore list install.py copies with. Digesting a byte-cache would report a
    file missing from every install, since a source directory grows a `__pycache__` as
    soon as anything imports it and the copy deliberately has none.
    """
    return path.suffix != ".pyc" and "__pycache__" not in rel.parts


class TreeTooLarge(Exception):
    """A recorded source is too big to digest at session start.

    Not an error about the tree: it is this hook declining to spend a session start on it.
    `classify()` turns it into the `error` verdict, which already means "could not be
    compared at all" and is already in `REPORTING_VERDICTS`.
    """


def digest_tree(root: Path, max_files: int = None, max_bytes: int = None) -> dict:
    """SHA256 per file beneath `root`, keyed by its POSIX-relative path.

    Byte-for-byte the same derivation install.py records with, because a different one
    would disagree with the baseline it is being compared against. Bytes, never decoded
    text, and POSIX-relative keys so a record written on Windows reads on macOS and Linux.

    Bounded, unlike install.py's copy, and the asymmetry is the point (`chore-0082`). That
    one runs because a person invoked the installer and can watch it. This one runs at
    **every session start**, on a path read out of a manifest rather than derived, and
    `find_manifest()` walks upward, so a manifest at any ancestor of the session's working
    directory decides what gets read. Past either bound this raises rather than finishing,
    so a pathological entry costs a stat walk instead of a full recursive read.

    The bounds are set far above any real module: the largest the kit ships is the hooks
    directory at a handful of files and tens of kilobytes, so a correct install cannot reach
    them. That direction matters more than the exact numbers, because `error` is a reporting
    verdict and a cap set below a real install would fire this hook on every session start,
    which is the crying-wolf failure its own docstring says gets it uninstalled in a week.
    """
    # Read at call time rather than bound as default arguments. A default is evaluated once
    # when the function is defined, so the constants above would be untunable and, worse,
    # untestable: a test raising or lowering them would change the name and not the bound.
    max_files = MAX_DIGEST_FILES if max_files is None else max_files
    max_bytes = MAX_DIGEST_BYTES if max_bytes is None else max_bytes
    digests = {}
    if not root.is_dir():
        return digests
    seen_bytes = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if not _digestable(rel, path):
            continue
        if len(digests) >= max_files:
            raise TreeTooLarge(f"more than {max_files} files under {root}")
        # Sized before reading, so an enormous single file is refused rather than held in
        # memory. `stat` on a file that vanished mid-walk is an OSError, which `classify()`
        # already treats as `error`.
        seen_bytes += path.stat().st_size
        if seen_bytes > max_bytes:
            raise TreeTooLarge(f"more than {max_bytes} bytes under {root}")
        digests[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def find_manifest(start: Path):
    """The nearest `scripts/.install-manifest.json` at or above `start`, or None.

    Walks upward rather than checking `start` alone, because a harness may report a
    subdirectory as the session's working directory and a hook that answers correctly only
    from the repository root is the "registered and inert" failure this module has already
    been bitten by twice. The walk is stats only, so the no-manifest path stays free.
    """
    for directory in (start, *start.parents):
        candidate = directory / MANIFEST_SUBPATH
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            return None
    return None


def is_draft(skill_dir: Path) -> bool:
    """Whether a skill marks itself `metadata.status: draft`, as install.py reads it.

    Only the frontmatter's `metadata:` block counts, so a `status:` line written anywhere
    in the body is prose and not a marker. Several skills here discuss draft status in
    their bodies. An unreadable or unrecognised skill reads as shipped, matching
    install.py, so the error direction over-reports a real skill rather than silently
    dropping one.
    """
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return False
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    inside = False
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        if inside:
            if raw.strip() and not raw[:1].isspace():
                inside = False  # a new top-level key ended the metadata block
            else:
                m = STATUS_FIELD_RE.match(raw)
                if m:
                    return m.group(1).strip().strip('"').strip("'").lower() == DRAFT_STATUS
        if not inside and METADATA_KEY_RE.match(raw):
            inside = True
    return False


def classify(entry, cache=None) -> str:
    """One manifest entry's verdict, in install.py --check's vocabulary.

    The order of the branches mirrors `_check_entry` there, including the falsiness test on
    `digests`: a map that is present but empty is no more of a baseline than a missing one,
    and treating it as valid is how a hand-edited manifest once reported a clean verdict for
    an entry nothing had been recorded for.

    `cache` memoises digested sources across entries. One skill installed for two tools is
    two entries naming one source directory, so without it every source in a two-tool
    install is read twice at every session start.
    """
    if not isinstance(entry, dict):
        return "error"
    recorded = entry.get("digests")
    if not recorded:
        return "unknown"

    target = Path(entry.get("target") or "")
    source = Path(entry.get("source") or "")
    try:
        if not (target.exists() or target.is_symlink()):
            return "diverged"
        if not source.is_dir():
            return "error"
        if target.is_symlink() and target.resolve() == source.resolve():
            # It cannot be stale, because it IS the source. Read from the filesystem
            # rather than from the recorded `mode`, since a copy can replace a link
            # between runs, which is the same call install.py makes.
            return "linked"
        key = str(source)
        if cache is not None and key in cache:
            current = cache[key]
        else:
            current = digest_tree(source)
            if cache is not None:
                cache[key] = current
    except (OSError, TreeTooLarge):
        # `TreeTooLarge` is this hook declining to spend a session start on a recorded path
        # that is too big to digest, not a fault in the tree. `error` already means "could
        # not be compared at all" and is already reported, so it needs no seventh verdict
        # (chore-0082).
        return "error"

    if current == recorded:
        return "ok"
    # An adopted lens the adopter was invited to rewrite. The kit's copy having moved is
    # information, not a problem, and install.py exits 0 on it.
    return "revised" if entry.get("name") in ADOPTED_ENTRY_NAMES else "diverged"


def unrecorded_skills(project_root: Path, recorded_names) -> list:
    """Shipped skills in this tree that no manifest entry names, sorted.

    Drafts are excluded because they are deliberately not installed. A skill left out by a
    narrow `--profile` is NOT excluded and will be listed, which is honest but noisy for an
    adopter who chose that profile on purpose, so the message names the profile case as one
    of the two readings.
    """
    try:
        candidates = sorted(p for p in project_root.joinpath(SKILLS_SUBPATH).iterdir()
                            if (p / "SKILL.md").is_file())
    except OSError:
        return []
    return [p.name for p in candidates
            if p.name not in recorded_names and not is_draft(p)]


def _listing(label: str, names) -> str:
    shown = ", ".join(names[:MAX_NAMED])
    if len(names) > MAX_NAMED:
        shown += f", and {len(names) - MAX_NAMED} more"
    return f"{label}: {shown}."


def report(manifest, project_root: Path):
    """The reminder text for this manifest, or None when there is nothing to say."""
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        return None

    found = {verdict: [] for verdict in VERDICTS}
    recorded_names = set()
    cache = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name"):
            recorded_names.add(entry["name"])
        verdict = classify(entry, cache)
        name = entry.get("name") if isinstance(entry, dict) else None
        found[verdict].append(name or "(unnamed entry)")

    # Distinct names, because one skill installed for two tools is one thing to fix and
    # naming it twice reads like two.
    stale = sorted(set(found["diverged"]))
    baseless = sorted(set(found["unknown"]))
    unreadable = sorted(set(found["error"]))
    missing = unrecorded_skills(project_root, recorded_names)

    if not (stale or baseless or unreadable or missing):
        # Silence is the whole report here, and it is a claim: the record says these copies
        # still match this tree. A hook that speaks on every start becomes a line an agent
        # learns to skip, and then says nothing on the start that mattered.
        return None

    parts = [
        f"{BANNER}: this repository holds an install record, and it no longer agrees with "
        f"the working tree. Nothing else in this session will mention it."
    ]
    if stale:
        parts.append(_listing(
            f"{len(stale)} installed copy/copies have gone stale, because the kit's own "
            f"copy has changed since they were installed", stale))
    if baseless:
        parts.append(_listing(
            f"{len(baseless)} entry/entries carry no digest baseline, so the currency "
            f"check is INOPERATIVE for them until re-installing records one, and their "
            f"state is unknown rather than current", baseless))
    if unreadable:
        parts.append(_listing(
            f"{len(unreadable)} entry/entries could not be compared at all, because the "
            f"source they name is gone or unreadable", unreadable))
    if missing:
        parts.append(_listing(
            f"{len(missing)} shipped skill(s) are in this tree with no install record, so "
            f"they were never installed, or you installed a profile that excludes them",
            missing))
    parts.append(REMEDY)
    return " ".join(parts)


def evaluate(payload, root=None):
    """Return the hook's output object for this payload, or None to stay silent.

    `root` is the injectable seam, and it is the project root rather than the home the
    sibling reachability hook takes, because this hook's whole question lives in the source
    repository and it never opens an install home. A test drives it without a real
    checkout by pointing this at a fixture tree.
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "SessionStart":
        return None
    if payload.get("source") not in FIRING_SOURCES:
        return None

    if root is None:
        cwd = payload.get("cwd")
        root = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
    root = Path(root)

    # The cost gate, and it is first on purpose: no manifest means no question to answer,
    # which is every session outside this repository. Nothing below this line runs.
    manifest_path = find_manifest(root)
    if manifest_path is None:
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # An unreadable or malformed record is install.py's problem to report, not a
        # reason to shout at a session that may have nothing to do with it.
        return None

    text = report(manifest, manifest_path.parent.parent)
    if text is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }


def main(stdin=None, stdout=None) -> int:
    """Read one payload, emit at most one object. `stdin`/`stdout` are injectable so the
    behavior is reachable from a test without spawning a subprocess."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.load(stdin)
    except Exception:
        return 0
    try:
        out = evaluate(payload)
        if out is not None:
            stdout.write(json.dumps(out))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
