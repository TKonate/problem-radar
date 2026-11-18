"""Tests for :mod:`problem_radar.config`."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from problem_radar.config import (
    DEFAULT_CONFIG,
    Config,
    SourceConfig,
    load_config,
    validate_domains,
    write_default_config,
)
from problem_radar.errors import ConfigError


class SourceConfigTests(unittest.TestCase):
    def test_valid_source(self) -> None:
        source = SourceConfig(name="hn", kind="hackernews", tier="social", queries=["ai"])
        self.assertEqual(source.limit, 25)

    def test_unknown_kind(self) -> None:
        with self.assertRaises(ConfigError):
            SourceConfig(name="x", kind="telegram")

    def test_queries_required_for_search_sources(self) -> None:
        with self.assertRaises(ConfigError):
            SourceConfig(name="hn", kind="hackernews")
        with self.assertRaises(ConfigError):
            SourceConfig(name="gh", kind="github")

    def test_feeds_required_for_rss(self) -> None:
        with self.assertRaises(ConfigError):
            SourceConfig(name="rss", kind="rss")

    def test_limit_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            SourceConfig(name="hn", kind="hackernews", queries=["ai"], limit=0)


class LoadConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.directory = Path(self.temp.name)
        (self.directory / "config").mkdir()
        (self.directory / "data").mkdir()
        self.config_path = self.directory / "config" / "radar.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, payload: object) -> Path:
        self.config_path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
        )
        return self.config_path

    def minimal(self) -> dict[str, object]:
        return {
            "storage": {"data_dir": "../data"},
            "sources": [{"name": "hn", "kind": "hackernews", "queries": ["ai"]}],
        }

    def test_minimal_config(self) -> None:
        config = load_config(self.write(self.minimal()))
        self.assertEqual(config.data_dir, (self.directory / "data").resolve())
        self.assertEqual(config.report_dir, (self.directory / "reports").resolve())
        self.assertEqual(config.cluster_threshold, 0.30)
        self.assertEqual(config.max_signals, 2000)
        self.assertEqual(config.report_top, 15)
        self.assertEqual(len(config.sources), 1)

    def test_missing_file(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.directory / "missing.json")

    def test_invalid_json(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write("{not json"))

    def test_non_object(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write([]))

    def test_sources_required(self) -> None:
        payload = self.minimal()
        payload["sources"] = []
        with self.assertRaises(ConfigError):
            load_config(self.write(payload))

    def test_bad_threshold(self) -> None:
        for threshold in (0, -1, 2):
            payload = self.minimal()
            payload["cluster"] = {"threshold": threshold}
            with self.subTest(threshold=threshold), self.assertRaises(ConfigError):
                load_config(self.write(payload))

    def test_weights_merge_with_defaults(self) -> None:
        payload = self.minimal()
        payload["scoring"] = {"weights": {"volume": 5}}
        config = load_config(self.write(payload))
        self.assertEqual(config.score.weights["volume"], 5.0)
        self.assertIn("diversity", config.score.weights)

    def test_thresholds_override(self) -> None:
        payload = self.minimal()
        payload["scoring"] = {"thresholds": {"submit": 10, "research": 5, "watch": 1}}
        config = load_config(self.write(payload))
        self.assertEqual(config.score.thresholds["submit"], 10.0)

    def test_enabled_sources_and_lookup(self) -> None:
        payload = self.minimal()
        payload["sources"] = [
            {"name": "hn", "kind": "hackernews", "queries": ["ai"], "enabled": True},
            {"name": "gh", "kind": "github", "queries": ["x"], "enabled": False},
        ]
        config = load_config(self.write(payload))
        self.assertEqual([source.name for source in config.enabled_sources], ["hn"])
        self.assertEqual(config.source("gh").name, "gh")
        with self.assertRaises(ConfigError):
            config.source("nope")

    def test_ensure_directories(self) -> None:
        config = load_config(self.write(self.minimal()))
        config.ensure_directories()
        self.assertTrue(config.data_dir.is_dir())
        self.assertTrue(config.report_dir.is_dir())


class DefaultConfigTests(unittest.TestCase):
    def test_write_and_reload(self) -> None:
        with TemporaryDirectory() as temp:
            path = write_default_config(temp)
            self.assertTrue(path.is_file())
            config = load_config(path)
            self.assertEqual(config.data_dir, (Path(temp) / "data").resolve())
            self.assertEqual(config.report_dir, (Path(temp) / "reports").resolve())
            self.assertEqual(len(config.sources), len(DEFAULT_CONFIG["sources"]))

    def test_domains_filter(self) -> None:
        self.assertEqual(validate_domains(["ai-agents", "nope"]), ["ai-agents"])


class ConfigObjectTests(unittest.TestCase):
    def test_properties(self) -> None:
        config = Config(
            path=Path("c/radar.json"),
            data_dir=Path("c/data"),
            sources=[SourceConfig(name="hn", kind="hackernews", queries=["ai"])],
            score=None,  # type: ignore[arg-type]
        )
        self.assertEqual(config.signals_path, Path("c/data/signals.jsonl"))
        self.assertEqual(config.clusters_path, Path("c/data/clusters.json"))


if __name__ == "__main__":
    unittest.main()
