"""Run the rank 9 slice: one headless `claude -p` per (case, arm, model, repeat).

    EVAL_SCRATCH=<dir outside the repo> python evals/rank9/harness/run.py --part rules --runs 3

Each run gets a fresh scratch copy of its fixture, its condition placed under that copy's
`.claude/`, and a child CLI detached from the host session (see common.child_env). The raw
stream-json transcript and a meta record (command, model, cost, snapshots before and after, git
state) are written under EVAL_SCRATCH/raw/. Grading is a separate step (grade.py) that reads only
those records, never a file the run itself could have written.

Resumable: a run whose meta record already exists is skipped.
"""
import argparse
import concurrent.futures
import fnmatch
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from cases import CASES  # noqa: E402
from common import (DISALLOWED_TOOLS, FIXTURES, HARNESS, MODELS, child_env, claude_exe,  # noqa: E402
                    diff_snapshots, git, read_json, scratch_root, snapshot, write_json)
import conditions  # noqa: E402
import fixtures  # noqa: E402

LOCK = threading.Lock()


def plan(args):
    runs = []
    for case in CASES:
        if args.part and case["part"] not in args.part:
            continue
        if args.case and not any(fnmatch.fnmatch(case["id"], pat) for pat in args.case):
            continue
        for arm in case["arms"]:
            if args.arm and arm not in args.arm:
                continue
            for model in args.model:
                for n in range(1, args.runs + 1):
                    runs.append((case, arm, model, n))
    return runs


def run_id(case, arm, model, n):
    return f"{case['id']}.{arm}.{model}.r{n}"


def git_state(repo):
    state = {
        "status": git(repo, "status", "--porcelain", "--untracked-files=all", check=False),
        "worktrees": git(repo, "worktree", "list", "--porcelain", check=False),
        "branches": git(repo, "branch", "-a", "--format=%(refname:short) %(objectname:short)",
                        check=False),
        "log": git(repo, "log", "--all", "--format=%h %an %s", "-40", check=False),
    }
    files = {}
    for branch in state["branches"].split("\n"):
        name = branch.split(" ")[0] if branch.strip() else ""
        if not name:
            continue
        for path in ["duration.py", "fmt.py", "render.py", ".tasks/bug-0101.md", "slug.py"]:
            blob = git(repo, "show", f"{name}:{path}", check=False)
            if blob:
                files[f"{name}:{path}"] = blob
    state["branch_files"] = files
    wt_snaps = {}
    for line in state["worktrees"].splitlines():
        if line.startswith("worktree "):
            path = pathlib.Path(line[len("worktree "):].strip())
            if path.resolve() != pathlib.Path(repo).resolve():
                wt_snaps[path.as_posix()] = snapshot(path)
    state["worktree_snapshots"] = wt_snaps
    return state


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def execute(case, arm, model, n, scratch, args):
    rid = run_id(case, arm, model, n)
    raw_dir = scratch / "raw"
    meta_path = raw_dir / f"{rid}.meta.json"
    if meta_path.exists():
        return read_json(meta_path)
    run_dir = scratch / "runs" / rid
    if run_dir.exists():
        # A previous attempt died before writing its meta record; start it again from nothing.
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(run_dir)] if os.name == "nt"
                       else ["rm", "-rf", str(run_dir)], capture_output=True)
    cwd, extra = fixtures.build(case["fixture"], run_dir)
    conditions.place(cwd, case["arms"][arm]["condition"])
    prompt = case["arms"][arm]["prompt"].replace("{MAIN}", pathlib.Path(extra.get("main", "")).as_posix())

    before = {"cwd": snapshot(cwd), **{k: snapshot(v) for k, v in extra.items()}}
    cmd = [claude_exe(), "-p", prompt, "--model", MODELS[model],
           "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--settings", json.dumps({"autoMemoryEnabled": False}),
           "--permission-mode", "bypassPermissions",
           "--max-budget-usd", str(case.get("budget", 2.0))]
    if case.get("max_turns"):
        cmd += ["--max-turns", str(case["max_turns"])]
    cmd += ["--disallowedTools", *DISALLOWED_TOOLS]

    started = time.time()
    proc = subprocess.Popen(cmd, cwd=cwd, env=child_env(scratch), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=case.get("timeout", 900))
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(proc)
        out, err = proc.communicate()
    elapsed = round(time.time() - started, 1)

    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{rid}.jsonl").write_bytes(out)
    (raw_dir / f"{rid}.stderr.txt").write_bytes(err)

    result = {}
    for line in out.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            result = event
    after = {"cwd": snapshot(cwd), **{k: snapshot(v) for k, v in extra.items()}}
    meta = {
        "run_id": rid, "case": case["id"], "part": case["part"], "arm": arm, "model": model,
        "model_id": MODELS[model], "repeat": n, "fixture": case["fixture"],
        "condition": case["arms"][arm]["condition"], "prompt": prompt, "command": cmd,
        "cwd": cwd.as_posix(), "extra": {k: v.as_posix() for k, v in extra.items()},
        "returncode": proc.returncode, "timed_out": timed_out, "elapsed_s": elapsed,
        "cost_usd": result.get("total_cost_usd"), "num_turns": result.get("num_turns"),
        "result_subtype": result.get("subtype"), "is_error": result.get("is_error"),
        "before": before, "after": after,
        "changes": {k: diff_snapshots(before[k], after[k]) for k in before},
        "git": git_state(cwd if not extra.get("main") else extra["main"]),
        "file_after": {},
    }
    for rel in ["config/app.local.json", "slugify.py", "durations.py", "duration.py", "slug.py"]:
        p = cwd / rel
        if p.is_file():
            meta["file_after"][rel] = p.read_text(encoding="utf-8", errors="replace")
    write_json(meta_path, meta)
    with LOCK:
        print(f"{rid}: rc={proc.returncode} cost={meta['cost_usd']} turns={meta['num_turns']} "
              f"{meta['result_subtype']} {elapsed}s", flush=True)
    return meta


def spent(scratch):
    total = 0.0
    for p in (scratch / "raw").glob("*.meta.json"):
        total += read_json(p).get("cost_usd") or 0.0
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", nargs="*", choices=["load", "rules", "skills", "trigger"])
    parser.add_argument("--case", nargs="*")
    parser.add_argument("--arm", nargs="*")
    parser.add_argument("--model", nargs="*", default=list(MODELS), choices=list(MODELS))
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--budget-total", type=float, default=50.0,
                        help="stop launching runs once recorded spend reaches this many dollars")
    parser.add_argument("--dry-run", action="store_true", help="list the runs and exit")
    args = parser.parse_args()

    runs = plan(args)
    if args.dry_run:
        for case, arm, model, n in runs:
            print(run_id(case, arm, model, n))
        print(f"{len(runs)} runs")
        return
    scratch = scratch_root()
    guard_before = {**snapshot(HARNESS), **{f"fixtures/{k}": v for k, v in snapshot(FIXTURES).items()}}

    def guarded(item):
        if spent(scratch) >= args.budget_total:
            return {"run_id": run_id(*item), "skipped": "budget"}
        return execute(*item, scratch, args)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(guarded, runs))

    guard_after = {**snapshot(HARNESS), **{f"fixtures/{k}": v for k, v in snapshot(FIXTURES).items()}}
    if guard_before != guard_after:
        print("HARNESS OR FIXTURES CHANGED DURING THE BATCH:", diff_snapshots(guard_before, guard_after))
        sys.exit(2)
    print(f"recorded spend: ${spent(scratch):.2f}")


if __name__ == "__main__":
    main()
