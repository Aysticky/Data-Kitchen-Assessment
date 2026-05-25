"""Engine error types.

Kept intentionally small. The assessment expects this layer to grow —
see the ticket in README.md for the reasoning.
"""

from __future__ import annotations


class EngineError(Exception):
    """Base class for all engine errors."""


class ConfigError(EngineError):
    """Raised when a model configuration is invalid.

    Carries the originating file path where available so callers can
    surface actionable messages to domain engineers.
    """

    def __init__(self, message: str, *, source: str | None = None) -> None:
        """Create a config error.

        Args:
            message: Human-readable description of the problem.
            source: Path or identifier of the config file the error
                relates to, if known.
        """
        super().__init__(message)
        self.source = source

    def __str__(self) -> str:
        """Render the error with its source when available."""
        base = super().__str__()
        if self.source:
            return f"[{self.source}] {base}"
        return base


class LoadError(EngineError):
    """Raised when a load mode fails at runtime."""
