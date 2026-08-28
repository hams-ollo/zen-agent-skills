#!/usr/bin/env python3
"""Check that a conformance matrix's cited evidence still resolves in the file it names.

    python scripts/check-citations.py

A conformance matrix under `docs/spec/` asserts things about code: that a symbol exists,
that a test exists, that a phrase appears in a file. Nothing checked any of it. `bug-0037`
measured 65 pointers in one matrix and found seven pointing at something other than what
they claimed, from two independent causes in one month, and `chore-0049` exists because
two causes in one month is a class rather than an incident.

Citations here are by symbol, section heading, or quoted phrase, never by line number:
`bug-0037` removed line anchors on purpose and this checker deliberately does not make
them safe again. It decides three forms, none of which is a line anchor.

Exit codes
----------
    0   every citation this checker can decide still resolves
    1   at least one citation no longer resolves
    2   the check could not run: no matrix was found, so the question was never asked

The 2 branch is the one worth explaining. A checker that reports `ok` over a directory
holding nothing is the exact defect this task belongs to a group of, so this one is asked
the degenerate question at birth: no matrices means no answer, not a clean answer.

What is decided, and what is declined
-------------------------------------
The design problem is false positives, not coverage. A check that cries wolf gets
disabled within a week, which is why `check-provenance.py` is deliberately kept out of
required CI, and a noisy checker a later task switches off is worse than no checker
because it looks like coverage. So this prefers a small set of high-confidence failures,
and **anything it cannot decide is reported unchecked rather than treated as passing**,
following the coverage-proof habit `spec-conformance` already uses.

Three forms are decided:

| Form | Recognised as | Decided against | Why it is decidable |
|---|---|---|---|
| Test name | `test_*`, anywhere in a matrix row | a `def` under `tests/` | a test name is a Python function name, so no file attribution is needed at all |
| Symbol | `name(...)` or `UPPER_SNAKE`, in the Evidence column | word-boundary presence in a candidate | a renamed symbol leaves the file entirely |
| Quoted phrase | a multi-token span, in the Evidence column | normalised substring of a candidate | a substring test against a named file |

Everything else is unchecked and counted as such: single words, flags, task and scenario
ids, bare filenames, prose, section headings named in running text rather than in
backticks, and every span outside a matrix row.

Subject attribution, and why it is deliberately generous
--------------------------------------------------------
A citation needs a file to be checked against, and matrices name that file in several
ways: in the header prose that says what the matrix audits, as `` `file.py` / `symbol` ``
in a cell, as a markdown link inside a cell, or as a bare backticked filename in a
sentence. An earlier version of this checker attributed by position, taking the most
recent `` `file` / `` marker as the subject of every span after it. Measured against the
real corpus on 2026-08-28, that produced false positives and no true findings: the S-005
row of `tracker-links.conformance.md` cites `pr-describe`'s clause and then, in the same
cell, `EXTERNAL_RE`, which lives in `.tasks/validate.py`, and positional attribution
checked the second against the first.

So attribution does not guess. Every file a row names becomes a **candidate**, and a
citation resolves if it resolves in any candidate. For a single-subject matrix this is
identical to naming the file outright. For a multi-subject matrix it means a citation is
reported only when it resolves in none of the files that row names, which is the
conservative direction: the failure this checker is built for is a symbol renamed or a
phrase edited, and either removes the text from every candidate at once.

Three normalisations, each of which can only create a match
------------------------------------------------------------
Applied in turn to a quoted phrase, because each was a verified false positive on the
real corpus rather than a hypothetical:

1. **Whitespace collapsed**, on both sides. A citation writes on one line what the source
   wraps over several.
2. **Full-line comments removed** from the source. `cloud-executable.conformance.md`'s
   S-010 row cites `if reachable(project_root, home): return None`, and the hook has two
   comment lines between the guard and the return. The citation is correct.
3. **Quote characters removed**, on both sides. The bootstrap-registration row cites
   `matcher: "startup"` where `.claude/settings.json` holds `"matcher": "startup"`. A
   citation may render quoting differently from the source it quotes, and a difference in
   quoting is not the staleness anyone is looking for.

A widening can only turn a report into silence, never the reverse, so each is safe in the
direction that matters. Each was adopted only after reading the source and confirming by
hand that the flagged citation was correct.

The elision rule
----------------
**A quoted phrase carrying `...` or an angle-bracket placeholder like `<name>` is a
signposted elision, and is unchecked rather than unresolved.** An author who writes `...`
has said they are standing in for text rather than quoting it, so it is a substring of
nothing and a substring test cannot decide it. Three rows in
`build-adapters.conformance.md` are written this way and all three are correct as
written: `SHARED/skills/<name>/<target>` in S-007, `any(start <= m.start() < end ...)` in
S-018, and `for fname, obj in ...` in S-015. A naive matcher fires on all three, and
three false positives on the first run is how a gate gets switched off.

A builtin is unchecked for the same reason a check that cannot fail is unchecked: `sum()`
appears in `build-adapters.conformance.md` as prose about a builtin call, and asserting
that `sum` is present in a Python file is a test with no failing case.

Standard library only.
"""
from __future__ import annotations

import builtins
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The corpus. Globbed rather than listed, because a hardcoded list silently excludes
# every matrix written after it, which is the same failure `run-checks.py`'s doc-links
# gate avoids by globbing.
MATRIX_DIR = ("docs", "spec")
MATRIX_GLOB = "*.conformance.md"

# Where a cited test name must be defined. A test name needs no subject file, which is
# what makes it the highest-confidence form here.
TEST_DIR = "tests"

# Directories never walked when indexing the repository's files by basename.
#
# `.claude/worktrees` is named by path rather than by the bare word, which is generic
# enough to belong to something real one day. It is where `fix-batch` puts an agent's
# isolated checkout, so a machine mid-batch holds a second copy of every script in this
# repository. That is not a cosmetic slowdown: the index resolves a bare `` `install.py` ``
# only when exactly one file carries the name, so a stray checkout would silently stop
# resolving it, and every phrase cited against that file would be reported unresolved. A
# guard whose findings depend on whether someone happens to have a worktree open is worse
# than one that reports nothing.
UNINDEXED = {".git", "__pycache__", ".tmp", "node_modules", ".venv", "venv"}
UNINDEXED_PATHS = ((".claude", "worktrees"),)

BUILTIN_NAMES = frozenset(dir(builtins))

LINK_LABELLED = re.compile(r"\[`([^`]+)`\]\(([^)]+)\)")
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")
SPAN = re.compile(r"`([^`]+)`")
FILE_THEN_SLASH = re.compile(r"`([^`]+)`\s*/")
DEFINITION = re.compile(r"^[ \t]*(?:def|class)[ \t]+([A-Za-z_][A-Za-z0-9_]*)", re.M)
FULL_LINE_COMMENT = re.compile(r"^[ \t]*#.*$", re.M)

TEST_NAME = re.compile(r"^test_[A-Za-z0-9_]+$")
CALL_FORM = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\(.*\)$",
                       re.S)
CONSTANT_FORM = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
ELISION = re.compile(r"\.\.\.|<[A-Za-z][A-Za-z0-9_ -]*>")

# A phrase shorter than this is a word, not a quotation, and checking it against a whole
# file is close to a coin toss. Calibrated against the corpus rather than chosen: below
# it the spans are flags, ids, and single identifiers, none of which is a quoted phrase.
MIN_PHRASE_LENGTH = 9

UNCHECKED_ELISION = "signposted elision"
UNCHECKED_NO_SUBJECT = "no resolvable subject file"
UNCHECKED_BUILTIN = "builtin name whose presence test could not fail"
UNCHECKED_FORM = "not a decidable citation form"


class Citation:
    """One cited thing, with what became of it.

    `status` is one of `resolved`, `unresolved`, `unchecked`. The third is not a soft
    failure and not a soft pass: it is the checker saying it did not ask, which is the
    only honest answer for a form it cannot decide.
    """

    def __init__(self, matrix, item, kind, text, status, reason="", candidates=()):
        self.matrix = matrix
        self.item = item
        self.kind = kind
        self.text = text
        self.status = status
        self.reason = reason
        self.candidates = list(candidates)


def _tally(values):
    """Count occurrences, as a plain dict, so a breakdown is one entry per input."""
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


class Result:
    """Everything one run learned, so the report and the tests read the same numbers.

    Both breakdowns are derived from one partition of `citations`, so every citation
    contributes exactly one entry to exactly one of them. That is what makes
    `sum(audited_kinds().values()) == audited` and
    `sum(unaudited_reasons().values()) == unaudited` true by construction rather than by
    luck, and the shape is deliberate rather than tidy.

    The first version of this class exposed a single `kinds(status=None)` helper and the
    report called it without the argument, so the printed audited breakdown counted every
    citation of each form, including the five that have a decidable form and were
    deliberately not audited: two signposted elisions and three builtin names. It printed
    `quoted phrase 110, symbol 235, test name 56` beneath the total 396, and those sum to
    401. A coverage proof whose own arithmetic does not close is the exact failure this
    checker exists to make findable, so the shape that permitted it is gone rather than
    corrected at the one call site that happened to be wrong.
    """

    def __init__(self, matrices, citations):
        self.matrices = list(matrices)
        self.citations = list(citations)

    def _partition(self):
        """`(audited, unaudited)`, with every citation in exactly one half."""
        audited, unaudited = [], []
        for citation in self.citations:
            half = unaudited if citation.status == "unchecked" else audited
            half.append(citation)
        return audited, unaudited

    @property
    def extracted(self):
        return len(self.citations)

    @property
    def audited(self):
        return len(self._partition()[0])

    @property
    def unaudited(self):
        return len(self._partition()[1])

    @property
    def unresolved(self):
        return [c for c in self.citations if c.status == "unresolved"]

    def audited_kinds(self):
        """What was actually decided, by form. Sums to `audited`."""
        return _tally(c.kind for c in self._partition()[0])

    def unaudited_reasons(self):
        """What was declined, and why. Sums to `unaudited`."""
        return _tally(c.reason for c in self._partition()[1])


def matrices_under(root):
    """Every conformance matrix, sorted, so a run's report is stable across platforms."""
    return sorted((Path(root) / Path(*MATRIX_DIR)).glob(MATRIX_GLOB))


def _index_by_basename(root):
    """Every file in the tree, grouped by basename.

    Used only to resolve a filename a matrix names without linking to it, such as
    `` `install.py` / `check()` `` in a matrix whose header never mentions `install.py`.
    A basename with more than one holder is not resolved at all, because picking one
    would be a guess, and a guess is what this checker is built not to make.
    """
    root = Path(root).resolve()
    excluded = {root.joinpath(*parts) for parts in UNINDEXED_PATHS}
    index = {}
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.name in UNINDEXED or entry in excluded:
                continue
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                index.setdefault(entry.name, []).append(entry)
    return index


def _defined_test_names(root):
    names = set()
    tests = Path(root) / TEST_DIR
    if not tests.is_dir():
        return names
    for path in sorted(tests.rglob("*.py")):
        names |= set(DEFINITION.findall(_read(path)))
    return names


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def _unquoted(text):
    return text.replace('"', "").replace("'", "")


class _Sources:
    """Reads each candidate file once and keeps the four forms a phrase is tried against."""

    def __init__(self):
        self._cache = {}

    def variants(self, path):
        key = str(path)
        if key not in self._cache:
            text = _read(path)
            plain = _collapse(text)
            uncommented = _collapse(FULL_LINE_COMMENT.sub("", text))
            self._cache[key] = (plain, uncommented,
                                _unquoted(plain), _unquoted(uncommented))
        return self._cache[key]


def _rows(text):
    """Every markdown table row in a matrix, as a list of cells.

    Split on ` | ` rather than `|` on purpose: cells here routinely contain a pipe inside
    a code span, and splitting on the bare character would tear those rows apart.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            yield [cell.strip() for cell in stripped[1:-1].split(" | ")]


def _is_body_row(cells):
    """A data row, as opposed to a header row or the `|---|` separator beneath it."""
    return (len(cells) >= 4
            and cells[0] not in ("Section", "Item")
            and not set(cells[0]) <= set("-: "))


def _header_subjects(matrix, text):
    """The files a matrix says it audits, from the prose above its first table.

    Files under the matrix's own directory are excluded here: a matrix links to its spec
    and to neighbouring matrices for cross-reference, and treating those as subjects
    would let a citation resolve against the contract it is auditing rather than against
    the code. Its own ledger siblings are added back by `_ledger_siblings()`, which is a
    narrower rule than "anything in this directory".
    """
    head = text.split("## Matrix")[0]
    spec_dir = matrix.parent.resolve()
    found = []
    for _label, target in LINK_LABELLED.findall(head):
        path = _resolve(matrix, target)
        if path is not None and spec_dir not in path.parents and path not in found:
            found.append(path)
    return found


def _ledger_siblings(matrix):
    """This spec's own verification, readiness, characterization and runbook records.

    A matrix cites these as superseded evidence, and it does so in prose that no rule can
    follow: `cloud-executable.conformance.md`'s S-018 row cites
    `evidence_owed: S-017, S-018, S-019` and names its source only as "Same record",
    meaning the verification ledger linked in the row above it. Verified by hand on
    2026-08-28, that citation is correct and sits at the top of
    `cloud-executable.verification.md`.

    The spec itself, `<stem>.md`, is deliberately not included. Resolving a citation
    against the contract it audits is the one direction that would make this checker
    agree with a matrix by reading the matrix's own source of truth.
    """
    suffix = ".conformance.md"
    if not matrix.name.endswith(suffix):
        return []
    stem = matrix.name[:-len(suffix)]
    return [p for p in sorted(matrix.parent.glob(f"{stem}.*.md"))
            if p.resolve() != matrix.resolve()]


def _resolve(matrix, target):
    try:
        path = (matrix.parent / target.split("#")[0]).resolve()
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def _row_candidates(matrix, cell, subjects, index):
    """The subjects, plus every file this row names for itself.

    Three ways a row names a file, all of them used in the real corpus: as
    `` `file.py` / `` before a citation, as a markdown link, and as a bare backticked
    filename in a sentence, which is how the bootstrap-registration row names
    `.claude/settings.json`.
    """
    candidates = list(subjects)

    def add(path):
        if path is not None and path not in candidates:
            candidates.append(path)

    for target in LINK_TARGET.findall(cell):
        add(_resolve(matrix, target))
    named = set(FILE_THEN_SLASH.findall(cell)) | set(SPAN.findall(cell))
    for span in named:
        holders = index.get(Path(span.strip()).name, [])
        if len(holders) == 1:
            add(holders[0])
    return candidates


def _classify(span):
    """Which of the three decided forms a span is, or None when it is none of them.

    Order matters. A call form is examined before the elision rule so that
    `check_lenses_are_composed(portable_root / "rules", ...)` is checked as the symbol it
    names rather than dismissed for the `...` inside its arguments, while
    `for fname, obj in ...`, which names no symbol, falls through to the elision rule.
    """
    if TEST_NAME.match(span):
        return "test name", span
    call = CALL_FORM.match(span)
    if call:
        return "symbol", call.group(1).split(".")[-1]
    if CONSTANT_FORM.match(span):
        return "symbol", span
    if " " in span.strip() and len(span) >= MIN_PHRASE_LENGTH:
        return "quoted phrase", span
    return None, None


def audit(root=None):
    """Read every matrix and decide every citation in it. Returns a `Result`."""
    root = REPO_ROOT if root is None else Path(root)
    matrices = matrices_under(root)
    index = _index_by_basename(root)
    test_names = _defined_test_names(root)
    sources = _Sources()
    citations = []

    for matrix in matrices:
        text = _read(matrix)
        subjects = _header_subjects(matrix, text) + _ledger_siblings(matrix)
        for cells in _rows(text):
            if not _is_body_row(cells):
                continue
            item = cells[1]
            seen_tests = set()
            for span in SPAN.findall(" ".join(cells)):
                if TEST_NAME.match(span) and span not in seen_tests:
                    seen_tests.add(span)
                    citations.append(Citation(
                        matrix, item, "test name", span,
                        "resolved" if span in test_names else "unresolved"))
            evidence = cells[3]
            candidates = _row_candidates(matrix, evidence, subjects, index)
            for span in SPAN.findall(evidence):
                kind, needle = _classify(span)
                if kind is None:
                    citations.append(Citation(matrix, item, "other", span,
                                              "unchecked", UNCHECKED_FORM))
                    continue
                if kind == "test name":
                    continue  # already recorded once, from the whole row
                if kind == "symbol" and needle in BUILTIN_NAMES:
                    citations.append(Citation(matrix, item, kind, span,
                                              "unchecked", UNCHECKED_BUILTIN))
                    continue
                if kind == "quoted phrase" and ELISION.search(span):
                    citations.append(Citation(matrix, item, kind, span,
                                              "unchecked", UNCHECKED_ELISION))
                    continue
                if not candidates:
                    citations.append(Citation(matrix, item, kind, span,
                                              "unchecked", UNCHECKED_NO_SUBJECT))
                    continue
                citations.append(Citation(
                    matrix, item, kind, span,
                    "resolved" if _resolves(kind, needle, candidates, sources)
                    else "unresolved",
                    candidates=candidates))
    return Result(matrices, citations)


def _resolves(kind, needle, candidates, sources):
    if kind == "symbol":
        pattern = re.compile(r"\b%s\b" % re.escape(needle))
        return any(pattern.search(sources.variants(c)[0]) for c in candidates)
    collapsed = _collapse(needle)
    unquoted = _unquoted(collapsed)
    for candidate in candidates:
        plain, uncommented, plain_q, uncommented_q = sources.variants(candidate)
        if (collapsed in plain or collapsed in uncommented
                or unquoted in plain_q or unquoted in uncommented_q):
            return True
    return False


def _relative(path, root):
    """A repository-relative, forward-slash path, or the basename when it escapes.

    Both sides are resolved before comparing. A path built from an unresolved root and
    one recorded from a resolved root are different strings on macOS, where `/var`
    resolves to `/private/var`, and on Windows, where a runner is reached by an 8.3 short
    name. Comparing unresolved to resolved passes locally and fails on four of six CI
    cells, which has happened here before.
    """
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name


def report(result, root, out):
    """Write the findings, then the coverage proof. Returns the exit code."""
    if not result.matrices:
        out.write(f"could not run: no conformance matrices under "
                  f"{'/'.join(MATRIX_DIR)}/{MATRIX_GLOB}\n")
        return 2

    unresolved = result.unresolved
    for citation in unresolved:
        where = _relative(citation.matrix, root)
        named = ", ".join(sorted(_relative(c, root) for c in citation.candidates))
        out.write(f"{where}\n")
        out.write(f"    {citation.item}\n")
        out.write(f"    {citation.kind} `{citation.text}` no longer resolves in "
                  f"{named or 'any file this row names'}\n")

    if unresolved:
        out.write("\nA citation that no longer resolves is a pointer problem, not "
                  "automatically a wrong verdict.\nRe-derive the row against the current "
                  "code before repointing it: a citation repaired without\nre-deriving "
                  "what it supports asserts a freshness the repair did not establish.\n\n")

    # No `if kind != "other"` filter here any more, and none is needed: every citation of
    # the `other` kind is unchecked by construction, so the audited half never holds one.
    # That filter was part of what disguised the arithmetic defect described on `Result`.
    audited_kinds = ", ".join(f"{kind} {count}" for kind, count
                              in sorted(result.audited_kinds().items())) or "nothing"
    reasons = ", ".join(f"{reason} {count}" for reason, count
                        in sorted(result.unaudited_reasons().items())) or "nothing"
    out.write(f"Matrix citations: {len(unresolved)} unresolved.\n")
    out.write(f"Audited {result.audited} of {result.extracted} citation(s) "
              f"by decidable form: {audited_kinds}.\n")
    out.write(f"Unaudited {result.unaudited} of {result.extracted}, reported rather than "
              f"assumed to pass: {reasons}.\n")
    # Last, and carrying a digit, because run-checks.py surfaces the last such line
    # beneath this gate's status word. It has to vary with what was examined, or the gate
    # reports coverage it did not have (bug-0045, and chore-0064 for the lesson that a
    # line which cannot vary is the same defect one level down).
    out.write(f"{result.audited} audited + {result.unaudited} unaudited = "
              f"{result.extracted} extracted, over {len(result.matrices)} matrix file(s) "
              f"holding {len(set(str(c.matrix) for c in result.citations))} with "
              f"citations.\n")
    return 1 if unresolved else 0


def main(argv=None, out=None, root=None) -> int:
    """Entry point. Takes no options; `argv` exists only to reject any that are passed."""
    argv = sys.argv[1:] if argv is None else argv
    out = sys.stdout if out is None else out
    if argv:
        out.write("check-citations.py takes no arguments; it checks every matrix, "
                  "always.\n")
        return 2
    root = REPO_ROOT if root is None else Path(root)
    return report(audit(root), root, out)


if __name__ == "__main__":
    raise SystemExit(main())
