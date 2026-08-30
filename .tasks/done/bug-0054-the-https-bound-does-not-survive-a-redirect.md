---
id: bug-0054
title: The https bound applies to the recorded URL and not to what is actually fetched
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
  - SECURITY.md
created: 2026-08-29
---

## Problem

[`check-provenance.py`](../../scripts/check-provenance.py)'s `validate()` rejects an `http://` source at
line 427, and its comment states exactly why:

> Over plaintext the digest authenticates nothing, so the record would read as verified provenance
> for bytes anyone on the path could have written.

`fetch()` at line 450 then calls `urllib.request.urlopen`, which follows redirects by default. The
scheme check ran against the recorded string; nothing checks where the request ends up.

Reproduced 2026-08-29 on loopback, with no outbound traffic: two local servers, A answering `302
Location:` pointing at B.

```text
recorded source : http://127.0.0.1:17935/recorded
redirects to    : http://127.0.0.1:17934/t
fetch() returned: b'BYTES FROM THE REDIRECT TARGET, NOT FROM THE RECORDED SOURCE'
```

The caller is told nothing, and the digest it computes belongs to a URL the record does not name.

The scheme survives no better than the host. The standard library's own allow-list, in
`urllib.request.HTTPRedirectHandler.http_error_302` on the Python 3.11.10 this was run against, is:

```python
    if urlparts.scheme not in ('http', 'https', 'ftp', ''):
```

So an `https://` source answering `302 Location: http://...` is followed into plaintext, which is the
one thing `validate()`'s comment says must not happen.

**Why this is worth fixing now rather than in principle.** All nine destinations
`python scripts/check-provenance.py --list` prints today are `raw.githubusercontent.com`, so nothing
is exploitable against the current file. [`SECURITY.md`](../../SECURITY.md) line 20 already names the
shape that changes that: "a pull request can add a provenance block, and its `source:` URL is a
destination a maintainer's later run will contact from their machine." Accepting public
contributions is the event that makes this reachable, and it is the event this task is filed ahead
of.

`SECURITY.md` line 18 also states the property to a reader as absolute:

> **`https://` only, under a read bound.** A record pinning an `http://` source is reported as
> malformed rather than fetched, and a response over 10 MiB is reported as an error rather than read
> into memory whole.

The read bound half of that sentence is true and correctly built (`response.read(max_bytes + 1)`,
then compare, so a truncated read is distinguishable). The `https://` half describes what a record
may say, not what the script will talk to, and the sentence does not read that way.

## Scope

**In scope:** making the fetch refuse a non-`https` hop, reporting the final URL when it differs from
the recorded one, and correcting the `SECURITY.md` sentence to match the code once the code holds.

**Out of scope:**

- Certificate pinning, or any change to how TLS is verified. `urlopen` verifies by default and that
  is enough here.
- Refusing redirects outright. Upstream repositories legitimately redirect, and a checker that fails
  on a moved file gets disabled, which is the fate `AGENTS.md` already records for a network check
  that fails when GitHub is slow.
- The `--list` path, which fetches nothing and is correct as it stands.
- The 10 MiB read bound, which was tested and is correctly constructed.

## Implementation notes

Install a redirect handler rather than post-hoc checking. Subclass
`urllib.request.HTTPRedirectHandler`, override `redirect_request`, and return `None` (which raises
the original `HTTPError`) when `urlparse(newurl).scheme != "https"`. Build an opener from it and use
that opener in `fetch()` instead of the module-level `urlopen`. Checking after the fact is too late:
the plaintext request has already been made and answered.

`fetch()` should return the final URL alongside the bytes, and `check_record()` should treat a final
URL differing from the recorded one as reportable. A redirect to a different `https` location is not
an error, but it is drift in the thing the record pins, so it belongs in the message rather than
being swallowed into `ok`. The vocabulary already has `drift` and `error`; deciding which one a moved
location earns is the one design question here, and `drift` is the better fit because the recorded
`source:` genuinely no longer names what was retrieved.

`fetcher` is an injected seam in `check_record()`, so the tests can drive both the refusal and the
moved-location report without a network. `tests/test_check_provenance.py` already exercises that
seam; mirror how it does it rather than spawning servers, and use a loopback server only for the one
test that has to prove the real handler refuses.

## Decisions

- **A seam left open deliberately.** This does not stop a first-hop `https` server from returning
  arbitrary bytes. It cannot: fetching to digest means trusting the endpoint to be what the record
  names, and the digest is the only check on the content. What it closes is the narrower thing the
  code already claims, which is that the bytes were retrieved over a channel where the digest means
  something.
- **A departure from this task's own implementation notes.** They say to return `None` from
  `redirect_request`, which is urllib's documented way to decline and which re-raises the original
  `HTTPError`. That reaches a reader as "HTTP Error 302: Found" and says nothing about why a checker
  refused, which is the same complaint this repository has about a traceback standing in for a
  diagnosis. `InsecureRedirect` is raised instead. It is a `ValueError`, so it lands in
  `check_record()`'s existing `except` with no new branch, and it carries both URLs into the message.
- **A rejected alternative.** Changing every injected fetcher in `tests/test_check_provenance.py` to
  return the new two-field shape. Rejected because those tests are about parsing, placements, and
  digests, and none of them is about where the bytes came from; restating a field they do not care
  about in each would be noise that obscures what each test is actually pinning. `check_record()`
  takes either shape, and the tolerance is documented where it is implemented.
- **A stand-in that would have stopped standing in, caught rather than shipped.** `_fake_urlopen` in
  the test file patched `urllib.request.urlopen`. `fetch()` now calls `_OPENER.open`, so the patch
  would have gone on applying to a function nothing calls, and the three read-bound tests would have
  gone on passing over a response nobody served. That is the check-that-cannot-fail shape `AGENTS.md`
  names, arriving as a side effect of a change somewhere else, and it is the reason those three tests
  failed loudly here instead: the helper patches the opener now, and its docstring says why.
- **A classification decision, taken as the task proposed and worth restating.** A source that
  redirects to a different `https` location is reported `drift`, not `ok`, even when the bytes are
  identical. The record's `source:` no longer names what answered, and reporting `ok` would let a
  record sit on a redirect indefinitely, which is the rot this script exists to surface. It is worded
  as `MOVED` rather than sharing the content-drift wording, because the remedy differs: repoint the
  record, do not re-take the digest.
- **An outstanding verification, not performed.** The Risks section above says to verify against the
  real nine URLs by hand before closing. That is an outbound network run and the maintainer had
  scoped this session to no outbound traffic, so it has not been done. Everything mechanical is
  covered by the acceptance criteria, which do not require it, and `--list` still enumerates the same
  nine without contacting any of them. The one thing a real run would add is confirmation that no
  recorded source currently redirects, which would show as `MOVED` rather than as a failure.

## Risks and rollback

Touches the one script in the kit that makes network calls, and `SECURITY.md`, so it meets the
more-than-one-module rule. The failure direction is a handler that refuses a legitimate `https` to
`https` redirect and turns every run red, which is how a network check gets disabled. Verify against
the real nine URLs once, by hand, before closing.

Reversible by reverting one commit. Nothing persisted changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test proves an `https` source redirecting to `http` is refused rather than digested, driven
      through the real opener against a loopback server so it would fail if the handler were removed.
- [x] A test proves an `https` to `https` redirect still succeeds and reports the final URL when it
      differs from the recorded one.
- [x] A test proves the existing `http://` rejection in `validate()` still fires.
- [x] `SECURITY.md`'s bullet says what the code does, distinguishing the recorded-URL rule from the
      transport rule.
- [x] `python scripts/check-provenance.py --list` still fetches nothing and still prints nine
      destinations.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
