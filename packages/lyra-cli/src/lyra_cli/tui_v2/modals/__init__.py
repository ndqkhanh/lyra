"""Lyra-specific Textual modals.

Phase 5 of the v3.14 rewrite. harness-tui already ships:

  * ``SessionPicker`` (Ctrl+R / ``/resume``)
  * ``ThemePicker`` (``/theme``)
  * ``HelpModal`` (Ctrl+P / ``?`` / ``/help``)
  * ``TranscriptSearch`` (Ctrl+F)
  * ``PermissionGate`` (auto on ``PermissionRequested``)
  * ``PlanEditor`` (auto on ``PlanProposed``)

Lyra adds three project-specific pickers:

  * ``ModelPicker``  — switch LLM provider/model
  * ``SkillPicker``  — browse installed skills
  * ``McpPicker``    — browse configured MCP servers

All three share the :class:`base.LyraPickerModal` filter+list contract
so they look and feel consistent. OpenCode-style size tiers map onto
the modals' DEFAULT_CSS widths (60 / 88 / 116 cols).
"""
from __future__ import annotations

from .mcp import McpPicker
from .model import ModelPicker
from .skill import SkillPicker

__all__ = ["McpPicker", "ModelPicker", "SkillPicker"]
