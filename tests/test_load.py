"""Reference tests for the existing load modes.

These tests show the shape of a Delta-backed test: build a source
DataFrame, seed the target once, run the loader, then assert on the
contents of the Delta table. Use them as a reference when testing a new
load mode.
"""

from __future__ import annotations

import pytest

from engine.config.enums import LoadMode
from engine.load import get_loader


def _read(spark, path: str):
    return spark.read.format("delta").load(path)


def _rows(df, *cols):
    return sorted(tuple(r[c] for c in cols) for r in df.collect())


def test_full_overwrites_target(spark, delta_path):
    initial = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "name"])
    initial.write.format("delta").save(delta_path)

    replacement = spark.createDataFrame([(3, "c")], ["id", "name"])
    get_loader(LoadMode.FULL, primary_keys=[]).run(replacement, delta_path)

    assert _rows(_read(spark, delta_path), "id", "name") == [(3, "c")]


@pytest.fixture
def seeded_target(spark, delta_path):
    """Seed the target Delta table with three customer rows."""
    seed = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),
            (2, "bob@x.com", "BE"),
            (3, "carol@x.com", "NL"),
        ],
        ["customer_id", "email", "country"],
    )
    seed.write.format("delta").save(delta_path)
    return delta_path


def test_full_compare_inserts_updates_and_deletes(spark, seeded_target):
    source = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),  # unchanged
            (2, "bob@new.com", "BE"),  # updated
            (4, "dave@x.com", "DE"),  # new — row 3 is absent
        ],
        ["customer_id", "email", "country"],
    )

    loader = get_loader(LoadMode.FULL_COMPARE, primary_keys=["customer_id"])
    loader.run(source, seeded_target)

    result = _rows(_read(spark, seeded_target), "customer_id", "email", "country")
    assert result == [
        (1, "alice@x.com", "NL"),
        (2, "bob@new.com", "BE"),
        (4, "dave@x.com", "DE"),
    ]


def test_full_compare_is_idempotent(spark, seeded_target):
    source = spark.createDataFrame(
        [(1, "alice@x.com", "NL"), (2, "bob@x.com", "BE"), (3, "carol@x.com", "NL")],
        ["customer_id", "email", "country"],
    )
    loader = get_loader(LoadMode.FULL_COMPARE, primary_keys=["customer_id"])

    loader.run(source, seeded_target)
    loader.run(source, seeded_target)

    assert _read(spark, seeded_target).count() == 3


## Soft-delete mode tests

@pytest.fixture
def soft_delete_seeded_target(spark, tmp_path):
    """Seed the target Delta table with three customer rows for soft delete tests."""
    target_path = str(tmp_path / "soft_delete_customers")
    seed = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),
            (2, "bob@x.com", "BE"),
            (3, "carol@x.com", "NL"),
        ],
        ["customer_id", "email", "country"],
    )
    # Add the deleted_at column to match the expected schema
    from pyspark.sql import functions as F

    seed_with_marker = seed.withColumn("deleted_at", F.lit(None).cast("timestamp"))
    seed_with_marker.write.format("delta").save(target_path)
    return target_path


def test_soft_delete_marks_absent_rows_as_deleted(spark, soft_delete_seeded_target):
    """Rows that disappear from source should be marked deleted, not removed."""
    source = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),  # unchanged
            (2, "bob@x.com", "BE"),  # unchanged
            # row 3 (carol) is absent, should be soft-deleted
        ],
        ["customer_id", "email", "country"],
    )

    loader = get_loader(
        LoadMode.FULL_COMPARE_SOFT_DELETE, primary_keys=["customer_id"]
    )
    loader.run(source, soft_delete_seeded_target)

    result_df = _read(spark, soft_delete_seeded_target)

    # All three rows should still be present
    assert result_df.count() == 3

    # Rows 1 and 2 should have deleted_at = NULL
    active = result_df.filter("deleted_at IS NULL")
    assert _rows(active, "customer_id", "email") == [
        (1, "alice@x.com"),
        (2, "bob@x.com"),
    ]

    # Row 3 should have deleted_at set
    deleted = result_df.filter("deleted_at IS NOT NULL")
    assert _rows(deleted, "customer_id", "email") == [(3, "carol@x.com")]


def test_soft_delete_restores_reappearing_rows(spark, soft_delete_seeded_target):
    """Rows that reappear in source after deletion should be restored."""
    # First load: remove row 3
    source_1 = spark.createDataFrame(
        [(1, "alice@x.com", "NL"), (2, "bob@x.com", "BE")],
        ["customer_id", "email", "country"],
    )
    loader = get_loader(
        LoadMode.FULL_COMPARE_SOFT_DELETE, primary_keys=["customer_id"]
    )
    loader.run(source_1, soft_delete_seeded_target)

    # Verify row 3 is soft-deleted
    result_1 = _read(spark, soft_delete_seeded_target)
    deleted_1 = result_1.filter("deleted_at IS NOT NULL")
    assert deleted_1.count() == 1
    assert deleted_1.first()["customer_id"] == 3

    # Second load: row 3 reappears with updated data
    source_2 = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),
            (2, "bob@x.com", "BE"),
            (3, "carol@new.com", "DE"),  # reappears with new email and country
        ],
        ["customer_id", "email", "country"],
    )
    loader.run(source_2, soft_delete_seeded_target)

    # Verify row 3 is restored (deleted_at = NULL) and updated
    result_2 = _read(spark, soft_delete_seeded_target)
    assert result_2.filter("deleted_at IS NOT NULL").count() == 0  # no deleted rows
    restored = result_2.filter("customer_id = 3")
    assert restored.count() == 1
    restored_row = restored.first()
    assert restored_row["deleted_at"] is None
    assert restored_row["email"] == "carol@new.com"
    assert restored_row["country"] == "DE"


def test_soft_delete_updates_active_rows(spark, soft_delete_seeded_target):
    """Active rows should be updated normally when data changes."""
    source = spark.createDataFrame(
        [
            (1, "alice@updated.com", "DE"),  # email and country updated
            (2, "bob@x.com", "BE"),  # unchanged
            (3, "carol@x.com", "NL"),  # unchanged
        ],
        ["customer_id", "email", "country"],
    )

    loader = get_loader(
        LoadMode.FULL_COMPARE_SOFT_DELETE, primary_keys=["customer_id"]
    )
    loader.run(source, soft_delete_seeded_target)

    result_df = _read(spark, soft_delete_seeded_target)
    updated_row = result_df.filter("customer_id = 1").first()
    assert updated_row["email"] == "alice@updated.com"
    assert updated_row["country"] == "DE"
    assert updated_row["deleted_at"] is None


def test_soft_delete_inserts_new_rows(spark, soft_delete_seeded_target):
    """New rows should be inserted with deleted_at = NULL."""
    source = spark.createDataFrame(
        [
            (1, "alice@x.com", "NL"),
            (2, "bob@x.com", "BE"),
            (3, "carol@x.com", "NL"),
            (4, "dave@x.com", "DE"),  # new row
        ],
        ["customer_id", "email", "country"],
    )

    loader = get_loader(
        LoadMode.FULL_COMPARE_SOFT_DELETE, primary_keys=["customer_id"]
    )
    loader.run(source, soft_delete_seeded_target)

    result_df = _read(spark, soft_delete_seeded_target)
    assert result_df.count() == 4
    new_row = result_df.filter("customer_id = 4").first()
    assert new_row["email"] == "dave@x.com"
    assert new_row["deleted_at"] is None


def test_soft_delete_is_idempotent(spark, soft_delete_seeded_target):
    """Running the same load multiple times should produce the same result."""
    source = spark.createDataFrame(
        [(1, "alice@x.com", "NL"), (2, "bob@x.com", "BE")],  # row 3 absent
        ["customer_id", "email", "country"],
    )
    loader = get_loader(
        LoadMode.FULL_COMPARE_SOFT_DELETE, primary_keys=["customer_id"]
    )

    # Run twice
    loader.run(source, soft_delete_seeded_target)
    result_1 = _read(spark, soft_delete_seeded_target)
    deleted_at_1 = result_1.filter("customer_id = 3").first()["deleted_at"]

    loader.run(source, soft_delete_seeded_target)
    result_2 = _read(spark, soft_delete_seeded_target)
    deleted_at_2 = result_2.filter("customer_id = 3").first()["deleted_at"]

    # The deleted_at timestamp should not change on subsequent runs
    assert deleted_at_1 is not None
    assert deleted_at_1 == deleted_at_2
    assert result_2.count() == 3

