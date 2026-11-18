"""Explainable opportunity scoring.

The score answers one question: *is this problem worth a human hour?* It is a
weighted sum of observable facts, each reported separately so a reader can
disagree with one component without rejecting the whole number.

What the score does **not** measure (documented in ``docs/methodology.md`` and
repeated in every report):

* market demand — mentions are not willingness to pay;
* feasibility or cost of a solution;
* absence of an existing solution (that is a separate, human research step);
* strategic interest for the person reading the report.

It is an input to a decision, never the decision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from .models import Cluster, Score, Signal
from .text import severity_hits

#: Default weights, summing to 100 points before penalties.
DEFAULT_WEIGHTS: dict[str, float] = {
    "volume": 25.0,  # how many independent signals
    "diversity": 20.0,  # how many different sources
    "recency": 15.0,  # how recent the last signal is
    "severity": 15.0,  # how painful the wording is
    "evidence": 10.0,  # how complete the evidence is
    "confidence": 15.0,  # how reliable the source family is
}

#: Penalty applied per solution finding, in points.
SOLUTION_PENALTIES: dict[str, float] = {
    "exists": -30.0,
    "poorly_documented": -8.0,
    "inaccessible": 0.0,
    "none_found": 0.0,
    "unknown": 0.0,
}

#: Default recommendation thresholds (score is out of 100).
DEFAULT_THRESHOLDS: dict[str, float] = {
    "submit": 65.0,
    "research": 45.0,
    "watch": 30.0,
}

#: Volume is normalised against this many signals: ten independent reports is
#: already a strong signal for this kind of radar.
_VOLUME_REFERENCE = 10.0

#: Recency half-life in days: a six-month-old problem is worth half as much.
_RECENCY_HALF_LIFE_DAYS = 90.0

#: Severity saturates at this many distinct severity words.
_SEVERITY_SATURATION = 4.0

#: Corroboration factor applied to the final score, by number of signals.
#: A single well-formed bug report reaches ~65/100 on recency and severity alone;
#: without this factor, unconfirmed reports would outrank corroborated problems.
#: A multiplier (not a flat cap) keeps singletons comparable: a severe, recent,
#: well-documented single report still ranks above a vague one.
_CORROBORATION: dict[int, float] = {1: 0.55, 2: 0.75, 3: 0.90}
_CORROBORATION_FULL = 1.0


def _parse_date(value: str) -> date | None:
    """Parse an ISO date or datetime, returning ``None`` when unusable."""
    if not value:
        return None
    candidate = value[:10]
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        return None


def _reference_date(now: str | date | None) -> date:
    if isinstance(now, date):
        return now
    if isinstance(now, str):
        parsed = _parse_date(now)
        if parsed:
            return parsed
    return datetime.now(timezone.utc).date()


@dataclass
class ScoreOptions:
    """Weights and thresholds, usually loaded from ``config.json``."""

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    thresholds: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))

    def recommendation(self, total: float) -> str:
        """Map a score to a recommendation label."""
        if total >= self.thresholds["submit"]:
            return "submit"
        if total >= self.thresholds["research"]:
            return "research"
        if total >= self.thresholds["watch"]:
            return "watch"
        return "ignore"


def _evidence_completeness(signal: Signal) -> float:
    """Share of the evidence fields that are filled in."""
    points = 0.0
    points += 0.40 if signal.url else 0.0
    points += 0.20 if signal.author else 0.0
    points += 0.20 if _parse_date(signal.published_at) else 0.0
    points += 0.20 if signal.evidence else 0.0
    return points


def score_cluster(
    cluster: Cluster,
    signals: list[Signal],
    *,
    options: ScoreOptions | None = None,
    now: str | date | None = None,
) -> Score:
    """Score one cluster from its member signals.

    Args:
        cluster: Cluster to score (``signal_ids`` selects the members).
        signals: Every known signal; the function picks the cluster members.
        options: Weights and thresholds.
        now: Reference date, injectable for deterministic tests.

    Returns:
        A :class:`Score` with every component and one explanation line each.
    """
    options = options or ScoreOptions()
    by_id = {signal.id: signal for signal in signals}
    members = [by_id[signal_id] for signal_id in cluster.signal_ids if signal_id in by_id]
    if not members:
        return Score(
            total=0.0, explanation=["no signal attached to this cluster"], recommendation="ignore"
        )

    reference = _reference_date(now)
    components: dict[str, float] = {}
    penalties: dict[str, float] = {}
    explanation: list[str] = []

    # Volume: logarithmic so 50 mentions do not linearly crush everything else.
    volume_ratio = min(1.0, math.log2(1 + len(members)) / math.log2(1 + _VOLUME_REFERENCE))
    components["volume"] = volume_ratio * options.weights["volume"]
    explanation.append(
        f"volume: {len(members)} signal(s), saturating at {int(_VOLUME_REFERENCE)} "
        f"→ {components['volume']:.1f}/{options.weights['volume']:.0f}"
    )

    # Diversity: four distinct sources is the maximum useful spread here.
    sources = {signal.source for signal in members}
    diversity_ratio = min(1.0, len(sources) / 4)
    components["diversity"] = diversity_ratio * options.weights["diversity"]
    explanation.append(
        f"diversity: {len(sources)} distinct source(s) ({', '.join(sorted(sources))}) "
        f"→ {components['diversity']:.1f}/{options.weights['diversity']:.0f}"
    )

    # Recency: exponential decay from the most recent member.
    dates = [
        parsed for parsed in (_parse_date(signal.published_at) for signal in members) if parsed
    ]
    if dates:
        age_days = max(0, (reference - max(dates)).days)
        recency_ratio = 0.5 ** (age_days / _RECENCY_HALF_LIFE_DAYS)
        explanation.append(
            f"recency: last signal {age_days} day(s) old, half-life "
            f"{int(_RECENCY_HALF_LIFE_DAYS)} days → {recency_ratio:.2f}"
        )
    else:
        age_days = None
        recency_ratio = 0.5
        explanation.append("recency: no usable publication date, neutral 0.50")
    components["recency"] = recency_ratio * options.weights["recency"]

    # Severity: distinct pain words, saturating quickly to avoid keyword stuffing.
    hits: set[str] = set()
    for signal in members:
        hits |= severity_hits(f"{signal.title} {signal.body}")
    severity_ratio = min(1.0, len(hits) / _SEVERITY_SATURATION)
    components["severity"] = severity_ratio * options.weights["severity"]
    explanation.append(
        f"severity: {len(hits)} distinct pain word(s) "
        f"({', '.join(sorted(hits)) or 'none'}) → {components['severity']:.1f}"
        f"/{options.weights['severity']:.0f}"
    )

    # Evidence: average completeness, so one empty signal does not hide behind others.
    completeness = sum(_evidence_completeness(signal) for signal in members) / len(members)
    components["evidence"] = completeness * options.weights["evidence"]
    explanation.append(
        f"evidence: {completeness:.0%} of fields filled (url, author, date, quote) "
        f"→ {components['evidence']:.1f}/{options.weights['evidence']:.0f}"
    )

    # Confidence: reliability of the source families.
    mean_confidence = sum(signal.confidence for signal in members) / len(members)
    components["confidence"] = mean_confidence * options.weights["confidence"]
    explanation.append(
        f"confidence: mean source confidence {mean_confidence:.2f} "
        f"→ {components['confidence']:.1f}/{options.weights['confidence']:.0f}"
    )

    # Solution penalty: an existing, adopted solution is the strongest reason not to build.
    for solution in cluster.solutions:
        penalty = SOLUTION_PENALTIES.get(solution.status, 0.0)
        if penalty:
            key = f"solution_{solution.status}"
            penalties[key] = penalties.get(key, 0.0) + penalty
            explanation.append(
                f"penalty: {solution.label} ({solution.url or 'no link'}) → {penalty:+.0f}"
            )

    corroboration = _CORROBORATION.get(len(members), _CORROBORATION_FULL)
    subtotal = sum(components.values()) + sum(penalties.values())
    total = subtotal * corroboration
    explanation.append(
        f"corroboration: {len(members)} signal(s) → ×{corroboration:.2f} "
        f"({subtotal:.1f} → {total:.1f})"
    )
    total = max(0.0, min(100.0, total))

    return Score(
        total=total,
        components=components,
        penalties=penalties,
        explanation=explanation,
        recommendation=options.recommendation(total),
    )


def score_clusters(
    clusters: list[Cluster],
    signals: list[Signal],
    *,
    options: ScoreOptions | None = None,
    now: str | date | None = None,
) -> list[Cluster]:
    """Score every cluster in place and return them sorted by score."""
    for cluster in clusters:
        cluster.score = score_cluster(cluster, signals, options=options, now=now)
    clusters.sort(key=lambda item: (-(item.score.total if item.score else 0.0), item.title.lower()))
    return clusters
