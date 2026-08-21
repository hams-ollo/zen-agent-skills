# Installation and integration

The complete installation reference: every profile, every harness, adapter generation, validation commands, uninstall, and troubleshooting. For the five-minute path, see the quick start in [`README.md`](../README.md).

## Prerequisites

- Python 3.11 or newer. The floor and the newest release are both exercised by CI on Linux, macOS, and Windows; the kit does not claim a version it does not test.
- One or more supported AI coding tools, depending on the integration you choose.
- A project where you want to use the skills. The kit itself can also be used as a dogfooding example.

Check the Python version before installing:

```bash
python --version
```

On systems where Python is exposed as `python3`, use `python3` in the commands below.

## Get the kit

```bash
git clone https://github.com/hams-ollo/zen-agent-skills.git
cd zen-agent-skills
```

## Review the installation plan

The dry run makes no changes. It shows which skills would be installed and where:

```bash
python scripts/install.py --dry-run
```

## Install global skills

Install the default tool set, Claude Code and OpenCode:

```bash
python scripts/install.py
```

The installer is idempotent, so it is safe to run again after the kit changes. On Windows it uses directory copies by default. On macOS and Linux it uses directory symlinks by default.

Install for only one supported tool when needed:

```bash
python scripts/install.py --tools claude
python scripts/install.py --tools opencode
```

The installer writes its copy-mode manifest to `scripts/.install-manifest.json` so it can recognize and update files it previously created. It reports a conflict instead of overwriting an unmanaged file. The manifest also records a SHA256 for every file it places, which is what makes the staleness check below possible.

## Check whether an installed set is still current

An installed skill is a snapshot. In copy mode (the Windows default, and available everywhere) editing a skill in this repository does not change your installed copy, and nothing about the stale copy looks wrong: it is a valid skill that passes both validators and reads correctly. This check is the only thing that will tell you:

```bash
python scripts/install.py --check
python scripts/install.py --check --home ./.tmp/zen-home
```

Pass the same `--home` you installed with. The check reads the manifest, re-reads each installed target, and reports one line per installed module. It writes nothing, ever: an installed file you edited on purpose is yours, and this command will not overwrite it.

| Report | Meaning |
|---|---|
| `ok` | For a skill, every placed file still matches the kit. For the rules module the claim is narrower, because that module is yours: every file the install placed is still there, and the kit's own copy of it has not moved since. A lens you edited is not checked against anything and is never counted against this |
| `diverged` | At least one file no longer matches, named individually, with the installed and source digests. For the rules module this is absence only: a file the install placed is gone. Editing a lens there is never divergence |
| `linked` | The target is a symlink to its source, so it cannot go stale |
| `revised` | The kit's copy of an adopter-owned file (the rules module) changed since you installed. Your copy is left alone |
| `unknown` | The entry predates this baseline, so its state is not known. Re-install to establish one, or `--replace-adopted` for the rules module, where a re-install preserves your files and records nothing |

Exit codes are `0` when everything current, `1` when something diverged, and `2` when the check could not answer (an entry with no baseline, or a source the kit no longer has). Nothing recorded beneath the given home is also a `2`, not a clean result: a check that never saw your install has learned nothing about it.

Run it when a skill behaves like an older version of itself, after pulling changes into this repository, and before trusting an installed skill for anything consequential. The fix for a diverged entry is to re-install: this command deliberately does not do it for you.

The rules module is handled differently on purpose. [`.agents/rules/`](../.agents/rules/) is swappable, and rewriting a lens is something the kit invites you to do, so your edits there are never reported as divergence. What you are told instead is when the kit's own copy of that lens has moved since you installed, which is news you can act on rather than a warning that fires forever.

Deleting a lens is the one thing there the check does report. A file the installer placed and that is no longer on disk is named individually and exits `1`, because a missing lens is a different claim from an edited one: `house-review` reads its entire rubric and severity scheme out of that module, and an install missing it behaves like a skill that never had one. The check still writes nothing, so the file is not restored. Re-install to have the removal recorded, after which the check stops reporting it, or run `--replace-adopted` to take the kit's copy back.

## Your edits to the rules module survive a re-install

The same invitation binds the installer, not just the check. Re-running the install refreshes a rules file you have not touched, and keeps one you have, naming it:

```
preserved claude   rules  -> C:\Users\you\.claude\rules
          preserved house-style.md: you edited it
```

The two cases are told apart by the digest recorded when the file was placed. A file that still matches its baseline is one nobody edited, so the kit refreshes it and you stay current. A file that does not is yours, so it is kept and the kit's version is never merged into it: reconciling the two is your call, not the installer's. A rules file you *added* beside the kit's is left alone in both directions, since it is not the kit's to refresh or to remove.

When you want the kit's copy back, ask for it:

```bash
python scripts/install.py --replace-adopted
```

That discards your edits to the rules module and re-establishes the baseline. It is its own flag rather than a mode, because it decides what happens to your work.

One case cannot be answered: an install predating the digest baseline recorded nothing, so an edited file is indistinguishable from an untouched one. There the installer preserves everything and says the baseline is unknown, because a stale lens is visible and recoverable while overwritten work is neither. Use `--replace-adopted` to take the kit's copies and start recording a baseline again.

## Choose how many skills to install

Every installed skill's `description` is loaded so your agent can route to it, and that budget is shared with every other skill you have installed. So `--profile` selects how many skills to place, and the run reports what each profile costs in description characters:

```bash
python scripts/install.py --profile core
python scripts/install.py --profile all
```

| Profile | Skills | What it is |
|---|---|---|
| `core` | 3 | Scaffold a project, track work in it, describe the change at the end |
| `spine` | 18 | The contract-driven delivery loop. **The default** |
| `all` | 20 | Everything, adding the two handoff skills |

A profile is expanded over sibling references before anything is placed, so it can never install a skill whose composed sibling is missing, and the run says when it expanded what you asked for. That is also why the sizes jump the way they do rather than offering a middle: most of the skills reference each other, so any profile reaching into that group brings the group with it.

Defaulting to `spine` means `agent-handoff` and `human-handoff` are not placed. Nothing is removed if you already installed them: this command only places and updates, and reversal is `--uninstall`. Pass `--profile all` to keep them refreshed.

## Hooks, if you want enforcement (opt-in)

Everything above is Markdown your agent reads. Hooks are different: they are small Python programs your harness runs at a lifecycle event, inside your session, in your repository. So they are not installed by default and they are not activated by this installer.

```bash
python scripts/install.py --with-hooks
```

That places the module and then prints a registration block. **Nothing fires until you paste that block into `~/.claude/settings.json` yourself.** The installer does not edit your settings, for two reasons: a settings file is the one thing here the uninstall manifest cannot cleanly reverse, and a guardrail you did not knowingly switch on is indistinguishable from a bug when it fires.

Today the module ships three hooks, two reminders and one gate:

- **`skill-reachability-reminder`** says so, once, when a session starts with none of this kit's skills reachable at either project or user scope. It recognises them by directory name, so a library of somebody else's skills is not counted as this kit installed. It stays completely silent when the kit's skills are reachable, and it reports reachability only: not whether what it found is current, which is what `--check` below answers. It never blocks and never writes.
- **`delegation-reminder`** notes, after a delegated agent reports back, that its summary is a claim rather than evidence. It never blocks.
- **`spec-conformance-gate`** blocks when work a contract governs is closed and nothing records whether the implementation actually matches that contract. Every block names its escape: run `spec-conformance`, or add a `conformance:` key to the frontmatter declaring the audit lives elsewhere.

See [`.agents/hooks/README.md`](../.agents/hooks/README.md) for the module contract and the rules a new hook has to satisfy.

To back out: remove the block from your settings to deactivate, and `--uninstall` to remove the files.

## Or install with `npx skills`

The kit is discoverable by [`npx skills`](https://github.com/vercel-labs/skills), the cross-agent installer indexed at skills.sh, with no manifest and no configuration: `.agents/skills/` is one of the layouts it walks.

```bash
npx skills add hams-ollo/zen-agent-skills
```

**It installs the skill bodies and nothing else, which matters here.** Every skill in this kit composes a lens from [`.agents/rules/`](../.agents/rules/) through a relative reference, and that installer copies only each skill's `SKILL.md`, so those references resolve to nothing. Most skills lose the house-style module; `house-review` loses its entire rubric and severity scheme, because they live in the lens rather than in the skill. Verified against this repository on 2026-07-28.

So use it if you want the skill bodies in a hurry, across a harness the Python installer does not target. Use `python scripts/install.py` if you want the kit as designed: it is the only path that places the rules module where the skills' own references resolve, and it needs no Node and no network.

## Generate project-level adapters

Cursor and VS Code or Copilot use project-level configuration in this kit. Generate adapters into the project where you want to use the skills:

```bash
python scripts/build-adapters.py --target cursor,vscode --out ../my-project
```

This creates:

- `.cursor/rules/<skill-name>.mdc` for Cursor.
- `.github/prompts/<skill-name>.prompt.md` for VS Code or Copilot.
- `.agents/rules/` and `.agents/skills/<skill-name>/`, holding the material those adapters link to: the swappable rules module (the review rubric, the house style) and each skill's own templates. The adapters' relative links are rewritten to point here, so a lens reference resolves in the target project instead of dangling. An `.agents/rules/` file that already exists is never overwritten, because that module is swappable and the project's own copy outranks the kit's.

Generated adapters are derived files. Edit the source `SKILL.md` under [`.agents/skills/`](../.agents/skills/), then regenerate the adapters. A generation run overwrites the adapter files it owns.

## Integration by harness

| Harness | Integration | Command or location |
|---|---|---|
| Claude Code | Global skill discovery | `python scripts/install.py --tools claude` |
| OpenCode | Global skill discovery | `python scripts/install.py --tools opencode` |
| Cursor | Project rule adapter | `python scripts/build-adapters.py --target cursor --out <project>` |
| VS Code or Copilot | Project prompt adapter | `python scripts/build-adapters.py --target vscode --out <project>` |
| Other harnesses | Read the canonical skill manually or add a local adapter | [`.agents/skills/`](../.agents/skills/) |

The kit does not maintain separate hand-edited versions of a skill for each harness. The canonical source remains the `SKILL.md` file.

## Use a skill

Ask the installed harness to use a skill by name, or select the generated rule or prompt in the target project. Begin with a workflow skill such as `project-bootstrap`, `init-worktracking`, or `new-task`. Read the skill's `SKILL.md` when you need the complete procedure and acceptance criteria.

## Validate changes

One command decides whether a change to the kit is acceptable, and it takes no flags:

```bash
python scripts/run-checks.py
```

[`run-checks.py`](../scripts/run-checks.py) runs every gate in a single pass, including the ones that cover the installer this page documents. [`AGENTS.md`](../AGENTS.md) names what those gates are, and this page deliberately does not restate the list: a second copy of it is a second thing to go stale. CI calls the same script, so the gate set cannot drift between your machine and the pipeline either.

It exits `0` when every gate passed, `1` when a gate ran and failed, and `2` when a gate could not run at all. A `2` outranks a `1`, for the same reason `--check` above uses that precedence: an incomplete report is a different claim from a bad change. Every gate runs even after one fails, so a single run tells you everything that is wrong rather than only the first thing. CI runs Linux, macOS, and Windows across the supported Python range, so passing locally is necessary but not sufficient.

The gates that place files use a throwaway home under `./.tmp/`, so a real installation of your own is never touched. While you are iterating, running one gate directly is a faster loop, for instance `python scripts/install.py --dry-run --home ./.tmp/zen-home` while you are reworking the installer. That is a convenience and not a substitute, because the acceptance command is what decides.

The scripts and the test suite use only the Python standard library, so there is no package installation step. The suite under [`tests/`](../tests/) covers the kit's own tooling, derived from the specifications in [`spec/`](spec/); the kit has no runtime application to test. The contribution rules themselves, including what the skill schema requires of a skill's frontmatter, live in [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Uninstall

Remove the targets recorded by the installer:

```bash
python scripts/install.py --uninstall --dry-run
python scripts/install.py --uninstall
```

If you installed with `--home`, provide the same `--home` value when uninstalling. Generated Cursor and VS Code or Copilot adapters are project files and should be removed from the target project through its normal version-control workflow.

## Troubleshooting

### The installer reports a conflict

The installer found a file or directory at a target path that it did not create. Move it, remove it, or choose a different home directory, then rerun the command. The installer does not overwrite unmanaged targets.

### Symlink creation fails on Windows

Use the default Windows copy mode, or force it explicitly:

```bash
python scripts/install.py --mode copy
```

### A generated adapter is out of date

Regenerate it from the kit root. Do not edit the generated file directly:

```bash
python scripts/build-adapters.py --target cursor,vscode --out ../my-project
```

### A skill is not discovered

Confirm that the skill has a `SKILL.md`, run the validator, and verify that you installed the correct integration for your harness. Claude Code and OpenCode use `install.py`; Cursor and VS Code or Copilot use `build-adapters.py`.
