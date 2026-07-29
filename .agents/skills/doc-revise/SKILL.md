---
name: doc-revise
description: >-
  Updates and revises existing Markdown documentation in place, without flattening its voice or
  rewriting more than asked. Reconciles a doc with the current code or project state, fixes
  cross-document links and references after files or folders have moved, keeps a set of docs
  internally consistent. Use this whenever the
  user wants to change documentation that already exists. Trigger on phrases like: "update the
  docs to reflect this", "I moved these files, fix the links", "make sure the linking across the
  docs is still valid", "revise the README with this new content", "move completed items to the
  changelog", "the docs are out of date after these changes", "add contextual emojis to the
  headings", or any request to edit, refresh, or reconcile existing .md files. When the document
  does not exist yet and needs to be created from scratch, use doc-author instead. When the user
  does not know which document is wrong, use doc-sync instead.
license: MIT
---

# Doc revise

Change existing documentation surgically. The reader already relies on these docs, so the goal is the smallest change that satisfies the request while keeping the document's voice, structure, and correctness intact. The two failure modes are doing too little (leaving the doc internally inconsistent or its links broken) and doing too much (rewriting whole sections that were fine, flattening the author's voice). Aim between them. When the document does not exist yet and needs creating from scratch, use [`doc-author`](../doc-author/SKILL.md) instead. When the user does not yet know which document drifted, use [`doc-sync`](../doc-sync/SKILL.md) to find out first; it composes this skill's editing discipline when it applies an approved correction.

## Read before you edit

Read the target document in full, and read the neighbors it links to or that link to it, before changing anything. You cannot keep a set of docs consistent if you have only seen one. If the revision is about reflecting code or state changes, read the actual current code or state too, so the update is grounded and not a guess.

## Common revision shapes

Most requests are one of these. Recognize which, because each has a different risk.

- **Reconcile with reality**: the code or project moved and the doc is stale. Find the specific claims that drifted and correct just those. Do not rewrite passages that are still accurate.
- **Fix links and references after a move**: the user reorganized files or folders and references are now broken. This is common and mechanical: find every internal link and path reference across the affected docs, resolve each against the new locations, and update the broken ones. Verify, do not assume, that each target now exists at the path you wrote.
- **Keep a doc set consistent**: a change in one document implies changes in others (a renamed concept, a moved section, a new component). Propagate the change across all affected docs so they agree.
- **Move items between docs**: for example, completed items from a TODO into a CHANGELOG with a dated line, or an item from a roadmap into a task file. Preserve the entry's meaning, match the destination's format, and remove it cleanly from the source.
- **Targeted addition or formatting**: add a subsection, insert new content the user provides, add section emojis, adjust structure. Touch only what the request names.

## Preserve voice and structure

Match the document as it is. Reuse its heading style, its list conventions, its level of formality, its terminology. A good revision should be hard to spot as machine-made because it reads like the same author continued. Do not impose a template on a doc that already has a shape.

## Verify links after any structural change

Whenever you move content, rename a file, or touch references, do a link pass at the end: every internal link and relative path in the affected documents should resolve to a file that actually exists. Broken links are the most common and most silent way a revision goes wrong, and they are cheap to catch if you check.

## Conventions

Hold the repo's `AGENTS.md` and its house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)) on anything you touch or add: Mermaid over ASCII for new diagrams, sentence-case headings, clickable file links, no em-dashes. But do not go reformatting existing content that already reads fine just to enforce a convention the user did not ask about; keep the change scoped to the request.
