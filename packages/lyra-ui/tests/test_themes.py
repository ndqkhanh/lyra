"""Tests for theme system."""

from lyra_ui import (
    AnimationEffects,
    ThemeColors,
    ThemeManager,
    ThemeName,
)

# Theme Manager Tests


def test_theme_manager_init():
    """Test theme manager initialization."""
    manager = ThemeManager()
    assert manager.console is not None
    assert manager.current_theme == ThemeName.DEFAULT
    assert len(manager.themes) > 0


def test_get_theme():
    """Test getting theme."""
    manager = ThemeManager()
    theme = manager.get_theme(ThemeName.DEFAULT)
    assert theme is not None
    assert isinstance(theme, ThemeColors)


def test_get_all_builtin_themes():
    """Test getting all built-in themes."""
    manager = ThemeManager()

    themes = [
        ThemeName.DEFAULT,
        ThemeName.DARK,
        ThemeName.LIGHT,
        ThemeName.SOLARIZED_DARK,
        ThemeName.SOLARIZED_LIGHT,
        ThemeName.DRACULA,
        ThemeName.MONOKAI,
        ThemeName.NORD,
        ThemeName.GRUVBOX,
    ]

    for theme_name in themes:
        theme = manager.get_theme(theme_name)
        assert theme is not None
        assert theme.primary is not None
        assert theme.success is not None
        assert theme.error is not None


def test_set_theme():
    """Test setting theme."""
    manager = ThemeManager()
    manager.set_theme(ThemeName.DRACULA)
    assert manager.current_theme == ThemeName.DRACULA


def test_get_current_theme():
    """Test getting current theme."""
    manager = ThemeManager()
    manager.set_theme(ThemeName.NORD)
    theme = manager.get_current_theme()
    assert theme is not None
    assert theme == manager.get_theme(ThemeName.NORD)


def test_create_custom_theme():
    """Test creating custom theme."""
    manager = ThemeManager()
    colors = ThemeColors(
        primary="cyan",
        secondary="blue",
        success="green",
        warning="yellow",
        error="red",
        info="cyan",
        background="black",
        foreground="white",
        dim="dim white",
        bright="bright_white",
    )
    manager.create_custom_theme("my_theme", colors)
    assert "my_theme" in manager.custom_themes


def test_get_custom_theme():
    """Test getting custom theme."""
    manager = ThemeManager()
    colors = ThemeColors(
        primary="magenta",
        secondary="cyan",
        success="green",
        warning="yellow",
        error="red",
        info="cyan",
        background="black",
        foreground="white",
        dim="dim white",
        bright="bright_white",
    )
    manager.create_custom_theme("custom", colors)

    retrieved = manager.get_custom_theme("custom")
    assert retrieved is not None
    assert retrieved.primary == "magenta"


def test_list_themes():
    """Test listing themes."""
    manager = ThemeManager()
    themes = manager.list_themes()
    assert len(themes) > 0
    assert "default" in themes


def test_list_themes_with_custom():
    """Test listing themes with custom themes."""
    manager = ThemeManager()
    colors = ThemeColors(
        primary="cyan",
        secondary="blue",
        success="green",
        warning="yellow",
        error="red",
        info="cyan",
        background="black",
        foreground="white",
        dim="dim white",
        bright="bright_white",
    )
    manager.create_custom_theme("custom1", colors)
    manager.create_custom_theme("custom2", colors)

    themes = manager.list_themes()
    assert "custom1" in themes
    assert "custom2" in themes


def test_preview_theme():
    """Test previewing theme."""
    manager = ThemeManager()
    # Should not raise error
    manager.preview_theme(ThemeName.DRACULA)


def test_export_theme():
    """Test exporting theme."""
    manager = ThemeManager()
    theme_dict = manager.export_theme(ThemeName.DEFAULT)
    assert isinstance(theme_dict, dict)
    assert "primary" in theme_dict
    assert "success" in theme_dict
    assert "error" in theme_dict


def test_import_theme():
    """Test importing theme."""
    manager = ThemeManager()
    theme_dict = {
        "primary": "cyan",
        "secondary": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "cyan",
        "background": "black",
        "foreground": "white",
        "dim": "dim white",
        "bright": "bright_white",
    }
    manager.import_theme("imported", theme_dict)
    assert "imported" in manager.custom_themes


def test_to_rich_theme():
    """Test converting to Rich theme."""
    manager = ThemeManager()
    rich_theme = manager.to_rich_theme(ThemeName.DEFAULT)
    assert rich_theme is not None


def test_theme_colors():
    """Test theme colors dataclass."""
    colors = ThemeColors(
        primary="cyan",
        secondary="blue",
        success="green",
        warning="yellow",
        error="red",
        info="cyan",
        background="black",
        foreground="white",
        dim="dim white",
        bright="bright_white",
    )
    assert colors.primary == "cyan"
    assert colors.success == "green"
    assert colors.error == "red"


# Animation Effects Tests


def test_animation_effects_init():
    """Test animation effects initialization."""
    effects = AnimationEffects()
    assert effects.console is not None


def test_typing_indicator():
    """Test typing indicator."""
    effects = AnimationEffects()
    # Should not raise error
    effects.typing_indicator("Typing")


def test_pulse_effect():
    """Test pulse effect."""
    effects = AnimationEffects()
    # Should not raise error
    effects.pulse_effect("Processing")


def test_pulse_effect_with_color():
    """Test pulse effect with custom color."""
    effects = AnimationEffects()
    # Should not raise error
    effects.pulse_effect("Processing", color="green")


def test_loading_spinner():
    """Test loading spinner."""
    effects = AnimationEffects()
    # Should not raise error
    effects.loading_spinner("Loading")


def test_success_animation():
    """Test success animation."""
    effects = AnimationEffects()
    # Should not raise error
    effects.success_animation("Task completed")


def test_error_animation():
    """Test error animation."""
    effects = AnimationEffects()
    # Should not raise error
    effects.error_animation("Task failed")


# Integration Tests


def test_theme_switching():
    """Test switching between themes."""
    manager = ThemeManager()

    themes = [
        ThemeName.DEFAULT,
        ThemeName.DARK,
        ThemeName.LIGHT,
        ThemeName.DRACULA,
        ThemeName.NORD,
    ]

    for theme_name in themes:
        manager.set_theme(theme_name)
        assert manager.current_theme == theme_name
        theme = manager.get_current_theme()
        assert theme is not None


def test_custom_theme_workflow():
    """Test complete custom theme workflow."""
    manager = ThemeManager()

    # Create custom theme
    colors = ThemeColors(
        primary="#00ff00",
        secondary="#0000ff",
        success="#00ff00",
        warning="#ffff00",
        error="#ff0000",
        info="#00ffff",
        background="#000000",
        foreground="#ffffff",
        dim="#808080",
        bright="#ffffff",
    )
    manager.create_custom_theme("matrix", colors)

    # Verify it exists
    assert "matrix" in manager.custom_themes

    # Get it
    retrieved = manager.get_custom_theme("matrix")
    assert retrieved is not None
    assert retrieved.primary == "#00ff00"

    # Export it
    exported = manager.export_theme(ThemeName.DEFAULT)
    assert isinstance(exported, dict)

    # Import as new theme
    manager.import_theme("matrix_copy", exported)
    assert "matrix_copy" in manager.custom_themes


def test_theme_export_import_roundtrip():
    """Test theme export/import roundtrip."""
    manager = ThemeManager()

    # Export theme
    exported = manager.export_theme(ThemeName.DRACULA)

    # Import as custom theme
    manager.import_theme("dracula_copy", exported)

    # Verify
    original = manager.get_theme(ThemeName.DRACULA)
    copy = manager.get_custom_theme("dracula_copy")

    assert copy is not None
    assert copy.primary == original.primary
    assert copy.success == original.success
    assert copy.error == original.error


def test_animation_effects_workflow():
    """Test complete animation effects workflow."""
    effects = AnimationEffects()

    # Show loading
    effects.loading_spinner("Loading data")

    # Show typing
    effects.typing_indicator("Agent is thinking")

    # Show pulse
    effects.pulse_effect("Processing", color="cyan")

    # Show success
    effects.success_animation("Task completed successfully")

    # Show error
    effects.error_animation("Task failed with error")


def test_all_builtin_themes_valid():
    """Test all built-in themes are valid."""
    manager = ThemeManager()

    for theme_name in ThemeName:
        theme = manager.get_theme(theme_name)
        assert theme is not None
        assert theme.primary is not None
        assert theme.secondary is not None
        assert theme.success is not None
        assert theme.warning is not None
        assert theme.error is not None
        assert theme.info is not None
        assert theme.background is not None
        assert theme.foreground is not None
        assert theme.dim is not None
        assert theme.bright is not None
