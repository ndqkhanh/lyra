"""Example plugin: Custom greeting tool.

This demonstrates the basic plugin structure for Lyra.
"""
from __future__ import annotations

from typing import Any


def greet(name: str, *, formal: bool = False) -> dict[str, Any]:
    """Greet a user by name.

    Args:
        name: The name to greet.
        formal: Use formal greeting (default: False).

    Returns:
        Dict with greeting message.
    """
    if formal:
        greeting = f"Good day, {name}."
    else:
        greeting = f"Hey {name}!"

    return {
        "greeting": greeting,
        "name": name,
        "formal": formal,
    }


# Plugin manifest
manifest = {
    "name": "greeting-plugin",
    "version": "1.0.0",
    "description": "Example plugin with custom greeting tool",
    "author": "Lyra Team",
    "tools": [
        {
            "name": "greet",
            "function": greet,
            "description": "Greet a user by name",
            "category": "communication",
        }
    ],
}
