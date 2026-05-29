"""Lyra Tools Universe — Centralized tool registry, catalog, and discovery.

Plan 9: 200+ tools across 20 toolsets with progressive disclosure (3 levels),
tool categorization, search, and dependency management.

Phase 5.4: Extended Tool Suite with 16 real tool implementations across
filesystem, code quality, security, network, git, and observability domains.

US-009: Comprehensive tools ecosystem matching Claude Code and Hermes-agent
capabilities with memory operations, model routing, skill management, and
code analysis tools.
"""

from __future__ import annotations

# Phase 5.4 — Extended Tool Suite
# US-009 — New Tool Modules
from . import (
    code_analysis,
    code_quality,
    file_ops,
    git_ops,
    memory_ops,
    model_routing,
    network_ops,
    obs_health,
    secrets_scan,
    skill_ops,
)
from .tool_registry import (
    ToolCategory,
    ToolDisclosureLevel,
    ToolManifest,
    ToolRegistry,
    Toolset,
    tool_registry,
)

__all__ = [
    # Registry
    "ToolCategory",
    "ToolDisclosureLevel",
    "ToolManifest",
    "ToolRegistry",
    "Toolset",
    "tool_registry",
    # Tool modules (Phase 5.4)
    "file_ops",
    "code_quality",
    "secrets_scan",
    "network_ops",
    "git_ops",
    "obs_health",
    # US-009 Tool modules
    "memory_ops",
    "model_routing",
    "code_analysis",
    "skill_ops",
]
