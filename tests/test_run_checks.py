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

    EXPECTED = [
        ("lint skills", "scripts/validate-skills.py"),
        ("test suite", "test_*.py"),
        ("backlog", "--strict"),
        ("adapters dry run", "--dry-run"),
        ("install dry run", "./.tmp/zen-home"),
        ("install cycle", "./.tmp/zen-home"),
        ("doc links", "docs/**/*.md"),
    ]

    def test_the_seven_gates_are_present_and_ordered(self):
        actual = [(g.name, g.commands[0][-1]) for g in rc.gates()]
        self.assertEqual(self.EXPECTED, actual,
                         "the gate set changed; if that was deliberate, update this list "
                         "and checks.yml's expectations together")

    def test_only_the_install_cycle_cleans_up_after_itself(self):
        # The cleanup is what makes S-004 hold when a gate fails midway. If another gate
        # grows one, that is a design change worth noticing rather than absorbing.
        with_cleanup = [g.name for g in rc.gates() if g.cleanup is not None]
        self.assertEqual(["install cycle"], with_cleanup)

    def test_the_install_cycle_reverses_what_it_placed(self):
        cycle = next(g for g in rc.gates() if g.name == "install cycle")
        self.assertIn("--uninstall", cycle.cleanup)
        self.assertIn(rc.THROWAWAY_HOME, cycle.cleanup)


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

    def test_ci_does_not_separately_restate_any_gate(self):
        # One rule, two callers. An inline copy of the link rule drifted once already and
        # let a correctly quoted changelog entry pass --strict and fail CI (chore-0029).
        # This is that lesson made mechanical for all seven.
        restated = [g.commands[0][-1] for g in rc.gates()]
        for tail in restated:
            with self.subTest(tail=tail):
                self.assertNotIn(f"run: python {tail}", self.workflow)
        self.assertNotIn("validate-skills.py", self.workflow)
        self.assertNotIn("unittest discover", self.workflow)


class ArgumentTests(unittest.TestCase):
    """The Proposed Surface says no flags. An unrecognised one is refused, not ignored."""

    def test_any_argument_is_refused(self):
        buf = io.StringIO()
        code = rc.main(["--only", "tests"], out=buf)
        self.assertEqual(2, code)
        self.assertIn("takes no arguments", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
