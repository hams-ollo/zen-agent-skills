# Quest tracker: authoring guide

How to start and run a development season from the quest tracker template. The template is a private Claude artifact: [Quest tracker template](https://claude.ai/artifact/2CXWWBAuu9RfieCVn156LA). The first full season run on this pattern is the [NYFG launch run sheet](https://claude.ai/artifact/7feLZSDFECEty9PSDNHfbh) (October 2026).

## What the template is

One page that holds a whole season of work: phases of steps, each step opening into its lines to tick, a check, a stop, facts to write down, links, and a session log with screenshots. Everything on the page is drawn from **one data block** at the top of the page's script, between the `DATA BLOCK` and `END OF DATA BLOCK` markers. Edit that block and the rest follows:

- the quest board (who does what, in order), the route strip and the "steps left to <goal>" counter
- open blocker tags and the "Stop and check in" stripes
- the season map, the burndown of steps left, the People panel, Next up and Recent activity
- the owner filter chips, the facts table and the reference sections

Ticks, facts and notes are saved live in the artifact's shared database and seen by everyone who can open the page. Filters and which steps are open are remembered only in each viewer's own browser.

## Start a new project's tracker

1. Ask Claude: "start a quest tracker for <project> from the template", and give it the template link above plus whatever you already know (the goal, the people, the first phases).
2. Claude reads the template with the Artifact tool, writes the new project into the data block, and publishes it as a **new** private artifact with the capabilities `db`, `user` (scope `profile`) and `assets`. Never publish over the template itself: each project gets its own artifact and its own database.
3. Claude sets a new `storageKey` (for example `ht-sourdough`), so remembered filters do not mix between trackers.
4. Open the new link. The yellow "Data block check" box under the header lists anything malformed (duplicate ids, a quest naming a step that does not exist, a step with nobody in `who`). Nothing shows when the block is clean.
5. Share it from the page's Share menu: Editor for anyone who ticks or attaches screenshots, Viewer for anyone who only reads.

Doing it by hand also works: copy the template's HTML, edit the data block, and publish the file as a new artifact with those three capabilities.

## The data block

| Field | What it holds |
|---|---|
| `LINK` | Base addresses (repository, docs folder, help sites) so step links stay short. |
| `storageKey` | Prefix for each viewer's remembered filters. One per project. |
| `skin` | The default look: `zen`, `quest` or `field` (see "The three looks"). Each viewer can switch with the Look picker. |
| `ranks` | Rank titles, one per 100 XP, for the game skins. |
| `eyebrow`, `title`, `lede`, `statusNote` | The header: project line, page heading, how to use the page, and a dated status line. In `title`, `*word*` sets one word in the accent italic, like the "ship." on the Zen Solutions site. |
| `started` | First day of the season, `YYYY-MM-DD`. The burndown starts here. |
| `goal` | `{ label, target }`. The label finishes "steps left to ..."; the optional target date draws the even-pace line on the burndown. |
| `questsIntro` | The sentence above the quest board. |
| `doclinks` | Header buttons: `[label, url, small text]`. |
| `rules` | The rules strip: `{ title, text, warn }`. `warn: true` paints it as the "never" rule. |
| `people` | `key: { name, tone }`. Tone is one of `ink`, `accent`, `gate`, `done`, `plain`. |
| `phases` | The work, in order (below). |
| `quests` | The order of work across phases (below). |
| `reference` | Extra sections under the facts table: `{ title, text: [paragraphs], table: { head, rows } }`. |
| `footer` | The last line on the page. |

Text anywhere in the block understands five marks: `[[On-screen control]]`, `**bold**`, `*italic*`, `` `code` ``, and `[link text](https://...)`.

## The three looks

One token set, three skins, picked by `skin` in the data block and switchable per viewer (the Look picker in the toolbar, remembered in that viewer's browser):

| Skin | For | Look |
|---|---|---|
| `zen` | Zen Solutions work and professional projects (the default) | The Zen Solutions site palette: near-black, cream serif headings, vermilion accent, `//` eyebrows, a low red sun behind the header. With an 8-bit layer: pixel labels, notched corners, segmented progress bars, `LV` badges, square map cells. |
| `quest` | Main Quest Zen and anything playful | Main Quest Zen's look: night navy with a faint pixel starfield, heavy sans headings, pixel labels, cyan, amber and violet. |
| `field` | Client-facing trackers (NYFG style) | The light work-order sheet, which follows the viewer's light or dark setting and drops the game layer. |

Both game skins are dark by design. The game layer adds a pixel burst and "+XP" when a step is ticked, and a "Quest complete" notice when the last step of a quest is ticked; both are skipped for anyone who has reduced motion switched on.

## XP and ranks

The game skins show season XP and a rank in the Season map panel. XP rewards writing things down as well as ticking:

| Action | XP |
|---|---|
| A step ticked | 10 |
| ...that is a blocker | +20 |
| ...that is a stop | +10 |
| A fact recorded | 5 |
| A note logged | 3, +2 with a screenshot |

Every 100 XP is a rank, named from `ranks`. XP is drawn from the saved ticks, facts and notes, so it is the same for everyone and goes down if a step is unticked. It never changes what a tick means: tick only checked work.

## The season log, for the docs

The Reference section has a **Copy the log as Markdown** button: every phase and step with its state, its line count, its facts and its notes, dated, ready to paste into the project's docs or to hand to Claude at the end of a session. Where the viewer blocks copying, the text appears selected in a box instead.

## How to write a phase

```js
{ id: "p1", title: "Lock down the accounts", when: "Guide part A", now: true,
  intro: "One paragraph: what this stretch of work is, in what order, and what must be true at the end.",
  docs: "Which documents this phase changes",
  steps: [ ... ] }
```

`now: true` highlights the phase's `when` tag as the current one (`today: true` from the NYFG sheet works too). A phase ends in something you can check.

## How to write a step

Every step carries its own context, so anyone can pick it up on any day without a call: **what** to do, **why** it matters, and **what closes it**.

```js
{ id: "p1-namecheap", t: "Lock the domain and turn on auto-renew", who: ["santosh"],
  why: "The lock stops anyone with the password moving the domain away.",
  steps: [
    "At the registrar: [[Domain List]], [[Manage]], turn on [[Domain Lock]].",
    "Turn on [[Auto-Renew]]. The card is the owner's call.",
  ],
  check: "The public registry record lists `client transfer prohibited`.",
  stop: "anything asks you to [[Import]] or [[Reset DNS Records]].",
  tip: "If a record is changed by mistake: [[DNS history]], [[Restore]].",
  facts: [{ id: "domain_lock", label: "Domain Lock", hint: "on or off, and the date", placeholder: "On, 14 Oct" }],
  docs: [["Help: Domain Lock", "https://..."]],
  ours: [["Guide A2", LINK.GUIDE + "#a2"]],
  doc: "Inventory, Namecheap row" }
```

| Field | Use it for |
|---|---|
| `id` | The permanent key for the step's ticks, notes and facts. See the id rules below. |
| `t` | The title: a short imperative, the thing done. |
| `short` | A shorter name for the open-blockers line, when `t` is long. |
| `who` | Person keys from `people`. The first is whoever leads it. |
| `why` | One or two sentences: what goes wrong without it, and any decision already taken (with its date and who took it). |
| `steps` | The lines to follow, one click or one action each. Each line gets its own tick. |
| `check` | What proves it worked, observable by someone else ("asks for an app code", "answers 401"). This is what closes the step. |
| `stop` | Finishes the sentence "Stop if: ...". The condition that means do not go on. |
| `tip` | "Good to know": context that saves a wrong turn. |
| `facts` | Values to write down as you go (see below). |
| `docs` / `ours` | Links: vendor help pages, then the project's own docs. |
| `doc` | Which document to update after the step. |
| `gate: true` | A striped stop step: someone named in it must check in before anyone goes past. |
| `blocker: true` | Counts toward "N blockers open" until ticked, with a red tag on the board and the map. |
| `optional: true` | Shown dashed; never on the route, never warned about for a missing `why`. |

A step with neither `why` nor `check` is flagged by the data check: if you cannot say why it matters or what closes it, it is not ready to be a step.

## Ids

- Phase ids `p0`, `p1`, ... and step ids `<phase>-<word>`, such as `p3-ftp`. Letters, digits, `-` and `_` only.
- Fact ids are short snake_case names for the value, such as `ftp_cert_host`.
- **An id never changes once anything is ticked, logged or recorded against it.** The saved ticks, notes and facts are keyed by id: rename the id and they stay behind under the old one, invisible.
- An id need not match the phase it sits in. Moving a step to another phase is safe if the id stays (NYFG's `p2-org` lives in phase 1). Never reuse an old id for a different step.
- The data check flags duplicate step, fact and phase ids.

## Never move a step's lines

Line ticks are stored as a list by position (`subs: [true, false, true]`): the first tick belongs to line 1, the second to line 2, and so on. The list does not know the text of the line.

So, once any line of a step is ticked:

- **Add** new lines at the end only.
- **Never** insert a line above others, reorder lines, or delete one: every tick below it shifts onto the wrong line.
- **Reword** a line in place only if it still means the same action.
- If the lines must change shape, write a new step with a new id and mark the old one `optional`, with a `why` that says it was replaced.

The step-level tick (done or not) is safe: it is keyed by the step's id, not by position.

## Ticks: what they mean

A tick means the work is done **and** its `check` passed. Not started, half done, or "should be fine" stays unticked. A step can have every line ticked and still be open, because the step's own tick is the claim that it was checked. The burndown, the season map and the quest board all count only the step's own tick.

## How ticks, facts and logs are stored

```mermaid
flowchart LR
  D[Data block in the page] --> P[Page renders steps by id]
  P --> C[checks: one doc per step id]
  P --> F[facts: one doc per fact id]
  P --> L[log: one doc per note]
  L --> A[assets: screenshot files]
```

| Collection | One document per | Fields |
|---|---|---|
| `checks` | step, named by its id | `done`, `by` (a person id), `at` (when last ticked or unticked), `subs` (line ticks by position), `note` (an older free-text note, shown as "Earlier note") |
| `facts` | fact, named by its id | `value` (300 characters at most), `by`, `at`, `step` |
| `log` | note | `step`, `text` (4,000 characters at most), `asset` (a screenshot's id, or none), `by`, `at` |

Screenshots are uploaded to the artifact's asset store (Editors only) and shown from it. People are stored as opaque ids and their names looked up when the page renders, so a renamed account shows its new name. Claude can read and write all three collections with the ArtifactData tool, which is how a session's results get copied into the project's docs at the end of a session, and how example ticks are seeded.

The burndown is drawn from each route step's `at`. A step unticked and ticked again moves to its newer date; there is no separate history.

## What goes in facts

Facts are values someone will need again, written down while the screen is in front of them: names, places, settings and decisions that are safe to share.

- **Yes:** a folder path, a host name, a container or property ID, which login holds the domain, "on, 14 Oct", where the backup is kept, which phone holds the authenticator app, an expiry date, a yes or no answer to a question the step asks.
- **Never:** a password, sign-in code, backup or recovery code, API key, token, form key, card number, or anything a person could log in with. The page refuses a fact or note that looks like one (`password:`, a UUID-shaped key, `ghp_...`, `AIza...`, `sk_live_...`), but the check is a net, not a guarantee.
- Write the date and the person into the value when it matters ("Mon to Sat, 8 to 5, confirmed by Narine, 14 Oct").
- At the end of a session Claude copies the facts into the project's own docs (an inventory or playbook), so the tracker is never the only copy.

## Quests and the route

A quest is one run of work, in order, usually one call or one person's sitting. The `quests` list is the route to the goal:

```js
{ tone: "accent", short: "2 Santosh call", title: "2. Santosh call: accounts and hosting prep",
  note: "Who is needed, what to have ready, about how long.",
  wait: "Waiting on Narine",          // optional: the quest sits with someone else
  ids: ["p1-google", "p2-org", "p1-namecheap"] }
```

- The first quest not done and not waiting is marked "Up next". A quest with `wait` shows that label instead and is skipped for "Up next".
- The route is every step listed in any quest, in quest order. It drives "N steps left", Next up, the burndown, and the ringed cells on the season map. With no quests, the route is every step that is not optional.
- A step can sit in one quest only; listing it twice counts it once.
- `tone` picks the quest's color. The NYFG sheet's `cls: "<person key>"` also works and borrows that person's color.

## The views

- **Quest board and route strip:** the chain of runs, with progress bars, blocker tags and who is on each open step.
- **XP and rank** (game skins): season XP, the rank, and the XP to the next rank.
- **Season map:** every step of every phase as one cell, in phase order. Green is done, red outline an open blocker, amber stripes a stop, dashed optional, a blue ring on the route. Each cell opens its step.
- **Steps left to <goal>:** the burndown. One point per day from `started` to today, the dashed even-pace line to `goal.target`, and a hover read-out of the day's count and how many steps were ticked that day.
- **People:** one card per person: their steps done, their open blockers, their next step, and a button to filter the page to them.
- **Next up and Recent activity:** the next four route steps, and the last six ticks, facts and notes with who and when.

## Ideas for more visualization, not built yet

Each of these reads only what the page already stores.

- **Blocker age:** how many days each open blocker has been open, from `started` or from the step's first note. Cheap; needs no new data.
- **Session calendar:** a heatmap of days with ticks and notes, which shows the season's rhythm and the quiet stretches. Cheap.
- **Dependency view:** a Mermaid flowchart from an optional `after: ["step-id"]` field on steps, showing which steps unlock which. Needs one new field.
- **True history:** an append-only `events` collection (one document per tick or untick) so the burndown never moves when a step is reticked. Needs a small change to the tick code; old trackers keep working without it.
- **Cross-project overview:** one page listing each project's tracker with its steps left and open blockers, read from each artifact's database by Claude at the end of a session. Needs a session routine, not a page change.

## Porting an existing sheet

The NYFG run sheet's `PHASES`, `QUESTS` and `OWNERS` move across almost unchanged: put `PHASES` into `phases`, `QUESTS` into `quests` (its `cls` still works), and turn `OWNERS` into `people` with a tone for each. Keep every id exactly as it was; the saved ticks stay in the old artifact's database, so a port is a fresh start unless Claude copies the documents across with ArtifactData.

## House rules

- No em-dashes; sentence-case headings, in the data block as anywhere else.
- Every step says what, why, and what closes it. No bare titles.
- Tick only verified work.
- Never move a step's lines once ticked.
- No secrets in notes, facts or screenshots. Crop screenshots first.
