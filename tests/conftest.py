"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    """Session-scoped local Spark with Delta Lake configured."""
    builder = (
        SparkSession.builder.master("local[1]")
        .appName("engine-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.ui.showConsoleProgress", "false")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture
def delta_path(tmp_path: Path) -> str:
    """A filesystem path suitable for a Delta table in a test."""
    return str(tmp_path / "delta")


@pytest.fixture
def models_dir() -> Path:
    """Path to the sample domain model YAMLs at the repo root."""
    return Path(__file__).resolve().parent.parent / "models"
