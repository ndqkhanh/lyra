"""HUD config + built-in presets (Phase 6i).

Presets describe *which* widgets render, in what order, with what
colour palette. Operators override via ``~/.lyra/hud.yaml`` (loaded
by a future PR; for now only the built-in presets are used).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HudConfig:
    """One HUD layout preset.

    Attributes
    ----------
    name
        Identifier (``"compact"`` / ``"full"`` / ``"minimal"`` / ``"inline"``).
    widgets
        Ordered list of widget names. Each must be a key in
        :data:`lyra_cli.hud.widgets.WIDGET_REGISTRY`.
    max_width
        Column cap for each rendered widget line. ``120`` is the
        default for non-inline presets; ``0`` means no cap.
    """

    name: str
    widgets: tuple[str, ...]
    max_width: int = 120


_PRESETS: dict[str, HudConfig] = {
    "minimal": HudConfig(
        name="minimal",
        widgets=("identity_line",),
    ),
    "compact": HudConfig(
        name="compact",
        widgets=(
            "identity_line",
            "context_bar",
            "usage_line",
        ),
    ),
    "full": HudConfig(
        name="full",
        widgets=(
            "identity_line",
            "context_bar",
            "usage_line",
            "tools_line",
            "agents_line",
            "todos_line",
            "git_line",
            "cache_line",
            "tracer_line",
        ),
    ),
    "inline": HudConfig(
        name="inline",
        # Single-line layout for prompt_toolkit's bottom-toolbar.
        widgets=("identity_line", "context_bar", "usage_line"),
        max_width=80,
    ),
}


def available_presets() -> list[str]:
    """Names of all built-in presets, in display order."""
    return ["minimal", "compact", "full", "inline"]


def load_preset(name: str) -> HudConfig:
    """Look up a built-in preset by name.

    Raises ``ValueError`` for unknown names with a helpful message
    listing the valid options.
    """
    if name not in _PRESETS:
        raise ValueError(
            f"unknown HUD preset {name!r}; valid: {sorted(_PRESETS)}"
        )
    return _PRESETS[name]


__all__ = ["HudConfig", "available_presets", "load_preset"]
