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
import re
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

    `check` is the second gate kind, added by `chore-0072`: an in-process callable
    returning `(ok, report)` instead of a list of commands. Every other gate here shells
    out to a script that a person can also run alone, and that remains the right default;
    this one exists because `chore-0072` owns exactly two files, this one and its test,
    so a gate with a script of its own would have been a third. The cost is named rather
    than hidden: an in-process gate cannot be run standalone, and it is the one gate whose
    crash could take the aggregator down with it, which `run_gate` handles explicitly.
    A gate carries commands or a check, never both.
    """

    def __init__(self, name, commands, cleanup=None, check=None):
        self.name = name
        self.commands = commands
        self.cleanup = cleanup
        self.check = check


# The ROADMAP bookkeeping check (chore-0072). Its subject is ROADMAP.md, which AGENTS.md
# calls authoritative for what happens next and which no gate has ever read.
ROADMAP = "ROADMAP.md"

TASK_ID = re.compile(r"\b(?:feat|bug|chore|docs|spike)-\d{4}\b")

# A markdown block starts at a list item, a heading, or a table row, and otherwise runs to
# the next blank line. The unit matters, and it was measured: an earlier draft treated
# every unindented line as a new block, which split this file's wrapped paragraphs one
# line each and lost the chore-0042 defect entirely, because the claim and the id it was
# about sat on different lines.
BLOCK_START = re.compile(r"^\s*(?:[-*+]\s|\d+\.\s)|^#|^\|")

# Two tiers, and the split is the whole false-positive answer. A PRESENT-tense claim that
# work is outstanding contradicts a closed id on its own, so nothing in the block excuses
# it. A HEDGED phrase is one this file also uses historically, and its corrected idiom is
# always "Scoped as [id](...) and **shipped <date>**", so a completion marker anywhere in
# the same block means the sentence is a record rather than a claim.
#
# Measured before being written, over ROADMAP.md at b7cd720^ (the state chore-0066 found)
# and at 7a9558f (the state it left): 6 findings on the first, 0 on the second. The tense
# in "are filed rather than fixed" is load-bearing rather than stylistic. chore-0066
# corrected that exact sentence to "were filed rather than fixed and **both closed
# 2026-08-19**", so matching the bare phrase would fire on its own fix.
OPEN_STATE_PRESENT = (
    "are filed rather than fixed",
    "is filed rather than fixed",
    "not yet filed",
    "is still open",
    "are still open",
    "remains open",
    "remain open",
)
OPEN_STATE_HEDGED = (
    "scoped as",
    "pending",
    "ready to dispatch",
    "in flight",
    "awaiting",
)

# A completion word bolded at the head of its span, or sitting beside a date, or a
# struck-through item. Deliberately not the bare word: this file writes "the shipped task
# template" and "the shipped validator" as adjectives, and matching those suppressed two
# real defects when it was tried.
_COMPLETION_WORD = (r"(?:shipped|landed|closed|merged|superseded|completed|struck"
                    r"|discharged|corrected)")
COMPLETION_MARKER = re.compile(
    r"~~|\*\*\s*(?:and\s+)?" + _COMPLETION_WORD
    + r"|" + _COMPLETION_WORD + r"\b[^.\n]{0,25}\d{4}-\d{2}-\d{2}", re.IGNORECASE)

# chore-0066 removed the whole-file header on 2026-08-27, after it had read 2026-08-07 for
# twenty days with nothing checking it. This keeps that decision from being undone by
# someone who reads its absence as an oversight. The pattern needs the colon and a date on
# the same line, because the sentence recording the removal names the field in prose and
# must not match itself.
STALE_HEADER = re.compile(r"Last updated:.{0,20}?\d{4}-\d{2}-\d{2}")


def task_locations(repo_root=None):
    """Every task id under `.tasks/`, mapped to the directories holding it.

    A set rather than a string, because an id sitting in both directories is a real state
    this must not silently resolve to one of them.
    """
    repo_root = REPO_ROOT if repo_root is None else Path(repo_root)
    found = {}
    for directory, where in ((repo_root / ".tasks", "open"),
                             (repo_root / ".tasks" / "done", "done")):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            match = TASK_ID.match(path.name)
            if match:
                found.setdefault(match.group(0), set()).add(where)
    return found


def markdown_blocks(text):
    """(first line number, block text) for every markdown block in `text`."""
    blocks = []
    current = None
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            current = None
            continue
        if current is None or BLOCK_START.match(raw):
            current = [number, [raw]]
            blocks.append(current)
        else:
            current[1].append(raw)
    return [(number, "\n".join(lines)) for number, lines in blocks]


def roadmap_findings(text, locations):
    """Blocks whose prose claims a closed task id is still outstanding.

    Returns `[(line_number, [phrases], [ids])]`. The comparison runs over the block with
    its whitespace collapsed, because this file wraps prose at about a hundred columns and
    every multi-word phrase in the vocabulary straddles a line break somewhere in it.
    """
    findings = []
    for number, block in markdown_blocks(text):
        flat = " ".join(block.split())
        lowered = flat.lower()
        present = [p for p in OPEN_STATE_PRESENT if p in lowered]
        hedged = [p for p in OPEN_STATE_HEDGED if p in lowered]
        fired = present + ([] if COMPLETION_MARKER.search(flat) else hedged)
        if not fired:
            continue
        closed = sorted({i for i in TASK_ID.findall(block)
                         if locations.get(i) == {"done"}})
        if closed:
            findings.append((number, fired, closed))
    return findings


def check_roadmap(repo_root=None):
    """The `roadmap bookkeeping` gate: does ROADMAP.md still agree with .tasks/?

    Returns (ok, report). Two of the three shapes chore-0066 mapped, and a bound naming
    what is left. The bound is not decoration. This catches the bookkeeping class and
    cannot catch the defect that mattered most in that pass, Epic E item 2 restating an
    acceptance bar that docs/spec/cloud-executable.md had already repointed eight days
    earlier. Catching that means reading the contract the roadmap restates, which is a
    different capability, so a green run here must not be read as "the roadmap is
    current".

    The third shape, a quoted shell command written into the file beside its own output,
    is deliberately not built. One instance is not a mechanism; telling a claim about a
    command's current output from a command quoted as an illustration needs the judgment
    this check has none of; and running shell text lifted out of a document is an action
    no gate here takes.
    """
    repo_root = REPO_ROOT if repo_root is None else Path(repo_root)
    text = (repo_root / ROADMAP).read_text(encoding="utf-8")
    locations = task_locations(repo_root)

    named = sorted(set(TASK_ID.findall(text)))
    closed = [i for i in named if locations.get(i) == {"done"}]
    outstanding = [i for i in named if locations.get(i) == {"open"}]
    unresolved = [i for i in named if len(locations.get(i, ())) != 1]
    blocks = markdown_blocks(text)
    findings = roadmap_findings(text, locations)
    header = STALE_HEADER.search(text)

    lines = []
    for number, phrases, ids in findings:
        lines.append(
            f"{ROADMAP}:{number}: {', '.join(ids)} "
            f"{'is' if len(ids) == 1 else 'are'} in .tasks/done/, and this block "
            f"reads as outstanding: {'; '.join(repr(p) for p in phrases)}")
    if header:
        lines.append(
            f"{ROADMAP}: a `Last updated:` header is back ({header.group(0)!r}). "
            f"chore-0066 removed it on 2026-08-27 because a date nothing derives is a "
            f"claim nobody maintains, and `git log -1 ROADMAP.md` answers the same "
            f"question without being able to drift.")
    # Reported, never judged. An id naming no task file may be a typo or a file not yet
    # written, and this check cannot tell which; saying nothing would let the arithmetic
    # below imply a coverage it does not have.
    if unresolved:
        lines.append(f"{ROADMAP}: {len(unresolved)} id(s) named here resolve to no "
                     f"single task file and were not judged: "
                     f"{', '.join(unresolved)}")

    lines.append(
        f"Checked {ROADMAP}: {len(named)} task ids named, {len(closed)} in .tasks/done/, "
        f"{len(outstanding)} in .tasks/, {len(unresolved)} unresolved; {len(blocks)} "
        f"blocks read, {len(findings)} carrying an open-state claim over a closed id; "
        f"1 header rule, {0 if header is None else 1} tripped. Not judged: the "
        f"restated-contract class (a roadmap claim restating a spec's own bar, which "
        f"needs reading that contract), quoted commands and their written-down output, "
        f"and a hedged phrase in a block that also carries a completion marker. "
        f"2 of the 3 shapes chore-0066 mapped are covered, so a pass here is evidence "
        f"about bookkeeping and about nothing else.")
    return not findings and header is None, "\n".join(lines)


def gates():
    """The gate set: every gate that decides whether a change here is acceptable.

    Ordered as checks.yml ran the ones it used to restate. The set is open by design and
    its membership is the property that matters, not its size: it began as the seven
    steps checks.yml carried, and `chore-0049` added the matrix-citation gate. Naming a
    count here, or in the contract, goes stale the first time anyone adds a gate, which is
    the class this repository keeps filing tasks about.

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
        #
        # Each of the three patterns must match at least one document or this gate
        # fails and names the one that did not (chore-0032). Until then the guard fired
        # only when every pattern matched nothing, so renaming `docs/` left this gate
        # green over 9 documents of 45. The three trees are all guaranteed present here,
        # which is why no pattern needs an escape and none is offered.
        Gate("doc links",
             [[PY, ".tasks/validate.py", "--links",
               "*.md", ".github/**/*.md", "docs/**/*.md"]]),
        # Added by chore-0049. The doc-links gate above resolves a markdown link's path
        # and stops there; a conformance matrix's evidence is a symbol, a test name, or a
        # quoted phrase, and none of those is a path. So a matrix could go on asserting
        # that a renamed symbol exists with every gate green, which is what bug-0037
        # measured: seven of 65 pointers in one matrix aimed at something other than what
        # they claimed, from two independent causes in one month.
        Gate("matrix citations", [[PY, "scripts/check-citations.py"]]),
        # Added by chore-0072, and the first gate here that is a callable rather than a
        # script. Nothing above reads ROADMAP.md, which AGENTS.md calls authoritative for
        # what happens next: `backlog` walks the task files, and `doc links` resolves this
        # file's link paths and stops there. So a sentence saying a task is still to be
        # done, beside that task's own file sitting in `.tasks/done/`, passed every gate,
        # which is what chore-0066 measured when it corrected nine of them at once.
        Gate("roadmap bookkeeping", [], check=check_roadmap),
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


def _run_check(gate):
    """Run an in-process gate. Same (status, output, cleanup_ok) shape as a command gate.

    The broad `except Exception` is the one place in this file that catches everything,
    and it is deliberate. Every other gate is a subprocess, so its crash is somebody
    else's traceback and a non-zero return code; an in-process gate raising would abort
    the aggregator itself and take the gates after it down with it, which is exactly the
    fail-fast behaviour this command was written not to have. A crash is reported as
    `unrunnable` rather than `failed`, for the same reason a missing script is: it means
    the question was never answered, not that the answer was no.
    """
    try:
        ok, output = gate.check()
    except Exception as exc:  # deliberately broad; see the docstring
        return "unrunnable", f"could not run: {type(exc).__name__}: {exc}", True
    return ("ok" if ok else "failed"), output, True


def run_gate(gate, runner=None):
    """Run one gate. Returns (status, output, cleanup_ok).

    `cleanup_ok` is reported separately from `status` rather than folded into it. A
    cleanup that fails leaves files behind, which a reader needs to know about, but it
    says nothing about whether the change under test is good, so it must not turn a
    passing gate into a failing one. Keeping them separate is what lets the report say
    both things at once.
    """
    if gate.check is not None:
        return _run_check(gate)
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
    test without executing every real gate, which would make the failure and
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
