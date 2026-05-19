"""
Tests for Theme Manager (Funny Sounds Phase 0)

Tests sound theme management.
"""

import pytest
from pathlib import Path
from lyra_research.sounds.theme_manager import ThemeManager, SoundTheme


class TestThemeManager:
    """Test theme manager"""

    def test_load_builtin_themes(self):
        """Test loading built-in themes"""
        manager = ThemeManager()
        themes = manager.themes

        assert "warcraft" in themes
        assert "aoe" in themes
        assert "memes" in themes
        assert "minimal" in themes

    def test_get_theme(self):
        """Test getting theme by name"""
        manager = ThemeManager()

        warcraft = manager.get_theme("warcraft")
        assert warcraft is not None
        assert warcraft.name == "warcraft"
        assert "Warcraft III" in warcraft.description

    def test_get_nonexistent_theme(self):
        """Test getting non-existent theme"""
        manager = ThemeManager()
        theme = manager.get_theme("nonexistent")
        assert theme is None

    def test_list_themes(self):
        """Test listing available themes"""
        manager = ThemeManager()
        themes = manager.list_themes()

        assert len(themes) == 4
        assert "warcraft" in themes
        assert "aoe" in themes
        assert "memes" in themes
        assert "minimal" in themes

    def test_get_sound_path(self):
        """Test getting sound file path"""
        manager = ThemeManager()

        path = manager.get_sound_path("warcraft", "task_complete")
        assert path is not None
        assert "warcraft" in str(path)
        assert "job_done.mp3" in str(path)

    def test_get_sound_path_missing_theme(self):
        """Test getting sound path for missing theme"""
        manager = ThemeManager()
        path = manager.get_sound_path("nonexistent", "task_complete")
        assert path is None

    def test_get_sound_path_missing_event(self):
        """Test getting sound path for missing event"""
        manager = ThemeManager()
        path = manager.get_sound_path("warcraft", "nonexistent_event")
        assert path is None

    def test_warcraft_theme_sounds(self):
        """Test Warcraft theme has expected sounds"""
        manager = ThemeManager()
        warcraft = manager.get_theme("warcraft")

        assert "session_start" in warcraft.sounds
        assert "task_complete" in warcraft.sounds
        assert "error" in warcraft.sounds
        assert "milestone" in warcraft.sounds

    def test_aoe_theme_sounds(self):
        """Test Age of Empires theme has expected sounds"""
        manager = ThemeManager()
        aoe = manager.get_theme("aoe")

        assert "session_start" in aoe.sounds
        assert "task_complete" in aoe.sounds
        assert "compact" in aoe.sounds

    def test_memes_theme_sounds(self):
        """Test memes theme has expected sounds"""
        manager = ThemeManager()
        memes = manager.get_theme("memes")

        assert "session_start" in memes.sounds
        assert "task_complete" in memes.sounds
        assert "error" in memes.sounds

    def test_minimal_theme_sounds(self):
        """Test minimal theme has expected sounds"""
        manager = ThemeManager()
        minimal = manager.get_theme("minimal")

        assert "session_start" in minimal.sounds
        assert "task_complete" in minimal.sounds
        assert "error" in minimal.sounds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
