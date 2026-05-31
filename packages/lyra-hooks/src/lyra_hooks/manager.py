"""
Hook Manager — registers and executes hooks across all providers.

Hooks run at the harness level, not the provider level. This ensures
consistent behavior regardless of which backend is active.
"""

from __future__ import annotations

import fnmatch
import logging
import subprocess
import time
from typing import Any

from .models import HookResult, HookSpec, HookType

logger = logging.getLogger(__name__)


class HookManager:
    """Manages the lifecycle of hooks (PreToolUse, PostToolUse, Stop)."""

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[HookSpec]] = {
            t: [] for t in HookType
        }

    def register(self, spec: HookSpec) -> None:
        self._hooks[spec.hook_type].append(spec)

    def unregister(self, name: str) -> bool:
        for hooks in self._hooks.values():
            for h in hooks:
                if h.name == name:
                    hooks.remove(h)
                    return True
        return False

    def run_pre_tool(self, tool_name: str, tool_input: dict[str, Any]) -> list[HookResult]:
        """Run PreToolUse hooks for a tool. Returns results including any modifications."""
        results = []
        current = dict(tool_input)
        for hook in self._hooks[HookType.PRE_TOOL_USE]:
            if fnmatch.fnmatch(tool_name, hook.matcher):
                result = self._execute(hook, tool_input=current)
                results.append(result)
                if result.success and result.modified_input:
                    current = result.modified_input
        return results

    def run_post_tool(self, tool_name: str, tool_result: dict[str, Any]) -> list[HookResult]:
        """Run PostToolUse hooks after a tool completes."""
        return [
            self._execute(h, tool_result=tool_result)
            for h in self._hooks[HookType.POST_TOOL_USE]
            if fnmatch.fnmatch(tool_name, h.matcher)
        ]

    def run_stop(self) -> list[HookResult]:
        """Run Stop hooks on session end."""
        return [self._execute(h) for h in self._hooks[HookType.STOP]]

    def _execute(self, spec: HookSpec, tool_input: dict[str, Any] | None = None,
                 tool_result: dict[str, Any] | None = None) -> HookResult:
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                spec.command, shell=True, capture_output=True, text=True,
                timeout=spec.timeout_seconds,
            )
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("Hook '%s' completed in %.0fms (exit=%d)", spec.name, elapsed, proc.returncode)
            return HookResult(
                hook_name=spec.name,
                success=proc.returncode == 0,
                stdout=proc.stdout.strip(),
                stderr=proc.stderr.strip(),
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return HookResult(hook_name=spec.name, success=False, stderr=f"Timeout after {spec.timeout_seconds}s")
        except Exception as e:
            return HookResult(hook_name=spec.name, success=False, stderr=str(e))
