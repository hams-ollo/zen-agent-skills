# .tasks/: active work items

Atomic, agent-assignable work. One file per task. This directory is the 1,000-foot layer of the work-altitude model; strategy lives one level up in [`../ROADMAP.md`](../ROADMAP.md), and finished work is logged in [`../CHANGELOG.md`](../CHANGELOG.md). The full model is in [`../AGENTS.md`](../AGENTS.md).

## For an assigned agent

Read [`../AGENTS.md`](../AGENTS.md) (global rules) plus your one assigned task file plus the files it names in `touched_files`. Do not scan this directory or read other task files.

## Naming

`<type>-<NNNN>-<slug>.md`, where `type` is `bug`, `feat`, `chore`, or `epic`. The `id` frontmatter field equals the `<type>-<NNNN>` prefix. IDs are stable and never reused, even after a task moves to `done/`. Use the next unused number per type (zero-padded to four digits).

## Authoring a new task

Copy [`_TEMPLATE.md`](_TEMPLATE.md), give it the next id, and fill every section. A good task is self-contained: an agent that reads only `AGENTS.md`, this file, and the `touched_files` should be able to complete it without asking questions. Keep `touched_files` honest and complete: it is the agent's entire read/write surface and the whitelist that keeps context small.

Prefer the `new-task` skill (from Zen Agent Skills) to author tasks at the gold-standard bar automatically, then this format is filled for you.

## Validating

Run the shipped checker before dispatching work to agents:

    python .tasks/validate.py

It verifies frontmatter schema, id uniqueness, that every `depends_on` resolves to a real task, that every relative markdown link resolves from the directory the file is actually in, and (with `--strict`) that every `touched_files` path exists. It exits non-zero on any error, so it drops cleanly into CI or a pre-commit hook.

## Lifecycle

`open -> in_progress -> done`. On done: move the file to `done/`, set `status: done`, re-anchor the file's relative links for their new depth (a task authored in `.tasks/` links to `../x`; from `done/` that is `../../x`), add one dated line to `../CHANGELOG.md` referencing the task id, and (if it completed a roadmap Feature) strike that Feature through in `../ROADMAP.md`. See the task-lifecycle section of `AGENTS.md`.

The re-anchoring step is in that list because its absence was invisible for months: 101 links across 36 completed tasks had broken this way while every command reported success. `validate.py` now fails on them, so the move tells you.

## Frontmatter fields

| Field | Meaning |
|---|---|
| `id` | Stable task id, matches the filename prefix. |
| `type` | `bug` \| `feat` \| `chore` \| `epic`. |
| `status` | `open` \| `in_progress` \| `blocked` \| `done`. |
| `priority` | `P0` (blocks a shipped output) \| `P1` \| `P2`. |
| `parent` | The roadmap Feature/Epic this task serves (up-link, 100ft -> 30k ft). |
| `depends_on` | Task ids that must reach `done/` before this one starts; `[]` if none. |
| `spec` | Optional. Path to the approved spec this task implements. |
| `scenarios` | Optional. The `S-NNN` scenario ids from that spec this task covers. |
| `external` | Optional. The upstream GitHub issue this task serves: `#123` here, `owner/repo#123` elsewhere. |
| `touched_files` | Every file the task expects to read or modify, each of which must already exist. |
| `created` | ISO date the task was authored. |

`external` links the task to the issue tracker. Store the reference in GitHub's own syntax, because
`pr-describe` emits it verbatim after a closing keyword so merging the pull request closes the issue.
A bare number is rejected on purpose: keeping the stored value identical to what GitHub expects means
emission is concatenation rather than translation. See [`docs/spec/tracker-links.md`](../docs/spec/tracker-links.md).

`spec` and `scenarios` are what make a task traceable back to a contract. Omit both for a task that
does not come from a spec, which is most of them. Fill both when one exists, because a readiness
gate run before implementation reads them to confirm every scenario has a task and every task has a
reason to exist.

`touched_files` is the agent's entire read/write surface, and every path in it must already exist:
`validate.py --strict` reports one that does not, and `--strict` is the mode a backlog gate in CI
runs, so naming a file that has not been created yet fails the build. A file the task will **create**
is named in that task's **Scope** section instead, with the exact path it belongs at. That is where
an implementing agent reads where a new file goes, and where an author says it.

## A note on parallel agents

These task files are the natural unit of work for a batch of parallel, worktree-isolated agents (one task per agent). For that to be safe, `.tasks/` must be tracked by git: if it is gitignored, worktree isolation silently splits the backlog from the main checkout and agents will invent incompatible bookkeeping. Keep this directory committed.
