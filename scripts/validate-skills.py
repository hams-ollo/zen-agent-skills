#!/usr/bin/env python3
"""Kit-level lint for every skill in .agents/skills/.

Checks that each skill has a well-formed SKILL.md: frontmatter with `name` and
`description`, `name` matching its directory, a description that says both what
and when (a rough proxy: non-trivial length) and that fits the 1024-character
limit both target harnesses enforce, and a body that is not so long it
defeats progressive disclosure, and frontmatter written in a form no real YAML
parser can read. It also checks that inline relative links resolve
on disk, that `../<name>/SKILL.md` references point at a skill that actually
exists, that every self-declared lens under `.agents/rules/` is referenced by at
least one skill, and warns when a skill asserts both draft and shipped status. A link inside
an inline code span or a fenced code block is left alone, because it renders as
literal text and opens nothing, so a skill may show an example link. Standard
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

# A run of one or more backticks, and a fenced code block delimiter: a whole line whose
# content is a run of three or more backticks, optionally followed by an info string.
# Up to three spaces of indentation, per CommonMark. The info string may not contain a
# backtick, because a run followed by a backtick is simply a longer run.
#
# These two patterns and the two helpers below are REPRODUCED from `.tasks/validate.py`,
# where bug-0015 and bug-0017 taught the backlog validator that a link rendered as
# literal text is not a link. Copied rather than imported: the two validators are
# separate tools with separate lifecycles, and `validate.py` also ships as a template
# into other repositories, so neither may depend on the other. The regexes are kept
# character-identical to the originals so a later reader can diff the two copies.
BACKTICK_RUN_RE = re.compile(r"`+")
FENCE_RE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")

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

# A rules file that presents itself as a lens: something a skill is meant to compose,
# rather than a plain document that happens to live beside them. All three shipped
# lenses say so in their own opening, either by naming themselves one in the title or
# by the "swappable module" formula the rules directory uses as a header convention.
#
# Keyed off that self-declaration rather than a list of filenames, deliberately: a
# hardcoded list passes the day a fourth lens is added and nobody edits this script,
# which is the exact failure feat-0048 was filed for. `autonomy.md` called itself the
# third lens for ten days while no skill composed it, and every gate passed.
LENS_DECLARATION_RE = re.compile(r"\*\*swappable module\*\*|\blens\b", re.IGNORECASE)

# How far into a rules file the self-declaration has to appear. See
# `declares_itself_a_lens` for why the window exists and why it is this size.
LENS_DECLARATION_LINES = 10


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


def code_span_ranges(text):
    """Character ranges `(start, end)` of the inline code spans in `text`.

    A span opens with a run of backticks and closes with a run of the same length, so
    both the single and the double form are spans, and a check that knows only the first
    fixes half the occurrences it meets.

    Scanned one line at a time, deliberately, and an unmatched run opens nothing:
    pairing runs across the whole file means one stray backtick swallows everything up
    to the next stray one, and a caller that skips those ranges then reports success
    while checking nothing. See `code_span_ranges()` in .tasks/validate.py, the original.
    """
    ranges = []
    offset = 0
    for line in text.splitlines(keepends=True):
        runs = [(m.start(), m.end()) for m in BACKTICK_RUN_RE.finditer(line)]
        i = 0
        while i < len(runs):
            opener = runs[i]
            width = opener[1] - opener[0]
            closer = next((j for j in range(i + 1, len(runs))
                           if runs[j][1] - runs[j][0] == width), None)
            if closer is None:
                i += 1
                continue
            ranges.append((offset + opener[0], offset + runs[closer][1]))
            i = closer + 1
        offset += len(line)
    return ranges


def fenced_block_ranges(text):
    """Character ranges `(start, end)` of the fenced code blocks in `text`.

    A fence is a line-level construct where an inline code span is a character-level
    one. Its delimiters sit alone on lines of their own, so code_span_ranges() pairs
    them with nothing: the two rules compose by union rather than by replacement.

    An unterminated opening fence yields no range at all, the same trade
    code_span_ranges() makes for an unmatched run and for the same reason: a detector
    that ran an unclosed fence to end of file would switch the caller's link check off
    for everything below it and report success while doing so. See
    `fenced_block_ranges()` in .tasks/validate.py, the original.
    """
    ranges = []
    offset = 0
    start = None
    width = 0
    for line in text.splitlines(keepends=True):
        match = FENCE_RE.match(line.rstrip("\r\n"))
        if match:
            if start is None:
                start, width = offset, len(match.group(1))
            elif len(match.group(1)) >= width and not match.group(2).strip():
                ranges.append((start, offset + len(line)))
                start = None
        offset += len(line)
    return ranges


def _link_targets(text: str):
    """Yield the raw target of every inline markdown link found in text.

    A link whose opening bracket falls inside an inline code span or a fenced code
    block is skipped: it renders as literal text, so it opens nothing and there is no
    reader to strand. Without this a skill body could not *show* an example markdown
    link, which is exactly what the documentation skills want to do (bug-0027).
    """
    spans = code_span_ranges(text) + fenced_block_ranges(text)
    for m in LINK_RE.finditer(text):
        if any(start <= m.start() < end for start, end in spans):
            continue
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

    A link inside an inline code span or a fenced code block is not checked at all, by
    any of the three rules here, because it is not a link: it renders as literal text.
    That includes the escape rule, which protects a reader who follows a link that
    dangles once the skill is installed, and there is no such reader for an example
    (bug-0027). Outside a span or a fence the escape rule is unchanged, and an absolute
    or `file://` link is still an error here even though the backlog validator skips one.
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


def declares_itself_a_lens(text: str) -> bool:
    """True when a rules file's opening presents it as a lens skills compose.

    Bounded to the first `LENS_DECLARATION_LINES` lines because the declaration is a
    header convention, not a fact stated anywhere in the body: all three shipped lenses
    make it by line 3 (a title ending in "lens", or "This file is a **swappable
    module**"). Without the bound the patterns are broad enough to match any rules file
    that merely *mentions* a lens further down, for instance a directory README
    describing what the other files are, and a check that fires on a document nobody
    intended as a lens gets switched off rather than satisfied.
    """
    opening = "\n".join(text.splitlines()[:LENS_DECLARATION_LINES])
    return bool(LENS_DECLARATION_RE.search(opening))


def check_lenses_are_composed(rules_dir: Path, skill_texts: dict, errors: list) -> None:
    """Flag a self-declared lens under `.agents/rules/` that no skill references.

    A lens is composed, not run: it reaches an agent only through the skill that points
    at it. One nobody points at is inert, and the failure is silent, because the module
    still reads correctly on its own and its claim to govern anything is never tested.
    The swappability promise fails with it: an adopter who rewrites the module changes
    nothing, which is the same class of defect the link-escape rule catches.

    A reference is the lens's filename appearing anywhere in a `SKILL.md`, which counts
    both the usual relative link and a prose mention that names the file. The bare word
    (`autonomy`) is deliberately not enough, or any skill discussing the subject would
    satisfy the rule without giving a reader a way to reach the module.

    Skipped entirely when there is no sibling `rules/` directory, since a skills tree
    without one has no lens to leave unwired.
    """
    if not rules_dir.is_dir():
        return
    for rules_file in sorted(rules_dir.glob("*.md")):
        text = rules_file.read_text(encoding="utf-8")
        if not declares_itself_a_lens(text):
            continue
        if any(rules_file.name in skill_text for skill_text in skill_texts.values()):
            continue
        errors.append(
            f"{_rel(rules_file)}: declares itself a lens but no skill references it, so "
            f"nothing composes it and an adopter who rewrites it changes nothing. Point at "
            f"it from the skills whose rules it holds (one line in a `## Conventions` "
            f"section is the usual shape), or drop the self-declaration from its opening."
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
    skill_texts: dict = {}

    for d in skills:
        rel = _rel(d)
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{rel}: no SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        skill_texts[d.name] = text
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

    # Checked once over the whole tree rather than per skill: "no skill references this
    # lens" is a fact about every skill together, and it is the one rule here that reads
    # outside .agents/skills/.
    check_lenses_are_composed(portable_root / "rules", skill_texts, errors)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\nChecked {len(skills)} skill(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
