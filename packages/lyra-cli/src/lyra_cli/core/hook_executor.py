"""Hook executor for running hooks at lifecycle points via subprocess."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any

from .hook_metadata import HookMetadata, HookType
from .hook_registry import HookRegistry


@dataclass(frozen=True)
class HookResult:
    success: bool
    output: str
    error: str | None = None
    hook_name: str = ""
    duration_ms: float = 0.0


class HookExecutor:
    """Executes hooks at lifecycle points via subprocess with timeout.

    Hooks are shell scripts triggered at lifecycle events (PreToolUse,
    PostToolUse, Stop, etc.). Failed hooks are reported but do not
    halt execution by default.
    """

    DEFAULT_TIMEOUT = 30.0

    def __init__(self, registry: HookRegistry) -> None:
        self._registry = registry
        self._halt_on_failure = False

    def execute_hooks(
        self, hook_type: HookType, context: dict[str, Any] | None = None,
        *, timeout: float | None = None,
    ) -> list[HookResult]:
        hooks = self._registry.get_hooks_by_type(hook_type)
        results: list[HookResult] = []

        for hook in hooks:
            result = self._execute_hook(hook, context, timeout=timeout)
            results.append(result)
            if not result.success and self._halt_on_failure:
                break

        return results

    def _execute_hook(
        self, hook: HookMetadata, context: dict[str, Any] | None = None,
        *, timeout: float | None = None,
    ) -> HookResult:
        if not hook.script:
            return HookResult(success=True, output="", hook_name=hook.name)

        shell_env = {}
        if context:
            shell_env.update({str(k): str(v) for k, v in context.items()})

        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                hook.script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout or self.DEFAULT_TIMEOUT,
                env={**__import__("os").environ, **shell_env},
            )
            duration = (time.monotonic() - t0) * 1000
            output = proc.stdout.strip()
            if proc.returncode != 0:
                return HookResult(
                    success=False, output=output,
                    error=proc.stderr.strip() or f"Exit code: {proc.returncode}",
                    hook_name=hook.name, duration_ms=duration,
                )
            return HookResult(
                success=True, output=output, hook_name=hook.name, duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            duration = (time.monotonic() - t0) * 1000
            return HookResult(
                success=False, output="",
                error=f"Hook '{hook.name}' timed out",
                hook_name=hook.name, duration_ms=duration,
            )
        except Exception as exc:
            duration = (time.monotonic() - t0) * 1000
            return HookResult(
                success=False, output="", error=str(exc),
                hook_name=hook.name, duration_ms=duration,
            )
