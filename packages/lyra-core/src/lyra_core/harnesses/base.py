"""Deprecated re-export: :mod:`lyra_core.harnesses.base` → :mod:`lyra_core.adapters.base`."""
from __future__ import annotations

from lyra_core.adapters.base import (
    HarnessPlugin,
    get_harness,
    register_harness,
)

__all__ = ["HarnessPlugin", "get_harness", "register_harness"]
