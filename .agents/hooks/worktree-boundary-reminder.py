#!/usr/bin/env python3
"""Reminder hook: a shell command in a worktree named a path outside it.

Fires on PostToolUse when a shell tool (`Bash`, `PowerShell`, or a harness's equivalent)
runs inside a **linked** git worktree, and the command both looks like it writes (a
redirect, or a verb such as `cp`, `mv`, `rm`, `Copy-Item`, `Set-Content`) and names an
absolute path outside that worktree. Emits one reminder naming the paths, then exits. It
never blocks.

Why a reminder and not a gate
-----------------------------
Which files a shell command writes is not decidable from its text: a variable, a script,
a `cd`, or a quoted string defeats any parser, so a gate would both miss real writes and
refuse harmless ones. The question a careful person could disagree with the hook about is
exactly the one it would have to decide, which by the module contract makes it a reminder.

Why it exists at all
--------------------
Claude Code's own worktree checks refuse an Edit, Write, or NotebookEdit into the main
checkout, and say in their documentation that none of them "tracks which files a shell
command writes", that a PowerShell command gets only the working-directory check, and that
the sandbox which would bound shell writes does not run on native Windows. The kit's
autonomy module states the rule (`A1`: stay inside your workspace) and records the
incident behind it: an agent in an isolated worktree used a shell to overwrite a file in
the main checkout with a stale copy. The 2026-10 kit refresh audit found nothing that
reminds an agent of the rule at the moment it matters.

Silent outside a linked worktree, because `A1` is about an assigned workspace and an
ordinary checkout has none: there, writing to an absolute path elsewhere is normal work.
Paths under the system temporary directory are ignored, since harnesses hand agents a
scratch directory there.

Contract
--------
stdin   a JSON object with `hook_event_name`, `tool_name`, `tool_input.command`, `cwd`
stdout  one JSON object, or nothing
exit    always 0
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SHELL_TOOLS = {
    "Bash",          # Claude Code
    "PowerShell",    # Claude Code on Windows
    "bash",          # opencode
    "shell",         # Codex
    "local_shell",   # Codex
    "exec_command",  # Codex
}

# A command "looks like it writes" when it carries an output redirect or one of these
# verbs. Deliberately broad: the cost of a false positive is one paragraph of context.
WRITE_VERB_RE = re.compile(
    r"(?<![\w-])(?:cp|mv|rm|rmdir|tee|touch|mkdir|ln|rsync|install|truncate|dd|"
    r"sed\s+-i|perl\s+-i|copy-item|move-item|remove-item|rename-item|new-item|"
    r"set-content|add-content|out-file|clear-content)(?![\w-])",
    re.IGNORECASE,
)
REDIRECT_RE = re.compile(r"(?<![<>&\d])>>?(?!&)")

# Absolute path tokens in three spellings: Windows (`C:\x` or `C:/x`), POSIX (`/x/y`), and
# home-relative (`~/x`). Quotes and shell punctuation end a token. The lookbehinds keep a URL
# out: without them the `s:/` in `https://` reads as a drive and `//host/path` as a root path.
PATH_RE = re.compile(
    r"""(?:(?<![A-Za-z])[A-Za-z]:[\\/]|~[\\/]|(?<![\w.~:/])/)[^\s"'`|;&<>()]*""")

REMINDER = (
    "WORKTREE BOUNDARY: this session is in the linked worktree {root}, and the shell command "
    "that just ran looks like it writes and names a path outside it: {paths}. Worktree "
    "isolation does not track which files a shell command writes; Claude Code refuses an "
    "Edit or Write into the main checkout, not a cp, a mv, or a redirect. If this command "
    "wrote outside the worktree, say so in your report and do not repeat it. Needing to "
    "reach outside your workspace is a blocker to report, not a step to take."
)


def _worktree_root(cwd: str):
    """The root of the linked worktree containing `cwd`, or None.

    A linked worktree's `.git` is a file pointing at the main repository; the main
    checkout's `.git` is a directory. Only the first case is a sandbox this hook guards.
    """
    try:
        here = Path(cwd).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    for directory in (here, *here.parents):
        marker = directory / ".git"
        try:
            if marker.is_file():
                return directory
            if marker.is_dir():
                return None
        except OSError:
            return None
    return None


def _normalize(token: str):
    """An absolute Path for a path token, or None when it cannot be read as one."""
    token = token.rstrip(".,:")
    if not token:
        return None
    if token.startswith(("~/", "~\\")):
        token = str(Path.home()) + token[1:]
    # Git Bash spells `C:\Users` as `/c/Users`.
    match = re.match(r"^/([A-Za-z])(/.*)?$", token)
    if match and os.name == "nt":
        token = f"{match.group(1)}:{match.group(2) or '/'}"
    try:
        return Path(token).resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _ignored(token: str, path: Path) -> bool:
    """Paths no workspace rule is about: device files and the system temp directory.

    The device check reads the token as written, because on Windows `/dev/null` resolves
    to a path on the current drive and would no longer look like a device.
    """
    if token.lower().startswith("/dev/"):
        return True
    try:
        temp = Path(tempfile.gettempdir()).resolve()
    except (OSError, RuntimeError):
        return False
    return _is_inside(path, temp)


def outside_paths(command: str, root: Path):
    """Absolute paths named in a write-shaped `command` that resolve outside `root`."""
    if not (WRITE_VERB_RE.search(command) or REDIRECT_RE.search(command)):
        return []
    found = []
    for token in PATH_RE.findall(command):
        path = _normalize(token)
        if path is None or _ignored(token, path) or _is_inside(path, root):
            continue
        if str(path) not in found:
            found.append(str(path))
    return found


def evaluate(payload):
    """Return the hook's output object for this payload, or None to stay silent."""
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "PostToolUse":
        return None
    if payload.get("tool_name") not in SHELL_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    cwd = payload.get("cwd")
    if not isinstance(command, str) or not isinstance(cwd, str):
        return None
    root = _worktree_root(cwd)
    if root is None:
        return None
    paths = outside_paths(command, root)
    if not paths:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER.format(root=root, paths=", ".join(paths)),
        }
    }


def main(stdin=None, stdout=None) -> int:
    """Read one payload, emit at most one object. `stdin`/`stdout` are injectable so the
    behavior is reachable from a test without a subprocess."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.load(stdin)
    except Exception:
        return 0
    try:
        out = evaluate(payload)
        if out is not None:
            stdout.write(json.dumps(out))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
