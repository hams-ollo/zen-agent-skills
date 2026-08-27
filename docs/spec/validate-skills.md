---
title: validate-skills
status: approved
---

# validate-skills

Behavioral contract for [`scripts/validate-skills.py`](../../scripts/validate-skills.py), written
2026-07-24 to serve as the audit target for the first in-kit dogfood of the `spec-conformance`
lens. It captures the tool's intended contract from its module docstring and observable behavior.

Reopened to `draft` on 2026-07-27 and amended (`chore-0013`). The implementation had twice grown
past this contract without it: `feat-0023` added link resolution, sibling-reference, and
status-contradiction checking on 2026-07-25, and the 2026-07-27 review pass added the portability
check now specified as S-011. Scenarios S-009 through S-016 close that gap. Re-approved by the
author on 2026-07-27.

**Amended 2026-08-27 (`chore-0065`) to state the non-skill `.agents/` markdown link rule: the
markdown that ships in the tree the skills sit in, outside every skill directory, is link-checked
from where it sits, and a link reaching above that tree is reported as non-portable rather than as
merely broken. Scenario S-025, plus the `Output` and `What it reads` surface entries it moves.** This
amendment is **pending the author's re-approval**. It writes down the behaviour `chore-0058` gave the
validator on 2026-08-27, which this contract did not mention at all. S-024 covers a markdown file
shipped beside a `SKILL.md`; nothing covered one shipped beside the skills *tree*, which is a
different geometry: its links resolve one directory level higher, the sibling-skill shortcut is wrong
there for a sharper reason, and the walk that finds those files does not always run. No goal is
added, for the reason `chore-0054` gave and with one qualification worth stating: Goal 4 names a
skill's cross-references, and a link in the rules module or the hooks README is not one, so the rule
serves that goal's property (a reference that breaks once the tree is distributed) over a subject
Goal 4's wording does not reach. Widening it is the author's call rather than an agent's, and S-023
already set the precedent that a rule here may have a non-skill subject without a goal of its own.
`status` is left reading `approved` per the convention in [`README.md`](README.md). This is the fifth
time the implementation has grown past this contract, after `feat-0023`, `bug-0027`, `feat-0048` and
`chore-0036`, and every one of the five was found at a later task's closeout rather than by any gate.

**Amended 2026-08-21 (`chore-0054`) to state the supporting-file link rule: the markdown a skill
ships beside its `SKILL.md` is link-checked from where it sits, and a file authored to be written
into another repository is excluded. Scenario S-024, plus the `Output` and `What it reads` surface
entries it moves.** This amendment is **pending the author's re-approval**. It writes down the
behaviour `chore-0036` gave the validator on 2026-08-21, which this contract did not mention at all:
it described a validator that reads one file per skill and ends its run at a single summary line. No
goal is added, because Goal 4 already reads "a skill's cross-references" rather than a `SKILL.md`'s,
and the constraint below that a skill is distributed as a directory already carries the reason a file
beside the body is in scope at all. `status` is left reading `approved` per the convention in
[`README.md`](README.md), for the reason the notes below give. This is the fourth time the
implementation has grown past this contract, after `feat-0023`, `bug-0027` and `feat-0048`, and every
one of the four was found at a later task's closeout rather than by any gate.

**Amended 2026-08-20 (`chore-0047`) to state the lens-composition rule: a file under the sibling
rules module that declares itself a lens must be referenced by at least one skill. Scenario S-023,
plus the Proposed Surface entry admitting that the tool reads `.agents/rules/` and not only
`.agents/skills/`.** This amendment is **pending the author's re-approval**. It writes down the
behaviour `feat-0048` gave the validator on 2026-08-19, which this contract did not mention at all.
It is structurally unlike every amendment before it: each earlier rule here is about a **skill**, and
this is the first that reads a sibling directory, which is why the surface entry is part of the
amendment rather than an afterthought. `status` is left reading `approved` per the convention in
[`README.md`](README.md), for the reason the note below gives.

**Amended 2026-08-19 (`chore-0039`) to state that a markdown link rendering as literal text is not
a link and is not checked at all: scenario S-022, an exception to the link rules S-009 through
S-013.** This amendment is **pending the author's re-approval**. It writes down the behaviour
`bug-0027` gave `check_links()` on 2026-08-18, which the contract did not state at all, and `status`
is left reading `approved` per the convention in [`README.md`](README.md): `verifier-agent` returns
`blocked` on a spec that is not approved, so flipping the field would make the verification run for
this very amendment unanswerable.

**Amended 2026-07-29 (`bug-0008`) on the author's explicit instruction, and re-approved.** S-020 and
S-021 add the two remaining rules of the skill schema this validator did not check: no angle brackets in
`description`, and an allow-list of frontmatter properties. Both are hard failures at the consumer.
`human-handoff` was failing the first, found by running Anthropic's reference validator over the tree.
This is the third defect in the same field in two days, after `bug-0005` and `bug-0007`, each found by a
different external check and none by this one. The pattern, now recorded in the constraint below, is that
validating against this contract was never the same thing as validating against the schema the
distribution targets enforce.

**Amended 2026-07-28 (`bug-0007`) on the author's explicit instruction, and re-approved.** S-019 was
added, along with Goal 7 and the non-goal bounding it. Eight of the nineteen shipped skills had
frontmatter that no real YAML parser could read: a plain unquoted `description` containing a colon
followed by a space, which YAML parses as a nested mapping. Every gate passed, because both kit scripts
read frontmatter with a regex that accepts it, so the kit had never parsed its own frontmatter the way a
consumer does. It was found by running a third-party installer, which skipped all eight.

**Amended 2026-07-28 (`feat-0032`) on the author's explicit instruction, and re-approved.** S-017 and
S-018 were added, along with Goal 6 and the field-limit constraint they serve. This contract had a soft
floor on the description and no ceiling, while both harnesses `install.py` targets cap the field at
1024 characters, so five shipped skills exceeded a hard distribution limit and the validator reported
nothing (`bug-0005`). S-018 exists because fixing S-017 alone would have been wrong: the parser counted
a YAML block-scalar indicator as description content, so the number the validator reported was three
characters higher than the number the harness measures, and a ceiling built on it would reject
descriptions the harness accepts.

## Problem

The kit ships skills as `SKILL.md` files. A malformed skill (missing frontmatter, a `name` that
does not match its directory, a thin description) should fail loudly before it is distributed. The
validator is the kit-level lint that enforces that bar.

## Goals

1. Fail (non-zero exit) when any skill is structurally invalid.
2. Warn without failing when a skill is well-formed but below a soft quality bar.
3. Report a summary of how many skills were checked and the error and warning counts.
4. Fail when a skill's cross-references are broken, or when they would break once the skill is
   distributed away from this repository.
5. Fail rather than report a vacuous success when the target skills directory cannot be read, so an
   absent check is never indistinguishable from a passing one.
6. Fail when a field exceeds a limit the distribution targets enforce, because a skill a harness
   rejects or truncates has not shipped, and it fails by simply never being selected.
7. Fail when frontmatter is written in a form a real YAML parser rejects, since this validator's own
   reader is more permissive than any consumer's and a skill it accepts may still be unreadable
   everywhere it is installed.

## Non-Goals

- **Full YAML validation.** The standard-library-only constraint rules out a YAML library, so the
  parseability check in S-019 targets the specific construct that has actually shipped rather than
  claiming general validity. It is a check for one known defect, and its message says so.
- Judging skill prose quality beyond the structural and length proxies.
- Modifying or fixing any skill.
- Verifying that a link's target contains what the linking text claims about it.
- Resolving external URLs, which would require network access.

## Constraints

- Standard library only.
- A `SKILL.md` is YAML frontmatter (delimited by `---`) followed by a Markdown body.
- **The skill schema is external and this validator's job includes conforming to it, not only to this
  contract.** The reference implementation is `quick_validate.py` in Anthropic's `skill-creator` plugin,
  read 2026-07-29. It caps `description` at 1024 characters, forbids angle brackets in it, requires a
  kebab-case `name` of at most 64 characters, and allows exactly six frontmatter properties: `name`,
  `description`, `license`, `allowed-tools`, `metadata`, `compatibility`. Those bounds are not the kit's
  to choose, which is why violating one is an error rather than a matter of taste. Three separate defects
  in `description` shipped while this contract and the implementation agreed with each other, so a rule
  that exists only upstream is treated here as part of the contract.
- Frontmatter is read by a small standard-library parser, not a YAML library. A field's value is
  therefore whatever that parser yields, so where YAML syntax and the parser could disagree about what
  the value is, the contract states which one the checks mean.
- A skill is distributed as a directory alongside its sibling skills and the swappable rules module,
  without the surrounding repository. A link is therefore legal only if it stays inside that
  distributed tree: the skill's own files, a sibling skill, or the rules module. A link above it
  resolves in this repository and dangles everywhere the skill is actually used.

## Scenarios

### Scenario S-001: skill directory without SKILL.md

- **Given** a directory under `.agents/skills/` that has no `SKILL.md`
- **When** the validator runs
- **Then** it records an error for that directory and exits non-zero.

### Scenario S-002: SKILL.md without frontmatter

- **Given** a `SKILL.md` whose first line is not `---`, or that has no closing `---`
- **When** the validator runs
- **Then** it records a "no YAML frontmatter" error and exits non-zero.

### Scenario S-003: name does not match directory

- **Given** a `SKILL.md` whose frontmatter `name` differs from its directory name
- **When** the validator runs
- **Then** it records a name-mismatch error and exits non-zero.

### Scenario S-004: missing name or description

- **Given** a `SKILL.md` missing the `name` or `description` key
- **When** the validator runs
- **Then** it records a missing-field error and exits non-zero.

### Scenario S-005: thin description warns but does not fail

- **Given** a `SKILL.md` with a `description` shorter than the soft minimum
- **When** the validator runs
- **Then** it records a warning, records no error for that description, and (absent other errors)
  exits zero.

### Scenario S-006: oversized body warns but does not fail

- **Given** a `SKILL.md` whose body exceeds the progressive-disclosure line guideline
- **When** the validator runs
- **Then** it records a warning and (absent other errors) exits zero.

### Scenario S-007: all skills valid

- **Given** a skills directory where every skill is well-formed
- **When** the validator runs
- **Then** it prints a summary line with the skill count and zero errors, and exits zero.

### Scenario S-008: description states what and when

- **Given** a `SKILL.md` whose description is long enough to pass the length check but does not
  actually state both what the skill does and when to use it
- **When** the validator runs
- **Then** the description is flagged as not meeting the "what and when" bar.

### Scenario S-009: link to a target that does not exist

- **Given** a `SKILL.md` containing a relative link whose target is not present on disk
- **When** the validator runs
- **Then** it records a link-target error naming the unresolved path, and exits non-zero.

### Scenario S-010: reference to a sibling skill that does not exist

- **Given** a `SKILL.md` referencing a sibling skill that is not present in the kit
- **When** the validator runs
- **Then** it records an error naming that skill, and exits non-zero.

### Scenario S-011: link that escapes the distributed skill tree

- **Given** a `SKILL.md` containing a relative link that resolves above the distributed skill tree,
  and whose target does exist in this repository
- **When** the validator runs
- **Then** it records an error naming the link as non-portable, and exits non-zero. The target's
  existence in this repository does not satisfy the check, because the skill is not distributed with
  this repository around it.

### Scenario S-012: link to the rules module is legal

- **Given** a `SKILL.md` linking to a file in the sibling rules module
- **When** the validator runs
- **Then** it records no finding for that link, because the rules module travels with the skills.

### Scenario S-013: external and same-page links are not resolved

- **Given** a `SKILL.md` containing `http`, `https`, or `mailto` links, or links to an anchor on the
  same page
- **When** the validator runs
- **Then** it records no finding for any of them, and does not attempt to resolve them on disk.

### Scenario S-022: a link that renders as literal text is not a link

- **Given** a `SKILL.md` containing a markdown link whose opening bracket sits inside an inline code
  span (a run of backticks of any length, closed on the same line by a run of the same length) or
  inside a fenced code block
- **When** the validator runs
- **Then** it records no finding for that link, from any of the link rules, and does not resolve it
  on disk.

  This is an exception to S-009 through S-013 and takes precedence over all of them. Those scenarios
  sort a link by its *kind*; this one decides whether the text is a link at all. A link rendered as
  literal text is the body **showing** a link as an example rather than making one, so there is no
  reader to strand and nothing to resolve. Without this rule a skill body cannot show an example
  markdown link, which is exactly what the documentation skills want to do, and the error it earns
  never names the fence as the cause (`bug-0027`).

  The exception includes the portability rule S-011, deliberately rather than incidentally. That
  rule protects a reader who follows a link that dangles once the skill is installed, and a link
  rendered as literal text is followed by nobody; keeping the rule armed inside a fence would stop
  an author showing the very construct the rule exists to teach.

  A link whose *text* is wrapped in a code span, which is how nearly every link in this kit is
  written, is still checked. It is the link's opening bracket that has to fall inside the span or
  the fence for this scenario to apply.

  Outside a span or a fence nothing about the link rules changed, and the boundary is worth stating
  because the two validators here differ on it: an absolute or `file://` link is still an error in
  this tool, whether by escaping the shipped tree or by failing to resolve, even though the backlog
  validator in `.tasks/validate.py` tolerates one.

  An unterminated opening fence yields no range and therefore suppresses nothing below it: the links
  after it are checked as usual. A detector that ran an unclosed fence to end of file would switch
  the link check off for the rest of the body while still reporting success, which is the one failure
  indistinguishable from success. An unmatched backtick run opens nothing for the same reason. That
  trade is the one `bug-0015`, `bug-0017`, `bug-0023` and `bug-0028` each settled in the other
  checkers carrying this rule, and this contract restates it rather than inheriting it silently.

### Scenario S-024: a markdown file shipped beside a SKILL.md is link-checked where it sits

- **Given** a skill directory holding, beside its `SKILL.md`, a markdown file that carries a relative
  link which does not resolve, or which resolves above the distributed skill tree
- **When** the validator runs
- **Then** it records the finding that link would earn in a `SKILL.md` under S-009 or S-011, naming
  the supporting file rather than the `SKILL.md`, and exits non-zero.

  The subject of the constraint above is a **directory**, not a file: a skill is distributed as a
  directory alongside its sibling skills and the rules module. A markdown file read in place inside
  that installed directory strands exactly the reader a broken `SKILL.md` link strands, so the link
  rules reach it unchanged, resolved from where that file sits rather than from the `SKILL.md`.

  **A file authored to be written into another repository is excluded, and that limit is part of the
  contract rather than an implementation detail.** Its links are written for the destination and are
  meant not to resolve where the file currently sits, so checking them here would report every one of
  them as broken and make the rule unusable. The marker is the `.tmpl` suffix on the file's name,
  which this kit already puts on exactly the files it writes elsewhere. The marker being a property
  of the file is the load-bearing part: a table of destinations declared in a skill body or in the
  tool would be a second source of truth that drifts from the skill silently, and silent drift is the
  failure this whole rule exists to catch, so buying coverage with it would be a bad trade
  (`chore-0036`). Neither is the exclusion drawn by directory name: a document that describes the
  directory it sits in is checked wherever it sits, including inside a `templates/` directory.

  **The cost is stated rather than hidden.** A destination-bound markdown file added *without* the
  marker is checked against this repository and reports links written for somewhere else. That
  failure is loud, and the fix is a rename that also makes the file read as a template to every
  human, where the failure of a directory-name rule would be silent.

  **The sibling-skill shortcut S-010 does not apply to a supporting file.** That rule reads
  `../<name>/SKILL.md` as a skill *name* rather than as a path, which is true only one directory
  level up from a sibling skill, where a `SKILL.md` sits. From a file one level deeper the same text
  names a subdirectory of its own skill, so the shortcut would clear a genuinely broken link whenever
  a real skill happened to share that name. Resolved on disk like any other link, it earns the
  ordinary S-009 message instead. S-011, S-012, S-013 and S-022 apply here unchanged.

  **A non-markdown file is counted and not read**, because markdown link syntax inside a `.py` or a
  `.json` is not a link. **A file the kit does not distribute, such as a byte cache, is neither read
  nor counted**, so two runs over the same tree report the same numbers whether or not the test suite
  has run in between. A count that moved with the state of the working tree could not be compared
  across runs, which is the only thing it is for.

  **What a skill ships beside its body is a fact about the directory**, so this rule is not
  conditional on the `SKILL.md` being there or being readable. A directory that earns the S-001 or
  S-002 error still has its supporting files checked and counted, rather than dropping out of both at
  the moment its body became unreadable.

  **What the run reports is both what it read and what it declined to read**, which is what makes the
  bound checkable: "0 supporting files checked" reads identically whether the rule is working or the
  walk is broken, until the count of the skipped sits beside it. **No coverage figure is a clause of
  this contract.** What the tree holds changes, a stated limit is worth more than a coverage number
  nobody can trust, and the measurement belongs in the conformance matrix beside the date it was
  taken.

### Scenario S-025: markdown shipped beside the skills tree is link-checked where it sits

- **Given** a markdown file that ships inside the distributed tree but outside every skill directory,
  carrying a relative link which does not resolve, or which resolves above that tree
- **When** the validator runs
- **Then** it records the finding that link would earn in a `SKILL.md` under S-009 or S-011, naming
  that file, and exits non-zero.

  **The subject is the tree, not a named pair of directories.** The constraint above says a skill is
  distributed alongside its sibling skills and the rules module, and `install.py` places the optional
  hooks module as a sibling of the skills directory too. Every one of those files travels to an
  adopter exactly as a skill does, so a link in one is exactly as clickable and exactly as breakable.
  The rule is therefore drawn by geometry, over whatever ships in that tree outside the skills
  directory, rather than over a list of directory names. A list would be a second source of truth
  that goes stale the first time the tree gains a third sibling, which is the same trade S-024
  already refused when it declined to draw its exclusion by directory name. Today the rule reaches
  the rules module and the hooks README; that inventory is a fact about the tree on a given date and
  belongs in the conformance matrix, not in this clause.

  **Both halves are reported, and they are different findings.** A link that resolves nowhere is
  broken here and everywhere, and someone will notice. A link that reaches *above* the distributed
  tree is the half worth having: it resolves in this repository, so it reads correctly to every
  reader here, and it dangles in every installed tree, because nothing above that tree is placed
  alongside it. Reporting the second merely as broken would lose the distinction, and reporting it
  not at all is how the defect stays invisible until an adopter clicks it. The ceiling is the same
  one S-011 applies to a `SKILL.md`, so a rules file reaching a sibling skill's `SKILL.md` stays
  inside the tree and is legal, exactly as S-012 makes the reverse direction legal.

  **The sibling-skill shortcut S-010 does not apply, for S-024's reason made sharper.** From a file
  beside the skills tree, `../<name>/SKILL.md` names a sibling of *that* file's own directory, and
  the skill of that name lives at `../skills/<name>/SKILL.md` instead. Read as a skill name the link
  would be cleared whenever a real skill happened to share it, which is precisely the broken link
  this rule exists to catch. Resolved on disk like any other link it earns the ordinary S-009
  message. S-011, S-012, S-013 and S-022 apply here unchanged, as do S-024's exclusions: a file
  authored to be written into another repository is skipped by the same `.tmpl` marker, a
  non-markdown file is counted and not read, and a file the kit does not distribute is neither read
  nor counted.

  **The run must distinguish three outcomes from one another**, and that is the observable property
  this contract fixes:

  1. it declined to look at all, because the tree it was given is not a distributed layout;
  2. it looked and nothing ships there;
  3. it looked and link-checked none of what it found.

  The third and the second both involve the number zero, and the first involves no number at all, so
  a report that renders any two of them alike says nothing. This is S-024's "what it read and what it
  declined to read" carried one level up, where it is load-bearing rather than merely tidy, because a
  walk that never runs and a walk that finds nothing are the two ways this rule fails silently.

  **The first outcome exists for a reason no reader will reconstruct from the behaviour alone.** The
  validator's entry point is deliberately callable against any directory of skill folders, and for
  such a caller whatever sits beside that directory is not a distributed tree but whatever the
  filesystem happens to hold. `chore-0058` measured it rather than asserting it: roughly forty
  existing fixtures pass a bare temporary directory, whose neighbour is the system temp directory,
  holding 20,203 entries and 51 markdown files on the machine that ran the measurement. An
  unconditional walk would have read unrelated markdown off that machine and reported its broken
  links as this kit's. So declining is correct, and declining *audibly* is what this scenario
  requires.

  **How the run decides is deliberately not fixed here.** The implementation bounds the hazard by
  requiring the skills directory to be named the way every layout `install.py` places names it, which
  is a mechanism chosen for today's callers and will change if the walk root ever becomes an explicit
  parameter. Writing it into the contract would leave this document asserting a decision nobody
  revisited. What is contractual is that the run says which of the three things happened.

### Scenario S-014: contradictory status claim warns but does not fail

- **Given** a `SKILL.md` that asserts it is a draft and also records that it shipped
- **When** the validator runs
- **Then** it records a warning naming the contradiction, and (absent other errors) exits zero.
  Either assertion alone is not a contradiction and produces no finding.

### Scenario S-015: skills directory does not exist

- **Given** an invocation whose target skills directory is not present
- **When** the validator runs
- **Then** it reports the missing directory and exits non-zero, rather than reporting zero skills
  checked and succeeding.

### Scenario S-016: skills directory exists but is empty

- **Given** an invocation whose target skills directory is present and contains no skill
- **When** the validator runs
- **Then** it reports that no skills were found and exits zero, because an empty directory is a
  legitimate zero-skill result rather than an unreadable one.

### Scenario S-017: description over the harness limit fails

- **Given** a `SKILL.md` whose `description` is longer than the 1024-character limit the distribution
  targets enforce
- **When** the validator runs
- **Then** it records an error naming the measured length and that limit, and exits non-zero. A
  description at or below the limit produces no finding from this check.

### Scenario S-018: a description is measured by its value, not its YAML syntax

- **Given** a `SKILL.md` whose `description` is written as a YAML block scalar, so the field line
  carries an indicator (`>`, `>-`, `>+`, `|`, `|-`, or `|+`) and the text follows on continuation lines
- **When** the validator measures that description
- **Then** the length is of the scalar's value, excluding the indicator, so the reported number is the
  one a harness reading the same file would measure. A plain single-line description is measured
  unchanged.

### Scenario S-019: frontmatter a real YAML parser would reject fails

- **Given** a `SKILL.md` whose frontmatter holds a plain unquoted scalar containing a colon followed by
  a space, or ending in a colon, which YAML reads as a nested mapping rather than as text
- **When** the validator runs
- **Then** it records an error naming the field and exits non-zero, so the file cannot ship in a form no
  consumer can read. The same text quoted, or written as a block scalar, produces no finding, because
  both are valid YAML.

### Scenario S-020: a description containing an angle bracket fails

- **Given** a `SKILL.md` whose `description` value contains `<` or `>`
- **When** the validator runs
- **Then** it records an error naming the field and the schema rule, and exits non-zero. The check reads
  the parsed value, so a description written as a block scalar is not flagged for the `>` in its own
  indicator.

### Scenario S-021: a frontmatter property outside the schema fails

- **Given** a `SKILL.md` whose frontmatter declares a key other than `name`, `description`, `license`,
  `allowed-tools`, `metadata`, or `compatibility`
- **When** the validator runs
- **Then** it records an error naming the offending key and the permitted set, and exits non-zero,
  because the schema rejects an unrecognised property outright rather than ignoring it.

### Scenario S-023: a self-declared lens that no skill references fails

- **Given** a file in the sibling rules module whose opening presents it as a lens, either by naming
  itself one or by the "swappable module" formula that directory uses as a header convention, and no
  `SKILL.md` anywhere in the tree that references it
- **When** the validator runs
- **Then** it records an error naming that file and exits non-zero, because a lens is composed rather
  than run: it reaches an agent only through a skill that points at it, so one nobody points at is
  inert and an adopter who rewrites it changes nothing.

  This is the only rule in this contract about a file that is **not a skill**, and the only one whose
  subject is the absence of an inbound reference rather than the state of an outbound one. Every other
  rule above is checked per skill; this one is a fact about every skill together, so an unreferenced
  lens is reported once, not once per skill that failed to reference it. That is also why the gap
  existed long enough to need a rule: nothing here read the rules directory at all, so a lens shipped
  calling itself the third beside two others while no skill composed it, and every gate passed
  (`feat-0048`).

  **What counts as a reference** is the lens's filename appearing in a `SKILL.md`. A relative link to
  the module counts, and so does prose naming the file, because the portability contract in
  `AGENTS.md` tells a skill to name some files in prose rather than link to them, and requiring a link
  specifically would push an author to break one rule to satisfy another. A bare subject-word mention
  is deliberately not a reference: a skill that discusses autonomy without ever naming `autonomy.md`
  would satisfy the rule while leaving a reader no way to reach the module, which is the failure the
  rule exists to catch rather than a lesser form of compliance.

  **A reference does not make the lens canonical** over the referencing skill's own inline prose. The
  rule is about reachability only: it asks that at least one skill point at the module, not that any
  skill defer to it. Stating it the other way would contradict the module being wired in, since
  `autonomy.md`'s own Scope section says a skill may state a local exception, and the same is true of
  the other two lenses. Which of a skill's inline rules should be thinned in favour of a lens it now
  points at is an editorial question this validator has no view on.

  **The declaration is read in the file's opening**, not anywhere in its body. A rules-directory
  document that merely mentions a lens further down, such as one describing what its neighbours are,
  is not conscripted into being one, and a rules file that never declares itself a lens is under no
  obligation to be referenced by anything. That bound is what keeps the rule usable: it reads files
  nobody asked it to lint, so a finding against a document whose author never opted into being a lens
  invites deleting the rule rather than satisfying it.

## Proposed Surface

| Element | Detail |
|---|---|
| Invocation | `python scripts/validate-skills.py` |
| What it reads | every skill directory under the target skills directory, in full rather than its `SKILL.md` alone: the body, plus the files the kit distributes beside it, of which the markdown is read for S-024 and the rest is counted without being opened. Plus the rest of the distributed tree that skills directory sits in (`.agents/` for the default target, holding the rules module and the hooks module): its markdown is read for S-025, and a rules file is read for S-023 as well, while the rest is counted without being opened. Nothing above that tree is read. The walk outside the skills directory does not always run, and S-025 requires the run to say when it did not. |
| Exit code | non-zero when any error is recorded, zero otherwise (warnings do not fail) |
| Output | per-issue `WARN`/`ERROR` lines, then a `Checked N skill(s): E error(s), W warning(s).` summary, then a second line reporting how many supporting files were link-checked and how many were skipped, by reason (S-024), and on that same second line what the walk outside the skills directory covered (S-025). That second half must make the three outcomes S-025 names distinguishable from one another: a run that declined to look, a run that looked and found nothing shipped there, and a run that looked and link-checked none of what it found. What is fixed is that the three are told apart, not which words or numbers tell them apart. When the skills directory is absent, a missing-directory error instead of both summary lines; when it is present but empty, a no-skills-found line instead of both. The count `N` is of skills, so an S-023, S-024 or S-025 error raises the error count without changing it. |

## Open Questions

None.
