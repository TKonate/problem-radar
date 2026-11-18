"""Tests for :mod:`problem_radar.store`."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from problem_radar.errors import StorageError
from problem_radar.models import Cluster, Signal, Solution
from problem_radar.store import (
    append_signals,
    atomic_write_text,
    carry_over_state,
    load_clusters,
    load_signals,
    save_clusters,
)


def signal(source_id: str, title: str = "Agent loop crashes") -> Signal:
    return Signal(
        source="hackernews",
        source_id=source_id,
        url=f"https://example.org/{source_id}",
        title=title,
        published_at="2026-11-01",
    )


class SignalStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "data" / "signals.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_file_is_empty(self) -> None:
        self.assertEqual(load_signals(self.path), [])

    def test_append_and_reload(self) -> None:
        added, skipped = append_signals(self.path, [signal("1"), signal("2")])
        self.assertEqual((added, skipped), (2, 0))
        loaded = load_signals(self.path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].title, "Agent loop crashes")

    def test_duplicates_are_skipped(self) -> None:
        append_signals(self.path, [signal("1")])
        added, skipped = append_signals(self.path, [signal("1"), signal("2")])
        self.assertEqual((added, skipped), (1, 1))
        self.assertEqual(len(load_signals(self.path)), 2)

    def test_duplicate_inside_one_batch(self) -> None:
        added, skipped = append_signals(self.path, [signal("1"), signal("1")])
        self.assertEqual((added, skipped), (1, 1))

    def test_corrupt_line_is_reported(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"source": "x", "source_id": 1, "url": "", "title": "t"}\nnot json\n')
        with self.assertRaises(StorageError) as caught:
            load_signals(self.path)
        self.assertIn(":2:", str(caught.exception))


class ClusterStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "data" / "clusters.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_file(self) -> None:
        self.assertEqual(load_clusters(self.path), [])

    def test_round_trip(self) -> None:
        clusters = [
            Cluster(
                id="a",
                title="Agent loop crashes",
                signal_ids=["1", "2"],
                status="researched",
                note="checked",
                solutions=[Solution(status="none_found")],
            )
        ]
        save_clusters(self.path, clusters)
        loaded = load_clusters(self.path)
        self.assertEqual(loaded[0].to_dict(), clusters[0].to_dict())

    def test_invalid_json(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{oops", encoding="utf-8")
        with self.assertRaises(StorageError):
            load_clusters(self.path)

    def test_wrong_shape(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"items": []}), encoding="utf-8")
        with self.assertRaises(StorageError):
            load_clusters(self.path)

    def test_atomic_write_leaves_no_temp(self) -> None:
        atomic_write_text(self.path, "hello\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "hello\n")
        self.assertEqual(list(self.path.parent.glob(".radar-*")), [])


class CarryOverTests(unittest.TestCase):
    def test_status_note_and_solutions_are_kept(self) -> None:
        previous = Cluster(
            id="old",
            title="Agent loop crashes",
            signal_ids=["1", "2"],
            status="approved",
            note="worth building",
            solutions=[Solution(status="exists", url="https://example.org")],
        )
        new = Cluster(id="new", title="Agent loop crashes", signal_ids=["1", "2", "3"])
        carried = carry_over_state([new], [previous])
        self.assertEqual(carried, 1)
        self.assertEqual(new.status, "approved")
        self.assertEqual(new.note, "worth building")
        self.assertEqual(new.solutions[0].status, "exists")

    def test_title_fallback(self) -> None:
        previous = Cluster(
            id="old", title="Agent loop crashes", signal_ids=["9"], status="rejected"
        )
        new = Cluster(id="new", title="agent loop crashes", signal_ids=["1", "2"])
        carry_over_state([new], [previous])
        self.assertEqual(new.status, "rejected")

    def test_unrelated_cluster_is_untouched(self) -> None:
        previous = Cluster(
            id="old", title="Docker build fails", signal_ids=["9"], status="approved"
        )
        new = Cluster(id="new", title="Calendar sync fails", signal_ids=["1"])
        carry_over_state([new], [previous])
        self.assertEqual(new.status, "clustered")

    def test_score_is_not_carried(self) -> None:
        previous = Cluster(id="old", title="T", signal_ids=["1"], status="approved")
        new = Cluster(id="new", title="T", signal_ids=["1"])
        carry_over_state([new], [previous])
        self.assertIsNone(new.score)


if __name__ == "__main__":
    unittest.main()
