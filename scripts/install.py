#!/usr/bin/env python3
"""Install the Zen Agent Skills library into your AI tools' discovery directories.

Idempotent and safe to re-run. Previews with --dry-run, reverses with
--uninstall. Never clobbers a real file it did not create: such a target is
reported CONFLICT and skipped for you to resolve.

In copy mode, re-run recognition relies on scripts/.install-manifest.json to
know which targets this tool created. If that manifest is deleted, previously
copied targets are treated as unmanaged and reported CONFLICT (symlink mode
recognizes its own links directly and does not have this dependency).

    python scripts/install.py --dry-run          # preview
    python scripts/install.py                     # install (copy on Windows, symlink on POSIX)
    python scripts/install.py --mode symlink      # force symlinks
    python scripts/install.py --tools claude      # only Claude Code
    python scripts/install.py --profile all       # every skill, not just the default set
    python scripts/install.py --uninstall         # remove what this installed

A --profile selects which skills to place, and defaults to less than all of them
because every installed description is loaded so an agent can route to it. A profile
is expanded over sibling references before anything is placed, so it can never ship a
skill whose composed sibling is missing. --uninstall is unaffected by the profile: it
reverses every recorded target beneath --home, whichever run placed it.

A skill whose frontmatter carries `metadata.status: draft` is placed by no profile,
including `all`, so a skill the kit has not blessed is never distributed to an adopter
(S-015). No marker means shipped, so the exclusion is always a deliberate act.

Discovery targets (per tool), each skill linked/copied as <base>/<skill-name>:
    claude    -> ~/.claude/skills
    opencode  -> ~/.agents/skills

The swappable rules module (.agents/rules/) travels with the skills, placed as
the sibling <base>/../rules. That location is not arbitrary: a skill body
references its lens as ../../rules/<file>.md, which resolves from
<base>/<skill-name>/SKILL.md to exactly this directory. Without it, house-review
loses its whole rubric and twelve other skills lose their house-style module.

Cursor and Copilot read repo-level pointer files, not a global skills dir, so
they are handled by build-adapters.py per project, not here.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
RULES_DIR = REPO_ROOT / ".agents" / "rules"
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
MANIFEST = REPO_ROOT / "scripts" / ".install-manifest.json"

TOOL_SUBPATHS = {
    "claude": Path(".claude") / "skills",
    "opencode": Path(".agents") / "skills",
}

# Which skills a profile asks for. Each is a seed, not the final set: it is expanded
# over sibling references before anything is placed (S-013), because a skill that
# composes a sibling by reference is broken without it.
#
# These boundaries are dictated by the reference graph, not chosen. It has one
# strongly connected component of fourteen skills, so any profile touching it is at
# least seventeen; the only separable skills are the handoff pair and the three that
# reference no sibling. `core` is therefore small but cannot include new-task, which
# lives inside the component. See docs/spec/install.md.
PROFILE_SEEDS = {
    "core": ["project-bootstrap", "init-worktracking", "pr-describe"],
    "spine": ["spec-author", "spec-plan-readiness", "new-task", "fix-batch", "test-author",
              "spec-conformance", "verifier-agent", "reconcile-worktrees", "doc-sync",
              "pr-describe", "project-bootstrap", "init-worktracking", "house-review"],
    "all": None,  # everything discovered
}
DEFAULT_PROFILE = "spine"

SIBLING_REF_RE = re.compile(r"\]\(\.\./([^/)]+)/SKILL\.md")
# Narrow readers for one frontmatter field, deliberately not a YAML parser. The block
# scalar case matters here for the same reason it does in validate-skills.py: without
# it the reported description budget is inflated by three characters per skill that
# uses one. This is the third copy of this shape in scripts/; unifying them is a
# standing recommendation, not a drive-by change.
DESC_FIELD_RE = re.compile(r"^description:\s*(.*)$")
BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\s*")

# The draft marker (S-015). `metadata` is one of the six frontmatter properties the
# skill schema permits, so a nested `status` under it is the only spelling that is both
# legal for the external validator and mechanical here. A bare top-level `status:` key
# would be rejected outright by validate-skills.py's allow-list, and the flow form
# `metadata: {status: draft}` trips its plain-scalar-with-a-colon check, so only the
# block form below is read:
#
#     metadata:
#       status: draft
#
# Deliberately not a YAML parser, for the same reason DESC_FIELD_RE is not one.
METADATA_KEY_RE = re.compile(r"^metadata:\s*$")
STATUS_FIELD_RE = re.compile(r"^\s+status:\s*(\S.*?)\s*$")
DRAFT_STATUS = "draft"


def discover_skills():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def description_of(skill_dir: Path) -> str:
    """The skill's `description` value, or "" when absent.

    Only the frontmatter is scanned, and only for this one field. A block-scalar
    indicator is dropped so the length is the text's, matching what a harness measures.
    """
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    parts, collecting = [], False
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        m = DESC_FIELD_RE.match(raw)
        if m:
            parts.append(BLOCK_SCALAR_RE.sub("", m.group(1).strip().strip('"').strip("'"), count=1))
            collecting = True
        elif collecting:
            if re.match(r"^\w[\w-]*:", raw):
                break
            if raw.strip():
                parts.append(raw.strip())
    return " ".join(p for p in parts if p).strip()


def status_of(skill_dir: Path) -> str:
    """The skill's `metadata.status` value, lowercased, or "" when it carries none.

    Only the frontmatter's `metadata:` block is read, so a `status:` line written
    anywhere in the body is prose and not a marker. That distinction is load-bearing:
    several skills in this kit discuss draft status in their bodies, and reading one of
    those as a marker would drop a shipped skill from every profile with no signal.

    An unrecognised value reads as shipped rather than as a draft, so a typo
    over-delivers (today's defect) instead of silently under-delivering (the worse one).
    """
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
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
                    return m.group(1).strip().strip('"').strip("'").lower()
        if not inside and METADATA_KEY_RE.match(raw):
            inside = True
    return ""


def partition_drafts(skills):
    """Split discovered skills into (shipped, drafts).

    Absence of a marker means shipped, so this only ever holds back a skill that says
    so itself. Applied before a profile is resolved, so the closure in resolve_profile
    runs over the shipped set rather than around it.
    """
    draft_names = {d.name for d in skills if status_of(d) == DRAFT_STATUS}
    return ([d for d in skills if d.name not in draft_names],
            [d for d in skills if d.name in draft_names])


def draft_conflicts(selected, seed, draft_names) -> list:
    """Contradictions between what a profile would place and the draft markers.

    Two shapes, both of which would otherwise resolve silently and wrongly:

    - A selected skill references a draft sibling. Dropping the reference reintroduces
      the dangling-sibling defect S-013 exists to prevent; pulling the draft in defeats
      the marker. Neither is this tool's call to make, so it places nothing and says so.
    - A profile seed names a draft. The seed is filtered against the shipped set, so
      such a name would otherwise vanish from the request without a word.
    """
    problems = []
    for name in (seed or []):
        if name in draft_names:
            problems.append(f"the profile seed names {name!r}, which is marked a draft")
    for d in selected:
        for ref in sorted(sibling_refs(d) & set(draft_names)):
            problems.append(f"{d.name} references {ref!r} as a sibling, "
                            f"and {ref!r} is marked a draft")
    return problems


def sibling_refs(skill_dir: Path) -> set:
    """Skill names this skill links to as ../<name>/SKILL.md."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    return set(SIBLING_REF_RE.findall(text)) - {skill_dir.name}


def resolve_profile(profile: str, skills):
    """Return (selected_dirs, added_names) for a profile.

    The seed is expanded over sibling references until closed (S-013). Computed rather
    than listed, so a skill that gains a reference later cannot silently leave a
    profile shipping a dangling one.
    """
    by_name = {d.name: d for d in skills}
    seed = PROFILE_SEEDS[profile]
    if seed is None:
        return list(skills), []
    wanted = {n for n in seed if n in by_name}
    stack = list(wanted)
    while stack:
        for ref in sibling_refs(by_name[stack.pop()]):
            if ref in by_name and ref not in wanted:
                wanted.add(ref)
                stack.append(ref)
    added = sorted(wanted - {n for n in seed if n in by_name})
    return [d for d in skills if d.name in wanted], added


def profile_budgets(skills):
    """Description-character total per profile, so the figure is comparable."""
    return {name: sum(len(description_of(d)) for d in resolve_profile(name, skills)[0])
            for name in PROFILE_SEEDS}


def load_manifest():
    if MANIFEST.is_file():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"entries": []}
    return {"entries": []}


def save_manifest(entries, dry):
    if dry:
        return
    MANIFEST.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")


def is_managed(target: Path, manifest) -> bool:
    tp = str(target)
    return any(e.get("target") == tp for e in manifest["entries"])


# Where each tool expects the hooks module, as a sibling of its skills directory. Absent
# from this map means the tool has no hook mechanism this installer knows how to place.
HOOK_SUBPATHS = {
    "claude": Path(".claude") / "hooks",
    "opencode": Path(".agents") / "hooks",
}

# Each hook in the module and the PostToolUse matcher that must wake it. A matcher may be
# broader than the hook's own condition, since every hook re-checks; it may never be
# narrower, or the hook is placed and silently never fires. `tests/test_hooks.py`
# asserts the delegation matcher against the hook's own tool set for exactly that reason.
HOOK_REGISTRATIONS = [
    ("delegation-reminder.py", "^Task$|^Agent$|^TaskOutput$|agent_run"),
    ("spec-conformance-gate.py", "^Edit$|^Write$|^MultiEdit$|^NotebookEdit$|apply_patch"),
]


def hook_interpreter() -> str:
    """The interpreter name to write into a hook registration.

    Not hardcoded to `python3`. On Windows that name usually resolves to the Microsoft
    Store's app-execution alias, which prints an install advertisement and exits without
    running anything, so a registration naming it produces a hook that fails silently
    forever. Found by dogfooding feat-0038 on Windows, where the first draft did exactly
    that. Mirrors how `--mode` already defaults per platform.
    """
    return "python" if os.name == "nt" else "python3"


def claude_registration(home: Path) -> str:
    """The settings.json block a user pastes to activate the hooks.

    Printed rather than merged. Editing someone's settings file is the one step of this
    install the uninstall manifest cannot cleanly reverse, and a hook is the only thing
    the kit ships that runs inside their session, so the placement is automated and the
    activation is not: nothing fires until a person pastes this in.

    The path is absolute and resolved rather than `~/...`, because whether a tilde is
    expanded depends on how the harness spawns the command, and a registration that
    silently does not run is the worst outcome available here.

    Built from HOOK_REGISTRATIONS rather than written out, so a hook added to the module
    without a matcher here is a mistake that shows up as a missing entry instead of a hook
    that was placed and never fires.
    """
    hooks_home = home / HOOK_SUBPATHS["claude"]
    entries = []
    for script_name, matcher in HOOK_REGISTRATIONS:
        if not (HOOKS_DIR / script_name).is_file():
            continue
        command = f"{hook_interpreter()} \"{hooks_home / script_name}\""
        entries.append({
            "matcher": matcher,
            "hooks": [{"type": "command", "command": command}],
        })
    return json.dumps({"hooks": {"PostToolUse": entries}}, indent=2)


def discover_hooks():
    if not HOOKS_DIR.is_dir():
        return []
    return sorted(p for p in HOOKS_DIR.glob("*.py"))


def install(tools, mode, home: Path, dry: bool, profile: str = DEFAULT_PROFILE,
            with_hooks: bool = False) -> int:
    # Resolved here and not only in `main()` (bug-0010), because every target below is
    # built from `home` and written verbatim into a persisted record. A relative spelling
    # records a string whose meaning depends on the reader's current directory, which
    # `bug-0009`'s normalisation cannot repair: there is no fixed path to normalise
    # toward. `install()` is a supported entry point (chore-0017), so the guarantee that a
    # recorded target is absolute belongs with the recording rather than with one caller.
    home = home.expanduser().resolve()
    all_skills = discover_skills()
    if not all_skills:
        print(f"No skills found under {SKILLS_DIR}.")
        return 0

    # Drafts are removed before the profile is resolved (S-015), so the closure that
    # keeps a profile sound (S-013) runs over the shipped set rather than around it.
    shipped, drafts = partition_drafts(all_skills)
    skills, added = resolve_profile(profile, shipped)

    problems = draft_conflicts(skills, PROFILE_SEEDS[profile], {d.name for d in drafts})
    if problems:
        print(f"Refusing to place anything for profile {profile!r}: it collides with a "
              f"draft marker, and every way through is wrong without a person deciding.")
        for p in problems:
            print(f"  - {p}")
        print("\nEither bless the draft by removing its marker, or mark the skill that "
              "references it a draft too. Placing it would ship a reference to a skill "
              "this run did not place; skipping the reference would ship the dangling "
              "sibling the closure exists to prevent.")
        return 2

    if drafts:
        print(f"{len(drafts)} skill(s) marked a draft are excluded from every profile, "
              f"including 'all': {', '.join(d.name for d in drafts)}.\n")
    if added:
        print(f"Profile {profile!r} was expanded to stay closed over sibling references: "
              f"{len(added)} skill(s) added ({', '.join(added)}). A skill that composes a "
              f"sibling is broken without it.\n")

    manifest = load_manifest()
    entries = {e["target"]: e for e in manifest["entries"]}
    conflicts = 0
    tag = "[dry-run] " if dry else ""
    hooks = discover_hooks() if with_hooks else []
    if with_hooks and not hooks:
        print(f"--with-hooks was given but no hooks were found under {HOOKS_DIR}.\n")

    for tool in tools:
        base = home / TOOL_SUBPATHS[tool]
        if not dry:
            base.mkdir(parents=True, exist_ok=True)
        for src in skills:
            target = base / src.name
            status = _place(src, target, mode, dry, manifest)
            if status == "CONFLICT":
                conflicts += 1
            else:
                entries[str(target)] = {
                    "tool": tool, "name": src.name,
                    "target": str(target), "mode": mode, "source": str(src),
                }
            print(f"{tag}{status:9} {tool:8} {src.name}  -> {target}")

        # The rules module, as the sibling <base>/../rules, so each skill's
        # ../../rules/<file>.md reference resolves in the installed layout too.
        if RULES_DIR.is_dir():
            rules_target = base.parent / "rules"
            status = _place(RULES_DIR, rules_target, mode, dry, manifest)
            if status == "CONFLICT":
                conflicts += 1
            else:
                entries[str(rules_target)] = {
                    "tool": tool, "name": "rules",
                    "target": str(rules_target), "mode": mode, "source": str(RULES_DIR),
                }
            print(f"{tag}{status:9} {tool:8} rules  -> {rules_target}")

        # The hooks module, opt-in. Placed as the sibling <base>/../hooks, which for
        # Claude Code is the directory it already reads hooks from.
        if with_hooks and hooks and tool in HOOK_SUBPATHS:
            hooks_target = home / HOOK_SUBPATHS[tool]
            status = _place(HOOKS_DIR, hooks_target, mode, dry, manifest)
            if status == "CONFLICT":
                conflicts += 1
            else:
                entries[str(hooks_target)] = {
                    "tool": tool, "name": "hooks",
                    "target": str(hooks_target), "mode": mode, "source": str(HOOKS_DIR),
                }
            print(f"{tag}{status:9} {tool:8} hooks  -> {hooks_target}")

    save_manifest(list(entries.values()), dry)
    if conflicts:
        print(f"\n{conflicts} CONFLICT(s): a real file exists at those targets. "
              f"Move or remove them, then re-run.")
    if not RULES_DIR.is_dir():
        print(f"\nWARNING: no rules module at {RULES_DIR}. Skills that reference "
              f"../../rules/ (house-review's rubric, the house-style module) will "
              f"dangle in the installed layout.")
    # Over the shipped set, not everything discovered: a draft is placed by no profile,
    # so counting its description would report a budget no run can incur (S-015).
    budgets = profile_budgets(shipped)
    print(f"\n{tag}Done: profile {profile!r}, {len(skills)} of {len(all_skills)} skill(s) "
          f"x {len(tools)} tool(s), plus the rules module"
          + (f", plus {len(hooks)} hook(s)." if hooks else "."))
    if hooks and "claude" in tools:
        # Deliberately the last thing printed, and deliberately not done for the user.
        print(f"\n{tag}The hooks are placed but INACTIVE. Nothing runs until you register "
              f"them. Merge this into ~/.claude/settings.json:\n")
        print(claude_registration(home))
        print(f"\nRemove that block to deactivate; `--uninstall` removes the files.")
    # A count, not a percentage: the harness budget scales with the context window and
    # is shared with skills this tool cannot see, so a proportion here would be invented.
    print(f"{tag}Description budget: {budgets[profile]} characters for this profile "
          f"(" + ", ".join(f"{n}={budgets[n]}" for n in PROFILE_SEEDS) + ").")
    return 1 if conflicts else 0


def _place(src: Path, target: Path, mode: str, dry: bool, manifest) -> str:
    """Create one link/copy at target. Returns a status word."""
    if target.is_symlink():
        try:
            points_to = target.resolve()
        except OSError:
            points_to = None
        if mode == "symlink":
            if points_to == src.resolve():
                return "ok"
            if not dry:
                target.unlink()
                _link(src, target)
            return "relinked"
        # copy mode but a symlink is there: ours only if it points exactly at our source
        if points_to == src.resolve():
            if not dry:
                target.unlink()
                _copy(src, target)
            return "updated"
        return "CONFLICT"

    if target.exists():
        if is_managed(target, manifest):
            if mode == "copy":
                if not dry:
                    _rm(target)
                    _copy(src, target)
                return "updated"
            if not dry:
                _rm(target)
                _link(src, target)
            return "relinked"
        return "CONFLICT"

    # nothing there
    if not dry:
        if mode == "symlink":
            _link(src, target)
        else:
            _copy(src, target)
    return "linked" if mode == "symlink" else "copied"


def _link(src: Path, target: Path):
    try:
        os.symlink(src, target, target_is_directory=True)
    except (OSError, NotImplementedError) as e:
        raise SystemExit(
            f"symlink failed ({e}). On Windows, enable Developer Mode or run "
            f"with --mode copy.")


def _copy(src: Path, target: Path):
    # Byte-caches are not part of any module the kit distributes, and the hooks module
    # grows one as soon as the test suite imports it. Copying it would ship a stale .pyc
    # into an adopter's home for a source file that is about to be a symlink or a
    # different version.
    shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _rm(target: Path):
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    else:
        target.unlink()


def _beneath(target: str, home: Path) -> bool:
    """True when a recorded target lies under `home`.

    One manifest serves every home installed to from this checkout, because
    `install` merges into the existing record rather than replacing it. Reversal
    is therefore scoped here, per S-007 and S-012: without this, uninstalling a
    throwaway home also removes the user's real installation.

    Both sides are normalised first (bug-0009), because `is_relative_to` compares
    components as spelled. S-007 scopes reversal to a directory, not to one spelling
    of it, so a relative `home`, one carrying `..`, or one reached through a symlinked
    parent has to match the same recorded targets an absolute one does. Without that,
    such a caller matches nothing, every entry is classed as another home's, and the
    run reports success having removed nothing. `main()` resolves `--home`, so the CLI
    never hit this; `uninstall()` is a supported entry point (chore-0017) that callers
    and tests reach directly, and the guarantee belongs with the comparison rather
    than with one caller.

    The target's final component is deliberately left unresolved. In symlink mode
    every recorded target *is* a link this tool created, pointing back at its source
    in this checkout, so resolving it would place the target beneath no home at all.
    Its parent chain is safe to resolve and always contains `home`, which is what lets
    a symlinked home normalise identically on both sides.
    """
    try:
        t = Path(target)
        return (t.parent.resolve() / t.name).is_relative_to(home.resolve())
    except (OSError, ValueError):
        return False


def uninstall(home: Path, dry: bool) -> int:
    manifest = load_manifest()
    if not manifest["entries"]:
        print("Nothing recorded as installed.")
        return 0

    mine = [e for e in manifest["entries"] if _beneath(e["target"], home)]
    others = [e for e in manifest["entries"] if not _beneath(e["target"], home)]

    tag = "[dry-run] " if dry else ""
    if not mine:
        print(f"Nothing recorded as installed beneath {home}.")
        if others:
            print(f"{len(others)} target(s) recorded under other homes are untouched.")
        return 0

    removed = 0
    for e in mine:
        target = Path(e["target"])
        if target.is_symlink() or target.exists():
            if not dry:
                _rm(target)
            removed += 1
            print(f"{tag}removed   {e['tool']:8} {e['name']}  ({target})")
        else:
            print(f"{tag}gone      {e['tool']:8} {e['name']}  ({target})")
    save_manifest(others, dry)
    print(f"\n{tag}Uninstalled {removed} target(s).")
    if others:
        print(f"{tag}Kept {len(others)} target(s) recorded under other homes.")
    return 0


def main(argv=None) -> int:
    """Entry point. `argv` defaults to sys.argv[1:]; pass a list to drive it in a test."""
    ap = argparse.ArgumentParser(description="Install the Zen Agent Skills library.")
    ap.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove what was installed")
    ap.add_argument("--mode", choices=["symlink", "copy"],
                    default="copy" if os.name == "nt" else "symlink",
                    help="link mode (default: copy on Windows, symlink elsewhere)")
    ap.add_argument("--tools", default="claude,opencode",
                    help="comma-separated subset of: " + ",".join(TOOL_SUBPATHS))
    ap.add_argument("--profile", default=DEFAULT_PROFILE,
                    help="which skills to place: " + ", ".join(PROFILE_SEEDS)
                         + f" (default: {DEFAULT_PROFILE})")
    ap.add_argument("--with-hooks", action="store_true",
                    help="also place .agents/hooks/ (opt-in: hooks run inside your "
                         "session, and stay inactive until you register them)")
    ap.add_argument("--home", default=None,
                    help="override the base home dir (for testing/unusual setups)")
    args = ap.parse_args(argv)

    home = Path(args.home).expanduser().resolve() if args.home else Path.home()

    if args.uninstall:
        return uninstall(home, args.dry_run)

    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    bad = [t for t in tools if t not in TOOL_SUBPATHS]
    if bad:
        print(f"Unknown tool(s): {bad}. Choose from {list(TOOL_SUBPATHS)}.")
        return 2
    if args.profile not in PROFILE_SEEDS:
        print(f"Unknown profile: {args.profile!r}. Choose from {list(PROFILE_SEEDS)}.")
        return 2
    return install(tools, args.mode, home, args.dry_run, args.profile, args.with_hooks)


if __name__ == "__main__":
    raise SystemExit(main())
