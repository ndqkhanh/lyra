"""Port of lyra-ui tests/test_ui.py → tests TUI Rich console and HUD system.

Original tested RichConsole singleton, Spinner, ProgressManager.
Our TUI equivalents: theme_manager.py (Rich integration), HUD, progress widgets.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_rich_theme_bridge():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    mgr = ThemeManager()
    for preset in ThemePreset:
        theme = mgr.to_rich_theme(preset)
        assert theme is not None


def test_animation_effects():
    from lyra_cli.tui_v2.theme_manager import AnimationEffects
    anim = AnimationEffects()
    anim.typing_indicator("Testing")
    anim.success_animation("Done")
    anim.error_animation("Failed")
    anim.pulse_effect("Pulse test")
    assert anim is not None


def test_threshold_colour():
    from lyra_cli.tui_v2.theme_manager import threshold_colour
    assert "green" in threshold_colour(10)
    assert "yellow" in threshold_colour(60)
    assert "orange1" in threshold_colour(85)
    assert "red" in threshold_colour(95)


def test_hud_model_panel():
    from lyra_cli.hud import HudState, load_preset, render
    from lyra_cli.hud.testing import sample_state
    state = sample_state()
    cfg = load_preset("compact")
    rendered = render(state, cfg)
    assert "deepseek" in rendered


def test_hud_tokens_panel():
    from lyra_cli.hud import HudState, load_preset, render
    state = HudState(model="test", tokens_used=50000, tokens_max=200000)
    cfg = load_preset("compact")
    rendered = render(state, cfg)
    assert "50.0K" in rendered or "50000" in rendered


def test_hud_error_state():
    from lyra_cli.hud import HudState, load_preset, render
    state = HudState(model="", tokens_used=0, tokens_max=200000)
    cfg = load_preset("compact")
    rendered = render(state, cfg)
    assert rendered is not None


def test_hud_all_presets():
    from lyra_cli.hud import HudState, load_preset, render
    from lyra_cli.hud.testing import sample_state
    state = sample_state()
    for name in ("minimal", "compact", "full", "wide"):
        cfg = load_preset(name)
        rendered = render(state, cfg)
        assert rendered is not None


def test_hud_inline():
    from lyra_cli.hud import HudState, render_inline
    state = HudState(model="gpt-4o", tokens_used=25000, tokens_max=200000, turn=7)
    line = render_inline(state)
    assert "gpt-4o" in line
    assert "T#7" in line


def test_welcome_card_widget_init():
    from lyra_cli.tui_v2.widgets.welcome_card import WelcomeCard
    card = WelcomeCard()
    assert card.expanded is True
    assert card.model == "claude-sonnet-4-6"


def test_welcome_card_toggle():
    from lyra_cli.tui_v2.widgets.welcome_card import WelcomeCard
    card = WelcomeCard()
    card.action_toggle_expand()
    assert card.expanded is False


def test_progress_spinner():
    from lyra_cli.tui_v2.widgets.progress_spinner import ProgressSpinner
    spinner = ProgressSpinner()
    spinner.start()
    frame = spinner.next_frame()
    assert frame is not None
    assert len(frame) > 0
    spinner.stop()
    assert spinner.start_time is None


def test_progress_spinner_multi_agent():
    from lyra_cli.tui_v2.widgets.progress_spinner import ProgressSpinner
    spinner = ProgressSpinner()
    spinner.start()
    spinner.register_agent("a1")
    spinner.register_agent("a2")
    assert spinner.agent_count == 2

    frame = spinner.next_frame(agent_id="a1")
    assert "a1" in frame

    spinner.unregister_agent("a1")
    assert spinner.agent_count == 1
