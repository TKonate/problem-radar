"""Clustering: group signals that describe the same problem.

The algorithm is a greedy union-find over pairwise text similarity. It is
O(n²) by design: the MVP works on a few hundred signals per run, and an
explainable pairwise comparison is worth more than a faster opaque one. The
caller caps the input size (see ``pipeline.MAX_SIGNALS``).
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date

from .models import Cluster, Signal
from .text import clean_title, extract_problem, tokens


@dataclass
class ClusterOptions:
    """Clustering parameters.

    Attributes:
        threshold: Minimum similarity for two signals to be considered the same
            problem. 0.30 keeps near-duplicates together without merging every
            post that mentions "agent".
        max_signals: Safety cap; beyond it clustering is skipped.
    """

    threshold: float = 0.30
    max_signals: int = 2000


class _UnionFind:
    """Minimal union-find."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        root_first, root_second = self.find(first), self.find(second)
        if root_first != root_second:
            self.parent[root_second] = root_first


def token_weights(titles: list[str]) -> dict[str, float]:
    """Inverse document frequency of every token in the batch.

    Weighting tokens by rarity is what keeps "keeps crashing" from merging a
    plane crash with a software crash: common words still count, but they can no
    longer carry a pair over the threshold on their own.
    """
    counts: Counter[str] = Counter()
    for title in titles:
        counts.update(tokens(clean_title(title)))
    total = max(1, len(titles))
    return {token: math.log((1 + total) / (1 + count)) + 1.0 for token, count in counts.items()}


def weighted_similarity(first: str, second: str, weights: dict[str, float]) -> float:
    """IDF-weighted mix of Jaccard and containment."""
    first_tokens = tokens(clean_title(first))
    second_tokens = tokens(clean_title(second))
    if not first_tokens or not second_tokens:
        return 0.0

    def mass(items: set[str]) -> float:
        return sum(weights.get(token, 1.0) for token in items)

    union = first_tokens | second_tokens
    intersection = first_tokens & second_tokens
    if not intersection:
        return 0.0
    jaccard = mass(intersection) / mass(union)
    containment = mass(intersection) / min(mass(first_tokens), mass(second_tokens))
    return 0.6 * jaccard + 0.4 * containment


def _parse_date(value: str) -> str:
    """Return a sortable ISO date prefix, or an empty string."""
    if not value:
        return ""
    candidate = value[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return ""
    return candidate


def _representative(members: list[Signal]) -> Signal:
    """Pick the member whose title best represents the group.

    The most frequent normalised title wins; ties are broken by the shortest
    title, which is usually the least noisy one.
    """
    counter = Counter(fold_title(member.title) for member in members if member.title)
    if not counter:
        return members[0]
    best_title, _ = counter.most_common(1)[0]
    candidates = [member for member in members if fold_title(member.title) == best_title]
    return min(candidates, key=lambda member: len(member.title))


def fold_title(title: str) -> str:
    """Normalised title used as a grouping key."""
    return " ".join(sorted(tokens(clean_title(title))))


def cluster_id(members: list[Signal]) -> str:
    """Deterministic id for a group of signals."""
    joined = "|".join(sorted(member.id for member in members))
    return hashlib.sha256(joined.encode()).hexdigest()[:10]


def build_cluster(members: list[Signal], *, status: str = "clustered") -> Cluster:
    """Build a :class:`Cluster` from a non-empty list of signals."""
    if not members:
        raise ValueError("cannot build a cluster from zero signals")

    ordered = sorted(
        members, key=lambda member: (member.published_at or member.collected_at, member.id)
    )
    representative = _representative(ordered)
    problem, evidence = extract_problem(representative.title, representative.body)

    dates = [
        parsed for parsed in (_parse_date(member.published_at) for member in ordered) if parsed
    ]
    domains = sorted({member.domain for member in ordered})
    categories = sorted({member.category for member in ordered})

    statement = problem or representative.title
    if evidence and evidence not in statement:
        statement = f"{statement} — {evidence}"

    return Cluster(
        id=cluster_id(ordered),
        title=clean_title(representative.title) or representative.title,
        statement=statement,
        signal_ids=[member.id for member in ordered],
        domains=domains,
        categories=categories,
        first_seen=dates[0] if dates else "",
        last_seen=dates[-1] if dates else "",
        status=status,
    )


def cluster_signals(signals: list[Signal], options: ClusterOptions | None = None) -> list[Cluster]:
    """Group ``signals`` into clusters.

    Args:
        signals: Signals to group, in any order.
        options: Threshold and safety cap.

    Returns:
        Clusters sorted by descending member count, then by title.

    Raises:
        ValueError: When the input exceeds ``max_signals``.
    """
    options = options or ClusterOptions()
    if len(signals) > options.max_signals:
        raise ValueError(
            f"{len(signals)} signals is above the clustering cap "
            f"({options.max_signals}); narrow the collection window"
        )
    if not signals:
        return []

    weights = token_weights([signal.title for signal in signals])
    union = _UnionFind(len(signals))
    for left in range(len(signals)):
        for right in range(left + 1, len(signals)):
            score = weighted_similarity(signals[left].title, signals[right].title, weights)
            if score >= options.threshold:
                union.union(left, right)

    groups: dict[int, list[Signal]] = {}
    for index, signal in enumerate(signals):
        groups.setdefault(union.find(index), []).append(signal)

    clusters = [build_cluster(members) for members in groups.values()]
    clusters.sort(key=lambda item: (-len(item.signal_ids), item.title.lower()))
    return clusters
