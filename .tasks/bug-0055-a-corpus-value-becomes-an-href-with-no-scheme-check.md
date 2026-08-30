---
id: bug-0055
title: A corpus-supplied pr_url becomes an href with no scheme check, so one click runs script in the report's origin
type: bug
status: open
priority: P1
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
spec: "docs/spec/agent-observatory.md"
scenarios: [S-019, S-022]
touched_files:
  - scripts/observatory/ui/index.html
  - scripts/observatory/ingest.py
  - tests/test_observatory_serve.py
created: 2026-08-29
---

## Problem

[`index.html`](../scripts/observatory/ui/index.html) line 317, inside `actionControl()`, builds the
`open-pr` control:

```javascript
      "data-action": action.id, href: value, target: "_blank",
```

`value` is `row[action.field]`, and `open-pr`'s field is `pr_url`. That value is unvalidated at every
hop. [`ingest.py`](../scripts/observatory/ingest.py) line 199 stores it verbatim from the transcript:

```python
            (sid, project, rec.get("prNumber"), rec.get("prUrl")),
```

Confirmed end to end on 2026-08-29, against a scratch corpus and a scratch store, on a scratch port.
A transcript carrying a `pr-link` record whose `prUrl` was a `javascript:` URI:

```text
--- what the store now holds ---
('00000000-1111-2222-3333-444444444444', 80,
 "javascript:fetch('/api/sessions').then(r=>r.text()).then(...)")

/api/fleet: HTTP 200 | 'javascript:' in response: True
   served verbatim ->    "pr_url": "javascript:fetch('/api/sessions')...
```

The page then sets that string as the `href` of a link labelled "Pull request". Following it runs
script in the report's own origin, which can read every route on the server: session ids, project
names, working directories, branches, and the whole cost and health corpus. That is the same asset
`host_is_loopback()` was written to protect, described in its own docstring as "one maintainer's
entire session history".

**Why this is the finding rather than a symptom.** Every other sink on this page is handled
correctly, which is what makes the single exception worth reporting. There is not one use of
`innerHTML` in the file; text reaches the DOM through `textContent`; `rel="noreferrer noopener"` is
set on this very anchor with a comment explaining why. This is the one place a corpus value reaches
an interpreted context, and it is the one place nothing checks it.

**The trust boundary it sits on.** The transcript is written by the harness on the maintainer's own
machine, so a hostile `prUrl` has to arrive through whatever put a URL in front of that session. That
chain was not established and this task does not claim it. What is established is that the value is
unvalidated at all three hops and that the sink executes, which is `A10`'s class present in this
repository's own code rather than in a scenario.

## Scope

**In scope:** refusing a non-`http`/`https` scheme where the control is built, and a test that pins
it.

**Out of scope:**

- Sanitising at ingest. The store should keep what the corpus said, because the store is a record of
  the corpus and rewriting it there would make the ingester lie about what it read. The check belongs
  at the sink.
- Adding a Content-Security-Policy header, which is worth doing and is filed separately as
  [`chore-0082`](chore-0082-four-small-items-from-the-2026-08-29-pre-publication-review.md) item 4.
  It is defence in depth for this, not the fix for it.
- Any change to `ACTIONS` or to the `S-019` enumeration claim. This adds no control and removes none.
- The `copy-command` kinds, which put text on a clipboard and reach no interpreter.

## Implementation notes

Do it in `actionControl()`, at the one construction site the page already routes every control
through, so the check is as derivable as the enumeration the surrounding comment defends.

Parse rather than pattern-match: `new URL(value, window.location.href)` inside a `try`, then accept
only `protocol === "http:" || protocol === "https:"`. A `startsWith("http")` test passes
`httpx://` and fails a legitimate uppercase scheme, and `javascript:` can be spelled with embedded
newlines and tabs that a naive prefix test does not see but the URL parser normalises away.

When the scheme is refused, render the value the way the file already renders a command it cannot
put on a clipboard: as a `code` element carrying the text. The viewer still sees what the corpus
recorded, and nothing is silently dropped, which matters because the report's whole contract is that
it shows what the corpus holds.

`tests/test_observatory_serve.py` already builds stores and drives routes. The page itself is not
under test today, so the test for this asserts the server-side half (the value survives to
`/api/fleet` unchanged, which is deliberate) and the page-side half needs either a small parser test
over the emitted HTML or a documented gap. Prefer the first; do not pin the second as acceptable
without saying so.

## Decisions

- **A rejected alternative.** Blocking the value at ingest was considered and rejected. The store is
  a record of what the corpus said, `ingest.py` is careful elsewhere to record rather than
  interpret, and a sanitising ingester would make `/api/fleet` disagree with the transcript it
  claims to summarise. The sink is where the interpretation happens and is where the check belongs.

## Risks and rollback

Touches the page and the test suite. The failure direction is a check strict enough to refuse a real
pull request URL, which would remove a working control and be noticed only by someone who expected a
link. Verify against a real `pr_url` from the live store before closing.

Reversible by reverting one commit. No persisted format changes; the store keeps exactly what it
keeps today.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A `javascript:` value in `pr_url` does not become an anchor `href`. Drive it from an ingested
      transcript rather than from a hand-built row, so the test covers the path the defect took.
- [ ] A `data:` value is refused by the same route, proving the check is a scheme allow-list and not
      a `javascript:` denylist.
- [ ] An ordinary `https://github.com/...` value still renders as a followable link carrying
      `rel="noreferrer noopener"`.
- [ ] A refused value is still visible to the viewer as text rather than dropped.
- [ ] `/api/fleet` still returns the stored value unchanged, so the store and the report remain a
      record of the corpus.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `agent-observatory` conformance matrix is brought up to date for `S-019` and `S-022`, or the deferral is recorded.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
