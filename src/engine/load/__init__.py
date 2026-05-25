"""Load-mode implementations.

Adding a new load mode means adding a new ``Loader`` subclass here and
wiring it through the dispatcher in ``get_loader``.
"""

from __future__ import annotations

from engine.config.enums import LoadMode
from engine.errors import LoadError
from engine.load.base import Loader
from engine.load.full import FullLoader
from engine.load.full_compare import FullCompareLoader


def get_loader(mode: LoadMode, primary_keys: list[str]) -> Loader:
    """Return the loader implementation for a given load mode.

    Args:
        mode: The declared load mode.
        primary_keys: Column names marked as primary keys on the model.

    Raises:
        LoadError: If no loader is registered for ``mode``.
    """
    if mode == LoadMode.FULL:
        return FullLoader()
    if mode == LoadMode.FULL_COMPARE:
        return FullCompareLoader(primary_keys=primary_keys)
    raise LoadError(f"No loader registered for load mode {mode.value!r}.")


__all__ = [
    "FullCompareLoader",
    "FullLoader",
    "Loader",
    "get_loader",
]
