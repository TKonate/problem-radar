"""Tests for :mod:`problem_radar.scoring`."""

from __future__ import annotations

import unittest

from problem_radar.models import Cluster, Score, Signal, Solution
from problem_radar.scoring import DEFAULT_WEIGHTS, ScoreOptions, score_cluster, score_clusters


def make_signal(
    index: int,
    *,
    source: str = "hackernews",
    date: str = "2026-11-01",
    title: str = "Agent loop crashes",
) -> Signal:
    return Signal(
        source=source,
        source_id=str(index),
        url=f"https://example.org/{index}",
        title=title,
        body="It crashes and loses data.",
        author="someone",
        published_at=date,
        domain="ai-agents",
        category="recurring-bug",
        problem=title,
        evidence="It crashes and loses data.",
        confidence=0.35,
    )


def make_cluster(signals: list[Signal], **overrides: object) -> Cluster:
    values: dict[str, object] = {
        "id": "cluster01",
        "title": "Agent loop crashes",
        "signal_ids": [signal.id for signal in signals],
    }
    values.update(overrides)
    return Cluster(**values)  # type: ignore[arg-type]


class ScoreTests(unittest.TestCase):
    def test_components_are_reported(self) -> None:
        signals = [make_signal(1), make_signal(2, source="github")]
        score = score_cluster(make_cluster(signals), signals, now="2026-11-02")
        self.assertEqual(
            set(score.components),
            {"volume", "diversity", "recency", "severity", "evidence", "confidence"},
        )
        self.assertEqual(len(score.explanation), 7)  # six components + corroboration
        self.assertGreater(score.total, 0)
        self.assertLessEqual(score.total, 100)

    def test_volume_saturates(self) -> None:
        few = [make_signal(index) for index in range(2)]
        many = [make_signal(index) for index in range(10)]
        score_few = score_cluster(make_cluster(few), few, now="2026-11-02")
        score_many = score_cluster(make_cluster(many), many, now="2026-11-02")
        self.assertLess(score_few.components["volume"], score_many.components["volume"])
        self.assertAlmostEqual(score_many.components["volume"], 25.0, places=1)

    def test_recency_decays(self) -> None:
        signal = make_signal(1, date="2026-01-01")
        fresh = score_cluster(make_cluster([signal]), [signal], now="2026-01-02")
        old = score_cluster(make_cluster([signal]), [signal], now="2026-10-01")
        self.assertGreater(fresh.components["recency"], old.components["recency"])

    def test_missing_dates_are_neutral(self) -> None:
        signal = make_signal(1, date="")
        score = score_cluster(make_cluster([signal]), [signal], now="2026-11-02")
        self.assertAlmostEqual(score.components["recency"], 7.5, places=1)

    def test_diversity_rewards_distinct_sources(self) -> None:
        one_source = [make_signal(index, source="hackernews") for index in range(4)]
        four_sources = [
            make_signal(1, source="hackernews"),
            make_signal(2, source="github"),
            make_signal(3, source="rss"),
            make_signal(4, source="manual"),
        ]
        low = score_cluster(make_cluster(one_source), one_source, now="2026-11-02")
        high = score_cluster(make_cluster(four_sources), four_sources, now="2026-11-02")
        self.assertLess(low.components["diversity"], high.components["diversity"])
        self.assertAlmostEqual(high.components["diversity"], 20.0, places=1)

    def test_existing_solution_is_a_penalty(self) -> None:
        signals = [make_signal(1)]
        plain = score_cluster(make_cluster(signals), signals, now="2026-11-02")
        solved = score_cluster(
            make_cluster(
                signals,
                solutions=[Solution(status="exists", url="https://example.org/solved")],
            ),
            signals,
            now="2026-11-02",
        )
        self.assertLess(solved.total, plain.total)
        self.assertIn("solution_exists", solved.penalties)
        self.assertAlmostEqual(solved.penalties["solution_exists"], -30.0)

    def test_score_never_goes_negative(self) -> None:
        signals = [make_signal(1)]
        zero_weights = ScoreOptions(weights={key: 0.0 for key in DEFAULT_WEIGHTS})
        score = score_cluster(
            make_cluster(signals, solutions=[Solution(status="exists")]),
            signals,
            options=zero_weights,
            now="2026-11-02",
        )
        self.assertEqual(score.total, 0.0)
        self.assertEqual(score.recommendation, "ignore")

    def test_single_signal_is_discounted(self) -> None:
        one = [make_signal(1)]
        four = [
            make_signal(index, source=source)
            for index, source in enumerate(["hackernews", "github", "rss", "manual"])
        ]
        single = score_cluster(make_cluster(one), one, now="2026-11-02")
        corroborated = score_cluster(make_cluster(four), four, now="2026-11-02")
        self.assertLess(single.total, 45.0)
        self.assertLess(single.total, corroborated.total)
        self.assertTrue(any("corroboration" in line for line in single.explanation))

    def test_recommendation_thresholds(self) -> None:
        options = ScoreOptions(thresholds={"submit": 10, "research": 5, "watch": 1})
        signals = [make_signal(index) for index in range(10)]
        score = score_cluster(make_cluster(signals), signals, options=options, now="2026-11-02")
        self.assertEqual(score.recommendation, "submit")

    def test_empty_cluster_scores_zero(self) -> None:
        score = score_cluster(Cluster(id="x", title="T", signal_ids=["missing"]), [])
        self.assertEqual(
            score,
            Score(
                total=0.0,
                explanation=["no signal attached to this cluster"],
                recommendation="ignore",
            ),
        )

    def test_score_clusters_sorts(self) -> None:
        weak = [make_signal(1, source="hackernews")]
        strong = [
            make_signal(index, source=source)
            for index, source in enumerate(["hackernews", "github", "rss", "manual"])
        ]
        clusters = [make_cluster(weak, id="weak"), make_cluster(strong, id="strong")]
        scored = score_clusters(clusters, weak + strong, now="2026-11-02")
        self.assertEqual(scored[0].id, "strong")
        self.assertGreater(scored[0].score.total, scored[1].score.total)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
