"""Base Pydantic model for all engine config types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConfigBaseModel(BaseModel):
    """Shared config base.

    - Unknown fields are rejected (``extra="forbid"``) so a typo in a
      YAML config surfaces as a validation error instead of being
      silently ignored.
    - Enum values are populated by value (strings), which gives us
      readable error messages when YAML provides an invalid value.
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        frozen=False,
    )
