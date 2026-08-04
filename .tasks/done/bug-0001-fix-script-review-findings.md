---
id: bug-0001
title: Fix the code-review findings in the kit scripts
type: bug
status: done
priority: P1
parent: "ROADMAP: kit tooling quality (surfaced by code-review dogfood)"
depends_on: []
touched_files:
  - scripts/install.py
  - scripts/build-adapters.py
created: 2026-07-24
---

## Problem

Dogfooding the `code-review` skill on the kit's Python scripts surfaced real findings:

- **major** [`scripts/install.py:119`](../../scripts/install.py): copy-mode symlink-ownership uses a
  string-prefix test (`str(points_to).startswith(str(src.resolve()))`) instead of path equality, so
  a symlink whose resolved target is a string prefix of a skill path (a sibling with a prefix name)
  is misclassified as ours, unlinked, and replaced. Violates the "never clobbers a file it did not
  create" promise.
- **minor** [`scripts/build-adapters.py`](../../scripts/build-adapters.py): the skill `description` is
  interpolated raw into generated YAML frontmatter, so a description with a YAML-significant
  sequence would emit a malformed adapter.
- **minor** [`scripts/install.py:174`](../../scripts/install.py): in `uninstall()`, `remaining` is
  passed to `save_manifest` but never appended to (dead, misleading code).
- **minor** [`scripts/install.py:126`](../../scripts/install.py): copy-mode idempotency silently
  relies on the manifest; a lost manifest turns re-runs into CONFLICTs (undocumented).
- **nit** [`scripts/install.py:66`](../../scripts/install.py): `is_managed` assumes every manifest
  entry has a `target` key.

## Scope

**In scope:** fix `install.py` (exact path equality for symlink ownership; drop the dead `remaining`
and make the manifest-clear explicit; `is_managed` uses `.get`; document the copy-mode manifest
dependency in the module docstring) and `build-adapters.py` (emit the description as a safely
serialized YAML scalar via `json.dumps`, adding the `json` import).

**Out of scope:** iterating the `code-review` skill (that is `feat-0008`); rewriting the installer's
manifest design; adding a marker-file ownership scheme.

## Implementation notes

- `install.py:119` becomes `if points_to == src.resolve():` (mirrors the symlink-mode branch and
  handles `points_to is None`).
- `build-adapters.py` `emit_cursor`/`emit_vscode` use `description: {json.dumps(desc)}` (valid YAML).

## Acceptance criteria (mechanically verifiable)

    python scripts/build-adapters.py --dry-run && python scripts/install.py --dry-run && python scripts/validate-skills.py

- [ ] `install.py` uses `points_to == src.resolve()` (no `startswith`), `is_managed` uses `.get`,
      and `uninstall` no longer carries a dead `remaining` variable.
- [ ] `build-adapters.py` serializes the description with `json.dumps` and imports `json`.
- [ ] All three commands above exit 0.
- [ ] A re-run of `code-review` on the scripts no longer reports the major or the two code-level
      minors.

## Definition of done

- [ ] Acceptance commands pass locally.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated `CHANGELOG.md` line referencing this id.
