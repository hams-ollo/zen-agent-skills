"""Acceptance tests for .agents/hooks/skill-reachability-reminder.py (feat-0046).

Derived from docs/spec/cloud-executable.md, S-008 to S-016.

test-quality notes: every scenario is covered at the lowest faithful layer, calling
evaluate() and main() directly with injected streams and a temporary filesystem, matching
the convention in test_hooks.py. Oracles assert the exact emitted object or exact silence,
never "does not crash", because a hook that emits nothing is exactly what a broken one
also produces.

The defect each group protects against:
  reports      - a session starts with nothing loaded and is never told (S-008)
  foreign      - somebody else's skill library is counted as this kit's, so the hook is
                 silent in the exact state S-008 says it must speak in (bug-0021)
  stays quiet  - the hook speaks on every start and becomes a line agents skip (S-010)
  source       - it repeats itself on resume, clear, compact, and fork (S-013)
  writes       - a hook that never writes starts writing a cache or marker (S-014)
  robustness   - a malformed payload takes down the session (S-015)
  no detection - it grows an environment check and answers differently by host (S-016)
"""
import ast
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".agents" / "hooks" / "skill-reachability-reminder.py"

_spec = importlib.util.spec_from_file_location("skill_reachability_reminder", MODULE_PATH)
srr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srr)


def _analyse(path: Path):
    """Imported top-level modules, called names, and accessed attributes in a source file.

    Structural guards below assert on this rather than on raw text. Scanning text was
    tried first and fired on the word "subprocess" inside a docstring, which is prose
    describing why the hook does NOT spawn one. A guard that fails on its own
    documentation gets loosened until it catches nothing, so it is parsed instead.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules, calls, attributes = set(), [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                calls.append(target.attr)
            elif isinstance(target, ast.Name):
                calls.append(target.id)
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
    return modules, calls, attributes


def _attribute_chains(path: Path):
    """Every `name.attr` pair in a source file, for catching reads like `sys.platform`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {f"{n.value.id}.{n.attr}" for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}


# A library that is genuinely somebody else's. These are the names a stock cloud
# container ships at ~/.claude/skills, taken from the live session recorded in bug-0021,
# where 24 of them silenced the hook with none of this kit installed.
FOREIGN_SKILL_NAMES = ("brand-guidelines", "canvas-design", "docx", "pdf", "pptx", "xlsx")


def place_skill(root: Path, subpath: Path, name="doc-sync"):
    """Create one discoverable skill under root/subpath.

    The default name is a real skill of this kit, because reachability is a question
    about THIS kit's skills and a synthetic `alpha` answers it no. Pass a foreign name
    (or use `place_foreign_library`) for the other side of that question.
    """
    skill = root / subpath / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    return skill


def place_foreign_library(root: Path, subpath: Path, names=FOREIGN_SKILL_NAMES):
    """Create a whole skill library that belongs to somebody else."""
    return [place_skill(root, subpath, name=name) for name in names]


def payload(source="startup", cwd=None, event="SessionStart"):
    p = {"hook_event_name": event, "source": source}
    if cwd is not None:
        p["cwd"] = str(cwd)
    return p


class ReachabilityTests(unittest.TestCase):
    """S-008 to S-012: what counts as reachable, and what is reported."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_skills_anywhere_is_reported(self):
        # S-008.
        out = srr.evaluate(payload(cwd=self.project), home=self.home)
        self.assertIsNotNone(out, "an unreachable session must be told")
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual("SessionStart", out["hookSpecificOutput"]["hookEventName"])
        self.assertIn("NO SKILLS REACHABLE", context)

        # The placing command, specifically, and not merely the string "install.py".
        # Independent verification defeated the original assertion by replacing the
        # placing command with "(ask your administrator)": the test still passed, because
        # REPORT separately mentions `install.py --check` in its currency caveat, so the
        # substring survived while the actionable instruction did not. Blanking the
        # currency mention first is what makes this assert the thing it claims to.
        without_currency_note = context.replace("python scripts/install.py --check", "")
        self.assertIn("python scripts/install.py", without_currency_note,
                      "the report must name the command that PLACES skills, not only the "
                      "one that checks whether existing ones are current")

    def test_project_scope_skills_count_as_reachable(self):
        # S-009. The case a cloud session would be fixed by.
        place_skill(self.project, Path(".claude") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_user_scope_skills_count_as_reachable(self):
        # S-010, and the ordinary local case.
        place_skill(self.home, Path(".claude") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_the_opencode_user_scope_counts_too(self):
        # `.agents/skills` is opencode's USER-scope directory and install.py targets it.
        # A session with only the opencode tree installed is not an unreachable session.
        place_skill(self.home, Path(".agents") / "skills")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_the_opencode_path_does_NOT_count_at_project_scope(self):
        # The defect this hook shipped with, pinned from the unit side. No harness
        # discovers project-scope skills at `.agents/skills`; it is where a kit keeps its
        # sources. Counting it there is what made the hook silent in its own repository.
        place_skill(self.project, Path(".agents") / "skills")
        self.assertIsNotNone(
            srr.evaluate(payload(cwd=self.project), home=self.home),
            "a project-local .agents/skills tree is a source directory, not a discovery "
            "directory; treating it as reachable is the bug the cloud run exposed")

    def test_an_empty_discovery_directory_is_not_reachable(self):
        # --uninstall leaves the parent directory behind, so treating its existence as
        # reachability would report success for a home whose skills were just removed.
        # Verified against the real installer: after an uninstall the tree is
        # .claude/skills with no files under it.
        (self.home / ".claude" / "skills").mkdir(parents=True)
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_directory_without_skill_md_does_not_count(self):
        # A stray directory in the discovery path is not a skill.
        (self.home / ".claude" / "skills" / "notes").mkdir(parents=True)
        (self.home / ".claude" / "skills" / "notes" / "README.md").write_text("x")
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_stale_install_is_still_reachable_and_still_silent(self):
        # S-011. The hook answers reachability, not currency: a skill whose content has
        # drifted from its source is still reachable, and this hook makes no claim about
        # it. Its silence therefore means reachable and never means current.
        skill = place_skill(self.home, Path(".claude") / "skills")
        (skill / "SKILL.md").write_text("---\nname: alpha\n---\nedited since install\n",
                                        encoding="utf-8")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_skills_present_with_no_manifest_are_reachable(self):
        # S-012. The manifest is not consulted at all: reachability is a filesystem
        # question. install.py --check answers the other one and exits 2 for the same
        # home, which test_install.py already pins. Both answers are correct.
        place_skill(self.home, Path(".claude") / "skills")
        self.assertFalse((self.home / "scripts").exists(), "no manifest anywhere")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))


class ForeignLibraryTests(unittest.TestCase):
    """bug-0021: whose skills were found, not merely whether any were.

    `S-008`'s Given is "a clone where no KIT SKILL is present at project scope or at any
    user-scope discovery directory", and the Proposed Surface defines Reachable as "at
    least one KIT SKILL directory present". Counting any directory holding a SKILL.md
    answers a wider question than the contract asks, and the difference is not
    hypothetical: a stock cloud container ships its own ~/.claude/skills, so the hook was
    silent in a live session with none of this kit installed, which is the exact state
    S-008 says it must speak in.

    The risk running the other way is a recognition so narrow it cries wolf at an adopter
    who installed a subset. `--profile core` is three seeds, so that case has a test here
    too; a reminder that fires on a correct install gets uninstalled within a week, which
    costs more than the miss it fixes.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_foreign_library_at_user_scope_is_not_reachability(self):
        # S-008, reproduced from the live cloud run in bug-0021. This is the case the
        # hook shipped wrong: 24 skills at ~/.claude/skills, not one of them from this
        # kit, and the session proceeded with the report suppressed.
        place_foreign_library(self.home, Path(".claude") / "skills")
        out = srr.evaluate(payload(cwd=self.project), home=self.home)
        self.assertIsNotNone(
            out,
            "a home full of somebody else's skills is not this kit installed; the "
            "contract asks whether a KIT skill is reachable and the answer here is no")
        self.assertIn("REACHABLE",
                      out["hookSpecificOutput"]["additionalContext"])

    def test_a_foreign_library_at_the_opencode_user_scope_is_not_reachability(self):
        # Both user-scope directories install.py targets, so a fix that only narrows one
        # of them does not pass.
        place_foreign_library(self.home, Path(".agents") / "skills")
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_foreign_library_at_project_scope_is_not_reachability(self):
        place_foreign_library(self.project, Path(".claude") / "skills")
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_one_kit_skill_beside_a_foreign_library_is_silence(self):
        # S-010 still holds, and this is the property not to trade away: the foreign
        # library is irrelevant once a kit skill is actually there.
        place_foreign_library(self.home, Path(".claude") / "skills")
        place_skill(self.home, Path(".claude") / "skills", name="fix-batch")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_kit_skills_at_project_scope_only_are_silence(self):
        # S-009, with a foreign library at user scope to prove the two scopes are read
        # independently rather than one masking the other.
        place_foreign_library(self.home, Path(".claude") / "skills")
        place_skill(self.project, Path(".claude") / "skills", name="house-review")
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_partial_install_is_reachable(self):
        # The cries-wolf risk, from the task's Risks section. `--profile core` seeds
        # three skills, so an adopter can legitimately have a handful and no more.
        # Reporting "nothing reachable" at them is the false positive that gets a
        # reminder uninstalled.
        for name in ("project-bootstrap", "init-worktracking", "pr-describe"):
            place_skill(self.home, Path(".claude") / "skills", name=name)
        self.assertIsNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_a_kit_named_directory_without_skill_md_does_not_count(self):
        # Recognition is by name AND by the structural fact every harness agrees on. An
        # empty `doc-sync/` left behind by a half-finished copy is not a loaded skill.
        (self.home / ".claude" / "skills" / "doc-sync").mkdir(parents=True)
        self.assertIsNotNone(srr.evaluate(payload(cwd=self.project), home=self.home))

    def test_the_report_says_whose_skills_are_missing(self):
        # The old wording ("no skill directory found") is false in front of 24 foreign
        # skills, and a report an agent can see is wrong is a report it discounts.
        place_foreign_library(self.home, Path(".claude") / "skills")
        out = srr.evaluate(payload(cwd=self.project), home=self.home)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("kit", context.lower(),
                      "the report must say WHOSE skills are absent, since other skills "
                      "may well be present and loaded")


class ThisRepositoryTests(unittest.TestCase):
    """The hook, run against this repository itself.

    Every other test here builds a synthetic tree, and that is why all of them passed
    while the hook was inert in the one repository that ships it. The first live cloud run
    reported no message at startup; the cause was `.agents/skills` being counted at project
    scope, where this kit keeps its own twenty skill sources.

    A synthetic tree can never catch that, because the thing that broke it is a real
    property of this repository. So this class uses REPO_ROOT and nothing else.
    """

    def test_the_kits_own_source_tree_is_not_mistaken_for_installed_skills(self):
        # The exact cloud-clone case: this repository checked out, nothing installed.
        with tempfile.TemporaryDirectory() as empty_home:
            out = srr.evaluate(payload(cwd=REPO_ROOT), home=Path(empty_home))
        self.assertIsNotNone(
            out,
            "a fresh clone of this repository with nothing installed MUST be told. "
            "`.agents/skills/` here is the kit's source tree, not a discovery directory, "
            "and counting it silenced the hook in the environment it exists for")

    def test_the_sources_it_must_not_count_are_actually_there(self):
        # Guards the guard: if this repository ever stopped committing its skills to
        # `.agents/skills/`, the test above would pass for the wrong reason and quietly
        # stop testing anything.
        sources = REPO_ROOT / ".agents" / "skills"
        self.assertTrue(sources.is_dir())
        self.assertTrue(any((d / "SKILL.md").is_file() for d in sources.iterdir()),
                        "the premise of the test above is that these exist")

    def test_the_recognised_names_are_exactly_the_skills_this_kit_ships(self):
        # The standing objection to recognising a kit skill by name is that the list goes
        # stale the moment the catalog changes, and a hook cannot derive it at runtime
        # without importing from this repository, which the hooks module contract forbids.
        # It cannot derive it, but this repository can CHECK it, and that is what makes
        # the objection survivable: rename or drop a skill and this fails by name.
        #
        # Equality rather than a subset, in both directions. A shipped skill missing from
        # the constant is a false alarm waiting for whoever installs only that skill; a
        # constant naming a skill this kit no longer ships is a foreign directory that
        # could silence the hook by collision.
        shipped = {d.name for d in (REPO_ROOT / ".agents" / "skills").iterdir()
                   if (d / "SKILL.md").is_file()}
        self.assertTrue(shipped, "the premise of this test is that skills exist here")
        self.assertEqual(
            shipped, set(srr.KIT_SKILL_NAMES),
            "KIT_SKILL_NAMES in the hook and the skills under .agents/skills/ have "
            "diverged. Adding, renaming, or removing a skill means editing the constant "
            "in the same commit; that edit is the price of a hook that cannot import "
            "from this repository.")

    def test_a_real_project_scope_install_here_is_reachable(self):
        # The other direction, so the fix cannot be "always report". Placing a skill where
        # Claude Code actually discovers project skills must silence it, even though the
        # home is empty.
        target = REPO_ROOT / ".claude" / "skills"
        created = not target.exists()
        # Named after a real skill of this kit, not `_reachability_probe`: since bug-0021
        # the hook recognises a kit skill by directory name, so a probe named anything
        # else would prove the opposite of what this test claims.
        skill = target / "doc-sync"
        try:
            skill.mkdir(parents=True, exist_ok=True)
            (skill / "SKILL.md").write_text("---\nname: doc-sync\n---\n", encoding="utf-8")
            with tempfile.TemporaryDirectory() as empty_home:
                self.assertIsNone(srr.evaluate(payload(cwd=REPO_ROOT),
                                               home=Path(empty_home)))
        finally:
            # Leave the repository exactly as found. This is the one test here that
            # writes, and it writes into a gitignored-by-absence path it creates itself.
            shutil.rmtree(skill, ignore_errors=True)
            if created:
                shutil.rmtree(target, ignore_errors=True)


class SourceTests(unittest.TestCase):
    """S-013: only a genuinely new session fires."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_startup_fires(self):
        self.assertIsNotNone(
            srr.evaluate(payload("startup", cwd=self.root), home=self.home))

    def test_the_continuing_sources_do_not_fire(self):
        # Each is a session whose agent has already been told. Tested one at a time so a
        # failure names which source regressed.
        for source in ("resume", "clear", "compact", "fork"):
            with self.subTest(source=source):
                self.assertIsNone(
                    srr.evaluate(payload(source, cwd=self.root), home=self.home),
                    f"source {source} must not fire even when unreachable")

    def test_another_event_does_not_fire(self):
        # Two-stage filtering: the harness matcher is coarse, this is the precise check.
        self.assertIsNone(
            srr.evaluate(payload("startup", cwd=self.root, event="PostToolUse"),
                         home=self.home))


class SideEffectTests(unittest.TestCase):
    """S-014: it writes nothing, in every case."""

    def _tree(self, root):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*"))

    def test_the_reporting_path_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "home").mkdir()
            before = self._tree(root)
            srr.evaluate(payload(cwd=root / "project"), home=root / "home")
            self.assertEqual(before, self._tree(root),
                             "the hook must not create a cache, marker, or log")

    def test_the_silent_path_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            place_skill(home, Path(".claude") / "skills")
            before = self._tree(root)
            srr.evaluate(payload(cwd=root), home=home)
            self.assertEqual(before, self._tree(root))

    def test_main_writes_nothing_including_into_the_home_it_resolves(self):
        # The two snapshot tests above cover evaluate() and only the tree they created.
        # Independent verification defeated them three ways: a marker written into
        # Path.home(), a log written from main() rather than evaluate(), and a write into
        # the system temp directory. This covers the first two by steering Path.home() at
        # a snapshotted directory and going through main().
        saved = dict(os.environ)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                os.environ["HOME"] = str(root)
                os.environ["USERPROFILE"] = str(root)
                before = self._tree(root)
                out = io.StringIO()
                srr.main(stdin=io.StringIO(json.dumps(payload(cwd=root))), stdout=out)
                self.assertEqual(before, self._tree(root),
                                 "main() must not write into the home it resolves")
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_the_source_performs_no_write_of_any_kind(self):
        # A structural guard for the third mutation, a write into the system temp
        # directory, which no snapshot of a directory the test controls can ever catch.
        # The honest way to keep "writes nothing anywhere" true is not to have a write
        # call in the file. The one permitted write is to the injected stdout.
        #
        # Parsed rather than substring-matched. The first version of the sibling guard
        # below scanned raw text and failed on the word "subprocess" appearing inside a
        # docstring, which is prose, not behaviour. A guard that fires on documentation
        # gets loosened until it fires on nothing.
        modules, calls, attributes = _analyse(MODULE_PATH)

        for forbidden in ("tempfile", "shutil"):
            with self.subTest(module=forbidden):
                self.assertNotIn(forbidden, modules)

        for forbidden in ("open", "write_text", "write_bytes", "mkdir", "touch",
                          "unlink", "rmdir", "remove"):
            with self.subTest(call=forbidden):
                self.assertNotIn(forbidden, calls,
                                 f"{forbidden}() writes; this hook must not")

        self.assertIn("write", attributes, "stdout.write is expected")
        self.assertEqual(1, calls.count("write"),
                         "exactly one write call, and it is to the injected stdout")


class RobustnessTests(unittest.TestCase):
    """S-015: an unreadable payload leaves the session unchanged."""

    def run_main(self, text):
        out = io.StringIO()
        code = srr.main(stdin=io.StringIO(text), stdout=out)
        return code, out.getvalue()

    def test_malformed_json_is_silent_and_exits_zero(self):
        code, out = self.run_main("{not json")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_empty_stdin_is_silent_and_exits_zero(self):
        code, out = self.run_main("")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_a_non_object_payload_is_silent(self):
        code, out = self.run_main("[1, 2, 3]")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_a_payload_missing_every_field_is_silent(self):
        code, out = self.run_main("{}")
        self.assertEqual(0, code)
        self.assertEqual("", out)

    def test_main_emits_exactly_one_json_object_when_it_fires(self):
        # main() resolves the user scope through Path.home() and takes no injection point
        # for it, which is correct for a hook: the streams are injectable because the
        # module contract requires it, and nothing else needs to be. So this steers
        # Path.home() through the environment it reads, covering both platforms, rather
        # than reaching into the module. Without it this test passes or fails depending on
        # whether the machine running it happens to have skills installed.
        saved = dict(os.environ)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["HOME"] = tmp          # POSIX
                os.environ["USERPROFILE"] = tmp   # Windows
                code, out = self.run_main(json.dumps(payload(cwd=tmp)))
        finally:
            os.environ.clear()
            os.environ.update(saved)

        self.assertEqual(0, code)
        parsed = json.loads(out)  # raises if it is not exactly one object
        self.assertIn("hookSpecificOutput", parsed)
        self.assertEqual("SessionStart", parsed["hookSpecificOutput"]["hookEventName"])


class CommittedRegistrationTests(unittest.TestCase):
    """The one registration this kit commits rather than prints.

    It had no test at all, which independent verification found by noticing that the
    interpreter was wrong for the only environment the file exists to serve. `.claude/
    settings.json` said `python`, while `install.py`'s hook_interpreter() returns `python3`
    off Windows, `.codex/hooks.json` uses `python3`, and the opencode adapter probes both
    and says in a comment that most platforms ship `python3`. Cloud sessions run on Linux,
    where many distributions ship no `python`, and macOS has not since 12.3.

    The failure would have been silent in the worst available way: the interpreter does not
    resolve, the hook never launches, nothing is emitted, and the session proceeds looking
    exactly as it would if skills were reachable. That is the registered-and-inert failure
    feat-0038 hit from the opposite direction, in the exact environment the committed-
    settings exception was granted for.
    """

    SETTINGS = REPO_ROOT / ".claude" / "settings.json"

    def setUp(self):
        self.parsed = json.loads(self.SETTINGS.read_text(encoding="utf-8"))
        entries = self.parsed["hooks"]["SessionStart"]
        self.assertEqual(1, len(entries), "one matcher block")
        self.entry = entries[0]
        self.command = self.entry["hooks"][0]["command"]

    def test_it_is_committed(self):
        # The whole point. A user-level registration does not reach a cloud session, so an
        # untracked file here would leave the hook unregistered where it is needed.
        tracked = subprocess.run(["git", "ls-files", ".claude/settings.json"],
                                 cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertIn("settings.json", tracked.stdout)

    def test_the_interpreter_is_the_one_that_resolves_where_this_file_is_needed(self):
        # Not `python`. See the class docstring; this is the assertion that would have
        # caught the original defect.
        self.assertTrue(self.command.startswith("python3 "),
                        "cloud sessions are Linux, where `python` frequently does not "
                        "exist; a Windows developer overrides this in the untracked "
                        ".claude/settings.local.json")

    def test_it_registers_the_reachability_hook_on_a_new_session_only(self):
        self.assertEqual("startup", self.entry["matcher"])
        self.assertIn("skill-reachability-reminder.py", self.command)

    def test_the_registered_script_exists_at_the_path_named(self):
        # A repository-relative path, so a fresh clone runs the hook in the checkout with
        # nothing installed, which is the state it reports on. If the path is wrong the
        # hook is inert and silent, the same failure by another route.
        rel = self.command.split(" ", 1)[1].strip()
        self.assertTrue((REPO_ROOT / rel).is_file(), f"{rel} does not exist")

    def test_the_exception_is_documented_where_the_rule_it_bends_lives(self):
        # AGENTS.md states hook installation is opt-in. This file breaks that for every
        # collaborator, so the carve-out has to be written beside the rule rather than
        # discovered by whoever notices the file.
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(".claude/settings.json", agents)
        self.assertIn("skill-reachability-reminder.py", agents)

    def test_the_committed_file_registers_exactly_one_hook(self):
        # AGENTS.md bounds the exception to one non-blocking hook and says a second is a
        # new decision. This is that sentence made mechanical.
        all_hooks = [h for entries in self.parsed["hooks"].values()
                     for e in entries for h in e["hooks"]]
        self.assertEqual(1, len(all_hooks),
                         "AGENTS.md bounds this exception to one hook; adding another is "
                         "a new decision, not a change to make quietly")


class NoEnvironmentDetectionTests(unittest.TestCase):
    """S-016: the answer does not depend on where it runs."""

    def test_output_is_byte_identical_across_differing_environments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "home").mkdir()
            args = (payload(cwd=root / "project"),)
            kwargs = {"home": root / "home"}

            first = srr.evaluate(*args, **kwargs)
            saved = dict(os.environ)
            try:
                # Plausible cloud-ish markers. None of them may change the answer.
                os.environ["CI"] = "true"
                os.environ["CLAUDE_CODE_CLOUD"] = "1"
                os.environ["CODESPACES"] = "true"
                second = srr.evaluate(*args, **kwargs)
            finally:
                os.environ.clear()
                os.environ.update(saved)

        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_the_source_reads_no_environment(self):
        # A structural guard: the honest way to keep S-016 true is not to look. If this
        # ever needs relaxing, that is a contract change, not a test to loosen.
        #
        # The list was three entries and independent verification walked through it twice:
        # host detection via socket.gethostname() survived, and so would `sys.platform ==`
        # since it contains no "platform." substring. Both are exactly the environment
        # sniffing S-016 forbids. Widened, and the byte-identical test below is the weaker
        # of the two guards because it can only catch detection through variables it
        # happens to set.
        modules, calls, _attributes = _analyse(MODULE_PATH)

        # You cannot read the environment without importing one of these. `sys` is
        # legitimately imported for stdin and stdout, so it is handled separately below.
        for forbidden in ("os", "platform", "socket", "subprocess"):
            with self.subTest(module=forbidden):
                self.assertNotIn(forbidden, modules,
                                 f"importing {forbidden} is how environment detection "
                                 f"gets in; S-016 says the hook does not look")

        for forbidden in ("getenv", "gethostname", "uname", "system"):
            with self.subTest(call=forbidden):
                self.assertNotIn(forbidden, calls)

        # sys.platform reads the environment without importing anything new, and contains
        # no "platform." substring, so the previous text-scanning version missed it.
        chains = _attribute_chains(MODULE_PATH)
        for forbidden in ("sys.platform", "os.name", "os.environ", "os.sep"):
            with self.subTest(chain=forbidden):
                self.assertNotIn(forbidden, chains)

    def test_only_the_listed_sources_fire(self):
        # FIRING_SOURCES is an allowlist and must stay one. Inverting it to a denylist of
        # the four continuing sources survived every existing test, because every source
        # anyone thought to test was named in it. An unknown source is the case that
        # separates the two shapes, and an allowlist is the safer default: a source added
        # by the harness later stays silent until someone decides it should not.
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                srr.evaluate(payload("some-future-source", cwd=tmp), home=Path(tmp)),
                "an unrecognised source must not fire; FIRING_SOURCES is an allowlist")


if __name__ == "__main__":
    unittest.main()
