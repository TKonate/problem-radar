"""Regression tests for the heuristics that keep the radar usable.

Each case here was a real failure during the first runs: substrings matching
inside words ("debug" counted as "bug"), generic words merging unrelated
titles, bot issues flooding the report, and full issue threads stored verbatim.
"""

from __future__ import annotations

import json
import unittest

from problem_radar.dedupe import token_weights, weighted_similarity
from problem_radar.sources import HttpClient, SourceConfig, collect_github
from problem_radar.text import has_keyword, infer_category, is_problem_like
from tests.helpers import FakeTransport


class KeywordBoundaryTests(unittest.TestCase):
    def test_word_boundaries(self) -> None:
        self.assertFalse(has_keyword("debug the app", "bug"))
        self.assertTrue(has_keyword("a bug in the app", "bug"))
        self.assertFalse(has_keyword("capital gains", "api"))
        self.assertTrue(has_keyword("the api returns 500", "api"))

    def test_category_does_not_fire_on_substrings(self) -> None:
        self.assertEqual(infer_category("[Debug] chat · CHAT_FAILED"), "other")
        self.assertEqual(infer_category("App crashes on start"), "recurring-bug")


class NoiseFilterTests(unittest.TestCase):
    def test_commit_prefixes_are_rejected(self) -> None:
        for title in (
            "docs: update the readme",
            "chore(deps): bump pytest",
            "ci: pin actions",
            "feat(api): add endpoint",
        ):
            self.assertFalse(is_problem_like(title), title)

    def test_issue_prefixes_are_kept(self) -> None:
        self.assertTrue(is_problem_like("[Bug] the export is empty"))
        self.assertTrue(is_problem_like("fix: session drops after login"))
        self.assertTrue(is_problem_like("[Regression] CLI exits with 127"))

    def test_launch_announcements_are_rejected(self) -> None:
        self.assertFalse(is_problem_like("Show HN: my new startup"))
        self.assertFalse(is_problem_like("Introducing our new pricing page"))


class WeightedSimilarityTests(unittest.TestCase):
    def test_rare_tokens_weigh_more(self) -> None:
        weights = token_weights(
            [
                "Why birds keep crashing into planes",
                "Why ships keep crashing in storms",
                "Docker build crashes with exit code 137",
            ]
        )
        self.assertGreater(weights["docker"], weights["crashing"])

    def test_generic_word_is_not_enough(self) -> None:
        titles = [
            "Why birds keep crashing into planes",
            "Why ships keep crashing in storms",
            "Docker build crashes with exit code 137",
        ]
        weights = token_weights(titles)
        score = weighted_similarity(titles[0], titles[1], weights)
        self.assertLess(score, 0.45)

    def test_shared_rare_tokens_still_match(self) -> None:
        titles = [
            "Model not found: llama3.2 on startup",
            "Model not found after pulling qwen2.5",
            "Calendar sync fails on iOS",
        ]
        weights = token_weights(titles)
        score = weighted_similarity(titles[0], titles[1], weights)
        self.assertGreaterEqual(score, 0.30)


class BodyMinimisationTests(unittest.TestCase):
    def test_github_body_is_truncated(self) -> None:
        issue = {
            "number": 1,
            "title": "Model not found on startup",
            "body": "x" * 10_000,
            "html_url": "https://github.com/o/r/issues/1",
            "created_at": "2026-11-01T00:00:00Z",
            "repository_url": "https://api.github.com/repos/o/r",
            "user": {"login": "someone"},
            "labels": [],
        }
        transport = FakeTransport({"api.github.com": (200, json.dumps({"items": [issue]}))})
        client = HttpClient(transport, min_intervals={}, sleep=lambda _s: None)
        result = collect_github(
            SourceConfig(name="github", kind="github", queries=["model not found"]), client
        )
        self.assertEqual(len(result.signals), 1)
        self.assertLessEqual(len(result.signals[0].body), 2001)


if __name__ == "__main__":
    unittest.main()
