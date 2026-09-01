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

A link inside an inline code span or a fenced code block is left alone, because it
renders as literal text: the skill is showing an example link rather than making
one, and repointing it would change what the body says (bug-0028).

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

Every write lands inside <out>. A skill's frontmatter `name` becomes a path
component of the two inlining destinations, so a `..` segment in one would walk
out of the output root and write wherever it landed (bug-0060). Two things stop
that: a `name` that is not the source directory's name is refused before any
emitter is dispatched, which is the rule validate-skills.py already states, and
`_write` compares the resolved destination against the resolved root for every
file it places. Either refusal fails the whole run with exit 2, in a preview as
well as in a real run, rather than skipping the skill and emitting the rest.

Standard library only. Generated adapters are overwritten each run (they are
derived artifacts); do not hand-edit them, edit the SKILL.md instead.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import namedtuple
import sys
from pathlib import Path

# `_textio` is a sibling module in this directory, imported through the repository root so
# the one spelling works whether this file is run as a script or imported as a module of
# `scripts`, which `observatory/serve.py` already does for `install`. Same preamble as there,
# and the same reason: the two invocations put different directories on `sys.path`.
_TEXTIO_ROOT = Path(__file__).resolve().parent.parent
if str(_TEXTIO_ROOT) not in sys.path:
    sys.path.insert(0, str(_TEXTIO_ROOT))
from scripts._textio import NotUTF8, read_text_utf8   # noqa: E402

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

# A run of one or more backticks, and a fenced code block delimiter: a whole line whose
# content is a run of three or more backticks, optionally followed by an info string.
# Up to three spaces of indentation, per CommonMark. The info string may not contain a
# backtick, because a run followed by a backtick is simply a longer run.
#
# These two patterns and the two helpers below are REPRODUCED from validate-skills.py,
# which took them from `.tasks/validate.py`, where bug-0015 and bug-0017 taught the
# backlog validator that a link rendered as literal text is not a link. This is the
# third copy, and copying rather than importing is the decision bug-0027 recorded: the
# three tools have separate lifecycles and `validate.py` also ships as a template into
# other repositories, so none of them may depend on another. The regexes are kept
# character-identical to the originals so a later reader can diff the copies when the
# rule next changes.
BACKTICK_RUN_RE = re.compile(r"`+")
FENCE_RE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")


class OutsideOutputRoot(Exception):
    """A write whose destination resolved outside the run's output root.

    Raised rather than printed at the point of detection, because the two facts a
    reader needs are known in two different places: `_write` sees the destination and
    the root, and only the caller knows which skill and which target produced them.
    """

    def __init__(self, dest: Path, root: Path):
        self.dest = dest
        self.root = root
        super().__init__(f"{dest} is not under {root}")


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
    that ran an unclosed fence to end of file would switch the caller off for
    everything below it and report success while doing so. See `fenced_block_ranges()`
    in .tasks/validate.py, the original.
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


def rewrite_links(body: str, skill_name: str, ext: str) -> str:
    """Repoint a skill body's relative links so they resolve from the adapter.

    A link inside an inline code span or a fenced code block is emitted unchanged,
    exactly as an anchor or an external URL already is. It renders as literal text
    rather than as a link, so it is a skill *showing* an example rather than making
    one, and repointing it rewrites what the body says instead of where it points:
    the kit reads one way and every generated adapter reads another (bug-0028).
    Nothing fails when that happens. The adapter renders, the run reports success,
    and the only reader who finds out is one following a documented example in
    another repository.

    The excluded ranges are computed once for the whole body rather than once per
    link, because `re.sub()` calls the replacement for every match and the natural
    placement inside `repl` would rescan the body each time. That is the note
    bug-0023 left when it made the same change in `broken_links()`.
    """
    spans = code_span_ranges(body) + fenced_block_ranges(body)

    def repl(m: re.Match) -> str:
        # LINK_RE here anchors on `](` rather than on the link text's opening bracket,
        # so `m.start()` is the bracket that closes the text. It falls inside the same
        # span or fence as the opening one for any link a span or fence contains, and
        # keying on it leaves a link whose *text* is a code span (which is how most
        # links in this kit are written) correctly rewritten.
        if any(start <= m.start() < end for start, end in spans):
            return m.group(0)  # rendered as literal text, so it is an example, not a link

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


def emit_rules_module(out: Path, dry: bool,
                      layout: Layout = LAYOUTS["cursor"]) -> list[Path]:
    """Place the rules module every emitted body shares. Returns what was written.

    Once per layout, which is what the module is: one copy shared by every skill,
    so that swapping it is one edit rather than one per skill. `layout` says where
    it lands for the requesting target; the rule it is treated by does not vary
    with the layout, only its destination.

    Once per layout is also what a real run has always produced, but it used to
    get there by accident. This loop ran once per skill and the second and later
    passes short-circuited on `dest.exists()`. A preview writes nothing, so that
    guard never became true and the preview counted the module once per skill: 74
    shared assets reported against the 17 a real run writes (bug-0025). Emitting
    it where it belongs removes the divergence instead of compensating for it, and
    matches what this docstring already claimed.

    A copy already in the target project is never overwritten (S-010, S-014). The
    module is swappable by design, so the project's own copy outranks the kit's.

    The module is copied and never passed through `rewrite_links()`, and that is a
    decision rather than an omission (bug-0044). A lens may link its sibling lenses,
    which sit beside it in every layout and therefore resolve everywhere unchanged.
    It may not link a skill: cursor and vscode share one Layout and one emitted copy
    of this module, while their adapters land at `.cursor/rules/<name>.mdc` and
    `.github/prompts/<name>.prompt.md` respectively, so no single rewritten target
    resolves for both, and a default run emits exactly one file that would have to
    serve them both. The lenses name skills in prose instead, which is the rule
    `autonomy.md` states about itself, and the walk in
    `TestEmittedRulesModuleResolves` is what keeps a link from creeping back in.
    """
    written = []
    if not RULES_DIR.is_dir():
        return written
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
    return written


def emit_skill_assets(skill_dir: Path, out: Path, dry: bool,
                      layout: Layout = LAYOUTS["cursor"]) -> list[Path]:
    """Place one skill's own supporting files. Returns what was written.

    Everything but the SKILL.md itself: the templates, references, and scripts an
    emitted body points at. Per skill, unlike the rules module beside it, and
    unconditionally: these are derived from the kit rather than adopted, so a
    re-run refreshes them (S-014).

    Byte-caches are excluded, by the same rule `install.py` filters them with
    (`_digestable`, and the ignore list `_copy` places with). A skill directory
    grows a `templates/__pycache__/` as soon as anything imports what is in it,
    which the test suite does, and the payload this places is meant to be a
    portable human-readable skill rather than one checkout's compiled bytecode
    (bug-0036). The directory half of the rule stands on its own: a future
    artefact inside `__pycache__` with some other suffix is still not part of the
    skill. Real `.py` files under `templates/`, such as the validator
    `init-worktracking` scaffolds, are unaffected and still emit.
    """
    written = []
    for src in sorted(skill_dir.rglob("*")):
        if not src.is_file() or src.name == "SKILL.md":
            continue
        rel = src.relative_to(skill_dir)
        if src.suffix == ".pyc" or "__pycache__" in rel.parts:
            continue
        dest = out / layout.assets_dir / skill_dir.name / rel
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


# Where each inlining target places a skill, as a function of the frontmatter `name`.
# One source of truth, because two callers need the same answer: the emitter that writes
# the file, and `_main`'s name refusal, which names a destination the rejected name would
# have produced (bug-0060). A refusal that reconstructed the path itself would drift into
# naming something this tool no longer emits, which is a confident citation pointing at
# nothing. `plugin` is absent deliberately rather than by oversight: it builds its
# destination from the source directory, so a `name` is never a path component there and
# there is no escaping path to show.
NAME_DESTINATIONS = {
    "cursor": lambda name, out: out / ".cursor" / "rules" / f"{name}.mdc",
    "vscode": lambda name, out: out / ".github" / "prompts" / f"{name}.prompt.md",
}


def emit_cursor(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    dest = NAME_DESTINATIONS["cursor"](name, out)
    content = (
        f"---\ndescription: {json.dumps(desc)}\nalwaysApply: false\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.mdc')}\n"
    )
    _write(dest, content, dry, out)
    return dest


def emit_vscode(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    dest = NAME_DESTINATIONS["vscode"](name, out)
    content = (
        f"---\nmode: agent\ndescription: {json.dumps(desc)}\n---\n\n"
        f"{BANNER.format(name=name)}\n\n{rewrite_links(body, name, '.prompt.md')}\n"
    )
    _write(dest, content, dry, out)
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
        _write(dest, json.dumps(obj, indent=2) + "\n", dry, out)
        written.append(dest)
    return written


def _write(dest: Path, content: str, dry: bool, root: Path):
    """Write `content` to `dest`, which must resolve inside `root`.

    The containment check sits here rather than in each emitter because this is the
    one place every emitted file passes through, so a target added later inherits it
    instead of restating it (bug-0060). It is needed because a skill's frontmatter
    `name` becomes a path component in both inlining emitters, and a `..` segment in
    one walks straight out of the output root: `_main` refuses such a name before it
    dispatches an emitter, and this is the boundary that holds whatever gets past
    that. `emit_plugin_manifests` passes destinations this module builds itself, so
    the check is silent there by construction.

    Both sides are resolved, because the escape is a `..` segment that exists only
    before resolution and `is_relative_to` on unresolved paths compares the spelling
    rather than the location. `root` is resolved again here even though `_main`
    already resolved it, so the guarantee belongs to this function rather than to its
    callers remembering.

    The check runs *before* the `dry` early return, deliberately. A preview that
    reports a destination the real run would refuse is misleading, and the adapters
    gate in `run-checks.py` is a `--dry-run`, so a check behind that branch would
    never fire in the one place this repository actually exercises the tool.
    """
    resolved = dest.resolve()
    root = root.resolve()
    if not resolved.is_relative_to(root):
        raise OutsideOutputRoot(resolved, root)
    if dry:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    # `newline=""` disables newline translation, so the bytes on disk are exactly the
    # newlines in `content` (LF) rather than the platform default, which is CRLF on
    # Windows. Emitted adapters are untracked, so nothing is broken today; the point is
    # that a writer whose line endings vary by platform is the shape that makes a
    # digest comparison answer differently on Windows than on Linux.
    dest.write_text(content, encoding="utf-8", newline="")


EMITTERS = {"cursor": emit_cursor, "vscode": emit_vscode, "plugin": emit_plugin}


def main(argv=None) -> int:
    """Entry point. `argv` defaults to sys.argv[1:]; pass a list to drive it in a test.

    Wraps the real entry point so an undecodable file anywhere in the tree is reported
    as a diagnosis naming the file rather than as a traceback naming this tool
    (chore-0081).
    """
    try:
        return _main(argv)
    except NotUTF8 as exc:
        # Exit 2, could not run, rather than 1. Nothing was compared or placed: a file this
        # tool must read is not readable, which is a different claim from "the change is bad"
        # and is the distinction install.py --check and check-provenance.py already draw.
        print(f"Cannot read a file this run needs: {exc}", file=sys.stderr)
        return 2
    except OutsideOutputRoot as exc:
        # The backstop for any write `_main` does not wrap with the skill it belongs to.
        # Exit 2 for the same reason as above: nothing was placed, so the report is
        # incomplete rather than the input bad. A traceback here would name this tool
        # instead of the path that was refused.
        #
        # It is unreachable today, and kept anyway. `emit_plugin_manifests` is the only
        # `_write` caller outside `_main`'s try, and it builds its destination from `out`
        # itself, so that call cannot escape and nothing else can raise past `_main`. Do
        # not write a test for this arm: it would be a test for dead code. It earns its
        # place when the next `_write` caller lands outside that try, which is exactly
        # when a traceback would otherwise reach a user.
        print(f"Refusing to write outside the output root: {exc.dest} is not under "
              f"{exc.root}.", file=sys.stderr)
        return 2


def _main(argv=None) -> int:
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
    # The rules module is one copy shared by every skill, so it is emitted per
    # layout and outside the per-skill loop. Inside it, a preview counted it once
    # per skill (bug-0025); see emit_rules_module().
    assets = sum(len(emit_rules_module(out, args.dry_run, layout))
                 for layout in layouts)
    for d in skills:
        fm, body = split_frontmatter(read_text_utf8(d / "SKILL.md"))
        name = fm.get("name", d.name)
        desc = fm.get("description", "")
        if name != d.name:
            # The rule validate-skills.py already states, borrowed rather than moved
            # (bug-0060). `name` becomes a path component in both inlining emitters,
            # so a name that is not the directory it came from is refused before any
            # emitter is dispatched, and a `..` in one never reaches a path at all.
            # Run-level rather than a skipped skill: goal 6 of the contract is to fail
            # clearly on an unusable invocation rather than write a partial result.
            #
            # The message names a destination and not only the root, because the root
            # alone leaves a reader unable to see that the name escapes at all, which is
            # the fact that carries the severity. It is one target's destination out of
            # however many were requested, so it is labelled representative rather than
            # offered as the only one, and it is read from NAME_DESTINATIONS rather than
            # rebuilt here. No emitter is dispatched to obtain it.
            shown = next((t for t in targets if t in NAME_DESTINATIONS), None)
            if shown is None:
                # A plugin-only run. Nothing requested derives a path from `name`, so
                # there is no destination to show and inventing one would be false.
                where = ("No requested target derives a destination from it, so nothing "
                         f"would leave the output root {out}")
            else:
                would_be = NAME_DESTINATIONS[shown](name, out).resolve()
                side = "inside" if would_be.is_relative_to(out) else "outside"
                where = (f"Representative, for target {shown!r}: {would_be}, {side} the "
                         f"output root {out}")
            print(f"{tag}Refusing to emit skill {d.name!r}: frontmatter name {name!r} "
                  f"!= directory {d.name!r}, and that name becomes a path component of "
                  f"every inlining target's destination. {where}. Fix the SKILL.md "
                  f"frontmatter; validate-skills.py states the same rule.")
            return 2
        for t in targets:
            try:
                dest = EMITTERS[t](d, name, desc, body, out, args.dry_run)
            except OutsideOutputRoot as exc:
                # The boundary at `_write` fired, so the name check above did not cover
                # this destination. Reported with the skill and the target, which are
                # known here and not there.
                print(f"{tag}Refusing to emit skill {d.name!r} for target {t!r}: "
                      f"destination {exc.dest} is outside the output root {exc.root}.")
                return 2
            print(f"{tag}{t:7} {name}  -> {dest.relative_to(out) if dest.is_relative_to(out) else dest}")
            n += 1
        # The emitted bodies point at these; without them the links dangle.
        for layout in layouts:
            assets += len(emit_skill_assets(d, out, args.dry_run, layout))

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
