#!/usr/bin/env python3
"""Validate the .tasks/ backlog.

Ships with the init-worktracking scaffold. Checks the mechanical integrity a
multi-agent workflow depends on: every task file has a well-formed frontmatter,
ids are unique and match their filenames, every depends_on resolves to a real
task, every relative markdown link resolves from where the file actually lives,
and (with --strict) every touched_files path exists.

It also warns when a link's text names one path and the link opens another, the
class underneath a dangling link. That one is a heuristic rather than a fact, so
it is reported as a warning on purpose: see mislabelled_links() for why a false
positive there is more expensive than a miss.

A second mode link-checks an arbitrary set of documents instead of the backlog,
so a CI docs link gate can call the link rule here rather than author its own
copy of it. Every pattern it is given must match at least one document, and the
run names any that did not. See check_links() for why that matters.

Standard library only, so it runs anywhere a bare Python 3 does. Exits non-zero
on any error, so it drops cleanly into CI or a pre-commit hook.

    python .tasks/validate.py            # errors fail, missing files warn
    python .tasks/validate.py --strict   # warnings become errors too
    python .tasks/validate.py --links '*.md' 'docs/**/*.md'   # link-check documents
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TASKS_DIR.parent

REQUIRED = ["id", "type", "status", "priority", "parent", "depends_on",
            "touched_files", "created"]
# Optional, and only meaningful together: the approved spec this task implements
# and the scenario ids it covers. They are what makes a task traceable to a
# contract, which is what a spec-plan-readiness gate checks for.
OPTIONAL_SPEC_FIELDS = ["spec", "scenarios"]
TYPES = {"bug", "feat", "chore", "epic"}
STATUSES = {"open", "in_progress", "blocked", "done"}
PRIORITIES = {"P0", "P1", "P2"}
ID_RE = re.compile(r"^(bug|feat|chore|epic)-\d{4}$")
SCENARIO_RE = re.compile(r"^S-\d{3}$")
# An upstream issue reference, stored in GitHub's own syntax so emitting it is
# concatenation rather than translation: `#123` here, `owner/repo#123` elsewhere.
# A bare number is rejected on purpose; see docs/spec/tracker-links.md.
EXTERNAL_RE = re.compile(r"^(?:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)?#\d+$")

SKIP_NAMES = {"README.md", "_TEMPLATE.md"}

# A complete markdown link: bracketed text followed immediately by a parenthesised
# target. It ignores a bare closing fragment, which is how prose that describes a
# link escapes being treated as one.
#
# This comment used to claim the regex was "deliberately identical" to a copy of it
# inside the docs link step in .github/workflows/checks.yml. The claim was true when
# written and false by the time anyone relied on it: bug-0015 taught this copy that a
# link inside a code span is not a link, and the CI copy learned nothing, so the two
# disagreed about what counts as a link while a comment said they could not. That step
# now calls check_links() below instead of restating the rule (chore-0029), which is
# why the guarantee is structural rather than a promise in a comment.
#
# Which functions honour the code-span and fenced-block exclusion, stated here because
# the paragraph above once implied "this file" and meant one of its two functions:
# BOTH do. broken_links() skips a match whose opening bracket falls inside an inline
# code span or a fenced code block, and mislabelled_links() skips one on the same test
# over LINK_TEXT_RE below. bug-0015 and bug-0017 gave the rule to the second only;
# bug-0023 gave it to the first, which is the one both callers actually run.
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# `file://` belongs here for a different reason than the other three. Those are
# network schemes this checker has no business fetching. This one is an absolute
# path outside the repository: an adopting repository may write absolute `file:`
# links as its documented house style, and such a path is not this checker's to
# resolve, because it names a location on someone's disk rather than a place inside
# the repository. Treating one as relative reported every such link as broken, which
# made the validator unusable in exactly the repositories that had committed to the
# convention.
#
# `file://` and not a bare `file:`, deliberately. The two-slash form covers
# `file:///d:/x` and `file://host/share`, which is every form the house style in
# question produces. A bare `file:` is legal in the URI spec, is not what anyone
# writes in Markdown, and is short enough that matching it risks swallowing a
# genuinely broken relative link that happens to start the same way.
#
# TWO copies of this rule exist and must stay in step: here, and the
# `init-worktracking` template that ships into an adopter's tree. The template cannot
# import from this repository, which is why that one duplication is tolerated rather
# than fixed. A third copy used to live inline in `.github/workflows/checks.yml`; it
# drifted, and chore-0029 replaced it with a call to check_links() below.
#
# Deliberately NOT a fourth and fifth copy: `scripts/validate-skills.py` and
# `scripts/build-adapters.py` carry a similar-looking tuple guarding a different
# rule, that a skill body's links may not escape the installed skill tree. An
# absolute link there is a portability defect the contract already forbids, so
# adding `file://` to those would weaken a real check rather than fix this one.
LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:", "file://")

# The same links LINK_RE matches, with the text captured as well. A second pattern
# rather than a second group on LINK_RE so that pattern stays character-for-character
# comparable with the copy it is kept in step with.
LINK_TEXT_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
# Link text that is path-shaped: no whitespace, and made only of the characters a
# repository path uses. Prose fails this on the first space, which is the cheapest
# reliable way to tell "README.md" from "the readme".
TEXT_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
# A trailing `:29`, as in `.tasks/README.md:29`. Text in that form cites a location
# inside a file rather than claiming which file the link opens, so it is left alone.
LINE_SUFFIX_RE = re.compile(r":\d+$")
# A run of one or more backticks. Markdown opens an inline code span with a run of
# any length and closes it with a run of the same length, so the single-backtick
# form is half the problem: a task file documenting a link bug reaches for the
# double form the moment the text it quotes contains a backtick of its own.
BACKTICK_RUN_RE = re.compile(r"`+")
# A fenced code block delimiter: a whole line whose content is a run of three or more
# backticks, optionally followed by an info string. Up to three spaces of indentation,
# per CommonMark. The info string may not contain a backtick, because a run followed by
# a backtick is simply a longer run rather than a fence with a label.
FENCE_RE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")


def parse_frontmatter(text: str):
    """Return a dict from a leading `---` YAML-ish block, or None if absent.

    Handles the small subset the task template uses: `key: scalar`,
    `key: [a, b]` inline lists, and block lists of `  - item` lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None

    data = {}
    current_list_key = None
    for raw in lines[1:end]:
        if re.match(r"^\s*-\s+", raw) and current_list_key is not None:
            item = raw.strip()[1:].strip().strip('"').strip("'")
            data[current_list_key].append(item)
            continue
        m = re.match(r"^(\w+):\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            data[key] = []
            current_list_key = key
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            data[key] = [x.strip().strip('"').strip("'")
                         for x in inner.split(",") if x.strip()]
            current_list_key = None
        else:
            data[key] = val.strip('"').strip("'")
            current_list_key = None
    return data


def task_files():
    files = []
    for p in sorted(TASKS_DIR.glob("*.md")):
        if p.name not in SKIP_NAMES:
            files.append(p)
    done = TASKS_DIR / "done"
    if done.is_dir():
        for p in sorted(done.glob("*.md")):
            if p.name not in SKIP_NAMES:
                files.append(p)
    return files


def markdown_files():
    """Every Markdown file under .tasks/, not only the task files.

    Wider than task_files() on purpose: a broken link in README.md is exactly as
    clickable as one in a task file, and excluding it would leave a hole for no
    benefit.
    """
    return sorted(TASKS_DIR.rglob("*.md"))


def broken_links(path):
    """Relative link targets in `path` that do not resolve from its own directory.

    Resolving against `path.parent` rather than against the repository root is the
    whole point. A task file is authored in .tasks/, where `../scripts/x.py` is
    correct, and the lifecycle moves it to .tasks/done/ at closeout, where `../`
    now means .tasks/ and every such link dangles. Checking a link where the file
    currently lives is what makes that move fail loudly instead of silently.

    A link inside an inline code span or a fenced code block is skipped, the same rule
    mislabelled_links() follows and for the same reason: such a link renders as literal
    text, so there is no target to resolve and no reader to send anywhere (bug-0015,
    bug-0017). It reached this function last (bug-0023), which cost two task files a
    rewording apiece to quote a broken link as the example of the bug they documented.

    The ranges are computed once for the file rather than once per link, because this
    runs over every markdown file under .tasks/ and every globbed document.
    """
    found = []
    content = path.read_text(encoding="utf-8")
    spans = code_span_ranges(content) + fenced_block_ranges(content)
    for match in LINK_RE.finditer(content):
        if any(start <= match.start() < end for start, end in spans):
            continue
        target = match.group(1).split("#")[0].strip()
        if not target or target.startswith(LINK_SKIP_PREFIXES):
            continue
        if not (path.parent / target).exists():
            found.append(target)
    return found


def code_span_ranges(text):
    """Character ranges `(start, end)` of the inline code spans in `text`.

    A code span opens with a run of backticks and closes with a run of the same
    length, so both the single and the double form are spans, and a check that
    knows only the first fixes half the occurrences it meets.

    Scanned one line at a time, deliberately. Markdown does let a span wrap across
    lines inside a paragraph, but pairing runs across the whole file means one
    stray backtick swallows everything up to the next stray one, and a caller that
    skips those ranges then reports success while checking nothing. Bounding the
    search to a line caps what a stray backtick costs at that line, so the worst
    case is the false positive this helper exists to remove, never a check that has
    quietly switched itself off. An unmatched run is left as ordinary text for the
    same reason: it opens nothing.
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
    them with nothing and a link inside a fence went on being reported after the
    inline form was fixed (bug-0017). The two rules compose by union rather than by
    replacement, which is why this is a separate pass and not a change to the pairing
    above.

    A line whose whole content is a run of three or more backticks opens a block, and
    a later line whose own run is at least as long and carries nothing after it closes
    one.

    An unterminated opening fence yields no range at all. That is the same trade
    code_span_ranges() makes for an unmatched backtick run, for the same reason: a
    detector that ran an unclosed fence to end of file would switch the caller's check
    off for everything below it and report success while doing so. Preferring the
    false positive this helper exists to remove over a check that has quietly disabled
    itself is the direction of failure this validator chose (bug-0015).
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


def mislabelled_links(path):
    """Links in `path` whose text names one repository path and which open another.

    The class underneath broken_links(). `.tasks/README.md` exists, so `../README.md`
    written from `.tasks/done/` resolves to it rather than to the root README: existence
    is satisfied, nothing dangles, and the reader still lands somewhere the link text
    never named. Three completed task files in this repository carried exactly that link
    while every check reported success (bug-0012).

    Returns a list of `(text, target, actual)` triples, where `actual` is the
    repository-relative path the link really opens.

    This is a heuristic, and its false positives are the design problem, so it is
    deliberately a quiet one. It fires only when all of the following hold:

      * the link's opening bracket is outside every inline code span and every fenced
        code block, because a link that renders as literal text is clickable by nobody,
        so there is no reader to mislead and nothing to report (bug-0015, bug-0017);
      * the text is path-shaped, so prose like `the readme` is never compared;
      * the text carries no `:line` suffix, which cites a location rather than naming
        the file a link opens;
      * the text names a file that actually exists when read from the repository root,
        so a bare word that merely looks path-shaped is ignored;
      * the link's own target resolves, since a dangling one is broken_links()' finding
        and reporting it twice helps nobody;
      * and the two are different files.

    Preferring to under-fire is the point. A false positive on a completed task file
    pressures an author into rewording a historical record to satisfy a checker, which
    is worse than a missed link. That is also why callers report this as a warning.
    """
    found = []
    content = path.read_text(encoding="utf-8")
    spans = code_span_ranges(content) + fenced_block_ranges(content)
    for match in LINK_TEXT_RE.finditer(content):
        if any(start <= match.start() < end for start, end in spans):
            continue
        text = match.group(1).strip().strip("`").strip()
        target = match.group(2).split("#")[0].strip()
        if not target or target.startswith(LINK_SKIP_PREFIXES):
            continue
        if not text or not TEXT_PATH_RE.match(text) or LINE_SUFFIX_RE.search(text):
            continue
        named = REPO_ROOT / text
        actual = path.parent / target
        if not named.is_file() or not actual.exists():
            continue
        try:
            if named.resolve() == actual.resolve():
                continue
            rel = actual.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        found.append((text, target, rel))
    return found


def check_links(patterns) -> int:
    """Report relative links that do not resolve, across an arbitrary set of globs.

    The second caller of the one link rule in this file, and the only entry point here
    that does not read the backlog at all. A CI docs link gate needs the same rule over
    a different file set: this validator walks the tracker directory, and the gate walks
    the documents around it. Those sets are disjoint on purpose and each has caught
    breakage the other passed clean over, so the answer was never to delete one check.

    It was to give the rule a second caller instead of a second author. The gate used to
    restate the rule inline, and the restatement drifted the moment bug-0015 taught this
    file that a link inside a code span is not a link: a correctly quoted example in a
    changelog passed here and failed there, and the entry had to be reworded to satisfy
    a checker (chore-0029).

    Patterns are globbed from the repository root, so `**` means what pathlib means by
    it everywhere else in this file. Matching nothing is an error rather than a pass:
    a link check over an empty file set reports zero broken links over zero documents
    and exits clean, which is the one failure indistinguishable from success.

    **Every pattern must match at least one document**, and the run names each one that
    did not. The first form of this guard fired per run instead, so it caught only the
    case where every pattern died: a caller passing three globs kept passing when one of
    them stopped matching, on the strength of the others (chore-0032). Measured here on
    2026-08-27, `--links '*.md' 'docs/**/*.md' 'totally-gone/**/*.md'` reported 44
    documents and exit 0, and renaming `docs/` would have left the CI gate checking 9 of
    45 documents while reporting success. The dead glob is exactly the case with no
    other symptom, because the surviving patterns supply a reassuring count.

    There is deliberately no way to mark a pattern optional. No caller here or in the
    scaffolded template has a pattern that can legitimately match nothing, and an escape
    hatch is how a guard stops guarding; a caller whose tree may be absent passes only
    the patterns it has.
    """
    docs = set()
    unmatched = []
    for pattern in patterns:
        matched = [p for p in REPO_ROOT.glob(pattern) if p.is_file()]
        if not matched:
            unmatched.append(pattern)
        docs.update(matched)

    broken = []
    for path in sorted(docs):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for target in broken_links(path):
            broken.append(f"{rel} -> {target}")

    for entry in broken:
        print(f"broken link: {entry}")
    print(f"checked {len(docs)} documents, {len(broken)} broken link(s)")
    # `--links` with nothing after it reaches the loop above with nothing to iterate, so
    # it produces no dead pattern to blame and would otherwise exit 0 over zero
    # documents. It gets its own branch rather than a `not docs` test, because after
    # this change `docs` being empty is a consequence of the patterns rather than the
    # thing being reported.
    if not patterns:
        print("no document matched: (no pattern given)")
        return 1
    for pattern in unmatched:
        print(f"no document matched: {pattern}")
    return 1 if broken or unmatched else 0


def main(argv=None) -> int:
    # `argv` is injectable so the CLI layer is reachable from a test, matching
    # validate-skills.py, build-adapters.py, and install.py (chore-0017). Calling
    # main() with no argument behaves exactly as before.
    args = sys.argv[1:] if argv is None else list(argv)
    # A second mode, and the only one that does not read .tasks/ at all: link-check an
    # arbitrary set of documents, so the docs link gate in CI calls this rule rather
    # than restate it (chore-0029). Everything after --links is a glob, resolved from
    # the repository root:
    #
    #     python .tasks/validate.py --links '*.md' 'docs/**/*.md'
    #
    # Every pattern must match at least one document, and one that does not fails the
    # run and is named (chore-0032). The bound is per pattern, not per run.
    if "--links" in args:
        return check_links(args[args.index("--links") + 1:])
    strict = "--strict" in args
    files = task_files()

    errors, warnings = [], []

    def err(f, msg):
        errors.append((f, msg))

    def warn(f, msg):
        (errors if strict else warnings).append((f, msg))

    parsed = {}
    ids_seen = {}
    all_ids = set()

    for f in files:
        rel = f.relative_to(REPO_ROOT).as_posix()
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            err(rel, "no YAML frontmatter block")
            continue
        parsed[f] = fm
        tid = fm.get("id")
        if tid:
            all_ids.add(tid)
            ids_seen.setdefault(tid, []).append(rel)

    for f, fm in parsed.items():
        rel = f.relative_to(REPO_ROOT).as_posix()
        in_done = f.parent.name == "done"

        for field in REQUIRED:
            if field not in fm:
                err(rel, f"missing required field: {field}")

        tid = fm.get("id", "")
        ttype = fm.get("type", "")
        status = fm.get("status", "")
        priority = fm.get("priority", "")

        if ttype and ttype not in TYPES:
            err(rel, f"invalid type: {ttype!r} (expected {sorted(TYPES)})")
        if status and status not in STATUSES:
            err(rel, f"invalid status: {status!r}")
        if priority and priority not in PRIORITIES:
            warn(rel, f"unusual priority: {priority!r} (expected {sorted(PRIORITIES)})")

        if tid:
            if not ID_RE.match(tid):
                warn(rel, f"id {tid!r} does not match <type>-NNNN")
            stem = f.stem
            if not (stem == tid or stem.startswith(tid + "-")):
                err(rel, f"id {tid!r} does not match filename {f.name!r}")

        if in_done and status and status != "done":
            warn(rel, f"file in done/ but status is {status!r}")
        if not in_done and status == "done":
            warn(rel, "status is done but file is not in done/")

        for dep in fm.get("depends_on", []) or []:
            if dep == tid:
                err(rel, f"depends_on lists itself: {dep}")
            elif dep not in all_ids:
                err(rel, f"depends_on unresolved: {dep!r} is not a known task id")

        touched = fm.get("touched_files", []) or []
        if not touched:
            warn(rel, "touched_files is empty")
        # A completed task's touched_files are a historical record of what it changed,
        # not a claim about the tree today. Checking them means any later rename, move,
        # or deletion breaks the backlog permanently, and the only way to "fix" it is to
        # rewrite the ledger. So the existence check applies to open work only.
        if not in_done:
            for path in touched:
                if not (REPO_ROOT / path).exists():
                    warn(rel, f"touched_files path does not exist: {path}")

        # Spec traceability, when the task claims any. Absent is fine: not every
        # task comes from a spec. Present but malformed is not, because a
        # readiness gate reads these to map tasks to scenarios.
        spec = fm.get("spec", "")
        scenarios = fm.get("scenarios", []) or []
        if isinstance(scenarios, str):
            scenarios = [scenarios]
        for sid in scenarios:
            if not SCENARIO_RE.match(sid):
                err(rel, f"scenario id {sid!r} does not match S-NNN")
        if scenarios and not spec:
            warn(rel, "scenarios are listed but no spec: field names the contract they come from")
        if spec and not (REPO_ROOT / spec).exists():
            warn(rel, f"spec path does not exist: {spec}")

        # The upstream issue this task serves, when it has one. Absent is fine
        # (S-008). Present but malformed is an error rather than a warning
        # (S-007), because the value is emitted verbatim into a pull request
        # description: a form GitHub does not recognise is ignored silently, and
        # the issue simply never closes.
        external = fm.get("external", "")
        if external and not EXTERNAL_RE.match(external):
            err(rel, f"external {external!r} is not a GitHub issue reference "
                     f"(#123 or owner/repo#123)")

    for tid, where in ids_seen.items():
        if len(where) > 1:
            err(where[0], f"duplicate id {tid!r} also in: {', '.join(where[1:])}")

    # Links are checked in done/ too, unlike touched_files. The asymmetry is
    # deliberate: a completed task's touched_files are a historical claim that
    # harms nobody once a file is renamed, whereas a link is a live affordance a
    # reader clicks and gets nothing from. So a rename that orphans a link in the
    # ledger is a thing to fix, not a thing to exempt.
    for f in markdown_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        for target in broken_links(f):
            hint = ""
            if (f.parent / ".." / target).exists():
                hint = (" (one level too shallow; a file moved to done/ needs "
                        "one more '../')")
            err(rel, f"relative link does not resolve: {target}{hint}")
        # A warning and not an error, deliberately. The check above states a fact
        # (the file is not there); this one states a judgement about what an author
        # meant, and it ships to every repository the scaffold touches. Failing an
        # adopter's clean tree on a guess is the one outcome worth designing against,
        # so a default run reports it and only --strict promotes it.
        for text, target, actual in mislabelled_links(f):
            warn(rel, f"link text names {text} but {target} opens {actual}")

    for f, msg in warnings:
        print(f"WARN  {f}: {msg}")
    for f, msg in errors:
        print(f"ERROR {f}: {msg}")

    n = len(files)
    print(f"\nChecked {n} task file{'s' if n != 1 else ''}: "
          f"{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
