"""YAML configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from engine.config.model import ModelConfig
from engine.errors import ConfigError


def load_config(path: Path | str) -> ModelConfig:
    """Load and validate a YAML model configuration file.

    Args:
        path: Filesystem path to a YAML file.

    Returns:
        A validated ``ModelConfig``.

    Raises:
        ConfigError: If the file does not exist, is not a YAML mapping,
            or fails validation.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open() as f:
        raw: Any = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config file must contain a YAML mapping, got {type(raw).__name__}.",
            source=str(path),
        )

    try:
        return ModelConfig(**raw)
    except ValidationError as e:
        raise ConfigError(str(e), source=str(path)) from e
