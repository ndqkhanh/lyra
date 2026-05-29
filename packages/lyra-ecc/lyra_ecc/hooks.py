"""
ECC Hooks Engine

Implements ECC-compatible hooks system for Lyra.
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Hook event types."""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    STOP = "stop"


@dataclass(frozen=True)
class HookContext:
    """Context passed to hooks."""
    event_type: HookType
    tool_name: Optional[str] = None
    file_path: Optional[Path] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None


@dataclass(frozen=True)
class HookResult:
    """Result from hook execution."""
    success: bool
    skipped: bool = False
    formatted: bool = False
    error: Optional[str] = None

    @classmethod
    def merge(cls, results: List['HookResult']) -> 'HookResult':
        """Merge multiple hook results."""
        if not results:
            return cls(success=True)

        success = all(r.success for r in results)
        formatted = any(r.formatted for r in results)
        errors = [r.error for r in results if r.error]

        return cls(
            success=success,
            formatted=formatted,
            error="; ".join(errors) if errors else None
        )


class ECCHooksEngine:
    """ECC-compatible hooks engine for Lyra."""

    def __init__(self):
        """Initialize hooks engine."""
        self.hooks: Dict[HookType, List[Callable]] = {
            HookType.PRE_TOOL_USE: [],
            HookType.POST_TOOL_USE: [],
            HookType.SESSION_START: [],
            HookType.SESSION_END: [],
            HookType.STOP: [],
        }
        self._load_default_hooks()

    def _load_default_hooks(self) -> None:
        """Load default hooks."""
        # Register default post-tool-use hooks
        self.register_hook(HookType.POST_TOOL_USE, self._auto_format_hook)
        self.register_hook(HookType.POST_TOOL_USE, self._type_check_hook)

    def register_hook(self, hook_type: HookType, hook_fn: Callable) -> None:
        """
        Register a hook function.

        Args:
            hook_type: Type of hook event
            hook_fn: Hook function to register
        """
        self.hooks[hook_type].append(hook_fn)
        logger.info(f"Registered hook for {hook_type.value}")

    async def fire(self, event: HookType, context: HookContext) -> HookResult:
        """
        Fire all hooks for an event.

        Args:
            event: Hook event type
            context: Hook context

        Returns:
            Merged result from all hooks
        """
        results: List[HookResult] = []

        for hook in self.hooks.get(event, []):
            try:
                if inspect.iscoroutinefunction(hook):
                    result = await hook(context)
                else:
                    result = hook(context)
                results.append(result)
            except Exception as e:
                error_msg = f"Hook failed: {e}"
                logger.error(error_msg)
                results.append(HookResult(success=False, error=error_msg))

        return HookResult.merge(results)

    async def _auto_format_hook(self, context: HookContext) -> HookResult:
        """Auto-format code after Write/Edit tools."""
        if context.tool_name not in ["Write", "Edit"] or not context.file_path:
            return HookResult(success=True, skipped=True)

        file_path = context.file_path

        try:
            # Detect language and run formatter
            if file_path.suffix == ".py":
                await self._run_command(f"black {file_path}")
                return HookResult(success=True, formatted=True)
            elif file_path.suffix in [".ts", ".tsx", ".js", ".jsx"]:
                await self._run_command(f"prettier --write {file_path}")
                return HookResult(success=True, formatted=True)
            elif file_path.suffix == ".go":
                await self._run_command(f"gofmt -w {file_path}")
                return HookResult(success=True, formatted=True)

            return HookResult(success=True, skipped=True)
        except Exception as e:
            return HookResult(success=False, error=str(e))

    async def _type_check_hook(self, context: HookContext) -> HookResult:
        """Run type checking after editing typed files."""
        if context.tool_name not in ["Write", "Edit"] or not context.file_path:
            return HookResult(success=True, skipped=True)

        file_path = context.file_path

        try:
            if file_path.suffix == ".py":
                await self._run_command(f"mypy {file_path}")
                return HookResult(success=True)
            elif file_path.suffix in [".ts", ".tsx"]:
                await self._run_command(f"tsc --noEmit {file_path}")
                return HookResult(success=True)

            return HookResult(success=True, skipped=True)
        except Exception as e:
            # Type errors are warnings, not failures
            logger.warning(f"Type check warning: {e}")
            return HookResult(success=True)

    async def _run_command(self, command: str) -> None:
        """Run shell command asynchronously."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
