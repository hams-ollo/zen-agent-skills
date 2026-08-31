#!/usr/bin/env python3
"""Gate hook: a contract may not close without an audit against it.

Fires on PostToolUse after a file edit. Blocks when work that a contract governs is being
closed and no conformance matrix records whether the implementation actually matches that
contract. Green tests are not sufficient: they assert code contracts, not spec conformance.

Two closing shapes, one rule
----------------------------
The rule is "nothing closes unaudited". What *closing* looks like differs by repository,
so the gate recognises two shapes and blocks on either:

  A. A spec file reaches a terminal status (`shipped`, `done`, `verified`, ...) with no
     conformance sibling. This is the portable shape, for repositories whose specs carry a
     closing status.

  B. A task file carrying a `spec:` reference is set to `status: done` while that spec has
     no conformance sibling. This is the shape this kit actually uses, and without it the
     gate would be inert here: this repository's spec lifecycle is `draft` -> `approved`
     and stops, so no spec ever reaches a terminal status. A guardrail that cannot fire in
     the repository that ships it is one nobody has ever seen work.

`approved` is deliberately NOT terminal
---------------------------------------
Upstream's terminal set includes `approved`. Here `approved` means the opposite end of the
lifecycle: a human has signed off on the contract so decomposition may begin, which is the
gate `spec-author` and `new-task` enforce between them. Every spec in this repository is
`approved`. Treating it as closing would block the next edit to all of them and demand a
matrix for work not yet written, so the hook would be uninstalled within the hour and the
idea discredited by its own first run. There is a test pinning this, because the removal
looks like an oversight to anyone reading this file against upstream.

The escape
----------
Every block names one: add a `conformance:` key to the frontmatter to declare the audit
recorded elsewhere. That is a written claim rather than a silent bypass, which is the
difference between a gate and a trap.

Contract
--------
stdin   a JSON object with `hook_event_name`, `tool_name`, and `tool_input`
stdout  one JSON object, or nothing
exit    always 0

Adapted from `spec-conformance-gate.py` in RepoPrompt Workflows by Balarama Bosch (MIT),
https://github.com/moonray/repoprompt-workflows. Shape B, the `approved` removal, and the
repository-root resolution are this kit's.

Provenance
----------
source: https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/hooks/spec-conformance-gate.py
author: Balarama Bosch
license: MIT
retrieved: 2026-08-06
sha256: 55a654f4f1e223bcef89803b0832e114f28406604674df9f3196b04f2fcfa6fb
note: backfilled baseline (feat-0043). The snapshot this file was adapted from is gone, so the digest pins upstream as of the retrieved date, not the exact bytes adapted.
"""
import json
import os
import re
import sys

# Statuses that mean "this is finished". `approved` is excluded on purpose; see the
# module docstring. Kept broad because an adopting repository picks its own vocabulary.
TERMINAL_STATUSES = {
    "implemented", "shipped", "done", "closed", "complete", "completed",
    "resolved", "final", "released", "verified",
}

# Frontmatter `type` values that mark a document as a contract even when its path does not.
SPEC_TYPES = {"spec", "specification", "contract", "feature-spec", "featurespec"}

# Frontmatter keys that declare the audit exists somewhere this hook cannot see.
CONFORMANCE_KEYS = ("conformance", "conformed", "audited", "conformance_matrix")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Codex and opencode deliver edits as an apply_patch command with no path field.
_PATCH_FILE_RE = re.compile(r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s*(.+?)\s*$", re.MULTILINE)


def _paths_from_payload(payload):
    """Every edited path in this payload, across the harnesses' differing shapes."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    paths = []
    for key in ("file_path", "path", "filePath", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    command = tool_input.get("command")
    if isinstance(command, str):
        paths.extend(_PATCH_FILE_RE.findall(command))
    return paths


def _frontmatter(text):
    """The document's frontmatter as a lowercased flat dict. Deliberately not a YAML parser.

    Only scalar `key: value` lines are read, which is all any rule here needs. A real
    parser would be a dependency, and this file is standard library only.
    """
    match = _FRONTMATTER_RE.match(text or "")
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-", "#")):
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip().strip('"').strip("'")
    return fields


def _read_head(path, limit=4000):
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.read(limit)
    except OSError:
        return None


def _is_spec_path(path):
    normalized = path.replace("\\", "/")
    return (re.search(r"(^|/)(spec|specs|specifications)(/|$)", normalized) is not None
            or normalized.endswith(".spec.md"))


def _stem(path):
    base = os.path.basename(path)
    if base.endswith(".spec.md"):
        return base[:-8]
    if base.endswith(".md"):
        return base[:-3]
    return base


def _matrix_present(spec_path, fields):
    """True when an audit of this spec is recorded, by sibling file or by declaration."""
    for key in CONFORMANCE_KEYS:
        if fields.get(key):
            return True
    directory = os.path.dirname(spec_path) or "."
    if not os.path.isdir(directory):
        return False
    prefix = (_stem(spec_path) + ".conformance").lower()
    return any(name.lower().startswith(prefix) for name in os.listdir(directory))


def _repo_root(path, cwd):
    """Best effort repository root, for resolving a task's repo-relative `spec:` value.

    The payload's cwd is trusted first. Otherwise walk up from the edited file looking for
    a marker, which handles a task edited from somewhere else in the tree.
    """
    if cwd and os.path.isdir(cwd):
        return cwd
    current = os.path.dirname(os.path.abspath(path))
    while True:
        if any(os.path.exists(os.path.join(current, m)) for m in (".git", "AGENTS.md", ".tasks")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.dirname(os.path.abspath(path))
        current = parent


def _within(root, candidate):
    """True when `candidate` lands inside `root`, so a `spec:` value cannot escape it.

    `os.path.join` is not a containment operator: an absolute second argument discards the
    first outright, and a `../` chain walks out of it. The `spec:` value is ordinary
    frontmatter, so nothing upstream of here bounds it. Compared with `normcase` because
    Windows paths differ in case without differing in identity, and `abspath` rather than
    `realpath` because the question is which tree the reference names, not where a symlink
    inside that tree happens to point.
    """
    try:
        root = os.path.normcase(os.path.abspath(root))
        candidate = os.path.normcase(os.path.abspath(candidate))
    except (OSError, ValueError):
        return False
    # `join(root, "")` rather than `root + os.sep`, so a root that already ends in a
    # separator (a checkout at a drive root) does not get a doubled one and reject
    # every path inside itself.
    return candidate == root or candidate.startswith(os.path.join(root, ""))


def _block(reason):
    return {"decision": "block", "reason": reason}


def _evaluate_spec_close(path, fields):
    """Shape A: a spec file reaching a terminal status with no matrix."""
    if not (_is_spec_path(path) or fields.get("type", "").lower() in SPEC_TYPES):
        return None
    if fields.get("status", "").lower() not in TERMINAL_STATUSES:
        return None
    if _matrix_present(path, fields):
        return None
    name = os.path.basename(path)
    return _block(
        f"Spec-closeout gate: '{name}' is marked status='{fields.get('status')}' but has no "
        f"conformance matrix. Run the spec-conformance skill on it to produce "
        f"{_stem(path)}.conformance.md, or add a frontmatter 'conformance:' key naming where "
        f"the audit lives. Green tests are not sufficient: they assert code contracts, not "
        f"conformance to this spec."
    )


def _evaluate_task_close(path, fields, cwd):
    """Shape B: a task claiming a spec being closed while that spec has no matrix."""
    if fields.get("status", "").lower() != "done":
        return None
    spec_ref = fields.get("spec", "")
    if not spec_ref:
        return None
    if any(fields.get(key) for key in CONFORMANCE_KEYS):
        return None
    root = _repo_root(path, cwd)
    spec_path = os.path.join(root, spec_ref.replace("\\", "/"))
    if not _within(root, spec_path) or not os.path.isfile(spec_path):
        # Either the reference points outside the repository, or it does not resolve. Both
        # are task-file defects for the validator to report, not conformance questions, and
        # blocking on one would be this hook answering a question it was not asked. Reading
        # the head of a file the repository does not own is the part worth refusing: the
        # impact is nil today because nothing here emits what it read, and the bound costs
        # one condition and removes the question (chore-0038).
        return None
    spec_fields = _frontmatter(_read_head(spec_path) or "")
    if _matrix_present(spec_path, spec_fields):
        return None
    return _block(
        f"Spec-closeout gate: '{os.path.basename(path)}' is being closed (status=done) and "
        f"claims spec '{spec_ref}', which has no conformance matrix. Run the spec-conformance "
        f"skill on that spec to produce {_stem(spec_path)}.conformance.md, or add a frontmatter "
        f"'conformance:' key to this task naming where the audit lives. Closing the work that "
        f"implements a contract without auditing against it is how four specs in this "
        f"repository went unaudited for months."
    )


def evaluate(payload):
    """Return a block object for this payload, or None to stay silent."""
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "PostToolUse":
        return None
    cwd = payload.get("cwd")
    for path in _paths_from_payload(payload):
        if not path or not os.path.isfile(path):
            continue
        head = _read_head(path)
        if head is None:
            continue
        fields = _frontmatter(head)
        if not fields:
            continue
        for check in (_evaluate_spec_close(path, fields),
                      _evaluate_task_close(path, fields, cwd)):
            if check:
                return check
    return None


def main(stdin=None, stdout=None) -> int:
    """Read one payload, emit at most one object. Streams are injectable for testing."""
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
        # A guardrail that breaks a session because it could not read a file is worse than
        # no guardrail. Fail open, always.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
