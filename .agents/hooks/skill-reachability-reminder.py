#!/usr/bin/env python3
"""Reminder hook: tell a session at startup when none of this kit's skills is reachable.

Fires on SessionStart with source `startup`. If at least one skill OF THIS KIT is
reachable at project or user scope, it emits nothing at all. If none is, it says so once
and names the way out. It never blocks and it never writes.

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

Whose skills it found
---------------------
It answers that one, by name, and the first version did not. `_has_skill()` counted ANY
directory holding a `SKILL.md`, while `cloud-executable.md` defines reachability over
"kit skill" directories, so a machine carrying somebody else's library satisfied the code
and not the contract. That is not an edge case on the platform this hook was written for:
a stock cloud container ships its own populated `~/.claude/skills`, and a live session on
2026-08-08 found 24 skills there, none of them from this kit, with this hook silent
(`bug-0021`). The one state the hook exists to report was the state it could not report.

The recognition is a name list, `KIT_SKILL_NAMES` below, and the choice is worth the
paragraph because the next reader will ask. Two alternatives were rejected:

- **Read `install.py`'s manifest.** Authoritative, and it makes a portable hook depend on
  one repository's script layout, which the currency section above already rejects for the
  same reason. Worse here: the manifest lives in the checkout that ran the installer, so a
  cloud clone has none, which is exactly the case being answered.
- **Have the installer place a marker and look for that.** Retroactively wrong. Every
  install that already exists has no marker, so the hook would cry wolf at each of them
  until it was re-run, and a reminder that fires on a correct install is uninstalled inside
  a week.

A name list goes stale, which is the standing objection to it. A hook cannot derive the
catalog at runtime without importing from this repository, forbidden by the hooks module
contract, but the repository CAN check the constant against what it ships, and
`tests/test_hooks_reachability.py` asserts the two are equal. Renaming or dropping a skill
fails that test by name. The objection is real and it is answered at test time, which is
the only place a standalone hook could ever have it answered.

What the name list buys is bounded, and honestly: it recognises a NAME, not a provenance.
A foreign library shipping a skill called `doc-sync` would silence this hook. That is the
cheap direction to be wrong in for a reminder, per the hooks module contract: the cost is
one missing paragraph, against a false alarm that costs the adopter their trust in it.

It still cannot tell whether the kit skill it found is the kit's copy or a fork of it.
That needs the manifest, which is `--check`'s business, and the message says so.

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

# A discovery directory is one a harness actually LOADS skills from. That is not the same
# as a directory containing skills, and conflating the two made this hook inert in the one
# repository that ships it.
#
# The first version checked both subpaths at both scopes, reasoning that which directory a
# harness reads is the harness's business. It is not: `.agents/skills` is opencode's
# USER-scope directory, and no harness discovers project-scope skills there. This kit
# commits its own sources to `.agents/skills/`, so at project scope that check found
# twenty SKILL.md files, called them reachable, and stayed silent, in a fresh clone with
# nothing installed. Exactly the case the hook exists for.
#
# Found by the first live cloud run (2026-08-07), which reported no message at startup.
# Every unit test had missed it because all of them build synthetic trees; none had ever
# run the hook against this repository's own root. `.agents/hooks/README.md` warns about
# precisely this: a guardrail that cannot fire in the repository that ships it is one
# nobody has ever seen work.
#
# The contract was right and the code was wrong. `cloud-executable.md`'s Proposed Surface
# says "the repository's project-scope discovery directory", singular, "or at any
# user-scope discovery directory install.py targets". This now implements that sentence.

# Claude Code's project-scope directory, and the only one. Deliberately not a tuple of
# convenience: adding `.agents/skills` back here reintroduces the defect above.
PROJECT_SKILL_SUBPATHS = (
    Path(".claude") / "skills",
)

# The two directories install.py places into, both relative to the user's home.
USER_SKILL_SUBPATHS = (
    Path(".claude") / "skills",
    Path(".agents") / "skills",
)

# The skills this kit ships, which is what "kit skill" in the contract means. Every one
# of them installs under its own directory name, so a name match at a discovery directory
# is the reachability question answered.
#
# Kept in sync by a test rather than by discipline: see the docstring above, and
# `test_the_recognised_names_are_exactly_the_skills_this_kit_ships`. Adding, renaming, or
# removing a skill means editing this constant in the same commit, and the test suite says
# so by name when you do not. ONE match is enough, so an adopter running `--profile core`
# with three skills installed is reachable and hears nothing.
KIT_SKILL_NAMES = frozenset({
    "agent-handoff",
    "agent-observatory",
    "doc-author",
    "doc-revise",
    "doc-sync",
    "fix-batch",
    "house-review",
    "human-handoff",
    "init-worktracking",
    "new-task",
    "pr-describe",
    "project-bootstrap",
    "reconcile-worktrees",
    "review-depth",
    "spec-author",
    "spec-conformance",
    "spec-plan-readiness",
    "spec-quality",
    "systematic-debugging",
    "test-author",
    "test-quality",
    "verifier-agent",
})

# The banner keeps the exact words `NO SKILLS REACHABLE` at its head on purpose, and the
# qualifier follows them. `cloud-executable.runbook.md` tells a person to look for a
# message beginning with that phrase, and the proof run it governs has not happened yet, so
# narrowing the check must not quietly retarget the string that run is waiting for.
REPORT = (
    "NO SKILLS REACHABLE FROM THIS KIT: this session started with none of this kit's "
    "skills found at either project scope or user scope, so any skill-driven workflow "
    "this repository documents is unavailable right now and nothing else will say so. "
    "Other skills may "
    "well be loaded; none of them is one of these. Work that assumes a skill is loaded "
    "will silently proceed without it. If skills are expected here, install them (for "
    "this kit: `python scripts/install.py`) and start a new session. If you are working "
    "deliberately without them, ignore this. Note the limits of this check: it matches "
    "skill directories by name, so it confirms they exist, not that they are current or "
    "that they are this kit's copies. Run `python scripts/install.py --check` for that."
)


def _has_kit_skill(directory: Path) -> bool:
    """True when `directory` holds at least one skill belonging to this kit.

    A skill is a directory containing SKILL.md, which is the one structural fact every
    harness in scope agrees on. A KIT skill is one of those whose directory name is in
    `KIT_SKILL_NAMES`: counting any SKILL.md at all is the wider question the contract
    does not ask, and answering it made this hook silent in front of a foreign library.

    An empty discovery directory does not count, and neither does an empty directory
    carrying a kit skill's name: `--uninstall` leaves the parent behind, so treating mere
    existence as reachability would report success for a home whose skills were just
    removed.
    """
    try:
        if not directory.is_dir():
            return False
        for child in directory.iterdir():
            if child.name in KIT_SKILL_NAMES and (child / "SKILL.md").is_file():
                return True
    except OSError:
        # An unreadable directory is not a reachable one, and is not worth crashing over.
        return False
    return False


def reachable(project_root: Path, home: Path) -> bool:
    """Whether any of this kit's skills is reachable from either scope.

    The two scopes are checked against different directory sets on purpose; see the
    constants above for why collapsing them is the defect this hook shipped with.
    """
    for sub in PROJECT_SKILL_SUBPATHS:
        if _has_kit_skill(project_root / sub):
            return True
    for sub in USER_SKILL_SUBPATHS:
        if _has_kit_skill(home / sub):
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
