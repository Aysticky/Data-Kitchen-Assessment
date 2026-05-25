"""``full`` load mode: truncate target and rewrite from source."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class FullLoader:
    """Overwrites the target Delta table with the source DataFrame.

    The target is replaced atomically — readers see either the old
    snapshot or the new one, never a partial write.
    """

    def run(self, source: DataFrame, target_path: str) -> None:
        """Overwrite ``target_path`` with ``source``."""
        (
            source.write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(target_path)
        )
