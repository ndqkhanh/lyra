"""Smoke tests for HUD system, modals, and integration modules.

Run: ``pytest tests/test_hud_modals.py -v``
"""
from __future__ import annotations

import pytest

# ── HUD tests ─────────────────────────────────────────────────────────

class TestHUD:
    def test_hud_imports(self):
        from lyra_cli.hud import (
            available_presets,
            load_preset,
        )
        assert available_presets() == ["minimal", "compact", "full", "wide"]
        cfg = load_preset("compact")
        assert cfg.sections == ["model", "tokens", "agents"]

    def test_hud_state(self):
        from lyra_cli.hud import HudState
        state = HudState(model="test-model", tokens_used=50000, tokens_max=200000, turn=5)
        assert state.model == "test-model"
        assert state.tokens_used == 50000

    def test_hud_render(self):
        from lyra_cli.hud import HudState, render
        state = HudState(model="deepseek", tokens_used=45678, tokens_max=200000, turn=12)
        rendered = render(state)
        assert "deepseek" in rendered
        assert "45678" in rendered or "45" in rendered

    def test_hud_render_inline(self):
        from lyra_cli.hud import HudState, render_inline
        state = HudState(model="gpt-4o", tokens_used=10000, tokens_max=200000, turn=3, agent_running=2)
        line = render_inline(state)
        assert "gpt-4o" in line
        assert "T#3" in line

    def test_hud_testing(self):
        from lyra_cli.hud.testing import sample_state
        state = sample_state()
        assert state.model == "deepseek-chat"
        assert state.tokens_used == 45678
        assert state.agent_count == 4

    def test_hud_presets_loaded(self):
        from lyra_cli.hud import load_preset
        for name in ("minimal", "compact", "full", "wide"):
            cfg = load_preset(name)
            assert len(cfg.sections) > 0

    def test_hud_all_sections(self):
        from lyra_cli.hud import load_preset, render
        from lyra_cli.hud.testing import sample_state
        state = sample_state()
        for name in ("minimal", "compact", "full", "wide"):
            cfg = load_preset(name)
            rendered = render(state, cfg)
            assert rendered is not None


# ── Theme manager tests ──────────────────────────────────────────────

class TestThemeManager:
    def test_theme_presets(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.theme_manager import ThemePreset
        assert len(list(ThemePreset)) >= 9

    def test_theme_manager_imports(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.theme_manager import (
            ThemePreset,
            get_theme_manager,
        )
        mgr = get_theme_manager()
        assert mgr.current_preset == ThemePreset.DEFAULT

    def test_theme_switching(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
        mgr = ThemeManager()
        mgr.set_theme_from_preset(ThemePreset.DRACULA)
        assert mgr.current_preset == ThemePreset.DRACULA
        colors = mgr.get_colors()
        assert colors.primary is not None

    def test_theme_list(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.theme_manager import ThemeManager
        mgr = ThemeManager()
        themes = mgr.list_themes()
        assert "dracula" in themes
        assert "default" in themes

    def test_theme_colors(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.theme_manager import ThemeColors
        c = ThemeColors(primary="red", secondary="blue")
        assert c.primary == "red"
        assert c.secondary == "blue"


# ── Modal smoke tests ─────────────────────────────────────────────────

class TestModals:
    def test_session_manager_imports(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.modals.session_manager import SessionEntry
        entry = SessionEntry(session_id="s1", title="Test session", model="gpt-4o")
        assert "Test session" in entry.summary
        assert entry.model == "gpt-4o"

    def test_notification_drawer_imports(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.modals.notification_drawer import (
            NotificationEntry,
        )
        n = NotificationEntry(level="info", title="Test notification")
        assert "ℹ" in n.glyph
        assert n.level == "info"

    def test_theme_switcher_imports(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.modals.theme_switcher import ThemeSwitcherModal
        assert ThemeSwitcherModal is not None

    def test_status_dashboard_imports(self):
        pytest.importorskip("textual", reason="textual not installed")
        from lyra_cli.tui_v2.modals.status_dashboard import StatusDashboardModal
        modal = StatusDashboardModal(snapshot={"model_name": "test"})
        assert modal.model_name == "test"


# ── Tool Approval Viz tests ──────────────────────────────────────────

class TestToolApproval:
    def test_approval_request(self):
        from lyra_cli.interactive.tool_approval_viz import ApprovalRequest
        req = ApprovalRequest.from_tool_call("Bash", {"command": "ls -la"})
        assert req.tool_name == "Bash"
        assert req.risk_level in ("low", "medium", "high")

    def test_risk_classification(self):
        from lyra_cli.interactive.tool_approval_viz import classify_risk
        # Actual classification per tool_approval_viz.py risk tables
        assert classify_risk("Read") == "low"        # in LOW_RISK_TOOLS
        assert classify_risk("Bash") == "low"         # in LOW_RISK_TOOLS
        assert classify_risk("Edit") == "medium"      # in MEDIUM_RISK_TOOLS
        assert classify_risk("Deploy") == "high"      # in HIGH_RISK_TOOLS
        assert classify_risk("UnknownTool") == "medium"  # default fallback

    def test_approval_panel_renders(self):
        from lyra_cli.interactive.tool_approval_viz import (
            ApprovalRequest,
            render_approval_panel,
        )
        req = ApprovalRequest(tool_name="Read", risk_level="low")
        panel = render_approval_panel(req)
        assert panel is not None

    def test_approval_summary(self):
        from lyra_cli.interactive.tool_approval_viz import render_approval_summary
        panel = render_approval_summary({"Bash": "allow", "Write": "deny"})
        assert panel is not None


# ── Profile system tests ─────────────────────────────────────────────

class TestProfile:
    def test_profile_defaults(self):
        from lyra_cli.interactive.profile_cmd import LyraProfile
        p = LyraProfile()
        assert p.technical_level in ("beginner", "intermediate", "advanced", "expert")
        assert p.verbosity == "balanced"

    def test_profile_summary(self):
        from lyra_cli.interactive.profile_cmd import LyraProfile
        p = LyraProfile(name="Test User", domains=["python", "typescript"])
        summary = p.summary()
        assert "Test User" in summary
        assert "python" in summary

    def test_profile_render(self):
        from lyra_cli.interactive.profile_cmd import LyraProfile
        p = LyraProfile(name="Dev")
        rendered = p.render()
        assert "Dev" in rendered
