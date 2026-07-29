#!/usr/bin/env python3
"""Kit-level lint for every skill in .agents/skills/.

Checks that each skill has a well-formed SKILL.md: frontmatter with `name` and
`description`, `name` matching its directory, a description that says both what
and when (a rough proxy: non-trivial length) and that fits the 1024-character
limit both target harnesses enforce, and a body that is not so long it
defeats progressive disclosure, and frontmatter written in a form no real YAML
parser can read. It also checks that inline relative links resolve
on disk, that `../<name>/SKILL.md` references point at a skill that actually
exists, and warns when a skill asserts both draft and shipped status. Standard
library only. Exits non-zero on error.

Link checks are made against the *shipped* layout, not just the authoring one. A
skill is distributed as a directory alongside the rules module (see
scripts/install.py), so a link that escapes the `.agents/` tree resolves here and
dangles everywhere the skill is actually used. Those are errors even though the
file they name exists in this repository.

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
# Hard upper bound enforced by both harnesses install.py targets, so it is an
# error rather than a guideline: a description over it is rejected or truncated
# by the harness, and the skill then simply never gets selected. Five skills
# shipped over this limit before the check existed (bug-0005).
MAX_DESC_CHARS = 1024

# The frontmatter properties the skill schema permits. An unrecognised key is
# rejected outright rather than ignored, so this is an allow-list and not a
# style preference. Source: ALLOWED_PROPERTIES in quick_validate.py from
# Anthropic's skill-creator plugin, read 2026-07-29. If a harness adds a legal
# property, this constant is what to update; `version` is deliberately absent
# because that reference implementation rejects it even though Anthropic's own
# example skill documents it (bug-0008).
ALLOWED_FRONTMATTER_KEYS = frozenset({
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
})

# A YAML block scalar puts an indicator on the field line and the text on the
# continuation lines below. parse_frontmatter folds those lines together, so
# without this the indicator is counted as description content and every length
# check reads three characters more than a harness would (S-018).
BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\s*")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SIBLING_SKILL_RE = re.compile(r"^\.\./([^/]+)/SKILL\.md$")
EXTERNAL_LINK_PREFIXES = ("http://", "https://", "mailto:")

# A skill declaring itself a draft in prose while also declaring itself shipped
# (typically a "- Shipped <date>" provenance bullet) is self-contradictory.
#
# Neither half needs to be precise on its own, because the finding requires BOTH.
# That conjunction is what keeps the check specific, and it is why these patterns
# can afford to be generous: a skill merely discussing drafts, or merely recording
# that it shipped, produces nothing. Narrow patterns were the actual defect here
# (S-014, 2026-07-27): matching only "is a draft" and a "- Shipped" list item let
# through "remains a draft" beside "- Blessed <date>", among others.
DRAFT_STATUS_RE = re.compile(
    r"\b(?:is|remains|stays)\s+(?:still\s+)?(?:a\s+)?draft\b"
    r"|^\s*status:\s*draft\b"
    r"|\bdraft\s+pending\b",
    re.IGNORECASE | re.MULTILINE,
)
SHIPPED_STATUS_RE = re.compile(
    r"^\s*[-*]\s*\**(?:shipped|blessed)\b"
    r"|\b(?:shipped|blessed)\s+(?:on\s+)?\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE | re.MULTILINE,
)


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
            value = m.group(2).strip().strip('"').strip("'")
            # Drop a block-scalar indicator so the value is the text, not the
            # YAML that introduces it (S-018). Only at the head of a field line:
            # a `>` inside prose is content.
            data[key] = BLOCK_SCALAR_RE.sub("", value, count=1)
        elif key and raw.strip():
            # folded continuation of the previous scalar
            data[key] = (data[key] + " " + raw.strip()).strip()
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


def check_links(skill_md: Path, text: str, skill_names: set, rel: str, errors: list,
                portable_root: Path | None = None) -> None:
    """Flag unresolved relative links, dangling siblings, and non-portable links.

    `portable_root` is the highest directory a skill link may reach: the `.agents/`
    tree that install.py ships (the skills plus the rules module beside them). A link
    above it resolves in this repository and dangles once the skill is installed.
    """
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
        resolved = (skill_md.parent / path_part).resolve()
        if portable_root is not None and not resolved.is_relative_to(portable_root):
            errors.append(
                f"{rel}/SKILL.md: link escapes the shipped skill tree: {path_part}. "
                f"It resolves in this repo but dangles once the skill is installed; "
                f"name the file in prose instead of linking to it."
            )
            continue
        if not resolved.exists():
            errors.append(f"{rel}/SKILL.md: link target does not exist: {path_part}")


def check_frontmatter_is_parseable(text: str, rel: str, errors: list) -> None:
    """Flag a plain frontmatter scalar that a real YAML parser would reject.

    Deliberately narrow, and not a YAML validator: the standard-library-only rule
    rules out importing one. This catches the single construct that has actually
    shipped here (S-019). A plain unquoted value containing ": " reads as a nested
    mapping, and one ending in ":" reads as a key expecting a value, so YAML
    rejects the whole file. This script's own parser is a regex and accepts both,
    which is how eight skills stayed unreadable by every real consumer while every
    gate passed (bug-0007). Quote the value or use a block scalar.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        m = re.match(r"^(\w[\w-]*):[ \t]+(\S.*)$", raw)
        if not m:
            continue
        key, value = m.group(1), m.group(2).rstrip()
        if BLOCK_SCALAR_RE.match(value):
            continue  # a block scalar may contain anything
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            continue  # quoted, so the colon is just text
        if ": " in value or value.endswith(":"):
            errors.append(
                f"{rel}/SKILL.md: `{key}` is a plain scalar containing a colon, which YAML "
                f"reads as a nested mapping, so no real parser can read this file. Quote the "
                f"value or write it as a block scalar (`{key}: >-`). This checks one known "
                f"construct, not YAML validity in general."
            )


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
    # Everything install.py ships: the skills plus the sibling rules module.
    portable_root = skills_dir.parent.resolve()

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
        elif len(desc) > MAX_DESC_CHARS:
            errors.append(f"{rel}/SKILL.md: description is {len(desc)} chars, over the "
                          f"{MAX_DESC_CHARS}-char limit both target harnesses enforce; "
                          f"cut prose that restates the body and keep the trigger phrases")
        # Checked on the parsed value, not the raw line: a block scalar's field line
        # is literally `description: >-`, so a raw-text check would flag the twelve
        # skills that use one (S-020).
        if desc and ("<" in desc or ">" in desc):
            errors.append(f"{rel}/SKILL.md: description contains an angle bracket, which the "
                          f"skill schema both target harnesses enforce rejects; use a plain "
                          f"noun instead of a `<placeholder>` in trigger phrases")
        for key in sorted(set(fm) - ALLOWED_FRONTMATTER_KEYS):
            errors.append(f"{rel}/SKILL.md: frontmatter key {key!r} is not in the skill schema, "
                          f"which rejects an unrecognised property rather than ignoring it; "
                          f"allowed: {', '.join(sorted(ALLOWED_FRONTMATTER_KEYS))}")
        if body_lines > MAX_BODY_LINES:
            warnings.append(f"{rel}/SKILL.md: body is {body_lines} lines "
                            f"(> {MAX_BODY_LINES}); push detail into referenced files")
        check_links(skill_md, text, skill_names, rel, errors, portable_root)
        check_frontmatter_is_parseable(text, rel, errors)
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
