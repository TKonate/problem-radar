"""Problem Radar — collect public problem signals and score opportunities.

The package is deliberately dependency-free: sources are public APIs and RSS
feeds, storage is JSONL, and the whole pipeline can run from a cron job on the
smallest VPS.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
