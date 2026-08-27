#!/usr/bin/env python3
"""Run every gate that decides whether a change to this repository is acceptable.

One command, one exit code, no flags. This exists because until now the seven gates
lived only as seven separate steps in .github/workflows/checks.yml, so the only ways to
get the answer were to push and read CI, or to run seven commands by hand and remember
all seven. Measured 2026-08-07: the 97 acceptance chains across .tasks/ and .tasks/done/
run one, two, three, or five commands, and none of them runs the seven.

For a person that is friction. For an agent working unattended it is disqualifying: it
cannot push and wait for someone to read the result, and it has no way to know that the
three commands its task file named are not the seven that gate the merge.

    python scripts/run-checks.py

Exit codes, and why 2 outranks 1
--------------------------------
    0   every gate passed
    1   at least one gate ran and failed
    2   at least one gate could not run at all

The precedence is the same one install.py --check and check-provenance.py already use.
A gate that could not execute is not a gate that answered "no": it means the report
itself is incomplete, and that outranks a clean "no" because a reader who treats it as
one is reasoning from an answer nobody produced.

What this command is NOT
------------------------
Passing here is NECESSARY BUT NOT SUFFICIENT. CI runs three operating systems by two
Python versions; any single run of this covers one of those six cells. The summary says
so on every run rather than leaving the reader to remember it.

Every gate runs, even after one fails
-------------------------------------
Deliberately not fail-fast. An unattended agent gets one round trip, and a report naming
only the first failure spends another one to find the second.

What the report carries per gate
--------------------------------
A status word, the gate's name, and then one indented line of the gate's own output
saying what it covered. The coverage line is there because without it a status word is
not falsifiable: measured 2026-08-22 over a copy of this repository with the skills,
the tests, and the task files removed, six of the seven gates exited 0 having examined
nothing, and the report was byte-for-byte the report of a full clean run (bug-0045).
Only `doc links` noticed, and only incidentally.

The counts themselves are not new. Every gate already prints one, each added by a task
that had just been burned by its absence; this command captured them and threw them away
on any gate that passed. See `coverage_line()` for which line is chosen and why.

Standard library only.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The throwaway home the install gates use. Chosen to match what checks.yml already
# used, and gitignored via `.tmp/`. Nothing outside it is ever touched: `--uninstall` is
# scoped to the home it is given (bug-0003), which is what makes running this on a
# development machine safe for a real installation.
THROWAWAY_HOME = "./.tmp/zen-home"

PY = sys.executable


class Gate:
    """One named gate: a sequence of commands that must all succeed.

    `cleanup` runs after `commands` whether they passed or failed, and exists for one
    reason: the install gate places files, and a run that fails midway must not leave a
    populated throwaway home behind. Its failure is reported but does not by itself fail
    the gate, because a cleanup that could not run says nothing about the change under
    test.
    """

    def __init__(self, name, commands, cleanup=None):
        self.name = name
        self.commands = commands
        self.cleanup = cleanup


def gates():
    """The seven gates, in the order checks.yml ran them.

    A function rather than a module constant so a test can hold the canonical list
    without depending on import-time state, and so the interpreter is resolved at call
    time rather than at import.
    """
    install_home = ["--home", THROWAWAY_HOME]
    return [
        Gate("lint skills", [[PY, "scripts/validate-skills.py"]]),
        Gate("test suite",
             [[PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]]),
        Gate("backlog", [[PY, ".tasks/validate.py", "--strict"]]),
        Gate("adapters dry run", [[PY, "scripts/build-adapters.py", "--dry-run"]]),
        Gate("install dry run", [[PY, "scripts/install.py", "--dry-run"] + install_home]),
        # Exercises the real placement path, including POSIX symlink mode, which the dry
        # run does not cover. Running it twice proves idempotence; the uninstall proves
        # the manifest can find what it created.
        #
        # `--with-hooks` is here by a decision recorded in chore-0067, not by habit. It
        # costs this gate the six files of .agents/hooks/ written into the gitignored
        # throwaway home per tool and removed again by the cleanup below, which needed no
        # change: `--uninstall` reverses every recorded target beneath the home it is
        # given, and the hooks placement is a recorded target. What it buys is the only
        # module the kit runs inside an adopter's session being placed at least once per
        # CI cell, in the real default mode for that platform, which is symlink on four of
        # the six. The rejected option was leaving the flag off and relying on the
        # component tests in tests/test_install.py alone: those run in-process and, off a
        # POSIX host or on an account that cannot symlink, never take the link branch at
        # all, so the saving would have been six temporary files against a placement path
        # that still ran on no cell.
        Gate("install cycle",
             [[PY, "scripts/install.py", "--with-hooks"] + install_home,
              [PY, "scripts/install.py", "--with-hooks"] + install_home],
             cleanup=[PY, "scripts/install.py", "--uninstall"] + install_home),
        # Calls the link rule in .tasks/validate.py rather than restating it. An inline
        # copy of that rule drifted once already (chore-0029). Globbed rather than
        # listed, because a hardcoded list silently excludes every new document.
        Gate("doc links",
             [[PY, ".tasks/validate.py", "--links",
               "*.md", ".github/**/*.md", "docs/**/*.md"]]),
    ]


def _script_of(command):
    """The repository-relative script a command runs, when it names one.

    Returns None for a command that runs a module (`-m unittest`) rather than a file,
    since there is then no path to check.
    """
    if len(command) < 2 or command[1].startswith("-"):
        return None
    return command[1]


def _run(command, runner=None):
    """Execute one command. Returns (ok, unrunnable, output).

    The missing-script check happens before the call, and it is not belt-and-braces: a
    missing script is the most likely real cause of a gate that cannot run, and
    subprocess does NOT raise for it. `subprocess.run([sys.executable, "gone.py"])`
    starts the interpreter successfully and exits non-zero, so the whole
    could-not-run branch would be dead in exactly the case it exists for, and the gate
    would be reported as `failed` at exit 1 instead of `unrunnable` at exit 2.

    Found by exercising the branch against a real subprocess after a stubbed test of it
    passed. The stub raised OSError because that is what the code expected, which is the
    failure mode where a test confirms an assumption instead of checking it.
    """
    script = _script_of(command)
    if script is not None and not (REPO_ROOT / script).exists():
        return False, True, f"could not run: {script} does not exist"
    runner = subprocess.run if runner is None else runner
    try:
        done = runner(command, cwd=str(REPO_ROOT), capture_output=True, text=True)
    except OSError as exc:
        # The interpreter itself could not be started. Rarer than the case above, and
        # still distinct from a command that ran and returned non-zero.
        return False, True, f"could not run: {exc}"
    output = (done.stdout or "") + (done.stderr or "")
    return done.returncode == 0, False, output


def run_gate(gate, runner=None):
    """Run one gate. Returns (status, output, cleanup_ok).

    `cleanup_ok` is reported separately from `status` rather than folded into it. A
    cleanup that fails leaves files behind, which a reader needs to know about, but it
    says nothing about whether the change under test is good, so it must not turn a
    passing gate into a failing one. Keeping them separate is what lets the report say
    both things at once.
    """
    collected = []
    status = "ok"
    for command in gate.commands:
        ok, unrunnable, output = _run(command, runner)
        collected.append(output)
        if unrunnable:
            status = "unrunnable"
            break
        if not ok:
            status = "failed"
            break
    cleanup_ok = True
    if gate.cleanup is not None:
        ok, _unrunnable, output = _run(gate.cleanup, runner)
        if not ok:
            cleanup_ok = False
            collected.append("cleanup did not complete:\n" + output)
    return status, "\n".join(c for c in collected if c.strip()), cleanup_ok


def coverage_line(output):
    """The one line of a gate's own output to show beside its status. Display only.

    Every gate here already prints what it covered, and each of those counts was added
    by a task that had just been burned by its absence: `validate-skills.py`'s skill and
    supporting-file counts, `.tasks/validate.py`'s `Checked N task files`, `install.py`'s
    placed count and description budget, and `--links`'s document count. Until bug-0045
    this aggregator captured all of them and printed none, so seven gates passing over a
    full tree and seven gates passing over an empty one were byte-identical reports.

    The rule is the last non-blank line that contains a digit, falling back to the last
    non-blank line when no line has one, and to `(no output)` when a gate said nothing.

    Why a digit and not simply the last line, which is the cheaper rule bug-0045
    suggested trying first: it was measured against all seven real gates on 2026-08-22
    and it is uninformative for three of them. The test suite's last line is unittest's
    bare `OK`, which is identical over 482 tests and over zero, that being the exact
    failure this function exists to remove; both install gates end on `install.py`'s
    "Run ... --check" advice line, which says nothing about what was placed. The digit
    rule picks `Ran 482 tests in 8.395s` and `Description budget: ...` instead. It needs
    no per-gate knowledge and no name-to-regex table, which the task's implementation
    notes rule out as a second source of truth that drifts the first time a gate rewords
    its summary (the failure `chore-0029` recorded for a copied link rule).

    The fallback matters as much as the rule. A gate declining to look says so in words
    and no digits: `validate-skills.py`, `install.py`, and `build-adapters.py` all print
    "No skills found under <dir>." over an empty tree, so the fallback surfaces that
    sentence verbatim, which is the whole finding of bug-0045.

    This is display, never a verdict. The exit code stays the gates' own, and nothing
    here parses the text for anything but which line to echo.
    """
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "(no output)"
    for line in reversed(lines):
        if any(character.isdigit() for character in line):
            return line
    return lines[-1]


def run_all(the_gates=None, runner=None, out=None):
    """Run every gate and report. Returns the exit code.

    `the_gates` and `runner` are injectable so the aggregation logic is reachable from a
    test without executing seven real gates, which would make the failure and
    could-not-run branches untestable.
    """
    the_gates = gates() if the_gates is None else the_gates
    out = sys.stdout if out is None else out

    counts = {"ok": 0, "failed": 0, "unrunnable": 0}
    notes = []
    for gate in the_gates:
        status, output, cleanup_ok = run_gate(gate, runner)
        counts[status] += 1
        suffix = "" if cleanup_ok else "  (cleanup did not complete)"
        out.write(f"{status:11} {gate.name}{suffix}\n")
        # Every gate, passing or not, carries its own account of what it covered on an
        # indented second line. Unconditional on purpose: the passing case is the one
        # bug-0045 found silent, and a status word alone cannot distinguish a gate that
        # checked the whole tree from one that found nothing to check and said so.
        out.write(f"{'':11} {coverage_line(output)}\n")
        # A passing gate whose cleanup failed still needs its output shown, or the
        # leftover files are announced in one word and explained nowhere.
        if status != "ok" or not cleanup_ok:
            notes.append((gate.name, status, output))

    for name, status, output in notes:
        out.write(f"\n----- {name}: {status} -----\n{output.rstrip()}\n")

    out.write(f"\n{counts['ok']} passed, {counts['failed']} failed, "
              f"{counts['unrunnable']} could not run.\n")
    out.write(f"Ran on {platform.system()}, Python {platform.python_version()}. "
              f"CI runs 3 operating systems x 2 Python versions, so this is one of six "
              f"cells: passing here is necessary but not sufficient.\n")

    if counts["unrunnable"]:
        return 2
    return 1 if counts["failed"] else 0


def main(argv=None, the_gates=None, runner=None, out=None) -> int:
    """Entry point. Takes no options; `argv` exists only to reject any that are passed."""
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        out = sys.stdout if out is None else out
        out.write("run-checks.py takes no arguments; it runs every gate, always.\n")
        return 2
    return run_all(the_gates, runner, out)


if __name__ == "__main__":
    raise SystemExit(main())
