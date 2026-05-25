"""Base ``Loader`` protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class Loader(Protocol):
    """Runs a single load from a source DataFrame to a Delta target."""

    def run(self, source: DataFrame, target_path: str) -> None:
        """Load ``source`` into the Delta table at ``target_path``."""
        ...
