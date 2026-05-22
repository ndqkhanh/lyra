"""Lyra-specific Textual modals.

Phase 5 of the v3.14 rewrite. harness-tui already ships:

  * ``SessionPicker`` (Ctrl+R / ``/resume``)
  * ``ThemePicker`` (``/theme``)
  * ``HelpModal`` (Ctrl+P / ``?`` / ``/help``)
  * ``TranscriptSearch`` (Ctrl+F)
  * ``PermissionGate`` (auto on ``PermissionRequested``)
  * ``PlanEditor`` (auto on ``PlanProposed``)

Lyra adds four project-specific pickers:

  * ``CommandPaletteModal`` — fuzzy-searchable command palette (Ctrl+K)
  * ``ModelPicker``  — switch LLM provider/model
  * ``SkillPicker``  — browse installed skills
  * ``McpPicker``    — browse configured MCP servers

Plus new UX modals:

  * ``SessionManagerModal`` — browse & search session history
  * ``NotificationDrawer``  — notification history drawer
  * ``StatusDashboardModal`` — ECC-inspired consolidated /status view
"""
from __future__ import annotations

from .command_palette import CommandPaletteModal
from .mcp import McpPicker
from .model import ModelPicker
from .skill import SkillPicker
from .session_manager import SessionManagerModal
from .notification_drawer import NotificationDrawer
from .theme_switcher import ThemeSwitcherModal
from .status_dashboard import StatusDashboardModal
from .model_picker import ModelPickerModal

__all__ = [
    "CommandPaletteModal", "McpPicker", "ModelPicker", "SkillPicker",
    "SessionManagerModal", "NotificationDrawer", "ThemeSwitcherModal",
    "StatusDashboardModal",
    "ModelPickerModal",
]
