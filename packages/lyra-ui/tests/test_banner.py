"""Tests for banner system."""

from lyra_ui import (
    BannerStats,
    BannerStyle,
    BannerSystem,
    BannerTheme,
    ShutdownBanner,
    StartupBanner,
)


# Banner System Tests


def test_banner_system_init():
    """Test banner system initialization."""
    banner = BannerSystem()
    assert banner.console is not None
    assert banner.style == BannerStyle.STANDARD
    assert banner.theme == BannerTheme.DEFAULT


def test_banner_system_custom_style():
    """Test banner system with custom style."""
    banner = BannerSystem(style=BannerStyle.MINIMAL)
    assert banner.style == BannerStyle.MINIMAL


def test_banner_system_custom_theme():
    """Test banner system with custom theme."""
    banner = BannerSystem(theme=BannerTheme.DRACULA)
    assert banner.theme == BannerTheme.DRACULA


def test_render_minimal_banner():
    """Test rendering minimal banner."""
    banner = BannerSystem(style=BannerStyle.MINIMAL)
    panel = banner.render(title="Test")
    assert panel is not None


def test_render_standard_banner():
    """Test rendering standard banner."""
    banner = BannerSystem(style=BannerStyle.STANDARD)
    panel = banner.render(
        title="Test",
        subtitle="Subtitle",
        status="Running",
    )
    assert panel is not None


def test_render_full_banner():
    """Test rendering full banner."""
    banner = BannerSystem(style=BannerStyle.FULL)
    stats = BannerStats(
        tokens_used=1000,
        total_cost=0.05,
        elapsed_time=10.5,
        agents_active=3,
    )
    panel = banner.render(
        title="Test",
        subtitle="Subtitle",
        status="Running",
        stats=stats,
    )
    assert panel is not None


def test_set_style():
    """Test setting banner style."""
    banner = BannerSystem()
    banner.set_style(BannerStyle.FULL)
    assert banner.style == BannerStyle.FULL


def test_set_theme():
    """Test setting banner theme."""
    banner = BannerSystem()
    banner.set_theme(BannerTheme.SOLARIZED)
    assert banner.theme == BannerTheme.SOLARIZED


def test_display_banner():
    """Test displaying banner."""
    banner = BannerSystem()
    # Should not raise error
    banner.display(title="Test")


def test_banner_stats():
    """Test banner stats."""
    stats = BannerStats(
        tokens_used=5000,
        total_cost=0.25,
        elapsed_time=30.0,
        agents_active=5,
    )
    assert stats.tokens_used == 5000
    assert stats.total_cost == 0.25
    assert stats.elapsed_time == 30.0
    assert stats.agents_active == 5


# Startup Banner Tests


def test_startup_banner_init():
    """Test startup banner initialization."""
    banner = StartupBanner()
    assert banner.console is not None


def test_startup_banner_display():
    """Test startup banner display."""
    banner = StartupBanner()
    # Should not raise error
    banner.display(version="1.0.0", loading_message="Starting...")


# Shutdown Banner Tests


def test_shutdown_banner_init():
    """Test shutdown banner initialization."""
    banner = ShutdownBanner()
    assert banner.console is not None


def test_shutdown_banner_display():
    """Test shutdown banner display."""
    banner = ShutdownBanner()
    # Should not raise error
    banner.display(tasks_completed=10, total_time=120.5)


# Integration Tests


def test_banner_style_switching():
    """Test switching banner styles."""
    banner = BannerSystem()

    # Minimal
    banner.set_style(BannerStyle.MINIMAL)
    panel = banner.render(title="Test")
    assert panel is not None

    # Standard
    banner.set_style(BannerStyle.STANDARD)
    panel = banner.render(title="Test", subtitle="Subtitle")
    assert panel is not None

    # Full
    banner.set_style(BannerStyle.FULL)
    stats = BannerStats(tokens_used=1000)
    panel = banner.render(title="Test", stats=stats)
    assert panel is not None


def test_banner_theme_switching():
    """Test switching banner themes."""
    banner = BannerSystem()

    themes = [
        BannerTheme.DEFAULT,
        BannerTheme.DARK,
        BannerTheme.LIGHT,
        BannerTheme.SOLARIZED,
        BannerTheme.DRACULA,
    ]

    for theme in themes:
        banner.set_theme(theme)
        panel = banner.render(title="Test")
        assert panel is not None


def test_complete_banner_workflow():
    """Test complete banner workflow."""
    # Startup
    startup = StartupBanner()
    startup.display(version="1.0.0")

    # Main banner
    banner = BannerSystem(style=BannerStyle.FULL, theme=BannerTheme.DRACULA)
    stats = BannerStats(
        tokens_used=10000,
        total_cost=0.50,
        elapsed_time=60.0,
        agents_active=3,
    )
    banner.display(
        title="Lyra",
        subtitle="AI Research Agent",
        status="Processing",
        stats=stats,
    )

    # Shutdown
    shutdown = ShutdownBanner()
    shutdown.display(tasks_completed=5, total_time=60.0)
