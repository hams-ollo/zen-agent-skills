#!/usr/bin/env python3
"""Install the Zen Starter Kit skills into your AI tools' discovery directories.

Idempotent and safe to re-run. Previews with --dry-run, reverses with
--uninstall. Never clobbers a real file it did not create: such a target is
reported CONFLICT and skipped for you to resolve.

    python scripts/install.py --dry-run          # preview
    python scripts/install.py                     # install (copy on Windows, symlink on POSIX)
    python scripts/install.py --mode symlink      # force symlinks
    python scripts/install.py --tools claude      # only Claude Code
    python scripts/install.py --uninstall         # remove what this installed

Discovery targets (per tool), each skill linked/copied as <base>/<skill-name>:
    claude    -> ~/.claude/skills
    opencode  -> ~/.agents/skills

Cursor and Copilot read repo-level pointer files, not a global skills dir, so
they are handled by build-adapters.py per project, not here.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
MANIFEST = REPO_ROOT / "scripts" / ".install-manifest.json"

TOOL_SUBPATHS = {
    "claude": Path(".claude") / "skills",
    "opencode": Path(".agents") / "skills",
}


def discover_skills():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def load_manifest():
    if MANIFEST.is_file():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"entries": []}
    return {"entries": []}


def save_manifest(entries, dry):
    if dry:
        return
    MANIFEST.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")


def is_managed(target: Path, manifest) -> bool:
    tp = str(target)
    return any(e["target"] == tp for e in manifest["entries"])


def install(tools, mode, home: Path, dry: bool) -> int:
    skills = discover_skills()
    if not skills:
        print(f"No skills found under {SKILLS_DIR}.")
        return 0

    manifest = load_manifest()
    entries = {e["target"]: e for e in manifest["entries"]}
    conflicts = 0
    tag = "[dry-run] " if dry else ""

    for tool in tools:
        base = home / TOOL_SUBPATHS[tool]
        if not dry:
            base.mkdir(parents=True, exist_ok=True)
        for src in skills:
            target = base / src.name
            status = _place(src, target, mode, dry, manifest)
            if status == "CONFLICT":
                conflicts += 1
            else:
                entries[str(target)] = {
                    "tool": tool, "name": src.name,
                    "target": str(target), "mode": mode, "source": str(src),
                }
            print(f"{tag}{status:9} {tool:8} {src.name}  -> {target}")

    save_manifest(list(entries.values()), dry)
    if conflicts:
        print(f"\n{conflicts} CONFLICT(s): a real file exists at those targets. "
              f"Move or remove them, then re-run.")
    print(f"\n{tag}Done: {len(skills)} skill(s) x {len(tools)} tool(s).")
    return 1 if conflicts else 0


def _place(src: Path, target: Path, mode: str, dry: bool, manifest) -> str:
    """Create one link/copy at target. Returns a status word."""
    if target.is_symlink():
        try:
            points_to = target.resolve()
        except OSError:
            points_to = None
        if mode == "symlink":
            if points_to == src.resolve():
                return "ok"
            if not dry:
                target.unlink()
                _link(src, target)
            return "relinked"
        # copy mode but a symlink is there: ours only if it points into our repo
        if points_to and str(points_to).startswith(str(src.resolve())):
            if not dry:
                target.unlink()
                _copy(src, target)
            return "updated"
        return "CONFLICT"

    if target.exists():
        if is_managed(target, manifest):
            if mode == "copy":
                if not dry:
                    _rm(target)
                    _copy(src, target)
                return "updated"
            if not dry:
                _rm(target)
                _link(src, target)
            return "relinked"
        return "CONFLICT"

    # nothing there
    if not dry:
        if mode == "symlink":
            _link(src, target)
        else:
            _copy(src, target)
    return "linked" if mode == "symlink" else "copied"


def _link(src: Path, target: Path):
    try:
        os.symlink(src, target, target_is_directory=True)
    except (OSError, NotImplementedError) as e:
        raise SystemExit(
            f"symlink failed ({e}). On Windows, enable Developer Mode or run "
            f"with --mode copy.")


def _copy(src: Path, target: Path):
    shutil.copytree(src, target)


def _rm(target: Path):
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    else:
        target.unlink()


def uninstall(home: Path, dry: bool) -> int:
    manifest = load_manifest()
    if not manifest["entries"]:
        print("Nothing recorded as installed.")
        return 0
    tag = "[dry-run] " if dry else ""
    remaining = []
    removed = 0
    for e in manifest["entries"]:
        target = Path(e["target"])
        if target.is_symlink() or target.exists():
            if not dry:
                _rm(target)
            removed += 1
            print(f"{tag}removed   {e['tool']:8} {e['name']}  ({target})")
        else:
            print(f"{tag}gone      {e['tool']:8} {e['name']}  ({target})")
    save_manifest(remaining, dry)
    print(f"\n{tag}Uninstalled {removed} target(s).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Install Zen Starter Kit skills.")
    ap.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove what was installed")
    ap.add_argument("--mode", choices=["symlink", "copy"],
                    default="copy" if os.name == "nt" else "symlink",
                    help="link mode (default: copy on Windows, symlink elsewhere)")
    ap.add_argument("--tools", default="claude,opencode",
                    help="comma-separated subset of: " + ",".join(TOOL_SUBPATHS))
    ap.add_argument("--home", default=None,
                    help="override the base home dir (for testing/unusual setups)")
    args = ap.parse_args()

    home = Path(args.home).expanduser().resolve() if args.home else Path.home()

    if args.uninstall:
        return uninstall(home, args.dry_run)

    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    bad = [t for t in tools if t not in TOOL_SUBPATHS]
    if bad:
        print(f"Unknown tool(s): {bad}. Choose from {list(TOOL_SUBPATHS)}.")
        return 2
    return install(tools, args.mode, home, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
