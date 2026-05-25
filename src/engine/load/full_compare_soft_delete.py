"""``full_compare_soft_delete`` load mode: Delta MERGE with soft deletes"""

from __future__ import annotations

from typing import TYPE_CHECKING

from delta.tables import DeltaTable
from pyspark.sql import functions as F

from engine.errors import LoadError

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

# Column for tracking soft deletes from the Engine. This column is
# injected into the target schema automatically.
DELETED_AT_COLUMN = "deleted_at"


class FullCompareSoftDeleteLoader:
    
    def __init__(self, primary_keys: list[str]) -> None:
        # Create a loader bound to primary_keys
        if not primary_keys:
            raise LoadError(
                "FullCompareSoftDeleteLoader requires at least one primary key."
            )
        self.primary_keys = primary_keys

    def _merge_condition(self) -> str:
        # Build the join condition on primary keys
        return " AND ".join(f"target.{k} = source.{k}" for k in self.primary_keys)

    def _prepare_source(self, source: DataFrame) -> DataFrame:
        # Add the deleted_at column to source, set to NULL for all rows
        return source.withColumn(DELETED_AT_COLUMN, F.lit(None).cast("timestamp"))

    def _ensure_target_schema(self, spark: SparkSession, target_path: str) -> None:
        # Ensure the target table has the deleted_at column

        try:
            target = DeltaTable.forPath(spark, target_path)
            existing_columns = {c.lower() for c in target.toDF().columns}
            if DELETED_AT_COLUMN not in existing_columns:
                # Add the column with a SQL ALTER TABLE statement
                table_name = f"delta.`{target_path}`"
                spark.sql(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {DELETED_AT_COLUMN} TIMESTAMP"
                )
        except Exception:
            # Target doesn't exist yet. It will be created by Terraform
            # The first write will include the column from source.
            pass

    def run(self, source: DataFrame, target_path: str) -> None:
        # Run the soft-delete MERGE against the Delta table at target_path

        spark = source.sparkSession
        self._ensure_target_schema(spark, target_path)

        # Add deleted_at column to source (always NULL source rows are active)
        source_with_marker = self._prepare_source(source)

        target = DeltaTable.forPath(spark, target_path)

        # Build the merge statements as:
        # whenMatchedUpdate: row exists in both, update all columns, clear deleted_at
        # whenNotMatchedInsert: new row in source, insert with deleted_at = NULL
        # whenNotMatchedBySource: row only in target, set deleted_at if not already set
        merge = (
            target.alias("target")
            .merge(source_with_marker.alias("source"), self._merge_condition())
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
        )

        # For rows in target but not in source, soft-delete them.
        # Bring in Idempotency. Only update if deleted_at is NULL (not already deleted).
        merge = merge.whenNotMatchedBySourceUpdate(
            condition=f"target.{DELETED_AT_COLUMN} IS NULL",
            set={DELETED_AT_COLUMN: "current_timestamp()"},
        )

        merge.execute()
