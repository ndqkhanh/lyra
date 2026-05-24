"""ContextNamespace + IsolatedContext — fail-closed-across-namespaces context.

Each context bucket is keyed by a namespace id; cross-namespace reads require
an explicit :class:`PermissionGrant`. Default semantics are fail-closed: a
read against a namespace you don't own and don't have a grant for raises
:class:`PermissionError`.

The namespace hierarchy supports parent-child relationships. A child namespace
inherits its parent's grants only when explicitly opted in (``inherit_grants``).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class NamespacePermission(str, enum.Enum):
    """The granted operations a foreign namespace may perform."""

    READ = "read"
    WRITE = "write"
    LIST = "list"  # may enumerate keys but not read values


@dataclass(frozen=True)
class PermissionGrant:
    """Source-namespace → target-namespace grant of a permission set.

    Grants are *one-way*: granting source=A → target=B does NOT permit B → A.
    Asymmetric by design; symmetric grants require two records.
    """

    source_namespace: str
    target_namespace: str
    permissions: frozenset[NamespacePermission]
    reason: str = ""

    def allows(self, perm: NamespacePermission) -> bool:
        return perm in self.permissions


@dataclass
class ContextNamespace:
    """A named, scoped context bucket.

    ``parent`` is for hierarchical namespaces (e.g. tenant/runbook/incident).
    ``inherit_grants`` controls whether the namespace can use its parent's
    grants (default off — explicit opt-in for safety).
    """

    namespace_id: str
    parent: Optional[str] = None
    inherit_grants: bool = False

    def __post_init__(self) -> None:
        if not self.namespace_id or not self.namespace_id.strip():
            raise ValueError("namespace_id must be non-empty")


# Module-level grant registry. Real deployments wire through a permission
# service; in-process this is the canonical store.
_GRANTS: dict[tuple[str, str], list[PermissionGrant]] = {}


def register_grant(grant: PermissionGrant) -> None:
    """Add a grant to the in-process registry."""
    key = (grant.source_namespace, grant.target_namespace)
    _GRANTS.setdefault(key, []).append(grant)


def _resolve_grant(
    *,
    source_ns: str,
    target_ns: str,
    perm: NamespacePermission,
) -> Optional[PermissionGrant]:
    grants = _GRANTS.get((source_ns, target_ns), [])
    for g in grants:
        if g.allows(perm):
            return g
    return None


def _clear_grants_for_test() -> None:
    """Test-only helper to reset the registry."""
    _GRANTS.clear()


@dataclass
class IsolatedContext:
    """A typed key-value context, scoped to a namespace.

    Every read/write checks the namespace + grants. Cross-namespace reads
    via :meth:`cross_read` raise PermissionError when no grant exists.

    >>> ns = ContextNamespace(namespace_id="runbook-1")
    >>> ctx = IsolatedContext(namespace=ns)
    >>> ctx.put("alert_id", "ALERT-1234")
    >>> ctx.get("alert_id")
    'ALERT-1234'
    """

    namespace: ContextNamespace
    _data: dict[str, Any] = field(default_factory=dict, init=False)

    @property
    def namespace_id(self) -> str:
        return self.namespace.namespace_id

    def put(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("key must be non-empty")
        self._data[key] = value

    def get(self, key: str, *, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def cross_read(
        self,
        *,
        other: "IsolatedContext",
        key: str,
        default: Any = None,
    ) -> Any:
        """Read a key from a different namespace.

        Requires a :class:`PermissionGrant` from the other namespace
        (source) to this one (target) for :class:`NamespacePermission.READ`,
        or this is a parent-child read with ``inherit_grants=True``.
        """
        if other.namespace_id == self.namespace_id:
            return other.get(key, default=default)

        if self._can_inherit_from(other):
            return other.get(key, default=default)

        grant = _resolve_grant(
            source_ns=other.namespace_id,
            target_ns=self.namespace_id,
            perm=NamespacePermission.READ,
        )
        if grant is None:
            raise PermissionError(
                f"namespace {self.namespace_id!r} cannot read from "
                f"{other.namespace_id!r}: no grant for READ"
            )
        return other.get(key, default=default)

    def cross_list(self, *, other: "IsolatedContext") -> list[str]:
        """List keys in another namespace; requires LIST grant.

        Use case: a supervisor sub-agent enumerates the runbook's known facts
        to decide whether to escalate.
        """
        if other.namespace_id == self.namespace_id:
            return other.keys()
        if self._can_inherit_from(other):
            return other.keys()
        grant = _resolve_grant(
            source_ns=other.namespace_id,
            target_ns=self.namespace_id,
            perm=NamespacePermission.LIST,
        )
        if grant is None:
            raise PermissionError(
                f"namespace {self.namespace_id!r} cannot list "
                f"{other.namespace_id!r}: no grant for LIST"
            )
        return other.keys()

    def _can_inherit_from(self, other: "IsolatedContext") -> bool:
        """True if this namespace inherits from ``other`` (parent-child)."""
        if not self.namespace.inherit_grants:
            return False
        return self.namespace.parent == other.namespace_id


__all__ = [
    "ContextNamespace",
    "IsolatedContext",
    "NamespacePermission",
    "PermissionGrant",
    "register_grant",
]
