#!/usr/bin/env python3
"""Reminder hook: tell a session at startup when no skills are reachable.

Fires on SessionStart with source `startup`. If at least one skill is reachable at
project or user scope, it emits nothing at all. If none is, it says so once and names
the way out. It never blocks and it never writes.

Why this exists
---------------
A session can start in a repository with none of its skills loaded, do a full piece of
work, and never mention it. The output looks exactly like output produced with the
skills; nothing distinguishes them. That is the same silent-wrong-result shape this kit
keeps getting bitten by: an installed copy gone stale with no signal, and a hook that was
registered and inert.

It bites hardest in a cloud session, which sees only what is committed. This kit installs
its skills to a user-scope directory, so a fresh clone on a fresh machine has none of
them, and the repository that builds the kit is the one place the kit is reliably absent.

Why a reminder and not a gate
-----------------------------
Because a careful person can disagree with it. An adopter may deliberately work here
without the skills installed, and blocking that would be a false refusal in their
repository rather than ours. So this reports and leaves the decision alone, which is the
principle the autonomy rules module names: detect and report, never rewrite.

What it does NOT answer
-----------------------
Whether what it reached is CURRENT. This checks that skill directories exist, not that
they match any source, so its silence means reachable and never means up to date. A
copied skill is a snapshot taken at install time, and a stale one is a valid skill that
passes every validator and reads correctly. `install.py --check` is the tool that answers
currency, and it is deliberately not called here: walking a digest of every installed file
would put a per-file read in front of every session start, and would make a portable hook
depend on one repository's script layout.

It also cannot tell whose skills it found. Distinguishing one library's skills from an
adopter's own needs the install manifest, which is `--check`'s business and not this
hook's. Reported honestly in the message rather than overclaimed.

No environment detection
------------------------
There is deliberately no check for whether this is a cloud session, a container, or a
laptop. The three harnesses this module targets share no such signal, so detecting it
would mean one implementation per harness for a single question whose answer does not
depend on it. Two sessions with the same reachability produce byte-identical output.

Contract
--------
stdin   a JSON object with `hook_event_name` and `source`
stdout  one JSON object, or nothing
exit    always 0

Any malformed input, and any unexpected failure, exits 0 silently. A guardrail that
breaks a session because it could not parse its own payload is worse than no guardrail.
"""
import json
import sys
from pathlib import Path

# Only a genuinely new session. `resume`, `clear`, `compact`, and `fork` all continue a
# session whose agent has already been told, so firing there would repeat a message that
# was already delivered. The harness matcher filters this too; this is the precise check,
# per the module's two-stage filtering rule.
FIRING_SOURCES = {"startup"}

# The discovery directories skills are placed in, relative to a scope root. Both are
# checked at both scopes, because which one a harness reads is the harness's business and
# the question here is only whether anything is reachable at all.
SKILL_SUBPATHS = (
    Path(".claude") / "skills",
    Path(".agents") / "skills",
)

REPORT = (
    "NO SKILLS REACHABLE: this session started with no skill directory found at either "
    "project scope or user scope, so any skill-driven workflow this repository documents "
    "is unavailable right now and nothing else will say so. Work that assumes a skill is "
    "loaded will silently proceed without it. If skills are expected here, install them "
    "(for this kit: `python scripts/install.py`) and start a new session. If you are "
    "working deliberately without them, ignore this. Note the limits of this check: it "
    "confirms that skill directories exist, not that they are current or that they are "
    "the ones you expect. Run `python scripts/install.py --check` for that."
)


def _has_skill(directory: Path) -> bool:
    """True when `directory` holds at least one skill.

    A skill is a directory containing SKILL.md, which is the one structural fact every
    harness in scope agrees on. An empty discovery directory does not count: `--uninstall`
    leaves the parent behind, so treating its existence as reachability would report
    success for a home whose skills were just removed.
    """
    try:
        if not directory.is_dir():
            return False
        for child in directory.iterdir():
            if (child / "SKILL.md").is_file():
                return True
    except OSError:
        # An unreadable directory is not a reachable one, and is not worth crashing over.
        return False
    return False


def reachable(project_root: Path, home: Path) -> bool:
    """Whether any skill is reachable from either scope."""
    for root in (project_root, home):
        for sub in SKILL_SUBPATHS:
            if _has_skill(root / sub):
                return True
    return False


def evaluate(payload, home=None):
    """Return the hook's output object for this payload, or None to stay silent."""
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "SessionStart":
        return None
    if payload.get("source") not in FIRING_SOURCES:
        return None

    cwd = payload.get("cwd")
    project_root = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
    home = Path.home() if home is None else home

    if reachable(project_root, home):
        # Silence is the whole report here. A hook that speaks on every start becomes a
        # line an agent learns to skip, and then says nothing on the start that mattered.
        return None

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": REPORT,
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
