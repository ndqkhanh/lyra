"""
Permission system — PermissionManager with tool-level granularity.

Provides ALLOW / DENY / ASK access control, per-session overrides,
and permission inheritance from policy objects.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AccessLevel(Enum):
    """Access level for a tool or resource."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class PermissionResult:
    """Result of a permission check."""

    allowed: bool
    level: AccessLevel
    reason: str = ""


@dataclass
class PermissionOverride:
    """A per-session override for a specific tool."""

    tool_name: str
    level: AccessLevel
    session_id: str = ""
    reason: str = ""


@dataclass
class PermissionPolicy:
    """
    A named policy that defines defaults and overrides for a set of tools.

    Supports inheritance: a child policy can override some tools from a parent.
    """

    name: str
    default_level: AccessLevel = AccessLevel.ASK
    tools: dict[str, AccessLevel] = field(default_factory=dict)
    parent: "PermissionPolicy | None" = None

    def get_level(self, tool_name: str) -> AccessLevel:
        """
        Get the effective access level for a tool, considering inheritance.

        Args:
            tool_name: Name of the tool.

        Returns:
            The resolved AccessLevel.
        """
        # Check direct tool mapping first
        if tool_name in self.tools:
            return self.tools[tool_name]

        # Check parent policy
        if self.parent is not None:
            return self.parent.get_level(tool_name)

        # Fall back to default
        return self.default_level


class PermissionManager:
    """
    Manages tool-level permissions with ALLOW / DENY / ASK granularity.

    Supports:
    - Global defaults
    - Named policies with parent-based inheritance
    - Per-session overrides
    - Registration of tools to policies
    """

    def __init__(self, default_level: AccessLevel = AccessLevel.ASK) -> None:
        """
        Initialize the permission manager.

        Args:
            default_level: Default access level for unregistered tools.
        """
        self._default_level = default_level
        self._policies: dict[str, PermissionPolicy] = {}
        self._tool_to_policy: dict[str, str] = {}
        self._session_overrides: dict[str, dict[str, AccessLevel]] = {}

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def create_policy(
        self,
        name: str,
        default_level: AccessLevel = AccessLevel.ASK,
        parent_name: str | None = None,
    ) -> PermissionPolicy:
        """
        Create a new permission policy.

        Args:
            name: Unique policy name.
            default_level: Default access level for tools in this policy.
            parent_name: Optional parent policy name for inheritance.

        Returns:
            The created PermissionPolicy.

        Raises:
            ValueError: If a policy with this name already exists, or if
                parent_name refers to a non-existent policy.
        """
        if name in self._policies:
            raise ValueError(f"Policy '{name}' already exists")

        parent = None
        if parent_name is not None:
            parent = self._policies.get(parent_name)
            if parent is None:
                raise ValueError(f"Parent policy '{parent_name}' not found")

        policy = PermissionPolicy(
            name=name,
            default_level=default_level,
            parent=parent,
        )
        self._policies[name] = policy
        return policy

    def get_policy(self, name: str) -> PermissionPolicy | None:
        """
        Retrieve a policy by name.

        Args:
            name: Policy name.

        Returns:
            The PermissionPolicy or None.
        """
        return self._policies.get(name)

    def delete_policy(self, name: str) -> bool:
        """
        Delete a policy.

        Args:
            name: Policy name.

        Returns:
            True if deleted.
        """
        if name not in self._policies:
            return False

        # Remove tool registrations for this policy
        to_remove = [
            tool for tool, pname in self._tool_to_policy.items() if pname == name
        ]
        for tool in to_remove:
            del self._tool_to_policy[tool]

        del self._policies[name]
        return True

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tool(
        self,
        tool_name: str,
        policy_name: str | None = None,
        level: AccessLevel | None = None,
    ) -> None:
        """
        Register a tool with an optional policy or explicit level.

        Args:
            tool_name: Name of the tool.
            policy_name: Optional policy name to associate this tool with.
            level: Optional explicit level (takes priority over policy).

        Raises:
            ValueError: If the policy does not exist.
        """
        if policy_name is not None and policy_name not in self._policies:
            raise ValueError(f"Policy '{policy_name}' not found")

        if level is not None:
            # Explicit level — store in a special policy
            if "_explicit" not in self._policies:
                self._policies["_explicit"] = PermissionPolicy(
                    name="_explicit",
                    default_level=self._default_level,
                )
            self._policies["_explicit"].tools[tool_name] = level
            self._tool_to_policy[tool_name] = "_explicit"
        elif policy_name is not None:
            self._tool_to_policy[tool_name] = policy_name

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from registration.

        Args:
            tool_name: Name of the tool.

        Returns:
            True if the tool was registered.
        """
        return self._tool_to_policy.pop(tool_name, None) is not None

    # ------------------------------------------------------------------
    # Session overrides
    # ------------------------------------------------------------------

    def set_session_override(
        self,
        session_id: str,
        tool_name: str,
        level: AccessLevel,
    ) -> None:
        """
        Set a per-session permission override for a specific tool.

        Args:
            session_id: The session identifier.
            tool_name: The tool name.
            level: The overridden access level.
        """
        if session_id not in self._session_overrides:
            self._session_overrides[session_id] = {}
        self._session_overrides[session_id][tool_name] = level

    def clear_session_overrides(self, session_id: str) -> None:
        """
        Remove all overrides for a given session.

        Args:
            session_id: The session identifier.
        """
        self._session_overrides.pop(session_id, None)

    def clear_tool_override(self, session_id: str, tool_name: str) -> bool:
        """
        Remove a single override for a tool in a session.

        Args:
            session_id: The session identifier.
            tool_name: The tool name.

        Returns:
            True if the override existed and was removed.
        """
        overrides = self._session_overrides.get(session_id)
        if overrides and tool_name in overrides:
            del overrides[tool_name]
            return True
        return False

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def check(self, tool_name: str, session_id: str = "") -> PermissionResult:
        """
        Check whether a tool is allowed, optionally in a session context.

        Resolution order:
        1. Session override
        2. Tool-level policy or explicit level
        3. Policy default
        4. Global default

        Args:
            tool_name: Name of the tool to check.
            session_id: Optional session ID for per-session overrides.

        Returns:
            PermissionResult with resolved decision.
        """
        # 1. Check session override first
        if session_id:
            session_level = self._session_overrides.get(session_id, {}).get(tool_name)
            if session_level is not None:
                return PermissionResult(
                    allowed=session_level == AccessLevel.ALLOW,
                    level=session_level,
                    reason=f"Session override for '{tool_name}': {session_level.value}",
                )

        # 2. Check tool-to-policy mapping
        policy_name = self._tool_to_policy.get(tool_name)
        if policy_name is not None:
            policy = self._policies.get(policy_name)
            if policy is not None:
                level = policy.get_level(tool_name)
                return PermissionResult(
                    allowed=level == AccessLevel.ALLOW,
                    level=level,
                    reason=f"Policy '{policy_name}' for '{tool_name}': {level.value}",
                )

        # 3. Fall back to global default
        return PermissionResult(
            allowed=self._default_level == AccessLevel.ALLOW,
            level=self._default_level,
            reason=f"Global default for '{tool_name}': {self._default_level.value}",
        )

    def is_allowed(self, tool_name: str, session_id: str = "") -> bool:
        """
        Convenience: check if a tool is allowed.

        Args:
            tool_name: Name of the tool.
            session_id: Optional session ID.

        Returns:
            True if allowed.
        """
        return self.check(tool_name, session_id).allowed

    # ------------------------------------------------------------------
    # Bulk / introspection
    # ------------------------------------------------------------------

    def list_tools(self, policy_name: str | None = None) -> list[str]:
        """
        List all registered tool names, optionally filtered by policy.

        Args:
            policy_name: Optional policy filter.

        Returns:
            List of tool names.
        """
        if policy_name is not None:
            return [
                tool for tool, pname in self._tool_to_policy.items()
                if pname == policy_name
            ]
        return list(self._tool_to_policy.keys())

    def list_policies(self) -> list[str]:
        """List all policy names (excluding internal ones)."""
        return [
            name for name in self._policies
            if not name.startswith("_")
        ]

    def list_session_overrides(self, session_id: str) -> dict[str, AccessLevel]:
        """
        List all overrides for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Dict of tool name to AccessLevel.
        """
        return dict(self._session_overrides.get(session_id, {}))
