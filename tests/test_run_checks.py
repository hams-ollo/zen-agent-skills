"""Tests for scripts/run-checks.py, the committed acceptance command (feat-0045).

Derived from docs/spec/cloud-executable.md, S-001 to S-007.

The aggregation branches are exercised with a stubbed gate table and a stubbed runner.
That is the lowest faithful layer for them: making a real gate fail on demand would mean
breaking a real script, and making one unrunnable would mean deleting one. The stub makes
both deterministic, and what is under test is the aggregation, not the gates themselves.

The two branches that a stub could not prove honestly are tested against real artifacts
instead: S-004's filesystem claim, and S-005's claim about a checked-in workflow file.
"""
import importlib.util
import io
import platform
import re
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Loaded by path: the filename has a hyphen, so it is not importable as a module name.
# Mirrors how the other script tests in this suite reach their subject.
_spec = importlib.util.spec_from_file_location(
    "run_checks", REPO_ROOT / "scripts" / "run-checks.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)


class _Done:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def stub_runner(outcomes):
    """A subprocess.run stand-in driven by a {command-tail: outcome} mapping.

    An outcome is an int return code, or an exception instance to raise.
    """
    calls = []

    def run(command, cwd=None, capture_output=False, text=False):
        calls.append(command)
        key = command[-1]
        outcome = outcomes.get(key, 0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Done(outcome, stdout=f"output of {key}")

    run.calls = calls
    return run


def gate(name, tail, cleanup_tail=None):
    """A stub gate whose command names no script file.

    The `-c` form matters: `_script_of` treats a bare second element as a path and marks
    the gate unrunnable when it does not exist, which is correct for real gates and would
    make every stub here unrunnable regardless of the outcome being tested.
    """
    return rc.Gate(name, [["py", "-c", tail]],
                   cleanup=["py", "-c", cleanup_tail] if cleanup_tail else None)


class GateSetTests(unittest.TestCase):
    """The gate set itself, pinned.

    This test is deliberately a second source of truth. The obvious guard, comparing the
    table against the steps in checks.yml, cannot work: S-005 replaces those seven steps
    with one call to this command, so after that change there is nothing left there to
    compare against. Without a pinned list, a gate quietly deleted from run-checks.py
    would narrow what CI checks and nothing would notice, which is strictly worse than
    the situation this command was written to fix.
    """

    # The full shape of every gate, with the interpreter dropped because sys.executable
    # varies by host. Names alone are not enough: the first version of this pinned
    # (name, commands[0][-1]), and independent verification showed that swapping a gate's
    # script for a different one with the same trailing token survived, as did deleting
    # the install cycle's SECOND run, which is the entire idempotence proof. Both are
    # exactly the "silently narrowing what is checked" the criterion names, so the pin
    # now covers every command and the cleanup.
    EXPECTED = [
        ("lint skills",
         [["scripts/validate-skills.py"]],
         None),
        ("test suite",
         [["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]],
         None),
        ("backlog",
         [[".tasks/validate.py", "--strict"]],
         None),
        ("adapters dry run",
         [["scripts/build-adapters.py", "--dry-run"]],
         None),
        ("install dry run",
         [["scripts/install.py", "--dry-run", "--home", "./.tmp/zen-home"]],
         None),
        # `--with-hooks` added by chore-0067. The cleanup deliberately does not carry it:
        # `install.py`'s uninstall branch returns before it ever reads the flag, and the
        # reversal is driven by the recorded manifest entry instead.
        ("install cycle",
         [["scripts/install.py", "--with-hooks", "--home", "./.tmp/zen-home"],
          ["scripts/install.py", "--with-hooks", "--home", "./.tmp/zen-home"]],
         ["scripts/install.py", "--uninstall", "--home", "./.tmp/zen-home"]),
        ("doc links",
         [[".tasks/validate.py", "--links", "*.md", ".github/**/*.md", "docs/**/*.md"]],
         None),
        # Added by chore-0049. The doc-links gate above resolves a link's path; a matrix
        # cites a symbol, a test name, or a quoted phrase, none of which is a path.
        ("matrix citations",
         [["scripts/check-citations.py"]],
         None),
        # Added by chore-0072, and the first gate whose work is a callable rather than a
        # subprocess, so it pins as no commands and no cleanup. The empty list is not the
        # whole shape, which is why the test below asserts the callable separately: a gate
        # that lost its `check` would pin identically and do nothing.
        ("roadmap bookkeeping",
         [],
         None),
    ]

    @staticmethod
    def _shape(gate_):
        return (gate_.name,
                [command[1:] for command in gate_.commands],
                gate_.cleanup[1:] if gate_.cleanup else None)

    def test_the_gate_set_is_present_ordered_and_complete(self):
        # Renamed by chore-0049 from `test_the_seven_gates_are_...`. The gate set is open
        # and the eighth gate landed in that task, so a name carrying a count was already
        # false of the thing it pins. That is the same count-shaped staleness the
        # cloud-executable `Gate set` element was amended to remove on the same date, and
        # a test name is read far more often than the list beneath it.
        actual = [self._shape(g) for g in rc.gates()]
        self.assertEqual(self.EXPECTED, actual,
                         "the gate set changed; if that was deliberate, update this list "
                         "and checks.yml's expectations together")

    def test_the_roadmap_gate_is_a_callable_and_not_an_empty_gate(self):
        # The pin above records `roadmap bookkeeping` as carrying no commands, which is
        # also exactly what a gate whose `check` was deleted would look like. This is the
        # half of its shape the pin cannot express.
        roadmap = next(g for g in rc.gates() if g.name == "roadmap bookkeeping")
        self.assertEqual([], roadmap.commands)
        self.assertTrue(callable(roadmap.check),
                        "an empty command list with no check is a gate that never runs")

    def test_no_gate_carries_both_commands_and_a_check(self):
        # Two gate kinds, and `run_gate` dispatches on the check first, so a gate carrying
        # both would silently never run its commands.
        for gate_ in rc.gates():
            with self.subTest(gate=gate_.name):
                self.assertFalse(gate_.commands and gate_.check is not None,
                                 "a gate carries commands or a check, never both")

    def test_the_install_cycle_runs_twice_to_prove_idempotence(self):
        # Called out separately from the pin above because it is the one duplicate in the
        # table and reads like a copy-paste mistake to anyone tidying up. Re-running the
        # install is what proves a second run recognises its own targets rather than
        # reporting a conflict against its own work (install.md S-003).
        cycle = next(g for g in rc.gates() if g.name == "install cycle")
        self.assertEqual(2, len(cycle.commands),
                         "the second install run is the idempotence proof, not a typo")
        self.assertEqual(cycle.commands[0], cycle.commands[1])

    def test_only_the_install_cycle_cleans_up_after_itself(self):
        # The cleanup is what makes S-004 hold when a gate fails midway. If another gate
        # grows one, that is a design change worth noticing rather than absorbing.
        with_cleanup = [g.name for g in rc.gates() if g.cleanup is not None]
        self.assertEqual(["install cycle"], with_cleanup)

    def test_the_install_cycle_reverses_what_it_placed(self):
        cycle = next(g for g in rc.gates() if g.name == "install cycle")
        self.assertIn("--uninstall", cycle.cleanup)
        self.assertIn(rc.THROWAWAY_HOME, cycle.cleanup)

    def test_the_install_cycle_exercises_the_hook_placement_path(self):
        # Called out separately from the pin above for the same reason the duplicate run
        # is: the flag reads like something to drop when tidying, and dropping it costs
        # more than it looks. `.agents/hooks/` is the only module the kit runs inside an
        # adopter's session, and before chore-0067 its placement path ran on none of the
        # six CI cells: `grep -n with-hooks scripts/run-checks.py` returned nothing.
        #
        # The component tests in tests/test_install.py cover placement in-process and in
        # copy mode; this gate is what covers it through the real CLI in whichever mode
        # the platform defaults to, which is symlink on macOS and Linux.
        cycle = next(g for g in rc.gates() if g.name == "install cycle")
        for command in cycle.commands:
            with self.subTest(command=command):
                self.assertIn("--with-hooks", command,
                              "the hooks module ships untested on every cell without it")
        self.assertNotIn("--with-hooks", cycle.cleanup,
                         "reversal is driven by the manifest entry, not by the flag")


class AggregationTests(unittest.TestCase):
    """S-001 to S-003: what the exit code means."""

    def test_every_gate_runs_and_all_passing_exits_zero(self):
        # S-001.
        stub = stub_runner({})
        buf = io.StringIO()
        code = rc.run_all([gate("a", "one"), gate("b", "two")], stub, buf)
        self.assertEqual(0, code)
        self.assertEqual(2, len(stub.calls), "every gate must run")
        self.assertIn("ok", buf.getvalue())

    def test_a_failing_gate_does_not_stop_the_ones_after_it(self):
        # S-002. The load-bearing half: an unattended agent gets one round trip, so a
        # report truncated at the first failure costs it another.
        stub = stub_runner({"one": 1})
        buf = io.StringIO()
        code = rc.run_all([gate("a", "one"), gate("b", "two")], stub, buf)
        self.assertEqual(1, code)
        self.assertEqual(2, len(stub.calls),
                         "the gate after a failure must still run")
        out = buf.getvalue()
        self.assertIn("failed", out)
        self.assertIn("output of one", out, "the failing gate's own output is reported")

    def test_a_gate_that_cannot_run_outranks_one_that_failed(self):
        # S-003. Both branches present at once, so precedence is actually exercised
        # rather than inferred from two separate single-branch runs.
        stub = stub_runner({"one": 1, "two": FileNotFoundError("no such script")})
        buf = io.StringIO()
        code = rc.run_all([gate("a", "one"), gate("b", "two")], stub, buf)
        self.assertEqual(2, code, "could-not-run must outrank failed")
        self.assertIn("unrunnable", buf.getvalue())

    def test_an_unrunnable_gate_is_not_reported_as_failed(self):
        # The distinction is the whole point of the third exit code: "the report is
        # incomplete" is a different claim from "the change is bad".
        stub = stub_runner({"one": OSError("interpreter could not start")})
        buf = io.StringIO()
        rc.run_all([gate("a", "one")], stub, buf)
        out = buf.getvalue()
        self.assertIn("unrunnable", out)
        self.assertIn("0 passed, 0 failed, 1 could not run", out)

    def test_cleanup_runs_even_when_the_gate_failed(self):
        # S-004's mechanism. A run that fails midway must not leave a populated
        # throwaway home behind.
        stub = stub_runner({"install": 1})
        buf = io.StringIO()
        rc.run_all([gate("cycle", "install", cleanup_tail="uninstall")], stub, buf)
        self.assertIn(["py", "-c", "uninstall"], stub.calls,
                      "the reversal must run even after the gate failed")

    def test_a_failed_cleanup_is_reported_without_masking_the_result(self):
        stub = stub_runner({"uninstall": 1})
        buf = io.StringIO()
        code = rc.run_all([gate("cycle", "install", cleanup_tail="uninstall")], stub, buf)
        self.assertEqual(0, code, "a cleanup failure says nothing about the change")
        self.assertIn("cleanup did not complete", buf.getvalue())


class CoverageReportTests(unittest.TestCase):
    """S-001 and S-002, the passing half (bug-0045): a gate reports what it covered.

    S-001 requires every gate to be "named in the output with its own outcome" and S-002
    requires a failing gate to be "named with its output". Neither says what a *passing*
    gate carries, and the answer used to be one status word: `run_all()` collected every
    gate's output and appended it only `if status != "ok"`. Measured 2026-08-22 over a
    copy of this repository with the skills, the tests, and the task files removed, six
    of the seven gates exited 0 having examined nothing and the report was byte-identical
    to a full clean run.

    The tests below assert the *property* rather than any gate's current wording, as
    bug-0045 required, so a gate rewording its summary line does not break them.
    """

    @staticmethod
    def _runner(outputs):
        """A subprocess.run stand-in returning a chosen (returncode, stdout) per tail."""
        def run(command, cwd=None, capture_output=False, text=False):
            code, text_out = outputs[command[-1]]
            return _Done(code, stdout=text_out)
        return run

    def _report(self, gates_, outputs):
        buf = io.StringIO()
        code = rc.run_all(gates_, self._runner(outputs), buf)
        return code, buf.getvalue()

    @staticmethod
    def _coverage_of(report, name):
        """The line the report puts directly beneath a named gate's status line."""
        pattern = re.compile(
            r"^(ok|failed|unrunnable)\s+" + re.escape(name) + r"(\s+\(cleanup.*)?$")
        lines = report.splitlines()
        for index, line in enumerate(lines):
            if pattern.match(line):
                return lines[index + 1].strip()
        raise AssertionError(f"{name} is not named in the report:\n{report}")

    def test_a_passing_run_differs_when_a_gate_reports_different_coverage(self):
        # The property, with two injected gates whose outputs differ only in the count.
        # Asserted by comparing the two coverage lines to each other rather than to a
        # fixed string, so nothing here has to be edited when a gate rewords its summary.
        full = "walking the tree\nChecked 20 skill(s): 0 error(s), 0 warning(s)."
        empty = "walking the tree\nChecked 0 skill(s): 0 error(s), 0 warning(s)."
        code, report = self._report(
            [gate("full scope", "one"), gate("empty scope", "two")],
            {"one": (0, full), "two": (0, empty)})
        self.assertEqual(0, code, "both gates passed, so the exit code is unchanged")
        self.assertNotEqual(self._coverage_of(report, "full scope"),
                            self._coverage_of(report, "empty scope"),
                            "two gates that covered different amounts must not read alike")

    def test_two_passing_runs_over_different_scopes_are_not_byte_identical(self):
        # The same property stated end to end over the whole report, which is the form
        # the defect took: a run over an empty tree printed the bytes of a clean run.
        gates_ = [gate("a", "one")]
        _, full = self._report(gates_, {"one": (0, "Checked 155 task files.")})
        _, empty = self._report(gates_, {"one": (0, "Checked 0 task files.")})
        self.assertNotEqual(full, empty)

    def test_a_passing_gate_carries_a_coverage_line_at_all(self):
        # The branch the old code excluded outright, named directly so its removal is
        # not something a wording change could quietly undo.
        _, report = self._report([gate("a", "one")], {"one": (0, "Checked 9 documents.")})
        self.assertEqual("Checked 9 documents.", self._coverage_of(report, "a"))

    def test_a_gate_that_examined_nothing_says_so_instead_of_only_ok(self):
        # `validate-skills.py`, `install.py`, and `build-adapters.py` all print this
        # sentence over an empty tree and exit 0. It carries no digit, so it is the
        # fallback rather than the count rule that has to surface it.
        _, report = self._report([gate("a", "one")],
                                 {"one": (0, "No skills found under /x/skills.")})
        self.assertEqual("No skills found under /x/skills.",
                         self._coverage_of(report, "a"))

    def test_a_trailing_status_word_does_not_displace_the_count_before_it(self):
        # unittest's own output shape, and the reason the rule is not simply "the last
        # non-blank line": its final line is a bare `OK`, byte-identical over 482 tests
        # and over zero, which is the exact failure this whole class exists to remove.
        output = ("-" * 70 + "\nRan 482 tests in 8.395s\n\nOK\n")
        _, report = self._report([gate("a", "one")], {"one": (0, output)})
        self.assertEqual("Ran 482 tests in 8.395s", self._coverage_of(report, "a"))

    def test_the_addition_is_one_line_per_gate_not_the_whole_output(self):
        # bug-0045's stated risk: a report so long that the tally at the bottom stops
        # being read would be a worse outcome than the terseness it replaced.
        output = "\n".join(f"detail line {n}" for n in range(50)) + "\nChecked 7 things."
        _, report = self._report([gate("a", "one")], {"one": (0, output)})
        self.assertNotIn("detail line 0", report,
                         "a passing gate's whole output must not be dumped")
        head = report.split("\n\n")[0].splitlines()
        self.assertEqual(2, len(head),
                         "a gate contributes its status line and exactly one more")

    def test_a_multi_command_gate_reports_its_last_commands_count(self):
        # The `install cycle` gate runs `install.py` twice, so "the last count" there is
        # the re-install's. That is the right one to show: the second run is the
        # idempotence proof, the one that has to recognise its own targets rather than
        # report a conflict against its own work. The stated limitation is that one line
        # cannot show the two runs disagreeing, which the exit code would not catch
        # either, since both runs returning 0 is the whole of the gate's verdict.
        two_runs = rc.Gate("cycle", [["py", "-c", "first"], ["py", "-c", "second"]])
        _, report = self._report(
            [two_runs],
            {"first": (0, "Done: placed 18 skill(s)."),
             "second": (0, "Done: re-placed 18 skill(s).")})
        self.assertEqual("Done: re-placed 18 skill(s).",
                         self._coverage_of(report, "cycle"))

    def test_the_failure_branch_still_shows_the_gates_full_output(self):
        # Unchanged by bug-0045, and pinned here because the coverage line is a summary
        # and a failing gate's detail is the thing that gets acted on.
        output = "first\nsecond\nChecked 3 things.\nfourth"
        code, report = self._report([gate("a", "one")], {"one": (1, output)})
        self.assertEqual(1, code)
        self.assertIn("----- a: failed -----", report)
        for line in output.splitlines():
            self.assertIn(line, report)

    def test_the_could_not_run_branch_still_shows_its_full_output(self):
        # Run for real rather than stubbed, for the reason RealSubprocessTests gives:
        # subprocess does not raise for a missing script, so a stub of this branch tests
        # the assumption instead of the behaviour.
        missing = rc.Gate("missing", [[rc.PY, "scripts/does-not-exist.py"]])
        buf = io.StringIO()
        code = rc.run_all([missing], out=buf)
        report = buf.getvalue()
        self.assertEqual(2, code)
        self.assertIn("----- missing: unrunnable -----", report)
        self.assertIn("scripts/does-not-exist.py does not exist",
                      self._coverage_of(report, "missing"))


class CoverageLineRuleTests(unittest.TestCase):
    """`coverage_line()` on its own: which line, and what happens when there is none."""

    def test_the_last_line_carrying_a_count_is_chosen(self):
        self.assertEqual(
            "Checked 155 task files: 0 error(s), 0 warning(s).",
            rc.coverage_line("reading .tasks\n"
                             "Checked 155 task files: 0 error(s), 0 warning(s).\n"))

    def test_a_later_line_without_a_count_does_not_win(self):
        # Both install gates end on `install.py`'s "Run ... --check" advice, which says
        # nothing about what was placed.
        output = ("Done: profile 'spine', 18 of 20 skill(s) x 2 tool(s).\n"
                  "Run `python scripts/install.py --check` to compare an installed set.\n")
        self.assertEqual("Done: profile 'spine', 18 of 20 skill(s) x 2 tool(s).",
                         rc.coverage_line(output))

    def test_output_with_no_digits_anywhere_falls_back_to_its_last_line(self):
        self.assertEqual("No skills found under /x/skills.",
                         rc.coverage_line("scanning\nNo skills found under /x/skills.\n"))

    def test_a_silent_gate_is_named_as_silent_rather_than_left_blank(self):
        # A blank second line would read as a formatting glitch; this reads as a fact.
        self.assertEqual("(no output)", rc.coverage_line(""))
        self.assertEqual("(no output)", rc.coverage_line("   \n\n\t\n"))


class RealSubprocessTests(unittest.TestCase):
    """The branches that a stub got wrong, exercised against real subprocesses.

    These exist because the stubbed version of `test_a_gate_that_cannot_run_outranks_one
    _that_failed` passed while the real behaviour was different. The stub raised
    FileNotFoundError because that is what the code expected; subprocess does not raise
    for a missing script at all. Every branch below therefore runs a real process, and
    the cost of being slower than the stubbed tests is the point of them.
    """

    def test_a_missing_script_is_unrunnable_not_failed(self):
        # The realistic cause of a gate that cannot run, and the one the stub hid:
        # subprocess.run([python, "gone.py"]) starts the interpreter fine and exits
        # non-zero, so without an explicit check this reports `failed` at exit 1.
        missing = rc.Gate("missing", [[rc.PY, "scripts/does-not-exist.py"]])
        buf = io.StringIO()
        code = rc.run_all([missing], out=buf)
        self.assertEqual(2, code)
        self.assertIn("unrunnable", buf.getvalue())
        self.assertIn("does not exist", buf.getvalue())

    def test_unrunnable_outranks_failed_for_real(self):
        missing = rc.Gate("missing", [[rc.PY, "scripts/does-not-exist.py"]])
        failing = rc.Gate("failing", [[rc.PY, "-c", "import sys; sys.exit(1)"]])
        buf = io.StringIO()
        self.assertEqual(2, rc.run_all([missing, failing], out=buf))

    def test_a_real_failure_exits_one_and_later_gates_still_run(self):
        failing = rc.Gate("failing", [[rc.PY, "-c", "import sys; sys.exit(1)"]])
        passing = rc.Gate("passing", [[rc.PY, "-c", "print('fine')"]])
        buf = io.StringIO()
        self.assertEqual(1, rc.run_all([failing, passing], out=buf))
        self.assertIn("ok          passing", buf.getvalue())

    def test_a_module_command_is_not_mistaken_for_a_missing_script(self):
        # `-m unittest` names no file. Treating "-m" as a path would make the real test
        # suite gate permanently unrunnable, which is the inverse defect.
        module = rc.Gate("module", [[rc.PY, "-c", "print('ran')"]])
        buf = io.StringIO()
        self.assertEqual(0, rc.run_all([module], out=buf))

    def test_every_real_gate_names_a_script_that_exists(self):
        # Guards the whole table against the same class: a gate whose script was renamed
        # would report unrunnable at exit 2 on every run.
        for g in rc.gates():
            for command in g.commands + ([g.cleanup] if g.cleanup else []):
                script = rc._script_of(command)
                if script is not None:
                    with self.subTest(gate=g.name, script=script):
                        self.assertTrue((REPO_ROOT / script).exists(),
                                        f"{g.name} names a script that does not exist")


class SummaryTests(unittest.TestCase):
    """S-006: the run states the bound of its own answer."""

    def test_the_summary_names_the_platform_and_interpreter(self):
        buf = io.StringIO()
        rc.run_all([gate("a", "one")], stub_runner({}), buf)
        out = buf.getvalue()
        self.assertIn(platform.system(), out)
        self.assertIn(platform.python_version(), out)

    def test_the_summary_states_that_passing_is_not_sufficient(self):
        buf = io.StringIO()
        rc.run_all([gate("a", "one")], stub_runner({}), buf)
        self.assertIn("necessary but not sufficient", buf.getvalue())

    def test_agents_md_states_the_bound_in_those_words(self):
        # S-006's second half, and S-007's. The bound has to be where an agent reads the
        # rules before working, not only in the output of a run that already happened.
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("run-checks.py", agents)
        self.assertIn("necessary but not sufficient", agents)


class WorkflowWiringTests(unittest.TestCase):
    """S-005: CI calls the command instead of restating the gates."""

    def setUp(self):
        self.workflow = (REPO_ROOT / ".github" / "workflows" / "checks.yml").read_text(
            encoding="utf-8")

    def test_ci_invokes_the_acceptance_command(self):
        self.assertIn("scripts/run-checks.py", self.workflow)

    def _run_lines(self):
        """Every `run:` value in the workflow, which is where a gate could be restated.

        Scanning `run:` values rather than the whole file on purpose. The workflow's
        comments legitimately name scripts and task ids while explaining why the gates are
        no longer listed, and a whole-file scan would either fail on those or force the
        comments to be written around the test.
        """
        lines = []
        for raw in self.workflow.splitlines():
            stripped = raw.strip()
            if stripped.startswith("run:"):
                lines.append(stripped[len("run:"):].strip())
        return lines

    def test_ci_does_not_separately_restate_any_gate(self):
        # One rule, two callers. An inline copy of the link rule drifted once already and
        # let a correctly quoted changelog entry pass --strict and fail CI (chore-0029).
        #
        # This assertion was rewritten after independent verification found the first
        # version vacuous for five of the seven gates. It built `assertNotIn("run: python
        # " + tail)` where `tail` was the command's LAST token, so for the backlog gate it
        # asserted the absence of "run: python --strict", a string that can never appear:
        # a real restatement reads "run: python .tasks/validate.py --strict". Four genuine
        # restatements were reinserted into checks.yml and the suite stayed green. Only the
        # two hardcoded lines below did any work, while the comment claimed the chore-0029
        # lesson was mechanical for all seven.
        #
        # The fix is to match on each gate's identifying script or module, derived from the
        # gate table rather than hand-listed, so a gate added later is covered without
        # anyone remembering to come back here.
        markers = set()
        for gate_ in rc.gates():
            for command in gate_.commands + ([gate_.cleanup] if gate_.cleanup else []):
                script = rc._script_of(command)
                if script:
                    markers.add(script)
                elif "-m" in command:
                    markers.add(command[command.index("-m") + 1])

        self.assertIn("scripts/run-checks.py", " ".join(self._run_lines()),
                      "CI must call the acceptance command")
        for marker in sorted(markers):
            for line in self._run_lines():
                if "run-checks.py" in line:
                    continue
                with self.subTest(marker=marker, line=line):
                    self.assertNotIn(marker, line,
                                     f"checks.yml restates the {marker} gate; the gate set "
                                     f"must live only in run-checks.py")

    def test_the_marker_set_actually_covers_every_gate(self):
        # Guards the guard. The rewritten test above is only as strong as the markers it
        # derives, and a gate whose command names neither a script nor a `-m` module would
        # contribute no marker and be silently unprotected.
        for gate_ in rc.gates():
            with self.subTest(gate=gate_.name):
                # An in-process gate (chore-0072) names no command, so there is nothing
                # checks.yml could restate and nothing for a marker to protect. The
                # guarantee is kept rather than widened: such a gate must prove it is that
                # kind by carrying a check, so "no marker" can never mean "no work".
                if not gate_.commands:
                    self.assertIsNotNone(gate_.check,
                                         f"{gate_.name} names no command and no "
                                         f"check, so it contributes no marker and "
                                         f"does nothing")
                    continue
                command = gate_.commands[0]
                self.assertTrue(rc._script_of(command) or "-m" in command,
                                f"{gate_.name} contributes no marker, so restating it in "
                                f"checks.yml would not be caught")


class ArgumentTests(unittest.TestCase):
    """The Proposed Surface says no flags. An unrecognised one is refused, not ignored."""

    def test_any_argument_is_refused(self):
        buf = io.StringIO()
        code = rc.main(["--only", "tests"], out=buf)
        self.assertEqual(2, code)
        self.assertIn("takes no arguments", buf.getvalue())


class RoadmapBookkeepingTests(unittest.TestCase):
    """The `roadmap bookkeeping` gate (chore-0072).

    Characterization, not spec-derived: `docs/spec/cloud-executable.md` contracts the gate
    SET as an open membership and says nothing about any individual gate, so there is no
    S-NNN scenario to be faithful to here. What these pin instead is that the check fires
    on the input it claims to reject and stays quiet on the input it claims to accept, and
    both halves are anchored to real text rather than to invented examples.

    The fixtures are built in a temporary directory rather than under `tests/fixtures/`,
    so the whole change stays inside the two files chore-0072 owns.
    """

    def _repo(self, roadmap, done=(), still_open=()):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / ".tasks" / "done").mkdir(parents=True)
        for task_id in done:
            (root / ".tasks" / "done" / f"{task_id}-slug.md").write_text(
                "x", encoding="utf-8")
        for task_id in still_open:
            (root / ".tasks" / f"{task_id}-slug.md").write_text("x", encoding="utf-8")
        (root / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
        return root

    # The two sentences below are verbatim from ROADMAP.md at b7cd720^, the state
    # chore-0066 found. Quoting the real defect rather than inventing one is the point:
    # a check proved against a fixture written to match it has proved nothing.
    SCOPED_AS = ("- **The lite tier scaffolds a required field that cannot be "
                 "satisfied.** Lite ships no `ROADMAP.md`,\n  `_TEMPLATE.md.tmpl` seeds "
                 "`parent`. Scoped as [`bug-0030`]"
                 "(.tasks/done/bug-0030-lite-tier-parent-field-has-no-roadmap-to-name.md).")
    FILED_NOT_FIXED = ("**Landed 2026-08-18, in one worktree-isolated batch of six**: "
                       "`bug-0026`, `bug-0028`.\nTwo findings the batch itself surfaced "
                       "are filed rather\nthan fixed: [`chore-0042`]"
                       "(.tasks/done/chore-0042-renormalise-the-authors-working-tree.md), "
                       "the\nrenormalise remainder.")

    def test_an_open_state_claim_over_a_closed_id_is_reported(self):
        root = self._repo(self.SCOPED_AS, done=["bug-0030"])
        ok, report = rc.check_roadmap(root)
        self.assertFalse(ok, "the gate did not fail on the defect it exists for")
        self.assertIn("bug-0030", report)
        self.assertIn("ROADMAP.md:1", report)
        self.assertIn("scoped as", report)

    def test_the_shipped_clause_chore_0066_added_clears_the_finding(self):
        # The correction, not a different sentence: the same block with the completion
        # clause chore-0066 appended. If this still fired, the check would have failed
        # every run since 2026-08-27 and been disabled within a week.
        fixed = self.SCOPED_AS[:-1] + " and **shipped 2026-08-19**."
        root = self._repo(fixed, done=["bug-0030"])
        ok, report = rc.check_roadmap(root)
        self.assertTrue(ok, report)

    def test_a_present_tense_claim_survives_a_completion_marker_elsewhere(self):
        # `**Landed 2026-08-18**` is a true claim about the batch and says nothing about
        # the two findings the same paragraph reports as unfixed. A block-wide marker
        # suppressing a present-tense claim would lose this whole defect, which is what an
        # earlier draft of the check did.
        root = self._repo(self.FILED_NOT_FIXED, done=["chore-0042", "bug-0026", "bug-0028"])
        ok, report = rc.check_roadmap(root)
        self.assertFalse(ok, "a present-tense claim must not be excused by a marker")
        self.assertIn("chore-0042", report)

    def test_the_past_tense_correction_of_that_sentence_is_clean(self):
        # chore-0066 corrected it to "were filed rather than fixed and **both closed
        # 2026-08-19**". The tense is the whole distinction between a claim and a record.
        fixed = self.FILED_NOT_FIXED.replace(
            "are filed rather\nthan fixed:",
            "were filed rather\nthan fixed and **both closed 2026-08-19**:")
        root = self._repo(fixed, done=["chore-0042", "bug-0026", "bug-0028"])
        ok, report = rc.check_roadmap(root)
        self.assertTrue(ok, report)

    def test_a_phrase_split_across_a_line_break_is_still_found(self):
        # ROADMAP.md wraps prose at about a hundred columns, so every multi-word phrase in
        # the vocabulary straddles a newline somewhere. Matching the raw block text missed
        # the chore-0042 defect for exactly this reason.
        self.assertIn("rather\nthan fixed", self.FILED_NOT_FIXED)
        root = self._repo(self.FILED_NOT_FIXED, done=["chore-0042"])
        self.assertFalse(rc.check_roadmap(root)[0])

    def test_the_same_claim_over_an_open_id_is_not_reported(self):
        # `bug-0030` in `.tasks/` makes "Scoped as" true, and the check must say nothing.
        root = self._repo(self.SCOPED_AS, still_open=["bug-0030"])
        ok, report = rc.check_roadmap(root)
        self.assertTrue(ok, report)

    def test_a_returned_last_updated_header_is_reported(self):
        root = self._repo("**Status:** living document | **Last updated:** 2026-08-07\n")
        ok, report = rc.check_roadmap(root)
        self.assertFalse(ok, "the header chore-0066 removed came back unreported")
        self.assertIn("Last updated", report)
        self.assertIn("chore-0066", report)

    def test_the_sentence_recording_the_removal_is_not_read_as_the_header(self):
        # The live file explains the removal in prose and names the field while doing it.
        # A check that fired on its own rationale would be uninstalled on day one.
        root = self._repo("A whole-file `Last updated` header was removed on 2026-08-27.\n")
        self.assertTrue(rc.check_roadmap(root)[0])

    def test_an_id_naming_no_task_file_is_reported_but_not_judged(self):
        root = self._repo("Scoped as `feat-9999`, which is still to do.\n")
        ok, report = rc.check_roadmap(root)
        self.assertTrue(ok, "an unresolvable id is a bound on the answer, not a failure")
        self.assertIn("feat-9999", report)
        self.assertIn("not judged", report)

    def test_the_report_carries_the_arithmetic_and_not_a_claim(self):
        root = self._repo(self.SCOPED_AS, done=["bug-0030"])
        report = rc.check_roadmap(root)[1]
        self.assertIn("1 task ids named, 1 in .tasks/done/", report)
        self.assertIn("blocks read", report)

    def test_the_report_names_the_class_it_cannot_reach(self):
        # The bound is the point of the gate as much as the findings are. Epic E item 2
        # restating a bar `docs/spec/cloud-executable.md` had already repointed is the
        # defect that mattered most in chore-0066's pass and the one nothing mechanical
        # catches, so a passing run must not read as "the roadmap is current".
        report = rc.check_roadmap(self._repo("Nothing here.\n"))[1]
        self.assertIn("restated-contract", report)
        self.assertIn("2 of the 3 shapes", report)

    def test_the_coverage_line_run_checks_shows_is_the_bound(self):
        # `coverage_line` echoes the last line carrying a digit, so the arithmetic and the
        # bound have to share that line or the run shows one without the other.
        report = rc.check_roadmap(self._repo("Nothing here.\n"))[1]
        line = rc.coverage_line(report)
        self.assertIn("task ids named", line)
        self.assertIn("restated-contract", line)

    def test_the_check_is_clean_over_this_repositorys_own_roadmap(self):
        # Run over the real file, per the task's own criterion. This is also what keeps
        # the check honest in the other direction: the fixtures above are small, and a
        # rule that over-fires shows up here or nowhere.
        ok, report = rc.check_roadmap(REPO_ROOT)
        self.assertTrue(ok, report)
        self.assertRegex(report, r"\d+ task ids named")


class CheckGateWiringTests(unittest.TestCase):
    """`run_gate`'s second branch: a gate whose work is a callable (chore-0072)."""

    def test_a_check_returning_false_is_a_failure_not_an_error(self):
        failing = rc.Gate("check", [], check=lambda: (False, "found 1 thing"))
        buf = io.StringIO()
        self.assertEqual(1, rc.run_all([failing], out=buf))
        self.assertIn("found 1 thing", buf.getvalue())

    def test_a_check_that_raises_is_unrunnable_not_failed(self):
        # Same precedence as a missing script: the question was never answered, which is
        # a different claim from "the answer is no".
        def boom():
            raise RuntimeError("no ROADMAP.md")

        buf = io.StringIO()
        self.assertEqual(2, rc.run_all([rc.Gate("check", [], check=boom)], out=buf))
        self.assertIn("unrunnable", buf.getvalue())
        self.assertIn("no ROADMAP.md", buf.getvalue())

    def test_a_raising_check_does_not_stop_the_gates_after_it(self):
        # The whole reason the exception is caught rather than allowed to propagate: an
        # unattended agent gets one round trip, and an aborted aggregator costs another.
        def boom():
            raise RuntimeError("boom")

        after = rc.Gate("after", [[rc.PY, "-c", "print('ran 1 thing')"]])
        buf = io.StringIO()
        self.assertEqual(2, rc.run_all([rc.Gate("check", [], check=boom), after], out=buf))
        self.assertIn("ok          after", buf.getvalue())

    def test_a_check_gate_never_invokes_the_subprocess_runner(self):
        stub = stub_runner({})
        passing = rc.Gate("check", [], check=lambda: (True, "read 2 files"))
        buf = io.StringIO()
        self.assertEqual(0, rc.run_all([passing], stub, buf))
        self.assertEqual([], stub.calls)
        self.assertIn("read 2 files", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
