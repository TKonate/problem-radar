"""Tests for :mod:`problem_radar.models`."""

from __future__ import annotations

import unittest

from problem_radar.models import (
    PIPELINE_STATUSES,
    SOLUTION_STATUSES,
    Cluster,
    Score,
    Signal,
    Solution,
    utc_now,
)


def make_signal(**overrides: object) -> Signal:
    values: dict[str, object] = {
        "source": "hackernews",
        "source_id": "1234",
        "url": "https://news.ycombinator.com/item?id=1234",
        "title": "Agent loop never stops",
        "body": "It keeps calling the same tool.",
        "author": "someone",
        "published_at": "2026-11-01",
        "domain": "ai-agents",
        "category": "recurring-bug",
        "problem": "Agent loop never stops",
        "evidence": "It keeps calling the same tool.",
        "confidence": 0.35,
        "tags": ["social"],
    }
    values.update(overrides)
    return Signal(**values)  # type: ignore[arg-type]


class SignalTests(unittest.TestCase):
    def test_id_is_stable_and_source_scoped(self) -> None:
        first = make_signal()
        self.assertEqual(first.id, make_signal().id)
        self.assertNotEqual(first.id, make_signal(source="github").id)
        self.assertNotEqual(first.id, make_signal(source_id="999").id)
        self.assertEqual(len(first.id), 16)

    def test_round_trip(self) -> None:
        signal = make_signal()
        payload = signal.to_dict()
        rebuilt = Signal.from_dict(payload)
        self.assertEqual(rebuilt.to_dict(), payload)
        self.assertEqual(rebuilt.id, signal.id)

    def test_from_dict_tolerates_missing_optional_fields(self) -> None:
        rebuilt = Signal.from_dict({"source": "manual", "source_id": "x", "url": "", "title": "T"})
        self.assertEqual(rebuilt.domain, "other")
        self.assertEqual(rebuilt.tags, [])
        self.assertAlmostEqual(rebuilt.confidence, 0.5)


class SolutionTests(unittest.TestCase):
    def test_label(self) -> None:
        self.assertEqual(Solution(status="none_found").label, "no solution found")

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError):
            Solution(status="maybe")

    def test_round_trip(self) -> None:
        solution = Solution(
            status="exists", url="https://example.org", note="covers 80%", checked_by="palantir"
        )
        rebuilt = Solution.from_dict(solution.to_dict())
        self.assertEqual(rebuilt.to_dict(), solution.to_dict())


class ScoreTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        score = Score(
            total=42.5,
            components={"volume": 10.0},
            penalties={"solution_exists": -30.0},
            explanation=["volume: 2 signals"],
            recommendation="watch",
        )
        rebuilt = Score.from_dict(score.to_dict())
        self.assertEqual(rebuilt.total, 42.5)
        self.assertEqual(rebuilt.recommendation, "watch")
        self.assertEqual(rebuilt.penalties["solution_exists"], -30.0)


class ClusterTests(unittest.TestCase):
    def test_defaults(self) -> None:
        cluster = Cluster(id="abc", title="T")
        self.assertEqual(cluster.status, "clustered")

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError):
            Cluster(id="abc", title="T", status="done")

    def test_round_trip(self) -> None:
        cluster = Cluster(
            id="abc123",
            title="Agent loop never stops",
            statement="It loops",
            signal_ids=["1", "2"],
            domains=["ai-agents"],
            categories=["recurring-bug"],
            first_seen="2026-11-01",
            last_seen="2026-11-02",
            score=Score(total=10.0, recommendation="ignore"),
            solutions=[Solution(status="unknown")],
            status="researched",
            note="checked by hand",
        )
        rebuilt = Cluster.from_dict(cluster.to_dict())
        self.assertEqual(rebuilt.to_dict(), cluster.to_dict())
        self.assertEqual(rebuilt.score.total, 10.0)  # type: ignore[union-attr]

    def test_statuses_and_solutions_are_known(self) -> None:
        self.assertIn("deployed", PIPELINE_STATUSES)
        self.assertIn("poorly_documented", SOLUTION_STATUSES)

    def test_utc_now_looks_like_iso(self) -> None:
        value = utc_now()
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
