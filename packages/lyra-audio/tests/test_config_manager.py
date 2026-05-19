"""Tests for configuration manager."""

import json
import tempfile
from pathlib import Path

from lyra_audio.config_manager import ConfigurationManager


def test_config_manager_init():
    """Test configuration manager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))
        assert manager.config is not None


def test_config_manager_default_config():
    """Test default configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))

        assert manager.get("enabled") is True
        assert manager.get("theme") == "warcraft"
        assert manager.get("volume") == 0.7


def test_config_manager_get_set():
    """Test get and set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))

        manager.set("volume", 0.5)
        assert manager.get("volume") == 0.5


def test_config_manager_nested_get_set():
    """Test nested get and set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))

        manager.set("adaptive_volume.enabled", False)
        assert manager.get("adaptive_volume.enabled") is False


def test_config_manager_save_load():
    """Test save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))

        manager.set("theme", "glados")
        manager.save()

        # Load again
        manager2 = ConfigurationManager(str(config_path))
        assert manager2.get("theme") == "glados"


def test_config_manager_reset():
    """Test reset to defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        manager = ConfigurationManager(str(config_path))

        manager.set("theme", "custom")
        manager.reset()

        assert manager.get("theme") == "warcraft"


def test_config_manager_export():
    """Test export configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        export_path = Path(tmpdir) / "export.json"

        manager = ConfigurationManager(str(config_path))
        manager.set("theme", "mario")
        manager.export(str(export_path))

        assert export_path.exists()


def test_config_manager_import():
    """Test import configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        import_path = Path(tmpdir) / "import.json"

        # Create import file
        import_config = {"enabled": False, "theme": "starcraft"}
        with open(import_path, "w") as f:
            json.dump(import_config, f)

        manager = ConfigurationManager(str(config_path))
        manager.import_config(str(import_path))

        assert manager.get("enabled") is False
        assert manager.get("theme") == "starcraft"
