"""Unit tests for config schema migration (v6.0.0).

Tests the migration from fallback_chain to primary_provider.
"""

import json
import tempfile
from pathlib import Path

import pytest
from lyra_cli.config_io import (
    LYRA_CONFIG_VERSION,
    SettingsConfig,
    load_settings,
    save_settings,
)


class TestConfigSchema:
    """Test the new config schema."""

    def test_default_config(self):
        config = SettingsConfig()
        assert config.primary_provider == "auto"
        assert config.enable_task_routing is True
        assert config.config_version == 4

    def test_config_has_no_fallback_chain(self):
        """Ensure fallback_chain is removed from schema."""
        config = SettingsConfig()
        assert not hasattr(config, "fallback_chain")


class TestConfigMigration:
    """Test migration from old config format."""

    def test_migrate_fallback_chain_to_primary_provider(self):
        """Old config with fallback_chain should migrate to primary_provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            # Write old config format (v3)
            old_config = {
                "config_version": 3,
                "last_model": "claude-sonnet-4.6",
                "last_provider": "anthropic",
                "fallback_chain": ["anthropic", "deepseek", "openai"],
                "theme": "dracula",
                "permission_mode": "allow",
                "auto_detect_tasks": True,
            }
            config_path.write_text(json.dumps(old_config), encoding="utf-8")

            # Load should migrate automatically
            config = load_settings(config_path)

            # Should use first provider from fallback_chain
            assert config.primary_provider == "anthropic"
            # Config version is preserved from file (migration doesn't bump it)
            assert config.config_version == 3
            assert config.enable_task_routing is True

    def test_migrate_empty_fallback_chain(self):
        """Empty fallback_chain should default to 'auto'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            old_config = {
                "config_version": 3,
                "fallback_chain": [],
            }
            config_path.write_text(json.dumps(old_config), encoding="utf-8")

            config = load_settings(config_path)
            assert config.primary_provider == "auto"

    def test_new_config_with_primary_provider(self):
        """New config with primary_provider should load correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            new_config = {
                "config_version": 4,
                "primary_provider": "deepseek",
                "enable_task_routing": True,
            }
            config_path.write_text(json.dumps(new_config), encoding="utf-8")

            config = load_settings(config_path)
            assert config.primary_provider == "deepseek"
            assert config.enable_task_routing is True

    def test_both_fallback_chain_and_primary_provider(self):
        """If both exist, primary_provider takes precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            mixed_config = {
                "config_version": 4,
                "fallback_chain": ["anthropic", "deepseek"],
                "primary_provider": "openai",
            }
            config_path.write_text(json.dumps(mixed_config), encoding="utf-8")

            config = load_settings(config_path)
            # primary_provider should win
            assert config.primary_provider == "openai"


class TestConfigSave:
    """Test saving config with new schema."""

    def test_save_new_config(self):
        """Saved config should use new schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            config = SettingsConfig(
                primary_provider="anthropic",
                enable_task_routing=True,
                theme="aurora",
            )

            # Temporarily override settings_path
            import lyra_cli.config_io as config_io
            original_settings_path = config_io.settings_path
            config_io.settings_path = lambda: config_path

            try:
                save_settings(config)

                # Read back and verify
                data = json.loads(config_path.read_text(encoding="utf-8"))
                assert data["primary_provider"] == "anthropic"
                assert data["enable_task_routing"] is True
                assert data["config_version"] == 4
                assert "fallback_chain" not in data
            finally:
                config_io.settings_path = original_settings_path

    def test_save_preserves_all_fields(self):
        """Ensure all fields are saved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            config = SettingsConfig(
                last_model="claude-opus-4.7",
                last_provider="anthropic",
                primary_provider="anthropic",
                enable_task_routing=False,
                theme="dracula",
                permission_mode="strict",
                auto_detect_tasks=False,
                config_version=4,
            )

            import lyra_cli.config_io as config_io
            original_settings_path = config_io.settings_path
            config_io.settings_path = lambda: config_path

            try:
                save_settings(config)
                loaded = load_settings(config_path)

                assert loaded.last_model == "claude-opus-4.7"
                assert loaded.last_provider == "anthropic"
                assert loaded.primary_provider == "anthropic"
                assert loaded.enable_task_routing is False
                assert loaded.theme == "dracula"
                assert loaded.permission_mode == "strict"
                assert loaded.auto_detect_tasks is False
            finally:
                config_io.settings_path = original_settings_path


class TestConfigVersion:
    """Test config version handling."""

    def test_config_version_bumped(self):
        """Config version should be 4 for v6.0.0."""
        assert LYRA_CONFIG_VERSION == 4

    def test_new_config_has_correct_version(self):
        config = SettingsConfig()
        assert config.config_version == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
