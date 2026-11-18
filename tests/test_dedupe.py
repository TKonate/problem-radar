"""Tests for :mod:`problem_radar.dedupe`."""

from __future__ import annotations

import unittest

from problem_radar.dedupe import ClusterOptions, build_cluster, cluster_id, cluster_signals
from problem_radar.models import Signal


def signal(
    source_id: str, title: str, *, date: str = "2026-11-01", source: str = "hackernews"
) -> Signal:
    return Signal(
        source=source,
        source_id=source_id,
        url=f"https://example.org/{source_id}",
        title=title,
        published_at=date,
        domain="ai-agents",
        confidence=0.35,
    )


class ClusteringTests(unittest.TestCase):
    def test_identical_titles_are_grouped(self) -> None:
        clusters = cluster_signals(
            [signal("1", "Agent loop never stops"), signal("2", "Agent loop never stops")]
        )
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].signal_ids.__len__(), 2)

    def test_near_duplicates_are_grouped(self) -> None:
        clusters = cluster_signals(
            [
                signal("1", "Postgres connection pool exhausted in production"),
                signal("2", "Postgres connection pool keeps getting exhausted in production"),
            ]
        )
        self.assertEqual(len(clusters), 1)

    def test_unrelated_titles_stay_separate(self) -> None:
        clusters = cluster_signals(
            [
                signal("1", "Docker build fails on arm64"),
                signal("2", "Calendar events are not syncing anymore"),
            ]
        )
        self.assertEqual(len(clusters), 2)

    def test_threshold_is_respected(self) -> None:
        signals = [
            signal("1", "Agent loop never stops when tools fail"),
            signal("2", "Agent loop stops when the tool fails"),
        ]
        loose = cluster_signals(signals, ClusterOptions(threshold=0.3))
        strict = cluster_signals(signals, ClusterOptions(threshold=0.99))
        self.assertEqual(len(loose), 1)
        self.assertEqual(len(strict), 2)

    def test_empty_input(self) -> None:
        self.assertEqual(cluster_signals([]), [])

    def test_cap_is_enforced(self) -> None:
        signals = [signal(str(index), f"Title number {index}") for index in range(5)]
        with self.assertRaises(ValueError):
            cluster_signals(signals, ClusterOptions(max_signals=3))


class ClusterBuildingTests(unittest.TestCase):
    def test_representative_title_is_the_most_frequent(self) -> None:
        members = [
            signal("1", "Agent loop never stops"),
            signal("2", "Agent loop never stops"),
            signal("3", "Agent loop keeps running forever"),
        ]
        cluster = build_cluster(members)
        self.assertEqual(cluster.title, "Agent loop never stops")

    def test_dates_and_labels(self) -> None:
        cluster = build_cluster(
            [
                signal("1", "Agent loop never stops", date="2026-11-03"),
                signal("2", "Agent loop never stops", date="2026-10-01"),
            ]
        )
        self.assertEqual(cluster.first_seen, "2026-10-01")
        self.assertEqual(cluster.last_seen, "2026-11-03")
        self.assertEqual(cluster.domains, ["ai-agents"])
        self.assertEqual(cluster.status, "clustered")

    def test_statement_includes_evidence(self) -> None:
        first = signal("1", "Agent loop never stops")
        first.body = "It crashes after two minutes of use."
        first.evidence = "It crashes after two minutes of use."
        cluster = build_cluster([first])
        self.assertIn("crashes", cluster.statement)

    def test_empty_members_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_cluster([])

    def test_id_is_order_independent(self) -> None:
        first = [signal("1", "A problem in the agent"), signal("2", "A problem in the agent loop")]
        second = list(reversed(first))
        self.assertEqual(cluster_id(first), cluster_id(second))


if __name__ == "__main__":
    unittest.main()
