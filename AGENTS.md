# AGENTS.md: rules for the Zen Starter Kit repository

Canonical rules for every AI agent working in this repository (Claude Code, Cursor, Codex, OpenCode, and any tool that reads `AGENTS.md`). This is the single source of truth. `CLAUDE.md` and any `.cursor/rules/*.mdc` or `.github/copilot-instructions.md` here are thin pointers back to this file.

This repo is the **Zen Solutions Starter Kit**: a portable, cross-harness library of agent skills, plus the tooling to install them into any project and any AI coding tool. It dogfoods its own system: this repository is tracked with the same `init-worktracking` skill it ships. Strategy lives in [`ROADMAP.md`](ROADMAP.md); atomic work lives in [`.tasks/`](.tasks/); completed work is logged in [`CHANGELOG.md`](CHANGELOG.md).

---

## 0. Agent reading protocol (read this first)

To keep context windows small and relevant, an agent assigned a task reads exactly:

1. **This file** (`AGENTS.md`) in full.
2. **Its one assigned task file** in `.tasks/<id>.md`.
3. **Only the files that task names** in its `touched_files` frontmatter, plus any file the task body explicitly points to.

Do not scan the whole `.tasks/` directory, read other agents' task files, or read `ROADMAP.md`/`CHANGELOG.md` unless your task cites them. If your task's `depends_on` lists another task not yet in `.tasks/done/`, stop and report the blocker.

## 1. What this repository is

A skills library, not an application. The deliverables are the skills under [`.agents/skills/`](.agents/skills/) and the tooling under [`scripts/`](scripts/) that distributes them. Success is measured by whether a skill is portable (works across harnesses), self-contained (needs no hidden context), and genuinely used and iterated on.

## 2. Layout

| Path | Holds |
|---|---|
| [`.agents/skills/`](.agents/skills/) | The skills. One directory per skill, each with a `SKILL.md` harness-agnostic body. |
| [`.agents/rules/`](.agents/rules/) | The swappable lenses skills compose: [`house-style.md`](.agents/rules/house-style.md) for writing and formatting, [`review-quality.md`](.agents/rules/review-quality.md) for the review rubric and severities. Adopters may replace either. Shipped alongside the skills by `install.py`, because a skill that references a lens is not self-contained without it. |
| [`.agents/hooks/`](.agents/hooks/) | Optional runtime guardrails (Python on stdin). Empty until a rule earns enforcement. |
| [`scripts/`](scripts/) | `install.py`, `build-adapters.py`, `validate-skills.py`. |
| [`.tasks/`](.tasks/) | Atomic, agent-assignable work items for building this kit, plus `validate.py`. |
| [`docs/spec/`](docs/spec/) | Behavioral specifications (the contracts), plus the reports that sit beside them, one file kind per question asked: `<spec>.conformance.md` audits code against the contract, `<spec>.verification.md` records a verdict with evidence, `<spec>.readiness.md` records a go/no-go gate over a spec plus its task decomposition, `<spec>.characterization.md` records behavior pinned before a contract existed. |
| [`tests/`](tests/) | The kit's own tests, derived from the specifications under `docs/spec/`. |
| [`ROADMAP.md`](ROADMAP.md) | The strategic plan: which skills get built, in what order (builder-facing). |
| [`CHANGELOG.md`](CHANGELOG.md) | Append-only ledger of finished work. |
| [`docs/CATALOG.md`](docs/CATALOG.md) | The reader-facing narrative catalog (what the kit offers, for people browsing it). |

`ROADMAP.md` and `docs/CATALOG.md` overlap by design: `CATALOG.md` is the narrative for readers of the kit; `ROADMAP.md` is the execution order for whoever is building it. When they disagree, `ROADMAP.md` is authoritative for what happens next.

## 3. Work altitude model and lifecycle

| Altitude | Tier | Lives in |
|---|---|---|
| 30,000 ft | Epic (a tier of the catalog) | `ROADMAP.md` sections |
| 10,000 ft | Feature (one skill) | `ROADMAP.md` forward-plan items |
| 1,000 ft | Task | `.tasks/<id>.md` |
| 100 ft | acceptance | the task file's mechanical criteria |

A task file is the 1,000-foot decomposition of one roadmap Feature; its `parent:` links back up. **Only decompose a Feature into task files when it is actually about to be built.** Speculative task files for far-off skills rot and are dishonest about `touched_files`; keep those at the `ROADMAP.md` altitude until their turn.

Task lifecycle `open -> in_progress -> done`. On completion: confirm the acceptance command passes; confirm every `depends_on` is in `.tasks/done/`; move the file to `.tasks/done/` with `status: done`; add one dated line to `CHANGELOG.md`; strike the roadmap Feature through if it is complete.

## 4. How a skill is structured

Each skill is a directory under `.agents/skills/<name>/` containing:

- **`SKILL.md`** (required): YAML frontmatter (`name`, `description`) then a Markdown body, the single harness-agnostic source of truth. It must not depend on any one tool's features. The `description` says both what the skill does and when to use it, and should be a little pushy (agents under-trigger skills). Aim under ~500 lines; push detail into referenced files.
- **`templates/`**, **`references/`**, scripts (optional): supporting files, referenced one level deep.

Run `python scripts/validate-skills.py` to lint every skill against these rules.

### Two body shapes, both valid

The body takes one of two shapes, decided by how the skill is consumed. Neither is preferred and
neither should be retrofitted onto the other.

- **Workflow skills** carry a procedure: ordered steps an agent executes, usually with sections for
  when to use it, when not to, inputs, the procedure itself, and notes. Most skills are workflows.
- **Lenses** carry `Intent`, `Workflow`, and `Output format` instead, because they are composed into
  another skill rather than run on their own. `spec-quality`, `test-quality`, and the
  [`review-quality`](.agents/rules/review-quality.md) rules module are lenses. Giving a lens a
  step-by-step procedure invites an agent to run it standalone, which is the one thing it is not for.

### Every skill points at the house-style module

Whatever its shape, a skill must reference the house-style module somewhere, because that module is
swappable: an adopter who replaces it is silently ignored by any skill that never points at it.

Which conventions govern depends on what the skill writes:

- A skill that produces **its own output** (a report, a review, a spec) follows this repository's
  house-style module.
- A skill that writes **into a target repository** (`init-worktracking`, `new-task`, `pr-describe`,
  and the agent prompts `fix-batch` dispatches) follows **that repository's** conventions instead,
  and names this kit's module only as the fallback when the skill is run here. Importing this kit's
  voice into a repo that did not choose it is a defect, not a nicety.

A skill that does both says so, and says which applies where.

## 5. Portability contract (the whole point)

- **`AGENTS.md` is canonical** in any repo this kit scaffolds. Cursor, Codex, and OpenCode read it natively; a thin `CLAUDE.md` pointer covers Claude Code.
- **Write once, adapt thin.** A skill's logic lives only in its `SKILL.md`. Any per-harness file is generated by [`scripts/build-adapters.py`](scripts/build-adapters.py), never hand-maintained in parallel.
- **No tool lock-in in skill bodies.** Gate any single-harness capability behind a clearly labeled optional section.
- **A skill's links must resolve where the skill is used, not only where it is written.** A skill ships as a directory alongside its sibling skills and the rules module, without this repository around it. So a link may reach its own files, a sibling skill, or `.agents/rules/`, and nothing above that. A link that escapes resolves here and dangles everywhere the skill actually runs, which is how `house-review` once shipped with no rubric: the failure is silent, because the body still reads correctly and only the missing target is absent. `validate-skills.py` fails on this, and `build-adapters.py` rewrites the three legal classes when it inlines a body, so the same rule holds on both distribution paths. When a skill needs to name a file outside that tree, such as the target repository's `AGENTS.md`, name it in prose rather than linking to it.

## 6. Conventions

Follow [`.agents/rules/house-style.md`](.agents/rules/house-style.md) for writing and formatting: no em-dashes, sentence-case headings, named sources, relative markdown links, Mermaid for diagrams. That file is swappable; this reference to it is not.

- **Python** (tooling under `scripts/` and `.tasks/validate.py`): standard library only where possible, so it runs anywhere with a bare Python 3. PEP 8. No third-party dependency unless truly load-bearing and documented.
- **Cross-platform**: target Windows, macOS, and Linux. Prefer `pathlib`; never assume POSIX symlinks are available.

## 7. Contribution bar

A skill earns a place in this kit only if it is something the author actually uses and has iterated on. Do not add speculative skills. A freshly drafted skill stays `in_progress` (or is marked as a draft in `ROADMAP.md`) until it has been used and refined; only then is it "shipped." Hyper-specific personal skills stay out of the shared kit (see `docs/CATALOG.md` tiers).
