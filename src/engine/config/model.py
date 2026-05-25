"""Pydantic models for YAML model configuration.

Structure:

- ``Column``       — a single column definition
- ``Refresh``      — load mode + any mode-specific configuration
- ``ModelConfig``  — the top-level object for a single YAML file

Extending this module (new load modes, new column types, new refresh
config fields) is part of the normal engine development loop.
"""

from __future__ import annotations

import re

from pydantic import Field, field_validator, model_validator

from engine.config.base_model import ConfigBaseModel
from engine.config.enums import DataType, Layer, LoadMode

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_name(value: str) -> str:
    if not _NAME_PATTERN.fullmatch(value):
        msg = (
            f"Invalid identifier {value!r}: must be lowercase, start with "
            "a letter, and contain only letters, digits, and underscores."
        )
        raise ValueError(msg)
    return value


class Column(ConfigBaseModel):
    """A single column in a model."""

    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _validate_name(value)


class Refresh(ConfigBaseModel):
    """Load-mode selection and any mode-specific configuration.

    Modes that do not need extra configuration simply leave ``config``
    unset. Modes that do need extra configuration (for example, any
    mode that requires primary keys) are expected to validate that in
    ``ModelConfig`` once the columns are visible.
    """

    mode: LoadMode


class ModelConfig(ConfigBaseModel):
    """Top-level model configuration parsed from a YAML file."""

    layer: Layer
    name: str
    description: str | None = None
    refresh: Refresh
    columns: list[Column] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _validate_name(value)

    @property
    def primary_keys(self) -> list[str]:
        """Return the primary-key column names in declaration order."""
        return [c.name for c in self.columns if c.primary_key]

    @model_validator(mode="after")
    def _validate_mode_requirements(self) -> ModelConfig:
        """Cross-field validation for load modes that have extra rules.

        ``full_compare`` can only produce correct results if it has at
        least one primary key to match source rows against target rows.
        """
        if self.refresh.mode == LoadMode.FULL_COMPARE and not self.primary_keys:
            msg = (
                "Load mode 'full_compare' requires at least one column "
                "marked primary_key: true."
            )
            raise ValueError(msg)
        return self
