"""Data model: signals, clusters, solutions and pipeline states.

A *signal* is one observable fact collected from a public source (an issue, a
forum thread, a blog post). A *cluster* groups signals that describe the same
underlying problem. A *solution check* records what was found when looking for
an existing answer. Nothing here decides anything: the score explains, the
human decides.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

#: Pipeline states, in order. ``rejected`` and ``approved`` are terminal for the
#: automatic pipeline; anything after ``approved`` is human work.
PIPELINE_STATUSES: tuple[str, ...] = (
    "discovered",
    "clustered",
    "researched",
    "proposed",
    "approved",
    "rejected",
    "built",
    "deployed",
)

#: What a solution search concluded.
SOLUTION_STATUSES: tuple[str, ...] = (
    "unknown",
    "none_found",
    "exists",
    "inaccessible",
    "poorly_documented",
)

#: Human readable labels for the report.
SOLUTION_LABELS: dict[str, str] = {
    "unknown": "not searched yet",
    "none_found": "no solution found",
    "exists": "solution exists and covers the need",
    "inaccessible": "solution exists but is inaccessible (price, licence, closed beta)",
    "poorly_documented": "solution exists but is poorly documented or hard to adopt",
}


def utc_now() -> str:
    """Current UTC timestamp, second precision, ISO 8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    """Current UTC date, ISO 8601."""
    return date.today().isoformat()


@dataclass
class Signal:
    """One collected observation.

    Attributes:
        source: Source name (``hackernews``, ``github``, ``rss``, ``manual``).
        source_id: Identifier inside that source (issue number, objectID, URL).
        url: Public URL of the evidence.
        title: Raw title as published.
        body: Raw body/excerpt, truncated by the collector.
        author: Public author handle when available.
        published_at: Publication date (ISO 8601 date or datetime) when available.
        domain: Taxonomy domain inferred or supplied.
        category: Taxonomy category inferred or supplied.
        problem: One sentence describing the problem, extracted from the title.
        evidence: Short quote supporting the problem statement.
        confidence: 0..1, how much the signal can be trusted as evidence.
        tags: Free labels (source labels, keywords).
        collected_at: When the collector stored it.
    """

    source: str
    source_id: str
    url: str
    title: str
    body: str = ""
    author: str = ""
    published_at: str = ""
    domain: str = "other"
    category: str = "other"
    problem: str = ""
    evidence: str = ""
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    collected_at: str = field(default_factory=utc_now)

    @property
    def id(self) -> str:
        """Stable identifier derived from the source and its own id."""
        digest = hashlib.sha256(f"{self.source}:{self.source_id}".encode()).hexdigest()
        return digest[:16]

    def to_dict(self) -> dict[str, Any]:
        """Serialise for JSONL storage."""
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "published_at": self.published_at,
            "domain": self.domain,
            "category": self.category,
            "problem": self.problem,
            "evidence": self.evidence,
            "confidence": round(float(self.confidence), 3),
            "tags": list(self.tags),
            "collected_at": self.collected_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Signal:
        """Rebuild a signal from its stored form, ignoring unknown keys."""
        return cls(
            source=str(payload["source"]),
            source_id=str(payload["source_id"]),
            url=str(payload.get("url", "")),
            title=str(payload.get("title", "")),
            body=str(payload.get("body", "")),
            author=str(payload.get("author", "")),
            published_at=str(payload.get("published_at", "")),
            domain=str(payload.get("domain", "other")),
            category=str(payload.get("category", "other")),
            problem=str(payload.get("problem", "")),
            evidence=str(payload.get("evidence", "")),
            confidence=float(payload.get("confidence", 0.5)),
            tags=[str(tag) for tag in payload.get("tags", [])],
            collected_at=str(payload.get("collected_at", utc_now())),
        )


@dataclass
class Solution:
    """Result of looking for an existing solution.

    Attributes:
        status: One of :data:`SOLUTION_STATUSES`.
        url: Best link found, if any.
        note: One line of justification.
        checked_at: When the search was done.
        checked_by: Profile or person who did it (``palantir``, ``human``...).
    """

    status: str = "unknown"
    url: str = ""
    note: str = ""
    checked_at: str = ""
    checked_by: str = ""

    def __post_init__(self) -> None:
        if self.status not in SOLUTION_STATUSES:
            raise ValueError(f"unknown solution status: {self.status!r}")

    @property
    def label(self) -> str:
        """Human readable status."""
        return SOLUTION_LABELS[self.status]

    def to_dict(self) -> dict[str, str]:
        """Serialise for storage."""
        return {
            "status": self.status,
            "url": self.url,
            "note": self.note,
            "checked_at": self.checked_at,
            "checked_by": self.checked_by,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Solution:
        """Rebuild a solution record."""
        return cls(
            status=str(payload.get("status", "unknown")),
            url=str(payload.get("url", "")),
            note=str(payload.get("note", "")),
            checked_at=str(payload.get("checked_at", "")),
            checked_by=str(payload.get("checked_by", "")),
        )


@dataclass
class Score:
    """Explainable opportunity score.

    Attributes:
        total: 0..100.
        components: Each positive contribution, by name, in points.
        penalties: Each negative contribution, by name, in points (negative).
        explanation: One human sentence per component.
        recommendation: ``ignore``, ``watch``, ``research`` or ``submit``.
    """

    total: float = 0.0
    components: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    explanation: list[str] = field(default_factory=list)
    recommendation: str = "ignore"

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage and the report."""
        return {
            "total": round(self.total, 1),
            "components": {key: round(value, 1) for key, value in self.components.items()},
            "penalties": {key: round(value, 1) for key, value in self.penalties.items()},
            "explanation": list(self.explanation),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Score:
        """Rebuild a score."""
        return cls(
            total=float(payload.get("total", 0.0)),
            components={str(k): float(v) for k, v in payload.get("components", {}).items()},
            penalties={str(k): float(v) for k, v in payload.get("penalties", {}).items()},
            explanation=[str(item) for item in payload.get("explanation", [])],
            recommendation=str(payload.get("recommendation", "ignore")),
        )


@dataclass
class Cluster:
    """A group of signals describing the same problem.

    Attributes:
        id: Stable identifier (first eight hex chars of the member hash).
        title: Representative title, the shortest clear member title.
        statement: Problem statement (one sentence).
        signal_ids: Member signal ids, in collection order.
        domains: Domains observed in the members.
        categories: Categories observed in the members.
        first_seen: Oldest member date (ISO), falls back to collection date.
        last_seen: Newest member date (ISO).
        score: Computed score, ``None`` before scoring.
        solutions: Solution searches, usually filled by a research pass.
        status: Pipeline status.
        note: Free note, kept when the human reviews the cluster.
    """

    id: str
    title: str
    statement: str = ""
    signal_ids: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    score: Score | None = None
    solutions: list[Solution] = field(default_factory=list)
    status: str = "clustered"
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in PIPELINE_STATUSES:
            raise ValueError(f"unknown pipeline status: {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage and the report."""
        return {
            "id": self.id,
            "title": self.title,
            "statement": self.statement,
            "signal_ids": list(self.signal_ids),
            "domains": list(self.domains),
            "categories": list(self.categories),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "score": self.score.to_dict() if self.score else None,
            "solutions": [solution.to_dict() for solution in self.solutions],
            "status": self.status,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Cluster:
        """Rebuild a cluster from its stored form."""
        score = payload.get("score")
        return cls(
            id=str(payload["id"]),
            title=str(payload.get("title", "")),
            statement=str(payload.get("statement", "")),
            signal_ids=[str(item) for item in payload.get("signal_ids", [])],
            domains=[str(item) for item in payload.get("domains", [])],
            categories=[str(item) for item in payload.get("categories", [])],
            first_seen=str(payload.get("first_seen", "")),
            last_seen=str(payload.get("last_seen", "")),
            score=Score.from_dict(score) if isinstance(score, dict) else None,
            solutions=[Solution.from_dict(item) for item in payload.get("solutions", [])],
            status=str(payload.get("status", "clustered")),
            note=str(payload.get("note", "")),
        )
