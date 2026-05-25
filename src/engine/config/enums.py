"""Enumerations used by the configuration schema."""

from __future__ import annotations

from enum import StrEnum


class LoadMode(StrEnum):
    """How a target table is loaded from a source DataFrame.

    Extend this enum when adding new load modes.
    """

    FULL = "full"
    FULL_COMPARE = "full_compare"


class Layer(StrEnum):
    """Medallion layer a model belongs to."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class DataType(StrEnum):
    """Spark-compatible column data types supported by the engine."""

    INT = "int"
    BIGINT = "bigint"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    DECIMAL = "decimal"
    DOUBLE = "double"
