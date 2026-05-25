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
