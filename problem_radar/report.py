"""Report generation: a Markdown document and a JSON export.

The report is the product of the tool. It must be readable in five minutes,
link every claim to public evidence, and repeat what the score does not measure
— otherwise a number becomes a decision by accident.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .models import SOLUTION_LABELS, Cluster, Signal
from .store import atomic_write_text
from .text import clip, slug

#: Human labels for the recommendation values.
RECOMMENDATIONS: dict[str, str] = {
    "submit": "submit to validation",
    "research": "research further",
    "watch": "watch",
    "ignore": "ignore",
}

#: Human labels for the pipeline statuses.
STATUS_LABELS: dict[str, str] = {
    "discovered": "discovered",
    "clustered": "clustered",
    "researched": "researched",
    "proposed": "proposed",
    "approved": "approved",
    "rejected": "rejected",
    "built": "built",
    "deployed": "deployed",
}

LIMITS = """\
**What the score does not measure.** Mentions are not demand; the score says nothing about
willingness to pay, feasibility, solution cost, legal risk or strategic interest. An existing
solution is only accounted for when a human recorded a solution check. The recommendation is a
reading aid, never a decision: every cluster that matters must be validated by a person before a
project is created.
"""


def _escape_cell(text: str) -> str:
    """Make a string safe inside a Markdown table cell."""
    return clip(text, 120).replace("|", "\\|")


def _sources_of(cluster: Cluster, signals: dict[str, Signal]) -> list[str]:
    """Distinct source names of a cluster, sorted."""
    return sorted(
        {signals[signal_id].source for signal_id in cluster.signal_ids if signal_id in signals}
    )


def _members(cluster: Cluster, signals: dict[str, Signal]) -> list[Signal]:
    """Member signals in chronological order."""
    members = [signals[signal_id] for signal_id in cluster.signal_ids if signal_id in signals]
    return sorted(members, key=lambda item: (item.published_at or item.collected_at, item.title))


def _solution_block(cluster: Cluster) -> str:
    if not cluster.solutions:
        return (
            "**Solutions.** Not searched yet — this is the next human step "
            "(`radar solution <id> --status ...`)."
        )
    lines = ["**Solutions.**"]
    for solution in cluster.solutions:
        detail = f" — {solution.note}" if solution.note else ""
        link = f" {solution.url}" if solution.url else ""
        who = f" ({solution.checked_by}, {solution.checked_at})" if solution.checked_by else ""
        lines.append(f"- {solution.label}{detail}{link}{who}")
    return "\n".join(lines)


def render_cluster(
    cluster: Cluster,
    signals: dict[str, Signal],
    *,
    rank: int | None = None,
) -> str:
    """Render one cluster as a Markdown section."""
    score = cluster.score
    heading = f"{rank}. {cluster.title}" if rank is not None else cluster.title
    if score:
        heading = f"{heading} — {score.total:.1f}/100 ({RECOMMENDATIONS[score.recommendation]})"

    members = _members(cluster, signals)
    lines = [f"## {heading}", ""]

    meta = [
        f"status: **{STATUS_LABELS.get(cluster.status, cluster.status)}**",
        f"signals: **{len(cluster.signal_ids)}**",
        f"sources: {', '.join(_sources_of(cluster, signals)) or '—'}",
        f"domains: {', '.join(cluster.domains) or '—'}",
        f"categories: {', '.join(cluster.categories) or '—'}",
    ]
    if cluster.first_seen or cluster.last_seen:
        meta.append(f"seen: {cluster.first_seen or '?'} → {cluster.last_seen or '?'}")
    lines.append(" · ".join(meta))
    lines.append("")

    if cluster.statement:
        lines += ["**Problem.** " + clip(cluster.statement, 600), ""]

    if score:
        lines.append("**Why this score**")
        lines.append("")
        for component in score.explanation:
            lines.append(f"- {component}")
        if score.penalties:
            total_penalty = sum(score.penalties.values())
            lines.append(f"- penalties total: {total_penalty:+.1f}")
        lines.append("")

    lines.append(_solution_block(cluster))
    lines.append("")

    if cluster.note:
        lines += [f"**Note.** {clip(cluster.note, 400)}", ""]

    lines.append("**Evidence**")
    lines.append("")
    for signal in members:
        line = f"- [{clip(signal.title, 140)}]({signal.url}) — {signal.source}"
        details = [
            part for part in (signal.author and f"@{signal.author}", signal.published_at) if part
        ]
        if details:
            line += f", {' '.join(details)}"
        lines.append(line)
        if signal.evidence:
            lines.append(f"  > {clip(signal.evidence, 240)}")
    lines.append("")
    return "\n".join(lines)


def render_markdown(
    clusters: list[Cluster],
    signals: list[Signal],
    *,
    config: Config,
    top: int = 15,
    generated_at: str | None = None,
) -> str:
    """Render the full periodic report.

    Args:
        clusters: Scored clusters (already sorted by score).
        signals: Every known signal, used to resolve evidence.
        config: Configuration, for the source list in the header.
        top: Number of detailed clusters.
        generated_at: Timestamp override, for reproducible tests.
    """
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    by_id = {signal.id: signal for signal in signals}
    source_names = ", ".join(source.name for source in config.enabled_sources) or "(none)"
    total_members = sum(len(cluster.signal_ids) for cluster in clusters)

    lines = [
        f"# Problem Radar — {generated_at[:10]}",
        "",
        f"> Generated {generated_at} · **{len(signals)}** signals · "
        f"**{len(clusters)}** clusters · {total_members} attached signals",
        f"> Sources: {source_names}",
        "",
        "> The score is an input to a decision, never the decision itself.",
        "",
        "## Summary",
        "",
        "| # | Score | Recommendation | Signals | Domain | Problem |",
        "|---|-------|----------------|---------|--------|---------|",
    ]

    for rank, cluster in enumerate(clusters[:top], start=1):
        score = cluster.score.total if cluster.score else 0.0
        recommendation = RECOMMENDATIONS[cluster.score.recommendation] if cluster.score else "—"
        domain = cluster.domains[0] if cluster.domains else "—"
        lines.append(
            f"| {rank} | {score:.1f} | {recommendation} | {len(cluster.signal_ids)} | "
            f"{domain} | {_escape_cell(cluster.title)} |"
        )
    if not clusters:
        lines.append("| — | — | — | — | — | no cluster yet |")

    lines += ["", "## Opportunities", ""]
    if not clusters:
        lines += ["No cluster yet: run `radar collect` then `radar cluster`.", ""]
    for rank, cluster in enumerate(clusters[:top], start=1):
        lines.append(render_cluster(cluster, by_id, rank=rank))

    hidden = max(0, len(clusters) - top)
    if hidden:
        lines += [
            "### Not detailed in this report",
            "",
            f"{hidden} lower-scored cluster(s) are stored in `{config.clusters_path}`. "
            "Use `radar list` to see them.",
            "",
        ]

    lines += [
        "## How to read this report",
        "",
        "Each score is the sum of six observable components, minus solution penalties:",
        "",
        "- **volume** — independent signals describing the problem (logarithmic, saturates at 10);",
        "- **diversity** — how many different source families report it (saturates at 4);",
        "- **recency** — how recent the last signal is (90-day half-life);",
        "- **severity** — how painful the wording is (distinct pain words, saturates at 4);",
        "- **evidence** — how complete the evidence is (URL, author, date, quote);",
        "- **confidence** — the reliability of the source family.",
        "",
        LIMITS,
        "",
        "## Provenance",
        "",
        f"- Configuration: `{config.path}`",
        f"- Signals: `{config.signals_path}`",
        f"- Clusters: `{config.clusters_path}`",
        "- Tool: problem-radar, data collected from public APIs only.",
        "",
    ]
    return "\n".join(lines)


def write_report(
    clusters: list[Cluster],
    signals: list[Signal],
    *,
    config: Config,
    top: int = 15,
    output: Path | None = None,
    generated_at: str | None = None,
) -> Path:
    """Render and write the Markdown report, returning its path."""
    stamp = (generated_at or datetime.now(timezone.utc).date().isoformat())[:10]
    destination = output or (config.report_dir / f"{stamp}-problem-radar.md")
    content = render_markdown(clusters, signals, config=config, top=top, generated_at=generated_at)
    atomic_write_text(destination, content)
    return destination


def export_json(
    clusters: list[Cluster],
    signals: list[Signal],
    *,
    config: Config,
    output: Path,
) -> Path:
    """Export clusters and signals as one JSON document (dashboard, tests)."""
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "config": str(config.path),
        "counts": {"signals": len(signals), "clusters": len(clusters)},
        "clusters": [cluster.to_dict() for cluster in clusters],
        "signals": [signal.to_dict() for signal in signals],
    }
    atomic_write_text(output, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return output


def report_filename(cluster: Cluster) -> str:
    """Suggested Markdown file name for one cluster brief."""
    return f"{cluster.id}-{slug(cluster.title)}.md"


def solution_label(status: str) -> str:
    """Expose the solution labels for the CLI."""
    return SOLUTION_LABELS.get(status, status)
