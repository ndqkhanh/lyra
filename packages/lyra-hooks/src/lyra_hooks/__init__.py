"""
Lyra Hooks System — PreToolUse, PostToolUse, and Stop hooks.

Provider-agnostic: hooks execute at the harness level regardless of which
provider is active. Uses the provider abstraction layer (§4.5) to normalize
tool calls before hook evaluation.

Hook types:
- **PreToolUse**: Before tool execution — validation, parameter modification
- **PostToolUse**: After tool execution — auto-format, checks, notifications
- **Stop**: When session ends — final verification, cleanup

Per BREAKTHROUGH-ARCHITECTURE.md: hooks back hard guarantees (§4.10), not
prompt instructions alone — on any provider, an injected hook is a strong
suggestion, not an enforced gate.
"""

from __future__ import annotations

from .manager import HookManager, HookType
from .models import HookResult, HookSpec

__all__ = ["HookManager", "HookResult", "HookSpec", "HookType"]
