# AGENTS.md: rules for the Zen Agent Skills repository

Canonical rules for every AI agent working in this repository (Claude Code, Cursor, Codex, OpenCode, and any tool that reads `AGENTS.md`). This is the single source of truth. `CLAUDE.md` and any `.cursor/rules/*.mdc` or `.github/copilot-instructions.md` here are thin pointers back to this file.

This repo is **Zen Agent Skills**: a portable, cross-harness library of agent skills, plus the tooling to install them into any project and any AI coding tool. It dogfoods its own system: this repository is tracked with the same `init-worktracking` skill it ships. Strategy lives in [`ROADMAP.md`](ROADMAP.md); atomic work lives in [`.tasks/`](.tasks/); completed work is logged in [`CHANGELOG.md`](CHANGELOG.md).

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
| [`.agents/rules/`](.agents/rules/) | The swappable lenses skills compose: [`house-style.md`](.agents/rules/house-style.md) for writing and formatting, [`review-quality.md`](.agents/rules/review-quality.md) for the review rubric and severities, [`autonomy.md`](.agents/rules/autonomy.md) for what an agent may do when nobody is watching. Adopters may replace any of them. Shipped alongside the skills by `install.py`, because a skill that references a lens is not self-contained without it. |
| [`.agents/hooks/`](.agents/hooks/) | Optional runtime guardrails (Python on stdin), each a *reminder* (injects context, never blocks) or a *gate* (blocks, only when the condition is decidable from the payload). The only thing the kit ships that runs inside an adopter's session, so installation is opt-in and activation is theirs: `install.py --with-hooks` places the files and prints the registration rather than editing anyone's settings. Contract in [`.agents/hooks/README.md`](.agents/hooks/README.md). |
| [`scripts/`](scripts/) | `install.py`, `build-adapters.py`, `validate-skills.py`, `check-provenance.py`. |
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

Task lifecycle `open -> in_progress -> done`. On completion: confirm the acceptance command passes; confirm every `depends_on` is in `.tasks/done/`; **run `doc-sync` over the reader-facing documents and apply or dismiss each finding**; move the file to `.tasks/done/` with `status: done` and **re-anchor its relative links for the extra directory level**; add one dated line to `CHANGELOG.md`; strike the roadmap Feature through if it is complete.

The re-anchoring clause is in that list because the move silently invalidates every link in the file: a task authored in `.tasks/` correctly links to `../scripts/x.py`, and from `.tasks/done/` that same text means `.tasks/scripts/x.py`. `bug-0011` found 101 links across 36 completed tasks broken exactly this way, with `validate.py --strict` and the CI docs link step both passing, because neither looked here. `validate.py` now checks every link against the directory the file is actually in, so the move fails loudly.

The `doc-sync` step is in that list because its absence has cost real work. `feat-0031` shipped a user-facing feature that was dogfooded, given a conformance matrix and a verification record, and left every reader-facing document with zero mention of it. Updating `CHANGELOG.md` and the task file is bookkeeping, not documentation: a feature only a maintainer can find out about has not shipped for anyone else.

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

### Provenance for material folded in from elsewhere

A meaningful share of this kit was adapted from somewhere else, and prose credit alone decays into folklore. `ROADMAP.md` once credited `doc-sync` to an upstream `document` workflow that was never vendored here, and the only surviving trace of the real contract was one line inside a gitignored folder that no longer exists. The attribution went wrong in under two weeks, and nothing could check it.

So any file or region adapted from an external source carries a **provenance block**, and [`scripts/check-provenance.py`](scripts/check-provenance.py) re-fetches every recorded source and reports drift.

| Field | Required | Content |
|---|---|---|
| `source` | yes | Absolute raw URL of the exact upstream file, not the repository's landing page. This is what gets re-fetched. |
| `author` | yes | The upstream author, named. |
| `license` | yes | The upstream license. |
| `retrieved` | yes | ISO date the fetch actually ran. |
| `sha256` | yes | SHA256 of the retrieved upstream bytes. |
| `origin` | no | A further hop, when the immediate source is itself carrying the material from somewhere else. Prose only, never fetched. |
| `note` | no | One line of context. |
| `status` | no | `unlocatable`, when the upstream source genuinely cannot be found. It replaces `retrieved` and `sha256`, and makes `note` required, where the note says what was searched. |

Placement follows the file type, and there is no sidecar file: a Python hook carries the block in a `Provenance` section of its module docstring, a skill in a `## Provenance` body footer inside a fenced code block tagged `provenance`, and a rules lens the same way. One adapted file may carry more than one block when it draws on more than one upstream file. A `source:` line alone does not make a block: the parser requires at least one other field, because `source:` is an ordinary word that other templates use.

A skill's block never becomes a new frontmatter key. `ALLOWED_FRONTMATTER_KEYS` in `validate-skills.py` deliberately mirrors Anthropic's own six-key schema, so a seventh key would be rejected by Anthropic's validator even after ours was widened to accept it. Use the body footer, or the existing `license` or `metadata` key.

Four rules the convention only works if you follow:

- **Digest the retrieved upstream content, never the adapted local file.** The local file is expected to differ, because adaptation is the point. The digest answers whether the thing we adapted *from* has changed since we looked, which is the only question a drift check can honestly answer for adapted material.
- **Fetch with `urllib` and digest with `hashlib`.** Never use an agent's web-fetching tool. Those return a model-summarized markdown conversion of a page rather than its bytes, so the digest would be a digest of a summary: stable-looking, meaningless, and impossible for anyone to reproduce.
- **The block records the immediate source, not the origin.** You can only drift-check what you actually retrieved, so the digest belongs to the file you fetched. When the chain has a further hop, name it in `origin` and leave tracking its drift to whoever fetched it.
- **An unlocatable source is recorded, not guessed.** A confident-looking digest for content nobody re-fetched is worse than no provenance at all, because a wrong digest reads as verified and passes every automated check.

A block backfilled after the fact pins upstream as of its `retrieved` date, not the exact bytes originally adapted, whenever the snapshot that was adapted from is gone. Say so in `note` rather than letting the date imply more than it proves.

The check stays out of required CI: it needs network, and a check that fails when GitHub is slow gets disabled within a week. Run it on demand. It reports drift and never syncs. Upstream's own `sync-maintainability-review.mjs` rewrites its vendored region in place, which is correct for verbatim vendoring and wrong here, because every fold-in in this kit was house-styled and retargeted and an overwrite would destroy the adaptation.

## 7. Contribution bar

A skill earns a place in this kit only if it is something the author actually uses and has iterated on. Do not add speculative skills. A freshly drafted skill stays `in_progress` (or is marked as a draft in `ROADMAP.md`) until it has been used and refined; only then is it "shipped." Hyper-specific personal skills stay out of the shared kit (see `docs/CATALOG.md` tiers).
