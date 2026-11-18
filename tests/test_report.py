"""Tests for :mod:`problem_radar.report`."""

from __future__ import annotations

import json
import unittest

from problem_radar.models import Cluster, Score, Signal, Solution
from problem_radar.report import (
    RECOMMENDATIONS,
    export_json,
    render_cluster,
    render_markdown,
    report_filename,
    solution_label,
    write_report,
)
from tests.helpers import make_sandbox


def signal(source_id: str = "1", **overrides: object) -> Signal:
    values: dict[str, object] = {
        "source": "hackernews",
        "source_id": source_id,
        "url": f"https://example.org/{source_id}",
        "title": "Agent loop never stops",
        "body": "It crashes after two minutes.",
        "author": "someone",
        "published_at": "2026-11-01",
        "domain": "ai-agents",
        "category": "recurring-bug",
        "problem": "Agent loop never stops",
        "evidence": "It crashes after two minutes.",
        "confidence": 0.35,
    }
    values.update(overrides)
    return Signal(**values)  # type: ignore[arg-type]


def cluster(**overrides: object) -> Cluster:
    values: dict[str, object] = {
        "id": "abc123",
        "title": "Agent loop never stops",
        "statement": "The agent keeps calling the same tool.",
        "signal_ids": ["1", "2"],
        "domains": ["ai-agents"],
        "categories": ["recurring-bug"],
        "first_seen": "2026-11-01",
        "last_seen": "2026-11-02",
        "score": Score(
            total=72.0,
            components={"volume": 20.0},
            explanation=["volume: 2 signal(s), saturating at 10 → 20.0/25"],
            recommendation="submit",
        ),
    }
    values.update(overrides)
    return Cluster(**values)  # type: ignore[arg-type]


class ClusterRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        items = [signal("1"), signal("2")]
        self.signals = {item.id: item for item in items}
        self.ids = [item.id for item in items]

    def test_heading_with_score(self) -> None:
        text = render_cluster(cluster(signal_ids=self.ids), self.signals, rank=1)
        self.assertIn("## 1. Agent loop never stops — 72.0/100 (submit to validation)", text)

    def test_metadata_line(self) -> None:
        text = render_cluster(cluster(signal_ids=self.ids), self.signals)
        self.assertIn("signals: **2**", text)
        self.assertIn("status: **clustered**", text)

    def test_evidence_links(self) -> None:
        text = render_cluster(cluster(signal_ids=self.ids), self.signals)
        self.assertIn("[Agent loop never stops](https://example.org/1)", text)
        self.assertIn("> It crashes after two minutes.", text)

    def test_missing_solution_search_is_explicit(self) -> None:
        text = render_cluster(cluster(signal_ids=self.ids), self.signals)
        self.assertIn("Not searched yet", text)

    def test_solution_recorded(self) -> None:
        recorded = cluster(
            signal_ids=self.ids,
            solutions=[
                Solution(status="exists", url="https://example.org/solved", note="covers it")
            ],
        )
        text = render_cluster(recorded, self.signals)
        self.assertIn("solution exists and covers the need", text)
        self.assertIn("https://example.org/solved", text)

    def test_note_is_rendered(self) -> None:
        self.assertIn(
            "**Note.** keep",
            render_cluster(cluster(signal_ids=self.ids, note="keep"), self.signals),
        )

    def test_missing_signal_is_tolerated(self) -> None:
        text = render_cluster(cluster(signal_ids=["missing"]), self.signals)
        self.assertIn("signals: **1**", text)


class ReportRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp, self.sandbox = make_sandbox()
        self.config = self.sandbox.config
        self.signals = [signal("1"), signal("2")]
        self.clusters = [cluster()]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_main_sections(self) -> None:
        text = render_markdown(
            self.clusters,
            self.signals,
            config=self.config,
            generated_at="2026-11-18T00:00:00+00:00",
        )
        self.assertIn("# Problem Radar — 2026-11-18", text)
        self.assertIn("## Summary", text)
        self.assertIn("| 1 | 72.0 | submit to validation | 2 | ai-agents |", text)
        self.assertIn("## Opportunities", text)
        self.assertIn("What the score does not measure", text)
        self.assertIn("## Provenance", text)

    def test_pipe_is_escaped_in_table(self) -> None:
        tricky = cluster(title="Loop | crash")
        text = render_markdown(
            [tricky], self.signals, config=self.config, generated_at="2026-11-18"
        )
        self.assertIn("Loop \\| crash", text)

    def test_empty_report(self) -> None:
        text = render_markdown([], [], config=self.config, generated_at="2026-11-18")
        self.assertIn("no cluster yet", text)
        self.assertIn("run `radar collect`", text)

    def test_hidden_clusters_are_announced(self) -> None:
        clusters = [cluster(id=f"id{index}", title=f"Problem {index}") for index in range(4)]
        text = render_markdown(clusters, self.signals, config=self.config, top=2)
        self.assertIn("2 lower-scored cluster(s)", text)

    def test_write_report_default_name(self) -> None:
        path = write_report(
            self.clusters,
            self.signals,
            config=self.config,
            generated_at="2026-11-18T00:00:00+00:00",
        )
        self.assertEqual(path.name, "2026-11-18-problem-radar.md")
        self.assertTrue(path.is_file())

    def test_write_report_custom_path(self) -> None:
        destination = self.sandbox.directory / "custom" / "report.md"
        path = write_report(self.clusters, self.signals, config=self.config, output=destination)
        self.assertEqual(path, destination)
        self.assertTrue(destination.is_file())

    def test_export_json(self) -> None:
        destination = self.sandbox.directory / "export.json"
        export_json(self.clusters, self.signals, config=self.config, output=destination)
        payload = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(payload["counts"], {"signals": 2, "clusters": 1})
        self.assertEqual(payload["clusters"][0]["id"], "abc123")
        self.assertEqual(len(payload["signals"]), 2)

    def test_helpers(self) -> None:
        self.assertIn("abc123-", report_filename(cluster()))
        self.assertEqual(solution_label("none_found"), "no solution found")
        self.assertIn("submit", RECOMMENDATIONS)


if __name__ == "__main__":
    unittest.main()
