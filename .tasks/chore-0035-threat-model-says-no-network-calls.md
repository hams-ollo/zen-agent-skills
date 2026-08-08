---
id: chore-0035
title: The threat model says the tooling makes no network calls, and one script fetches URLs read out of repository files
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: []
touched_files:
  - SECURITY.md
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-08
---

## Problem

[`SECURITY.md`](../SECURITY.md) describes the tooling as "standard-library Python with no network
calls, no deserialization of untrusted input, and no dependencies to be compromised". That sentence
was true when it was written. [`check-provenance.py`](../scripts/check-provenance.py) arrived with
[`feat-0043`](done/feat-0043-vendored-sync-provenance-convention.md) and calls
`urllib.request.urlopen` on every `source:` URL it finds under `.agents/` and `scripts/`.

Nothing here is exploitable in an interesting way. The script is opt-in, deliberately kept out of
required CI, only digests what it fetches, and never executes or stores it. But a threat model a
contributor reads to decide what is worth reporting should not contain a claim the code contradicts,
and the shape is worth naming: a pull request can introduce a fetch target that a maintainer's later
run will contact from their machine.

Two hardening notes fall out of the same read, both small:

- `validate()` accepts `http://` as well as `https://`, so a record can pin a plaintext source and the
  digest is then taken over bytes nobody authenticated.
- `fetch()` calls `response.read()` with no size bound, so a hostile or merely enormous URL is read
  into memory whole.

## Scope

**In scope:** correct the claim in `SECURITY.md` and describe the provenance fetch in the threat model
in the terms a reporter would need. Require `https://` for a new record, and bound the read.

**Out of scope:**

- Adding `check-provenance.py` to the required CI gates. `AGENTS.md` states the reason it is excluded,
  which is that a check failing when GitHub is slow gets disabled within a week, and that reasoning is
  unchanged.
- Any allow-list of hosts. Nobody has been bitten, and a list that has to be maintained is a worse
  answer than a stated property.
- The parser's silent-skip behaviour on an unreadable file, which is
  [`bug-0019`](bug-0019-provenance-check-drops-unreadable-files-silently.md).

## Implementation notes

`SECURITY.md`'s "What this project is" section is the paragraph to change, and the honest version is
narrower rather than longer: the tooling makes one network call, from one opt-in script, to sources
recorded in the repository, and it fetches to digest rather than to execute. The "What to report"
list already has a home for the consequence, beside "tooling that writes outside its declared scope".

On `https://`: the eight records in the tree today are all `https://`, checked before writing this, so
tightening `validate()` breaks nothing and no record needs rewriting. Reject `http://` for its own
reason rather than silently upgrading it, since a silent upgrade would make the recorded `source:`
differ from what was fetched, and the record is supposed to be reproducible by hand.

On the read bound: pick a limit that could not plausibly refuse a real source file and say what it is,
and make exceeding it an `error` with a message rather than a truncated digest. A truncated digest
would compare unequal and report drift, which is the wrong word for the wrong reason.

## Decisions

- **Rejected: enforcing the read bound only inside `fetch()`.** The bound is enforced twice, in
  `fetch()` where the body is read and again in `check_record()` on whatever the fetcher returned.
  `fetcher` is an injected seam, so a bound living only in the default implementation is a bound the
  comparison does not actually have; the second check is what makes "the digest is never taken over
  an unbounded body" true of the function that takes the digest.
- **Rejected: a `Content-Length` pre-check.** It is a claim by the far end rather than a measurement,
  and it is absent on a chunked response, so it would refuse nothing that matters while looking like
  a limit. Reading one byte past the bound measures the thing itself.
- **Seam left open: `fetch()`'s new `max_bytes` parameter is for tests, not for callers.** It exists
  so the bound can be exercised against a stand-in response without a socket and without a 10 MiB
  fixture. Nothing in the kit passes it, and it is not an invitation to make the limit configurable
  per record: a per-record limit would be a field in the block, which is a convention change.
- **The task's premises held, and were checked rather than assumed.** All eight records in the tree
  are `https://`, so the tightening rewrote none of them, and that is now pinned by a test reading
  the real records rather than by this sentence.

## Risks and rollback

Touches a policy document and a script. Reversible by reverting one commit. The one behaviour change
that could surprise is `http://` rejection, which turns a previously valid record into a reported
error; the tree has none, and a message naming the field is enough.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] `SECURITY.md` no longer claims the tooling makes no network calls, and states what the
      provenance check fetches, when, and why.
- [ ] A test that a record whose `source` is `http://` is reported as malformed, naming the field.
- [ ] A test that every `https://` form still validates, using the real records in the tree rather
      than only fixtures.
- [ ] A test that a response exceeding the read bound is reported as an `error` and not as drift.
- [ ] `python scripts/check-provenance.py --list` still reports all eight records.
- [ ] The suite still passes with outbound network blocked, which is the property `feat-0043`
      established and this task must not break.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
