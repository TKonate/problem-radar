"""Tests for :mod:`problem_radar.sources`."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError

from problem_radar.config import SourceConfig
from problem_radar.errors import CollectionError
from problem_radar.sources import (
    HttpClient,
    HttpResponse,
    collect_github,
    collect_hackernews,
    collect_manual,
    collect_rss,
    collect_source,
    parse_feed,
)
from tests.helpers import FakeTransport


def make_client(routes: dict[str, tuple[int, str] | str], **kwargs: object) -> HttpClient:
    options = {"min_intervals": {}, "sleep": lambda _seconds: None}
    options.update(kwargs)
    return HttpClient(FakeTransport(routes), **options)  # type: ignore[arg-type]


class SequenceTransport:
    """Transport returning a scripted sequence of responses."""

    def __init__(self, responses: list[HttpResponse | Exception]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get(self, url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class HttpClientTests(unittest.TestCase):
    def test_get_json(self) -> None:
        client = make_client({"example.org": '{"ok": true}'})
        self.assertEqual(client.get_json("https://example.org/x"), {"ok": True})

    def test_params_are_encoded(self) -> None:
        transport = FakeTransport({"example.org": '{"ok": true}'})
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None)
        client.get_json("https://example.org/search", {"q": "a b", "n": 2})
        self.assertIn("q=a+b", transport.calls[0][0])
        self.assertIn("n=2", transport.calls[0][0])

    def test_user_agent_is_sent(self) -> None:
        transport = FakeTransport({"example.org": '{"ok": true}'})
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None)
        client.get_json("https://example.org/x")
        self.assertIn("problem-radar", transport.calls[0][1]["User-Agent"])

    def test_github_forbidden_explains_token(self) -> None:
        client = make_client({"api.github.com": (403, "")})
        with self.assertRaises(CollectionError) as caught:
            client.get_json("https://api.github.com/search/issues")
        self.assertIn("GITHUB_TOKEN", str(caught.exception))

    def test_not_found_raises(self) -> None:
        client = make_client({})
        with self.assertRaises(CollectionError) as caught:
            client.get("https://example.org/missing")
        self.assertEqual(caught.exception.status, 404)

    def test_retry_then_success(self) -> None:
        sleeps: list[float] = []
        transport = SequenceTransport(
            [
                HttpResponse(status=429, body="", headers={"retry-after": "1"}),
                HttpResponse(status=200, body='{"ok": 1}'),
            ]
        )
        client = HttpClient(transport, min_intervals={"example.org": 0.0}, sleep=sleeps.append)
        self.assertEqual(client.get_json("https://example.org/x"), {"ok": 1})
        self.assertEqual(sleeps, [1.0])

    def test_retries_exhausted(self) -> None:
        transport = SequenceTransport([HttpResponse(status=503, body="")] * 3)
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None, retries=2)
        with self.assertRaises(CollectionError):
            client.get("https://example.org/x")
        self.assertEqual(transport.calls, 3)

    def test_network_error_is_wrapped(self) -> None:
        transport = SequenceTransport([URLError("boom")] * 3)
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None, retries=2)
        with self.assertRaises(CollectionError) as caught:
            client.get("https://example.org/x")
        self.assertIn("network error", str(caught.exception))

    def test_throttle_sleeps_between_calls(self) -> None:
        sleeps: list[float] = []
        client = HttpClient(
            FakeTransport({"example.org": "ok"}),
            min_intervals={"example.org": 5.0},
            sleep=sleeps.append,
        )
        clock = [0.0]
        client._clock = lambda: clock[0]  # type: ignore[assignment]

        client.get("https://example.org/a")
        clock[0] = 2.0
        client.get("https://example.org/b")
        clock[0] = 10.0
        client.get("https://example.org/c")
        self.assertEqual(sleeps, [3.0])

    def test_invalid_json(self) -> None:
        client = make_client({"example.org": "not json"})
        with self.assertRaises(CollectionError):
            client.get_json("https://example.org/x")


class HackerNewsTests(unittest.TestCase):
    def source(self, query: str = "Ask HN") -> SourceConfig:
        return SourceConfig(
            name="hackernews", kind="hackernews", tier="social", queries=[query], limit=10
        )

    def test_collect_questions(self) -> None:
        client = make_client({"hn.algolia.com": "file:hn_search_ask.json"})
        result = collect_hackernews(self.source(), client)
        self.assertEqual(result.collected, 10)
        self.assertEqual(len(result.signals), 10)
        self.assertEqual(result.filtered, 0)
        first = result.signals[0]
        self.assertEqual(first.source, "hackernews")
        self.assertTrue(first.url.startswith("https://news.ycombinator.com/item?id="))
        self.assertTrue(first.published_at)
        self.assertIn("query:Ask HN", first.tags)
        self.assertAlmostEqual(first.confidence, 0.35)

    def test_noise_is_filtered(self) -> None:
        client = make_client({"hn.algolia.com": "file:hn_search_agent.json"})
        result = collect_hackernews(self.source("AI agent"), client)
        self.assertEqual(result.collected, 8)
        self.assertEqual(len(result.signals) + result.filtered, 8)
        self.assertGreater(result.filtered, 0)

    def test_query_error_is_reported(self) -> None:
        client = make_client({"hn.algolia.com": (500, "")})
        result = collect_hackernews(self.source(), client)
        self.assertTrue(result.errors)
        self.assertEqual(result.signals, [])


class GitHubTests(unittest.TestCase):
    def source(self) -> SourceConfig:
        return SourceConfig(
            name="github", kind="github", tier="issue-tracker", queries=["llm in:title"], limit=5
        )

    def test_collect(self) -> None:
        client = make_client({"api.github.com": "file:github_search_llm.json"})
        result = collect_github(self.source(), client)
        self.assertEqual(result.collected, 5)
        self.assertTrue(result.signals)
        signal = result.signals[0]
        self.assertEqual(signal.source, "github")
        self.assertIn("#", signal.source_id)
        self.assertTrue(signal.url.startswith("https://github.com/"))
        self.assertAlmostEqual(signal.confidence, 0.85)

    def test_token_is_used_when_present(self) -> None:
        import os

        transport = FakeTransport({"api.github.com": "file:github_search_llm.json"})
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None)
        previous = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "test-token"
        try:
            collect_github(self.source(), client)
        finally:
            if previous is None:
                os.environ.pop("GITHUB_TOKEN", None)
            else:
                os.environ["GITHUB_TOKEN"] = previous
        self.assertEqual(transport.calls[0][1]["Authorization"], "Bearer test-token")

    def test_rate_limit_error_is_reported(self) -> None:
        client = make_client({"api.github.com": (403, "")})
        result = collect_github(self.source(), client)
        self.assertTrue(result.errors)


class RssTests(unittest.TestCase):
    def source(self) -> SourceConfig:
        return SourceConfig(
            name="rss",
            kind="rss",
            tier="blog",
            feeds=["https://simonwillison.net/atom/everything/"],
            limit=5,
        )

    def test_parse_atom_fixture(self) -> None:
        items = parse_feed(
            (Path(__file__).parent / "fixtures" / "atom_sample.xml").read_text(encoding="utf-8")
        )
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0]["title"])
        self.assertTrue(items[0]["link"].startswith("http"))

    def test_parse_rss_style(self) -> None:
        rss = (
            "<rss><channel><item><title>Docker build fails</title>"
            "<link>https://example.org/a</link><description>It crashes.</description>"
            "<pubDate>Mon, 03 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>"
        )
        items = parse_feed(rss)
        self.assertEqual(items[0]["title"], "Docker build fails")
        self.assertEqual(items[0]["link"], "https://example.org/a")

    def test_invalid_xml(self) -> None:
        with self.assertRaises(CollectionError):
            parse_feed("<not-xml")

    def test_collect_rss(self) -> None:
        client = make_client({"simonwillison.net": "file:atom_sample.xml"})
        result = collect_rss(self.source(), client)
        self.assertEqual(result.collected, 3)
        self.assertGreaterEqual(len(result.signals) + result.filtered, 3)

    def test_feed_error_is_reported(self) -> None:
        client = make_client({"simonwillison.net": (500, "")})
        result = collect_rss(self.source(), client)
        self.assertTrue(result.errors)


class ManualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def source(self, path: str = "manual.jsonl") -> SourceConfig:
        return SourceConfig(name="manual", kind="manual", tier="unknown", path=path)

    def test_reads_valid_lines(self) -> None:
        path = self.directory / "manual.jsonl"
        path.write_text(
            json.dumps(
                {
                    "title": "Agent crashes on startup",
                    "url": "https://example.org/1",
                    "body": "It crashes every time.",
                    "domain": "ai-agents",
                    "category": "recurring-bug",
                }
            )
            + "\n"
            + "# a comment\n",
            encoding="utf-8",
        )
        client = make_client({})
        result = collect_manual(self.source(), client, base_dir=self.directory)
        self.assertEqual(len(result.signals), 1)
        signal = result.signals[0]
        self.assertEqual(signal.domain, "ai-agents")
        self.assertEqual(signal.category, "recurring-bug")
        self.assertEqual(signal.source, "manual")

    def test_invalid_lines_are_reported(self) -> None:
        path = self.directory / "manual.jsonl"
        path.write_text("{broken\n" + json.dumps({"title": ""}) + "\n", encoding="utf-8")
        result = collect_manual(self.source(), make_client({}), base_dir=self.directory)
        self.assertEqual(result.signals, [])
        self.assertEqual(len(result.errors), 2)

    def test_missing_file(self) -> None:
        result = collect_manual(self.source("nope.jsonl"), make_client({}), base_dir=self.directory)
        self.assertTrue(result.errors)

    def test_limit(self) -> None:
        path = self.directory / "manual.jsonl"
        lines = [
            json.dumps({"title": f"Agent crashes number {index}", "url": f"https://e.org/{index}"})
            for index in range(5)
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = collect_manual(self.source(), make_client({}), base_dir=self.directory, limit=2)
        self.assertEqual(len(result.signals), 2)


class DispatchTests(unittest.TestCase):
    def test_unknown_kind(self) -> None:
        source = SourceConfig(name="x", kind="hackernews", queries=["ai"])
        source.kind = "telegram"  # bypass __post_init__ on purpose
        with self.assertRaises(CollectionError):
            collect_source(source, make_client({}))


if __name__ == "__main__":
    unittest.main()
