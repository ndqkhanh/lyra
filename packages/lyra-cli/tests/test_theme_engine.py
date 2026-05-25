"""Tests for Theme, ThemeEngine, and BUILTIN_THEMES."""

import json
import tempfile
from pathlib import Path

from lyra_cli.theme_engine import (
    BUILTIN_THEMES,
    Theme,
    ThemeEngine,
    get_theme_engine,
)


class TestTheme:
    def test_default_values(self):
        t = Theme(name="test", description="a test theme")
        assert t.name == "test"
        assert t.description == "a test theme"
        assert t.variant == "dark"
        assert t.primary == "cyan"
        assert t.secondary == "magenta"

    def test_to_dict_roundtrip(self):
        t = Theme(
            name="custom",
            description="custom theme",
            variant="light",
            primary="blue",
            secondary="green",
            success="bright_green",
            warning="bright_yellow",
            error="bright_red",
            dim="bright_black",
            highlight="bold white",
            bg="white",
            fg="black",
            accent="blue",
            muted="bright_black",
            border="yellow",
            status_ok="bright_green",
            status_warn="bright_yellow",
            status_err="bright_red",
            link="blue",
            code_bg="bright_black",
            quote="green",
            heading="bold blue",
        )
        data = t.to_dict()
        t2 = Theme.from_dict(data)
        assert t2.name == "custom"
        assert t2.variant == "light"
        assert t2.primary == "blue"
        assert t2.secondary == "green"

    def test_to_dict_has_colors(self):
        t = Theme(name="test", description="desc")
        data = t.to_dict()
        assert "colors" in data
        assert data["colors"]["primary"] == "cyan"

    def test_from_dict_minimal(self):
        data = {"name": "minimal"}
        t = Theme.from_dict(data)
        assert t.name == "minimal"
        assert t.variant == "dark"

    def test_from_dict_partial_colors(self):
        data = {"name": "partial", "colors": {"primary": "red"}}
        t = Theme.from_dict(data)
        assert t.primary == "red"
        assert t.secondary == "magenta"

    def test_metadata_field(self):
        t = Theme(name="test", description="desc", metadata={"source": "custom"})
        assert t.metadata["source"] == "custom"


class TestBuiltinThemes:
    def test_all_builtins_are_themes(self):
        for name, theme in BUILTIN_THEMES.items():
            assert isinstance(theme, Theme)
            assert theme.name == name

    def test_dark_themes(self):
        dark = ["dracula", "tokyo-night", "catppuccin", "gruvbox"]
        for name in dark:
            assert BUILTIN_THEMES[name].variant == "dark"

    def test_light_themes(self):
        light = ["nord-light", "github-light"]
        for name in light:
            assert BUILTIN_THEMES[name].variant == "light"

    def test_colorblind_themes(self):
        cb = ["cb-blue", "cb-viridis"]
        for name in cb:
            assert BUILTIN_THEMES[name].variant == "colorblind"

    def test_lyra_signature_themes(self):
        sig = ["lyra-aurora", "lyra-crimson", "lyra-ocean", "lyra-ember"]
        for name in sig:
            assert BUILTIN_THEMES[name].variant == "dark"
            assert BUILTIN_THEMES[name].metadata.get("series") == "lyra-signature"

    def test_has_12_builtin_themes(self):
        assert len(BUILTIN_THEMES) == 12


class TestThemeEngine:
    def test_initial_state(self):
        engine = ThemeEngine()
        assert engine.current.name == "lyra-aurora"

    def test_apply_valid_theme(self):
        engine = ThemeEngine()
        assert engine.apply("dracula") is True
        assert engine.current.name == "dracula"

    def test_apply_invalid_theme(self):
        engine = ThemeEngine()
        assert engine.apply("nonexistent") is False
        assert engine.current.name == "lyra-aurora"

    def test_theme_names_sorted(self):
        engine = ThemeEngine()
        names = engine.theme_names
        assert "dracula" in names
        assert "lyra-aurora" in names

    def test_variant_groups(self):
        engine = ThemeEngine()
        groups = engine.variant_groups
        assert "dark" in groups
        assert "light" in groups
        assert "colorblind" in groups
        assert len(groups["dark"]) > 0

    def test_register_new_theme(self):
        engine = ThemeEngine()
        t = Theme(name="my-theme", description="custom", variant="dark")
        engine.register(t)
        assert "my-theme" in engine.theme_names
        assert engine.apply("my-theme") is True

    def test_reset_to_default(self):
        engine = ThemeEngine()
        engine.apply("tokyo-night")
        engine.reset()
        assert engine.current.name == "lyra-aurora"

    def test_export_current(self):
        engine = ThemeEngine()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "theme.json"
            engine.export_current(path)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["name"] == "lyra-aurora"

    def test_preview_returns_string(self):
        engine = ThemeEngine()
        preview = engine.preview("dracula")
        assert "dracula" in preview.lower()
        assert len(preview) > 0

    def test_preview_unknown_theme(self):
        engine = ThemeEngine()
        preview = engine.preview("nonexistent")
        assert "nonexistent" in preview


class TestGetThemeEngine:
    def test_returns_singleton(self):
        e1 = get_theme_engine()
        e2 = get_theme_engine()
        assert e1 is e2
