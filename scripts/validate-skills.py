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

The same link rules run over the markdown a skill ships *beside* its SKILL.md, in
`references/` or anywhere else in the skill directory, because those files are part
of the one tree that installs into an adopter's repository and nothing else looks at
them: the `--links` globs the CI gate passes never reach `.agents/` (chore-0036).
A file whose name carries the `.tmpl` suffix is deliberately not checked; see
`classify_supporting_file` for the rule and why it is drawn there.

They run once more over the markdown that ships under `.agents/` *outside* any skill
directory, which is the rules module and the hooks README (chore-0058). Those travel
to an adopter exactly as a skill does, so a link in one is exactly as breakable, and
until this rule nothing read a link out of them: `check_lenses_are_composed` opens the
rules directory to ask a different question entirely, and the CI `--links` globs stop
at `docs/`. See `check_portable_markdown` for the walk and the one geometry it
declines to run over.

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

# The two file kinds a skill ships beside its SKILL.md, and the marker that tells them
# apart. See `classify_supporting_file` for the argument; these are the constants it reads.
# Both are written lowercase and both are matched against a lowered name, because the case
# an author typed is not a fact about where a file's links resolve (chore-0055).
TEMPLATE_SUFFIX = ".tmpl"
SUPPORTING_MARKDOWN_SUFFIXES = frozenset({".md", ".mdc"})

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


def check_links(source: Path, text: str, skill_names: set, label: str, errors: list,
                portable_root: Path | None = None, sibling_shortcut: bool = True) -> None:
    """Flag unresolved relative links, dangling siblings, and non-portable links.

    `source` is the file the links were read from, and every relative target resolves
    from its parent directory. `label` is what the error messages name, so a caller
    checking a supporting file passes that file's path rather than the skill's.

    `portable_root` is the highest directory a skill link may reach: the `.agents/`
    tree that install.py ships (the skills plus the rules module beside them). A link
    above it resolves in this repository and dangles once the skill is installed.

    `sibling_shortcut` governs the `../<name>/SKILL.md` rule, and is off for a
    supporting file. That rule reads the target as a skill *name* rather than as a
    path, which is only correct one directory level up from a sibling skill, where a
    SKILL.md sits. From a supporting file one level deeper, `../beta/SKILL.md` names a
    subdirectory of this skill and not the skill `beta`, so the shortcut would clear a
    genuinely broken link whenever a real skill happened to share the name. With the
    shortcut off, the same link is resolved on disk like any other, which is correct
    there and simply reports the ordinary "does not exist" message.

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
        sibling = SIBLING_SKILL_RE.match(path_part) if sibling_shortcut else None
        if sibling:
            sibling_name = sibling.group(1)
            if sibling_name not in skill_names:
                errors.append(
                    f"{label}: references sibling skill {sibling_name!r} via "
                    f"{path_part}, but no such skill exists in this kit"
                )
            continue
        resolved = (source.parent / path_part).resolve()
        if portable_root is not None and not resolved.is_relative_to(portable_root):
            errors.append(
                f"{label}: link escapes the shipped skill tree: {path_part}. "
                f"It resolves in this repo but dangles once the skill is installed; "
                f"name the file in prose instead of linking to it."
            )
            continue
        if not resolved.exists():
            errors.append(f"{label}: link target does not exist: {path_part}")


def classify_supporting_file(path: Path) -> str:
    """Sort a file shipped beside a SKILL.md into `template`, `markdown`, or `other`.

    Only `markdown` is link-checked, and the bound is the whole point of this rule
    (chore-0036). A skill directory holds two kinds of file, and they answer the
    question "where do this file's links resolve from?" differently:

    - Read **in place**, from inside the installed skill tree: a `references/` note, or
      a document describing the directory it sits in. Its relative links must resolve
      from where the file sits, which is exactly what `check_links` already tests, so
      the SKILL.md rule extends to it unchanged.
    - Written **somewhere else**: a template, whose links are authored for the
      destination and are meant to dangle where the file currently sits. A link to
      `.tasks/` inside `AGENTS.md.tmpl` is correct at an adopter's repository root.
      Resolving it from `.agents/skills/init-worktracking/templates/` would report every
      such link as broken and make the check unusable.

    The marker is the `.tmpl` suffix, which this kit already puts on exactly the files
    it writes into another repository. It is deliberately a property of the file itself
    rather than a table of destinations declared in a skill body or in this script: a
    table is a second source of truth that drifts from the skill silently, and the
    silent-drift failure is the one this whole rule exists to catch. The cost is that a
    destination-bound markdown file added *without* the suffix would be checked against
    this repository and would report links written for somewhere else. That failure is
    loud rather than silent, and the fix is to rename the file, which is also what makes
    it a template to every other reader.

    `other` covers the non-markdown files (a `.py`, a `.toml`, a `.json`). Markdown link
    syntax in those is not a link, so they are counted and not read.

    **Both suffix tests are case-insensitive, and they have to agree** (chore-0055). They
    did not until then: the marker was matched exactly while the markdown suffixes were
    lowered first, so `AGENTS.md.TMPL` was neither a template nor markdown and fell to
    `other`. The direction is the one the markdown line already took, so an author's
    shift key changes no classification: `.TMPL` names a destination-bound file as plainly
    as `.tmpl` does, and the two spellings are the same file to a case-insensitive
    filesystem. Widening the marker can only move a file out of the checked set, never
    into it, since a name ending in `.tmpl` in any case has `.tmpl` as its suffix and so
    can never also be `.md` or `.mdc`. What it moves is one skipped count into the other.
    """
    name = path.name.lower()
    if name.endswith(TEMPLATE_SUFFIX):
        return "template"
    if path.suffix.lower() in SUPPORTING_MARKDOWN_SUFFIXES:
        return "markdown"
    return "other"


def _is_shipped(rel: Path, path: Path) -> bool:
    """Whether a file under a skill directory is authored content the kit distributes.

    Mirrors `_digestable` in scripts/install.py, which in turn mirrors the ignore list
    its `_copy` places with (`shutil.ignore_patterns("__pycache__", "*.pyc")`). A byte
    cache is in no installed skill, so it belongs in neither the checking nor the count.

    Not hypothetical: `init-worktracking/templates/validate.py` grows a `__pycache__` the
    moment the test suite imports it, and without this the reported supporting-file count
    would depend on whether the tests had already run.
    """
    return path.suffix != ".pyc" and "__pycache__" not in rel.parts


def check_supporting_files(skill_dir: Path, skill_names: set, rel: str, errors: list,
                           portable_root: Path | None = None) -> dict:
    """Link-check the markdown a skill ships beside its SKILL.md; return the file counts.

    The counts are returned rather than printed so `main` can report one total across
    the tree. All three are reported, including the two that were skipped, because a
    coverage number nobody can compare across runs is the gap this rule closes rather
    than a report of it: "0 supporting files checked" reads identically whether the rule
    is working or the walk is broken, until the count of what it declined to read sits
    beside it.
    """
    counts = {"markdown": 0, "template": 0, "other": 0}
    skill_md = skill_dir / "SKILL.md"
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        if path == skill_md:
            continue
        if not _is_shipped(path.relative_to(skill_dir), path):
            continue
        kind = classify_supporting_file(path)
        counts[kind] += 1
        if kind != "markdown":
            continue
        label = f"{rel}/{path.relative_to(skill_dir).as_posix()}"
        check_links(path, path.read_text(encoding="utf-8"), skill_names, label, errors,
                    portable_root, sibling_shortcut=False)
    return counts


def check_portable_markdown(portable_root: Path, skills_dir: Path, skill_names: set,
                            errors: list) -> dict | None:
    """Link-check the shipped markdown under `.agents/` that sits outside every skill.

    The same three rules a supporting file gets, one directory level up: the rules
    module and the hooks README ship to an adopter as surely as a skill does, so a link
    in one of them is exactly as clickable and exactly as breakable (chore-0058). Both
    existing link gates miss them by construction. `main` walks `SKILLS_DIR.iterdir()`,
    which cannot reach a sibling of the skills tree, and the `--links` globs the CI gate
    passes (`*.md`, `.github/**/*.md`, `docs/**/*.md`) never enter `.agents/` at all.

    `sibling_shortcut` stays off for the same reason it is off for a supporting file, and
    the reason is sharper here rather than weaker: from `.agents/rules/`,
    `../skills/doc-sync/SKILL.md` is a path to resolve on disk, and a bare
    `../doc-sync/SKILL.md` names a sibling of the *rules* directory that does not exist,
    not the skill `doc-sync`. With the shortcut on, the second form would be cleared
    whenever a real skill happened to share the name, which is the broken link this rule
    is for.

    The escape ceiling is `portable_root` unchanged. A rules file reaching
    `../skills/y/SKILL.md` stays inside it, and one reaching `../../ROADMAP.md` does not.
    That second form is the half worth having: it resolves in this repository, so it
    reads correctly to everyone here, and it dangles in every installed tree, because
    install.py places `rules/` beside `skills/` and nothing above.

    Classification, the `.tmpl` skip, and the byte-cache exclusion are `classify_supporting_file`
    and `_is_shipped` reused rather than reimplemented. Both decisions carry over unchanged:
    a template's links are authored for its destination, and a `__pycache__` is in no
    installed tree, so counting one would make the coverage number depend on whether the
    test suite had already run.

    Returns the counts, or `None` when the walk did not run. It runs only where the
    skills directory is named the way every layout install.py places names it
    (`<base>/skills`, with the rules module at `<base>/../rules`), because only then is
    the parent directory a shipped tree. `main` is deliberately callable against any
    directory of skill folders, and for such a caller the parent is whatever happens to
    sit beside it: pointed at a scratch directory it would walk that directory's parent,
    read unrelated markdown, and report someone else's broken links as this kit's. The
    returned `None` is reported in words rather than as a count of zero, so a run that
    declined to look never reads like a run that looked and found nothing.
    """
    if skills_dir.name != SKILLS_DIR.name:
        return None
    counts = {"markdown": 0, "template": 0, "other": 0}
    for path in sorted(p for p in portable_root.rglob("*") if p.is_file()):
        if path.is_relative_to(skills_dir):
            continue
        if not _is_shipped(path.relative_to(portable_root), path):
            continue
        kind = classify_supporting_file(path)
        counts[kind] += 1
        if kind != "markdown":
            continue
        check_links(path, path.read_text(encoding="utf-8"), skill_names, _rel(path),
                    errors, portable_root, sibling_shortcut=False)
    return counts


def portable_coverage(counts: dict | None, portable_root: Path, skills_dir: Path) -> str:
    """One sentence saying what the walk beside the skills tree actually covered.

    Three renderings, because there are three different facts and a coverage line that
    renders them identically is the failure bug-0045 exists to remove rather than a
    report of it:

    - It did not look, because the tree it was given is not a shipped layout.
    - It looked and there is nothing there, said in words and naming the directory.
    - It looked and found files, said as the checked count with both skipped counts
      beside it, so "0 checked" is separable from "0 present".

    Only the third has the shape `coverage_line()` in scripts/run-checks.py selects on,
    which is why the words in the first two matter: that function shows the last line of
    a gate's output containing a digit, and a gate declining to look must not be able to
    borrow a number from somewhere else in the sentence and look busy.
    """
    if counts is None:
        return (f"Did not look beside {_rel(skills_dir)}: a shipped skills tree is named "
                f"{SKILLS_DIR.name!r} in every layout install.py places, so this one has "
                f"no shipped tree around it to check.")
    if not any(counts.values()):
        return f"Nothing ships under {_rel(portable_root)} outside the skills tree."
    return (f"Also link-checked {counts['markdown']} file(s) under {_rel(portable_root)} "
            f"outside the skills tree; skipped {counts['template']} template(s) and "
            f"{counts['other']} non-markdown file(s).")


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


def _names_file_outside_fences(text: str, filename: str) -> bool:
    """True when `filename` appears in `text` somewhere other than a fenced code block.

    A fence is the body *showing* what a reference looks like rather than making one. In
    a skill that is usually sample text some other agent is being told to write, so it
    points no reader at the file and composes nothing, which is the failure the lens rule
    exists to catch rather than a lesser form of compliance (`bug-0040`).

    Inline code spans are deliberately **not** excluded, which is where this parts company
    with the link rules and their S-022 exception. A link inside a span is not a link at
    all: its brackets render as literal text, so there is nothing to follow and no reader
    to strand. A filename inside a span is still prose naming the file, and backticks are
    how the house style writes such a mention, so excluding spans here would reject the
    exact form S-023 protects and push an author to drop the backticks to satisfy a
    validator.

    An unterminated opening fence yields no range at all, inherited from
    `fenced_block_ranges()`, so one stray fence cannot suppress every mention below it and
    report a wired lens as unwired.
    """
    fences = fenced_block_ranges(text)
    start = text.find(filename)
    while start != -1:
        if not any(lo <= start < hi for lo, hi in fences):
            return True
        start = text.find(filename, start + len(filename))
    return False


def check_lenses_are_composed(rules_dir: Path, skill_texts: dict, errors: list) -> None:
    """Flag a self-declared lens under `.agents/rules/` that no skill references.

    A lens is composed, not run: it reaches an agent only through the skill that points
    at it. One nobody points at is inert, and the failure is silent, because the module
    still reads correctly on its own and its claim to govern anything is never tested.
    The swappability promise fails with it: an adopter who rewrites the module changes
    nothing, which is the same class of defect the link-escape rule catches.

    A reference is the lens's filename appearing in a `SKILL.md` outside every fenced
    code block, which counts both the usual relative link and a prose mention that names
    the file. The bare word (`autonomy`) is deliberately not enough, or any skill
    discussing the subject would satisfy the rule without giving a reader a way to reach
    the module. A mention inside a fence is not enough either, for the same reason: it
    shows what a reference looks like instead of making one. See
    `_names_file_outside_fences()` for why inline code spans still count.

    Skipped entirely when there is no sibling `rules/` directory, since a skills tree
    without one has no lens to leave unwired.
    """
    if not rules_dir.is_dir():
        return
    for rules_file in sorted(rules_dir.glob("*.md")):
        text = rules_file.read_text(encoding="utf-8")
        if not declares_itself_a_lens(text):
            continue
        if any(_names_file_outside_fences(skill_text, rules_file.name)
               for skill_text in skill_texts.values()):
            continue
        errors.append(
            f"{_rel(rules_file)}: declares itself a lens but no skill references it, so "
            f"nothing composes it and an adopter who rewrites it changes nothing. Point at "
            f"it from the skills whose rules it holds (one line in a `## Conventions` "
            f"section is the usual shape), or drop the self-declaration from its opening. "
            f"Naming the file only inside a fenced code block does not count: that shows "
            f"what a reference looks like rather than making one."
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
    supporting = {"markdown": 0, "template": 0, "other": 0}

    for d in skills:
        rel = _rel(d)
        skill_md = d / "SKILL.md"
        # Before the SKILL.md checks, and outside every `continue` below them: what a
        # skill ships beside its body is a fact about the directory, so a skill whose
        # frontmatter fails to parse must not silently drop its supporting files from
        # both the checking and the count.
        for kind, n in check_supporting_files(d, skill_names, rel, errors,
                                              portable_root).items():
            supporting[kind] += n
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
        check_links(skill_md, text, skill_names, f"{rel}/SKILL.md", errors, portable_root)
        check_frontmatter_is_parseable(text, rel, errors)
        check_status_contradiction(text, rel, warnings)

    # Checked once over the whole tree rather than per skill: "no skill references this
    # lens" is a fact about every skill together, and it is the one rule here that reads
    # outside .agents/skills/ to ask that question.
    check_lenses_are_composed(portable_root / "rules", skill_texts, errors)
    # And once over the markdown beside the skills tree, which is a different question
    # about the same files: check_lenses_are_composed asks whether a skill points *at*
    # a lens and never reads a link *out* of one (chore-0058). Deliberately not folded
    # into that function, which skips whenever there is no rules directory, a branch that
    # is correct for the lens rule and would silently drop `.agents/hooks/README.md` here.
    portable = check_portable_markdown(portable_root, skills_dir.resolve(),
                                       skill_names, errors)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\nChecked {len(skills)} skill(s): "
          f"{len(errors)} error(s), {len(warnings)} warning(s).")
    # A second line rather than a longer first one: the summary above is the shape the
    # contract states and the tests assert, and the supporting-file coverage is a
    # different count answering a different question.
    #
    # The walk beside the skills tree lands on that same second line rather than on a
    # third, and that is a decision rather than a layout preference (chore-0058).
    # `coverage_line()` in scripts/run-checks.py shows one line per gate: the last line
    # of its output containing a digit. For the `lint skills` gate that is already this
    # line, so a third line would take its place and the acceptance command would stop
    # reporting the supporting-file coverage that bug-0045 and chore-0036 put there.
    # Appending keeps every count in the one line that survives, which is what makes the
    # criterion "the run reports how many it checked" true of `validate-skills.py` and of
    # `run-checks.py` at once instead of only the first.
    #
    # The skill count is named here as well as on the line above, and that is the whole
    # of chore-0064 (2026-08-27). The same rule that keeps this line is what discards the
    # one before it, so until now the only line the acceptance command showed for this
    # gate carried no count of the thing the gate is named after: two clean runs, one
    # over 20 skills and one over 21, printed a byte-identical line. It also opened
    # "beside them", whose antecedent was the discarded line, so a reader of
    # `python scripts/run-checks.py` had none. Carrying the count into this line is the
    # one fix of the three available that neither reorders the two lines nor merges
    # them, both of which diverge from the `Output` surface element of
    # docs/spec/validate-skills.md, which fixes their order and their shape.
    print(f"Link-checked {supporting['markdown']} supporting file(s) beside the "
          f"{len(skills)} skill(s) checked; skipped {supporting['template']} "
          f"template(s) whose links are written for another repository and "
          f"{supporting['other']} non-markdown file(s). "
          f"{portable_coverage(portable, portable_root, skills_dir)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
