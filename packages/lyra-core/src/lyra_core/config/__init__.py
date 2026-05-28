"""Lyra configuration — feature flags and enterprise settings hierarchy.

Feature flags are environment-variable-controlled constants evaluated at import
time. The 4-tier settings hierarchy provides deny-first permission evaluation
with priority-based resolution (managed > CLI > local > project > user).
"""
from __future__ import annotations

import os
from typing import Final

# ---------------------------------------------------------------------------
# Process Transparency Feature Flags
# ---------------------------------------------------------------------------

LYRA_ENABLE_PROCESS_TRANSPARENCY: Final[bool] = (
    os.getenv("LYRA_ENABLE_PROCESS_TRANSPARENCY", "true").lower() == "true"
)
"""Master flag for all process transparency features.

When disabled, the following are turned off:
- EventBus event emission
- ProcessStateWriter (.lyra/process_state.json)
- EventStore SQLite persistence
- ProcessRegistry polling
- TUI v2 agent panel and process tab

Default: true (enabled)
"""

LYRA_ENABLE_EVENT_BUS: Final[bool] = (
    LYRA_ENABLE_PROCESS_TRANSPARENCY
    and os.getenv("LYRA_ENABLE_EVENT_BUS", "true").lower() == "true"
)
"""Enable EventBus for transparency events.

Default: true (follows LYRA_ENABLE_PROCESS_TRANSPARENCY)
"""

LYRA_ENABLE_EVENT_STORE: Final[bool] = (
    LYRA_ENABLE_PROCESS_TRANSPARENCY
    and os.getenv("LYRA_ENABLE_EVENT_STORE", "true").lower() == "true"
)
"""Enable SQLite EventStore persistence.

Default: true (follows LYRA_ENABLE_PROCESS_TRANSPARENCY)
"""

LYRA_ENABLE_PROCESS_STATE_WRITER: Final[bool] = (
    LYRA_ENABLE_PROCESS_TRANSPARENCY
    and os.getenv("LYRA_ENABLE_PROCESS_STATE_WRITER", "true").lower() == "true"
)
"""Enable ProcessStateWriter (.lyra/process_state.json).

Default: true (follows LYRA_ENABLE_PROCESS_TRANSPARENCY)
"""

LYRA_ENABLE_AGENT_PANEL: Final[bool] = (
    LYRA_ENABLE_PROCESS_TRANSPARENCY
    and os.getenv("LYRA_ENABLE_AGENT_PANEL", "true").lower() == "true"
)
"""Enable TUI v2 agent panel and process tab.

Default: true (follows LYRA_ENABLE_PROCESS_TRANSPARENCY)
"""


# ---------------------------------------------------------------------------
# Legacy TUI Fallback
# ---------------------------------------------------------------------------

LYRA_LEGACY_TUI: Final[bool] = os.getenv("LYRA_LEGACY_TUI", "false").lower() == "true"
"""Force legacy TUI v1, bypassing all TUI v2 features.

Use this for complete rollback to pre-transparency TUI.

Default: false (use TUI v2)
"""


# ---------------------------------------------------------------------------
# Context Optimization Feature Flags
# ---------------------------------------------------------------------------

LYRA_ENABLE_CONTEXT_OPTIMIZATION: Final[bool] = (
    os.getenv("LYRA_ENABLE_CONTEXT_OPTIMIZATION", "true").lower() == "true"
)
"""Master flag for context optimization features.

When disabled, the following are turned off:
- Cache telemetry tracking
- Proactive compaction controller
- Decision and temporal fact memory
- Tool output retention policy
- Repo-map code context
- Token compression pipeline

Default: true (enabled)
"""


# ---------------------------------------------------------------------------
# Performance Tuning
# ---------------------------------------------------------------------------

LYRA_TUI_REFRESH_RATE: Final[float] = float(
    os.getenv("LYRA_TUI_REFRESH_RATE", "30.0")
)
"""TUI refresh rate in FPS (frames per second).

Higher values = smoother updates but more CPU.
Lower values = less CPU but choppier updates.

Default: 30.0 FPS
"""

LYRA_PROCESS_REGISTRY_POLL_INTERVAL: Final[float] = float(
    os.getenv("LYRA_PROCESS_REGISTRY_POLL_INTERVAL", "1.0")
)
"""ProcessRegistry polling interval in seconds.

Default: 1.0 second
"""

LYRA_EVENT_QUEUE_MAX_SIZE: Final[int] = int(
    os.getenv("LYRA_EVENT_QUEUE_MAX_SIZE", "1000")
)
"""EventBus queue max size before backpressure (drops oldest).

Default: 1000 events
"""


# ---------------------------------------------------------------------------
# Debugging
# ---------------------------------------------------------------------------

LYRA_DEBUG_EVENT_BUS: Final[bool] = (
    os.getenv("LYRA_DEBUG_EVENT_BUS", "false").lower() == "true"
)
"""Enable verbose EventBus logging (prints every event).

Default: false
"""

LYRA_DEBUG_TUI: Final[bool] = (
    os.getenv("LYRA_DEBUG_TUI", "false").lower() == "true"
)
"""Enable verbose TUI logging (widget renders, state updates).

Default: false
"""

# ---------------------------------------------------------------------------
# Settings Hierarchy (Phase 13.5.4)
# ---------------------------------------------------------------------------

from .settings_hierarchy import (  # noqa: E402 — intentional late import
    LockedSettingError,
    ManagedPolicy,
    PolicyRule,
    PolicyViolationError,
    SettingOverride,
    SettingScope,
    SettingsError,
    SettingsHierarchy,
    SettingValue,
)

__all__ = [
    # Feature flags
    "LYRA_DEBUG_EVENT_BUS",
    "LYRA_DEBUG_TUI",
    "LYRA_ENABLE_AGENT_PANEL",
    "LYRA_ENABLE_CONTEXT_OPTIMIZATION",
    "LYRA_ENABLE_EVENT_BUS",
    "LYRA_ENABLE_EVENT_STORE",
    "LYRA_ENABLE_PROCESS_STATE_WRITER",
    "LYRA_ENABLE_PROCESS_TRANSPARENCY",
    "LYRA_EVENT_QUEUE_MAX_SIZE",
    "LYRA_LEGACY_TUI",
    "LYRA_PROCESS_REGISTRY_POLL_INTERVAL",
    "LYRA_TUI_REFRESH_RATE",
    # Settings hierarchy
    "LockedSettingError",
    "ManagedPolicy",
    "PolicyRule",
    "PolicyViolationError",
    "SettingsError",
    "SettingsHierarchy",
    "SettingOverride",
    "SettingScope",
    "SettingValue",
]
