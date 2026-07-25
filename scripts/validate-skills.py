#!/usr/bin/env python3
"""Kit-level lint for every skill in .agents/skills/.

Checks that each skill has a well-formed SKILL.md: frontmatter with `name` and
`description`, `name` matching its directory, a description that says both what
and when (a rough proxy: non-trivial length), and a body that is not so long it
defeats progressive disclosure. It also checks that inline relative links resolve
on disk, that `../<name>/SKILL.md` references point at a skill that actually
exists, and warns when a skill asserts both draft and shipped status. Standard
library only. Exits non-zero on error.

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

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SIBLING_SKILL_RE = re.compile(r"^\.\./([^/]+)/SKILL\.md$")
EXTERNAL_LINK_PREFIXES = ("http://", "https://", "mailto:")

# A skill declaring itself a draft in prose while also declaring itself shipped
# (typically a "- Shipped <date>" provenance bullet) is self-contradictory.
DRAFT_STATUS_RE = re.compile(r"\bis (?:a|still a) draft\b", re.IGNORECASE)
SHIPPED_STATUS_RE = re.compile(r"^-\s*shipped\b", re.IGNORECASE | re.MULTILINE)


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


def _rel(path: Path) -> str:
    """Repo-relative display path, falling back to the full path when outside the repo."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _link_targets(text: str):
    """Yield the raw target of every inline markdown link found in text."""
    for m in LINK_RE.finditer(text):
        target = m.group(1).strip()
        # Drop an optional "title" suffix, e.g. (path "some title").
        target = target.split(" ", 1)[0]
        if target:
            yield target


def check_links(skill_md: Path, text: str, skill_names: set, rel: str, errors: list) -> None:
    """Flag unresolved relative links and dangling sibling-skill references."""
    for target in _link_targets(text):
        if target.lower().startswith(EXTERNAL_LINK_PREFIXES):
            continue
        path_part, _, _anchor = target.partition("#")
        if not path_part:
            continue  # anchor-only link within the same page
        sibling = SIBLING_SKILL_RE.match(path_part)
        if sibling:
            sibling_name = sibling.group(1)
            if sibling_name not in skill_names:
                errors.append(
                    f"{rel}/SKILL.md: references sibling skill {sibling_name!r} via "
                    f"{path_part}, but no such skill exists in this kit"
                )
            continue
        if not (skill_md.parent / path_part).exists():
            errors.append(f"{rel}/SKILL.md: link target does not exist: {path_part}")


def check_status_contradiction(text: str, rel: str, warnings: list) -> None:
    """Warn when a skill asserts both draft and shipped status."""
    if DRAFT_STATUS_RE.search(text) and SHIPPED_STATUS_RE.search(text):
        warnings.append(
            f"{rel}/SKILL.md: asserts both draft and shipped status; reconcile which is current"
        )


def main(skills_dir: Path = SKILLS_DIR) -> int:
    if not skills_dir.is_dir():
        print(f"ERROR no skills directory at {skills_dir}")
        return 1

    errors, warnings = [], []
    skills = sorted(p for p in skills_dir.iterdir() if p.is_dir())

    if not skills:
        print(f"No skills found under {_rel(skills_dir)}.")
        return 0

    skill_names = {d.name for d in skills}

    for d in skills:
        rel = _rel(d)
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{rel}: no SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm, body_lines = parse_frontmatter(text)
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
        check_links(skill_md, text, skill_names, rel, errors)
        check_status_contradiction(text, rel, warnings)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\nChecked {len(skills)} skill(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
