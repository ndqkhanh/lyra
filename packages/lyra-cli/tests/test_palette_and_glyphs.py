"""Pin tests for the new palette + glyphs identity layer (Phase 1).

Two pure modules with no behaviour beyond constants and a small
detection function — these tests guard against accidental drift in
the visual language and verify the COLORFGBG algorithm matches
OpenClaw's reference behaviour.
"""
from __future__ import annotations

from typing import Any

import pytest

from lyra_cli.interactive import glyphs, palette


# ── glyphs ───────────────────────────────────────────────────────


def test_glyph_alphabet_uses_expected_characters() -> None:
    """The visible glyph set is the contract — pin it so a refactor
    cannot silently swap them out."""
    assert glyphs.PROMPT == "❯"
    assert glyphs.ASSISTANT == "⏺"
    assert glyphs.OUTPUT == "⎿"
    assert glyphs.CHECK == "✓"
    assert glyphs.CROSS == "✗"
    assert glyphs.LOCK == "🔒"
    assert glyphs.USER_OVERRIDE == "✎"
    assert glyphs.RUNNING == "▶"


def test_cursor_aliases_prompt() -> None:
    """Pickers and the input line use the same shape — that's a
    deliberate choice, not a coincidence."""
    assert glyphs.CURSOR == glyphs.PROMPT


# ── palette: dict shape ──────────────────────────────────────────


_REQUIRED_KEYS = (
    "text",
    "text_strong",
    "dim",
    "meta",
    "accent",
    "accent_warm",
    "success",
    "error",
    "selected_bg",
    "tool_pending",
    "tool_success",
    "tool_error",
)


@pytest.mark.parametrize("p", [palette.DARK, palette.LIGHT])
def test_each_palette_has_required_keys(p: dict) -> None:
    for key in _REQUIRED_KEYS:
        assert key in p, f"missing {key!r} in palette"


@pytest.mark.parametrize("p", [palette.DARK, palette.LIGHT])
def test_each_palette_value_is_seven_char_hex(p: dict) -> None:
    for key, value in p.items():
        assert isinstance(value, str), f"{key!r} → {value!r} not a string"
        assert value.startswith("#"), f"{key!r} → {value!r} missing #"
        assert len(value) == 7, f"{key!r} → {value!r} not 7 chars"


# ── palette: COLORFGBG detection ─────────────────────────────────


def test_explicit_lyra_theme_wins_over_colorfgbg(monkeypatch: Any) -> None:
    monkeypatch.setenv("LYRA_THEME", "light")
    monkeypatch.setenv("COLORFGBG", "0;0")  # would otherwise mean dark
    assert palette.is_light_terminal() is True

    monkeypatch.setenv("LYRA_THEME", "dark")
    monkeypatch.setenv("COLORFGBG", "15;15")  # would otherwise mean light
    assert palette.is_light_terminal() is False


def test_default_when_no_env_is_dark(monkeypatch: Any) -> None:
    monkeypatch.delenv("LYRA_THEME", raising=False)
    monkeypatch.delenv("COLORFGBG", raising=False)
    assert palette.is_light_terminal() is False


def test_colorfgbg_index_15_is_light(monkeypatch: Any) -> None:
    """COLORFGBG="0;15" → bg index 15 (white) → light terminal."""
    monkeypatch.delenv("LYRA_THEME", raising=False)
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert palette.is_light_terminal() is True


def test_colorfgbg_index_0_is_dark(monkeypatch: Any) -> None:
    monkeypatch.delenv("LYRA_THEME", raising=False)
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert palette.is_light_terminal() is False


def test_colorfgbg_three_field_form_uses_last_segment(monkeypatch: Any) -> None:
    """rxvt-family terminals emit ``"<fg>;<unused>;<bg>"`` — last wins."""
    monkeypatch.delenv("LYRA_THEME", raising=False)
    monkeypatch.setenv("COLORFGBG", "0;default;15")
    assert palette.is_light_terminal() is True


def test_colorfgbg_greyscale_dark_half(monkeypatch: Any) -> None:
    """Indices 232–243 are the dark half of the xterm greyscale ramp."""
    monkeypatch.delenv("LYRA_THEME", raising=False)
    for bg in (232, 235, 240, 243):
        monkeypatch.setenv("COLORFGBG", f"15;{bg}")
        assert palette.is_light_terminal() is False, f"bg={bg}"


def test_colorfgbg_greyscale_light_half(monkeypatch: Any) -> None:
    """Indices 244–255 are the light half of the xterm greyscale ramp."""
    monkeypatch.delenv("LYRA_THEME", raising=False)
    for bg in (244, 248, 252, 255):
        monkeypatch.setenv("COLORFGBG", f"0;{bg}")
        assert palette.is_light_terminal() is True, f"bg={bg}"


def test_colorfgbg_malformed_falls_back_to_dark(monkeypatch: Any) -> None:
    """Invalid integer or out-of-range bg → assume dark (don't crash)."""
    monkeypatch.delenv("LYRA_THEME", raising=False)
    for cfg in ("not-numbers", "0;999", "0;-1", ""):
        monkeypatch.setenv("COLORFGBG", cfg)
        assert palette.is_light_terminal() is False, f"cfg={cfg!r}"


def test_select_palette_returns_dark_when_dark_terminal(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("LYRA_THEME", "dark")
    assert palette.select_palette() is palette.DARK


def test_select_palette_returns_light_when_light_terminal(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("LYRA_THEME", "light")
    assert palette.select_palette() is palette.LIGHT


def test_module_level_palette_alias_resolves_to_one_of_the_profiles() -> None:
    """The PALETTE constant is module-level; whichever it points to,
    it must be one of our two profiles."""
    assert palette.PALETTE in (palette.DARK, palette.LIGHT)
