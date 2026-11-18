"""Shared test helpers: fake transport, temporary project, CLI runner."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from problem_radar.cli import main
from problem_radar.config import Config, SourceConfig, load_config
from problem_radar.scoring import ScoreOptions
from problem_radar.sources import HttpResponse

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class FakeTransport:
    """Transport that serves fixtures instead of network responses.

    ``routes`` maps a URL fragment to either ``(status, body)`` or a fixture file
    name. Unknown URLs answer 404, which is what a real server would do.
    """

    def __init__(self, routes: dict[str, tuple[int, str] | str]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        self.calls.append((url, dict(headers)))
        for fragment, target in self.routes.items():
            if fragment in url:
                if isinstance(target, tuple):
                    status, body = target
                elif target.startswith("file:"):
                    status, body = 200, (FIXTURES / target[5:]).read_text(encoding="utf-8")
                else:
                    status, body = 200, target
                return HttpResponse(status=status, body=body, url=url)
        return HttpResponse(status=404, body="", url=url)


@dataclass
class Sandbox:
    """Temporary project directory with a usable configuration."""

    directory: Path
    config_path: Path
    config: Config
    extra: dict[str, Any] = field(default_factory=dict)


def make_sandbox(
    *, sources: list[SourceConfig] | None = None
) -> tuple[TemporaryDirectory[str], Sandbox]:
    """Create a temporary project with ``config/radar.json`` and ``data/``."""
    temp = TemporaryDirectory()
    directory = Path(temp.name)
    (directory / "config").mkdir()
    (directory / "data").mkdir()
    config_path = directory / "config" / "radar.json"

    payload = {
        "storage": {"data_dir": "../data"},
        "cluster": {"threshold": 0.30, "max_signals": 500},
        "report": {"top": 10, "output_dir": "../reports"},
        "sources": [
            {
                "name": "hackernews",
                "kind": "hackernews",
                "tier": "social",
                "enabled": True,
                "limit": 5,
                "queries": ["AI agent"],
            },
            {
                "name": "github",
                "kind": "github",
                "tier": "issue-tracker",
                "enabled": True,
                "limit": 5,
                "queries": ["llm in:title"],
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
    if sources is not None:
        payload["sources"] = [
            {
                "name": source.name,
                "kind": source.kind,
                "tier": source.tier,
                "enabled": source.enabled,
                "limit": source.limit,
                "queries": source.queries,
                "feeds": source.feeds,
                "path": source.path,
            }
            for source in sources
        ]
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (directory / "data" / "manual-signals.jsonl").write_text("", encoding="utf-8")
    config = load_config(config_path)
    return temp, Sandbox(directory=directory, config_path=config_path, config=config)


def make_config(directory: Path, sources: list[SourceConfig] | None = None) -> Config:
    """Build a configuration object without touching disk."""
    return Config(
        path=directory / "config" / "radar.json",
        data_dir=directory / "data",
        sources=sources
        or [
            SourceConfig(
                name="hackernews",
                kind="hackernews",
                tier="social",
                queries=["AI agent"],
                limit=5,
            )
        ],
        score=ScoreOptions(),
        cluster_threshold=0.30,
        max_signals=500,
        report_top=10,
        report_dir=directory / "reports",
    )


def run_cli(args: list[str], config_path: Path) -> tuple[int, str, str]:
    """Run the CLI in-process and capture ``(code, stdout, stderr)``."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["-c", str(config_path), *args])
    return code, stdout.getvalue(), stderr.getvalue()


def run_cli_raw(args: list[str]) -> tuple[int, str, str]:
    """Run the CLI without prepending a configuration path."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()
