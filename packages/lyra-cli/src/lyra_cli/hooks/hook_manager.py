"""Hook manager - Core hook system implementation"""

from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
import json
import subprocess
import os
from pathlib import Path


class HookType(Enum):
    """Hook types matching ECC architecture"""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    PRE_COMPACT = "PreCompact"


@dataclass
class HookContext:
    """Context passed to hooks"""
    hook_type: HookType
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HookManager:
    """Manages hook registration and execution"""

    def __init__(self, hooks_dir: Optional[Path] = None):
        self.hooks_dir = hooks_dir or Path.home() / ".lyra" / "hooks"
        self.hooks: Dict[HookType, List[Callable]] = {
            hook_type: [] for hook_type in HookType
        }
        self.disabled_hooks: List[str] = []
        self._load_config()

    def _load_config(self):
        """Load hook configuration"""
        config_file = self.hooks_dir / "hooks.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                    self.disabled_hooks = config.get("disabled", [])
            except Exception as e:
                print(f"Warning: Failed to load hooks config: {e}")

    def register(self, hook_type: HookType, hook_fn: Callable, name: str = None):
        """Register a hook function"""
        if name and self._is_disabled(hook_type, name):
            return

        self.hooks[hook_type].append(hook_fn)

    def _is_disabled(self, hook_type: HookType, name: str) -> bool:
        """Check if hook is disabled"""
        hook_id = f"{hook_type.value.lower()}:{name}"
        return hook_id in self.disabled_hooks

    async def execute(self, context: HookContext) -> bool:
        """Execute all hooks for a given type

        Returns:
            True if execution should continue
            False if execution should be blocked (PreToolUse only)
        """
        hooks = self.hooks.get(context.hook_type, [])

        for hook_fn in hooks:
            try:
                result = hook_fn(context)

                # PreToolUse hooks can block execution
                if context.hook_type == HookType.PRE_TOOL_USE:
                    if result is False:
                        return False

            except Exception as e:
                print(f"Hook error ({context.hook_type.value}): {e}")

        return True

    def execute_script(self, script_path: Path, context: HookContext) -> int:
        """Execute a hook script (Node.js or shell)

        Returns:
            Exit code (0 = success, 2 = block for PreToolUse)
        """
        if not script_path.exists():
            return 0

        # Prepare input JSON
        input_data = {
            "hook_type": context.hook_type.value,
            "tool_name": context.tool_name,
            "tool_input": context.tool_input,
            "tool_output": context.tool_output,
            "session_id": context.session_id,
            "metadata": context.metadata or {},
        }

        try:
            # Execute script with JSON input
            result = subprocess.run(
                ["node", str(script_path)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=30,
            )

            return result.returncode

        except subprocess.TimeoutExpired:
            print(f"Hook timeout: {script_path}")
            return 0
        except Exception as e:
            print(f"Hook execution error: {e}")
            return 0

    def load_scripts(self):
        """Load hook scripts from hooks directory"""
        if not self.hooks_dir.exists():
            return

        # Load PreToolUse hooks
        pre_dir = self.hooks_dir / "pre"
        if pre_dir.exists():
            for script in pre_dir.glob("*.js"):
                name = script.stem
                self.register(
                    HookType.PRE_TOOL_USE,
                    lambda ctx, s=script: self.execute_script(s, ctx) == 0,
                    name=name
                )

        # Load PostToolUse hooks
        post_dir = self.hooks_dir / "post"
        if post_dir.exists():
            for script in post_dir.glob("*.js"):
                name = script.stem
                self.register(
                    HookType.POST_TOOL_USE,
                    lambda ctx, s=script: self.execute_script(s, ctx),
                    name=name
                )

        # Load other hook types
        for hook_type in [HookType.STOP, HookType.SESSION_START,
                         HookType.SESSION_END, HookType.PRE_COMPACT]:
            hook_dir = self.hooks_dir / hook_type.value.lower()
            if hook_dir.exists():
                for script in hook_dir.glob("*.js"):
                    name = script.stem
                    self.register(
                        hook_type,
                        lambda ctx, s=script: self.execute_script(s, ctx),
                        name=name
                    )


# Global hook manager instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get or create global hook manager"""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
        _hook_manager.load_scripts()
    return _hook_manager
