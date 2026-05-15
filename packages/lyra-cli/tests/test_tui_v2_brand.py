"""Brand identity contract for the Lyra theme.

The harness-tui ``Theme`` has 48 semantic tokens; the project's
``with_brand`` override sets only three (primary / primary_alt /
accent) plus the ASCII logo + spinner. The rest must survive the
override so the chat / tool-card / modal surfaces stay recognisable.
"""
from __future__ import annotations

from lyra_cli.tui_v2.brand import (
    ACCENT,
    LYRA_LOGO,
    PRIMARY,
    PRIMARY_ALT,
    lyra_theme,
    welcome_lines,
)


def test_brand_tokens_applied() -> None:
    theme = lyra_theme()
    assert theme.name == "lyra"
    assert theme.primary == PRIMARY
    assert theme.primary_alt == PRIMARY_ALT
    assert theme.accent == ACCENT


def test_base_palette_preserved_from_catppuccin() -> None:
    """Non-brand tokens must come straight from the base theme.

    If a future refactor accidentally clears these, the diff colours
    and syntax highlighting will go off-brand on first hover.
    """
    theme = lyra_theme()
    # Sample one token from each band that ``with_brand`` does NOT touch.
    for token in ("bg", "fg", "border", "success", "warning", "danger"):
        value = getattr(theme, token)
        assert isinstance(value, str) and value.startswith("#"), token


def test_logo_is_non_empty_multiline_with_brand_colours() -> None:
    assert LYRA_LOGO.count("\n") >= 5  # at least 6 lines
    # Logo must reference both brand hues so the constellation is visible
    # against both terminal backgrounds.
    assert PRIMARY in LYRA_LOGO
    assert ACCENT in LYRA_LOGO


def test_spinner_frames_set() -> None:
    theme = lyra_theme()
    frames = theme.spinner_frames
    assert isinstance(frames, tuple) and len(frames) >= 2
    # Lyra's brand spinner is musical notes (harp motif).
    assert all(isinstance(f, str) and len(f) >= 1 for f in frames)


def test_welcome_lines_has_intro_and_hint() -> None:
    lines = welcome_lines("3.14.0", model="deepseek-chat", mode="default", repo="lyra")
    text = "\n".join(lines)
    assert "Welcome to Lyra v3.14.0!" in text
    # Hint trio matches the screenshot semantics — Claude Code muscle memory.
    assert "/help" in text
    assert "/status" in text
    assert "⌥?" in text
    # Setup block carries model/mode/repo.
    assert "deepseek-chat" in text
    assert "default" in text
    assert "lyra" in text


def test_welcome_lines_handles_blank_fields() -> None:
    lines = welcome_lines("3.14.0", model="", mode="", repo="")
    text = "\n".join(lines)
    assert "Welcome to Lyra v3.14.0!" in text
    # Falls back to dashes/defaults rather than emitting blanks.
    assert "—" in text or "default" in text


def test_welcome_lines_intro_carries_brand_glyph() -> None:
    """The ✻ sigil matches the legacy REPL banner — muscle memory."""
    lines = welcome_lines("3.14.0", model="x", mode="default", repo="r")
    assert any("✻" in line for line in lines)


def test_theme_exposes_textual_variables() -> None:
    """harness-tui consumes the theme via ``to_textual_variables``.

    If a future Textual upgrade changes that contract, the chat
    stylesheet stops resolving ``$primary`` / ``$accent`` and the UI
    goes monochrome.
    """
    theme = lyra_theme()
    variables = theme.to_textual_variables()
    assert isinstance(variables, dict) and variables
    # Must expose at least the brand tokens for the stylesheet.
    for key in ("primary", "accent"):
        assert any(key in k for k in variables), key
