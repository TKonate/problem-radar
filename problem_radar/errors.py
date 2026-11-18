"""Exception hierarchy.

Every expected failure is one of these, so the CLI can print a readable message
and an exit code instead of a traceback.
"""

from __future__ import annotations


class RadarError(Exception):
    """Base class for expected failures."""


class ConfigError(RadarError):
    """The configuration is missing, malformed or inconsistent."""


class CollectionError(RadarError):
    """A source could not be collected (network, rate limit, bad payload)."""

    def __init__(self, message: str, *, source: str = "", url: str = "", status: int = 0) -> None:
        super().__init__(message)
        self.source = source
        self.url = url
        self.status = status


class StorageError(RadarError):
    """A data file could not be read or written."""


class ValidationError(RadarError):
    """A human supplied value is invalid."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []
