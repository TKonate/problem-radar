"""Storage: append-only signals, clusters and human state.

Two files, both plain text, both readable with ``cat``:

* ``data/signals.jsonl``: one signal per line, append-only, deduplicated by
  ``(source, source_id)``;
* ``data/clusters.json``: clusters with their score, solution checks, pipeline
  status and note.

Re-clustering changes cluster ids (the id derives from the members). Human work
must survive that, so :func:`carry_over_state` transfers status, note and
solution checks from the previous clusters to the new ones by signal overlap.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import StorageError
from .models import Cluster, Signal


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temporary file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".radar-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def load_signals(path: Path) -> list[Signal]:
    """Read the JSONL signal file.

    A malformed line is reported with its number: silently dropping it would
    hide a corrupted collection run.
    """
    if not path.is_file():
        return []
    signals: list[Signal] = []
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                signals.append(Signal.from_dict(payload))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"{path}:{number}: invalid signal line ({exc})") from exc
    return signals


def append_signals(path: Path, signals: list[Signal]) -> tuple[int, int]:
    """Append new signals, skipping duplicates.

    Duplicates are detected against the whole file, which is read once. The
    file is append-only and the JSONL format tolerates an interrupted run, so
    rewriting it is never necessary.

    Returns:
        ``(added, skipped)``, in that order.
    """
    known = {signal.id for signal in load_signals(path)}
    fresh: list[Signal] = []
    skipped = 0
    for signal in signals:
        if signal.id in known:
            skipped += 1
            continue
        known.add(signal.id)
        fresh.append(signal)

    if fresh:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            for signal in fresh:
                stream.write(json.dumps(signal.to_dict(), ensure_ascii=False) + "\n")
    return len(fresh), skipped


def load_clusters(path: Path) -> list[Cluster]:
    """Read the cluster file, returning an empty list when absent."""
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StorageError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or "clusters" not in payload:
        raise StorageError(f"{path} must contain an object with a 'clusters' key")
    clusters: list[Cluster] = []
    for item in payload["clusters"]:
        if not isinstance(item, dict):
            raise StorageError(f"{path}: cluster entries must be objects")
        clusters.append(Cluster.from_dict(item))
    return clusters


def save_clusters(path: Path, clusters: list[Cluster]) -> None:
    """Write every cluster to ``path``, in the order given by the caller."""
    payload: dict[str, Any] = {
        "version": 1,
        "count": len(clusters),
        "clusters": [cluster.to_dict() for cluster in clusters],
    }
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _overlap(first: Cluster, second: Cluster) -> float:
    """Share of ``first``'s signals present in ``second``."""
    if not first.signal_ids:
        return 0.0
    return len(set(first.signal_ids) & set(second.signal_ids)) / len(set(first.signal_ids))


def carry_over_state(new_clusters: list[Cluster], previous: list[Cluster]) -> int:
    """Copy human state from ``previous`` clusters to the new ones in place.

    A previous cluster is matched by signal overlap (at least half of its
    signals) and, as a fallback, by exact title. Only ``status``, ``note`` and
    ``solutions`` are carried: the score is always recomputed.

    Returns:
        Number of clusters that inherited state.
    """
    carried = 0
    for new_cluster in new_clusters:
        best: Cluster | None = None
        best_score = 0.0
        for old_cluster in previous:
            overlap = _overlap(old_cluster, new_cluster)
            if overlap > best_score:
                best_score = overlap
                best = old_cluster
        if best is None or best_score < 0.5:
            best = next(
                (
                    old
                    for old in previous
                    if old.title.strip().lower() == new_cluster.title.strip().lower()
                ),
                None,
            )
        if best is None:
            continue
        new_cluster.status = best.status
        new_cluster.note = best.note
        new_cluster.solutions = list(best.solutions)
        carried += 1
    return carried
