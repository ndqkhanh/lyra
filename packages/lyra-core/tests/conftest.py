"""Shared pytest fixtures for lyra-core."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Temporary repo root with minimal lyra layout."""
    (tmp_path / ".lyra").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path
