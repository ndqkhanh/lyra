"""Central configuration for the Lyra cockpit.

Aggregates configuration from all cockpit subsystems into a single
CockpitConfig dataclass and provides a loader for file-based config.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .agent_monitor import MonitorConfig
from .budget_dashboard import BudgetConfig
from .exceptions import ConfigError
from .iaa_engine import IAAConfig
from .voice_notifier import VoiceConfig


@dataclass(frozen=True)
class CockpitConfig:
    """Aggregate configuration for all cockpit subsystems.

    Attributes:
        iaa: Configuration for the IAA engine.
        monitor: Configuration for the agent monitor.
        budget: Configuration for the budget dashboard.
        voice: Configuration for the voice notifier.
        transparency_enabled: Whether the transparency dashboard is active.
        update_interval: Dashboard update interval in seconds.
    """

    iaa: IAAConfig
    monitor: MonitorConfig
    budget: BudgetConfig
    voice: VoiceConfig
    transparency_enabled: bool = True
    update_interval: float = 1.0


class CockpitConfigLoader:
    """Loads and saves CockpitConfig from various sources."""

    @staticmethod
    def load_default() -> CockpitConfig:
        """Create a CockpitConfig with all default values.

        Returns:
            A CockpitConfig with default subsystem configurations.
        """
        return CockpitConfig(
            iaa=IAAConfig(),
            monitor=MonitorConfig(),
            budget=BudgetConfig(),
            voice=VoiceConfig(),
            transparency_enabled=True,
            update_interval=1.0,
        )

    @staticmethod
    def load_from_file(path: str) -> CockpitConfig:
        """Load CockpitConfig from a JSON file.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            A CockpitConfig populated from the file.

        Raises:
            ConfigError: If the file cannot be read or parsed.
        """
        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {path}") from None
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {e}") from e

        iaa_data = data.get("iaa", {})
        monitor_data = data.get("monitor", {})
        budget_data = data.get("budget", {})
        voice_data = data.get("voice", {})

        return CockpitConfig(
            iaa=IAAConfig(
                preview_timeout=iaa_data.get("preview_timeout", 5.0),
                auto_execute_threshold=iaa_data.get(
                    "auto_execute_threshold", 0.85
                ),
                audit_enabled=iaa_data.get("audit_enabled", True),
                max_preview_tokens=iaa_data.get("max_preview_tokens", 200),
            ),
            monitor=MonitorConfig(
                refresh_interval=monitor_data.get("refresh_interval", 1.0),
                max_agents=monitor_data.get("max_agents", 50),
                alert_threshold_cpu=monitor_data.get(
                    "alert_threshold_cpu", 90.0
                ),
            ),
            budget=BudgetConfig(
                daily_limit=budget_data.get("daily_limit", 50.0),
                monthly_limit=budget_data.get("monthly_limit", 1000.0),
                alert_threshold=budget_data.get("alert_threshold", 0.8),
                currency=budget_data.get("currency", "USD"),
            ),
            voice=VoiceConfig(
                enabled=voice_data.get("enabled", True),
                volume=voice_data.get("volume", 0.7),
                voice_pack=voice_data.get("voice_pack", "default"),
                event_mappings=tuple(
                    tuple(m) for m in voice_data.get("event_mappings", [])
                ),
            ),
            transparency_enabled=data.get("transparency_enabled", True),
            update_interval=data.get("update_interval", 1.0),
        )

    @staticmethod
    def save_to_file(config: CockpitConfig, path: str) -> None:
        """Save CockpitConfig to a JSON file.

        Args:
            config: The CockpitConfig to serialize.
            path: Path where the JSON file will be written.

        Raises:
            ConfigError: If the file cannot be written.
        """
        data = {
            "iaa": {
                "preview_timeout": config.iaa.preview_timeout,
                "auto_execute_threshold": config.iaa.auto_execute_threshold,
                "audit_enabled": config.iaa.audit_enabled,
                "max_preview_tokens": config.iaa.max_preview_tokens,
            },
            "monitor": {
                "refresh_interval": config.monitor.refresh_interval,
                "max_agents": config.monitor.max_agents,
                "alert_threshold_cpu": config.monitor.alert_threshold_cpu,
            },
            "budget": {
                "daily_limit": config.budget.daily_limit,
                "monthly_limit": config.budget.monthly_limit,
                "alert_threshold": config.budget.alert_threshold,
                "currency": config.budget.currency,
            },
            "voice": {
                "enabled": config.voice.enabled,
                "volume": config.voice.volume,
                "voice_pack": config.voice.voice_pack,
                "event_mappings": list(config.voice.event_mappings),
            },
            "transparency_enabled": config.transparency_enabled,
            "update_interval": config.update_interval,
        }

        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise ConfigError(f"Failed to write configuration file: {e}") from e
