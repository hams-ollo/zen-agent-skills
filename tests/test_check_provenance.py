"""Acceptance tests for scripts/check-provenance.py.

Covers feat-0043: the provenance convention stated in the conventions section of AGENTS.md,
exercised through the checker that enforces it. Standard library only, per that same section.

test-quality notes: every scenario runs at the lowest faithful layer, calling main() with an
injected fetcher and an injected root rather than spawning a subprocess or touching the
network. A test that hits GitHub is a test that fails when GitHub is slow, and it would prove
the network works rather than that the comparison does. The fetcher seam exists for exactly
this reason.

Oracles assert the exact exit code plus the specific text the caller needs (the drifted URL,
the recorded and upstream digests), never "does not crash". A checker that fetched nothing and
printed nothing would also not crash, and would also exit 0.

The defect each group protects against:
  match         - the comparison passes everything, so drift is never reported at all
  drift         - drift is detected but the output does not say which source moved,
                  leaving a non-zero exit with nothing to act on
  unreachable   - the network is down and the script dies in a traceback, which reads as a
                  defect in the script rather than as an unreachable host
  unlocatable   - an honestly-recorded unlocatable source is treated as a failure, which
                  would pressure the next author into guessing a URL instead of recording
                  the truth: the exact failure the convention exists to prevent
  malformed     - a record missing its digest, or carrying a placeholder one, passes silently
  https only    - a record pins a plaintext http:// source, so the digest is taken over bytes
                  nobody authenticated, and the check quietly certifies them
  read bound    - a hostile or merely enormous URL is read into memory whole, or a truncated
                  read is compared and reported as drift, which is the wrong word for the
                  wrong reason
  blank line    - one blank line inside a block deletes the record from the run entirely,
                  and the checker reports a clean count nobody has reason to doubt
  unreadable    - a file the process cannot read drops every record it carries, is named
                  nowhere, and leaves a narrowed count that reads exactly like a clean one
  misspelled    - one mistyped field name after `source:` deletes the whole block from the
                  run, at exit 0, and the fix for it goes too far the other way and starts
                  reporting a template's own `source:` field as a broken fold-in
  unsourced     - a placement whose `source:` key is mistyped, or that carries no source
                  line at all, yields no record at all, so the run prints the clean empty
                  state of a repository with nothing folded in
  suffix case   - a file whose suffix an author typed uppercase is never selected, so
                  every record it carries leaves the run and no count records the file
  marker case   - the two placement markers answer differently on the same word, so a
                  docstring headed `provenance` is not a declared placement at all and
                  every malformed block inside it drops back out of the run, at exit 0
  real records  - a backfilled block in this repository is malformed and nobody notices
                  until the day someone runs the checker with a network
"""
import contextlib
import hashlib
import importlib.util
import io
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "check-provenance.py"

# Hyphenated filename, so it is not importable by a normal import statement.
_spec = importlib.util.spec_from_file_location("check_provenance", MODULE_PATH)
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

UPSTREAM = b"# upstream content\nthe bytes we adapted from\n"
UPSTREAM_SHA = hashlib.sha256(UPSTREAM).hexdigest()
URL = "https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/skills/x/SKILL.md"


def block(sha=UPSTREAM_SHA, url=URL, retrieved="2026-08-06", gap=""):
    """One provenance block. `gap="\\n"` puts a blank line after `source:` (bug-0016)."""
    return (
        "## Provenance\n\n"
        "```provenance\n"
        f"source: {url}\n"
        f"{gap}"
        "author: Balarama Bosch\n"
        "license: MIT\n"
        f"retrieved: {retrieved}\n"
        f"sha256: {sha}\n"
        "```\n"
    )


FENCE = "`" * 3


def provenance_fence(*lines):
    """A declared markdown placement carrying exactly `lines`, well formed or not.

    block() cannot express these: every shape below is missing the `source:` line that
    block() is built around, and one of them is missing every line.
    """
    body = "".join(f"{line}\n" for line in lines)
    return f"## Provenance\n\n{FENCE}provenance\n{body}{FENCE}\n"


def make_root(body, filename="SKILL.md"):
    """A throwaway repository root carrying one adapted file under a scanned directory.

    The local body is deliberately unlike UPSTREAM: the digest must be compared against the
    fetched bytes, not against the adapted file, and a fixture where the two matched would
    hide a checker that digested the wrong thing.

    `filename` exists for bug-0046, where the question is which files get read at all rather
    than what is inside them. One file per root, because a case-insensitive filesystem cannot
    hold `SKILL.md` and `SKILL.MD` side by side.
    """
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    skill = root / ".agents" / "skills" / "x"
    skill.mkdir(parents=True)
    (skill / filename).write_bytes(
        ("---\nname: x\n---\n\n# X\n\nHouse-styled and retargeted, so it differs from upstream.\n\n"
         + body).encode("utf-8")
    )
    return tmp, root


def run(body, fetcher, argv=(), filename="SKILL.md"):
    tmp, root = make_root(body, filename=filename)
    try:
        out = io.StringIO()
        code = cp.main(argv=list(argv), root=root, fetcher=fetcher, out=out)
        return code, out.getvalue()
    finally:
        tmp.cleanup()


LOCKED_URL = URL.replace("skills/x/", "skills/locked/")

_REAL_READ_TEXT = Path.read_text


def deny_reads(*skills):
    """Make `read_text` raise for the named skills, and read every other file normally.

    A stubbed failure rather than a real lock. An exclusive handle (`dwShareMode=0`) is a
    Windows-only trick, and the property under test is what the checker does with an
    OSError, not how an operating system produces one.
    """

    def read_text(self, *args, **kwargs):
        if self.parent.name in skills:
            raise PermissionError(13, "Permission denied")
        return _REAL_READ_TEXT(self, *args, **kwargs)

    return unittest.mock.patch.object(Path, "read_text", read_text)


def make_pair_root():
    """A root with two adapted files, each carrying one record, under separate skills."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for name, url in (("locked", LOCKED_URL), ("readable", URL)):
        skill = root / ".agents" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_bytes(
            (f"---\nname: {name}\n---\n\n# {name}\n\nAdapted, so it differs from upstream.\n\n"
             + block(url=url)).encode("utf-8")
        )
    return tmp, root


def run_pair(fetcher, argv=(), denied=("locked",)):
    """Run against that pair with the named skills' files made unreadable."""
    tmp, root = make_pair_root()
    try:
        out = io.StringIO()
        with deny_reads(*denied) if denied else contextlib.nullcontext():
            code = cp.main(argv=list(argv), root=root, fetcher=fetcher, out=out)
        return code, out.getvalue()
    finally:
        tmp.cleanup()


def serve(content):
    def fetcher(url, timeout=30):
        return content
    return fetcher


def unreachable(exc):
    def fetcher(url, timeout=30):
        raise exc
    return fetcher


class _FakeResponse:
    """The parts of an HTTP response `fetch()` uses, counting the bytes it hands over."""

    def __init__(self, payload, url=URL):
        self._buffer = io.BytesIO(payload)
        self.bytes_read = 0
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self, amount=None):
        chunk = self._buffer.read() if amount is None else self._buffer.read(amount)
        self.bytes_read += len(chunk)
        return chunk

    def geturl(self):
        # `fetch()` asks where the bytes came from, so a stand-in response has to answer.
        # Defaults to the recorded URL, which is the no-redirect case these tests are about.
        return self._url


class _fake_urlopen:
    """Serve `payload` to `fetch()` without a socket, and expose the response it served.

    `fetch()` is the one function with no injection seam, because the seam the rest of this
    file uses replaces it. Its read bound therefore has to be exercised against a stand-in
    response rather than a stand-in fetcher, and still without a socket.

    Patches the module's own opener rather than `urllib.request.urlopen`, because that is
    what `fetch()` calls since `bug-0054` put a redirect handler in front of it. Patching
    the function `fetch()` no longer uses would leave these three read-bound tests passing
    over a stand-in nothing consulted, which is the shape of a check that cannot fail.
    """

    def __init__(self, payload, url=URL):
        self.response = _FakeResponse(payload, url=url)
        self._patch = unittest.mock.patch.object(
            cp._OPENER, "open", lambda request, timeout=None: self.response
        )

    def __enter__(self):
        self._patch.start()
        return self.response

    def __exit__(self, *exc_info):
        self._patch.stop()
        return False


class MatchPath(unittest.TestCase):
    """The recorded digest matches what upstream currently returns."""

    def test_exits_zero_when_the_digest_matches(self):
        code, output = run(block(), serve(UPSTREAM))
        self.assertEqual(code, 0)
        self.assertIn("up to date", output)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_digest_is_taken_over_fetched_bytes_not_the_local_file(self):
        # The local file's own digest must never satisfy the record.
        tmp, root = make_root(block())
        try:
            local = (root / ".agents" / "skills" / "x" / "SKILL.md").read_bytes()
            self.assertNotEqual(hashlib.sha256(local).hexdigest(), UPSTREAM_SHA)
        finally:
            tmp.cleanup()
        code, _ = run(block(), serve(UPSTREAM))
        self.assertEqual(code, 0)
        # Serving the adapted file's bytes instead must be drift, not a pass.
        code, _ = run(block(), serve(local))
        self.assertEqual(code, 1)

    def test_url_is_requested_verbatim(self):
        seen = []

        def fetcher(url, timeout=30):
            seen.append(url)
            return UPSTREAM

        run(block(), fetcher)
        self.assertEqual(seen, [URL])


class DriftPath(unittest.TestCase):
    """Upstream has moved since the digest was recorded."""

    def test_exits_non_zero_on_drift(self):
        code, _ = run(block(), serve(b"upstream has been rewritten\n"))
        self.assertEqual(code, 1)

    def test_names_the_drifted_source_and_both_digests(self):
        moved = b"upstream has been rewritten\n"
        code, output = run(block(), serve(moved))
        self.assertEqual(code, 1)
        self.assertIn("DRIFT", output)
        self.assertIn(URL, output)
        self.assertIn(UPSTREAM_SHA, output)
        self.assertIn(hashlib.sha256(moved).hexdigest(), output)

    def test_does_not_rewrite_the_adapted_file(self):
        # Detect and report; never sync. An overwrite would destroy the adaptation.
        tmp, root = make_root(block())
        try:
            target = root / ".agents" / "skills" / "x" / "SKILL.md"
            before = target.read_bytes()
            code = cp.main(argv=[], root=root, fetcher=serve(b"moved\n"), out=io.StringIO())
            self.assertEqual(code, 1)
            self.assertEqual(target.read_bytes(), before)
        finally:
            tmp.cleanup()


class UnreachableSourcePath(unittest.TestCase):
    """The network is unavailable, or the host refuses."""

    def test_url_error_exits_two_with_a_clear_message(self):
        import urllib.error

        code, output = run(block(), unreachable(urllib.error.URLError("getaddrinfo failed")))
        self.assertEqual(code, 2)
        self.assertIn("could not fetch", output)
        self.assertIn(URL, output)
        self.assertIn("getaddrinfo failed", output)

    def test_http_error_exits_two(self):
        import urllib.error

        exc = urllib.error.HTTPError(URL, 404, "Not Found", None, None)
        code, output = run(block(), unreachable(exc))
        self.assertEqual(code, 2)
        self.assertIn("could not fetch", output)

    def test_socket_failure_does_not_escape_as_a_traceback(self):
        code, output = run(block(), unreachable(OSError("connection reset")))
        self.assertEqual(code, 2)
        self.assertIn("connection reset", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)


class UnlocatablePath(unittest.TestCase):
    """A source that genuinely cannot be found is recorded, not omitted or guessed."""

    BLOCK = (
        "## Provenance\n\n"
        "```provenance\n"
        "source: the vendored repoprompt-workflows-main snapshot, path unknown\n"
        "author: Balarama Bosch\n"
        "license: MIT\n"
        "status: unlocatable\n"
        "note: searched upstream's current tree at main; no file matches this content.\n"
        "```\n"
    )

    def test_unlocatable_is_reported_and_not_an_error(self):
        def never(url, timeout=30):
            raise AssertionError("an unlocatable record must not be fetched")

        code, output = run(self.BLOCK, never)
        self.assertEqual(code, 0)
        self.assertIn("source not locatable", output)
        self.assertIn("0 up to date, 0 drifted, 1 unlocatable, 0 error(s).", output)

    def test_unlocatable_without_a_note_is_malformed(self):
        # "unlocatable" is a finding, so it owes the search that established it. Without
        # that, the status is indistinguishable from not having looked.
        body = self.BLOCK.replace(
            "note: searched upstream's current tree at main; no file matches this content.\n", ""
        )
        code, output = run(body, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("unlocatable record is missing", output)


class MalformedRecordPath(unittest.TestCase):
    """A record that cannot be checked must fail loudly rather than pass quietly."""

    def test_missing_digest_exits_two(self):
        body = block().replace(f"sha256: {UPSTREAM_SHA}\n", "")
        code, output = run(body, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("missing required field(s): sha256", output)

    def test_placeholder_digest_exits_two(self):
        code, output = run(block(sha="TODO"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("sha256 is not 64 lowercase hex", output)

    def test_non_url_source_exits_two(self):
        code, output = run(block(url="somewhere upstream"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("source is not an absolute https:// URL", output)

    def test_malformed_retrieval_date_exits_two(self):
        code, output = run(block(retrieved="last week"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("retrieved is not an ISO date", output)


class HttpsOnlySourceTest(unittest.TestCase):
    """chore-0035: a source must be https://, because the digest authenticates nothing else.

    A plaintext source digests bytes that anyone on the path could have written, and the
    record then reads as verified provenance. Rejected for its own reason rather than
    silently upgraded to https://, because a silent upgrade makes the recorded `source:`
    differ from what was fetched, and the record is meant to be reproducible by hand.
    """

    HTTP_URL = URL.replace("https://", "http://")

    def test_an_http_source_is_reported_as_malformed(self):
        code, output = run(block(url=self.HTTP_URL), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_the_http_message_names_the_field_and_the_offending_url(self):
        # A rejection that does not say which field to edit costs the reader the search.
        code, output = run(block(url=self.HTTP_URL), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("source", output)
        self.assertIn("http://", output)
        self.assertIn(self.HTTP_URL, output)

    def test_an_http_source_is_never_fetched(self):
        def never(url, timeout=30):
            raise AssertionError("a rejected record must not be fetched")

        code, _ = run(block(url=self.HTTP_URL), never)
        self.assertEqual(code, 2)

    def test_an_https_source_still_validates(self):
        code, output = run(block(), serve(UPSTREAM))
        self.assertEqual(code, 0)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_the_scheme_is_matched_case_insensitively(self):
        # A scheme is case-insensitive per RFC 3986. Rejecting `HTTPS://` would be a new
        # failure introduced by the tightening rather than the one it was aimed at.
        self.assertIsNone(cp.validate({
            "source": URL.replace("https://", "HTTPS://"),
            "author": "Balarama Bosch",
            "license": "MIT",
            "retrieved": "2026-08-06",
            "sha256": UPSTREAM_SHA,
        }))

    def test_every_source_recorded_in_this_repository_is_https(self):
        # The real records, not fixtures. All eight were https:// before this tightening,
        # so it breaks nothing; this is the test that says so rather than a claim in a
        # commit message that nobody can re-run. Nine since `feat-0061` folded in the
        # `systematic-debugging` skill from an upstream library.
        found, _ = cp.collect(REPO_ROOT)
        self.assertEqual(len(found), 9)
        for rel, record in found:
            with self.subTest(path=rel, line=record["line"]):
                self.assertTrue(
                    record["source"].lower().startswith("https://"),
                    f"{rel}:{record['line']} pins a non-https source: {record['source']}",
                )
                self.assertIsNone(cp.validate(record), f"{rel}:{record['line']}")


class ReadBoundTest(unittest.TestCase):
    """chore-0035: the response body is read under a bound, and exceeding it is an error.

    `response.read()` with no argument reads whatever the far end sends. The bound is
    generous enough that no real source file could hit it, so hitting it means something is
    wrong with the source rather than with the record: the run must say `error`, never
    `drift`. Reporting drift would name a truncated digest as evidence upstream moved, which
    is the wrong word for the wrong reason and would invite someone to update the record.
    """

    def test_the_bound_is_documented_and_generous(self):
        # A bound nobody can name is a magic number, and one a real source could hit would
        # turn the check into a source of false errors.
        self.assertGreaterEqual(cp.MAX_FETCH_BYTES, 1024 * 1024)

    def test_fetch_returns_a_response_at_the_bound(self):
        payload = b"x" * 64
        with _fake_urlopen(payload):
            fetched = cp.fetch(URL, max_bytes=64)
        # Unchanged in intent: a body exactly at the bound comes back whole. `fetch()`
        # returns the landing URL beside the bytes since `bug-0054`, so the content is
        # reached through the field rather than compared against the whole return value.
        self.assertEqual(fetched.content, payload)
        self.assertEqual(fetched.url, URL,
                         "no redirect happened, so the landing URL is the recorded one")

    def test_fetch_raises_when_the_response_exceeds_the_bound(self):
        with _fake_urlopen(b"x" * 65):
            with self.assertRaises(ValueError) as caught:
                cp.fetch(URL, max_bytes=64)
        self.assertIn("64", str(caught.exception))

    def test_fetch_does_not_read_the_whole_oversized_body(self):
        # The point of the bound is memory, so a fetch that reads it all and then complains
        # would satisfy the message and not the requirement.
        payload = b"x" * 4096
        with _fake_urlopen(payload) as response:
            with self.assertRaises(ValueError):
                cp.fetch(URL, max_bytes=64)
        self.assertLessEqual(response.bytes_read, 65)

    def test_an_oversized_fetch_is_reported_as_an_error_not_as_drift(self):
        oversized = b"x" * (cp.MAX_FETCH_BYTES + 1)
        code, output = run(block(), serve(oversized))
        self.assertEqual(code, 2)
        self.assertNotIn("DRIFT", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_the_oversize_message_names_the_source_and_the_bound(self):
        oversized = b"x" * (cp.MAX_FETCH_BYTES + 1)
        code, output = run(block(), serve(oversized))
        self.assertEqual(code, 2)
        self.assertIn(URL, output)
        self.assertIn(str(cp.MAX_FETCH_BYTES), output)

    def test_the_size_error_raised_by_fetch_reaches_the_report_as_an_error(self):
        # The real fetch() signals the bound by raising, so the path a live run takes has
        # to land in the same bucket as the one the injected fetcher exercises.
        def oversized(url, timeout=30):
            raise cp.ResponseTooLarge("response exceeds the 10485760 byte read bound")

        code, output = run(block(), oversized)
        self.assertEqual(code, 2)
        self.assertNotIn("DRIFT", output)
        self.assertIn("could not fetch", output)
        self.assertIn(URL, output)


class ParsingTest(unittest.TestCase):
    """The block grammar reads the same in a docstring, a fenced block, and prose."""

    def test_reads_a_block_from_a_python_docstring(self):
        text = (
            '"""A hook.\n\nProvenance\n----------\n'
            f"source: {URL}\nauthor: Balarama Bosch\nlicense: MIT\n"
            f'retrieved: 2026-08-06\nsha256: {UPSTREAM_SHA}\n"""\n'
        )
        records = cp.parse_records(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], URL)
        self.assertEqual(records[0]["license"], "MIT")

    def test_reads_two_records_from_one_file(self):
        # A single adapted file may draw on more than one upstream file.
        second = URL.replace("skills/x/SKILL.md", "workflows/Deep-Review.md")
        records = cp.parse_records(block() + "\n" + block(url=second))
        self.assertEqual([r["source"] for r in records], [URL, second])

    def test_ignores_prose_that_merely_mentions_the_field_names(self):
        text = "The block carries a `source:` line, an `author:` line, and a `sha256:` line.\n"
        self.assertEqual(cp.parse_records(text), [])

    def test_ignores_an_unrelated_template_field_named_source(self):
        # The review-depth skill's output block has its own `source:` field meaning
        # "detected or user". An earlier draft of the parser reported it as a fold-in with
        # a missing digest, which would have made the checker fail on an untouched skill.
        text = (
            "depth: quick | standard | deep\n"
            "source: detected | user\n"
            "changeset: the range the signals were computed over\n"
        )
        self.assertEqual(cp.parse_records(text), [])

    def test_a_run_missing_only_its_author_is_still_reported(self):
        # Tightening the grammar must not create a hole: a real block with a typo has to
        # surface as malformed, not vanish.
        body = block().replace("author: Balarama Bosch\n", "")
        code, output = run(body, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("missing required field(s): author", output)


class BlankLineInsideABlockTest(unittest.TestCase):
    """bug-0016: one blank line inside a block deleted the record, silently, at exit 0.

    The blank line is the bug population, so every oracle here runs against a block that
    carries one. Before the fix these produced zero records, and the run printed "No
    provenance records found." and exited 0: the same output a repository with nothing
    folded in produces. So asserting "does not crash" or "exits 0" would have passed
    against the bug. The oracle has to assert the record was actually collected and
    checked.
    """

    def test_parser_keeps_a_block_whose_source_is_separated_by_a_blank_line(self):
        records = cp.parse_records(block(gap="\n"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], URL)
        self.assertEqual(records[0]["author"], "Balarama Bosch")
        self.assertEqual(records[0]["sha256"], UPSTREAM_SHA)

    def test_the_block_is_reported_in_the_counts_not_silently_absent(self):
        code, output = run(block(gap="\n"), serve(UPSTREAM))
        self.assertEqual(code, 0)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_drift_is_still_detected_across_the_blank_line(self):
        # The record has to be genuinely fetched and compared, not merely counted.
        moved = b"upstream has been rewritten\n"
        code, output = run(block(gap="\n"), serve(moved))
        self.assertEqual(code, 1)
        self.assertIn("DRIFT", output)
        self.assertIn(URL, output)
        self.assertIn(hashlib.sha256(moved).hexdigest(), output)

    def test_a_blank_line_block_missing_a_required_field_is_still_reported(self):
        # The opposite failure: a grammar tightened until nothing malformed is ever
        # reported would be a hole, not a fix. A typo must still surface.
        body = block(gap="\n").replace("author: Balarama Bosch\n", "")
        code, output = run(body, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("missing required field(s): author", output)

    def test_a_blank_line_does_not_read_across_intervening_prose(self):
        # Bounds the widening. Blank lines are transparent; prose is not. Without this, a
        # stray `source:` line would collect recognised keys from anywhere below it.
        text = (
            f"source: {URL}\n"
            "author: Balarama Bosch\n"
            "\n"
            "## An unrelated heading\n"
            "\n"
            "license: MIT\n"
        )
        records = cp.parse_records(text)
        self.assertEqual(len(records), 1)
        self.assertNotIn("license", records[0])

    def test_an_unrelated_source_field_followed_by_blank_lines_is_still_ignored(self):
        # The review-depth collision, retested against the new terminator: whitespace
        # after a template's own `source:` field must not let it reach a later key line.
        text = (
            "depth: quick | standard | deep\n"
            "source: detected | user\n"
            "\n"
            "\n"
            "Rules:\n"
            "\n"
            "license: MIT\n"
        )
        self.assertEqual(cp.parse_records(text), [])


class UnreadableFileTest(unittest.TestCase):
    """bug-0019: an unreadable file dropped every record it carried, at exit 0.

    `collect()` wrapped its read in `except OSError: continue`, so a file another process
    held open contributed no records, was named nowhere, and left a smaller count that is
    indistinguishable from a clean result. Demonstrated on 2026-08-06 by holding a Windows
    exclusive handle on one provenance-carrying file: 9 records readable, 8 records locked,
    exit 0 either way.

    So the oracles here assert the path is named and the exit code moved. "Does not crash"
    and "the other records were still checked" both passed against the bug. The fixture
    carries a second, readable file for the opposite reason: a fix that aborted on the
    first bad file would hide the state of everything after it, and a fix that failed every
    run would too.
    """

    LOCKED = ".agents/skills/locked/SKILL.md"
    READABLE = ".agents/skills/readable/SKILL.md"

    def test_the_unreadable_file_is_named_in_the_output(self):
        code, output = run_pair(serve(UPSTREAM))
        self.assertIn(self.LOCKED, output)
        self.assertIn("could not be read", output)

    def test_the_run_exits_non_zero_when_a_file_cannot_be_read(self):
        code, _ = run_pair(serve(UPSTREAM))
        self.assertEqual(code, 2)

    def test_the_readable_files_are_still_checked_and_reported(self):
        # One unreadable file must not hide the state of the others, so the readable
        # record is genuinely fetched and compared rather than merely counted.
        seen = []

        def fetcher(url, timeout=30):
            seen.append(url)
            return UPSTREAM

        code, output = run_pair(fetcher)
        self.assertEqual(code, 2)
        self.assertEqual(seen, [URL])
        self.assertIn(f"{self.READABLE}:", output)
        self.assertIn("up to date", output)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_the_failure_is_a_clear_message_not_a_traceback(self):
        # Matching the unreachable-source path: a traceback reads as a defect in this
        # script rather than as a file somebody else has open.
        code, output = run_pair(serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", output)
        self.assertIn("Permission denied", output)

    def test_the_report_says_the_counts_are_incomplete(self):
        # The count is the only number reported and nothing else states what it should
        # have been, so the run has to say the number it printed is short.
        code, output = run_pair(serve(UPSTREAM))
        self.assertIn("counts above are incomplete", output)

    def test_an_unreadable_file_is_not_reported_as_nothing_recorded(self):
        # The worst variant: when every file in scope is unreadable, the old code printed
        # the line a repository with no fold-ins prints, and exited 0.
        code, output = run_pair(serve(UPSTREAM), denied=("locked", "readable"))
        self.assertEqual(code, 2)
        self.assertNotIn("No provenance records found", output)
        self.assertIn(self.LOCKED, output)
        self.assertIn(self.READABLE, output)

    def test_list_mode_names_the_unreadable_file_and_exits_non_zero(self):
        # --list claims to print every URL a run would contact, so an unread file makes
        # that list short in the same silent way.
        def never(url, timeout=30):
            raise AssertionError("--list must fetch nothing")

        code, output = run_pair(never, argv=["--list"])
        self.assertEqual(code, 2)
        self.assertIn(self.LOCKED, output)
        self.assertIn("could not be read", output)
        self.assertIn("1 record(s).", output)

    def test_a_clean_run_still_succeeds(self):
        # The other direction. A check that failed whenever it was run would satisfy
        # every assertion above and be worthless.
        code, output = run_pair(serve(UPSTREAM), denied=())
        self.assertEqual(code, 0)
        self.assertIn("2 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)
        self.assertNotIn("could not be read", output)

    def test_collect_returns_the_failures_alongside_the_records(self):
        # At the unit layer, because this is where the records were dropped: a caller
        # cannot report what the helper never handed it.
        tmp, root = make_pair_root()
        try:
            with deny_reads("locked"):
                found, unreadable = cp.collect(root)
        finally:
            tmp.cleanup()
        self.assertEqual([rel for rel, _ in found], [self.READABLE])
        self.assertEqual([rel for rel, _ in unreadable], [self.LOCKED])
        self.assertIn("Permission denied", unreadable[0][1])


DOCSTRING_BLOCK = (
    '"""A hook.\n'
    "\n"
    "Provenance\n"
    "----------\n"
    f"source: {URL}\n"
    "author: Balarama Bosch\n"
    "license: MIT\n"
    "retrieved: 2026-08-06\n"
    f"sha256: {UPSTREAM_SHA}\n"
    '"""\n'
)


def docstring_block(heading="Provenance", underline="----------"):
    """DOCSTRING_BLOCK with its placement marker respelled, for bug-0047.

    Derived from the one fixture rather than copied, so a marker-case test can never drift
    into exercising a differently-shaped block than the tests above it.

    Both halves of the marker are parameters because both are load-bearing: a docstring
    placement is an underlined heading, not a heading. Varying `underline` is how the tests
    below hold the bound the widened heading match relies on.
    """
    return DOCSTRING_BLOCK.replace("Provenance", heading, 1).replace("----------", underline, 1)


class MisspelledFieldTest(unittest.TestCase):
    """bug-0041: a typo on the field after `source:` deleted the whole block, at exit 0.

    The run ended on the mistyped line with only `source` collected, which failed the same
    "at least one other recognised key" test that keeps `review-depth`'s unrelated `source:`
    field out of the record set. So the block did not become malformed, it stopped existing:
    no line in the output, no count, exit 0, and the upstream it credits never re-fetched
    again. Asserting "the well-formed block still parses" would have passed against that,
    because the well-formed block always did. The oracle has to be the mistyped one.

    The opposite failure is live and is why the fix keys on placement rather than on the
    field name: `review-depth`'s output template really does carry a `source:` line, inside
    a ```text fence, and any rule that turns every bare `source:` run into a record makes
    the checker fail on a skill nobody touched. Both directions are tested here.
    """

    def test_the_record_survives_a_misspelled_field(self):
        records = cp.parse_records(block().replace("author:", "authr:"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], URL)

    def test_the_run_names_the_file_and_the_misspelled_field(self):
        code, output = run(block().replace("author:", "authr:"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn(".agents/skills/x/SKILL.md", output)
        self.assertIn("authr", output)

    def test_the_misspelled_block_is_counted_as_an_error_not_as_nothing(self):
        # The bug's signature is a count that looks clean, so the count is the oracle.
        code, output = run(block().replace("author:", "authr:"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_a_malformed_block_is_never_fetched(self):
        def never(url, timeout=30):
            raise AssertionError("a record that cannot be checked must not be fetched")

        code, _ = run(block().replace("author:", "authr:"), never)
        self.assertEqual(code, 2)

    def test_a_typo_on_the_last_field_is_reported_too(self):
        # `note:` is optional, so the run had already collected every required field. The
        # block is still mistyped, and a checker that shrugs at it teaches the next author
        # that some field names are approximate.
        body = block()[:-4] + "notes: backfilled baseline\n```\n"
        code, output = run(body, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("notes", output)

    def test_the_docstring_placement_reports_a_misspelled_field_the_same_way(self):
        # The convention names two placements and the hooks use this one. A fix that only
        # understood markdown fences would leave half the tree exactly as it was.
        code, output = run(DOCSTRING_BLOCK.replace("author:", "authr:"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("authr", output)

    def test_the_docstring_placement_still_parses_when_it_is_well_formed(self):
        code, output = run(DOCSTRING_BLOCK, serve(UPSTREAM))
        self.assertEqual(code, 0)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_an_unlocatable_record_is_not_made_malformed_by_the_placement_rule(self):
        # The same family in the opposite direction: `status: unlocatable` legitimately
        # omits `retrieved` and `sha256`, so a placement rule paired with a naive
        # required-keys check would report every honest unlocatable record as broken.
        def never(url, timeout=30):
            raise AssertionError("an unlocatable record must not be fetched")

        code, output = run(UnlocatablePath.BLOCK, never)
        self.assertEqual(code, 0)
        self.assertIn("0 up to date, 0 drifted, 1 unlocatable, 0 error(s).", output)

    def test_a_source_field_in_someone_elses_fence_is_still_ignored(self):
        # The review-depth shape as a fixture: a `source:` line inside a ```text fence,
        # followed by field names this parser does not recognise. Before the placement
        # rule it was dropped for want of a second recognised key, which is the same
        # reason a mistyped block was dropped. Now it is dropped for being somewhere else.
        text = (
            "```text\n"
            "depth: quick | standard | deep\n"
            "source: detected | user\n"
            "changeset: the range the signals were computed over\n"
            "changeset_source: resolved | supplied\n"
            "```\n"
        )
        self.assertEqual(cp.parse_records(text), [])

    def test_a_source_field_in_open_prose_is_still_ignored(self):
        # And outside any fence, where the content rule is the only one that applies.
        text = "source: detected | user\nchangeset: working tree\n"
        self.assertEqual(cp.parse_records(text), [])

    def test_a_whole_run_of_that_shape_exits_zero_with_nothing_recorded(self):
        def never(url, timeout=30):
            raise AssertionError("nothing here should be fetched")

        code, output = run(
            "```text\nsource: detected | user\nchangeset: working tree\n```\n", never
        )
        self.assertEqual(code, 0)
        self.assertIn("No provenance records found", output)


class UnsourcedPlacementTest(unittest.TestCase):
    """bug-0042: a placement that never produced a `source:` token was examined by nothing.

    bug-0041 made a mistyped field *after* `source:` reportable. Two shapes survived it,
    both for one reason: parse_records() only ever began a run at a line whose key is
    exactly `source`, so a block that never produces that token was not examined at all.
    A typo on the key itself (`sorce:`) and a fence carrying every field but that one both
    printed nothing, counted nothing, and exited 0, which is what a repository with nothing
    folded in prints. The oracle has to be those shapes; a well-formed block always parsed.

    The empty placement is decided the other way and tested here too. It records nothing to
    re-fetch, so it is named in the output and left out of the counts rather than failing
    the run: see unsourced_placements() in the script for the rejected alternative.
    """

    SORCE = provenance_fence(
        f"sorce: {URL}",
        "author: Balarama Bosch",
        "license: MIT",
        "retrieved: 2026-08-06",
        f"sha256: {UPSTREAM_SHA}",
    )
    NO_SOURCE = provenance_fence(
        "author: Balarama Bosch",
        "license: MIT",
        "retrieved: 2026-08-06",
        f"sha256: {UPSTREAM_SHA}",
    )

    def test_a_typo_on_the_source_key_still_produces_a_record(self):
        records = cp.parse_records(self.SORCE)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["placement"], "no-source")

    def test_the_run_names_the_file_and_the_mistyped_key(self):
        code, output = run(self.SORCE, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn(".agents/skills/x/SKILL.md", output)
        self.assertIn("sorce", output)

    def test_the_mistyped_key_is_counted_as_an_error_not_as_nothing(self):
        # The bug's signature is a count that looks clean, so the count is the oracle.
        code, output = run(self.SORCE, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_a_placement_carrying_no_source_line_is_reported(self):
        code, output = run(self.NO_SOURCE, serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("no 'source:' line", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_neither_shape_is_ever_fetched(self):
        def never(url, timeout=30):
            raise AssertionError("a record that cannot be checked must not be fetched")

        for body in (self.SORCE, self.NO_SOURCE):
            with self.subTest(body=body.splitlines()[2]):
                code, _ = run(body, never)
                self.assertEqual(code, 2)

    def test_the_docstring_placement_reports_a_mistyped_key_the_same_way(self):
        # The convention names two placements and the hooks use this one, so a fix that
        # only understood markdown fences would leave half the tree exactly as it was.
        code, output = run(DOCSTRING_BLOCK.replace("source:", "sorce:"), serve(UPSTREAM))
        self.assertEqual(code, 2)
        self.assertIn("sorce", output)

    def test_list_mode_names_the_placement_and_says_it_has_no_source(self):
        code, output = run(self.SORCE, serve(UPSTREAM), argv=("--list",))
        self.assertEqual(code, 0)
        self.assertIn("[no-source]", output)
        self.assertIn("(no source)", output)

    def test_an_empty_placement_is_named_but_does_not_fail_the_run(self):
        def never(url, timeout=30):
            raise AssertionError("an empty placement records nothing to fetch")

        code, output = run(provenance_fence(), never)
        self.assertEqual(code, 0)
        self.assertIn("is empty", output)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_an_empty_placement_holding_only_a_blank_line_is_the_same(self):
        # The fence closed immediately and the fence holding one blank line are the same
        # placement to a reader, and the first has no lines between its markers at all.
        def never(url, timeout=30):
            raise AssertionError("an empty placement records nothing to fetch")

        code, output = run(provenance_fence(""), never)
        self.assertEqual(code, 0)
        self.assertIn("is empty", output)

    def test_an_empty_docstring_placement_is_named_too(self):
        def never(url, timeout=30):
            raise AssertionError("an empty placement records nothing to fetch")

        body = '"""A hook.\n\nProvenance\n----------\n"""\n'
        code, output = run(body, never)
        self.assertEqual(code, 0)
        self.assertIn("is empty", output)

    def test_an_empty_placement_does_not_hide_the_records_beside_it(self):
        # The whole family is "the run examined less than it claimed", so the real record
        # must still be fetched and counted with an unfinished fence sitting next to it.
        code, output = run(provenance_fence() + "\n" + block(), serve(UPSTREAM))
        self.assertEqual(code, 0)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)
        self.assertIn("is empty", output)

    def test_a_mistyped_key_in_someone_elses_fence_is_still_ignored(self):
        # The opposite failure, live: detection keys on the placement, so a rule that
        # widened to any near-`source` key would start reporting unrelated fenced examples.
        text = (
            f"{FENCE}text\n"
            "depth: quick | standard | deep\n"
            "sorce: detected | user\n"
            f"{FENCE}\n"
        )
        self.assertEqual(cp.parse_records(text), [])

    def test_a_run_over_someone_elses_fence_still_exits_zero_with_nothing_recorded(self):
        def never(url, timeout=30):
            raise AssertionError("nothing here should be fetched")

        code, output = run(f"{FENCE}text\nsorce: detected | user\n{FENCE}\n", never)
        self.assertEqual(code, 0)
        self.assertIn("No provenance records found", output)


class SuffixCaseTest(unittest.TestCase):
    """bug-0046: a file whose suffix an author typed uppercase was never read at all.

    `iter_provenance_files` selected with `path.suffix in SCAN_SUFFIXES`, an exact match
    against a lowercase tuple. Demonstrated on 2026-08-22 by renaming one real file:
    `.agents/rules/review-quality.md` to `.MD` took `--list` from 8 records to 6, at exit
    0, with no line naming the file.

    This is the layer above bug-0016, bug-0019, bug-0041 and bug-0042. Each of those fixed
    a way a record was lost inside a file that was read; this one loses the file. So the
    oracles assert the record is collected and counted, never that the run survives: a run
    over a tree it never opened also exits 0 and also prints a clean summary.

    The opposite direction is pinned too. Lowering only widens the scanned set, so the two
    tests at the end hold the boundary where it was: a lowercase suffix still scanned, and
    a suffix in neither family still ignored.
    """

    def collect_one(self, filename, body=None):
        tmp, root = make_root(block() if body is None else body, filename=filename)
        try:
            return cp.collect(root)
        finally:
            tmp.cleanup()

    def test_an_uppercase_markdown_suffix_is_still_scanned(self):
        found, unreadable = self.collect_one("SKILL.MD")
        self.assertEqual([rel for rel, _ in found], [".agents/skills/x/SKILL.MD"])
        self.assertEqual(unreadable, [])

    def test_a_mixed_case_markdown_suffix_is_still_scanned(self):
        found, _ = self.collect_one("SKILL.Md")
        self.assertEqual([rel for rel, _ in found], [".agents/skills/x/SKILL.Md"])

    def test_an_uppercase_python_suffix_is_still_scanned(self):
        # Both entries of SCAN_SUFFIXES, because the convention names two placements and a
        # fix that only reached the markdown one would leave half the tree as it was.
        found, _ = self.collect_one("hook.PY", body=DOCSTRING_BLOCK)
        self.assertEqual([rel for rel, _ in found], [".agents/skills/x/hook.PY"])

    def test_the_record_in_an_uppercase_file_is_fetched_and_counted(self):
        # End to end, because the count is what a reader acts on: the bug's whole symptom
        # was a summary line that reads exactly like a smaller repository.
        seen = []

        def fetcher(url, timeout=30):
            seen.append(url)
            return UPSTREAM

        code, output = run(block(), fetcher, filename="SKILL.MD")
        self.assertEqual(code, 0)
        self.assertEqual(seen, [URL])
        self.assertIn(".agents/skills/x/SKILL.MD:", output)
        self.assertIn("1 up to date, 0 drifted, 0 unlocatable, 0 error(s).", output)

    def test_an_uppercase_file_is_not_reported_as_nothing_recorded(self):
        # The exact silent state the bug produced: the line a repository with no fold-ins
        # prints, at exit 0, over a tree that has one.
        def never(url, timeout=30):
            raise AssertionError("--list must fetch nothing")

        code, output = run(block(), never, argv=("--list",), filename="SKILL.MD")
        self.assertEqual(code, 0)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("1 record(s).", output)

    def test_a_lowercase_suffix_is_scanned_exactly_as_before(self):
        found, _ = self.collect_one("SKILL.md")
        self.assertEqual([rel for rel, _ in found], [".agents/skills/x/SKILL.md"])

    def test_a_suffix_in_neither_family_is_still_ignored(self):
        # Lowering must widen the set by case alone. A fix that started reading every file
        # would satisfy every assertion above and change what the tool is for.
        for filename in ("NOTES.txt", "notes.txt"):
            with self.subTest(filename=filename):
                found, _ = self.collect_one(filename)
                self.assertEqual(found, [])

    def test_the_constant_stays_lowercase_so_the_comparison_stays_honest(self):
        # The comparison lowers one side only, so an uppercase entry here would be dead.
        self.assertEqual(list(cp.SCAN_SUFFIXES), [s.lower() for s in cp.SCAN_SUFFIXES])


class PlacementMarkerCaseTest(unittest.TestCase):
    """bug-0047: the two placement markers disagreed about case, so half the net was off.

    `_SECTION_RE` matched `Provenance` exactly, while the fence's info string was lowered
    before comparison. So ```Provenance opened a placement and a module docstring headed
    `provenance` did not: one concept, two answers on the same word.

    Placement is what bug-0041 and bug-0042 made load-bearing. Inside one, a typo on the
    field after `source:`, a typo on the `source` key itself, and a block carrying no
    `source:` line at all are all reported. Outside one, the same three are dropped and the
    run prints the clean empty state of a repository with nothing folded in, at exit 0. So
    the oracles here are the malformed shapes, not the well-formed one: a well-formed block
    under a mis-cased heading parses either way, because parse_records() also qualifies a
    run on its content, and asserting on it would pass against the bug.

    Characterization rather than acceptance: no spec covers this, so these pin the behaviour
    the widened marker produces and the boundary tests hold what it must not start
    capturing. The fenced marker is asserted here too, in both directions, because
    "unchanged" is a claim a test has to carry rather than a sentence in a closeout.

    The bound is the underline, which is the part the bug report's two-line excerpt did not
    show. A placement is an *underlined* heading outside any open fence, so widening the
    heading match cannot promote prose that merely says the word, in any spelling, and
    cannot reach inside somebody else's fenced example.
    """

    # 0-based half-open region of docstring_block(): the underline opens it, the closing
    # `\"\"\"` is the first line that is neither blank nor a `key: value` line.
    DOCSTRING_REGION = [(3, 9)]
    # And of block(): the fence line opens it, the closing fence is outside it.
    FENCE_REGION = [(2, 8)]

    @staticmethod
    def regions(body):
        return cp.placement_regions(cp.declared_lines(body.splitlines()))

    def test_every_spelling_of_the_docstring_heading_opens_the_same_placement(self):
        # The exact spelling leads the table deliberately: it is the case that already
        # worked, so a fix that widened the match by breaking it would fail here first.
        for heading in ("Provenance", "provenance", "PROVENANCE", "pRoVeNaNcE"):
            with self.subTest(heading=heading):
                self.assertEqual(self.regions(docstring_block(heading=heading)),
                                 self.DOCSTRING_REGION)

    def test_a_misspelled_field_under_a_mis_cased_heading_is_reported(self):
        # bug-0041's net, switched off for this spelling by the disagreement. Before the fix
        # the run collected `source` alone, failed the same content test that keeps
        # review-depth's unrelated `source:` field out, and appended nothing at all.
        body = docstring_block(heading="provenance").replace("author:", "authr:")
        code, output = run(body, serve(UPSTREAM), filename="hook.py")
        self.assertEqual(code, 2)
        self.assertIn("authr", output)

    def test_that_misspelled_field_is_counted_as_an_error_not_as_nothing(self):
        # The bug's signature is a summary that reads like a repository with no fold-ins, so
        # the count and the empty-tree sentence are the oracle rather than the exit code.
        body = docstring_block(heading="provenance").replace("author:", "authr:")
        code, output = run(body, serve(UPSTREAM), filename="hook.py")
        self.assertEqual(code, 2)
        self.assertNotIn("No provenance records found", output)
        self.assertIn("0 up to date, 0 drifted, 0 unlocatable, 1 error(s).", output)

    def test_a_mistyped_source_key_under_a_mis_cased_heading_is_reported(self):
        # bug-0042's net, the other half of what placement buys. Nothing here ever produces
        # a `source:` token, so only the placement pass can see this block at all.
        body = docstring_block(heading="PROVENANCE").replace("source:", "sorce:")
        code, output = run(body, serve(UPSTREAM), filename="hook.py")
        self.assertEqual(code, 2)
        self.assertIn("no 'source:' line", output)
        self.assertIn("sorce", output)

    def test_a_mis_cased_placement_is_never_fetched_when_it_is_malformed(self):
        def never(url, timeout=30):
            raise AssertionError("a record that cannot be checked must not be fetched")

        body = docstring_block(heading="provenance").replace("author:", "authr:")
        code, _ = run(body, never, filename="hook.py")
        self.assertEqual(code, 2)

    def test_every_spelling_of_the_fence_tag_opens_the_same_placement(self):
        # The fenced marker's behaviour is unchanged, proven rather than asserted: it was
        # already case-insensitive, and this fails if the fix had reached it.
        for tag in ("provenance", "Provenance", "PROVENANCE"):
            with self.subTest(tag=tag):
                body = block().replace("```provenance", "```" + tag, 1)
                self.assertEqual(self.regions(body), self.FENCE_REGION)

    def test_someone_elses_fence_is_still_not_a_placement_in_any_case(self):
        # The other direction, and the one that would fail if the fence match had been
        # widened past its tag rather than left alone.
        for tag in ("text", "Text", "TEXT", "python"):
            with self.subTest(tag=tag):
                body = block().replace("```provenance", "```" + tag, 1)
                self.assertEqual(self.regions(body), [])

    def test_a_heading_with_no_underline_opens_nothing_in_any_case(self):
        # The bound the widening rests on. Markdown is scanned as well as Python, and in
        # Markdown a word alone on a line above a run of dashes is a setext heading, so the
        # underline is the whole difference between a placement and a paragraph.
        for heading in ("Provenance", "provenance", "PROVENANCE"):
            with self.subTest(heading=heading):
                body = docstring_block(heading=heading, underline="Adapted from upstream.")
                self.assertEqual(self.regions(body), [])

    def test_a_mis_cased_heading_inside_someone_elses_fence_is_still_ignored(self):
        # The fence branch runs before the heading branch, so a documentation example that
        # shows the docstring shape inside a ```text block does not become a placement
        # because the widening made its heading match.
        body = (
            "# Example\n\n"
            + FENCE + "text\n"
            + "provenance\n"
            + "----------\n"
            + f"source: {URL}\n"
            + FENCE + "\n"
        )
        self.assertEqual(self.regions(body), [])

    def test_the_widening_moved_no_placement_in_this_repository(self):
        # The before-and-after measurement kept as a test rather than as a closeout claim.
        # The narrow marker is rebuilt here rather than left behind in the module, and both
        # are run over the real tree: they agree on every file, which is why `--list`
        # reports the same eight records after the fix as before it.
        narrow = re.compile(r"^[ \t]*Provenance[ \t]*$")
        files = list(cp.iter_provenance_files(REPO_ROOT))
        self.assertTrue(files, "nothing was scanned, so agreement would prove nothing")
        placements = 0
        for path in files:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            after = cp.placement_regions(cp.declared_lines(lines))
            with unittest.mock.patch.object(cp, "_SECTION_RE", narrow):
                before = cp.placement_regions(cp.declared_lines(lines))
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                self.assertEqual(before, after)
            placements += len(after)
        self.assertTrue(placements, "no placement was found at all, so equality is vacuous")


class RepositoryRecordsTest(unittest.TestCase):
    """Every block actually recorded in this repository is well formed. No network."""

    def test_all_seven_backfilled_targets_carry_a_valid_record(self):
        found, _ = cp.collect(REPO_ROOT)
        self.assertTrue(found, "no provenance records found in this repository")
        for rel, record in found:
            with self.subTest(path=rel, line=record["line"]):
                self.assertIsNone(cp.validate(record), f"{rel}:{record['line']}")

    def test_the_backfilled_files_are_the_expected_set(self):
        recorded = {rel for rel, _ in cp.collect(REPO_ROOT)[0]}
        for expected in (
            ".agents/skills/spec-quality/SKILL.md",
            ".agents/skills/spec-plan-readiness/SKILL.md",
            ".agents/skills/test-quality/SKILL.md",
            ".agents/skills/spec-conformance/SKILL.md",
            ".agents/rules/review-quality.md",
            ".agents/hooks/delegation-reminder.py",
            ".agents/hooks/spec-conformance-gate.py",
        ):
            self.assertIn(expected, recorded)

    def test_the_recorded_set_is_nine_records_across_eight_files(self):
        # Pins the count in both directions. A grammar widened until it collects unrelated
        # `source:` lines raises it; one narrowed until a real block drops out lowers it,
        # and the second failure is the silent one.
        #
        # The count is deliberately a count and not a property, unlike the gate set in
        # `cloud-executable.md` that `chore-0049` reworded: the whole question here is how
        # many blocks the grammar collects, so a property would answer a different one.
        # It moves whenever material is folded in, and `feat-0061` moved it from 8 across 7
        # by adding `systematic-debugging`, whose upstream is Jesse Vincent's `superpowers`.
        found, unreadable = cp.collect(REPO_ROOT)
        self.assertEqual(len(found), 9)
        self.assertEqual(len({rel for rel, _ in found}), 8)
        # And the count is a full one rather than a narrowed one: if any file in scope
        # could not be read, 9 would be what survived rather than what is there.
        self.assertEqual(unreadable, [])

    def test_no_record_in_this_repository_is_a_placement_without_a_source(self):
        # bug-0042 in the tree rather than in a fixture: every one of the eight is a real
        # sourced record, so the new rule reports nothing here and the count is unmoved.
        found, _ = cp.collect(REPO_ROOT)
        self.assertEqual([rel for rel, record in found if record.get("placement")], [])

    def test_the_review_depth_file_declares_no_provenance_placement(self):
        # The regression fixture from the other end. Its `source:` line is ignored because
        # of where it sits, so the file must contain no declared placement at all: if one
        # appeared, the placement-driven pass would report the skill as an unsourced block.
        path = REPO_ROOT / ".agents" / "skills" / "review-depth" / "SKILL.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(cp.placement_regions(cp.declared_lines(lines)), [])

    def test_the_review_depth_output_template_contributes_no_records(self):
        # The real file, not a fixture. `source: detected | user` in review-depth's output
        # block is the collision the grammar was tightened for: if a later change widens
        # it, the checker starts failing on a skill nobody touched.
        path = REPO_ROOT / ".agents" / "skills" / "review-depth" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("source: detected | user", text, "fixture is stale; the field moved")
        self.assertEqual(cp.parse_records(text), [])


class RedirectStaysOnHttps(unittest.TestCase):
    """bug-0054: the `https` bound applied to the recorded URL and not to what was fetched.

    `validate()` rejects an `http://` source and says why: over plaintext the digest
    authenticates nothing, so the record would read as verified provenance for bytes anyone
    on the path could have written. `fetch()` then called `urlopen`, which follows redirects
    by default, and the standard library's own allow-list admits `http`. So an `https`
    source answering `302 Location: http://...` was followed into plaintext, and the caller
    was told nothing.

    The loopback test below is the one that has to use a real server. Everything else here
    goes through the injected seam, per this file's opening note, but "the handler is
    actually installed on the opener `fetch()` uses" is not a claim a stand-in can make: the
    defect was precisely that the wrong opener was being used.
    """

    def _redirecting_pair(self):
        """Two loopback servers, the first answering 302 toward the second. No outbound
        traffic. Both speak http, which is the point: after the fix any redirect off https
        is refused, and http is the cheapest non-https scheme to serve."""
        import http.server
        import threading

        target_holder = {}

        class Target(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"BYTES FROM THE REDIRECT TARGET"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class Source(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", target_holder["url"])
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass

        target = http.server.HTTPServer(("127.0.0.1", 0), Target)
        source = http.server.HTTPServer(("127.0.0.1", 0), Source)
        target_holder["url"] = f"http://127.0.0.1:{target.server_port}/t"
        for server in (target, source):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{source.server_port}/recorded", target_holder["url"]

    def test_a_redirect_off_https_is_refused_by_the_opener_fetch_actually_uses(self):
        # Through the real opener against a real server, so it fails if the handler is
        # removed or if `fetch()` goes back to `urllib.request.urlopen`. Before the fix this
        # returned the target's bytes and said nothing.
        recorded, target = self._redirecting_pair()
        with self.assertRaises(cp.InsecureRedirect) as caught:
            cp.fetch(recorded)
        self.assertIn(target, str(caught.exception),
                      "the refusal does not say where the redirect pointed")

    def test_the_opener_carries_our_handler_and_not_the_default(self):
        # `build_opener` drops its own default when handed a subclass. If that ever stops
        # being true, the default would follow the redirect before ours declined it.
        redirects = [type(h).__name__ for h in cp._OPENER.handlers if "Redirect" in type(h).__name__]
        self.assertEqual(redirects, ["HttpsOnlyRedirectHandler"])

    def test_the_handler_permits_a_redirect_that_stays_on_https(self):
        # The failure direction that matters as much as the refusal: upstream repositories
        # get renamed, and a checker that fails on a moved file is one that gets disabled.
        # Driven at the handler because serving https on loopback needs a certificate.
        handler = cp.HttpsOnlyRedirectHandler()
        request = cp.urllib.request.Request(URL)
        moved = "https://raw.githubusercontent.com/moonray/renamed/main/x.md"
        new = handler.redirect_request(request, io.BytesIO(b""), 302, "Found", {}, moved)
        self.assertIsNotNone(new, "a redirect that stays on https was refused")
        self.assertEqual(new.full_url, moved)

    def test_the_handler_refuses_every_scheme_that_is_not_https(self):
        handler = cp.HttpsOnlyRedirectHandler()
        request = cp.urllib.request.Request(URL)
        for target in ("http://example.com/x.md",
                       "ftp://example.com/x.md",
                       "file:///etc/passwd",
                       "HTTP://example.com/x.md"):
            with self.subTest(target=target):
                with self.assertRaises(cp.InsecureRedirect):
                    handler.redirect_request(request, io.BytesIO(b""), 302, "Found", {}, target)

    def test_a_source_that_moved_is_reported_as_drift_even_when_the_bytes_match(self):
        # The record's `source:` no longer names what answered. Reporting `ok` would let a
        # record sit on a redirect indefinitely, which is the rot this script exists to
        # surface. The remedy differs from content drift, so the wording does too.
        moved_to = URL.replace("moonray", "moonray-renamed")

        def fetcher(url, timeout=30):
            return cp.Fetched(UPSTREAM, moved_to)

        code, output = run(block(), fetcher)
        self.assertEqual(code, 1, output)
        self.assertIn("MOVED", output)
        self.assertIn(moved_to, output)
        self.assertIn("repoint the record's source", output)
        self.assertIn("0 up to date, 1 drifted", output)

    def test_content_drift_names_where_the_bytes_were_actually_retrieved_from(self):
        moved_to = URL.replace("moonray", "moonray-renamed")

        def fetcher(url, timeout=30):
            return cp.Fetched(b"different bytes entirely\n", moved_to)

        code, output = run(block(), fetcher)
        self.assertEqual(code, 1, output)
        self.assertIn("DRIFT", output)
        self.assertIn("retrieved from", output)
        self.assertIn(moved_to, output)

    def test_an_unmoved_source_is_still_reported_ok_and_says_nothing_about_redirects(self):
        # The common case must not gain noise. A record whose source answered directly reads
        # exactly as it did before this change.
        def fetcher(url, timeout=30):
            return cp.Fetched(UPSTREAM, url)

        code, output = run(block(), fetcher)
        self.assertEqual(code, 0, output)
        self.assertIn("up to date", output)
        self.assertNotIn("MOVED", output)

    def test_a_fetcher_returning_bare_bytes_is_still_understood(self):
        # The seam takes either shape, so the tests above this class, which return bytes and
        # are about something else entirely, keep meaning what they meant.
        code, output = run(block(), serve(UPSTREAM))
        self.assertEqual(code, 0, output)
        self.assertIn("up to date", output)

    def test_a_refused_redirect_reaches_the_report_as_an_error_rather_than_a_traceback(self):
        # InsecureRedirect is a ValueError so it lands in check_record's existing except,
        # which is the branch that already means "this source could not honestly be
        # fetched". Exit 2, not 1: nothing was compared.
        code, output = run(block(), unreachable(cp.InsecureRedirect("refused a redirect off https")))
        self.assertEqual(code, 2, output)
        self.assertIn("could not fetch", output)
        self.assertIn("refused a redirect off https", output)

    def test_the_recorded_url_rule_and_the_transport_rule_are_both_still_enforced(self):
        # The recorded-URL half, which existed before this change and must not have been
        # traded away for the transport half.
        self.assertIsNotNone(cp.validate({
            "source": "http://raw.githubusercontent.com/x/y/main/z.md", "author": "A",
            "license": "MIT", "retrieved": "2026-08-30", "sha256": "0" * 64,
        }), "an http:// source is no longer reported as malformed")
        self.assertIsNone(cp.validate({
            "source": URL, "author": "A", "license": "MIT",
            "retrieved": "2026-08-30", "sha256": "0" * 64,
        }), "a well-formed https record is rejected")


if __name__ == "__main__":
    unittest.main()
