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
  real records  - a backfilled block in this repository is malformed and nobody notices
                  until the day someone runs the checker with a network
"""
import contextlib
import hashlib
import importlib.util
import io
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


def make_root(body):
    """A throwaway repository root carrying one adapted file under a scanned directory.

    The local body is deliberately unlike UPSTREAM: the digest must be compared against the
    fetched bytes, not against the adapted file, and a fixture where the two matched would
    hide a checker that digested the wrong thing.
    """
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    skill = root / ".agents" / "skills" / "x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_bytes(
        ("---\nname: x\n---\n\n# X\n\nHouse-styled and retargeted, so it differs from upstream.\n\n"
         + body).encode("utf-8")
    )
    return tmp, root


def run(body, fetcher, argv=()):
    tmp, root = make_root(body)
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

    def __init__(self, payload):
        self._buffer = io.BytesIO(payload)
        self.bytes_read = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self, amount=None):
        chunk = self._buffer.read() if amount is None else self._buffer.read(amount)
        self.bytes_read += len(chunk)
        return chunk


class _fake_urlopen:
    """Serve `payload` to `fetch()` without a socket, and expose the response it served.

    `fetch()` is the one function with no injection seam, because the seam the rest of this
    file uses replaces it. Its read bound therefore has to be exercised against a stand-in
    response rather than a stand-in fetcher, and still without a socket.
    """

    def __init__(self, payload):
        self.response = _FakeResponse(payload)
        self._patch = unittest.mock.patch.object(
            cp.urllib.request, "urlopen", lambda request, timeout=None: self.response
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
        # commit message that nobody can re-run.
        found, _ = cp.collect(REPO_ROOT)
        self.assertEqual(len(found), 8)
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
            self.assertEqual(cp.fetch(URL, max_bytes=64), payload)

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

    def test_the_recorded_set_is_eight_records_across_seven_files(self):
        # Pins the count in both directions. A grammar widened until it collects unrelated
        # `source:` lines raises it; one narrowed until a real block drops out lowers it,
        # and the second failure is the silent one.
        found, unreadable = cp.collect(REPO_ROOT)
        self.assertEqual(len(found), 8)
        self.assertEqual(len({rel for rel, _ in found}), 7)
        # And the count is a full one rather than a narrowed one: if any file in scope
        # could not be read, 8 would be what survived rather than what is there.
        self.assertEqual(unreadable, [])

    def test_the_review_depth_output_template_contributes_no_records(self):
        # The real file, not a fixture. `source: detected | user` in review-depth's output
        # block is the collision the grammar was tightened for: if a later change widens
        # it, the checker starts failing on a skill nobody touched.
        path = REPO_ROOT / ".agents" / "skills" / "review-depth" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("source: detected | user", text, "fixture is stale; the field moved")
        self.assertEqual(cp.parse_records(text), [])


if __name__ == "__main__":
    unittest.main()
