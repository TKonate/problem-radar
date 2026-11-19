"""Configuration: sources, queries, weights and storage paths.

The configuration is a single JSON file, versioned with the repository so a run
is reproducible. It contains no secret: the optional GitHub token is read from
the environment by the collector, never stored here. Loading validates the shape
once and fails with a message saying how to create a new file; it never reads
the environment and never migrates an older format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .scoring import DEFAULT_THRESHOLDS, DEFAULT_WEIGHTS, ScoreOptions
from .taxonomy import DOMAINS

#: Collector kinds the code knows how to run.
SOURCE_KINDS: tuple[str, ...] = ("hackernews", "github", "rss", "manual")

#: Usable configuration, written by ``radar init``.
DEFAULT_CONFIG: dict[str, Any] = {
    "storage": {"data_dir": "../data"},
    "cluster": {"threshold": 0.30, "max_signals": 2000},
    "report": {"top": 15, "output_dir": "../reports"},
    "sources": [
        {
            "name": "hackernews",
            "kind": "hackernews",
            "tier": "social",
            "enabled": True,
            "limit": 30,
            "queries": [
                "AI agent",
                "LLM tool",
                "developer tool",
            ],
        },
        {
            "name": "github",
            "kind": "github",
            "tier": "issue-tracker",
            "enabled": True,
            "limit": 30,
            "queries": [
                'is:issue state:open label:"bug" llm in:title',
                'is:issue state:open label:"enhancement" agent in:title',
            ],
        },
        {
            "name": "rss",
            "kind": "rss",
            "tier": "blog",
            "enabled": False,
            "limit": 20,
            "feeds": ["https://simonwillison.net/atom/everything/"],
        },
        {
            "name": "manual",
            "kind": "manual",
            "tier": "unknown",
            "enabled": True,
            "path": "../data/manual-signals.jsonl",
        },
    ],
}


@dataclass
class SourceConfig:
    """One collector configuration."""

    name: str
    kind: str
    tier: str = "unknown"
    enabled: bool = True
    limit: int = 25
    queries: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    path: str = ""

    def __post_init__(self) -> None:
        if self.kind not in SOURCE_KINDS:
            raise ConfigError(
                f"unknown source kind: {self.kind!r} (expected {', '.join(SOURCE_KINDS)})"
            )
        if self.limit <= 0:
            raise ConfigError(f"source {self.name!r}: limit must be positive")
        if self.kind in {"hackernews", "github"} and not self.queries:
            raise ConfigError(f"source {self.name!r}: at least one query is required")
        if self.kind == "rss" and not self.feeds:
            raise ConfigError(f"source {self.name!r}: at least one feed is required")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SourceConfig:
        """Build from the JSON object, rejecting unknown kinds."""
        return cls(
            name=str(payload["name"]),
            kind=str(payload["kind"]),
            tier=str(payload.get("tier", "unknown")),
            enabled=bool(payload.get("enabled", True)),
            limit=int(payload.get("limit", 25)),
            queries=[str(item) for item in payload.get("queries", [])],
            feeds=[str(item) for item in payload.get("feeds", [])],
            path=str(payload.get("path", "")),
        )


@dataclass
class Config:
    """Resolved configuration with absolute paths."""

    path: Path
    data_dir: Path
    sources: list[SourceConfig]
    score: ScoreOptions
    cluster_threshold: float = 0.30
    max_signals: int = 2000
    report_top: int = 15
    report_dir: Path = Path("reports")

    @property
    def signals_path(self) -> Path:
        """JSONL file holding every collected signal."""
        return self.data_dir / "signals.jsonl"

    @property
    def clusters_path(self) -> Path:
        """JSON file holding clusters, scores and human state."""
        return self.data_dir / "clusters.json"

    @property
    def enabled_sources(self) -> list[SourceConfig]:
        """Sources that are enabled."""
        return [source for source in self.sources if source.enabled]

    def source(self, name: str) -> SourceConfig:
        """Return one source by name."""
        for source in self.sources:
            if source.name == name:
                return source
        known = ", ".join(source.name for source in self.sources) or "(none)"
        raise ConfigError(f"unknown source: {name!r} (configured: {known})")

    def ensure_directories(self) -> None:
        """Create the data and report directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)


def _parse_score_options(raw: dict[str, Any]) -> ScoreOptions:
    """Read the optional ``scoring`` section, keeping the defaults for absent keys.

    A weight or threshold name that the scorer does not use is accepted and
    ignored, so a typo here produces no error and no effect.
    """
    scoring = raw.get("scoring", {})
    if not isinstance(scoring, dict):
        raise ConfigError("scoring must be an object")
    weights = dict(DEFAULT_WEIGHTS)
    thresholds = dict(DEFAULT_THRESHOLDS)
    weights.update({str(key): float(value) for key, value in scoring.get("weights", {}).items()})
    thresholds.update(
        {str(key): float(value) for key, value in scoring.get("thresholds", {}).items()}
    )
    return ScoreOptions(weights=weights, thresholds=thresholds)


def load_config(path: str | Path = "config/radar.json") -> Config:
    """Load and validate the configuration.

    Relative paths are resolved from the configuration file's directory, so the
    tool behaves identically whatever the current working directory is.

    Raises:
        ConfigError: When the file is missing, malformed or inconsistent.
    """
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise ConfigError(
            f"configuration not found: {config_path}\ncreate one with: radar init <directory>"
        )

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{config_path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path} must contain a JSON object")

    base = config_path.resolve().parent
    storage = raw.get("storage", {})
    data_dir = Path(str(storage.get("data_dir", "../data")))
    if not data_dir.is_absolute():
        data_dir = base / data_dir

    cluster = raw.get("cluster", {})
    threshold = float(cluster.get("threshold", 0.30))
    if not 0.0 < threshold <= 1.0:
        raise ConfigError("cluster.threshold must be in (0, 1]")

    report = raw.get("report", {})
    report_dir = Path(str(report.get("output_dir", "../reports")))
    if not report_dir.is_absolute():
        report_dir = base / report_dir

    sources_raw = raw.get("sources", [])
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ConfigError("config.sources must be a non-empty list")
    sources = [SourceConfig.from_dict(item) for item in sources_raw]

    return Config(
        path=config_path.resolve(),
        data_dir=data_dir.resolve(),
        sources=sources,
        score=_parse_score_options(raw),
        cluster_threshold=threshold,
        max_signals=int(cluster.get("max_signals", 2000)),
        report_top=int(report.get("top", 15)),
        report_dir=report_dir.resolve(),
    )


def write_default_config(directory: str | Path) -> Path:
    """Write a ready-to-run ``config/radar.json`` and return its path."""
    target = Path(directory).expanduser().resolve()
    config_dir = target / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "radar.json"
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    return path


def validate_domains(candidates: list[str]) -> list[str]:
    """Return ``candidates`` without the names that are not in ``DOMAINS``."""
    return [candidate for candidate in candidates if candidate in DOMAINS]
