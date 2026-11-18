"""Tests for :mod:`problem_radar.pipeline`."""

from __future__ import annotations

import unittest

from problem_radar.pipeline import collect, load_or_rebuild, rebuild_clusters
from problem_radar.sources import HttpClient
from problem_radar.store import load_clusters, load_signals, save_clusters
from tests.helpers import FakeTransport, make_sandbox


def make_client() -> HttpClient:
    return HttpClient(
        FakeTransport(
            {
                "hn.algolia.com": "file:hn_search_ask.json",
                "api.github.com": "file:github_search_llm.json",
            }
        ),
        min_intervals={},
        sleep=lambda _seconds: None,
    )


class CollectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp, self.sandbox = make_sandbox()
        self.config = self.sandbox.config

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_collect_writes_signals(self) -> None:
        summary = collect(self.config, client=make_client())
        self.assertEqual(len(summary.sources), 3)  # hackernews, github, manual
        self.assertGreater(summary.total_added, 0)
        self.assertTrue(self.config.signals_path.is_file())
        stored = load_signals(self.config.signals_path)
        self.assertEqual(len(stored), summary.total_added)

    def test_collect_is_idempotent(self) -> None:
        collect(self.config, client=make_client())
        second = collect(self.config, client=make_client())
        self.assertEqual(second.total_added, 0)
        self.assertGreater(sum(report.skipped for report in second.sources), 0)

    def test_dry_run_writes_nothing(self) -> None:
        summary = collect(self.config, client=make_client(), dry_run=True)
        self.assertGreater(summary.total_added, 0)
        self.assertFalse(self.config.signals_path.exists())

    def test_single_source(self) -> None:
        summary = collect(self.config, client=make_client(), only="hackernews")
        self.assertEqual([report.name for report in summary.sources], ["hackernews"])

    def test_missing_manual_file_is_reported_not_fatal(self) -> None:
        (self.sandbox.directory / "data" / "manual-signals.jsonl").unlink()
        summary = collect(self.config, client=make_client())
        manual = next(report for report in summary.sources if report.name == "manual")
        self.assertEqual(manual.added, 0)
        self.assertTrue(manual.errors)

    def test_limit_override(self) -> None:
        summary = collect(self.config, client=make_client(), only="hackernews", limit=2)
        self.assertLessEqual(summary.total_added, 2)


class ClusterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp, self.sandbox = make_sandbox()
        self.config = self.sandbox.config
        collect(self.config, client=make_client())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_rebuild_scores_and_saves(self) -> None:
        clusters = rebuild_clusters(self.config)
        self.assertTrue(clusters)
        self.assertIsNotNone(clusters[0].score)
        self.assertTrue(self.config.clusters_path.is_file())
        self.assertGreaterEqual(
            clusters[0].score.total,
            clusters[-1].score.total,  # type: ignore[union-attr]
        )

    def test_human_state_survives_reclustering(self) -> None:
        clusters = rebuild_clusters(self.config)
        clusters[0].status = "approved"
        clusters[0].note = "keep this"
        save_clusters(self.config.clusters_path, clusters)

        again = rebuild_clusters(self.config)
        matched = next(cluster for cluster in again if cluster.id == clusters[0].id)
        self.assertEqual(matched.status, "approved")
        self.assertEqual(matched.note, "keep this")

    def test_load_or_rebuild(self) -> None:
        clusters = load_or_rebuild(self.config)
        self.assertTrue(clusters)
        self.assertTrue(self.config.clusters_path.is_file())
        reloaded = load_clusters(self.config.clusters_path)
        self.assertEqual(len(reloaded), len(clusters))


class EmptyPipelineTests(unittest.TestCase):
    def test_no_signals(self) -> None:
        temp, sandbox = make_sandbox()
        try:
            clusters = load_or_rebuild(sandbox.config)
            self.assertEqual(clusters, [])
            self.assertTrue((sandbox.directory / "data" / "clusters.json").is_file())
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
