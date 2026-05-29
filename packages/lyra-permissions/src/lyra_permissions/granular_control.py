"""
Granular Control - Tool-specific and context-aware permissions.

Features:
- Tool-specific permissions
- Context-aware rules
- Permission profiles
- Time-based permissions
"""

import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

from lyra_permissions.types import PermissionDecision, PermissionLevel


class ToolPermission:
    """Tool-specific permission configuration."""

    ALWAYS_ALLOW = "always_allow"
    PROMPT_ONCE = "prompt_once"
    ALWAYS_PROMPT = "always_prompt"
    BYPASS_IF_SAFE = "bypass_if_safe"


class ContextRule:
    """Context-aware permission rule."""

    def __init__(
        self,
        name: str,
        condition: dict[str, Any],
        decision: PermissionDecision,
        priority: int = 0,
    ):
        """Initialize context rule."""
        self.name = name
        self.condition = condition
        self.decision = decision
        self.priority = priority

    def matches(self, context: dict[str, Any]) -> bool:
        """Check if context matches rule condition."""
        for key, value in self.condition.items():
            if key not in context:
                return False

            ctx_value = context[key]

            # Handle different condition types
            if isinstance(value, dict):
                # Complex condition (e.g., {"startswith": "/tmp"})
                if "startswith" in value:
                    if not str(ctx_value).startswith(value["startswith"]):
                        return False
                elif "contains" in value:
                    if value["contains"] not in str(ctx_value):
                        return False
                elif "equals" in value:
                    if ctx_value != value["equals"]:
                        return False
            else:
                # Simple equality
                if ctx_value != value:
                    return False

        return True


class PermissionProfile:
    """Permission profile for different environments."""

    def __init__(self, name: str, config: dict[str, Any]):
        """Initialize permission profile."""
        self.name = name
        self.config = config

    def get_tool_permission(self, tool: str, operation: str) -> str | None:
        """Get tool-specific permission."""
        tool_perms = self.config.get("toolPermissions", {})
        tool_key = f"{tool}:{operation}"

        if tool_key in tool_perms:
            return tool_perms[tool_key]

        # Check wildcard
        wildcard_key = f"{tool}:*"
        if wildcard_key in tool_perms:
            return tool_perms[wildcard_key]

        return None

    def get_context_rules(self) -> list[ContextRule]:
        """Get context rules."""
        rules = []
        for rule_config in self.config.get("contextRules", []):
            rule = ContextRule(
                name=rule_config["name"],
                condition=rule_config["condition"],
                decision=PermissionDecision(rule_config["decision"]),
                priority=rule_config.get("priority", 0),
            )
            rules.append(rule)

        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules


class GranularController:
    """
    Granular permission control.

    Features:
    - Tool-specific permissions
    - Context-aware rules
    - Permission profiles
    - Time-based permissions
    """

    def __init__(self, config_path: str | None = None):
        """Initialize granular controller."""
        if config_path:
            self.config_path = Path(config_path).expanduser()
        else:
            self.config_path = Path("~/.lyra/granular_permissions.json").expanduser()

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config()
        self.current_profile = self.config.get("currentProfile", "default")
        self.profiles = self._load_profiles()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return self._default_config()
        return self._default_config()

    def _default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "currentProfile": "default",
            "profiles": {
                "default": {
                    "name": "Default",
                    "toolPermissions": {},
                    "contextRules": [],
                },
                "development": {
                    "name": "Development",
                    "toolPermissions": {
                        "file_read:*": ToolPermission.ALWAYS_ALLOW,
                        "file_write:*": ToolPermission.BYPASS_IF_SAFE,
                        "file_delete:*": ToolPermission.ALWAYS_PROMPT,
                        "git:push": ToolPermission.PROMPT_ONCE,
                    },
                    "contextRules": [
                        {
                            "name": "Allow temp directory",
                            "condition": {"path": {"startswith": "/tmp"}},
                            "decision": "allow",
                            "priority": 10,
                        }
                    ],
                },
                "production": {
                    "name": "Production",
                    "toolPermissions": {
                        "file_read:*": ToolPermission.ALWAYS_ALLOW,
                        "file_write:*": ToolPermission.ALWAYS_PROMPT,
                        "file_delete:*": ToolPermission.ALWAYS_PROMPT,
                        "database:*": ToolPermission.ALWAYS_PROMPT,
                    },
                    "contextRules": [
                        {
                            "name": "Deny production paths",
                            "condition": {"path": {"startswith": "/var"}},
                            "decision": "prompt",
                            "priority": 100,
                        }
                    ],
                },
            },
        }

    def _save_config(self):
        """Save configuration."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except OSError:
            pass

    def _load_profiles(self) -> dict[str, PermissionProfile]:
        """Load permission profiles."""
        profiles = {}
        for name, config in self.config.get("profiles", {}).items():
            profiles[name] = PermissionProfile(name, config)
        return profiles

    def set_profile(self, profile_name: str):
        """Set current profile."""
        if profile_name in self.profiles:
            self.current_profile = profile_name
            self.config["currentProfile"] = profile_name
            self._save_config()

    def get_profile(self) -> PermissionProfile:
        """Get current profile."""
        return self.profiles.get(self.current_profile, self.profiles["default"])

    def check_tool_permission(
        self, tool: str, operation: str, level: PermissionLevel
    ) -> PermissionDecision | None:
        """
        Check tool-specific permission.

        Args:
            tool: Tool name
            operation: Operation name
            level: Permission level

        Returns:
            Permission decision or None if no rule applies
        """
        profile = self.get_profile()
        tool_perm = profile.get_tool_permission(tool, operation)

        if not tool_perm:
            return None

        if tool_perm == ToolPermission.ALWAYS_ALLOW:
            return PermissionDecision.ALLOW

        if tool_perm == ToolPermission.ALWAYS_PROMPT:
            return PermissionDecision.PROMPT

        if tool_perm == ToolPermission.BYPASS_IF_SAFE:
            if level == PermissionLevel.SAFE:
                return PermissionDecision.ALLOW
            return None

        return None

    def check_context_rules(
        self, context: dict[str, Any]
    ) -> PermissionDecision | None:
        """
        Check context-aware rules.

        Args:
            context: Operation context

        Returns:
            Permission decision or None if no rule matches
        """
        profile = self.get_profile()
        rules = profile.get_context_rules()

        for rule in rules:
            if rule.matches(context):
                return rule.decision

        return None

    def add_tool_permission(self, tool: str, operation: str, permission: str):
        """Add tool-specific permission."""
        profile = self.get_profile()
        tool_key = f"{tool}:{operation}"

        if "toolPermissions" not in profile.config:
            profile.config["toolPermissions"] = {}

        profile.config["toolPermissions"][tool_key] = permission

        # Update config
        self.config["profiles"][self.current_profile] = profile.config
        self._save_config()

    def add_context_rule(
        self,
        name: str,
        condition: dict[str, Any],
        decision: str,
        priority: int = 0,
    ):
        """Add context rule."""
        profile = self.get_profile()

        if "contextRules" not in profile.config:
            profile.config["contextRules"] = []

        rule_config = {
            "name": name,
            "condition": condition,
            "decision": decision,
            "priority": priority,
        }

        profile.config["contextRules"].append(rule_config)

        # Update config
        self.config["profiles"][self.current_profile] = profile.config
        self._save_config()

        # Reload profiles
        self.profiles = self._load_profiles()

    def list_profiles(self) -> list[str]:
        """List available profiles."""
        return list(self.profiles.keys())


class TimeBasedController:
    """Time-based permission control."""

    def __init__(self):
        """Initialize time-based controller."""
        self.rules: list[dict[str, Any]] = []

    def add_time_rule(
        self,
        start_time: time,
        end_time: time,
        decision: PermissionDecision,
        days: list[int] | None = None,
    ):
        """
        Add time-based rule.

        Args:
            start_time: Start time
            end_time: End time
            decision: Permission decision
            days: Days of week (0=Monday, 6=Sunday), None=all days
        """
        self.rules.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "decision": decision,
                "days": days,
            }
        )

    def check_time_rules(self) -> PermissionDecision | None:
        """Check if current time matches any rule."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()

        for rule in self.rules:
            # Check day of week
            if rule["days"] and current_day not in rule["days"]:
                continue

            # Check time range
            start = rule["start_time"]
            end = rule["end_time"]

            if start <= current_time <= end:
                return rule["decision"]

        return None

    def is_work_hours(self) -> bool:
        """Check if current time is work hours (9 AM - 5 PM, Mon-Fri)."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()

        # Monday-Friday (0-4)
        if current_day > 4:
            return False

        # 9 AM - 5 PM
        work_start = time(9, 0)
        work_end = time(17, 0)

        return work_start <= current_time <= work_end
