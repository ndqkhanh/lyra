"""Tests for lyra_core.config feature flags."""


def test_process_transparency_enabled_by_default():
    """Process transparency should be enabled by default."""
    from lyra_core.config import LYRA_ENABLE_PROCESS_TRANSPARENCY
    assert LYRA_ENABLE_PROCESS_TRANSPARENCY is True


def test_process_transparency_can_be_disabled(monkeypatch):
    """Process transparency can be disabled via env var."""
    monkeypatch.setenv("LYRA_ENABLE_PROCESS_TRANSPARENCY", "false")
    # Re-import to pick up new env var
    import importlib

    import lyra_core.config
    importlib.reload(lyra_core.config)
    from lyra_core.config import LYRA_ENABLE_PROCESS_TRANSPARENCY
    assert LYRA_ENABLE_PROCESS_TRANSPARENCY is False


def test_sub_flags_follow_master_flag(monkeypatch):
    """Sub-flags should follow master flag when master is disabled."""
    monkeypatch.setenv("LYRA_ENABLE_PROCESS_TRANSPARENCY", "false")
    import importlib

    import lyra_core.config
    importlib.reload(lyra_core.config)
    from lyra_core.config import (
        LYRA_ENABLE_AGENT_PANEL,
        LYRA_ENABLE_EVENT_BUS,
        LYRA_ENABLE_EVENT_STORE,
        LYRA_ENABLE_PROCESS_STATE_WRITER,
    )
    assert LYRA_ENABLE_EVENT_BUS is False
    assert LYRA_ENABLE_EVENT_STORE is False
    assert LYRA_ENABLE_PROCESS_STATE_WRITER is False
    assert LYRA_ENABLE_AGENT_PANEL is False


def test_legacy_tui_disabled_by_default():
    """Legacy TUI should be disabled by default (use TUI v2)."""
    from lyra_core.config import LYRA_LEGACY_TUI
    assert LYRA_LEGACY_TUI is False


def test_legacy_tui_can_be_enabled(monkeypatch):
    """Legacy TUI can be enabled for rollback."""
    monkeypatch.setenv("LYRA_LEGACY_TUI", "true")
    import importlib

    import lyra_core.config
    importlib.reload(lyra_core.config)
    from lyra_core.config import LYRA_LEGACY_TUI
    assert LYRA_LEGACY_TUI is True


def test_tui_refresh_rate_default():
    """TUI refresh rate should default to 30 FPS."""
    from lyra_core.config import LYRA_TUI_REFRESH_RATE
    assert LYRA_TUI_REFRESH_RATE == 30.0


def test_tui_refresh_rate_can_be_tuned(monkeypatch):
    """TUI refresh rate can be tuned via env var."""
    monkeypatch.setenv("LYRA_TUI_REFRESH_RATE", "60.0")
    import importlib

    import lyra_core.config
    importlib.reload(lyra_core.config)
    from lyra_core.config import LYRA_TUI_REFRESH_RATE
    assert LYRA_TUI_REFRESH_RATE == 60.0


def test_event_queue_max_size_default():
    """Event queue should default to 1000 events."""
    from lyra_core.config import LYRA_EVENT_QUEUE_MAX_SIZE
    assert LYRA_EVENT_QUEUE_MAX_SIZE == 1000


def test_context_optimization_enabled_by_default():
    """Context optimization should be enabled by default."""
    from lyra_core.config import LYRA_ENABLE_CONTEXT_OPTIMIZATION
    assert LYRA_ENABLE_CONTEXT_OPTIMIZATION is True
