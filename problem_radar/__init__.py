"""Problem Radar: collect public problem signals and score opportunities.

The package is deliberately dependency-free: sources are public APIs and RSS
feeds, storage is JSONL, so the whole pipeline runs from a cron job on the
smallest VPS. Importing this module has no side effect and loads no other
module, because ``problem_radar.__version__`` must stay cheap to read.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
