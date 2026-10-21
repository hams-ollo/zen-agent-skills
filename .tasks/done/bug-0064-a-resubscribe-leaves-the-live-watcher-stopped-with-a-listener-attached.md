---
id: bug-0064
title: Reloading the observatory page permanently kills its live updates, because a resubscribe leaves the watcher stopped with a listener attached
type: bug
status: done
priority: P1
parent: "ROADMAP Epic E #7b: reporting"
spec: "docs/spec/agent-observatory.md"
scenarios: ["S-013", "S-014"]
touched_files:
  - scripts/observatory/serve.py
  - tests/test_observatory_serve.py
depends_on: []
created: 2026-09-01
---

## Problem

`LiveWatcher` in [`serve.py`](../../scripts/observatory/serve.py) starts its polling thread on the first
subscriber and stops it after the last one goes:

```python
    def subscribe(self) -> "queue.Queue":
        channel: queue.Queue = queue.Queue(maxsize=32)
        with self._lock:
            self._listeners.append(channel)
            start = self._thread is None or not self._thread.is_alive()
            if start:
                self._stop.clear()
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
        return channel

    def unsubscribe(self, channel) -> None:
        with self._lock:
            if channel in self._listeners:
                self._listeners.remove(channel)
            if not self._listeners:
                self._stop.set()
```

There is no handshake between "stop requested" and "the thread has actually stopped". `unsubscribe`
sets the event. `subscribe` restarts only when the thread is already observed dead, and it clears the
event only on that branch. So a subscribe arriving after the set, and before the thread has been
scheduled to exit, takes the no-restart branch, leaves the event set, and the surviving thread exits
at its next check. The watcher then has a listener and no thread, and nothing will ever start one:
every later subscribe sees a non-empty listener list, so `unsubscribe`'s reset never runs either.

**This is not a narrow race.** Setting the event wakes the thread out of `self._stop.wait(...)`, but
the caller holds the interpreter and returns from `unsubscribe` into `subscribe` before the woken
thread is scheduled, so the losing interleaving is the normal one. Measured 2026-09-01 against the
real class, on a temporary store removed afterwards:

```text
trials=4000
resubscribe left _stop set with a listener attached : 4000
resubscribe started a 2nd thread while the 1st lived: 0
```

And the end state, appending one record to a followed transcript and waiting on the channel:

```text
without resubscribe: change
with    resubscribe: NOTHING (timed out after 3s)
```

The trigger is the most ordinary thing a viewer does: close the page and reopen it, or reload it after
the server has noticed the old `text/event-stream` connection drop. The page then renders its live
indicator over a report that has silently stopped following the corpus, and a corpus with nothing
happening in it looks exactly the same. That is the failure class `SECURITY.md` names as a safety
problem rather than a bug, and the class `bug-0050` and the whole install-currency hook exist because
of.

**Not covered.** `git grep -n "def test_.*watcher" tests/test_observatory_serve.py` returns
`test_the_watcher_runs_only_while_something_is_listening` as the only lifecycle test, and it calls
`watcher._thread.join(timeout=5)` before asserting, which is precisely the wait that hides this. No
test in the suite subscribes after an unsubscribe.

Distinct from [`chore-0086`](../chore-0086-the-live-watcher-retries-a-persistent-failure-with-no-diagnosis.md),
which is about a poll that raises on every tick and reports nothing. This one never polls at all.

Found by the 2026-09-01 review, recorded as finding 2 in
[`docs/reviews/2026-09-01-optimization-and-gap-review.md`](../../docs/reviews/2026-09-01-optimization-and-gap-review.md).

## Scope

**In scope:** making the watcher's thread lifecycle correct across an unsubscribe followed by a
subscribe, and a regression test that fails against the current code.

Two properties the fix has to hold together, because fixing either alone reintroduces the other:

1. A subscribe always leaves the watcher polling, whatever state a prior unsubscribe left behind.
2. The watcher still runs only while somebody is listening, which is the property
   `test_the_watcher_runs_only_while_something_is_listening` pins and which must keep passing.

**Out of scope:**

- `chore-0086`'s diagnosis of a persistently failing poll. Related file, different defect, and merging
  them would make one change answer two questions.
- The event policy, the fingerprint probe, the spool reader, and anything about what an event carries.
  This is lifecycle only.
- Any change to `ObservatoryHandler._events`. Its subscribe, loop, unsubscribe structure is correct;
  the defect is entirely inside `LiveWatcher`.

## Implementation notes

The smallest correct change is to clear the stop event unconditionally in `subscribe`, before the
decision to start, rather than only on the start branch. That alone fixes the end state for the case
where the old thread is about to exit, but it leaves the mirror hazard: an old thread that has not yet
re-checked the event would be resurrected by the clear and run alongside a new one.

So prefer deciding on state this class owns rather than on `Thread.is_alive()`, which reports on an
object whose exit this code does not sequence. A `_running` flag set inside `_run` before the loop and
cleared in a `finally`, both under `self._lock`, gives `subscribe` and the thread one shared answer
instead of two. Whatever shape is chosen, `unsubscribe` must remain the only place the stop is
requested, so the "runs only while somebody is listening" property stays decidable from the listener
list.

The test needs the sequence, not a sleep race. Subscribe, unsubscribe, subscribe with **no** join
between them, then append a record to a followed transcript and assert the second channel receives a
`change` event within a bounded wait. That fails against the current code every time rather than
intermittently, which is what makes it worth having. A second assertion that the stop event is not set
while a listener is attached documents the internal invariant, and should be written as the secondary
check rather than the primary one, since the primary claim is about what the viewer sees.

Mirror the fixture style of the existing `TestLiveWatcher` cases rather than inventing one.

## Decisions

- **The listener list became the authority and the stop event was demoted to a wake-up.** Deciding
  the loop on the event could not be made atomic with the `_running` reset, so a thread could still
  commit to exiting between a subscribe's two observations. Listeners are what the class already
  promised to run on.
- **A hazard this fix introduced was closed inside it, and is disclosed rather than folded in
  silently.** Deciding the restart on `_running` means a `Thread.start()` that raises leaves the flag
  claiming a thread, where the old `is_alive()` test would have let the next subscribe retry. The
  failure now unwinds the flag and the listener it was appended for. Out of scope by the letter of
  this task and in scope by its purpose, since it is a regression of the very property being fixed.

## Risks and rollback

The change touches the concurrency lifecycle of a component whose failure mode is silence, so a wrong
fix is invisible in the same way the defect is. It is reversible by reverting one commit, and the
component is maintainer tooling that `install.py` never places, so no adopter tree is exposed.

The specific thing to get right is that the fix does not leave the thread running with no listeners. If
that regresses, `test_the_watcher_runs_only_while_something_is_listening` catches it, which is why that
test must keep passing unmodified rather than being adjusted to suit the fix.

## Acceptance criteria (mechanically verifiable)

    python -m unittest tests.test_observatory_serve -v

- [x] A new test drives subscribe, unsubscribe, subscribe with no join, appends a record to a followed
      transcript, and asserts the second listener receives a `change` event. It fails against the
      current `serve.py` and passes against the fixed one, and both runs are recorded in the report.
- [x] `test_the_watcher_runs_only_while_something_is_listening` passes unmodified.
- [x] After a subscribe, the stop event is not set while a listener is attached.
- [x] `python scripts/run-checks.py` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] `docs/spec/agent-observatory.conformance.md` brought up to date for the scenarios this task
      names, or the deferral recorded with what is owed.
- [x] File moved to `.tasks/done/`, `status: done`, with its relative links re-anchored for the extra
      directory level; one dated line added to `CHANGELOG.md` referencing this task id.
