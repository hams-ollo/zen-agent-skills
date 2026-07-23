#!/usr/bin/env python3
"""Kit-level lint for every skill in .agents/skills/.

Checks that each skill has a well-formed SKILL.md: frontmatter with `name` and
`description`, `name` matching its directory, a description that says both what
and when (a rough proxy: non-trivial length), and a body that is not so long it
defeats progressive disclosure. Standard library only. Exits non-zero on error.

    python scripts/validate-skills.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

MAX_BODY_LINES = 500          # progressive-disclosure guideline
MIN_DESC_CHARS = 40           # a real "what + when" description is not tiny


def parse_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, 0
    data = {}
    key = None
    for raw in lines[1:end]:
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", raw)
        if m:
            key = m.group(1)
            data[key] = m.group(2).strip().strip('"').strip("'")
        elif key and raw.strip():
            # folded continuation of the previous scalar
            data[key] += " " + raw.strip()
    body_lines = len(lines) - (end + 1)
    return data, body_lines


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"ERROR no skills directory at {SKILLS_DIR}")
        return 1

    errors, warnings = [], []
    skills = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())

    if not skills:
        print(f"No skills found under {SKILLS_DIR.relative_to(REPO_ROOT).as_posix()}.")
        return 0

    for d in skills:
        rel = d.relative_to(REPO_ROOT).as_posix()
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{rel}: no SKILL.md")
            continue
        fm, body_lines = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{rel}/SKILL.md: no YAML frontmatter")
            continue
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            errors.append(f"{rel}/SKILL.md: missing `name`")
        elif name != d.name:
            errors.append(f"{rel}/SKILL.md: name {name!r} != directory {d.name!r}")
        if not desc:
            errors.append(f"{rel}/SKILL.md: missing `description`")
        elif len(desc) < MIN_DESC_CHARS:
            warnings.append(f"{rel}/SKILL.md: description looks thin "
                            f"({len(desc)} chars); say what it does and when to use it")
        if body_lines > MAX_BODY_LINES:
            warnings.append(f"{rel}/SKILL.md: body is {body_lines} lines "
                            f"(> {MAX_BODY_LINES}); push detail into referenced files")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\nChecked {len(skills)} skill(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
