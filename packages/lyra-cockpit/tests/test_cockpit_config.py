"""Tests for the cockpit config module."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from lyra_cockpit.agent_monitor import MonitorConfig
from lyra_cockpit.budget_dashboard import BudgetConfig
from lyra_cockpit.cockpit_config import CockpitConfig, CockpitConfigLoader
from lyra_cockpit.exceptions import ConfigError
from lyra_cockpit.iaa_engine import IAAConfig
from lyra_cockpit.voice_notifier import VoiceConfig


class TestCockpitConfig:
    def test_creation(self) -> None:
        config = CockpitConfig(
            iaa=IAAConfig(),
            monitor=MonitorConfig(),
            budget=BudgetConfig(),
            voice=VoiceConfig(),
        )
        assert config.transparency_enabled is True
        assert config.update_interval == 1.0
        assert config.iaa.audit_enabled is True
        assert config.monitor.max_agents == 50

    def test_custom_values(self) -> None:
        config = CockpitConfig(
            iaa=IAAConfig(preview_timeout=30.0),
            monitor=MonitorConfig(max_agents=10),
            budget=BudgetConfig(daily_limit=200.0),
            voice=VoiceConfig(enabled=False),
            transparency_enabled=False,
            update_interval=5.0,
        )
        assert config.iaa.preview_timeout == 30.0
        assert config.monitor.max_agents == 10
        assert config.budget.daily_limit == 200.0
        assert config.voice.enabled is False
        assert config.transparency_enabled is False
        assert config.update_interval == 5.0

    def test_frozen(self) -> None:
        config = CockpitConfig(IAAConfig(), MonitorConfig(), BudgetConfig(), VoiceConfig())
        with pytest.raises(AttributeError):
            config.transparency_enabled = False  # type: ignore[misc]


class TestCockpitConfigLoader:
    def test_load_default(self) -> None:
        config = CockpitConfigLoader.load_default()
        assert isinstance(config.iaa, IAAConfig)
        assert isinstance(config.monitor, MonitorConfig)
        assert isinstance(config.budget, BudgetConfig)
        assert isinstance(config.voice, VoiceConfig)
        assert config.transparency_enabled is True
        assert config.update_interval == 1.0

    def test_save_and_load(self) -> None:
        config = CockpitConfigLoader.load_default()
        modified = CockpitConfig(
            iaa=IAAConfig(preview_timeout=42.0),
            monitor=MonitorConfig(max_agents=99),
            budget=BudgetConfig(daily_limit=250.0),
            voice=VoiceConfig(volume=0.3),
            transparency_enabled=False,
            update_interval=2.0,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
            CockpitConfigLoader.save_to_file(modified, tmp_path)

        try:
            loaded = CockpitConfigLoader.load_from_file(tmp_path)
            assert loaded.iaa.preview_timeout == 42.0
            assert loaded.monitor.max_agents == 99
            assert loaded.budget.daily_limit == 250.0
            assert loaded.voice.volume == 0.3
            assert loaded.transparency_enabled is False
            assert loaded.update_interval == 2.0
        finally:
            os.unlink(tmp_path)

    def test_load_from_file_not_found(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            CockpitConfigLoader.load_from_file("/nonexistent/path/config.json")

    def test_load_from_file_invalid_json(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json")
            tmp_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid JSON"):
                CockpitConfigLoader.load_from_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_save_and_load_with_event_mappings(self) -> None:
        mappings = (("custom_event", "custom_sound"),)
        config = CockpitConfig(
            iaa=IAAConfig(),
            monitor=MonitorConfig(),
            budget=BudgetConfig(),
            voice=VoiceConfig(event_mappings=mappings),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
            CockpitConfigLoader.save_to_file(config, tmp_path)

        try:
            loaded = CockpitConfigLoader.load_from_file(tmp_path)
            assert loaded.voice.event_mappings == (("custom_event", "custom_sound"),)
        finally:
            os.unlink(tmp_path)

    def test_partial_file_uses_defaults(self) -> None:
        partial = {"iaa": {"preview_timeout": 99.0}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(partial, f)
            tmp_path = f.name

        try:
            loaded = CockpitConfigLoader.load_from_file(tmp_path)
            assert loaded.iaa.preview_timeout == 99.0
            assert loaded.monitor.max_agents == 50  # default
        finally:
            os.unlink(tmp_path)

    def test_save_to_file_creates_valid_json(self) -> None:
        config = CockpitConfigLoader.load_default()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            tmp_path = f.name

        try:
            CockpitConfigLoader.save_to_file(config, tmp_path)
            with open(tmp_path, "r") as f:
                data = json.load(f)
            assert "iaa" in data
            assert "monitor" in data
            assert "budget" in data
            assert "voice" in data
            assert "transparency_enabled" in data
            assert "update_interval" in data
        finally:
            os.unlink(tmp_path)
