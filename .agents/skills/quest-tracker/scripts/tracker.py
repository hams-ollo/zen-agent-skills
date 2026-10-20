#!/usr/bin/env python3
"""tracker.py: the deterministic parts of the quest-tracker skill.

    python tracker.py fill --block BLOCK.js --title "Sourdough season" --out tracker.html
    python tracker.py fill --from OLD.html --out tracker.html
    python tracker.py check tracker.html
    python tracker.py claim --step p2-check --agent go-live --lines 0,1 --command "npm test"

`fill` writes a tracker from the bundled template: the data block it is given goes between the
template's markers, the page title goes on the first line, and nothing else changes. With `--from`
it carries an existing tracker's data block onto the bundled template instead, which is how a
tracker is brought onto newer code. Either way `templateVersion` is set to the template's, because
that field names the code below the block, never the project.

`check` reports what is wrong with a tracker's data block before anyone sees it: the page's own
`dataIssues` (run under Node.js, read from the bundled template so an older page is checked by the
current rules), plus what only a comparison with the template can show: a `storageKey` or a title
still the template's, a `templateVersion` that does not name the code, and code edited below the
end marker.

`claim` runs the command that checks a step, and builds the claim document from what it printed:
the command exactly as given, the verbatim tail of its output ending with the exit status, and the
time read from this machine's clock in UTC. It refuses when the command fails, because a claim says
the check passed, and when any field looks like a secret, because the page would hide it anyway.

Standard library only, so it runs on a bare Python 3 wherever the skill is installed. Node.js is
needed by `check` alone, and its absence is reported rather than passed over.

Exit status: 0 done or clean, 1 refused or issues found, 2 could not run.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "quest-tracker.html"

START_MARK = "DATA BLOCK: the only part to edit"
END_LINE = "/* ========================= END OF DATA BLOCK ========================= */"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
VERSION_RE = re.compile(r'(templateVersion:\s*")([^"]*)(")')
STORAGE_RE = re.compile(r'storageKey:\s*"([^"]*)"')

# The page's `looksSecret`, ported. Kept pattern-for-pattern identical to the template, and
# `tests/test_quest_tracker.py` fails when the two lists differ, so a claim this refuses is exactly
# a claim the page would hide.
SECRET_PATTERNS = [
    (r"pass(word)?\s*[:=]|pwd\s*[:=]|api[_ -]?key\s*[:=]|secret\s*[:=]|token\s*[:=]|recovery code|backup code", re.I),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    (r"\b(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{16,}", 0),
    (r"\bAIza[0-9A-Za-z_-]{20,}", 0),
    (r"\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{12,}", 0),
    (r"\bsk-[A-Za-z0-9_-]{20,}", 0),
]


class Unusable(Exception):
    """The input cannot be worked on at all: exit 2, not a finding."""


def looks_secret(text: str) -> bool:
    return bool(text) and any(re.search(p, text, f) for p, f in SECRET_PATTERNS)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Unusable(f"cannot read {path}: {exc}") from None


def write_new(path: Path, text: str, force: bool) -> None:
    """Write `path`, refusing to replace a file that is already there unless told to."""
    if path.exists() and not force:
        raise Unusable(f"{path} already exists; pass --force to replace it, or choose another --out")
    with open(path, "w", encoding="utf-8", newline="") as fh:   # LF stays LF on Windows
        fh.write(text)


def block_bounds(page: str) -> tuple[int, int]:
    """Where the editable data block starts and ends: after the marker comment, before the end line."""
    starts = [m.start() for m in re.finditer(re.escape(START_MARK), page)]
    ends = [m.start() for m in re.finditer(re.escape(END_LINE), page)]
    if len(starts) != 1 or len(ends) != 1:
        raise Unusable(f"expected one data block start marker and one end line, found "
                       f"{len(starts)} and {len(ends)}")
    close = page.find("*/", starts[0])
    if close < 0 or close > ends[0]:
        raise Unusable("the data block's opening comment is not closed before the end line")
    return close + 2, ends[0]


def data_block(page: str) -> str:
    lo, hi = block_bounds(page)
    return page[lo:hi].strip("\n")


def template_version(text: str) -> str | None:
    m = VERSION_RE.search(text)
    return m.group(2) if m else None


def set_version(block: str, version: str) -> str:
    """Point `templateVersion` at `version`, adding the field to a block that predates it."""
    if VERSION_RE.search(block):
        return VERSION_RE.sub(lambda m: m.group(1) + version + m.group(3), block, count=1)
    m = re.search(r"const TRACKER = \{\n", block)
    if not m:
        raise Unusable("the data block has no `const TRACKER = {` line to add templateVersion to")
    return block[:m.end()] + f'  templateVersion: "{version}",\n' + block[m.end():]


def splice(template: str, block: str, title: str) -> str:
    lo, hi = block_bounds(template)
    page = template[:lo] + "\n\n" + block.strip("\n") + "\n" + template[hi:]
    if not TITLE_RE.search(page):
        raise Unusable("the template has no <title>")
    return TITLE_RE.sub(lambda _: "<title>" + title + "</title>", page, count=1)


def cmd_fill(args) -> int:
    template = read(Path(args.template))
    version = template_version(data_block(template))
    if not version:
        raise Unusable(f"{args.template} has no templateVersion in its data block")
    if args.from_:
        old = read(Path(args.from_))
        block = data_block(old)
        m = TITLE_RE.search(old)
        title = args.title or (m.group(1).strip() if m else "")
    else:
        block = read(Path(args.block)).lstrip("﻿")   # read_text has already made CRLF into LF
        if START_MARK in block or END_LINE in block:
            raise Unusable("--block holds the data block markers; give only the code between them")
        title = args.title or ""
    if not title.strip() or "<" in title:
        raise Unusable("give the page a --title: two to four words naming the tracker, no markup")
    was = template_version(block)
    page = splice(template, set_version(block, version), title.strip())
    write_new(Path(args.out), page, args.force)
    print(f"wrote {args.out}: template {version}, title \"{title.strip()}\", "
          f"data block {len(block.splitlines())} lines"
          + (f", templateVersion {was} -> {version}" if was != version else ""))
    if args.from_:
        print("The template's own sample `rules` and `reference` entries are not merged: compare "
              "them by hand with the tracker's.")
    print(f"Next: python {Path(__file__).name} check {args.out}")
    return 0


def outside_block(page: str) -> str:
    """Everything but the data block and the title, so two pages' code can be compared."""
    lo, hi = block_bounds(page)
    return TITLE_RE.sub("<title></title>", page[:lo], count=1) + page[hi:]


def function_source(code: str, name: str) -> str:
    """`function name(...) {...}`, by matching braces. The function it is used on holds none in strings."""
    start = code.find(f"function {name}(")
    if start < 0:
        raise Unusable(f"the bundled template has no function {name}")
    depth, i = 0, code.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(code[i], 0)
        if depth == 0:
            return code[start:i + 1]
        i += 1


def evaluate(block: str, checker: str) -> dict:
    node = shutil.which("node")
    if not node:
        raise Unusable("no `node` on PATH, so the data block cannot be checked here. Open the "
                       "published page and read its \"Data block check\" box before handing it over.")
    program = (block + "\n" + checker + "\nprocess.stdout.write(JSON.stringify({issues: dataIssues(TRACKER), "
               "storageKey: TRACKER.storageKey || null}));\n")
    run = subprocess.run([node, "-e", program], capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        err = (run.stderr.strip().splitlines() or ["(no message)"])
        raise Unusable("the data block does not run as JavaScript: " + next(
            (line for line in err if "Error" in line), err[-1]))
    return json.loads(run.stdout)


def cmd_check(args) -> int:
    page, template = read(Path(args.tracker)), read(Path(args.template))
    block, t_block = data_block(page), data_block(template)
    result = evaluate(block, function_source(template, "dataIssues"))
    issues, notices = list(result["issues"]), []
    t_version, version = template_version(t_block), template_version(block)
    if result["storageKey"] and result["storageKey"] == STORAGE_RE.search(t_block).group(1):
        issues.append(f"`storageKey` is still the template's (`{result['storageKey']}`): give this "
                      f"project its own, so viewers' remembered filters do not mix.")
    title, t_title = TITLE_RE.search(page), TITLE_RE.search(template)
    if not title or not title.group(1).strip() or title.group(1) == t_title.group(1):
        issues.append("The page's <title> is missing or still the template's: name the tracker.")
    same_code = outside_block(page) == outside_block(template)
    if version == t_version and not same_code:
        issues.append(f"The page says template {version} but its code differs from that template's "
                      f"outside the data block: something below the end marker was edited.")
    elif version != t_version and same_code:
        issues.append(f"`templateVersion` says {version} but the code is template {t_version}'s: "
                      f"leave it as copied.")
    elif version != t_version:
        notices.append(f"This page is on template {version}; the bundled template is {t_version}. "
                       f"`fill --from` carries its data block across.")
    for line in issues:
        print("issue:  " + line)
    for line in notices:
        print("notice: " + line)
    print(f"{len(issues)} issue(s) in {args.tracker}" + ("" if issues else ": ready to publish"))
    return 1 if issues else 0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_lines(text: str) -> list[int]:
    if not text.strip():
        return []
    try:
        lines = sorted({int(x) for x in text.split(",") if x.strip()})
    except ValueError:
        raise Unusable(f"--lines takes positions counted from 0, separated by commas, not {text!r}") from None
    if any(i < 0 for i in lines):
        raise Unusable("--lines are positions counted from 0, so none can be negative")
    return lines


def cmd_claim(args) -> int:
    lines = parse_lines(args.lines)
    if args.tail < 1:
        raise Unusable("--tail keeps at least one line of output")
    if not args.command.strip():
        raise Unusable("--command is empty: a claim names the command that checked the step")
    try:
        run = subprocess.run(args.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"refused: the command ran past {args.timeout} seconds, so nothing was checked")
        return 1
    output = run.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").rstrip()
    tail = "\n".join(output.splitlines()[-args.tail:]) if output else "(no output)"
    result = f"{tail}\nexit status {run.returncode}"
    if run.returncode != 0:
        print(f"refused: the command failed, so there is nothing to claim. Log a note instead.\n{result}")
        return 1
    document = {"agent": args.agent.strip(), "at": utc_now(), "lines": lines,
                "command": args.command, "result": result, "note": args.note}
    if not document["agent"]:
        raise Unusable("--agent is empty: a claim names the session that makes it")
    hits = [k for k in ("agent", "command", "result", "note") if looks_secret(document[k])]
    if hits:
        print(f"refused: the claim's {', '.join(hits)} looks like it holds a password, code or key, "
              f"and the page would hide it. Trim the output with --tail or rephrase, then run again.")
        return 1
    print(json.dumps({"collection": "claims", "doc_id": args.step, "document": document}, indent=2,
                     ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    fill = sub.add_parser("fill", help="write a tracker from the bundled template")
    src = fill.add_mutually_exclusive_group(required=True)
    src.add_argument("--block", help="a file holding the code between the data block markers")
    src.add_argument("--from", dest="from_", help="an existing tracker page, to carry onto the template")
    fill.add_argument("--title", help="the page's <title>; with --from, defaults to the old page's")
    fill.add_argument("--out", required=True, help="where to write the tracker page")
    fill.add_argument("--force", action="store_true", help="replace --out if it exists")
    fill.add_argument("--template", default=str(TEMPLATE), help=argparse.SUPPRESS)
    fill.set_defaults(run=cmd_fill)

    check = sub.add_parser("check", help="check a tracker page's data block before publishing")
    check.add_argument("tracker")
    check.add_argument("--template", default=str(TEMPLATE), help=argparse.SUPPRESS)
    check.set_defaults(run=cmd_check)

    claim = sub.add_parser("claim", help="run a step's check and build the claim document")
    claim.add_argument("--step", required=True, help="the step id the claim is for")
    claim.add_argument("--agent", required=True, help="the name this session reports under")
    claim.add_argument("--command", required=True, help="the command that checks the step, as typed")
    claim.add_argument("--lines", default="", help="line positions done, counted from 0: 0,1,2")
    claim.add_argument("--note", default="", help="what the person checking needs that the result does not say")
    claim.add_argument("--tail", type=int, default=20, help="how many output lines to keep (default 20)")
    claim.add_argument("--timeout", type=int, default=600, help="seconds before giving up (default 600)")
    claim.set_defaults(run=cmd_claim)

    args = ap.parse_args(argv)
    # Step titles and claims carry text a Windows console code page cannot encode, and a crash
    # half-way through printing a claim is worse than an odd glyph on a console.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        return args.run(args)
    except Unusable as exc:
        print(f"could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
