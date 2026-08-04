#!/usr/bin/env python3
"""Validate the .tasks/ backlog.

Ships with the init-worktracking scaffold. Checks the mechanical integrity a
multi-agent workflow depends on: every task file has a well-formed frontmatter,
ids are unique and match their filenames, every depends_on resolves to a real
task, every relative markdown link resolves from where the file actually lives,
and (with --strict) every touched_files path exists.

Standard library only, so it runs anywhere a bare Python 3 does. Exits non-zero
on any error, so it drops cleanly into CI or a pre-commit hook.

    python .tasks/validate.py            # errors fail, missing files warn
    python .tasks/validate.py --strict   # warnings become errors too
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
# target. Deliberately identical to the regex the docs link step in
# .github/workflows/checks.yml applies, so the two checks cannot disagree about
# what counts as a link. It ignores a bare closing fragment, which is how prose
# that describes a link escapes being treated as one.
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:")


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
    """
    found = []
    for match in LINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1).split("#")[0].strip()
        if not target or target.startswith(LINK_SKIP_PREFIXES):
            continue
        if not (path.parent / target).exists():
            found.append(target)
    return found


def main(argv=None) -> int:
    # `argv` is injectable so the CLI layer is reachable from a test, matching
    # validate-skills.py, build-adapters.py, and install.py (chore-0017). Calling
    # main() with no argument behaves exactly as before.
    args = sys.argv[1:] if argv is None else list(argv)
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
