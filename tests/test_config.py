"""Tests for the configuration layer.

These tests cover the shape of the API, not exhaustive validation cases.
Use them as a reference for style — your own tests for the new load mode
should live alongside these or in a new file in this directory.
"""

from __future__ import annotations

import pytest

from engine.config import LoadMode, ModelConfig, load_config
from engine.errors import ConfigError


def test_full_config_loads(models_dir):
    config = load_config(models_dir / "orders_raw.yaml")
    assert isinstance(config, ModelConfig)
    assert config.name == "orders_raw"
    assert config.refresh.mode == LoadMode.FULL
    assert config.primary_keys == []


def test_full_compare_config_loads(models_dir):
    config = load_config(models_dir / "dim_customers.yaml")
    assert config.refresh.mode == LoadMode.FULL_COMPARE
    assert config.primary_keys == ["customer_id"]


def test_full_compare_without_primary_keys_is_rejected():
    raw = {
        "layer": "gold",
        "name": "no_keys",
        "refresh": {"mode": "full_compare"},
        "columns": [{"name": "x", "data_type": "string"}],
    }
    with pytest.raises(ValueError, match="primary_key"):
        ModelConfig(**raw)


def test_unknown_field_is_rejected():
    raw = {
        "layer": "bronze",
        "name": "t",
        "refresh": {"mode": "full"},
        "columns": [{"name": "x", "data_type": "string"}],
        "extra_top_level": "oops",
    }
    with pytest.raises(ValueError, match="extra_top_level"):
        ModelConfig(**raw)


def test_missing_config_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")
