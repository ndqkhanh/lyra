"""Enterprise Settings Hierarchy --- 4-tier scope with deny-first permission
evaluation and priority-based resolution.

Priority order (highest to lowest): managed > CLI > local > project > user.

Managed settings are enforced via file-based policy fragments (JSON / YAML) that
are loaded into deny-first :class:`PolicyRule` objects.  All other scopes are
free-form and resolved by walking the hierarchy from highest to lowest priority.

Usage::

    hierarchy = SettingsHierarchy()
    hierarchy.set_value("theme", "dark", SettingScope.USER)
    hierarchy.set_value("theme", "light", SettingScope.CLI)
    assert hierarchy.get_effective_value("theme") == "light"

    policy = ManagedPolicy(
        policy_id="ui-restrictions",
        rules=(
            PolicyRule(
                key_pattern="theme",
                allowed_values=("light", "dark"),
                deny_message="Theme must be light or dark",
            ),
        ),
        description="UI theme restrictions",
    )
    hierarchy.apply_managed_policy(policy)
    allowed, reason = hierarchy.check_policy("theme", "neon")
    assert not allowed
"""
from __future__ import annotations

import fnmatch
import json
import logging
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SettingsError(Exception):
    """Raised when a settings operation cannot be completed (locked value,
    unknown key, invalid policy fragment, etc.)."""


class LockedSettingError(SettingsError):
    """Raised when attempting to set or delete a value that has been locked
    by a higher-priority scope."""


class PolicyViolationError(SettingsError):
    """Raised when a value is rejected by a managed policy rule."""


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class SettingScope(IntEnum):
    """Priority-ordered setting scopes.

    Lower integer values represent **higher** priority.
    ``MANAGED`` (0) > ``CLI`` (1) > ``LOCAL`` (2) > ``PROJECT`` (3) > ``USER`` (4).
    """

    MANAGED = 0
    CLI = 1
    LOCAL = 2
    PROJECT = 3
    USER = 4


@dataclass(frozen=True)
class SettingValue:
    """An individual setting stored at a specific scope."""

    value: Any
    """The actual setting value (any JSON-serializable type)."""

    source: SettingScope
    """The scope at which this value was set."""

    is_locked: bool = False
    """When ``True``, higher-priority scopes prevent lower scopes from
    overriding this key."""

    description: str = ""
    """Human-readable explanation of what this setting controls."""


@dataclass(frozen=True)
class SettingOverride:
    """A record of a key being set at a particular scope, used to report
    all active overrides for a given key."""

    key: str
    """The setting key that was overridden."""

    value: SettingValue
    """The value (and its scope metadata) stored at this override level."""

    reason: str = ""
    """Optional explanation of why this override exists."""


@dataclass(frozen=True)
class PolicyRule:
    """A single deny-first rule within a managed policy.

    If a key matches ``key_pattern`` (via ``fnmatch``) **and** its value is
    *not* in ``allowed_values``, the value is denied.
    """

    key_pattern: str
    """Glob-style pattern matched against setting keys (e.g. ``theme.*``)."""

    allowed_values: tuple[Any, ...]
    """Values that are permitted for keys matching ``key_pattern``."""

    deny_message: str = ""
    """Message returned when a value is denied by this rule."""


@dataclass(frozen=True)
class ManagedPolicy:
    """A named collection of :class:`PolicyRule` objects loaded from a single
    policy fragment (JSON / YAML file)."""

    policy_id: str
    """Unique identifier for this policy (used in log messages)."""

    rules: tuple[PolicyRule, ...]
    """Ordered sequence of rules evaluated in declaration order."""

    description: str = ""
    """Human-readable description of the policy's purpose."""


# ---------------------------------------------------------------------------
# SettingsHierarchy
# ---------------------------------------------------------------------------


class SettingsHierarchy:
    """Four-tier settings store with priority-based resolution and deny-first
    policy enforcement.

    Internal storage is a two-level mapping::

        dict[str, dict[SettingScope, SettingValue]]

    Each key maps to a per-scope dictionary.  Resolution walks scopes from
    ``MANAGED`` (highest priority) to ``USER`` (lowest) and returns the first
    match.
    """

    #: Scopes in priority order (highest first).
    _SCOPES_ORDERED: tuple[SettingScope, ...] = (
        SettingScope.MANAGED,
        SettingScope.CLI,
        SettingScope.LOCAL,
        SettingScope.PROJECT,
        SettingScope.USER,
    )

    def __init__(self) -> None:
        # Per-key, per-scope value registry.
        self._registry: dict[str, dict[SettingScope, SettingValue]] = {}
        # Ordered list of managed policies (evaluated in FIFO order).
        self._policies: list[ManagedPolicy] = []

    # ------------------------------------------------------------------ set_value
    def set_value(
        self,
        key: str,
        value: Any,
        scope: SettingScope,
        *,
        description: str = "",
    ) -> SettingValue:
        """Store a setting at the given scope.

        Parameters
        ----------
        key : str
            Setting key (e.g. ``"theme"``, ``"editor.font_size"``).
        value : Any
            Value to store.
        scope : SettingScope
            Scope at which to store the value.
        description : str, optional
            Human-readable description of the setting.

        Returns
        -------
        SettingValue
            The newly created setting.

        Raises
        ------
        LockedSettingError
            If a higher-priority scope has locked this key.

        PolicyViolationError
            If the value is denied by a managed policy rule and the setting
            is being stored at ``MANAGED`` scope.
        """
        # Check higher-scope locks.
        self._check_locks(key, scope)

        # If this is a managed setting, validate against policy.
        if scope is SettingScope.MANAGED:
            allowed, reason = self.check_policy(key, value)
            if not allowed:
                raise PolicyViolationError(reason)

        setting = SettingValue(
            value=value,
            source=scope,
            description=description,
        )
        self._registry.setdefault(key, {})[scope] = setting
        logger.debug("set %s=%r at %s", key, value, scope.name)
        return setting

    # ------------------------------------------------------------------ get_value
    def get_value(self, key: str) -> SettingValue | None:
        """Resolve a setting through the scope hierarchy by priority.

        Returns the highest-priority value for *key*, or ``None`` if the key
        has never been set at any scope.

        Parameters
        ----------
        key : str
            Setting key to look up.

        Returns
        -------
        SettingValue or None
        """
        scopes = self._registry.get(key)
        if scopes is None:
            return None
        for scope in self._SCOPES_ORDERED:
            if scope in scopes:
                return scopes[scope]
        return None

    # --------------------------------------------------------- get_effective_value
    def get_effective_value(self, key: str) -> Any:
        """Return the raw value of the highest-priority setting for *key*.

        Equivalent to ``get_value(key).value`` but returns ``None`` when the
        key is not found, avoiding an ``AttributeError``.

        Parameters
        ----------
        key : str
            Setting key to look up.

        Returns
        -------
        Any or None
        """
        sv = self.get_value(key)
        return sv.value if sv is not None else None

    # --------------------------------------------------------------- delete_value
    def delete_value(self, key: str, scope: SettingScope) -> bool:
        """Remove a setting at the given scope.

        Parameters
        ----------
        key : str
            Setting key to delete.
        scope : SettingScope
            Scope from which to remove the value.

        Returns
        -------
        bool
            ``True`` if a value was removed, ``False`` if the key did not
            exist at the given scope.

        Raises
        ------
        LockedSettingError
            If a higher-priority scope has locked this key.
        """
        self._check_locks(key, scope)
        scopes = self._registry.get(key)
        if scopes is None or scope not in scopes:
            return False
        del scopes[scope]
        if not scopes:
            del self._registry[key]
        logger.debug("deleted %s from %s", key, scope.name)
        return True

    # ---------------------------------------------------------------- lock_value
    def lock_value(self, key: str, scope: SettingScope) -> SettingValue:
        """Lock a setting so that lower-priority scopes cannot override it.

        Once locked, any subsequent call to :meth:`set_value` or
        :meth:`delete_value` at a *lower* scope will raise
        :class:`LockedSettingError`.

        Parameters
        ----------
        key : str
            Setting key to lock.
        scope : SettingScope
            Scope at which to apply the lock.

        Returns
        -------
        SettingValue
            The updated (locked) value.

        Raises
        ------
        SettingsError
            If no value exists for *key* at *scope*.
        """
        existing = self._registry.get(key, {}).get(scope)
        if existing is None:
            raise SettingsError(
                f"Cannot lock '{key}': no value set at {scope.name}"
            )
        locked = SettingValue(
            value=existing.value,
            source=existing.source,
            is_locked=True,
            description=existing.description,
        )
        self._registry[key][scope] = locked
        logger.info("locked %s at %s", key, scope.name)
        return locked

    # -------------------------------------------------------- apply_managed_policy
    def apply_managed_policy(self, policy: ManagedPolicy) -> None:
        """Register a managed policy for deny-first evaluation.

        Policies are evaluated in FIFO order.  All rules from the given
        policy are added to the internal rule list.

        Parameters
        ----------
        policy : ManagedPolicy
            The policy to register.
        """
        self._policies.append(policy)
        logger.info("applied policy %s (%d rules)", policy.policy_id, len(policy.rules))

    # ------------------------------------------------------- load_policy_fragment
    def load_policy_fragment(self, file_path: str) -> ManagedPolicy:
        """Load a :class:`ManagedPolicy` from a JSON or YAML file.

        Expected format::

            {
                "policy_id": "ui-restrictions",
                "description": "Restrict UI theme values",
                "rules": [
                    {
                        "key_pattern": "theme",
                        "allowed_values": ["light", "dark"],
                        "deny_message": "Theme must be light or dark"
                    }
                ]
            }

        Parameters
        ----------
        file_path : str
            Path to the JSON or YAML file (``.json`` / ``.yaml`` / ``.yml``).

        Returns
        -------
        ManagedPolicy
            The deserialized policy, ready for :meth:`apply_managed_policy`.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the format is unsupported.
        ImportError
            If the file is YAML but ``PyYAML`` is not installed.
        """
        path = Path(file_path)
        raw = path.read_text(encoding="utf-8")

        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            if _yaml is None:
                raise ImportError(
                    "PyYAML is required to load YAML policy fragments. "
                    "Install it with: pip install pyyaml"
                )
            data = _yaml.safe_load(raw)
        elif suffix == ".json":
            data = json.loads(raw)
        else:
            raise ValueError(
                f"Unsupported policy fragment format '{suffix}'. "
                f"Use .json, .yaml, or .yml."
            )

        rules = tuple(
            PolicyRule(
                key_pattern=r["key_pattern"],
                allowed_values=tuple(r["allowed_values"]),
                deny_message=r.get("deny_message", ""),
            )
            for r in data["rules"]
        )

        policy = ManagedPolicy(
            policy_id=data["policy_id"],
            rules=rules,
            description=data.get("description", ""),
        )
        logger.info("loaded policy fragment '%s' from %s", policy.policy_id, file_path)
        return policy

    # --------------------------------------------------------------- check_policy
    def check_policy(self, key: str, value: Any) -> tuple[bool, str]:
        """Evaluate *value* against all registered managed policies.

        Deny-first logic: if **any** policy rule matches the key **and** the
        value is *not* in that rule's ``allowed_values``, the check fails.

        Parameters
        ----------
        key : str
            Setting key to check.
        value : Any
            Proposed value to validate.

        Returns
        -------
        tuple of (bool, str)
            ``(True, "")`` if the value is allowed; ``(False, deny_message)``
            if denied.
        """
        for policy in self._policies:
            for rule in policy.rules:
                if fnmatch.fnmatch(key, rule.key_pattern):
                    if value not in rule.allowed_values:
                        msg = rule.deny_message or (
                            f"Value {value!r} not allowed for '{key}' "
                            f"(pattern '{rule.key_pattern}')"
                        )
                        logger.debug("policy denied %s=%r: %s", key, value, msg)
                        return (False, msg)
        return (True, "")

    # ------------------------------------------------------------- export_settings
    def export_settings(self, scope: SettingScope) -> dict[str, Any]:
        """Export all settings whose source scope is *at or above* the given
        priority threshold.

        For each key, the highest-priority value from the permitted scopes
        is included.

        Parameters
        ----------
        scope : SettingScope
            Only include settings from scopes whose priority is *at or above*
            this scope (i.e. the same or higher authority).

        Returns
        -------
        dict
            Flat key-value mapping of exported settings.
        """
        result: dict[str, Any] = {}
        for key, scopes in self._registry.items():
            for s in self._SCOPES_ORDERED:
                if s in scopes and s.value <= scope.value:
                    result[key] = scopes[s].value
                    break
        return result

    # -------------------------------------------------------------- list_overrides
    def list_overrides(self, key: str) -> list[SettingOverride]:
        """List all scopes that have set *key*, sorted from highest to lowest
        priority.

        Parameters
        ----------
        key : str
            Setting key to inspect.

        Returns
        -------
        list of SettingOverride
            Empty list if the key has never been set.
        """
        scopes = self._registry.get(key)
        if scopes is None:
            return []
        overrides: list[SettingOverride] = []
        for scope in self._SCOPES_ORDERED:
            sv = scopes.get(scope)
            if sv is not None:
                overrides.append(
                    SettingOverride(
                        key=key,
                        value=sv,
                        reason=f"Set at {scope.name} scope",
                    )
                )
        return overrides

    # ---------------------------------------------------------------- clear_scope
    def clear_scope(self, scope: SettingScope) -> int:
        """Remove **all** settings stored at the given scope.

        Parameters
        ----------
        scope : SettingScope
            Scope to clear.

        Returns
        -------
        int
            Number of settings removed.
        """
        count = 0
        keys_to_purge: list[str] = []
        for key, scopes in self._registry.items():
            if scope in scopes:
                del scopes[scope]
                count += 1
            if not scopes:
                keys_to_purge.append(key)
        for key in keys_to_purge:
            del self._registry[key]
        if count:
            logger.info("cleared %d setting(s) from %s", count, scope.name)
        return count

    # ------------------------------------------------------------------- helpers
    def _check_locks(self, key: str, scope: SettingScope) -> None:
        """Raise :class:`LockedSettingError` if a higher-priority scope has
        locked *key*.

        Iterates from MANAGED to one scope above *scope* and checks if any
        of them has a locked value for *key*.
        """
        scopes = self._registry.get(key)
        if scopes is None:
            return
        for higher in self._SCOPES_ORDERED:
            if higher.value >= scope.value:
                break
            existing = scopes.get(higher)
            if existing is not None and existing.is_locked:
                raise LockedSettingError(
                    f"Cannot modify '{key}' at {scope.name}: "
                    f"locked by {higher.name}"
                )

    def __repr__(self) -> str:  # pragma: no cover
        keys = len(self._registry)
        policies = len(self._policies)
        return f"<SettingsHierarchy keys={keys} policies={policies}>"


__all__ = [
    # Exceptions
    "LockedSettingError",
    "PolicyViolationError",
    "SettingsError",
    # Enums
    "SettingScope",
    # Data classes
    "SettingValue",
    "SettingOverride",
    "PolicyRule",
    "ManagedPolicy",
    # Primary class
    "SettingsHierarchy",
]
