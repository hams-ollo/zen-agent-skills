"""Acceptance tests for .agents/hooks/install-currency-reminder.py (feat-0049).

There is no approved spec for this hook, so these are derived from feat-0049's acceptance
criteria rather than from `S-NNN` scenarios, and the criterion each group covers is named
in its docstring. They are acceptance tests, not characterization ones: the hook is new, so
there is no prior behavior to pin.

test-quality notes: every scenario is covered at the lowest faithful layer, calling
`evaluate()` and `main()` directly against a temporary filesystem, matching the convention
in test_hooks.py and test_hooks_reachability.py. The one exception is the two
working-directory group, which spawns a subprocess on purpose: the defect it protects
against is a hook that answers correctly only from the repository root, and that defect is
invisible to an in-process call which never has a working directory of its own.

Oracles assert the exact emitted object or exact silence, never "does not crash", because
a hook that emits nothing is exactly what a broken one also produces. That symmetry is the
whole point here and it is why the speaking tests and the silent tests are equally
load-bearing: `bug-0021` recorded a hook measured in a live cloud session that emitted
nothing for the wrong reason, and every unit test it had was still green.

Baselines are built with install.py's own `digest_tree`, not with the hook's, so a
"matching" fixture is matching according to the code that really writes manifests. Using
the code under test to build its own expected input would make the silence tests agree with
themselves.

The defect each group protects against:
  speaks       - the install goes stale and the session is never told (criterion 1)
  inoperative  - the currency sensor has no baseline and says nothing about it (criterion 2)
  stays quiet  - the hook fires on a correct install and gets uninstalled (criterion 3)
  costs        - every session start outside this repo pays to be told nothing (criterion 4)
  vocabulary   - the hook invents a verdict install.py --check does not have (criterion 5)
  wiring       - the hook is placed, registered on the wrong event, and never fires,
                 or answers only from the repository root (criterion 6)
  documented   - the two hook tables stop listing what the module ships (criterion 7)
  robustness   - a malformed payload takes down the session
  drafts       - the never-installed check disagrees with install.py about what a draft is
"""
import ast
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
MODULE_PATH = HOOKS_DIR / "install-currency-reminder.py"
INSTALL_PATH = REPO_ROOT / "scripts" / "install.py"

# Hyphenated filename, so it is not importable by a normal import statement.
_spec = importlib.util.spec_from_file_location("install_currency_reminder", MODULE_PATH)
icr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(icr)

_ispec = importlib.util.spec_from_file_location("install_mod_currency", INSTALL_PATH)
install_mod = importlib.util.module_from_spec(_ispec)
_ispec.loader.exec_module(install_mod)


def startup(root=None) -> dict:
    payload = {"hook_event_name": "SessionStart", "source": "startup"}
    if root is not None:
        payload["cwd"] = str(root)
    return payload


def run(payload_text: str):
    """Run main() against raw stdin text, returning (exit_code, stdout_text)."""
    out = io.StringIO()
    code = icr.main(stdin=io.StringIO(payload_text), stdout=out)
    return code, out.getvalue()


class Fixture:
    """A throwaway repository plus the install home its manifest points at.

    Deliberately not a copy of this repository. Every test builds only the skills it needs,
    so a test that expects silence cannot be quietly rescued (or broken) by whatever the
    real tree happens to contain today.
    """

    def __init__(self, base: Path):
        self.base = base
        self.root = base / "repo"
        self.home = base / "home"
        (self.root / "scripts").mkdir(parents=True)
        self.entries = []

    def write_skill(self, name: str, body: str = "hello", draft: bool = False) -> Path:
        directory = self.root / ".agents" / "skills" / name
        directory.mkdir(parents=True, exist_ok=True)
        meta = "metadata:\n  status: draft\n" if draft else ""
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture skill.\n{meta}---\n\n{body}\n",
            encoding="utf-8", newline="\n")
        return directory

    def record(self, name: str, digests=None, place_target: bool = True,
               tool: str = "claude", entry_name=None):
        """Record an install of `name`, with a baseline taken from the tree right now.

        `digests=None` means "take the real baseline". Passing `{}` reproduces the
        pre-digest manifests `install.py` used to write, which is the `unknown` state.
        """
        source = self.root / ".agents" / "skills" / name
        target = self.home / f".{tool}" / "skills" / name
        if place_target:
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text("installed copy\n",
                                             encoding="utf-8", newline="\n")
        entry = {
            "tool": tool,
            "name": entry_name or name,
            "target": str(target),
            "mode": "copy",
            "source": str(source),
            # install.py's own derivation, so a "current" fixture is current according to
            # the code that actually writes manifests rather than to the code under test.
            "digests": install_mod.digest_tree(source) if digests is None else digests,
        }
        self.entries.append(entry)
        return entry

    def write_manifest(self):
        (self.root / "scripts" / ".install-manifest.json").write_text(
            json.dumps({"entries": self.entries}, indent=2),
            encoding="utf-8", newline="\n")

    def edit_source(self, name: str, body: str):
        """Move the kit's copy after the install was recorded. This is staleness."""
        (self.root / ".agents" / "skills" / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture skill.\n---\n\n{body}\n",
            encoding="utf-8", newline="\n")


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(Path(self._tmp.name))

    def context(self, root=None):
        """The single injected paragraph, asserted to be exactly one object."""
        out = icr.evaluate(startup(), root=root or self.fx.root)
        self.assertIsInstance(out, dict, "the hook stayed silent when it should have spoken")
        self.assertEqual(set(out), {"hookSpecificOutput"})
        inner = out["hookSpecificOutput"]
        self.assertEqual(inner["hookEventName"], "SessionStart")
        return inner["additionalContext"]


class SpeaksTests(FixtureCase):
    """Criterion 1: a manifest whose digests no longer match the tree names what drifted."""

    def test_a_stale_install_produces_one_reminder_naming_the_stale_skill(self):
        self.fx.write_skill("doc-sync")
        self.fx.write_skill("new-task")
        self.fx.record("doc-sync")
        self.fx.record("new-task")
        self.fx.edit_source("doc-sync", "the kit moved after this was installed")
        self.fx.write_manifest()

        text = self.context()
        self.assertIn(icr.BANNER, text)
        self.assertIn("doc-sync", text)
        self.assertNotIn("new-task", text)
        self.assertIn("stale", text)
        self.assertIn("install.py --check", text)

    def test_stdout_is_exactly_one_json_object(self):
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        self.fx.edit_source("doc-sync", "moved")
        self.fx.write_manifest()

        code, text = run(json.dumps(startup(self.fx.root)))
        self.assertEqual(code, 0)
        self.assertTrue(text, "the hook wrote nothing on a stale install")
        decoder = json.JSONDecoder()
        _, end = decoder.raw_decode(text)
        self.assertEqual(text[end:].strip(), "", "more than one object on stdout")

    def test_a_missing_installed_target_is_reported_as_stale(self):
        # The install was deleted from the home. install.py --check calls this `diverged`
        # and so does the hook, rather than inventing a word for it.
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync", place_target=False)
        self.fx.write_manifest()
        self.assertIn("doc-sync", self.context())

    def test_a_skill_in_the_tree_with_no_record_is_reported_as_never_installed(self):
        # The `review-depth` case from feat-0049's problem statement: present in the kit,
        # absent from every manifest entry, and reported by nothing.
        self.fx.write_skill("doc-sync")
        self.fx.write_skill("review-depth")
        self.fx.record("doc-sync")
        self.fx.write_manifest()

        text = self.context()
        self.assertIn("review-depth", text)
        self.assertIn("never installed", text)

    def test_one_skill_installed_for_two_tools_is_named_once(self):
        # Two entries, one thing to fix. Naming it twice reads like two problems.
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync", tool="claude")
        self.fx.record("doc-sync", tool="opencode")
        self.fx.edit_source("doc-sync", "moved")
        self.fx.write_manifest()
        self.assertEqual(self.context().count("doc-sync"), 1)


class InoperativeTests(FixtureCase):
    """Criterion 2: entries with no digests say the currency check cannot answer."""

    def test_entries_with_no_digests_report_the_check_as_inoperative(self):
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync", digests={})
        self.fx.write_manifest()

        text = self.context()
        self.assertIn("INOPERATIVE", text)
        self.assertIn("baseline", text)
        self.assertIn("doc-sync", text)

    def test_a_missing_digests_key_is_treated_the_same_as_an_empty_one(self):
        # Falsiness, not `is None`, mirroring install.py: a present-but-empty map is no
        # more of a baseline than a missing one, and treating it as valid is how a
        # hand-edited manifest once reported a clean verdict for an unrecorded entry.
        self.fx.write_skill("doc-sync")
        entry = self.fx.record("doc-sync")
        entry.pop("digests")
        self.fx.write_manifest()
        self.assertIn("INOPERATIVE", self.context())

    def test_an_entry_whose_source_is_gone_is_reported_as_uncomparable(self):
        self.fx.write_skill("doc-sync")
        entry = self.fx.record("doc-sync")
        entry["source"] = str(self.fx.root / ".agents" / "skills" / "never-existed")
        self.fx.write_manifest()
        self.assertIn("could not be compared", self.context())


class StaysQuietTests(FixtureCase):
    """Criterion 3: a manifest that matches the tree produces no output and exits 0.

    Without this group, every test above is satisfied by a hook that speaks unconditionally,
    which is the same as a hook that says nothing.
    """

    def test_a_current_install_produces_no_output(self):
        self.fx.write_skill("doc-sync")
        self.fx.write_skill("new-task")
        self.fx.record("doc-sync")
        self.fx.record("new-task")
        self.fx.write_manifest()
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))

    def test_a_current_install_exits_zero_with_empty_stdout(self):
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        self.fx.write_manifest()
        code, text = run(json.dumps(startup(self.fx.root)))
        self.assertEqual(code, 0)
        self.assertEqual(text, "")

    def test_a_draft_skill_that_was_never_installed_is_not_reported(self):
        # Drafts are deliberately not installed, so reporting one would make the hook fire
        # on a perfectly correct install, and a reminder that does that gets uninstalled.
        self.fx.write_skill("doc-sync")
        self.fx.write_skill("user-testing", draft=True)
        self.fx.record("doc-sync")
        self.fx.write_manifest()
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))

    def test_an_adopted_lens_whose_upstream_moved_is_not_reported(self):
        # install.py --check exits 0 on `revised` and leaves the adopter's copy alone,
        # because a lens is the one file they were invited to rewrite. Firing on it every
        # session would be crying wolf about a file that is theirs.
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        rules = self.fx.root / ".agents" / "rules"
        rules.mkdir(parents=True)
        (rules / "house-style.md").write_text("original\n", encoding="utf-8", newline="\n")
        target = self.fx.home / ".claude" / "rules"
        target.mkdir(parents=True)
        (target / "house-style.md").write_text("mine\n", encoding="utf-8", newline="\n")
        self.fx.entries.append({
            "tool": "claude", "name": "rules", "target": str(target), "mode": "copy",
            "source": str(rules), "digests": install_mod.digest_tree(rules),
        })
        (rules / "house-style.md").write_text("upstream moved\n",
                                              encoding="utf-8", newline="\n")
        self.fx.write_manifest()
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))

    def test_a_symlinked_entry_is_not_reported_as_stale(self):
        # It cannot be stale, because it is the source.
        self.fx.write_skill("doc-sync")
        source = self.fx.root / ".agents" / "skills" / "doc-sync"
        target = self.fx.home / ".claude" / "skills" / "doc-sync"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.symlink_to(source, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("this platform or account cannot create directory symlinks")
        self.fx.entries.append({
            "tool": "claude", "name": "doc-sync", "target": str(target),
            "mode": "symlink", "source": str(source),
            "digests": install_mod.digest_tree(source),
        })
        self.fx.write_manifest()
        self.fx.edit_source("doc-sync", "the source moved, and the link moved with it")
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))


class CostTests(FixtureCase):
    """Criterion 4: no manifest means no output, exit 0, and no other file read.

    This runs at every session start on the adopter's machine, and no manifest is the
    common case, so the price of the common case is a behavior worth pinning rather than
    an implementation detail.
    """

    def test_no_manifest_produces_no_output_and_exits_zero(self):
        self.fx.write_skill("doc-sync")
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))
        code, text = run(json.dumps(startup(self.fx.root)))
        self.assertEqual(code, 0)
        self.assertEqual(text, "")

    def test_no_manifest_reads_no_file_at_all(self):
        # Asserted by making every read fail loudly rather than by counting them: an
        # AssertionError raised inside evaluate() escapes it (only main() swallows), so a
        # hook that enumerates skills or digests a tree before checking for the manifest
        # fails this by name instead of merely being slow.
        self.fx.write_skill("doc-sync")
        self.fx.write_skill("new-task")
        original_text, original_bytes = Path.read_text, Path.read_bytes

        def boom(self, *args, **kwargs):
            raise AssertionError(f"the no-manifest path read {self}")

        Path.read_text, Path.read_bytes = boom, boom
        try:
            self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))
        finally:
            Path.read_text, Path.read_bytes = original_text, original_bytes

    def test_a_directory_with_no_repository_above_it_is_silent(self):
        empty = Path(self._tmp.name) / "somewhere" / "else"
        empty.mkdir(parents=True)
        self.assertIsNone(icr.evaluate(startup(), root=empty))


class PreciseFilterTests(FixtureCase):
    """Two-stage filtering: the harness matcher is coarse, this is the precise check."""

    def setUp(self):
        super().setUp()
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        self.fx.edit_source("doc-sync", "moved")
        self.fx.write_manifest()

    def test_the_stale_state_really_does_fire_for_this_fixture(self):
        # The control for the three tests below. Without it they pass against a hook that
        # is silent for some entirely different reason.
        self.assertIsNotNone(icr.evaluate(startup(), root=self.fx.root))

    def test_a_continued_session_is_silent(self):
        for source in ("resume", "clear", "compact", "fork"):
            with self.subTest(source=source):
                payload = startup(self.fx.root)
                payload["source"] = source
                self.assertIsNone(icr.evaluate(payload, root=self.fx.root))

    def test_a_different_lifecycle_event_is_silent(self):
        payload = startup(self.fx.root)
        payload["hook_event_name"] = "PostToolUse"
        self.assertIsNone(icr.evaluate(payload, root=self.fx.root))

    def test_the_firing_sources_constant_is_startup_only(self):
        self.assertEqual(icr.FIRING_SOURCES, {"startup"})


class RobustnessTests(FixtureCase):
    """A guardrail that breaks a session because it could not parse its payload is worse
    than no guardrail."""

    def test_malformed_json_is_survived_silently(self):
        self.assertEqual(run("{not json"), (0, ""))

    def test_empty_stdin_is_survived_silently(self):
        self.assertEqual(run(""), (0, ""))

    def test_a_non_object_payload_is_survived_silently(self):
        self.assertEqual(run("[1, 2, 3]"), (0, ""))
        self.assertIsNone(icr.evaluate("not a dict"))

    def test_a_manifest_that_is_not_json_is_survived_silently(self):
        self.fx.write_skill("doc-sync")
        (self.fx.root / "scripts" / ".install-manifest.json").write_text(
            "{ broken", encoding="utf-8", newline="\n")
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))

    def test_a_manifest_with_no_entries_list_is_survived_silently(self):
        self.fx.write_skill("doc-sync")
        (self.fx.root / "scripts" / ".install-manifest.json").write_text(
            json.dumps({"entries": "not a list"}), encoding="utf-8", newline="\n")
        self.assertIsNone(icr.evaluate(startup(), root=self.fx.root))

    def test_a_junk_entry_does_not_take_the_hook_down(self):
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        self.fx.entries.append("this is not an entry")
        self.fx.write_manifest()
        code, _ = run(json.dumps(startup(self.fx.root)))
        self.assertEqual(code, 0)


def _install_check_counts():
    """The verdict words `install.py`'s `check()` counts, read from its source.

    Parsed rather than executed, because executing it means running a real check against a
    real home. Parsed rather than string-matched, because the same six words appear in
    prose throughout that file and a text scan would agree with the documentation instead
    of with the code.
    """
    tree = ast.parse(INSTALL_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "check"):
            continue
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Dict)):
                continue
            if any(isinstance(t, ast.Name) and t.id == "counts" for t in sub.targets):
                return {k.value for k in sub.value.keys}
    return None


def _returned_strings(expr, words):
    """String literals a return EXPRESSION can evaluate to, branches included.

    Walking the whole Return subtree was tried first and collected `"name"` out of
    `entry.get("name")` in a conditional return, which is an argument and not a verdict. A
    guard that fires on the arguments of its own subject gets loosened until it catches
    nothing, so the expression is resolved instead of scanned.
    """
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        words.add(expr.value)
    elif isinstance(expr, ast.IfExp):
        _returned_strings(expr.body, words)
        _returned_strings(expr.orelse, words)


def _classify_returns():
    """Every string literal `classify()` in the hook can return."""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    words = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "classify"):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and sub.value is not None:
                _returned_strings(sub.value, words)
    return words


class VocabularyTests(unittest.TestCase):
    """Criterion 5: the hook's verdicts are install.py --check's, in both directions.

    The two implementations are genuinely duplicated: the hooks contract forbids the hook
    from importing this repository, so the agreement cannot be had by construction and is
    asserted here instead, the way bug-0026 asks for its two validator copies.

    Note for whoever reads feat-0049 next: the task says "three states". The check has six
    (`ok`, `linked`, `revised`, `diverged`, `unknown`, `error`), which the task's own
    Implementation notes half-acknowledge by quoting `current`, `diverged` and `unknown`
    from the printed summary. This pins the real vocabulary, which is the stronger reading
    of the criterion's operative clause: neither side may gain a state the other lacks.
    """

    def test_the_two_vocabularies_are_the_same_set(self):
        counts = _install_check_counts()
        self.assertIsNotNone(counts, "could not find `counts` in install.py's check()")
        self.assertEqual(set(icr.VERDICTS), counts)

    def test_classify_can_return_every_verdict_and_no_other(self):
        # Equality in both directions: a word in the constant that nothing produces is a
        # vocabulary the hook only claims to share, which is the failure this pins.
        returned = _classify_returns()
        self.assertTrue(returned, "could not read any verdict out of classify()")
        self.assertEqual(returned, set(icr.VERDICTS))

    def test_every_reporting_verdict_is_a_real_verdict(self):
        self.assertEqual(set(icr.REPORTING_VERDICTS) - set(icr.VERDICTS), set())

    def test_the_silent_verdicts_are_the_ones_check_exits_zero_on(self):
        # `ok`, `linked` and `revised` are exit 0 for install.py --check, and they are the
        # three the hook deliberately says nothing about. Pinning the complement means
        # moving one out of `REPORTING_VERDICTS` fails here rather than going unnoticed.
        self.assertEqual(set(icr.VERDICTS) - set(icr.REPORTING_VERDICTS),
                         {"ok", "linked", "revised"})


class DraftAgreementTests(unittest.TestCase):
    """The hook re-reads frontmatter that install.py already reads. They must agree."""

    def test_the_two_draft_readers_agree_on_every_skill_this_kit_ships(self):
        skills = install_mod.discover_skills()
        self.assertTrue(skills, "no skills found to compare the two readers against")
        for skill in skills:
            with self.subTest(skill=skill.name):
                self.assertEqual(icr.is_draft(skill),
                                 install_mod.status_of(skill) == install_mod.DRAFT_STATUS)

    def test_a_status_line_in_the_body_is_prose_and_not_a_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "some-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: some-skill\ndescription: x.\n---\n\n"
                "A body that mentions `  status: draft` as prose.\n",
                encoding="utf-8", newline="\n")
            self.assertFalse(icr.is_draft(skill))
            self.assertNotEqual(install_mod.status_of(skill), install_mod.DRAFT_STATUS)


class RegistrationTests(unittest.TestCase):
    """Criterion 6: registered on the right event, and answering from any directory.

    `tests/test_hooks.py` already asserts that every hook in the module appears in all
    three wirings, and picks this hook up automatically. What it does not check is the
    part that made a hook inert twice before: the EVENT it is registered on, and whether
    the command answers from anywhere but the repository root.
    """

    HOOK = "install-currency-reminder.py"

    def test_the_installer_registers_it_on_the_event_it_actually_fires_on(self):
        rows = [(event, matcher) for script, event, matcher
                in install_mod.HOOK_REGISTRATIONS if script == self.HOOK]
        self.assertEqual(len(rows), 1, f"{self.HOOK} should be registered exactly once")
        event, matcher = rows[0]
        self.assertEqual(event, "SessionStart")
        self.assertIn(matcher, icr.FIRING_SOURCES,
                      "the matcher is narrower than the hook's own firing sources, so the "
                      "hook is placed and never woken")

    def test_the_codex_wiring_registers_it_on_the_same_event_and_matcher(self):
        wiring = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(
            encoding="utf-8"))
        found = [(event, entry["matcher"])
                 for event, entries in wiring["hooks"].items()
                 for entry in entries for hook in entry["hooks"]
                 if self.HOOK in hook["command"]]
        self.assertEqual(len(found), 1, f"{self.HOOK} should appear once in .codex/hooks.json")
        self.assertEqual(found[0], ("SessionStart", "startup"))

    def test_the_opencode_adapter_runs_it_on_the_session_start_event(self):
        adapter = (REPO_ROOT / ".opencode" / "plugins" / "zen-hooks.mjs").read_text(
            encoding="utf-8")
        self.assertIn(self.HOOK, adapter)
        # It must be reached from the session event, not from the tool-result path, or it
        # would fire on every edit and never at startup.
        event_block = adapter.split("event: async")[1].split("tool.execute.after")[0]
        self.assertIn(self.HOOK, event_block)

    def test_it_is_not_added_to_the_committed_claude_settings(self):
        # The conventions section of AGENTS.md records exactly one committed hook
        # registration as a deliberate exception, and says adding a second is a new
        # decision. This pins that this change did not quietly spend it.
        settings = (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
        self.assertNotIn(self.HOOK, settings)


class WorkingDirectoryTests(unittest.TestCase):
    """Criterion 6, second half: the registered command answers from a subdirectory too.

    Spawned as a subprocess on purpose. The defect is a hook whose answer depends on the
    process working directory, and an in-process call has no working directory of its own,
    so no in-process test can see it. chore-0038 item 3 recorded a registration that
    resolved only from the repository root, and install.py:341 records a hook placed on an
    event nothing fires. Both are invisible from the outside.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(Path(self._tmp.name))
        self.fx.write_skill("doc-sync")
        self.fx.record("doc-sync")
        self.fx.edit_source("doc-sync", "the kit moved after this was installed")
        self.fx.write_manifest()
        self.nested = self.fx.root / "docs" / "spec"
        self.nested.mkdir(parents=True)
        self.elsewhere = Path(self._tmp.name) / "unrelated"
        self.elsewhere.mkdir()

    def _run(self, cwd: Path, payload: dict):
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH)],
            input=json.dumps(payload), capture_output=True, text=True,
            cwd=str(cwd), timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_the_answer_is_the_same_from_the_root_and_from_a_subdirectory(self):
        # No `cwd` in the payload, so the hook falls back to the process working
        # directory, which is the case a harness that omits the field produces.
        from_root = self._run(self.fx.root, startup())
        from_nested = self._run(self.nested, startup())
        self.assertIn("doc-sync", from_root)
        self.assertEqual(from_root, from_nested)

    def test_the_payload_cwd_wins_over_the_process_working_directory(self):
        out = self._run(self.elsewhere, startup(self.fx.root))
        self.assertIn("doc-sync", out)

    def test_a_process_outside_any_repository_says_nothing(self):
        self.assertEqual(self._run(self.elsewhere, startup()), "")


class DocumentedTests(unittest.TestCase):
    """Criterion 7: both hook tables list it, with its shape and its firing event."""

    HOOK = "install-currency-reminder"

    def _row(self, text: str, needle: str) -> str:
        rows = [line for line in text.splitlines()
                if line.startswith("|") and needle in line]
        self.assertEqual(len(rows), 1, f"expected exactly one table row naming {needle}")
        return rows[0]

    def test_the_hooks_readme_table_names_its_shape_and_event(self):
        row = self._row((HOOKS_DIR / "README.md").read_text(encoding="utf-8"),
                        f"{self.HOOK}.py")
        self.assertIn("reminder", row)
        self.assertIn("SessionStart", row)

    def test_the_catalog_hooks_table_lists_it_as_a_reminder(self):
        row = self._row((REPO_ROOT / "docs" / "CATALOG.md").read_text(encoding="utf-8"),
                        self.HOOK)
        self.assertIn("reminder", row)


class DigestAgreementTests(unittest.TestCase):
    """The hook re-derives the digest install.py records. A different derivation would
    disagree with the very baseline it is being compared against."""

    def test_the_two_digest_derivations_produce_the_same_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tree"
            (root / "references").mkdir(parents=True)
            (root / "SKILL.md").write_bytes(b"---\nname: x\n---\nbody\r\nwith crlf\n")
            (root / "references" / "notes.md").write_bytes(b"notes\n")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_bytes(b"cache")
            mine = icr.digest_tree(root)
            theirs = install_mod.digest_tree(root)
            self.assertEqual(mine, theirs)
            self.assertEqual(set(mine), {"SKILL.md", "references/notes.md"})
            self.assertEqual(mine["references/notes.md"],
                             hashlib.sha256(b"notes\n").hexdigest())


if __name__ == "__main__":
    unittest.main()
