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

Standard library only. Generated files are overwritten each run (they are
derived artifacts); do not hand-edit them, edit the SKILL.md instead.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

BANNER = "<!-- generated from .agents/skills/{name}/SKILL.md by build-adapters.py. Do not edit here. -->"


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
        f"---\ndescription: {desc}\nalwaysApply: false\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{body}\n"
    )
    _write(dest, content, dry)
    return dest


def emit_vscode(name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".github" / "prompts" / f"{name}.prompt.md"
    content = (
        f"---\nmode: agent\ndescription: {desc}\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{body}\n"
    )
    _write(dest, content, dry)
    return dest


def _write(dest: Path, content: str, dry: bool):
    if dry:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


EMITTERS = {"cursor": emit_cursor, "vscode": emit_vscode}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate per-harness skill adapters.")
    ap.add_argument("--target", default="cursor,vscode",
                    help="comma-separated subset of: " + ",".join(EMITTERS))
    ap.add_argument("--out", default=".", help="output project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

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
    for d in skills:
        fm, body = split_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        name = fm.get("name", d.name)
        desc = fm.get("description", "")
        for t in targets:
            dest = EMITTERS[t](name, desc, body, out, args.dry_run)
            print(f"{tag}{t:7} {name}  -> {dest.relative_to(out) if dest.is_relative_to(out) else dest}")
            n += 1
    print(f"\n{tag}Generated {n} adapter file(s) for {len(skills)} skill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
