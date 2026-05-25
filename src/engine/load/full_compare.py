"""``full_compare`` load mode: Delta MERGE with insert / update / delete."""

from __future__ import annotations

from typing import TYPE_CHECKING

from delta.tables import DeltaTable

from engine.errors import LoadError

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class FullCompareLoader:
    """Synchronises a Delta target with a source DataFrame.

    Semantics:

    - Rows present in source but not in target are **inserted**.
    - Rows present in both, with differing non-key values, are **updated**.
    - Rows present in target but missing from source are **deleted**.

    Requires at least one primary key to match source rows against
    target rows. Without a key, merge behaviour is undefined; the
    configuration layer is responsible for rejecting that case before
    we get here.
    """

    def __init__(self, primary_keys: list[str]) -> None:
        """Create a loader bound to ``primary_keys``."""
        if not primary_keys:
            raise LoadError("FullCompareLoader requires at least one primary key.")
        self.primary_keys = primary_keys

    def _merge_condition(self) -> str:
        return " AND ".join(f"target.{k} = source.{k}" for k in self.primary_keys)

    def run(self, source: DataFrame, target_path: str) -> None:
        """Run the MERGE against the Delta table at ``target_path``.

        The target Delta table must already exist (Terraform creates it
        at deployment time); the first load is a no-op against an empty
        table, which produces the same outcome as a ``full`` load.
        """
        spark = source.sparkSession
        target = DeltaTable.forPath(spark, target_path)
        (
            target.alias("target")
            .merge(source.alias("source"), self._merge_condition())
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .whenNotMatchedBySourceDelete()
            .execute()
        )
