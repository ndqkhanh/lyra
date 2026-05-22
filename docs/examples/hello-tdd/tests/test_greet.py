"""Red tests for the greeting library."""
from __future__ import annotations

import pytest

from greet import greet


def test_greets_named_user() -> None:
    assert greet("Ada") == "Hello, Ada!"


def test_refuses_empty_name() -> None:
    with pytest.raises(ValueError, match="empty"):
        greet("")
