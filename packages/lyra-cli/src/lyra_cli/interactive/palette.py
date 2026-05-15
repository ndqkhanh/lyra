"""Single-source palette for Lyra's REPL UI.

Two profiles (``DARK`` and ``LIGHT``) selected at startup by
:func:`is_light_terminal`, which mirrors OpenClaw's algorithm:

1. ``LYRA_THEME=light|dark`` — explicit override wins.
2. ``COLORFGBG`` env var — emitted by xterm and rxvt-family terminals
   as ``"<fg>;<bg>"`` or ``"<fg>;<unused>;<bg>"``. We parse the bg
   index against the xterm 256-colour cube and run a relative-
   luminance contrast check to pick the higher-contrast text colour.
3. Default to ``DARK``.

Every UI component reads colours from :data:`PALETTE` (a thin alias
for whichever of ``DARK`` / ``LIGHT`` is active for this process).
Tests can monkey-patch :func:`is_light_terminal` to exercise both
profiles.
"""
from __future__ import annotations

import os
from typing import TypedDict

__all__ = [
    "DARK",
    "LIGHT",
    "PALETTE",
    "Palette",
    "is_light_terminal",
    "select_palette",
]


class Palette(TypedDict):
    """Strict shape for a Lyra colour profile."""

    text: str
    text_strong: str
    dim: str
    meta: str
    accent: str
    accent_warm: str
    success: str
    error: str
    selected_bg: str
    # Tool-block tints (used by the OpenClaw-flavoured tinted render
    # profile; ignored by the flat profile).
    tool_pending: str
    tool_success: str
    tool_error: str


DARK: Palette = {
    "text":         "#cccccc",
    "text_strong":  "#ffffff",
    "dim":          "#555555",
    "meta":         "#888888",
    "accent":       "#5fafff",
    "accent_warm":  "#ffaf00",
    "success":      "#5fff87",
    "error":        "#ff6e6e",
    "selected_bg":  "#1f2533",
    "tool_pending": "#1f2a2f",
    "tool_success": "#1e2d23",
    "tool_error":   "#2f1f1f",
}


LIGHT: Palette = {
    "text":         "#222222",
    "text_strong":  "#000000",
    "dim":          "#888888",
    "meta":         "#5b6472",
    "accent":       "#0750a3",
    "accent_warm":  "#a86200",
    "success":      "#047857",
    "error":        "#b91c1c",
    "selected_bg":  "#e8eef8",
    "tool_pending": "#eff6ff",
    "tool_success": "#ecfdf5",
    "tool_error":   "#fef2f2",
}


# ── light/dark detection (port of OpenClaw's algorithm) ──────────


_XTERM_LEVELS: tuple[int, ...] = (0, 95, 135, 175, 215, 255)
_DARK_TEXT_HEX = "#e8e3d5"   # OpenClaw's reference dark-mode body
_LIGHT_TEXT_HEX = "#1e1e1e"  # OpenClaw's reference light-mode body


def _channel_to_srgb(value: int) -> float:
    n = value / 255.0
    return n / 12.92 if n <= 0.03928 else ((n + 0.055) / 1.055) ** 2.4


def _relative_luminance_rgb(r: int, g: int, b: int) -> float:
    return (
        0.2126 * _channel_to_srgb(r)
        + 0.7152 * _channel_to_srgb(g)
        + 0.0722 * _channel_to_srgb(b)
    )


def _relative_luminance_hex(hex_str: str) -> float:
    h = hex_str.lstrip("#")
    return _relative_luminance_rgb(
        int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    )


def _contrast_ratio(bg_lum: float, fg_hex: str) -> float:
    fg_lum = _relative_luminance_hex(fg_hex)
    lighter = max(bg_lum, fg_lum)
    darker = min(bg_lum, fg_lum)
    return (lighter + 0.05) / (darker + 0.05)


def _xterm_index_to_rgb(idx: int) -> tuple[int, int, int]:
    """Map an xterm 256 colour-cube index (16–231) to (r, g, b)."""
    cube = idx - 16
    b = _XTERM_LEVELS[cube % 6]
    g = _XTERM_LEVELS[(cube // 6) % 6]
    r = _XTERM_LEVELS[cube // 36]
    return r, g, b


def is_light_terminal() -> bool:
    """Best guess at whether the host terminal has a light background.

    Order of evidence:

    1. ``LYRA_THEME`` (``light`` / ``dark``) — explicit override.
    2. ``COLORFGBG`` — parse and compute contrast.
    3. Default ``False`` (assume dark).
    """
    explicit = (os.environ.get("LYRA_THEME") or "").strip().lower()
    if explicit == "light":
        return True
    if explicit == "dark":
        return False

    cfg = os.environ.get("COLORFGBG", "")
    if not cfg or len(cfg) > 64:
        return False
    sep = cfg.rfind(";")
    bg_str = cfg[sep + 1:] if sep >= 0 else cfg
    try:
        bg = int(bg_str)
    except ValueError:
        return False
    if not (0 <= bg <= 255):
        return False

    if bg <= 15:
        # Standard 16-colour palette: 7 (light grey) and 15 (white)
        # are the only routinely-used "light" entries.
        return bg in (7, 15)
    if bg >= 232:
        # 232–255 is the greyscale ramp (24 steps from black to white);
        # midpoint ≈ 244.
        return bg >= 244
    r, g, b = _xterm_index_to_rgb(bg)
    bg_lum = _relative_luminance_rgb(r, g, b)
    light_contrast = _contrast_ratio(bg_lum, _LIGHT_TEXT_HEX)
    dark_contrast = _contrast_ratio(bg_lum, _DARK_TEXT_HEX)
    return light_contrast >= dark_contrast


def select_palette() -> Palette:
    """Return the active palette for this process."""
    return LIGHT if is_light_terminal() else DARK


PALETTE: Palette = select_palette()
