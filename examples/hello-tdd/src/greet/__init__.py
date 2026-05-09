"""Tiny greeting library for the Lyra hello-tdd demo."""
from __future__ import annotations


def greet(name: str) -> str:
    """Return a greeting for ``name``.

    Empty names are rejected (we refuse to greet the void).
    """
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"
