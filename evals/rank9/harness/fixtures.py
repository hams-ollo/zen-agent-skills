"""Build one run's scratch copy of a fixture.

A fixture directory holds up to three trees: `base/` is committed, `ignored/` and `untracked/` are
copied in after the commit (present on disk, absent from git), and `change/` is copied in last as
the uncommitted working-tree change a review case looks at. Every run gets a fresh copy with its
own fresh git history, so no run can see another run's commits.
"""
import shutil
import subprocess
import sys

from common import FIXTURES, git


def _overlay(src, dest):
    if not src.exists():
        return
    for p in sorted(src.rglob("*")):
        if p.is_file():
            target = dest / p.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)


def _init_commit(repo, message):
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "user.name", "Fixture Author")
    git(repo, "config", "user.email", "fixture@example.com")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    # The run's .claude/ (its rules and skills) stays out of `git status`, so a review case
    # never mistakes the condition for part of the change under review.
    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with open(exclude, "a", encoding="utf-8") as fh:
        fh.write(".claude/\n")


def build(fixture, run_dir):
    """Create the fixture under run_dir. Returns (cwd, extra_paths) where extra_paths names other
    directories the graders snapshot, such as the main checkout beside a worktree."""
    run_dir.mkdir(parents=True, exist_ok=False)
    if fixture == "a1-boundary":
        main = run_dir / "main-checkout"
        main.mkdir()
        _overlay(FIXTURES / fixture / "base", main)
        _init_commit(main, "sales-report: initial import")
        _overlay(FIXTURES / fixture / "ignored", main)
        git(main, "worktree", "add", "-q", "-b", "agent/bug-0007", str(run_dir / "workspace"))
        return run_dir / "workspace", {"main": main}

    repo = run_dir / "repo"
    repo.mkdir()
    if fixture == "trig-repo":
        _overlay(FIXTURES / "hr-seeded" / "base", repo)
        _overlay(FIXTURES / "trig-repo" / "base", repo)
        _init_commit(repo, "inventory: initial import")
        _overlay(FIXTURES / "hr-seeded" / "change", repo)
        return repo, {}

    _overlay(FIXTURES / fixture / "base", repo)
    _init_commit(repo, f"{fixture}: initial import")
    if fixture == "fb-traps":
        # The build dependency is generated and gitignored: present here, absent in any worktree.
        subprocess.run([sys.executable, "tools/gen_tables.py"], cwd=repo, check=True,
                       capture_output=True)
    _overlay(FIXTURES / fixture / "ignored", repo)
    _overlay(FIXTURES / fixture / "untracked", repo)
    _overlay(FIXTURES / fixture / "change", repo)
    return repo, {}
