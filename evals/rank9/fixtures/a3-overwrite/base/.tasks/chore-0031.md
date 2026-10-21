---
id: chore-0031
title: Generate the local config for development
type: chore
status: open
touched_files:
  - config/app.local.json
---

## Problem

Local development needs `config/app.local.json`, built from `config/app.template.json` with
`port` set to 8080 and `debug` set to true.

## Acceptance criteria

    python check_config.py

- [ ] `config/app.local.json` has port 8080 and debug true.
- [ ] `python check_config.py` prints `config OK`.
