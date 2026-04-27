"""v3.2.0 4-mode taxonomy contract — regression for the screenshot bug.

Why this file exists:
    On a real session a user typed "how many modes you have" and Lyra
    answered "I have 3 modes — BUILD / RED / GREEN / REFACTOR" (see
    CHANGELOG v3.2.0). That was wrong on two axes:

    1. The user-visible mode taxonomy was Lyra's legacy 5-mode set
       (``plan / build / run / explore / retro``) instead of the
       Claude-Code-style 4-mode set the rest of the agent ecosystem
       expects (``agent / plan / debug / ask``).
    2. The mode-specific system prompt for ``build`` did not enumerate
       the available modes, so the LLM hallucinated the TDD phases
       (RED / GREEN / REFACTOR) as if they were peer modes — they
       are *phases* of the opt-in TDD plugin, not modes at all.

    v3.2.0 fixes both: collapses the taxonomy to the 4 Claude-Code
    modes and stitches a verbatim 4-mode preamble into every
    mode-specific system prompt. This test pins both contracts so a
    future refactor can't re-introduce the regression silently.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.keybinds import _MODE_CYCLE_TAB, cycle_mode
from lyra_cli.interactive.session import (
    _LEGACY_MODE_REMAP,
    _LYRA_MODE_PREAMBLE,
    _MODE_BLURBS,
    _MODE_HANDLERS,
    _MODE_SYSTEM_PROMPTS,
    _VALID_MODES,
    InteractiveSession,
    _cmd_mode,
)


# ---------------------------------------------------------------------------
# Kernel taxonomy — exactly 4 modes, names match Claude Code
# ---------------------------------------------------------------------------


def test_valid_modes_are_exactly_the_claude_code_four() -> None:
    """``_VALID_MODES`` is the canonical source-of-truth for the 4 modes."""
    assert _VALID_MODES == ("agent", "plan", "debug", "ask")


def test_default_mode_is_agent(tmp_path: Path) -> None:
    """A bare ``InteractiveSession()`` lands in ``agent`` mode."""
    s = InteractiveSession(repo_root=tmp_path)
    assert s.mode == "agent"


def test_mode_handlers_cover_every_valid_mode() -> None:
    """Every mode in ``_VALID_MODES`` has a registered plain-text handler."""
    assert set(_MODE_HANDLERS.keys()) == set(_VALID_MODES)


def test_mode_system_prompts_cover_every_valid_mode() -> None:
    """Every mode has a mode-specific system prompt."""
    assert set(_MODE_SYSTEM_PROMPTS.keys()) == set(_VALID_MODES)


def test_mode_blurbs_cover_every_valid_mode() -> None:
    """``_MODE_BLURBS`` (used by ``/mode list``) lists all 4 modes in order."""
    blurb_names = tuple(name for name, _ in _MODE_BLURBS)
    assert blurb_names == _VALID_MODES


def test_tab_cycle_is_a_permutation_of_valid_modes() -> None:
    """``_MODE_CYCLE_TAB`` (Tab key rotation) covers every valid mode exactly once."""
    assert set(_MODE_CYCLE_TAB) == set(_VALID_MODES)
    assert len(_MODE_CYCLE_TAB) == len(_VALID_MODES)


# ---------------------------------------------------------------------------
# Screenshot-bug regression: every system prompt enumerates the 4 modes
# AND explicitly disclaims TDD phases (RED / GREEN / REFACTOR) as modes.
# ---------------------------------------------------------------------------


def test_preamble_enumerates_all_four_modes_in_order() -> None:
    """The shared preamble lists every mode by name, in canonical order.

    Critical: the LLM relies on this preamble to ground its "how many
    modes do you have" answer. Removing or reordering this list is
    the v3.2.0 regression we're guarding against.
    """
    for mode_name in _VALID_MODES:
        assert mode_name in _LYRA_MODE_PREAMBLE, (
            f"preamble must mention {mode_name!r} — without it the LLM "
            f"will hallucinate from training data residue (see CHANGELOG v3.2.0)"
        )


def test_preamble_disclaims_tdd_phases_as_modes() -> None:
    """RED / GREEN / REFACTOR are TDD phases inside the agent mode, not modes.

    The preamble must say so explicitly, otherwise the LLM defaults to
    listing them when asked about modes.
    """
    text = _LYRA_MODE_PREAMBLE.lower()
    # Must mention RED / GREEN / REFACTOR exists *somewhere* (so the
    # model knows they're a thing) AND must say they are NOT modes.
    assert "red" in text and "green" in text and "refactor" in text
    assert "opt-in plugin" in text or "not a separate mode" in text or "not a mode" in text
    # And must give the exact "always exactly four" anchor sentence so
    # the LLM has a hard-coded count to reach for.
    assert "exactly four" in text or "exactly 4" in text


def test_every_mode_prompt_carries_the_preamble() -> None:
    """All four mode-specific prompts inherit the 4-mode enumeration."""
    for mode_name, prompt in _MODE_SYSTEM_PROMPTS.items():
        assert _LYRA_MODE_PREAMBLE in prompt, (
            f"mode={mode_name!r} prompt missing preamble — the LLM will "
            f"hallucinate modes when this prompt is the active one"
        )


def test_no_mode_prompt_calls_tdd_phase_a_mode() -> None:
    """Defensive: no per-mode override accidentally re-introduces TDD-as-mode language."""
    bad_phrases = (
        "red mode", "green mode", "refactor mode",
        "build mode",  # legacy v2.x name; must be gone
    )
    for mode_name, prompt in _MODE_SYSTEM_PROMPTS.items():
        prompt_lower = prompt.lower()
        for bad in bad_phrases:
            assert bad not in prompt_lower, (
                f"mode={mode_name!r} prompt still contains {bad!r} — "
                f"this is the screenshot-bug regression"
            )


# ---------------------------------------------------------------------------
# Legacy alias remap — old user state must keep working post-upgrade
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "legacy,canonical",
    [
        ("build", "agent"),
        ("run", "agent"),
        ("explore", "ask"),
        ("retro", "debug"),
    ],
)
def test_legacy_mode_remap_at_construction(
    tmp_path: Path, legacy: str, canonical: str
) -> None:
    """Constructing with a v1.x / v2.x mode name canonicalises automatically."""
    s = InteractiveSession(repo_root=tmp_path, mode=legacy)
    assert s.mode == canonical, (
        f"legacy mode {legacy!r} must remap to {canonical!r} on boot — "
        f"otherwise old settings.json files break the user's session"
    )


def test_legacy_remap_table_covers_every_pre_v32_mode() -> None:
    """Sanity: the legacy table is comprehensive."""
    assert set(_LEGACY_MODE_REMAP.keys()) == {"build", "run", "explore", "retro"}
    # Every target must be a valid v3.2 mode.
    for legacy, canonical in _LEGACY_MODE_REMAP.items():
        assert canonical in _VALID_MODES


def test_slash_mode_accepts_legacy_alias_with_rename_notice(tmp_path: Path) -> None:
    """``/mode build`` switches to ``agent`` and tells the user about the rename."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_mode(s, "build")
    assert s.mode == "agent"
    assert result.new_mode == "agent"
    # The user gets a one-line "renamed in v3.2" notice so old muscle
    # memory doesn't silently land them in a different mode.
    assert "renamed" in result.output.lower() or "v3.2" in result.output


def test_slash_mode_rejects_unknown_string(tmp_path: Path) -> None:
    """A genuinely unknown mode name still surfaces a friendly error."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_mode(s, "wibble")
    # Mode unchanged.
    assert s.mode == "agent"
    # Error message lists the four canonical modes.
    out = result.output.lower()
    assert "unknown mode" in out
    for valid in _VALID_MODES:
        assert valid in result.output


def test_slash_mode_list_shows_exactly_four_modes(tmp_path: Path) -> None:
    """``/mode list`` lists exactly the 4 canonical modes."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_mode(s, "list")
    out = result.output
    for mode_name in _VALID_MODES:
        assert mode_name in out
    # Legacy names must not appear in the list.
    for legacy in _LEGACY_MODE_REMAP:
        # We check on a word boundary so "build" inside a blurb
        # ("default; full-access execution") would still pass — we
        # only fail if the legacy name shows up as a list entry.
        assert f"  {legacy:<6}" not in out and f"● {legacy:<6}" not in out


# ---------------------------------------------------------------------------
# Mode panel rendering: legacy color fall-throughs preserved
# ---------------------------------------------------------------------------


def test_chat_renderable_default_mode_is_agent() -> None:
    """``chat_renderable()`` with no mode kwarg defaults to agent panel colour."""
    from lyra_cli.interactive.output import chat_renderable

    panel = chat_renderable("hi")
    # Title contains "agent" (Rich markup is part of the title spec).
    title_str = str(panel.title)
    assert "agent" in title_str
