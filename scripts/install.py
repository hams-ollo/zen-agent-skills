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
    python scripts/install.py --check             # is an installed set still current?
    python scripts/install.py --replace-adopted   # take the kit's rules module, lose yours
    python scripts/install.py --uninstall         # remove what this installed

Staleness, and why --check exists
---------------------------------
A copied skill is a snapshot taken at install time, so editing the skill here does
not change the installed copy and nothing said so: the stale copy is a valid skill
that passes every validator and reads correctly (chore-0031). So each entry in the
manifest now records a SHA256 per placed file, and --check re-reads the targets and
names any that no longer match their source. It reports and never rewrites, for the
same reason check-provenance.py does: an adopter may have edited an installed file
deliberately, and an overwrite destroys that without asking.

The baseline is per entry, not per manifest, so a manifest written before this change
degrades one entry at a time. Such an entry reports `unknown`, never `ok`: a clean
result for a state nobody recorded is the same silent failure --check exists to
remove, one level up. Re-install to establish a baseline.

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

That module is adopted, not derived, and a re-install treats it accordingly
(bug-0018). A skill directory is regenerated wholesale, because it is the kit's;
a rules file you edited is kept, reported, and never merged into, because the
kit invites you to make it your own and an overwrite would destroy that work
with nothing anywhere to say so. The recorded digests draw the line: a file
matching its baseline is untouched and is refreshed, a file that does not is
yours. `--replace-adopted` takes the kit's copies when you want them.

Cursor and Copilot read repo-level pointer files, not a global skills dir, so
they are handled by build-adapters.py per project, not here.

Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
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


# The one placed module an adopter is invited to rewrite. Matched by the entry name this
# tool records for it, so the classification travels in the record rather than being
# re-derived from a path. See `_check_entry` for what the invitation costs the check, and
# `_place_adopted` for what it costs placement.
ADOPTED_ENTRY_NAMES = {"rules"}


def _digestable(rel: Path, path: Path) -> bool:
    """Whether a file beneath a placed module is part of that module.

    Mirrors the ignore list `_copy` places with. Digesting a byte-cache would report a
    file missing from every install of the hooks module, since the source grows a
    `__pycache__` as soon as anything imports it and the copy deliberately has none.
    """
    return path.suffix != ".pyc" and "__pycache__" not in rel.parts


def digest_tree(root: Path) -> dict:
    """SHA256 per file beneath `root`, keyed by its POSIX-relative path.

    Per file and not per directory (chore-0031): a skill is a directory of templates and
    references, and a stale template is exactly as silent as a stale `SKILL.md`. Keys are
    POSIX-relative so a record written on Windows is readable on macOS and Linux.

    Bytes, never decoded text. This repository is LF by `.gitattributes`, but an installed
    copy lives outside git, and digesting decoded text would make the answer depend on how
    the reader normalises line endings rather than on what is actually on disk.
    """
    digests = {}
    if not root.is_dir():
        return digests
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if not _digestable(rel, path):
            continue
        digests[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


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
# (script, event, matcher). The event was added by feat-0046 and is not cosmetic: this
# table carried only (script, matcher) while claude_registration() hardcoded PostToolUse,
# so a hook on any other event was placed by --with-hooks and never registered. That is
# the "installed, correct-looking, and doing nothing" failure feat-0038 hit twice, and it
# would have been silent here too.
HOOK_REGISTRATIONS = [
    ("delegation-reminder.py", "PostToolUse",
     "^Task$|^Agent$|^TaskOutput$|agent_run"),
    ("spec-conformance-gate.py", "PostToolUse",
     "^Edit$|^Write$|^MultiEdit$|^NotebookEdit$|apply_patch"),
    # `startup` only. The other sources continue a session already told.
    ("skill-reachability-reminder.py", "SessionStart", "startup"),
    # Same event and the same reasoning, and deliberately a second hook rather than a
    # branch inside the first: reachability is a directory-name match, currency reads and
    # digests files, and the reachability reminder's own message disclaims this question.
    ("install-currency-reminder.py", "SessionStart", "startup"),
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

    Grouped by event rather than emitted under a hardcoded one. The event lives in the
    table now, so adding a hook on a new lifecycle event needs no change here at all,
    which is what the previous shape got wrong.
    """
    hooks_home = home / HOOK_SUBPATHS["claude"]
    by_event = {}
    for script_name, event, matcher in HOOK_REGISTRATIONS:
        if not (HOOKS_DIR / script_name).is_file():
            continue
        command = f"{hook_interpreter()} \"{hooks_home / script_name}\""
        by_event.setdefault(event, []).append({
            "matcher": matcher,
            "hooks": [{"type": "command", "command": command}],
        })
    return json.dumps({"hooks": by_event}, indent=2)


def discover_hooks():
    if not HOOKS_DIR.is_dir():
        return []
    return sorted(p for p in HOOKS_DIR.glob("*.py"))


def install(tools, mode, home: Path, dry: bool, profile: str = DEFAULT_PROFILE,
            with_hooks: bool = False, replace_adopted: bool = False) -> int:
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
    preserved_adopted = False
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
                    "digests": digest_tree(src),
                }
            print(f"{tag}{status:9} {tool:8} {src.name}  -> {target}")

        # The rules module, as the sibling <base>/../rules, so each skill's
        # ../../rules/<file>.md reference resolves in the installed layout too.
        #
        # Placed through `_place_adopted` and not `_place` (bug-0018): this is the one
        # module an adopter is invited to rewrite, so a re-run refreshes what they never
        # touched and leaves what they did. The previously recorded digests are the baseline
        # that separates the two, which is why they are read out of the existing entry
        # before it is overwritten.
        if RULES_DIR.is_dir():
            rules_target = base.parent / "rules"
            recorded = (entries.get(str(rules_target)) or {}).get("digests")
            status, digests, notes = _place_adopted(
                RULES_DIR, rules_target, mode, dry, manifest, recorded, replace_adopted)
            if status == "CONFLICT":
                conflicts += 1
            else:
                entries[str(rules_target)] = {
                    "tool": tool, "name": "rules",
                    "target": str(rules_target), "mode": mode, "source": str(RULES_DIR),
                    "digests": digests,
                }
            if status == "preserved":
                preserved_adopted = True
            print(f"{tag}{status:9} {tool:8} rules  -> {rules_target}")
            for note in notes:
                # Named per file, not counted. A run that says it kept "1 file" leaves the
                # reader to go and find out which, which is the investigation the whole
                # report exists to save them.
                print(f"{tag}          {note}")

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
                    "digests": digest_tree(HOOKS_DIR),
                }
            print(f"{tag}{status:9} {tool:8} hooks  -> {hooks_target}")

    save_manifest(list(entries.values()), dry)
    if preserved_adopted:
        # Exit-neutral on purpose, matching how `--check` treats `revised`: an adopted file
        # this run left alone is news about the install, not a fault in it.
        print(f"\n{tag}The rules module is yours to edit, so files you changed were kept "
              f"rather than replaced. Nothing was merged: compare with `--check`, or pass "
              f"`--replace-adopted` to take the kit's copies and lose yours.")
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
    # Printed on every run, because the whole point of the check is that nothing else
    # tells you the copy has gone stale: a reader who never learns the flag exists is in
    # the state chore-0031 was filed on.
    print(f"{tag}Run `python scripts/install.py --check` (with the same --home, if you "
          f"passed one) to see whether an installed set still matches this kit.")
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


def _place_adopted(src: Path, target: Path, mode: str, dry: bool, manifest,
                   recorded, replace: bool) -> tuple:
    """Place the adopted rules module without destroying what its adopter made theirs.

    Returns `(status, digests, notes)`: the status word to print, the digest map to record
    for this entry, and zero or more lines naming what the run declined to do.

    Why this exists at all (bug-0018). `_place` handles a managed target by removing it and
    copying the source back, which is right for a **derived** module and wrong for an
    **adopted** one. `.agents/rules/` is the module `AGENTS.md` calls swappable and
    `house-style.md` opens by inviting the reader to rewrite, so re-installing destroyed the
    one thing the kit specifically asks an adopter to own, silently and at exit 0. For a
    directory `_rm` took the whole tree, so a lens they *added* beside the kit's went too.
    `build-adapters.py` already got this right from a `dest.exists()` guard, and its
    contract states the reason as the contrast this function implements: supporting files
    are derived and are refreshed, a rules file is adopted and is preserved
    (`build-adapters.md` S-010 and S-014).

    Per file rather than per directory, for two reasons that pull the same way. A whole-tree
    verdict would refuse to deliver a lens the kit newly ships to anyone who edited any file
    in the module, and it cannot express the case the bug report singles out: a file the
    adopter added, which is neither the kit's to refresh nor the kit's to delete.

    The distinction is drawn against the **recorded baseline**, never against the source,
    and that is the whole design. A file differing from the recorded digest is the adopter's
    and is left alone; a file matching it differs only because the kit moved on, so it is
    ours to refresh. Deciding by "differs from the source" instead would preserve everything
    forever and pin every adopter to whatever shipped on the day they first installed, which
    is the inverse bug and just as silent. It is the same line `--check` already draws
    between `diverged` and `revised`.

    A preserved file keeps the digest previously recorded for it rather than taking the
    bytes now on disk. Recording what the adopter wrote would make the next run read their
    file as untouched and refresh over it, which is this same data loss delayed by one
    install. Keeping the baseline also lets `--check` keep answering the question it is for:
    the kit's copy has moved since you installed, and yours is yours.

    Only the copy path reaches here. In symlink mode the installed module *is* the kit's
    file, so there is no second copy to preserve and nothing to compare.
    """
    if (replace or mode != "copy" or target.is_symlink() or not target.exists()
            or not is_managed(target, manifest)):
        # Not a managed copy on disk, or the adopter has explicitly asked for the kit's.
        # `_place` keeps owning the CONFLICT rule (S-004), the fresh placement, and both
        # symlink branches: an unmanaged target is still refused rather than merged into.
        status = _place(src, target, mode, dry, manifest)
        return status, (None if status == "CONFLICT" else digest_tree(src)), []

    source = digest_tree(src)
    if not recorded:
        # The pre-digest case, exactly as in chore-0031: an install predating that change
        # recorded no baseline, so an edited file is indistinguishable from an untouched
        # one. The failure directions are not symmetric, so this preserves and says the
        # baseline is unknown. Falsiness rather than `is None`, matching `_check_entry`: a
        # `digests` map that is present but empty is no more of a baseline than a missing
        # one. Nothing is recorded either, because recording the source for files this run
        # did not place would claim a baseline that never existed.
        return "preserved", {}, [
            "no digest baseline was recorded for this install, so an edited file cannot be "
            "told from an untouched one: every file is left exactly as it is, and the "
            "baseline stays unknown.",
            "Run with --replace-adopted to take the kit's copy and record a baseline.",
        ]

    installed = digest_tree(target)
    digests = dict(recorded)
    placed, preserved, removed = [], [], []

    for rel in sorted(source):
        want, have, base = source[rel], installed.get(rel), recorded.get(rel)
        if have == want:
            digests[rel] = want                      # already exactly the kit's copy
        elif have is None and base is None:
            _copy_file(src / rel, target / rel, dry)  # new in the kit; nothing is at risk
            digests[rel] = want
            placed.append(rel)
        elif have == base:
            _copy_file(src / rel, target / rel, dry)  # untouched since we placed it
            digests[rel] = want
            placed.append(rel)
        elif have is None:
            # The digest goes with the file (bug-0022). Keeping it left the record asserting
            # a baseline for a file this very run has just said is gone, and nothing ever
            # reconciled the two, which is what let `--check` read that baseline forever. It
            # is not the "preserved file keeps its old baseline" property bug-0018 pinned:
            # that one is about a file the adopter *edited*, which is still on disk and
            # still has a baseline worth keeping.
            #
            # The seam this leaves open is stated rather than hidden: with no record of the
            # removal, a later run cannot tell this lens from one the adopter has never been
            # sent, so it places it. Remembering instead would need a tombstone in the
            # manifest, and the alternative is a deliberate deletion reported as divergence
            # on every check forever, which is noise aimed at exactly the people this
            # exemption was written for. Nothing of theirs is destroyed either way.
            preserved.append((rel, "you removed it, so this run does not restore it, and "
                                   "the record no longer claims it"))
            digests.pop(rel, None)
        elif base is None:
            preserved.append((rel, "yours, and the kit now ships a file of that name"))
        else:
            preserved.append((rel, "you edited it"))

    for rel in sorted(set(recorded) - set(source)):
        # The kit no longer ships this file. Removing it is only safe where the copy on
        # disk is provably the one this tool placed and nobody has touched it since.
        if installed.get(rel) == recorded[rel]:
            if not dry:
                (target / rel).unlink()
            removed.append(rel)
        elif rel in installed:
            preserved.append((rel, "you kept it after the kit dropped it"))
        digests.pop(rel, None)

    notes = [f"preserved {rel}: {why}" for rel, why in preserved]
    if placed:
        notes.append(f"refreshed {len(placed)} unmodified file(s): {', '.join(placed)}")
    if removed:
        notes.append(f"removed {len(removed)} unmodified file(s) the kit no longer ships: "
                     f"{', '.join(removed)}")
    if preserved:
        notes.append("Your copies are kept and the kit's are not merged in; that is a "
                     "person's call. Run with --replace-adopted to take the kit's instead.")
        return "preserved", digests, notes
    return ("updated" if placed or removed else "ok"), digests, notes


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


def _copy_file(src: Path, target: Path, dry: bool):
    """Place one file, creating the directories above it. The per-file half of `_copy`.

    Needed because the adopted module is placed file by file (see `_place_adopted`), so
    `copytree` is the wrong granularity there: it would overwrite a whole directory to
    deliver one file.
    """
    if dry:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)


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


def _compare(left: dict, right: dict, left_label: str = "installed",
             right_label: str = "source") -> list:
    """Every per-file disagreement between two digest maps.

    The labels are parameters because the two callers compare different things. The derived
    path really does hold a digest of the installed tree, but the adopted path passes the
    *recorded baseline*, and naming that "installed" printed a number matching nothing on
    disk: an adopter checksumming their own lens got a third value and no way to reconcile
    it. Reported by the automated reviewer on this pull request, which is the second time
    that reviewer has caught a class the local checks could not (see bug-0012).
    """
    problems = []
    for rel, digest in right.items():
        found = left.get(rel)
        if found is None:
            problems.append(f"{rel}: in the {right_label}, absent from the {left_label}")
        elif found != digest:
            problems.append(f"{rel}: {left_label} {found[:12]}, {right_label} {digest[:12]}")
    for rel in left:
        if rel not in right:
            problems.append(f"{rel}: in the {left_label}, absent from the {right_label}")
    return problems


def _check_entry(entry) -> tuple:
    """Classify one recorded target. Returns (status, message).

    status is one of `ok`, `linked`, `revised`, `diverged`, `unknown`, `error`, borrowing
    check-provenance.py's vocabulary rather than inventing a second one for the same idea.

    Three classifications are decisions rather than mechanics:

    - **`unknown`** for an entry carrying no recorded digests. The derived half of such an
      entry could be compared anyway, and deliberately is not: the adopted half cannot be
      answered without a baseline, and a per-entry verdict that reads `ok` while half of it
      is unanswerable is the clean-looking-but-partial result this check exists to remove.
    - **`linked`** for a target that is a symlink to its own source. It cannot be stale,
      because it *is* the source. Read from the filesystem rather than from the recorded
      `mode`, since a copy can replace a link between runs.
    - **`revised`** for the adopted rules module, where the question is not the derived
      one. A lens is the one file an adopter is invited to rewrite (`build-adapters.md`
      S-010 and S-014), so comparing their copy against the kit's is noise on every run for
      anyone who accepted the invitation. What is worth telling them is the other
      comparison: the kit's own copy has moved since they installed. That is
      check-provenance.py's question exactly, has the thing we copied *from* changed since
      we looked, and it is answerable only from the recorded baseline.
    """
    target = Path(entry.get("target", ""))
    source = Path(entry.get("source", ""))
    recorded = entry.get("digests")
    # Falsiness, not `is None`: a `digests` map that is present but empty is no more of a
    # baseline than a missing one, and treating it as valid let a hand-edited manifest
    # report `revised` at exit 0 for an entry nothing had been recorded for.
    if not recorded:
        return "unknown", ("installed before digests were recorded, so whether it is "
                           "current is unknown. Re-install to establish a baseline.")
    if not (target.exists() or target.is_symlink()):
        return "diverged", f"the installed target is gone: {target}"
    if not source.is_dir():
        return "error", (f"the kit no longer has a source at {source}, so the installed "
                         f"copy cannot be compared against anything.")
    if target.is_symlink():
        try:
            same = target.resolve() == source.resolve()
        except OSError:
            same = False
        if same:
            return "linked", "links to its source, so it cannot be stale"

    try:
        current = digest_tree(source)
    except OSError as exc:
        return "error", (f"the kit's source could not be read, so nothing can be compared "
                         f"against it: {exc}")
    if entry.get("name") in ADOPTED_ENTRY_NAMES:
        # Two independent questions, kept separable (bug-0022). The first is "has the kit's
        # copy moved since you installed", answerable only from the baseline. The second is
        # "is every file we placed still there", which needs the installed tree and which
        # nothing asked before: the comparison below ran the record against the source and
        # never opened the install, so whole-directory absence was caught a branch earlier
        # and per-file absence was caught by nothing at all. `_place_adopted` already names
        # a removed lens in plain words on the very next run, which is what makes the
        # silence here a defect rather than the exemption working as designed.
        #
        # The baseline, not the installed tree: naming it "installed" printed a digest
        # matching no file on disk (reported on this pull request).
        moved = _compare(recorded, current, "recorded", "source now")
        try:
            installed = digest_tree(target)
        except OSError as exc:
            return "error", (f"the installed copy could not be read, so whether every "
                             f"file this install placed is still there is unanswerable: "
                             f"{exc}")
        # Absence only, never a digest mismatch. Reporting a changed file here would undo
        # the whole reason this branch exists: an adopter is invited to rewrite a lens, and
        # a file they edited is theirs. A missing file is a different claim, and it is the
        # only one being added. A file they *added* is absent from the baseline and so is
        # ignored in both directions, exactly as `_place_adopted` ignores it.
        missing = [rel for rel in sorted(recorded) if rel not in installed]
        if missing:
            # `diverged` rather than a new word, so the vocabulary stays one vocabulary:
            # this is the same claim the derived path already makes for a file it cannot
            # find, and it carries the exit code that claim already means. What is local to
            # the adopted module is the remedy, because re-installing does not bring the
            # file back, so the message says so rather than leaving the summary's generic
            # advice to mislead the one reader it is aimed at.
            lines = [f"      {rel}: this install placed it, and it is gone from the "
                     f"installed module" for rel in missing]
            if moved:
                lines.append("      and, separately, the kit's copy has moved since this "
                             "install:")
                lines.extend(f"      {p}" for p in moved)
            return "diverged", (
                "a file this install placed is missing from the adopted module:\n"
                + "\n".join(lines)
                + "\n      Deleting a lens is yours to do and nothing here restores it. "
                  "Re-install to have the removal recorded, after which this stops being "
                  "reported, or `--replace-adopted` to take the kit's copy back.")
        if not moved:
            return "ok", f"every file this install placed is still there, and the kit's "\
                         f"copy is unchanged since this install ({len(recorded)} file(s))"
        return "revised", ("the kit's copy has changed since this install; yours is yours "
                           "to keep:\n" + "\n".join(f"      {p}" for p in moved))

    try:
        problems = _compare(digest_tree(target), current)
    except OSError as exc:
        return "error", (f"the installed copy could not be read, so whether it is current "
                         f"is unanswerable: {exc}")
    if not problems:
        return "ok", f"{len(current)} file(s) match the source"
    return "diverged", ("DIVERGED from the source:\n"
                        + "\n".join(f"      {p}" for p in problems))


def check(home: Path) -> int:
    """Report every installed target beneath `home` that no longer matches its source.

    Detect and report, never rewrite. Re-installing is a person's decision, because an
    adopter may have edited an installed file on purpose and an overwrite destroys that
    without asking, which is the same call `feat-0043` made for adapted upstream material.

    Exit codes mirror check-provenance.py, including its precedence: an unanswerable run
    outranks a diverged one, since the first says the report itself cannot be trusted.

    0   every entry beneath this home matches its source, or cannot be stale
    1   at least one installed target has diverged from its source
    2   at least one entry has no baseline, or could not be compared at all
    """
    manifest = load_manifest()
    scoped = [e for e in manifest["entries"] if _beneath(e["target"], home)]
    if not scoped:
        # Deliberately not zero. Nothing recorded is indistinguishable from a record that
        # was deleted (S-005), and reporting "current" for an install this tool cannot see
        # is exactly the silence chore-0031 removes.
        print(f"Nothing recorded as installed beneath {home}, so nothing can be checked.")
        print("If skills are installed there, the record is gone: re-install to "
              "establish a baseline.")
        return 2

    counts = {"ok": 0, "linked": 0, "revised": 0, "diverged": 0, "unknown": 0, "error": 0}
    for entry in sorted(scoped, key=lambda e: (e.get("tool", ""), e.get("name", ""))):
        status, message = _check_entry(entry)
        counts[status] += 1
        print(f"{status:9} {entry.get('tool', ''):8} {entry.get('name', '')}  {message}")

    print(f"\n{counts['ok']} current, {counts['diverged']} diverged, "
          f"{counts['linked']} linked, {counts['revised']} revised upstream, "
          f"{counts['unknown']} unknown, {counts['error']} error(s).")
    if counts["diverged"]:
        print("An installed copy no longer matches this kit. Re-install to refresh it, or "
              "keep your version: this check never rewrites anything.")
    if counts["revised"]:
        print("An adopted file's source has moved since you installed. Your copy is left "
              "alone; merge the kit's change only if you want it.")
    if counts["unknown"]:
        print("An entry predates the digest baseline, so its state is unknown rather than "
              "current. Re-install to establish one.")
    if counts["error"] or counts["unknown"]:
        return 2
    return 1 if counts["diverged"] else 0


def main(argv=None) -> int:
    """Entry point. `argv` defaults to sys.argv[1:]; pass a list to drive it in a test."""
    ap = argparse.ArgumentParser(description="Install the Zen Agent Skills library.")
    ap.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove what was installed")
    ap.add_argument("--check", action="store_true",
                    help="report installed targets beneath --home that no longer match "
                         "their source; writes nothing")
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
    # Deliberately its own flag rather than a --mode value (bug-0018). --mode says how
    # files are placed; this says what happens to work an adopter did, which is a different
    # question and the destructive one.
    ap.add_argument("--replace-adopted", action="store_true",
                    help="overwrite the installed rules module with the kit's copy, "
                         "discarding your edits to it (by default an edited rules file is "
                         "preserved and reported)")
    ap.add_argument("--home", default=None,
                    help="override the base home dir (for testing/unusual setups)")
    args = ap.parse_args(argv)

    home = Path(args.home).expanduser().resolve() if args.home else Path.home()

    if args.check and args.uninstall:
        # Refused rather than ordered. Either precedence silently drops half of what was
        # asked for, and one of the two halves removes files.
        print("--check and --uninstall ask for different things; run them separately.")
        return 2
    if args.check:
        return check(home)
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
    return install(tools, args.mode, home, args.dry_run, args.profile, args.with_hooks,
                   args.replace_adopted)


if __name__ == "__main__":
    raise SystemExit(main())
