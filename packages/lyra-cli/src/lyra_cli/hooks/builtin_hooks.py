"""Built-in hooks - ECC-inspired automation"""

import re

from .hook_manager import HookContext, HookManager, HookType
from .hook_registry import get_registry


def tmux_reminder_hook(context: HookContext) -> bool:
    """Remind to use tmux for long-running commands"""
    if context.tool_name != "Bash":
        return True

    command = context.tool_input.get("command", "")

    # Check for long-running commands
    long_running = ["npm run dev", "yarn dev", "python -m", "uvicorn", "flask run"]

    for pattern in long_running:
        if pattern in command:
            # Check if already in tmux
            import os
            if not os.getenv("TMUX"):
                print(f"\n⚠️  Consider running '{pattern}' in tmux for better management")
                print("   Tip: Start tmux with 'tmux new -s dev'\n")

    return True


def git_push_reminder_hook(context: HookContext) -> bool:
    """Remind to review before git push"""
    if context.tool_name != "Bash":
        return True

    command = context.tool_input.get("command", "")

    if "git push" in command and "--force" in command:
        print("\n⚠️  Force push detected! This will overwrite remote history.")
        print("   Make sure you know what you're doing.\n")

    return True


def secret_detection_hook(context: HookContext) -> bool:
    """Detect potential secrets in code"""
    if context.tool_name not in ["Write", "Edit"]:
        return True

    content = context.tool_input.get("content") or context.tool_input.get("new_string", "")

    # Simple secret patterns
    patterns = [
        (r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "API key"),
        (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "Password"),
        (r"secret\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "Secret"),
        (r"token\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "Token"),
    ]

    for pattern, name in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            print(f"\n⚠️  Potential {name} detected in code!")
            print("   Make sure this is not a real secret.\n")

    return True


def console_log_warning_hook(context: HookContext) -> None:
    """Warn about console.log statements"""
    if context.tool_name not in ["Write", "Edit"]:
        return

    content = context.tool_input.get("content") or context.tool_input.get("new_string", "")

    if "console.log" in content:
        print("\n💡 Tip: Consider using a proper logger instead of console.log\n")


def session_start_hook(context: HookContext) -> None:
    """Session start hook - load context"""
    print("🚀 Lyra session started")
    print(f"   Session ID: {context.session_id}\n")


def session_end_hook(context: HookContext) -> None:
    """Session end hook - save state"""
    print("\n👋 Lyra session ended")
    print(f"   Session ID: {context.session_id}")


def register_builtin_hooks(manager: HookManager):
    """Register all built-in hooks"""
    registry = get_registry()

    # PreToolUse hooks
    registry.register_hook(
        "tmux-reminder",
        HookType.PRE_TOOL_USE,
        "Remind to use tmux for long-running commands",
        tmux_reminder_hook
    )

    registry.register_hook(
        "git-push-reminder",
        HookType.PRE_TOOL_USE,
        "Warn before force push",
        git_push_reminder_hook
    )

    registry.register_hook(
        "secret-detection",
        HookType.PRE_TOOL_USE,
        "Detect potential secrets in code",
        secret_detection_hook
    )

    # PostToolUse hooks
    registry.register_hook(
        "console-log-warning",
        HookType.POST_TOOL_USE,
        "Warn about console.log usage",
        console_log_warning_hook
    )

    # Lifecycle hooks
    registry.register_hook(
        "session-start",
        HookType.SESSION_START,
        "Session initialization",
        session_start_hook
    )

    registry.register_hook(
        "session-end",
        HookType.SESSION_END,
        "Session cleanup",
        session_end_hook
    )

    # Register with manager
    for name, hook in registry.hooks.items():
        if hook["enabled"]:
            manager.register(hook["type"], hook["handler"], name=name)
