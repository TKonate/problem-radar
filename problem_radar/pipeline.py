"""Pipeline: collect, store, cluster, score.

The pipeline is a handful of pure-ish steps, each of which can be run alone from
the CLI. That matters for a tool whose whole point is to be inspectable: you can
collect today, re-cluster tomorrow and re-score with other weights next week
without re-downloading anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .dedupe import ClusterOptions, cluster_signals
from .models import Cluster, Signal
from .scoring import score_clusters
from .sources import HttpClient, collect_source
from .store import append_signals, carry_over_state, load_clusters, load_signals, save_clusters


@dataclass
class SourceReport:
    """Result of one collector, for the CLI summary."""

    name: str
    signals: int = 0
    collected: int = 0
    filtered: int = 0
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class CollectSummary:
    """Aggregated outcome of a collection run."""

    sources: list[SourceReport] = field(default_factory=list)

    @property
    def total_added(self) -> int:
        """New signals stored during this run."""
        return sum(report.added for report in self.sources)

    @property
    def total_collected(self) -> int:
        """Items read from the sources."""
        return sum(report.collected for report in self.sources)

    @property
    def errors(self) -> list[str]:
        """Every reported error, prefixed by its source."""
        return [f"{report.name}: {message}" for report in self.sources for message in report.errors]


def collect(
    config: Config,
    *,
    client: HttpClient | None = None,
    only: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> CollectSummary:
    """Run the enabled collectors and store new signals.

    Args:
        config: Resolved configuration.
        client: Optional HTTP client (tests inject a fake transport).
        only: Run a single source by name.
        limit: Override the number of items requested per query/feed.
        dry_run: Do not write anything, only report what would be added.

    Returns:
        A :class:`CollectSummary` with one entry per source, failures included.
    """
    client = client or HttpClient()
    sources = [config.source(only)] if only else config.enabled_sources
    summary = CollectSummary()

    for source in sources:
        report = SourceReport(name=source.name)
        try:
            result = collect_source(
                source,
                client,
                base_dir=config.path.parent,
                limit=limit,
            )
        except Exception as exc:  # one broken source must not stop the others
            report.errors.append(str(exc))
            summary.sources.append(report)
            continue

        # The same item can appear twice in one batch (same article submitted
        # twice, two queries overlapping): keep the first occurrence.
        unique = {signal.id: signal for signal in result.signals}
        result.signals = list(unique.values())

        report.signals = len(result.signals)
        report.collected = result.collected
        report.filtered = result.filtered
        report.errors = list(result.errors)

        if dry_run:
            report.added = len(result.signals)
            report.skipped = 0
        else:
            report.added, report.skipped = append_signals(config.signals_path, result.signals)
        summary.sources.append(report)

    return summary


def rebuild_clusters(
    config: Config,
    *,
    signals: list[Signal] | None = None,
    options: ClusterOptions | None = None,
    save: bool = True,
) -> list[Cluster]:
    """Cluster every stored signal, carry human state over and score.

    Args:
        config: Resolved configuration.
        signals: Signals to use; the stored ones when omitted.
        options: Clustering threshold and cap; taken from the config by default.
        save: Write ``data/clusters.json``.

    Returns:
        Scored clusters, sorted by descending score.
    """
    signals = signals if signals is not None else load_signals(config.signals_path)
    previous = load_clusters(config.clusters_path)

    clusters = cluster_signals(
        signals,
        options
        or ClusterOptions(threshold=config.cluster_threshold, max_signals=config.max_signals),
    )
    carry_over_state(clusters, previous)
    score_clusters(clusters, signals, options=config.score)
    if save:
        save_clusters(config.clusters_path, clusters)
    return clusters


def load_or_rebuild(config: Config) -> list[Cluster]:
    """Load the stored clusters and re-score them, rebuilding when absent.

    The stored path re-scores with the current weights against the current
    signals but does not re-cluster or save anything: a read command must not
    rewrite ``clusters.json``. A full rebuild, which does save, is reserved for
    the case where no cluster is stored yet.
    """
    signals = load_signals(config.signals_path)
    stored = load_clusters(config.clusters_path)
    if stored:
        return score_clusters(stored, signals, options=config.score)
    return rebuild_clusters(config, signals=signals)
