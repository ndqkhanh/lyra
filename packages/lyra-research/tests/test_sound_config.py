"""
Tests for Sound Config (Funny Sounds Phase 0)

Tests sound configuration management.
"""

import tempfile
from pathlib import Path

import pytest
from lyra_research.sounds.config import SoundConfig


class TestSoundConfig:
    """Test sound configuration"""

    def test_default_values(self):
        """Test default configuration values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)

            assert config.enabled is True
            assert config.theme == "warcraft"
            assert config.volume == 0.5
            assert config.adaptive_volume is False
            assert config.context_aware is False
            assert config.productivity_mode is False

    def test_save_and_load(self):
        """Test saving and loading configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"

            # Create and save config
            config1 = SoundConfig(config_path)
            config1.enabled = False
            config1.theme = "aoe"
            config1.volume = 0.8
            config1.save()

            # Load config
            config2 = SoundConfig(config_path)
            assert config2.enabled is False
            assert config2.theme == "aoe"
            assert config2.volume == 0.8

    def test_config_persistence(self):
        """Test config persists across instances"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"

            # Create and modify config
            config1 = SoundConfig(config_path)
            config1.adaptive_volume = True
            config1.context_aware = True
            config1.save()

            # Create new instance
            config2 = SoundConfig(config_path)
            assert config2.adaptive_volume is True
            assert config2.context_aware is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
