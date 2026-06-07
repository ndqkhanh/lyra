"""
Configuration loading for provider backends and the model router.

API keys are read from environment variables. Model preferences and
router settings are read from ``.lyra/settings.json`` in the project root.
"""

from __future__ import annotations

import json
import os
import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = structlog.get_logger(__name__)


def _find_project_root() -> Path:
    """Walk upward from CWD looking for ``.lyra/settings.json``."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / ".lyra" / "settings.json"
        if candidate.is_file():
            return parent
    return cwd


def _load_lyra_settings() -> dict[str, Any]:
    """Load settings from ``.lyra/settings.json`` if it exists."""
    project_root = _find_project_root()
    settings_path = project_root / ".lyra" / "settings.json"
    if settings_path.is_file():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("failed to load .lyra/settings.json", path=str(settings_path), error=str(exc))
    return {}


def get_api_key(provider_name: str) -> str | None:
    """Return the API key for *provider_name* from the environment.

    Lookup order:
      1. ``<PROVIDER>_API_KEY`` (e.g. ``ANTHROPIC_API_KEY``)
      2. ``<PROVIDER>_API_KEY`` from ``.lyra/settings.json``
    """
    env_var = f"{provider_name.upper()}_API_KEY"
    key = os.environ.get(env_var)
    if key:
        return key
    settings = _load_lyra_settings()
    key = settings.get(env_var.lower())
    return key


@dataclass
class RouterConfig:
    """Configuration for the model router.

    Parameters are loaded from ``.lyra/settings.json`` and can be
    overridden programmatically.
    """

    default_provider: str = "anthropic"
    fast_model: str = "claude-sonnet-4-6"
    smart_model: str = "claude-sonnet-4-6"
    premium_model: str = "claude-opus-4-5"
    fallback_chain: tuple[str, ...] = ("anthropic", "deepseek", "openai", "google")
    max_budget_usd: float = 10.0
    provider_configs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_settings(cls) -> RouterConfig:
        """Create a ``RouterConfig`` from ``.lyra/settings.json``.

        Falls back to defaults for any missing keys.
        """
        settings = _load_lyra_settings()
        fallback_raw = settings.get("fallback_chain", cls.fallback_chain)
        return cls(
            default_provider=settings.get("last_provider", cls.default_provider),
            fast_model=settings.get("fast_model", cls.fast_model),
            smart_model=settings.get("smart_model", cls.smart_model),
            premium_model=settings.get("premium_model", cls.premium_model),
            fallback_chain=tuple(fallback_raw) if isinstance(fallback_raw, list) else cls.fallback_chain,
            max_budget_usd=float(settings.get("max_budget_usd", cls.max_budget_usd)),
            provider_configs=settings.get("provider_configs", {}),
        )
