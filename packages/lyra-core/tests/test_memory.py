"""Memory system tests.

The memory architecture has been refactored into the lyra_memory package
(6-layer NeuroMemory) and lyra_core.memory directory. These tests have been
migrated to packages/lyra-memory/tests/.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Memory tests migrated to lyra_memory package")


def test_memory_stub() -> None:
    """Placeholder — memory tests live in packages/lyra-memory/tests/."""
    pass
