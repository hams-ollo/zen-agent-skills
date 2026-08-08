"""Acceptance tests for the .agents/hooks/ module.

Covers feat-0038: the module contract stated in .agents/hooks/README.md, exercised through
delegation-reminder.py, the first hook to ship. Standard library only, per the conventions
section of AGENTS.md.

test-quality notes: every scenario here is covered at the lowest faithful layer, calling
main() and evaluate() directly with injected streams rather than spawning a subprocess. A
subprocess would test the interpreter lookup rather than the hook, and the interpreter
lookup lives in the harness adapters, not in the Python. Oracles assert the exact emitted
object or exact silence, never "does not crash", because "does not crash" is precisely the
outcome a broken hook that emits nothing would also produce.

The defect each group protects against:
  fires        - the reminder silently stops firing and delegation goes unchecked again
  precise set  - a broad harness matcher fires the hook on the unrelated task-list tools
  robustness   - a malformed payload takes down the user's session
"""
import importlib.util
import io
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
MODULE_PATH = HOOKS_DIR / "delegation-reminder.py"

# Hyphenated filename, so it is not importable by a normal import statement.
_spec = importlib.util.spec_from_file_location("delegation_reminder", MODULE_PATH)
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)


def run(payload_text: str):
    """Run main() against raw stdin text, returning (exit_code, stdout_text)."""
    out = io.StringIO()
    code = dr.main(stdin=io.StringIO(payload_text), stdout=out)
    return code, out.getvalue()


def run_payload(payload: dict):
    return run(json.dumps(payload))


def post_tool_use(tool_name: str) -> dict:
    return {"hook_event_name": "PostToolUse", "tool_name": tool_name}


class ReminderFiresTests(unittest.TestCase):
    """The hook emits its reminder for every tool that hands back delegated work."""

    def test_every_delegation_tool_emits_the_reminder(self):
        # Subtests rather than one test per tool: the tools are equivalent branch cases of
        # one rule, so four near-identical test bodies would assert nothing extra.
        for tool in sorted(dr.DELEGATION_TOOLS):
            with self.subTest(tool=tool):
                code, out = run_payload(post_tool_use(tool))
                self.assertEqual(code, 0)
                emitted = json.loads(out)
                self.assertEqual(
                    emitted["hookSpecificOutput"]["hookEventName"], "PostToolUse")
                self.assertEqual(
                    emitted["hookSpecificOutput"]["additionalContext"], dr.REMINDER)

    def test_the_reminder_says_the_report_is_a_claim_not_evidence(self):
        # The hook's entire value is this message. An empty or truncated REMINDER would
        # still produce well-formed output and pass every structural assertion above.
        code, out = run_payload(post_tool_use("Task"))
        self.assertEqual(code, 0)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("claim of completion, not evidence", context)
        self.assertIn("verify", context)

    def test_stdout_is_exactly_one_json_object(self):
        # The harness parses stdout. A second object, or a trailing newline of prose,
        # corrupts the exchange.
        _, out = run_payload(post_tool_use("Task"))
        decoder = json.JSONDecoder()
        _, end = decoder.raw_decode(out)
        self.assertEqual(out[end:].strip(), "")


class PreciseFilterTests(unittest.TestCase):
    """The hook re-checks the tool name, so a broad harness matcher cannot misfire it."""

    def test_a_task_list_tool_is_not_treated_as_delegation(self):
        # The registered matcher is allowed to be broad. These tools contain "Task" but
        # return no delegated work, and a reminder on every todo-list update is noise that
        # gets the hook uninstalled.
        for tool in ("TaskCreate", "TaskUpdate", "TaskList", "TaskStop"):
            with self.subTest(tool=tool):
                code, out = run_payload(post_tool_use(tool))
                self.assertEqual(code, 0)
                self.assertEqual(out, "")

    def test_an_unrelated_tool_is_silent(self):
        code, out = run_payload(post_tool_use("Read"))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_a_different_lifecycle_event_is_silent(self):
        # Same tool, wrong event. Registering this hook on PreToolUse would fire it before
        # any report exists, which is advice about nothing.
        code, out = run_payload({"hook_event_name": "PreToolUse", "tool_name": "Task"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")


class RobustnessTests(unittest.TestCase):
    """Malformed input exits 0 and emits nothing. A guardrail must not break the session."""

    def test_malformed_json_is_survived_silently(self):
        code, out = run("this is not json {{{")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_empty_stdin_is_survived_silently(self):
        code, out = run("")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_a_non_object_payload_is_survived_silently(self):
        # Valid JSON, wrong shape. evaluate() must not assume a dict.
        for text in ("[]", '"a string"', "42", "null"):
            with self.subTest(payload=text):
                code, out = run(text)
                self.assertEqual(code, 0)
                self.assertEqual(out, "")

    def test_missing_fields_are_survived_silently(self):
        for payload in ({}, {"hook_event_name": "PostToolUse"}, {"tool_name": "Task"}):
            with self.subTest(payload=payload):
                code, out = run_payload(payload)
                self.assertEqual(code, 0)
                self.assertEqual(out, "")


class ModuleContractTests(unittest.TestCase):
    """Rules from .agents/hooks/README.md that apply to every hook in the module."""

    def hook_sources(self):
        return sorted(p for p in HOOKS_DIR.glob("*.py"))

    def test_the_module_ships_at_least_one_hook(self):
        # Guards the case where a refactor moves the hooks and every other test in this
        # file passes vacuously against an empty directory.
        self.assertTrue(self.hook_sources(), f"no hooks found under {HOOKS_DIR}")

    def test_no_hook_imports_from_this_repository(self):
        # A hook ships without this repository around it. A shared helper import would
        # work here and dangle everywhere it is actually installed, which is the silent
        # failure that once shipped house-review with no rubric.
        for path in self.hook_sources():
            with self.subTest(hook=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("from scripts", text)
                self.assertNotIn("import scripts", text)
                self.assertNotIn("sys.path", text)

    def test_every_hook_exposes_an_injectable_main(self):
        for path in self.hook_sources():
            with self.subTest(hook=path.name):
                spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.assertTrue(callable(getattr(mod, "main", None)))
                code = mod.main(stdin=io.StringIO(""), stdout=io.StringIO())
                self.assertEqual(code, 0)


class WiringConsistencyTests(unittest.TestCase):
    """The delegation tool set is encoded in more than one place. This is where they meet.

    `DELEGATION_TOOLS` lives in the hook; the harness matchers live in `.codex/hooks.json`
    and in the registration `install.py` prints. A tool added to one and not the others
    produces a hook that is silently inert on whichever harness was missed, which is the
    worst failure available to a guardrail: nothing fires, so nothing looks wrong.

    That is not hypothetical. Adding `Agent` to the set (found by dogfooding, where the
    reminder did not fire on an Agent SDK delegation) updated the hook, the Codex matcher,
    and the installer, and left a test pinning the old string. These tests assert the
    relationship rather than any one spelling, so the next tool added is covered without
    anyone remembering to come back here.
    """

    HOOK = "delegation-reminder.py"

    @staticmethod
    def _flatten(wiring):
        """Every (command, matcher) in a wiring, across every lifecycle event.

        Deliberately not scoped to `PostToolUse`. It was, until feat-0046 added the first
        hook on another event and this class reported it missing from two wirings that had
        in fact been updated correctly. A consistency test that only reads one event
        cannot support the claim in its own name, and the failure direction is the bad
        one: it would have passed for a hook wired nowhere on any event but PostToolUse.
        """
        return [(h["command"], e["matcher"])
                for entries in wiring["hooks"].values()
                for e in entries for h in e["hooks"]]

    def _entries(self):
        """Entries from each wiring, as (source name, [(command, matcher)])."""
        codex = json.loads(
            (REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        yield ".codex/hooks.json", self._flatten(codex)

        spec = importlib.util.spec_from_file_location(
            "install_mod", REPO_ROOT / "scripts" / "install.py")
        install_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install_mod)
        block = json.loads(install_mod.claude_registration(Path("/tmp/home")))
        yield "install.py claude_registration", self._flatten(block)

    def matcher_sources(self):
        """Each wiring's matcher for the delegation hook, found by script name not index.

        Looking it up by position broke the moment a second hook was registered, which is
        the kind of brittleness this class exists to remove rather than reproduce.
        """
        for name, entries in self._entries():
            matchers = [m for cmd, m in entries if self.HOOK in cmd]
            self.assertEqual(len(matchers), 1,
                             f"{name} should register {self.HOOK} exactly once")
            yield name, matchers[0]

    def test_every_hook_in_the_module_is_registered_everywhere(self):
        """A hook that ships without a matcher is placed and never fires.

        That is the failure the feat-0038 dogfood found on the Agent tool name: installed,
        correct-looking, and silently inert. This asserts the module and its wirings cannot
        drift apart in the other direction either, by a hook being added and not wired.
        """
        shipped = {p.name for p in HOOKS_DIR.glob("*.py")}
        self.assertTrue(shipped, "no hooks found to check")
        for name, entries in self._entries():
            commands = " ".join(cmd for cmd, _ in entries)
            for hook in sorted(shipped):
                with self.subTest(source=name, hook=hook):
                    self.assertIn(hook, commands, f"{hook} is not registered in {name}")
        adapter = (REPO_ROOT / ".opencode" / "plugins" / "zen-hooks.mjs").read_text(
            encoding="utf-8")
        for hook in sorted(shipped):
            with self.subTest(source=".opencode adapter", hook=hook):
                self.assertIn(hook, adapter, f"{hook} is not invoked by the opencode adapter")

    def test_every_matcher_covers_every_delegation_tool(self):
        for name, matcher in self.matcher_sources():
            for tool in sorted(dr.DELEGATION_TOOLS):
                with self.subTest(source=name, tool=tool):
                    self.assertRegex(
                        tool, matcher,
                        f"{name} does not fire for {tool!r}, so the hook is inert there")

    def test_no_matcher_fires_on_the_task_list_tools(self):
        # The matcher is allowed to be broader than the hook's set, since the hook
        # re-checks. It is not allowed to be so broad that it wakes the hook on every
        # todo-list update, which is the noise that gets a guardrail uninstalled.
        for name, matcher in self.matcher_sources():
            for tool in ("TaskCreate", "TaskUpdate", "TaskList", "TaskStop"):
                with self.subTest(source=name, tool=tool):
                    self.assertNotRegex(
                        tool, matcher, f"{name} fires on the unrelated {tool!r}")


if __name__ == "__main__":
    unittest.main()
