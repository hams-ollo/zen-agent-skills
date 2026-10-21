"""Shared constants and helpers for the rank 9 evaluation slice.

Every path a run touches is under the scratch directory named by EVAL_SCRATCH. Nothing here
writes under the user's home configuration directory, and nothing here reads or copies a
credential: the child CLI authenticates from its own store, untouched.
"""
import hashlib
import json
import os
import pathlib
import subprocess

HARNESS = pathlib.Path(__file__).resolve().parent
RANK9 = HARNESS.parent
REPO = RANK9.parents[1]
FIXTURES = RANK9 / "fixtures"
RESULTS = RANK9 / "results"

# The refresh under test is PR #91. PRE is developer before it, POST is developer after it and
# after the quest-tracker PRs, which is the base this slice was cut from.
PRE_REV = "ec1c1b3ced7cd67144485c2bc89125d4a8b8d6a4"
POST_REV = "66b16e124b688905142fd10eb0ca81203378a509"

MODELS = {
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}

# Tools no run needs, removed so a run cannot reach the network, a person, or a schedule.
# The Bash patterns are deny rules, so they hold under bypassPermissions too.
DISALLOWED_TOOLS = [
    "WebFetch", "WebSearch", "PowerShell", "AskUserQuestion", "RemoteTrigger", "CronCreate",
    "PushNotification",
    "Bash(gh *)", "Bash(git push *)", "Bash(curl *)", "Bash(wget *)",
    "Bash(pip install *)", "Bash(npm *)",
]

FIXED_GIT_DATE = "2026-10-01T09:00:00+00:00"


def scratch_root():
    """The scratch base for run directories. Required, so a run never defaults into the repo."""
    value = os.environ.get("EVAL_SCRATCH")
    if not value:
        raise SystemExit("set EVAL_SCRATCH to a scratch directory outside the repository")
    root = pathlib.Path(value).resolve()
    if REPO in root.parents or root == REPO:
        raise SystemExit("EVAL_SCRATCH must be outside the repository")
    root.mkdir(parents=True, exist_ok=True)
    return root


def claude_exe():
    """The CLI under test: the desktop app's bundled build when present, else `claude` on PATH."""
    return os.environ.get("EVAL_CLAUDE") or os.environ.get("CLAUDE_CODE_EXECPATH") or "claude"


def child_env(scratch):
    """Environment for a child run, detached from the host session.

    Every CLAUDE* and ANTHROPIC* variable is dropped, so the child carries no host session id,
    messaging socket, effort override, or attended flag; it authenticates from the CLI's own
    credential store. gh gets an empty config directory, so it has no account to act as.
    """
    env = {k: v for k, v in os.environ.items()
           if not (k.upper().startswith("CLAUDE") or k.upper().startswith("ANTHROPIC"))}
    no_gh = pathlib.Path(scratch) / ".no-gh"
    no_gh.mkdir(parents=True, exist_ok=True)
    env["GH_CONFIG_DIR"] = str(no_gh)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def git(cwd, *args, check=True, env_extra=None):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "Fixture Author", "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_NAME": "Fixture Author", "GIT_COMMITTER_EMAIL": "fixture@example.com",
        "GIT_AUTHOR_DATE": FIXED_GIT_DATE, "GIT_COMMITTER_DATE": FIXED_GIT_DATE,
    })
    if env_extra:
        env.update(env_extra)
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=check, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def repo_git(*args):
    """git against this repository, for reading pinned revisions."""
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def snapshot(root, skip=(".git", "__pycache__", ".claude")):
    """Map every file under root (relative, forward slashes) to its sha256."""
    root = pathlib.Path(root)
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in skip for part in rel.parts) or not p.is_file():
            continue
        out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def diff_snapshots(before, after):
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "modified": sorted(k for k in set(before) & set(after) if before[k] != after[k]),
    }


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
