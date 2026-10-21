---
id: chore-0086
title: The live watcher retries a persistent failure forever and exposes no diagnosis, so a stale page still looks healthy
type: chore
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
touched_files:
  - scripts/observatory/serve.py
  - tests/test_observatory_serve.py
created: 2026-08-31
---

## Problem

`LiveWatcher._run` in [`serve.py`](../scripts/observatory/serve.py) survives anything its poll
raises, and says why:

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:                # noqa: BLE001
                # A watcher that dies takes live updates with it and leaves the page
                # looking correct, so it survives anything the corpus throws at it.
                pass
            self._stop.wait(self.poll_seconds)

The broad catch is correct and this task does not propose changing it. The gap is the second half of
the comment's own reasoning. A watcher that dies leaves the page looking correct; a watcher that
raises on every tick leaves the page looking correct too, and nothing anywhere reports it. The
failure repeats at the poll interval, produces no event, produces no log line, and reaches the page
as silence, which is what an idle corpus also looks like.

`poll_once` already converts the two failures it expects into `return None`, `db.StoreUnusable` and
`OSError`, so anything reaching this handler is by construction something nobody anticipated. That
is the case most worth being able to see.

This is the kit's own recurring failure class rather than a general observability wish.
[`SECURITY.md`](../SECURITY.md) lists "anything that silently does nothing while reporting success"
as reportable, and `bug-0050` is the recorded instance: the one hook this repository commits had
exited non-zero on every session start for twenty-two days, fourteen times, and was found by
counting rather than by anything reporting it.

Reported as the minor finding of the 2026-08-31 external review,
[`docs/reviews/2026-08-31-security-reliability-review.md`](../docs/reviews/2026-08-31-security-reliability-review.md).
Its suggested fix named the health report as a destination; see the out-of-scope note below for why
that is the wrong surface here.

## Scope

**In scope:** a persistent watcher failure becomes observable without becoming noise.

- Keep the retry. The loop must still survive every exception.
- Record the failure in a bounded, rate-limited form: one diagnostic for a repeating failure, not
  one per tick. Consecutive identical failures collapse into a count.
- Clear or supersede the record after a successful poll, so a transient failure does not read as an
  ongoing one.
- Write it to the server's own output, the surface `--quiet` already governs and that `serve` already
  prints its startup lines to.

**Out of scope:**

- **`/api/health`.** In this codebase that report is built by `health_report` from `health_event`
  rows, which are hook outcomes read out of the session corpus. A server-process error is a
  different kind of fact with a different provenance, and putting it there changes what the report
  claims to be. If it should eventually surface in the page, that is a contract question against
  `docs/spec/agent-observatory.md` and belongs to its own task.
- Narrowing the `except Exception`. The breadth is deliberate and load-bearing.
- Changing the poll interval, adding backoff, or stopping the watcher after N failures. A bound with
  no observed run behind it is a guess with a number on it, which is the reason
  [`feat-0042`](feat-0042-repeat-and-futility-classification.md) is still open rather than decided.
- Any change to `poll_once`, `corpus_fingerprint`, or `_drain_spool`. The equal-size skip that makes
  `poll_once` return `None` on a real change is `bug-0059` and is a different defect.

## Implementation notes

`ObservatoryServer` already carries a `quiet` flag and `log_message` honours it, so the rate-limited
diagnostic should honour it the same way rather than inventing a second suppression switch.

Identity for "the same failure" wants deciding rather than assuming. The exception type plus the
final traceback frame is enough to collapse a repeating failure and cheap to compute; the message
text alone is not, because a message carrying a path or a timestamp differs on every tick and
defeats the collapsing.

The test is about the loop, not about the log format. Drive `poll_once` to raise, let the loop turn
several times, and assert two things: the thread is still alive, and the diagnostic appeared **once**
rather than once per tick. A test that asserts on exact log text will break the first time the
wording is improved.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A test makes `poll_once` raise repeatedly and asserts the watcher thread is still alive
      afterwards, which is the existing behavior and must not regress.
- [ ] The same test asserts the failure produced **one** diagnostic across several ticks, not one per
      tick.
- [ ] A test asserts a successful poll after a failure clears or supersedes the recorded failure.
- [ ] The one-diagnostic assertion fails against the current code, which produces zero. Confirm
      before the fix.
- [ ] `--quiet` suppresses the diagnostic, consistent with the request log.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
