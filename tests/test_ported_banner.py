"""Port of lyra-ui tests/test_banner.py → tests TUI claude_banner.py + onboarding_panel.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_banner_expand_collapse():
    from lyra_cli.tui_v2.widgets.claude_banner import ClaudeStyleBannerWidget
    b = ClaudeStyleBannerWidget()
    assert b.expanded is True
    b.action_toggle_banner()
    assert b.expanded is False
    b.action_toggle_banner()
    assert b.expanded is True


def test_banner_tip_rotation():
    from lyra_cli.tui_v2.widgets.claude_banner import ClaudeStyleBannerWidget
    b = ClaudeStyleBannerWidget()
    old = b._tip_index
    b.rotate_tip()
    assert b._tip_index == (old + 1)


def test_banner_truncate():
    from lyra_cli.tui_v2.widgets.claude_banner import ClaudeStyleBannerWidget
    assert ClaudeStyleBannerWidget._truncate("short", 50) == "short"
    result = ClaudeStyleBannerWidget._truncate("a" * 100, 40)
    assert len(result) <= 40
    assert result.startswith("…")


def test_onboarding_expand():
    from lyra_cli.tui_v2.widgets.onboarding_panel import OnboardingWidget
    o = OnboardingWidget()
    assert o.expanded is True
    o.action_dismiss()
    assert o.expanded is False


def test_onboarding_tip():
    from lyra_cli.tui_v2.widgets.onboarding_panel import OnboardingWidget
    o = OnboardingWidget()
    old = o._tip_index
    o.rotate_tip()
    assert o._tip_index == (old + 1) % 5
