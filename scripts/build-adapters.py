#!/usr/bin/env python3
"""Generate thin per-harness adapters from each skill's SKILL.md.

Each SKILL.md is the single harness-agnostic source of truth. Claude Code and
OpenCode read that format natively (install.py places it for them). Cursor and
VS Code do not, so this generates their native equivalents by inlining the skill
body, so the same instructions travel without being hand-maintained twice.

Targets:
    cursor  -> <out>/.cursor/rules/<name>.mdc          (Cursor rule)
    vscode  -> <out>/.github/prompts/<name>.prompt.md   (VS Code / Copilot prompt)

    python scripts/build-adapters.py                    # both, into ./ (cwd)
    python scripts/build-adapters.py --target cursor --out ../my-project

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

Standard library only. Generated adapters are overwritten each run (they are
derived artifacts); do not hand-edit them, edit the SKILL.md instead.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
RULES_DIR = REPO_ROOT / ".agents" / "rules"

BANNER = "<!-- generated from .agents/skills/{name}/SKILL.md by build-adapters.py. Do not edit here. -->"

# Where an adapter reaches for material shared between skills. Both adapter
# directories are two deep, so this is the same string for every target.
SHARED = "../../.agents"

LINK_RE = re.compile(r"\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
SIBLING_RE = re.compile(r"^\.\./([^/]+)/SKILL\.md(#.*)?$")
RULES_RE = re.compile(r"^\.\./\.\./rules/(.+)$")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


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


def emit_shared_assets(skill_dir: Path, out: Path, dry: bool) -> list[Path]:
    """Place the material a rewritten body now points at. Returns what was written."""
    written = []

    # The rules module, once per run, never clobbering a project's own copy.
    if RULES_DIR.is_dir():
        for src in sorted(RULES_DIR.rglob("*")):
            if not src.is_file():
                continue
            dest = out / ".agents" / "rules" / src.relative_to(RULES_DIR)
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
        dest = out / ".agents" / "skills" / skill_dir.name / src.relative_to(skill_dir)
        if dest.resolve() == src.resolve():
            continue  # building into the kit itself; the file is already there
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        written.append(dest)

    return written


def split_frontmatter(text: str):
    """Return (frontmatter_dict, body_text)."""
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
            data[key] = m.group(2).strip().strip('"').strip("'")
        elif key and raw.strip():
            data[key] += " " + raw.strip()
    body = "\n".join(lines[end + 1:]).strip()
    return data, body


def discover_skills():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def emit_cursor(name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".cursor" / "rules" / f"{name}.mdc"
    content = (
        f"---\ndescription: {json.dumps(desc)}\nalwaysApply: false\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.mdc')}\n"
    )
    _write(dest, content, dry)
    return dest


def emit_vscode(name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".github" / "prompts" / f"{name}.prompt.md"
    content = (
        f"---\nmode: agent\ndescription: {json.dumps(desc)}\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.prompt.md')}\n"
    )
    _write(dest, content, dry)
    return dest


def _write(dest: Path, content: str, dry: bool):
    if dry:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


EMITTERS = {"cursor": emit_cursor, "vscode": emit_vscode}


def main(argv=None) -> int:
    """Entry point. `argv` defaults to sys.argv[1:]; pass a list to drive it in a test."""
    ap = argparse.ArgumentParser(description="Generate per-harness skill adapters.")
    ap.add_argument("--target", default="cursor,vscode",
                    help="comma-separated subset of: " + ",".join(EMITTERS))
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

    tag = "[dry-run] " if args.dry_run else ""
    n = 0
    assets = 0
    for d in skills:
        fm, body = split_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        name = fm.get("name", d.name)
        desc = fm.get("description", "")
        for t in targets:
            dest = EMITTERS[t](name, desc, body, out, args.dry_run)
            print(f"{tag}{t:7} {name}  -> {dest.relative_to(out) if dest.is_relative_to(out) else dest}")
            n += 1
        # The rewritten bodies point at these; without them the links dangle.
        assets += len(emit_shared_assets(d, out, args.dry_run))
    print(f"\n{tag}Generated {n} adapter file(s) for {len(skills)} skill(s), "
          f"plus {assets} shared asset file(s) under .agents/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
