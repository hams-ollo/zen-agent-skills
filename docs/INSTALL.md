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

The installer writes its copy-mode manifest to `scripts/.install-manifest.json` so it can recognize and update files it previously created. It reports a conflict instead of overwriting an unmanaged file.

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

Today the module ships two hooks, one of each shape:

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

Run the skill linter from the repository root:

```bash
python scripts/validate-skills.py
```

It checks skill frontmatter, names, descriptions, and body length, plus unresolved relative links, references to sibling skills that do not exist, links that escape the shipped skill tree, and skills that claim both draft and shipped status. It also enforces the parts of the skill schema that fail at the consumer rather than here: a description over 1024 characters or containing an angle bracket, a frontmatter property outside the six the schema permits, and frontmatter written in a form no real YAML parser can read. All four have shipped as real defects, and the shipped skills pass Anthropic's own `quick_validate.py` as well as this one.

Run the kit's own test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Check the work-tracking backlog for structural integrity:

```bash
python .tasks/validate.py --strict
```

Preview adapter generation without writing files:

```bash
python scripts/build-adapters.py --dry-run
```

Preview installation for a specific test home without touching your normal tool directories:

```bash
python scripts/install.py --dry-run --home ./.tmp/zen-home
```

The scripts and the test suite use only the Python standard library, so there is no package installation step. The suite under [`tests/`](../tests/) covers the kit's own tooling, derived from the specifications in [`spec/`](spec/); the kit has no runtime application to test.

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
