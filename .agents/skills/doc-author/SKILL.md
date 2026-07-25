---
name: doc-author
description: >-
  Writes new, high-quality Markdown documentation for the repository it is used in, grounded
  in the actual code and following documentation best practices. Handles READMEs (technical or
  for non-technical readers), architecture docs with Mermaid diagrams, setup and deployment
  guides, contributing guides, design docs, and architecture decision records, and can bootstrap
  a fresh repo's baseline doc set. Use this whenever the user wants to create documentation that
  does not exist yet. Trigger on phrases like: "create a README", "write an architecture doc
  with mermaid diagrams", "document this project for non-technical users", "scaffold the repo
  docs", "set up the docs folder", "write a deployment guide", "create a CLAUDE.md for this
  repo", "we need a design doc for X", or any request to produce a new .md document describing
  the codebase or project. When the document already exists and the user wants it updated,
  revised, or its links fixed, use doc-revise instead. When the user does not know which
  document is wrong, use doc-sync instead.
---

# Doc author

Create documentation that is accurate, well-structured, and matched to its reader. The two ways documentation fails are being wrong (it describes code that does not exist or has drifted) and being shapeless (a wall of text with no reader in mind). This skill guards against both: ground every claim in the real repository, and pick a structure that fits the document type and audience. When the document already exists and needs updating rather than creating, use [`doc-revise`](../doc-revise/SKILL.md) instead. When the user does not yet know which document is wrong, use [`doc-sync`](../doc-sync/SKILL.md) to find out first.

## Ground it in the code first

Never document from assumption. Before writing, read the parts of the repository the document will describe: the relevant source, the `AGENTS.md` or `CLAUDE.md`, the config, the entry points. If you state that a command runs the tests or that a module does X, it should be because you saw it, not because it is a reasonable guess. Drifted docs are worse than missing ones because readers trust them.

## Identify the document type and reader

Ask, or infer from the request, two things: what kind of document this is, and who reads it. The structure follows from those. Common types and their spines:

- **README (technical)**: what the project is, quick start, install and run, key commands, layout, where to go next. Lead with the one-sentence description and the fastest path to running it.
- **README (non-technical)**: what this does and why it matters, in plain language, no jargon, with the mental model built from the ground up. The user asks for this often; assume the reader has no domain knowledge and explain the concepts, not just the steps.
- **Architecture doc**: the system in Mermaid diagrams (component, flow, sequence, state as fits), the major pieces and how they connect, the key decisions and why. Diagrams are Mermaid fenced blocks, never ASCII.
- **Setup or deployment guide**: prerequisites, step-by-step, configuration, verification, and common failure modes. Every step should be something the reader can actually execute and check.
- **Contributing guide**: how to get set up, conventions, the change and review workflow, how to run the checks.
- **Design doc or ADR**: the problem, the options considered, the decision, the rationale, and the consequences. Name the tradeoffs honestly.

If the type is unclear, ask one short question rather than guessing wrong and writing the whole thing in the wrong shape.

## Bootstrap mode (new repo)

When the user is starting a fresh repository and wants the baseline set, produce the trio: a pointer `CLAUDE.md` or `AGENTS.md`, an `ARCHITECTURE.md` with Mermaid diagrams, and a `README.md` at the reader level they name. Do not scaffold the work-tracking system here; if the user wants task tracking, defer to the [`init-worktracking`](../init-worktracking/SKILL.md) skill, which owns `AGENTS.md` rules, `ROADMAP.md`, and `.tasks/`. For a full new-repo setup (a language-aware scaffold plus tracking), [`project-bootstrap`](../project-bootstrap/SKILL.md) is the umbrella front door that composes this skill with `init-worktracking`. This skill and those are designed to compose, not overlap.

## Structure and quality bar

- Open every document with a one-sentence statement of what it is and who it is for. A reader should know within seconds whether they are in the right place.
- Use real headings in sentence case, short paragraphs, and lists where they earn their place. Do not pad.
- Diagrams are Mermaid, never ASCII art. Keep labels concise and on one line.
- Link to files and code symbols with clickable links so a reader can jump straight there.
- Name sources and authorities directly; no "studies show" or anonymous claims.
- No em-dashes; use commas, colons, or parentheses (the kit's swappable [`.agents/rules/house-style.md`](../../rules/house-style.md) is the source of these writing conventions).
- Write the file to the sensible location (repo root for README, a `docs/` folder for the rest) and tell the user where it landed.

## After writing

Reread the document once as its intended reader. If a non-technical README still assumes knowledge, fix it. If an architecture doc's diagram does not match the code you read, fix the diagram. The value is in the second pass.
