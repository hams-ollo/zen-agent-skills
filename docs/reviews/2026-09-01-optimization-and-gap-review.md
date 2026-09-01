# Optimization and gap review, 2026-09-01

This report records a third review of Zen Agent Skills for the maintainer. It was asked as an open
question rather than a scoped audit: what would optimize and refine the toolkit, what tools are worth
adding to the roadmap, and what issues are worth resolving.

Reviewed at `b250c44ed8ed5b243813ee4fd8c70904ab4d8ce8` on branch
`claude/2026-09-01-wave-0088-0089`, against
[`review-quality.md`](../../.agents/rules/review-quality.md).

The review began against that wave's work uncommitted and it was committed underneath the pass, at
`295578a` and `b250c44`, which is recorded rather than smoothed over because it is the hazard `A9`
exists for. It changed nothing here: no finding below touches a file those two commits modify, and
every quote was re-resolved against the tree at `b250c44` after they landed. The only files this pass
adds are this report and the task files it produced.

Report only. Nothing here was fixed. The findings are filed as task files and named at the end.

## Verdict

**The mechanical layer is in the best shape any of the three reviews has found it, and the two
defects worth acting on this week both live where this repository has already written down that it
cannot see.**

The prior two reviews went at hostile input and at trust boundaries. Both grounds are now well
covered: containment is enforced at the write boundary, the loopback surface refuses a rebound `Host`
before routing, every hook fails open, and the rule with four copies has two of them held together by
a test. Trying those grounds again produced three candidates and all three were withdrawn on
inspection, which is a result rather than an absence.

What produced findings instead was the list this repository keeps of what its own gates cannot reach.
The conventions section of [`AGENTS.md`](../../AGENTS.md) states it plainly: every gate decides a
mechanical property, and the defects that have hurt most sat outside all of them. Three of the four
findings below sit exactly there. One is a claim in prose that no gate reads. One is in JavaScript,
which the suite has no runtime for and says so. One is a concurrency lifecycle whose only test defeats
itself by waiting.

The most consequential is not any of the code defects. It is that **`SECURITY.md` currently tells a
security researcher that the kit has no answer to prompt injection**, five days after `A10` landed and
after every skill was wired to the module carrying it. The kit's posture on its highest-consequence
rule is stated backwards in the one document written for people who might test it.

The optimization question has a different answer from the defect question, and it sits in its own
section rather than here because it is a judgment for the maintainer rather than a finding: this kit
is now 9 percent of its own repository, and nothing measures that ratio.

## What was reviewed, and what was not

Read in full: the three rules modules, all 22 skill bodies at the frontmatter and structural level,
the five hooks, the six distribution scripts, the observatory (store, ingester, server, page), the CI
workflow, and the reader-facing document set (`README.md`, `SECURITY.md`, `CONTRIBUTING.md`,
`AGENTS.md`, `ROADMAP.md`, `docs/CATALOG.md`, `docs/GETTING-STARTED.md`).

Run, all read-only: `validate-skills.py`, `.tasks/validate.py --strict`, and `install.py --check`. The
first reports one warning across 22 skills, on `test-quality`'s shape, which `AGENTS.md` already
records as left standing deliberately. The second is clean, at 221 task files once this pass's four
are counted. The third reports 38 current against 6 diverged, the six being the copies the wave moved
ahead of the install record, which is the currency sensor working rather than a finding.

**Not done, and stated because the bound is the useful part.** No skill's behavior was exercised on
real work. This pass read procedures and did not run them, so it says nothing about whether
`house-review` reviews well or whether `spec-plan-readiness` gates correctly. That is Epic A item 8's
recurring question and Epic E item 6's suite, and neither is answered here.

## Findings

Ordered by severity. Every finding was resolved against the file it cites before being written down.

**No candidate was dropped by the evidence gate.** Three were investigated and withdrawn before
reaching this list, and they are named rather than left silent, because a reviewer whose candidates
routinely fail to resolve is one to distrust and that is invisible if withdrawals leave no trace.

| Withdrawn candidate | Why |
| --- | --- |
| The two `validate.py` copies can diverge | Not silently. `ValidatorCopiesAgreeTests` compares whole module ASTs. Confirmed independently: 14 functions each, zero body differences, prose differs by design. The unguarded copies are the link helpers in `validate-skills.py` and `build-adapters.py`, already open as `chore-0059`. |
| `host_is_loopback` accepts a suffixed name | It does not. `localhost.evil.com` and `127.0.0.1.evil.com` both reach `ipaddress.ip_address`, raise, and return `False`. Fails closed. |
| A skill body can inject frontmatter into an adapter | It cannot. `emit_cursor` and `emit_vscode` serialise the description with `json.dumps`, and the body is appended after the closing delimiter, where `---` is a horizontal rule. |

### Blocker

#### 1. The security policy denies a rule the kit ships and every skill carries

`blocker|SECURITY.md|docs|security-policy-denies-the-prompt-injection-rule`

| Field | Evidence |
| --- | --- |
| path | `SECURITY.md` |
| lines | 32 |
| symbol | "What to report" |

```text
- **Prompt-injection paths**, where content a skill is designed to read (a diff, an issue body, a
fetched page, a file in the target repo) can redirect the agent's behavior. No skill or rules module
here addresses this class yet: it is recorded as held, with its trigger, in the held section of
[`.agents/rules/autonomy.md`](.agents/rules/autonomy.md), so a report of one is new ground rather
than a broken promise.
```

Every clause after the colon has been false since 2026-08-27. `A10` is a full rule in the module, and
the held entry this sentence points at now opens by recording that it was discharged as `A10` on that
date. Measured on 2026-09-01: `grep -rl "autonomy.md" .agents/skills/*/SKILL.md | wc -l` returns 22,
against 22 skill directories, so the module reaches every one of them.

The consequence is not cosmetic, because this is the document that tells a researcher which promises
exist. It inverts the answer in the direction that costs most: a prompt-injection path in a skill is
now **a broken promise**, and this page tells whoever found it that it is new ground. It also
undersells the kit to every reader deciding whether to adopt it, since `A10` is the strongest safety
claim here and the security policy disclaims it.

**Why nothing caught it.** `SECURITY.md` is reader-facing, so the closeout lifecycle in `AGENTS.md`
put it inside the `doc-sync` step, and `chore-0071`, the task that discharged the held entry, did not
reach it. Nothing else could: no gate reads a prose claim, and this is precisely the
drift-between-changes class Epic B item 19 was filed for on 2026-08-18. It is the same shape as
`feat-0031`, whose closeout produced a conformance matrix and a verification record and left every
reader-facing document silent.

Worth noting for its own sake: the 2026-08-29 review found `A10` failing to reach the skills, and
`feat-0064` fixed that half. The document describing the rule's absence was not part of that fix, so
the correction moved the fact and left the claim about it behind.

**Suggested fix:** rewrite the item to say that `A10` governs this class, name what it does and does
not promise (it constrains the action, it is deliberately not a detector, and the reasoning behind
that choice is in the module), and keep the invitation to report a path that gets around it. Since
this claim inverted once with nothing noticing, prefer stating in the task what would catch a future
inversion over adding a gate this pass did not scope.

#### 2. Reloading the observatory page permanently kills its live updates

`blocker|scripts/observatory/serve.py|correctness|resubscribe-leaves-the-watcher-stopped`

| Field | Evidence |
| --- | --- |
| path | `scripts/observatory/serve.py` |
| lines | 2097 to 2113 |
| symbols | `LiveWatcher.subscribe`, `LiveWatcher.unsubscribe` |

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
sets the event; `subscribe` restarts only when the thread is already observed dead, and clears the
event only on that branch. A subscribe arriving after the set and before the thread has been scheduled
to exit therefore takes the no-restart branch, leaves the event set, and the surviving thread exits at
its next check. The result is a listener attached to a watcher that will never poll again.

**This is not a narrow race.** Setting the event wakes the thread out of its wait, but the caller holds
the interpreter and returns from `unsubscribe` into `subscribe` before the woken thread is scheduled,
so the losing interleaving is the normal one. Measured on 2026-09-01 against the real class, on a
temporary store removed afterwards:

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

The trigger is the most ordinary thing a viewer does. Closing the page and reopening it, or reloading
it after the server has noticed the old stream drop, produces exactly this sequence. The page then
renders its live indicator over a report that has silently stopped following the corpus, which looks
identical to an idle corpus. That is the failure class `SECURITY.md` names as a safety problem rather
than a bug, and the one `bug-0050` and the whole install-currency hook exist because of.

**Not covered.** `git grep -n "def test_.*watcher" tests/test_observatory_serve.py` returns
`test_the_watcher_runs_only_while_something_is_listening` as the only lifecycle test, and it calls
`watcher._thread.join(timeout=5)` before asserting, which is precisely the wait that hides this. No
test in the suite subscribes after an unsubscribe.

Distinct from open
[`chore-0086`](../../.tasks/chore-0086-the-live-watcher-retries-a-persistent-failure-with-no-diagnosis.md),
which is about a poll that raises on every tick. This one never polls at all.

**Suggested fix:** clear the stop event unconditionally in `subscribe` before deciding whether to
start, and decide on state the class owns rather than on `Thread.is_alive()`, which reports on an
object whose exit this code does not sequence. A test drives subscribe, unsubscribe, subscribe with no
join and asserts the second listener receives an event; it fails against the current code every time
rather than intermittently.

### Minor

#### 3. A recorded path is used as a regular-expression replacement pattern

`minor|scripts/observatory/ui/index.html|correctness|corpus-value-used-as-a-replacement-pattern`

| Field | Evidence |
| --- | --- |
| path | `scripts/observatory/ui/index.html` |
| lines | 345 |
| symbol | `actionControl` |

```js
  var text = action.template.replace("{" + action.field + "}", value);
```

`value` is the replacement argument, so ECMA-262's `GetSubstitution` interprets a dollar-sign escape
inside it rather than inserting it literally. `value` is `row[action.field]`, and the `copy-cwd`
action's field is `cwd`, a working directory the corpus recorded and this repository did not write.
Both characters in the shortest such escape are legal in a path on every platform the kit targets.

Measured on 2026-09-01, with the escape written into a path and the backslashes elided by the shell:

```text
template : {cwd}
value    : D:work$&stuff
result   : D:work{cwd}stuff
expected : D:work$&stuff
```

The impact is bounded and worth stating rather than inflating. The observatory is maintainer tooling
that `install.py` never places, the output reaches the page as a text node rather than as markup, so
this is not the `bug-0055` class, and the other two actions are safe today: `copy-resume` takes a
session UUID, and `open-pr` takes the navigate branch and never reaches this line. What it does is
hand the viewer a silently wrong path, from the one control whose entire job is handing them a correct
one.

**Not covered, and structurally so.** The suite reads this file as text by design: a test asserts
`node_modules` is never introduced, and `followable_url`'s docstring gives that as the reason the
scheme check lives in Python rather than on the page. No test here can execute this line.

**Suggested fix:** split on the token and join with the value, which performs no substitution and
gives the path back unchanged, or pass a function replacer. The test has to respect the no-runtime
bound and assert on the construction rather than the behavior, and should say so in its own body so a
later reader does not mistake it for a behavioral test.

#### 4. The description-budget figures are stale, and the claim they support is measurably wrong

`minor|ROADMAP.md|docs|stale-description-budget-figures-and-wrong-collision-cluster`

| Field | Evidence |
| --- | --- |
| path | `ROADMAP.md` |
| lines | 128 and 463 |
| symbols | Epic E item 6; "Out of scope by design" |

```text
with twenty skills whose descriptions average 759 characters and overlap heavily in vocabulary
(`spec-author` / `spec-quality` / `spec-plan-readiness` / `spec-conformance`, `doc-author` /
`doc-revise` / `doc-sync`, `test-author` / `test-quality`), the likeliest failure is not a skill
behaving wrongly but the wrong skill being selected
```

Both halves have drifted, and the second matters more than the first.

The counts, measured on 2026-09-01 through `install.description_of`, which is the reader the installer
itself uses, so this and the budget report cannot disagree: 22 skills discovered, two of them drafts,
17,197 characters across all of them at a mean of 782, and 15,317 across the 20 that ship at a mean of
766. A count written in prose beside the thing it counts is the case
[`house-style.md`](../../.agents/rules/house-style.md) forbids by name, and this is another instance
of it, in a sentence nothing recomputes.

The cluster claim is the part worth correcting, because it is the stated design input for an unbuilt
item. Jaccard similarity over content words in the descriptions, stop words removed:

| Pair | Overlap |
| --- | --- |
| `agent-handoff` / `human-handoff` | 0.236 |
| `doc-author` / `doc-revise` | 0.231 |
| `test-author` / `verifier-agent` | 0.196 |
| `fix-batch` / `reconcile-worktrees` | 0.180 |
| `init-worktracking` / `new-task` | 0.162 |
| `spec-author` / `spec-quality` | 0.139 |

Mean pairwise overlap across every pair is 0.046, so the top of that table sits four to five times
above the field. The `spec-*` family, named as the worst case, is well separated except for one pair.
The two families the sentence lists second and third are the real collisions, and one pair the
sentence never names, `test-author` against `verifier-agent`, ranks third. A trigger-disambiguation
suite built to the stated priorities would spend its fixtures on the wrong cluster.

**Suggested fix:** replace both figures with the measurement and its date, correct the cluster list
from the table above, and consider whether these numbers should be computed rather than written, which
the proposals below return to.

## Structural analysis

The findings above are defects. This section is about shape, and none of it is a defect: it is four
measurements and what they imply, offered because the question asked was what to optimize.

### The kit is 9 percent of its own repository

Tracked bytes on 2026-09-01, by area:

| Area | Bytes | Share |
| --- | --- | --- |
| `.tasks/` | 1,722,317 | 34% |
| `tests/` | 1,067,397 | 21% |
| `docs/` | 761,691 | 15% |
| `scripts/` | 508,441 | 10% |
| `CHANGELOG.md` | 371,008 | 7% |
| `.agents/` (the deliverable) | 455,010 | 9% |
| `ROADMAP.md` | 92,170 | 2% |

The apparatus is not overhead here. Evidence discipline is what this kit sells, the specs and
verification records are cited in the README as the reason to trust it, and the tests are why the
mechanical layer keeps coming back clean. So the ratio is not wrong in itself.

What is worth naming is that **nothing measures it, and every mechanism the kit adds increases the
denominator.** A new skill brings a spec, a conformance matrix, a verification record, a test module,
several task files, and changelog lines. That compounding is the intended design. It is also why a
number nobody watches is the kind that surprises you, and this repository's whole method is to prefer
a measurement over a memory.

### `AGENTS.md` is the largest fixed cost in the reading protocol

Section 0 instructs every agent to read this file in full before anything else. It is 30,496 bytes,
roughly 7,500 tokens, spent before the agent has opened its task file or a single source file.

| Section | Bytes | Share |
| --- | --- | --- |
| 6. Conventions | 13,093 | 42.9% |
| 4. How a skill is structured | 5,623 | 18.4% |
| 2. Layout | 3,476 | 11.4% |
| 3. Work altitude model and lifecycle | 3,187 | 10.5% |
| 5. Portability contract | 2,238 | 7.3% |
| 1. What this repository is | 1,107 | 3.6% |
| Preamble | 772 | 2.5% |
| 0. Agent reading protocol | 595 | 2.0% |
| 7. Contribution bar | 397 | 1.3% |

Most of the largest section is incident narrative: why the hook interpreter is a fallback and what
believing otherwise cost, why the commit-trailer rule exists and which sync it deadlocked, the four
rules of the provenance convention and the folklore that produced them. Every word is load-bearing for
trust. Almost none of it is load-bearing for the agent fixing a defect in `ingest.py`.

**The move is to split, not to cut.** The citations are what distinguish a consolidated rule from an
invented one, which is `autonomy.md`'s own argument, so deleting them would spend the thing that makes
the rules credible. Moving them into a provenance document, with each rule in `AGENTS.md` linking to
its own incident, keeps every word and takes the fixed read cost down substantially. This is the same
argument the kit already made and won when it split the lenses out of the skill bodies: a rule and its
justification have different readers and different lifetimes.

Combined with a task file now averaging around 10 KB in the most recent full band, the fixed cost
before a dispatched agent reads any code is roughly 10,000 tokens, on top of the description budget
below.

### The default install spends about 3,400 tokens of always-resident context

Measured through `install.resolve_profile` against the shipped set:

| Profile | Skills | Description budget |
| --- | --- | --- |
| `core` | 3 | 2,298 |
| `spine` (default) | 18 | 13,533 |
| `all` | 20 | 15,317 |

`docs/GETTING-STARTED.md` already explains the trade to readers, and the profile mechanism already
exists to manage it, so this is not a gap. It is context for the collision finding above: the budget
is spent whether or not the descriptions are distinguishable, and six pairs currently are not.

### Task files are growing

Mean size by id band, across every task file in the tree:

| Ids | Files | Mean |
| --- | --- | --- |
| 1 to 20 | 60 | 5,618 B |
| 21 to 40 | 60 | 8,207 B |
| 41 to 60 | 60 | 8,649 B |
| 61 to 80 | 26 | 10,111 B |
| 81 to 100 | 11 | 7,174 B |

The last band is partial and its mean sits below the trend, so it may be a turn rather than noise. The
honest reading is that the first four rise and the fifth is not yet decidable. What the rise is made of
is visible in the largest files, which carry investigation transcripts rather than instructions. A task
file is defined here as the 1,000-foot decomposition of a Feature, and 10 KB is roughly 2,500 tokens of
reading for one atomic item.

Not filed as a finding, because the direction of a fix is a judgment. A long task file is often the
right answer, and `feat-0062` at 26 KB earned every line. The question worth asking at some point is
whether the investigation belongs inside the task or beside it.

## Tool proposals

Four, each argued against the contribution bar rather than the idea's appeal, and each carrying the
thing that would kill it. None is decomposed and none is written into `ROADMAP.md`: whether any of them
is wanted is the maintainer's call, which is how the bar already works.

### `skill-author`, the workflow this kit performs most and has no skill for

This kit has authored 22 skills. Authoring one is also the workflow with the most rules attached to it
anywhere in this repository: two body shapes with a declared marker, a reference to every universal
lens, the portability contract's three legal link classes, sibling links that are silently profile
edges, provenance blocks with four rules and a placement per file type, a draft marker that has to be
spelled one specific way to satisfy two validators at once, a description budget shared with every
other installed skill, and a contribution bar that decides whether the thing ships at all.

All of that lives in `AGENTS.md` prose plus `validate-skills.py` exit codes. There is no skill for it.
Every skill here was authored by a person or an agent reading the rules and remembering them, which is
the exact condition `feat-0038` was filed against for enforcement generally: a rule that holds only
while the model keeps it in context.

The bar is unusually easy to meet. The skill is dogfooded by construction, because the next skill
authored uses it, and the twenty-two already authored are a ready evaluation corpus. Anthropic ships a
`skill-creator` occupying this slot, so the honest route is folding it in under the provenance
convention and retargeting it, the way `spec-quality` and `test-quality` came in, rather than writing
cold.

**What would kill it:** if a first real use shows the retargeting is most of the work and the upstream
contributes little, it is a rewrite wearing a provenance block, and should be declined the way the
third-hand `maintainability-review` lens was.

### An enforcement surface for `A10`

`A10` is the only rule in `autonomy.md` resting on someone else's incident, it is the newest, it is the
one the security policy is currently wrong about, and it is enforced by nothing.

That is out of step with everything around it. Every comparable rule here acquired a mechanism once it
mattered: lens references and link resolution went into `validate-skills.py`, conformance onto a gate
hook, matrix citations into `check-citations.py`, provenance into `check-provenance.py`, install
currency into a session hook. Meanwhile the roadmap holds a hook candidate for the commit-trailer rule,
whose worst measured cost was hours of a maintainer's time. `A10`'s worst case, in the incident it
cites, was a compromised package published under someone else's name.

The right shape is a reminder rather than a gate, and the hooks contract already says why: a gate may
block only when the condition is decidable from the payload, and whether an agent has been steered by
something it read is not. What is decidable is the ingestion. A fetch, a pull request body, an issue
body: a reminder there restates the rule at the moment the material arrives, which is the one moment it
is about to matter, and it costs one injected paragraph in the failure case.

**What would kill it:** if a real trial shows the reminder firing constantly on ordinary reading, it is
noise, and noise is how a rule gets ignored. Bound it to the tools that actually cross the provenance
boundary before shipping it.

### A retirement discipline

Every mechanism in this kit adds. The changelog is append-only by contract. The roadmap keeps struck
items in place. Task files move to `done/` rather than out. Skills accumulate, and the body shapes, the
profiles, the lenses, the hooks and the gates all grow by one when something is learned and never by
minus one.

That is mostly correct, and it is why the history here is trustworthy. But `doc-sync` detects drift,
`check-provenance.py` detects upstream movement, and nothing detects accretion. The kit has no answer
to "this rule stopped earning its place", "this gate has never failed", or "this skill has never been
invoked", even though the observatory can already answer the last one and did, finding that nine of the
skills in its roster had never been used.

The lightest honest version is not a skill. It is a question added to the after-action step already
planned as Epic E item 8, asking what a run made unnecessary as well as what it taught, plus a report
the observatory is already positioned to produce.

**What would kill it, and it is the bar Epic B item 19 sets for itself:** it has to find something. A
retirement pass concluding that everything should stay is a ceremony, and should be dropped rather than
repeated.

### A trigger-collision gate, and a sensor that runs when nobody asked

Two roadmap items deliberately leave their artifact open, and this pass produced a concrete candidate
for each.

Epic E item 6 names trigger disambiguation as the half nobody else's precedent covers, and finding 4
shows why it cannot rest on figures written by hand. A small gate that recomputes the description
budget per profile and reports any pair over an overlap threshold is mechanical, deterministic, cheap,
and joins the `run-checks.py` set without asking anyone for judgment. It would have caught finding 4
the day the twenty-first skill landed, and it turns a prose claim into a number that cannot go stale.

Epic B item 19 asks for a sensor that runs between changes and declines to presuppose the artifact. The
cheapest honest one is a scheduled workflow, because two of this kit's best sensors already exist and
are only ever run when someone remembers: `check-provenance.py` is deliberately outside required CI
because it needs network, and `install.py --check` answers currency correctly and is invoked on no
schedule at all. A weekly job calling both, changing nothing and reporting drift, is close to free and
satisfies item 19's own acceptance bar the first time it finds something on a repository nobody has
just reviewed. Finding 1 is evidence that the class is live: it sat wrong for five days across a green
tree.

**What would kill the scheduled sensor:** the reason `check-provenance.py` was kept out of CI in the
first place. A job that goes red when GitHub is slow gets disabled within a week, so it has to report
rather than fail, which is the posture `autonomy.md` already takes.

## Tasks filed

| Task | Finding |
| --- | --- |
| `bug-0063` | 1, the security policy denies `A10` |
| `bug-0064` | 2, resubscribe leaves the watcher stopped |
| `bug-0065` | 3, a recorded path used as a replacement pattern |
| `chore-0092` | 4, stale description-budget figures and the wrong collision cluster |

The proposals are not filed. Per the contribution bar, whether any of them is built is a decision
rather than a backlog item.
