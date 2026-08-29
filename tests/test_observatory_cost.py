#!/usr/bin/env python3
"""Tests for the observatory's cost and pressure report (`feat-0057`).

Four scenarios from `docs/spec/agent-observatory.md` are covered here, and each test names the
one it proves: `S-010` (cost is an estimate against a dated rate table), `S-011` (an unpriced
model yields no invented cost), `S-017` (context and quota pressure over time), and `S-021`
(tokens by kind, with the cache-served proportion derivable).

Two oracles are deliberately chosen so a plausible wrong implementation fails rather than
passes.

**Every token fixture uses a different number for each of the four kinds.** A report that
transposed input and cache-creation, or that summed the four into one figure and split it back
out by a ratio, would satisfy a fixture where the kinds were equal. Here it cannot.

**Zero and unknown are asserted as different values, not as different words.** `S-011`'s whole
content is that an unpriced model must not read as a free one, so the assertions distinguish
`cost_usd is None` from `cost_usd == 0.0` and require a priced model with no tokens to produce
the second while an unpriced model with tokens produces the first.

Standard library only, matching the rest of `tests/`. Nothing here reaches a remote host, and
one test asserts that by replacing `socket.socket` for the duration of a rate-table load.
"""

from __future__ import annotations

import http.client
import json
import re
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.observatory import db, ingest, serve      # noqa: E402

UI_INDEX = REPO_ROOT / "scripts" / "observatory" / "ui" / "index.html"
SHIPPED_PRICING = REPO_ROOT / "scripts" / "observatory" / "pricing.json"

# One priced model, with a different figure for each of the four kinds and rates chosen so the
# arithmetic is exact in binary floating point. 2*5 + 1*25 + 10*0.5 + 4*6.25 = 65.0.
PRICED = {"input": 5.0, "output": 25.0}
MILLION = 1_000_000


class CostTestCase(unittest.TestCase):
    """A corpus, a store built from it, and a rate table the test controls.

    The rate table is a fixture rather than `scripts/observatory/pricing.json`, so no assertion
    below silently changes meaning the day a real rate is corrected. One test,
    `test_s010_the_shipped_rate_table_records_a_date_and_a_source`, deliberately reads the
    shipped one.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obs-cost-"))
        self.corpus = self.tmp / "projects"
        self.project = self.corpus / "D--demo"
        self.project.mkdir(parents=True)
        self.store = self.tmp / "store.db"
        # Deliberately not created, so no test here reads the live registry of the machine it
        # runs on. The cost report does not use it; the server it is served from does.
        self.registry = self.tmp / "sessions"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- corpus fixtures ------------------------------------------------------------

    @staticmethod
    def assistant(uuid, model="test-model", sid="s1", ts="2026-08-01T10:00:00.000Z",
                  input_tokens=0, output_tokens=0, cache_read=0, cache_creation=0,
                  thinking=0):
        """One assistant record, shaped as the corpus shapes them.

        The usage keys are the corpus's own, read by `ingest._usage`: `input_tokens`,
        `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and
        `output_tokens_details.thinking_tokens`.
        """
        return {
            "type": "assistant", "uuid": uuid, "parentUuid": None, "sessionId": sid,
            "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main", "version": "2.1.247",
            "entrypoint": "claude-desktop", "slug": "demo", "isSidechain": False,
            "message": {"model": model, "role": "assistant", "content": [],
                        "usage": {"input_tokens": input_tokens,
                                  "output_tokens": output_tokens,
                                  "cache_read_input_tokens": cache_read,
                                  "cache_creation_input_tokens": cache_creation,
                                  "output_tokens_details": {"thinking_tokens": thinking}}},
        }

    @staticmethod
    def context_record(sid, ts, tokens_left):
        """One context-budget reading. The count is embedded in the attachment's text as
        `<total_tokens>N tokens left</total_tokens>`, which is where the ingester parses it
        from and the only context series the corpus carries."""
        return {"type": "attachment", "uuid": f"ctx-{sid}-{ts}", "sessionId": sid,
                "timestamp": ts, "cwd": "D:\\demo", "gitBranch": "main",
                "attachment": {"type": "total_tokens_reminder",
                               "text": f"<total_tokens>{tokens_left} tokens left"
                                       f"</total_tokens>"}}

    @staticmethod
    def compaction_record(sid, ts):
        """A `compact_boundary` system record. Nothing else in the corpus marks a compaction,
        which is why `S-017`'s "occasions are identifiable" turns on this one shape."""
        return {"type": "system", "subtype": "compact_boundary", "uuid": f"cb-{sid}-{ts}",
                "sessionId": sid, "timestamp": ts, "cwd": "D:\\demo",
                "compactMetadata": {"trigger": "auto"}}

    def write(self, records, name="session.jsonl", project=None):
        path = (project or self.project) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes("".join(json.dumps(r) + "\n" for r in records).encode("utf-8"))
        return path

    def build_store(self, records, name="session.jsonl", project=None):
        self.write(records, name=name, project=project)
        return ingest.ingest(self.corpus, self.store)

    # -- rate table and quota fixtures ----------------------------------------------

    def pricing_file(self, models, as_of="2026-01-01", multipliers=None, name="rates.json"):
        path = self.tmp / name
        payload = {
            "as_of": as_of, "transcribed": "2026-01-02", "currency": "USD",
            "unit": "per million tokens", "source": "a fixture table, not a real rate",
            "source_author": "this test",
            "cache_multipliers": ({"cache_read": 0.1, "cache_creation": 1.25}
                                  if multipliers is None else multipliers),
            "models": models,
        }
        path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        return path

    def quota_file(self, lines, name="quota.jsonl"):
        path = self.tmp / name
        path.write_text("".join(line + "\n" for line in lines),
                        encoding="utf-8", newline="\n")
        return path

    # -- the report -----------------------------------------------------------------

    def cost(self, project=None, pricing=None, quota=None):
        conn = db.connect(self.store)
        try:
            return serve.cost_report(conn, project, serve.load_pricing(pricing),
                                     serve.load_quota(quota))
        finally:
            conn.close()

    @staticmethod
    def by_model(payload):
        return {row["model"]: row for row in payload["models"]}


class ServedCostTestCase(CostTestCase):
    """Adds a running loopback server for the tests that go over HTTP."""

    def serve_on_loopback(self, pricing=None, quota=None):
        server = serve.make_server(self.store, serve.DEFAULT_HOST, 0, quiet=True,
                                   registry=self.registry, corpus=self.corpus,
                                   pricing=pricing, quota=quota)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        return server

    def fetch_json(self, server, path):
        host, port = server.server_address[0], server.server_address[1]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            conn.close()


class TestTokensByKind(CostTestCase):
    """S-021: token consumption is reported by kind, not as one number."""

    def test_s021_the_four_token_kinds_are_reported_separately(self):
        """The scenario's first Then. Four different numbers, so a report that transposed two
        kinds, or that carried one figure and split it, fails rather than passes."""
        self.build_store([self.assistant("a1", input_tokens=11, output_tokens=22,
                                         cache_read=33, cache_creation=44, thinking=7)])

        tokens = self.cost(pricing=self.pricing_file({}))["tokens"]

        self.assertEqual(tokens["input"], 11)
        self.assertEqual(tokens["output"], 22)
        self.assertEqual(tokens["cache_read"], 33)
        self.assertEqual(tokens["cache_creation"], 44)
        self.assertEqual(tokens["total"], 110, "the total is not the four kinds added up")
        self.assertEqual(tokens["thinking_within_output"], 7,
                         "thinking is reported as a memo beside the four")

    def test_s021_thinking_tokens_are_not_a_fifth_kind_in_the_total(self):
        """They arrive from `output_tokens_details` and are already inside `output_tokens`, so
        counting them again would overstate every total and every cost by the size of the
        model's reasoning. 110, not 117."""
        self.build_store([self.assistant("a1", input_tokens=11, output_tokens=22,
                                         cache_read=33, cache_creation=44, thinking=7)])

        tokens = self.cost(pricing=self.pricing_file({}))["tokens"]

        self.assertEqual(tokens["total"], tokens["input"] + tokens["output"]
                         + tokens["cache_read"] + tokens["cache_creation"])
        self.assertNotEqual(tokens["total"], 117,
                            "thinking tokens were added to the total as a fifth kind")

    def test_s021_the_cache_served_proportion_is_derivable_from_the_four_kinds(self):
        """The scenario's second Then, as an exact figure rather than a plausible one.

        10M cache reads against 2M input and 4M cache creation is 10/16 = 0.625 on the stated
        basis. The other defensible basis, all four kinds including the 1M of output, gives
        10/17 = 0.588..., so the assertion distinguishes them and the basis is asserted too.
        """
        self.build_store([self.assistant("a1", input_tokens=2 * MILLION,
                                         output_tokens=1 * MILLION,
                                         cache_read=10 * MILLION,
                                         cache_creation=4 * MILLION)])

        cache = self.cost(pricing=self.pricing_file({}))["cache"]

        self.assertEqual(cache["input_side_tokens"], 16 * MILLION)
        self.assertEqual(cache["served_share"], 0.625)
        self.assertIn("input plus cache read plus cache creation", cache["basis"],
                      "the report does not say what the proportion was derived from, so it "
                      "is not derivable by a reader")

    def test_s021_no_consumption_yields_no_proportion_rather_than_a_zero(self):
        """A degenerate input, constructed rather than assumed. Nothing consumed means the
        proportion is undefined, and reporting it as 0% would claim nothing was cached."""
        self.build_store([self.assistant("a1")])

        cache = self.cost(pricing=self.pricing_file({}))["cache"]

        self.assertEqual(cache["input_side_tokens"], 0)
        self.assertIsNone(cache["served_share"])

    def test_s021_a_replayed_message_is_counted_once_not_once_per_transcript(self):
        """The trap this component has already hit once, in the skills report.

        A forked or resumed session replays earlier history verbatim, so one uuid appears in
        more than one transcript: 5,442 of them in the maintainer's corpus. Summing over a join
        to `message_occurrence` would add that message's tokens once per replay. Here `a1`
        appears in two transcripts and `a2` in one, so the honest total is 111 and the
        double-counting total is 211.
        """
        self.write([self.assistant("a1", sid="s1", input_tokens=100)], name="first.jsonl")
        self.write([self.assistant("a1", sid="s2", input_tokens=100),
                    self.assistant("a2", sid="s2", input_tokens=11)], name="second.jsonl")
        ingest.ingest(self.corpus, self.store)

        everywhere = self.cost(pricing=self.pricing_file({}))
        scoped = self.cost(project="D--demo", pricing=self.pricing_file({}))

        self.assertEqual(everywhere["tokens"]["input"], 111)
        self.assertEqual(scoped["tokens"]["input"], 111,
                         "the scoped branch counted a replayed message once per transcript")
        self.assertEqual(scoped["tokens"]["messages"], 2,
                         "the message count double-counts the replay too")


class TestCostIsADatedEstimate(CostTestCase):
    """S-010: cost is reported as an estimate against a dated rate table."""

    def priced_corpus(self):
        """2M input, 1M output, 10M cache read, 4M cache creation of one priced model."""
        self.build_store([self.assistant("a1", model="test-model",
                                         input_tokens=2 * MILLION,
                                         output_tokens=1 * MILLION,
                                         cache_read=10 * MILLION,
                                         cache_creation=4 * MILLION)])

    def test_s010_the_figure_is_labelled_an_estimate_and_carries_the_rate_tables_date(self):
        """The scenario's Then, both halves, over a table whose date the test chose."""
        self.priced_corpus()

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED},
                                                      as_of="2026-03-04"))

        self.assertIn("stimate", payload["estimate_label"])
        self.assertIn("not billed", payload["estimate_label"])
        self.assertEqual(payload["rates"]["as_of"], "2026-03-04")
        self.assertEqual(payload["rates"]["transcribed"], "2026-01-02")
        self.assertTrue(payload["rates"]["source"],
                        "the report carries a rate date with no statement of where the rates "
                        "came from")

    def test_s010_the_estimate_is_the_four_kinds_against_the_tables_rates(self):
        """An exact figure, worked by hand: 2M at $5, 1M at $25, 10M at $0.50 (0.1x input),
        and 4M at $6.25 (1.25x input) is $65.00. A report that priced only input and output
        would say $35.00 and would look entirely reasonable."""
        self.priced_corpus()

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED}))

        self.assertEqual(payload["cost"]["estimated_usd"], 65.0)
        self.assertEqual(self.by_model(payload)["test-model"]["cost_usd"], 65.0)
        self.assertEqual(self.by_model(payload)["test-model"]["rate"],
                         {"input": 5.0, "output": 25.0,
                          "cache_read": 0.5, "cache_creation": 6.25})

    def test_s010_the_rate_table_is_data_on_disk_rather_than_a_constant_in_the_code(self):
        """Change the file, change the figure. Without this a hardcoded rate would satisfy
        every other assertion here, because every other assertion reads a fixture whose rates
        happen to be the ones a hardcoded table would carry."""
        self.priced_corpus()

        cheap = self.cost(pricing=self.pricing_file({"test-model": PRICED}, name="a.json"))
        dear = self.cost(pricing=self.pricing_file(
            {"test-model": {"input": 50.0, "output": 250.0}}, name="b.json"))

        self.assertEqual(cheap["cost"]["estimated_usd"], 65.0)
        self.assertEqual(dear["cost"]["estimated_usd"], 650.0)

    def test_s010_the_report_states_that_history_is_priced_at_current_rates(self):
        """One rate per model applied to a corpus spanning months is wrong for old sessions
        and is the right simplification anyway. It is only honest if the report says so."""
        self.priced_corpus()

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED}))

        self.assertIn("current rates", payload["historical_note"])
        self.assertIn("one rate per model", payload["historical_note"].lower())

    def test_s010_the_shipped_rate_table_records_a_date_and_a_source(self):
        """The artifact this task creates, checked as an artifact. A table with no date cannot
        satisfy S-010 however carefully the report renders it."""
        table = json.loads(SHIPPED_PRICING.read_text(encoding="utf-8"))

        self.assertRegex(table["as_of"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(table["transcribed"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(table["source"] and table["source_author"])
        self.assertTrue(table["models"], "the shipped table prices nothing")
        for name, rate in table["models"].items():
            with self.subTest(model=name):
                for key in ("input", "output"):
                    self.assertIsInstance(rate[key], (int, float))
                    self.assertGreater(rate[key], 0)
        for key in ("cache_read", "cache_creation"):
            self.assertGreater(table["cache_multipliers"][key], 0)

    def test_s010_the_shipped_table_loads_and_every_model_resolves_all_four_rates(self):
        """The loader's own invariant over the real file, not over a fixture: a model is
        priced only when all four of its rates resolve."""
        loaded = serve.load_pricing(SHIPPED_PRICING)

        self.assertTrue(loaded["present"])
        self.assertEqual(loaded["as_of"], "2026-06-24")
        self.assertTrue(loaded["models"])
        for name, rate in loaded["models"].items():
            with self.subTest(model=name):
                self.assertEqual(set(rate), {"input", "output", "cache_read",
                                             "cache_creation"})
                self.assertEqual(rate["cache_read"], rate["input"] * 0.1)
                self.assertEqual(rate["cache_creation"], rate["input"] * 1.25)

    def test_s010_the_page_puts_the_rate_date_in_the_figures_own_caption(self):
        """The task says to state the estimate as an estimate everywhere it appears, "not once
        in a footnote". The mechanical form of that is the caption under the number, so the
        assertion is on the construct that builds it rather than on the word `estimate`
        appearing somewhere in the file.
        """
        body = cost_renderer_body()

        self.assertIn('rates.as_of ? "estimated, rates of " + rates.as_of', body,
                      "the caption no longer derives its date from the rate table")
        self.assertIn('figure((rates.currency || "") + " " + usd(cost.estimated_usd), dated)',
                      body,
                      "the cost figure no longer carries the dated caption beside it")


class TestUnpricedModels(CostTestCase):
    """S-011: an unpriced model yields no invented cost."""

    def mixed_corpus(self):
        """One priced model and one the rate table will not name."""
        self.build_store([
            self.assistant("a1", model="test-model", input_tokens=2 * MILLION,
                           output_tokens=1 * MILLION, cache_read=10 * MILLION,
                           cache_creation=4 * MILLION),
            self.assistant("a2", model="mystery-model", input_tokens=7,
                           output_tokens=8, cache_read=9, cache_creation=10),
        ])

    def test_s011_an_unpriced_models_tokens_are_still_reported(self):
        """The scenario's first Then. Dropping the row would be the other way to avoid an
        invented cost, and it would lose the consumption as well."""
        self.mixed_corpus()

        row = self.by_model(self.cost(pricing=self.pricing_file(
            {"test-model": PRICED})))["mystery-model"]

        self.assertEqual((row["input_tokens"], row["output_tokens"],
                          row["cache_read_tokens"], row["cache_creation_tokens"]),
                         (7, 8, 9, 10))
        self.assertEqual(row["tokens"], 34)
        self.assertEqual(row["messages"], 1)

    def test_s011_its_cost_is_unknown_rather_than_zero_or_a_guess(self):
        """The scenario's second Then, and the whole content of the scenario. `None` is the
        JSON null the page renders as the word; `0.0` is a claim that the model was free."""
        self.mixed_corpus()

        row = self.by_model(self.cost(pricing=self.pricing_file(
            {"test-model": PRICED})))["mystery-model"]

        self.assertIsNone(row["cost_usd"])
        self.assertNotEqual(row["cost_usd"], 0.0)
        self.assertFalse(row["priced"])
        self.assertIsNone(row["rate"])

    def test_s011_zero_and_unknown_are_different_answers_in_the_same_report(self):
        """The distinction stated as a comparison rather than as two separate assertions.

        A priced model that consumed nothing costs exactly zero and is priced. An unpriced
        model that consumed something costs unknown. An implementation that defaulted a missing
        rate to zero would make these two rows identical, which is the failure this scenario
        exists to prevent, and it would pass every other test in this class.
        """
        self.build_store([
            self.assistant("a1", model="test-model"),
            self.assistant("a2", model="mystery-model", input_tokens=1000),
        ])

        rows = self.by_model(self.cost(pricing=self.pricing_file({"test-model": PRICED})))

        self.assertEqual(rows["test-model"]["cost_usd"], 0.0)
        self.assertTrue(rows["test-model"]["priced"])
        self.assertIsNone(rows["mystery-model"]["cost_usd"])
        self.assertNotEqual(rows["test-model"]["cost_usd"],
                            rows["mystery-model"]["cost_usd"])

    def test_s011_the_model_is_named_as_unpriced_in_the_total_it_contributes_to(self):
        """The scenario's third Then, plus the task's criterion that "a total including it says
        so". The total is the priced model's cost alone, it is marked incomplete, and the
        excluded model is named rather than merely counted."""
        self.mixed_corpus()

        cost = self.cost(pricing=self.pricing_file({"test-model": PRICED}))["cost"]

        self.assertEqual(cost["estimated_usd"], 65.0)
        self.assertFalse(cost["complete"])
        self.assertEqual(cost["unpriced_model_names"], ["mystery-model"])
        self.assertEqual(cost["unpriced_models"], 1)
        self.assertEqual(cost["priced_models"], 1)
        self.assertEqual(cost["unpriced_tokens"], 34)
        self.assertEqual(cost["unpriced_messages"], 1)
        self.assertIn("mystery-model", cost["note"])
        self.assertIn("unknown, not zero", cost["note"])

    def test_s011_a_fully_priced_scope_is_reported_complete(self):
        """The other side of the flag. Without this, `complete` could be hardcoded false and
        every assertion above would still pass."""
        self.build_store([self.assistant("a1", model="test-model", input_tokens=MILLION)])

        cost = self.cost(pricing=self.pricing_file({"test-model": PRICED}))["cost"]

        self.assertTrue(cost["complete"])
        self.assertEqual(cost["unpriced_model_names"], [])
        self.assertEqual(cost["estimated_usd"], 5.0)

    def test_s011_a_missing_rate_table_makes_every_model_unpriced_not_free(self):
        """The degenerate input, constructed rather than reasoned about, per the conventions
        section of `AGENTS.md`. A missing table is the state a fresh clone is in before anyone
        edits one, and it must not read as a corpus that cost nothing."""
        self.mixed_corpus()

        payload = self.cost(pricing=self.tmp / "there-is-no-table-here.json")

        self.assertFalse(payload["rates"]["present"])
        self.assertEqual(payload["rates"]["priced_models"], 0)
        self.assertIn("unknown rather than zero", payload["rates"]["note"])
        self.assertFalse(payload["cost"]["complete"])
        self.assertEqual(sorted(payload["cost"]["unpriced_model_names"]),
                         ["mystery-model", "test-model"])
        self.assertEqual(payload["tokens"]["input"], 2 * MILLION + 7,
                         "the token figures went missing with the rate table")
        self.assertIsNone(
            payload["cost"]["estimated_usd"],
            "a scope where nothing could be priced reported a number, and the number is "
            "zero: the confident zero over millions of tokens that S-011 exists to prevent")

    def test_s010_a_rate_with_a_stated_expiry_reaches_the_report_with_its_date(self):
        """A rate can be correct and temporary at the same time, and the number cannot say so.

        This is the failure the task's own Risks section names, with a date on it: the table
        keeps looking exactly as right as the day it was true, and every figure priced with
        that rate quietly drifts. The shipped table carries one such rate, so the mechanism
        that surfaces it is exercised here on a fixture rather than on the real file, which
        would tie the test to a maintenance decision.

        `expires` is carried and rendered, never compared against a clock. A report whose
        output depended on when it ran would answer differently to two readers looking at the
        same corpus, which is the property every other figure here is built to avoid.
        """
        self.mixed_corpus()
        table = self.pricing_file({
            "test-model": {"input": 2.0, "output": 10.0,
                           "note": "Introductory rate. The standard rate is $3.00 and $15.00.",
                           "expires": "2026-08-31"},
            "mystery-model": {"input": 1.0, "output": 5.0},
        })

        payload = self.cost(pricing=table)

        self.assertEqual(payload["rates"]["rate_notes"],
                         [{"model": "test-model",
                           "note": "Introductory rate. The standard rate is $3.00 and $15.00.",
                           "expires": "2026-08-31"}],
                         "a rate carrying a stated expiry did not reach the report, so the "
                         "page prices with it and never says it runs out")
        # Derived, not observed. `test-model` at 2.0/10.0 with the 0.1 and 1.25 multipliers:
        # 2M input at $2/M = 4.00, 1M output at $10/M = 10.00, 10M cache reads at $0.20/M =
        # 2.00, 4M cache writes at $2.50/M = 10.00, so 26.00. `mystery-model` at 1.0/5.0 adds
        # 7, 8, 9 and 10 tokens, which is 0.0000604. The point of the assertion is the first
        # figure: it is what the rate says, and the note beside it changed nothing.
        self.assertEqual(payload["cost"]["estimated_usd"], 26.00006,
                         "the note changed the arithmetic; it is for the reader, and the "
                         "rate applied must still be the one in `input` and `output`")

    def test_s010_a_rate_with_no_note_contributes_nothing_to_the_notes(self):
        """The empty case, which is what makes the list readable: a table where every rate is
        simply current produces no notes at all, so the page renders no section rather than an
        empty heading, and a note present anywhere means something is genuinely time-bound."""
        self.mixed_corpus()

        payload = self.cost(pricing=self.pricing_file(
            {"test-model": {"input": 2.0, "output": 10.0}}))

        self.assertEqual(payload["rates"]["rate_notes"], [])

    def test_s010_the_page_renders_a_time_bound_rate_where_the_reader_meets_the_rates(self):
        """Carried in the payload and never rendered would leave the reader exactly where the
        finding found them."""
        body = cost_renderer_body()

        self.assertIn("rates.rate_notes", body,
                      "the page never reads the rate notes, so a rate with a known expiry "
                      "is priced with and never mentioned")
        self.assertIn("entry.expires", body,
                      "the page renders a rate note without its date, which is the half of "
                      "the note a reader needs to know whether it still applies")

    def test_s011_a_priced_scope_that_genuinely_cost_nothing_is_still_zero_not_unknown(self):
        """The other side of the rule above, which is the one that makes it a rule.

        Answering `unknown` whenever the total is zero would be safe and wrong: a scope that
        was priced and came to nothing is a measured zero, and collapsing it into "unknown"
        loses exactly the distinction the null was introduced to preserve. Zero and unknown
        are two answers in both directions, not one answer and one escape hatch.

        The zero here is reached by consuming nothing at a real rate, not by pricing real
        consumption at a rate of zero. Both produce a total of `0.0` and only the first is
        the case the docstring describes: a rate table of zeros is a strange table, while a
        model that ran and consumed nothing is the ordinary empty scope this has to get
        right. Recorded because the first version of this test took the second route and an
        outside review caught the mismatch between what it said and what it built.
        """
        self.build_store([self.assistant("a1", model="test-model")])

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED}))

        self.assertEqual(payload["tokens"]["total"], 0, "the scope is not actually empty")
        self.assertEqual(payload["cost"]["estimated_usd"], 0.0,
                         "a fully priced scope that consumed nothing was reported as "
                         "unknown, which hides a real measurement behind an absence")
        self.assertTrue(payload["cost"]["complete"])
        self.assertEqual(payload["cost"]["unpriced_models"], 0)

    def test_s011_a_rate_of_zero_is_a_price_and_not_an_absence_of_one(self):
        """The neighbouring case, kept because it is genuinely different.

        A model priced at zero is priced: `_rate` admits `0.0`, so its cost is a measured
        `0.0` and the total stays complete. A rule that treated a zero rate as no rate would
        move this scope into the unpriced branch and report unknown, which is the same
        collapse from the other end.
        """
        self.mixed_corpus()

        payload = self.cost(pricing=self.pricing_file(
            {"test-model": {"input": 0.0, "output": 0.0},
             "mystery-model": {"input": 0.0, "output": 0.0}}))

        self.assertGreater(payload["tokens"]["total"], 0,
                           "this case is only interesting over real consumption")
        self.assertEqual(payload["cost"]["estimated_usd"], 0.0)
        self.assertTrue(payload["cost"]["complete"],
                        "a model priced at zero was treated as having no rate at all")
        self.assertEqual(payload["cost"]["unpriced_model_names"], [])

    def test_s011_an_unparseable_rate_table_is_stated_rather_than_absorbed(self):
        """A hand-edited table with a trailing comma must not silently price everything at
        zero, and must not take the whole report down either."""
        broken = self.tmp / "broken.json"
        broken.write_text('{"models": {,}}', encoding="utf-8", newline="\n")
        self.mixed_corpus()

        payload = self.cost(pricing=broken)

        self.assertFalse(payload["rates"]["present"])
        self.assertIn("does not parse", payload["rates"]["note"])
        self.assertFalse(payload["cost"]["complete"])
        self.assertEqual(payload["tokens"]["total"], 17 * MILLION + 34)

    def test_s011_a_model_priced_for_only_some_kinds_is_not_priced_at_all(self):
        """Half a rate is not a rate. A model with an input rate and no output rate would
        otherwise produce a figure that silently omits every output token, which reads as a
        cost rather than as a gap."""
        self.mixed_corpus()

        rows = self.by_model(self.cost(pricing=self.pricing_file(
            {"test-model": {"input": 5.0}})))

        self.assertIsNone(rows["test-model"]["cost_usd"])
        self.assertFalse(rows["test-model"]["priced"])

    def test_s011_a_table_with_no_cache_multipliers_prices_nothing(self):
        """Cache reads are the largest kind in this corpus by a wide margin, so a table that
        can price input and output but not the cache kinds must not produce a figure at all.
        The same rule as the previous test, applied to the multipliers rather than the model."""
        self.mixed_corpus()

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED},
                                                      multipliers={}))

        self.assertEqual(payload["rates"]["priced_models"], 0)
        self.assertIn("cache multipliers", payload["rates"]["note"])
        self.assertIsNone(self.by_model(payload)["test-model"]["cost_usd"])

    def test_s011_no_prefix_match_prices_a_model_the_table_does_not_name(self):
        """A dated snapshot id is a different string from the alias, and matching by prefix
        would price whatever a future model happened to be called. The shipped table names both
        forms explicitly; the loader matches neither loosely."""
        self.build_store([self.assistant("a1", model="claude-haiku-4-5-20251001",
                                         input_tokens=MILLION)])

        rows = self.by_model(self.cost(pricing=self.pricing_file(
            {"claude-haiku-4-5": {"input": 1.0, "output": 5.0}})))

        self.assertIn("claude-haiku-4-5-20251001", rows)
        self.assertIsNone(rows["claude-haiku-4-5-20251001"]["cost_usd"])

    def test_s011_a_record_carrying_no_model_is_named_rather_than_dropped(self):
        """Its tokens still have to land somewhere, or the per-model figures stop adding up to
        the totals printed beside them."""
        self.build_store([self.assistant("a1", model=None, input_tokens=42)])

        payload = self.cost(pricing=self.pricing_file({}))

        self.assertIn(serve.MODEL_UNRECORDED, self.by_model(payload))
        self.assertEqual(self.by_model(payload)[serve.MODEL_UNRECORDED]["input_tokens"], 42)
        self.assertEqual(payload["tokens"]["input"], 42)

    def test_s011_the_page_shows_an_unpriced_row_as_a_word_rather_than_a_number(self):
        """The report can be right and the page can still print a blank cell, which reads as
        zero. The assertion is on the branch that builds the cell."""
        body = cost_renderer_body()

        self.assertIn("row.priced", body, "the page does not branch on whether a row is priced")
        self.assertIn('text: "unpriced: unknown, not zero"', body,
                      "the page no longer names an unpriced model's cost as unknown")

    def test_s011_the_policy_is_stated_on_the_surface_rather_than_only_in_the_code(self):
        """A reader has to be told which of two answers they are looking at."""
        self.mixed_corpus()

        payload = self.cost(pricing=self.pricing_file({"test-model": PRICED}))

        self.assertIn("unknown, never zero", payload["unpriced_policy"])
        self.assertIn("data.unpriced_policy", cost_renderer_body(),
                      "the page does not show the policy the report states")


class TestPressureOverTime(CostTestCase):
    """S-017: context and quota pressure are reported over time."""

    def pressured_corpus(self):
        """Two days of context readings in one session, with one compaction between them."""
        self.build_store([
            self.assistant("a1", sid="s1", ts="2026-08-01T10:00:00.000Z"),
            self.context_record("s1", "2026-08-01T10:00:00.000Z", 90000),
            self.context_record("s1", "2026-08-01T11:00:00.000Z", 40000),
            self.compaction_record("s1", "2026-08-01T11:30:00.000Z"),
            self.context_record("s1", "2026-08-02T09:00:00.000Z", 150000),
            self.context_record("s1", "2026-08-02T12:00:00.000Z", 120000),
        ])

    def test_s017_the_context_budget_is_reported_as_a_series_over_time(self):
        """The scenario's Then for the half the corpus actually carries. Exact buckets, in
        order, so a report that returned an unordered bag or a single latest reading fails."""
        self.pressured_corpus()

        context = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]

        self.assertTrue(context["available"])
        self.assertEqual(context["samples"], 4)
        self.assertEqual(context["sessions"], 1)
        self.assertEqual([bucket["day"] for bucket in context["daily"]],
                         ["2026-08-01", "2026-08-02"])
        self.assertEqual(context["daily"][0],
                         {"day": "2026-08-01", "samples": 2,
                          "min_tokens_left": 40000, "max_tokens_left": 90000})
        self.assertEqual(context["daily"][1],
                         {"day": "2026-08-02", "samples": 2,
                          "min_tokens_left": 120000, "max_tokens_left": 150000})

    def test_s017_the_tightest_readings_are_reported_lowest_first(self):
        """"How close to a limit" is the question the report exists for, and a daily mean
        hides the answer. The lowest readings are reported in their own right."""
        self.pressured_corpus()

        lowest = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]["lowest"]

        self.assertEqual([row["tokens_left"] for row in lowest],
                         [40000, 90000, 120000, 150000])
        self.assertEqual(lowest[0]["ts"], "2026-08-01T11:00:00.000Z")
        self.assertEqual(lowest[0]["session_id"], "s1")

    def test_s017_a_compacted_session_is_identifiable(self):
        """The scenario's own clause. A `compact_boundary` record is the only marker the corpus
        carries for one, so identifiable means this row reaches the report with its session and
        its time."""
        self.pressured_corpus()

        context = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]

        self.assertEqual(context["compaction_count"], 1)
        self.assertEqual(context["compactions"],
                         [{"session_id": "s1", "ts": "2026-08-01T11:30:00.000Z"}])

    def test_s017_a_session_that_was_never_compacted_reports_none_rather_than_nothing(self):
        """Zero compactions is an answer. An empty list with no count beside it is not."""
        self.build_store([self.assistant("a1", sid="s1"),
                          self.context_record("s1", "2026-08-01T10:00:00.000Z", 90000)])

        context = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]

        self.assertTrue(context["available"])
        self.assertEqual(context["compaction_count"], 0)
        self.assertEqual(context["compactions"], [])

    def test_s017_pressure_is_restricted_to_one_project_with_the_rest_of_the_report(self):
        """The scope selector has to reach this panel too, or a reader sees one project's cost
        beside every project's pressure."""
        other = self.corpus / "D--other"
        self.build_store([self.assistant("a1", sid="s1"),
                          self.context_record("s1", "2026-08-01T10:00:00.000Z", 90000)])
        self.build_store([self.assistant("b1", sid="s2"),
                          self.context_record("s2", "2026-08-01T10:00:00.000Z", 10000),
                          self.compaction_record("s2", "2026-08-01T10:30:00.000Z")],
                         name="other.jsonl", project=other)

        here = self.cost(project="D--demo",
                         pricing=self.pricing_file({}))["pressure"]["context"]
        everywhere = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]

        self.assertEqual(here["samples"], 1)
        self.assertEqual(here["compaction_count"], 0,
                         "another project's compaction was reported under this one")
        self.assertEqual(everywhere["samples"], 2)
        self.assertEqual(everywhere["compaction_count"], 1)

    def test_s017_no_context_records_is_stated_rather_than_shown_as_a_flat_series(self):
        """The empty input. A chart of nothing looks like a corpus under no pressure."""
        self.build_store([self.assistant("a1")])

        context = self.cost(pricing=self.pricing_file({}))["pressure"]["context"]

        self.assertFalse(context["available"])
        self.assertEqual(context["daily"], [])
        self.assertIn("no series to report", context["reason"])

    # -- the quota half -------------------------------------------------------------

    def test_s017_the_report_renders_with_the_quota_source_absent(self):
        """The task's own acceptance criterion, and the contract's Sources table marking this
        source not required. Absent degrades the report to its context half; it does not fail
        it and does not report an error."""
        self.pressured_corpus()

        payload = self.cost(pricing=self.pricing_file({}), quota=None)
        quota = payload["pressure"]["quota"]

        self.assertFalse(quota["available"])
        self.assertTrue(quota["reason"], "the absence is silent rather than stated")
        self.assertEqual(quota["series"], [])
        self.assertEqual(quota["unreadable"], 0)
        # The key, not the word. The provenance sentence says "not an error", so a substring
        # search over the payload would have been satisfied by the very text that says the
        # opposite of what the assertion means.
        self.assertNotIn("error", quota, "the absent source is reported as an error")
        self.assertNotIn("error", payload, "the report as a whole failed")
        self.assertTrue(payload["pressure"]["context"]["available"],
                        "the context half went missing with the quota half")

    def test_s017_a_quota_file_that_is_not_there_is_a_state_not_a_failure(self):
        """The other absent case: a path was configured and nothing is at it."""
        self.pressured_corpus()

        quota = self.cost(pricing=self.pricing_file({}),
                          quota=self.tmp / "nope.jsonl")["pressure"]["quota"]

        self.assertFalse(quota["available"])
        self.assertIn("nope.jsonl", quota["reason"])
        self.assertIn("context half", quota["reason"])

    def test_s017_a_quota_file_that_exists_and_holds_nothing_readable_is_not_available(self):
        """The third absent case, and the only one nothing reached before.

        The two tests above return from earlier branches: no path configured, and a path with
        no file at it. Neither touches the line that decides availability from the samples
        actually parsed, so a file that exists and yields none of them could be reported
        available with the whole suite green, and the page would render a Quota panel over
        zero windows as though it had a reading.
        """
        self.pressured_corpus()
        empty = self.tmp / "unreadable.jsonl"
        empty.write_text('not json at all\n{"ts": "2026-08-01T10:00:00Z"}\n',
                         encoding="utf-8", newline="\n")

        quota = self.cost(pricing=self.pricing_file({}), quota=empty)["pressure"]["quota"]

        self.assertFalse(quota["available"],
                         "a file holding no readable sample was reported as an available "
                         "quota source, so the page shows a pressure panel with no reading")
        self.assertEqual(quota["samples"], 0)
        self.assertEqual(quota["windows"], [])
        self.assertEqual(quota["unreadable"], 2,
                         "the unusable lines were dropped silently rather than counted")
        self.assertIn("no readable sample", quota["reason"])

    def test_s017_a_quota_series_is_reported_as_a_series_per_window(self):
        """The other half of the scenario, over the only producer there is: whoever writes the
        file. Exact figures per window, including which sample is the latest."""
        self.pressured_corpus()
        path = self.quota_file([
            json.dumps({"ts": "2026-08-01T10:00:00Z", "window": "session",
                        "used_percent": 12.5}),
            json.dumps({"ts": "2026-08-01T18:00:00Z", "window": "session",
                        "used_percent": 60.0}),
            json.dumps({"ts": "2026-08-01T12:00:00Z", "window": "session",
                        "used_percent": 91.0}),
            json.dumps({"ts": "2026-08-01T12:00:00Z", "window": "week",
                        "used_percent": 30.0}),
        ])

        quota = self.cost(pricing=self.pricing_file({}), quota=path)["pressure"]["quota"]

        self.assertTrue(quota["available"])
        self.assertEqual(quota["samples"], 4)
        self.assertEqual([window["window"] for window in quota["windows"]],
                         ["session", "week"])
        session = quota["windows"][0]
        self.assertEqual(session["samples"], 3)
        self.assertEqual(session["first_ts"], "2026-08-01T10:00:00Z")
        self.assertEqual(session["last_ts"], "2026-08-01T18:00:00Z")
        self.assertEqual(session["latest_used_percent"], 60.0,
                         "the latest sample was taken by file order rather than by time")
        self.assertEqual(session["peak_used_percent"], 91.0,
                         "the peak was taken as the latest rather than as the highest")

    def test_s017_an_unreadable_quota_line_is_counted_rather_than_dropped_silently(self):
        """The same habit S-008 sets for the corpus, applied to the optional source: what could
        not be read is stated, and what could is still reported."""
        self.pressured_corpus()
        path = self.quota_file([
            json.dumps({"ts": "2026-08-01T10:00:00Z", "window": "session",
                        "used_percent": 12.5}),
            "{not json at all",
            json.dumps({"ts": "2026-08-01T11:00:00Z"}),
        ])

        quota = self.cost(pricing=self.pricing_file({}), quota=path)["pressure"]["quota"]

        self.assertTrue(quota["available"])
        self.assertEqual(quota["samples"], 1)
        self.assertEqual(quota["unreadable"], 2,
                         "a malformed line and a line missing its reading were absorbed")

    def test_s017_the_absent_quota_source_names_what_it_would_accept(self):
        """A source nothing on this machine writes is only useful if the report says what it
        would read, and honest only if it says nothing produces it."""
        self.pressured_corpus()

        quota = self.cost(pricing=self.pricing_file({}))["pressure"]["quota"]

        self.assertIn("used_percent", quota["format"])
        self.assertIn("nothing writes it", quota["provenance"])


class TestNoNetworkForRates(CostTestCase):
    """The task's criterion in its own words: no network call is made to obtain rates.

    S-022 already holds for the ingester and the server. This is the one new way in: a rate
    table is exactly the sort of thing a later change would be tempted to fetch, and Open
    Question 1 of the contract records the recommendation against it.
    """

    def test_s022_loading_the_rate_table_opens_no_socket(self):
        """`socket.socket` is replaced for the duration, so constructing one at all fails
        rather than only connecting to a remote host."""
        opened = []
        real_socket = socket.socket

        class Refusing(real_socket):
            def __init__(self, *args, **kwargs):
                # Recorded and then refused, rather than recorded and constructed. Calling
                # `super().__init__` would create a real file descriptor, which makes the
                # docstring above false and leaves a socket to be closed by whoever notices.
                # Raising also fails at the point of the attempt, so a regression names the
                # line that opened one instead of an assertion at the end of the test.
                opened.append(args)
                raise AssertionError(
                    "loading the rate table constructed a socket, which S-022 forbids")

        socket.socket = Refusing
        try:
            table = serve.load_pricing(SHIPPED_PRICING)
            quota = serve.load_quota(None)
        finally:
            socket.socket = real_socket

        self.assertTrue(table["models"], "nothing was loaded, so this asserted nothing")
        self.assertFalse(quota["available"])
        self.assertEqual(opened, [], "loading the rate table opened a socket")

    def test_s022_the_rate_table_is_a_local_file_inside_this_repository(self):
        """A table read from anywhere else is a table that could be fetched. The default path
        is resolved from the module's own location rather than from a URL or an environment
        variable."""
        self.assertTrue(serve.PRICING_PATH.is_file())
        self.assertEqual(serve.PRICING_PATH,
                         REPO_ROOT / "scripts" / "observatory" / "pricing.json")
        text = SHIPPED_PRICING.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"https?://",
                            "the rate table names a URL, which invites a fetch")


class TestCostOverHttp(ServedCostTestCase):
    """The route half. Calling the report function directly cannot catch a scope parameter
    that never reaches it, which is the mutation that left the shell's own scope test green."""

    def test_the_cost_report_is_served_over_http_and_matches_the_store(self):
        self.build_store([self.assistant("a1", model="test-model",
                                         input_tokens=2 * MILLION,
                                         output_tokens=1 * MILLION,
                                         cache_read=10 * MILLION,
                                         cache_creation=4 * MILLION)])
        pricing = self.pricing_file({"test-model": PRICED})
        server = self.serve_on_loopback(pricing=pricing)

        status, served = self.fetch_json(server, "/api/cost")
        direct = self.cost(pricing=pricing)

        self.assertEqual(status, 200)
        self.assertEqual(served["cost"], direct["cost"])
        self.assertEqual(served["tokens"], direct["tokens"])
        self.assertEqual(served["cost"]["estimated_usd"], 65.0)
        self.assertEqual(served["rates"]["as_of"], "2026-01-01")

    def test_the_scope_selectors_choice_reaches_the_cost_report(self):
        self.build_store([self.assistant("a1", sid="s1", input_tokens=100)])
        other = self.corpus / "D--other"
        self.build_store([self.assistant("b1", sid="s2", input_tokens=7)],
                         name="other.jsonl", project=other)
        server = self.serve_on_loopback(pricing=self.pricing_file({}))

        _, everywhere = self.fetch_json(server, "/api/cost")
        _, here = self.fetch_json(server, "/api/cost?project=D--demo")

        self.assertEqual(everywhere["tokens"]["input"], 107)
        self.assertEqual(here["project"], "D--demo",
                         "the requested scope did not reach the report")
        self.assertEqual(here["tokens"]["input"], 100)

    def test_the_cost_report_has_a_built_slot_in_the_registry_the_page_renders_from(self):
        """The shell renders navigation from `REPORTS` and the page from `RENDERERS`, so the
        report is only reachable if both name it. A registry entry with no renderer shows the
        owed panel and looks like the feature was never built."""
        entry = [report for report in serve.REPORTS if report["id"] == "cost"][0]

        self.assertEqual(entry["endpoint"], "/api/cost")
        self.assertIsNone(entry["owner"], "the cost report still names a task that owes it")
        self.assertEqual(entry["scenarios"], ["S-010", "S-011", "S-017", "S-021"])
        self.assertIn("  cost: function (data, into) {",
                      UI_INDEX.read_text(encoding="utf-8"),
                      "the page has no renderer for the cost report")

    def test_s021_the_four_kind_rows_each_bind_their_own_field(self):
        """The four rows are built from one array literal, so one careless edit sets them all
        to the same figure and the table renders four identical numbers under four different
        labels. Nothing else in this suite would notice: the payload is still correct, every
        row still renders, and the page still looks like a breakdown.

        Asserting the four bindings are four *distinct* fields is what catches that. A test
        that only asserted `tokens.input` appears somewhere passes against a table showing
        `tokens.total` four times, because the array still mentions the word.

        The bound, stated rather than left implied: this reads the renderer's source, it does
        not execute it. Python's standard library has no JavaScript engine and the conventions
        section of `AGENTS.md` forbids adding one, so the strongest available oracle is the
        binding rather than the rendered cell. It catches every mutation of the shape "this
        row now shows a different field" and would not catch a defect inside `group()`.
        """
        body = cost_renderer_body()
        kinds = body[body.index("var kinds = ["):body.index("]];") + 3]
        bound = set(re.findall(r"tokens\.[a-z_]+", kinds))

        self.assertEqual(
            bound, {"tokens.input", "tokens.output", "tokens.cache_read",
                    "tokens.cache_creation"},
            "the tokens-by-kind table does not bind exactly the four kinds, so two rows "
            "either show the same figure or a kind is missing from the breakdown")
        self.assertNotIn("tokens.total", kinds,
                         "a kind row is bound to the total, which renders as a share of "
                         "itself and reads as a measured breakdown")

    def test_s021_the_share_column_is_taken_against_the_total(self):
        """The share denominator is the one value in this table a reader cannot check by
        eye. Bound to a field that does not exist it renders `NaN%` in every row, which is
        visibly broken; bound to the wrong field it renders plausible percentages that do not
        sum to 100, which is not."""
        body = cost_renderer_body()
        share = body[body.index("Share of total"):body.index("data-memo")]

        self.assertIn("pair[1] / tokens.total", share,
                      "the share column is not the kind over the total, so the percentages "
                      "in it are against something else and need not sum to 100")

    def test_s011_the_incompleteness_note_is_bound_to_the_payload_that_states_it(self):
        """S-011's Then puts the burden on the total: one covering unpriced models says so.

        The sentence is the whole of that. Blanked, the report still shows a confident-looking
        headline over a corpus it only partly priced, and every other assertion here still
        passes because the payload's `note` is still correct: only the page stopped saying it.
        """
        body = cost_renderer_body()

        self.assertIn("text: cost.note", body,
                      "the page does not render `cost.note`, so a total covering unpriced "
                      "models no longer says so anywhere a reader looks")
        self.assertIn("cost.complete ?", body,
                      "the note is styled the same whether or not the total is complete, so "
                      "an incomplete total is muted to look like a footnote")
        for field, why in (
                ("data.historical_note", "the page drops the note saying historical sessions "
                                         "are priced at current rates"),
                ("data.estimate_label", "the page drops the label saying every figure is an "
                                        "estimate")):
            with self.subTest(field=field):
                self.assertIn(field, body, why)

        # Scoped to the headline block, not to the renderer. Every one of these fields also
        # appears in a paragraph further down, so a whole-body assertion is satisfied by the
        # second occurrence while the big number above it is a hardcoded literal.
        figures = body[body.index('el("div", { "class": "figures" }'):body.index("cost.note")]
        for field in ("cost.estimated_usd", "cache.served_share", "tokens.total",
                      "tokens.messages"):
            with self.subTest(headline=field):
                self.assertIn(field, figures,
                              f"the headline figures do not bind {field}, so one of the four "
                              f"numbers a reader sees first is not the payload's")

    def test_a_missing_store_is_stated_rather_than_reported_as_a_corpus_that_cost_nothing(self):
        """S-007's habit applied to this report: "the ingester has not run" and "nothing was
        consumed" are different answers, and a cost report is the one place merging them
        produces a confident zero."""
        server = self.serve_on_loopback(pricing=self.pricing_file({}))

        status, payload = self.fetch_json(server, "/api/cost")

        self.assertEqual(status, 200)
        self.assertFalse(payload["store_present"])
        self.assertIn("ingest.py", payload["message"])
        self.assertNotIn("cost", payload, "an absent store produced a cost figure")


def cost_renderer_body() -> str:
    """The body of the page's `cost` renderer, for the assertions that are about the page.

    Sliced by the renderer's own opening line rather than searched for by keyword, so an
    assertion cannot be satisfied by a comment elsewhere in the file. That has happened twice
    in this component: an assertion on a bare word passed against a docstring once and broke
    against a comment once.
    """
    html = UI_INDEX.read_text(encoding="utf-8")
    start = html.index("  cost: function (data, into) {")
    # Bounded at the next member, not at the end of the registry. `cost` is the last renderer
    # today, so the two agree and will stop agreeing the moment another is added after it:
    # the slice would then quietly cover two functions and every assertion here would pass on
    # the wrong one. Ending it at the next member costs nothing and cannot drift.
    following = [match.start() for match in
                 re.finditer(r"\n  [a-z]+: function \(data, into\) \{", html)
                 if match.start() > start]
    end = min(following + [html.index("\n};", start)])
    return html[start:end]


if __name__ == "__main__":
    unittest.main()
