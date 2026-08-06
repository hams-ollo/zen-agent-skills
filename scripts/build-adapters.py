#!/usr/bin/env python3
"""Generate thin per-harness adapters from each skill's SKILL.md.

Each SKILL.md is the single harness-agnostic source of truth. Claude Code and
OpenCode read that format natively (install.py places it for them). Cursor and
VS Code do not, so this generates their native equivalents by inlining the skill
body, so the same instructions travel without being hand-maintained twice.

Targets:
    cursor  -> <out>/.cursor/rules/<name>.mdc          (Cursor rule)
    vscode  -> <out>/.github/prompts/<name>.prompt.md   (VS Code / Copilot prompt)
    plugin  -> <out>/skills/<name>/SKILL.md             (Claude Code plugin tree)

    python scripts/build-adapters.py                    # cursor and vscode, into ./ (cwd)
    python scripts/build-adapters.py --target cursor --out ../my-project
    python scripts/build-adapters.py --target plugin --out .tmp/plugin

Inlining a body verbatim would break every relative link in it, because the
adapter does not sit where the skill sits. A skill references three things
outside its own file, and all three are rewritten and their targets emitted:

    ../<sibling>/SKILL.md  ->  <sibling><adapter-ext>, the adapter beside it
    ../../rules/<file>     ->  ../../.agents/rules/<file>, emitted once
    templates/<file>       ->  ../../.agents/skills/<name>/templates/<file>

Both adapter directories are two levels below <out>, so `../../` reaches the
project root from either, and the shared material has one location rather than
one per target. An existing <out>/.agents/rules/ file is never overwritten: that
module is swappable by design, so a project's own copy outranks this one.

The plugin target does not inline. Installing a plugin copies its directory, so
a path leaving that directory resolves to nothing at the installed location and
the emitted tree has to be self-contained. It is laid out to be exactly that:
each skill keeps its own directory under skills/, and the rules module sits
beside it at rules/. That is the same geometry the source tree already has, with
the .agents/ parent dropped, because a skill at .agents/skills/<name>/ reaching
../../rules/<file> lands on .agents/rules/<file> exactly as a skill at
skills/<name>/ reaching the same path lands on rules/<file>. Every source link
therefore resolves unchanged, so a skill is copied verbatim instead of rewritten
and nothing in the tree points outside it. The shared prefix is stated per target
rather than globally for this reason: the depth is the same, the .agents/ segment
is not.

The plugin target is opt-in rather than a default, because a default run writes
into a project root and a committed .claude-plugin/ there is the hand-maintained
second copy this generator exists to prevent.

Standard library only. Generated adapters are overwritten each run (they are
derived artifacts); do not hand-edit them, edit the SKILL.md instead.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import namedtuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
RULES_DIR = REPO_ROOT / ".agents" / "rules"

BANNER = "<!-- generated from .agents/skills/{name}/SKILL.md by build-adapters.py. Do not edit here. -->"

# Where an inlined adapter reaches for material shared between skills. Both
# adapter directories are two deep, so this is the same string for both of them.
# It is not the same for every target: the plugin target is two deep as well but
# reaches `../../rules/`, with no .agents/ segment, which is why the shared
# location is a property of the target below rather than this constant alone.
SHARED = "../../.agents"

# Where each target's shared material lands under <out>. The two inlining targets
# flatten every skill into one directory and share one .agents/ tree; the plugin
# target keeps each skill's own directory and must be self-contained, so its
# shared material sits at the plugin root (see the module docstring).
Layout = namedtuple("Layout", "rules_dir assets_dir")
LAYOUTS = {
    "cursor": Layout(".agents/rules", ".agents/skills"),
    "vscode": Layout(".agents/rules", ".agents/skills"),
    "plugin": Layout("rules", "skills"),
}

# The plugin's published identity, and the one place to edit it. Both manifests
# are generated from this single mapping, so the marketplace entry cannot drift
# from the plugin it points at. The repository carries no other version source,
# so bumping the release means bumping this line.
PLUGIN = {
    "name": "zen-agent-skills",
    "version": "0.1.0",
    "description": "Portable, cross-harness agent skills for spec-driven work: "
                   "authoring specs and tasks, dispatching parallel agents, and "
                   "reviewing, testing, and documenting what they produce.",
    "author": {"name": "Zen Solutions", "url": "https://github.com/hams-ollo"},
    "homepage": "https://github.com/hams-ollo/zen-agent-skills",
    "repository": "https://github.com/hams-ollo/zen-agent-skills",
    "license": "MIT",
    "keywords": ["skills", "agents", "spec-driven", "code-review", "documentation"],
}

LINK_RE = re.compile(r"\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
SIBLING_RE = re.compile(r"^\.\./([^/]+)/SKILL\.md(#.*)?$")
RULES_RE = re.compile(r"^\.\./\.\./rules/(.+)$")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
# Kept identical to validate-skills.py's copy. Two parsers that agree are bad; two
# that have drifted apart are worse, and this defect had to be found twice already.
BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\s*")


def rewrite_links(body: str, skill_name: str, ext: str) -> str:
    """Repoint a skill body's relative links so they resolve from the adapter."""

    def repl(m: re.Match) -> str:
        target, title = m.group(1), m.group(2)

        def out(new: str) -> str:
            return f"]({new}{title})"

        if target.startswith("#") or target.lower().startswith(EXTERNAL_PREFIXES):
            return m.group(0)  # anchors and external URLs travel unchanged

        sibling = SIBLING_RE.match(target)
        if sibling:
            # The sibling's adapter is generated into this same directory.
            return out(f"{sibling.group(1)}{ext}{sibling.group(2) or ''}")

        rules = RULES_RE.match(target)
        if rules:
            return out(f"{SHARED}/rules/{rules.group(1)}")

        if target.startswith("../"):
            # Nothing else should escape the skill directory; validate-skills.py
            # fails the build on those, so leaving it unrewritten is honest.
            return m.group(0)

        # Skill-local supporting file (templates/, references/, scripts/).
        return out(f"{SHARED}/skills/{skill_name}/{target}")

    return LINK_RE.sub(repl, body)


def emit_shared_assets(skill_dir: Path, out: Path, dry: bool,
                       layout: Layout = LAYOUTS["cursor"]) -> list[Path]:
    """Place the material an emitted body points at. Returns what was written.

    `layout` says where that material lands for the requesting target. The rule
    each kind is treated by does not vary with the layout, only its destination.
    """
    written = []

    # The rules module, once per run, never clobbering a project's own copy.
    if RULES_DIR.is_dir():
        for src in sorted(RULES_DIR.rglob("*")):
            if not src.is_file():
                continue
            dest = out / layout.rules_dir / src.relative_to(RULES_DIR)
            if dest.resolve() == src.resolve() or dest.exists():
                continue  # same file, or the project already has its own
            if not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            written.append(dest)

    # This skill's own supporting files (everything but the SKILL.md itself).
    for src in sorted(skill_dir.rglob("*")):
        if not src.is_file() or src.name == "SKILL.md":
            continue
        dest = out / layout.assets_dir / skill_dir.name / src.relative_to(skill_dir)
        if dest.resolve() == src.resolve():
            continue  # building into the kit itself; the file is already there
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        written.append(dest)

    return written


def split_frontmatter(text: str):
    """Return (frontmatter_dict, body_text).

    A block-scalar indicator is dropped so an emitted `description` is the scalar's
    text and not its YAML serialisation. Four skills write `description: >-`, and
    without this every adapter for them opened with `description: ">- Turns ..."`,
    which is well-formed and wrong: valid YAML holding three characters of syntax
    (bug-0006). The same fix is in validate-skills.py's copy of this parser, which
    is where the duplication is the real problem.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    data = {}
    key = None
    for raw in lines[1:end]:
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", raw)
        if m:
            key = m.group(1)
            value = m.group(2).strip().strip('"').strip("'")
            data[key] = BLOCK_SCALAR_RE.sub("", value, count=1)
        elif key and raw.strip():
            data[key] = (data[key] + " " + raw.strip()).strip()
    body = "\n".join(lines[end + 1:]).strip()
    return data, body


def discover_skills():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def emit_cursor(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".cursor" / "rules" / f"{name}.mdc"
    content = (
        f"---\ndescription: {json.dumps(desc)}\nalwaysApply: false\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.mdc')}\n"
    )
    _write(dest, content, dry)
    return dest


def emit_vscode(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".github" / "prompts" / f"{name}.prompt.md"
    content = (
        f"---\nmode: agent\ndescription: {json.dumps(desc)}\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.prompt.md')}\n"
    )
    _write(dest, content, dry)
    return dest


def emit_plugin(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    """Place a skill in the plugin tree, verbatim.

    Nothing is rewritten and nothing is re-serialised. The plugin layout keeps
    the geometry every source link is written for, so a rewrite would have to
    reproduce the path it was given; and round-tripping the frontmatter through
    this module's reader would drop any key it does not model and flatten any it
    does. The destination uses the source *directory* name rather than the
    frontmatter `name`, because `../<dir>/SKILL.md` is what a sibling link names.
    """
    dest = out / "skills" / src.name / "SKILL.md"
    if dry:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "SKILL.md", dest)
    return dest


def emit_plugin_manifests(out: Path, dry: bool) -> list[Path]:
    """Write the two manifests a Claude Code plugin and its marketplace need.

    Both are generated from PLUGIN, so the marketplace entry cannot drift from
    the plugin it points at. The marketplace lists exactly one plugin, whose
    source is the emitted root itself.
    """
    marketplace = {
        "name": PLUGIN["name"],
        "owner": PLUGIN["author"],
        "metadata": {"description": PLUGIN["description"], "version": PLUGIN["version"]},
        "plugins": [{
            "name": PLUGIN["name"],
            "source": "./",
            "description": PLUGIN["description"],
            "version": PLUGIN["version"],
        }],
    }
    written = []
    for fname, obj in (("plugin.json", dict(PLUGIN)), ("marketplace.json", marketplace)):
        dest = out / ".claude-plugin" / fname
        _write(dest, json.dumps(obj, indent=2) + "\n", dry)
        written.append(dest)
    return written


def _write(dest: Path, content: str, dry: bool):
    if dry:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


EMITTERS = {"cursor": emit_cursor, "vscode": emit_vscode, "plugin": emit_plugin}


def main(argv=None) -> int:
    """Entry point. `argv` defaults to sys.argv[1:]; pass a list to drive it in a test."""
    ap = argparse.ArgumentParser(description="Generate per-harness skill adapters.")
    ap.add_argument("--target", default="cursor,vscode",
                    help="comma-separated subset of: " + ",".join(EMITTERS)
                         + " (default: cursor,vscode; plugin is opt-in, because a "
                           "default run writes into a project root)")
    ap.add_argument("--out", default=".", help="output project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    bad = [t for t in targets if t not in EMITTERS]
    if bad:
        print(f"Unknown target(s): {bad}. Choose from {list(EMITTERS)}.")
        return 2

    out = Path(args.out).expanduser().resolve()
    skills = discover_skills()
    if not skills:
        print(f"No skills found under {SKILLS_DIR}.")
        return 0

    # Targets sharing a layout share one copy of the shared material, so cursor
    # and vscode together still emit it once. A layout is per target, so asking
    # for cursor and plugin emits it into both trees.
    layouts = []
    for t in targets:
        if LAYOUTS[t] not in layouts:
            layouts.append(LAYOUTS[t])

    tag = "[dry-run] " if args.dry_run else ""
    n = 0
    assets = 0
    for d in skills:
        fm, body = split_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        name = fm.get("name", d.name)
        desc = fm.get("description", "")
        for t in targets:
            dest = EMITTERS[t](d, name, desc, body, out, args.dry_run)
            print(f"{tag}{t:7} {name}  -> {dest.relative_to(out) if dest.is_relative_to(out) else dest}")
            n += 1
        # The emitted bodies point at these; without them the links dangle.
        for layout in layouts:
            assets += len(emit_shared_assets(d, out, args.dry_run, layout))

    manifests = emit_plugin_manifests(out, args.dry_run) if "plugin" in targets else []
    for dest in manifests:
        print(f"{tag}{'plugin':7} manifest  -> {dest.relative_to(out)}")

    roots = ", ".join(sorted({Path(p).parts[0] + "/"
                              for layout in layouts for p in layout}))
    print(f"\n{tag}Generated {n} adapter file(s) for {len(skills)} skill(s), "
          f"plus {assets} shared asset file(s) under {roots}.")
    if manifests:
        print(f"{tag}Generated {len(manifests)} plugin manifest file(s) "
              f"under .claude-plugin/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
