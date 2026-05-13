"""Access Policy Graph — collaborative memory with ACL enforcement (Phase M6).

Implements a bipartite graph connecting users, agents, and memory resources with
fine-grained access control. Supports:
  - User-level permissions (read/write/promote/delete)
  - Agent-level permissions (scoped to tasks/sessions)
  - Resource-level ACLs (per-fragment, per-tier)
  - Promotion gates (T1→T2, T2→T3) with approval workflows

Key design:
  - Policy graph stored as adjacency list: (subject, resource) → permissions
  - Subjects: user_id, agent_id, or role (e.g., "orchestrator", "sub-agent")
  - Resources: fragment_id, tier, or wildcard patterns
  - Permissions: READ, WRITE, PROMOTE, DELETE
  - Promotion gates: require explicit approval before T1→T2 or T2→T3

Integration:
  - Wire into memory/store.py: check_access() before read/write/promote
  - Wire into memory/lifecycle.py: enforce promotion gates
  - Wire into observability/event_bus.py: log access denials

Research grounding:
  - Design proposal §8 collaborative memory and access control
  - Multi-agent coordination requires isolation and controlled sharing
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

from .schema import Fragment, MemoryTier


# ---------------------------------------------------------------------------
# Permission types
# ---------------------------------------------------------------------------


class Permission(str, Enum):
    """Access control permissions."""

    READ = "read"
    WRITE = "write"
    PROMOTE = "promote"
    DELETE = "delete"


# ---------------------------------------------------------------------------
# Policy graph nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subject:
    """A subject in the policy graph (user, agent, or role)."""

    type: Literal["user", "agent", "role"]
    id: str

    @classmethod
    def user(cls, user_id: str) -> Subject:
        return cls(type="user", id=user_id)

    @classmethod
    def agent(cls, agent_id: str) -> Subject:
        return cls(type="agent", id=agent_id)

    @classmethod
    def role(cls, role_name: str) -> Subject:
        return cls(type="role", id=role_name)


@dataclass(frozen=True)
class Resource:
    """A resource in the policy graph (fragment, tier, or pattern)."""

    type: Literal["fragment", "tier", "pattern"]
    id: str

    @classmethod
    def fragment(cls, fragment_id: str) -> Resource:
        return cls(type="fragment", id=fragment_id)

    @classmethod
    def tier(cls, tier: MemoryTier) -> Resource:
        return cls(type="tier", id=tier.value)

    @classmethod
    def pattern(cls, pattern: str) -> Resource:
        """Wildcard pattern (e.g., 'task:123:*', 'agent:*')."""
        return cls(type="pattern", id=pattern)


# ---------------------------------------------------------------------------
# Access control list
# ---------------------------------------------------------------------------


@dataclass
class ACLEntry:
    """A single ACL entry: (subject, resource) → permissions."""

    subject: Subject
    resource: Resource
    permissions: set[Permission] = field(default_factory=set)
    granted_at: datetime = field(default_factory=datetime.now)
    granted_by: str = "system"

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions


# ---------------------------------------------------------------------------
# Policy graph
# ---------------------------------------------------------------------------


class PolicyGraph:
    """Bipartite graph connecting subjects (users/agents) to resources (fragments/tiers).

    Thread-safe. Supports:
      - grant(subject, resource, permissions): add ACL entry
      - revoke(subject, resource, permissions): remove permissions
      - check_access(subject, resource, permission): verify access
      - list_permissions(subject): get all permissions for a subject
      - list_subjects(resource): get all subjects with access to a resource
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (subject, resource) → ACLEntry
        self._acls: dict[tuple[Subject, Resource], ACLEntry] = {}
        # subject → set of resources
        self._subject_index: dict[Subject, set[Resource]] = {}
        # resource → set of subjects
        self._resource_index: dict[Resource, set[Subject]] = {}

    def grant(
        self,
        subject: Subject,
        resource: Resource,
        permissions: set[Permission],
        granted_by: str = "system",
    ) -> None:
        """Grant permissions to a subject for a resource."""
        with self._lock:
            key = (subject, resource)
            if key in self._acls:
                # Merge with existing permissions
                self._acls[key].permissions.update(permissions)
            else:
                # Create new ACL entry
                entry = ACLEntry(
                    subject=subject,
                    resource=resource,
                    permissions=permissions.copy(),
                    granted_by=granted_by,
                )
                self._acls[key] = entry
                # Update indexes
                if subject not in self._subject_index:
                    self._subject_index[subject] = set()
                self._subject_index[subject].add(resource)
                if resource not in self._resource_index:
                    self._resource_index[resource] = set()
                self._resource_index[resource].add(subject)

    def revoke(
        self,
        subject: Subject,
        resource: Resource,
        permissions: set[Permission] | None = None,
    ) -> None:
        """Revoke permissions from a subject for a resource.

        If permissions is None, revoke all permissions (remove ACL entry).
        """
        with self._lock:
            key = (subject, resource)
            if key not in self._acls:
                return

            if permissions is None:
                # Remove entire ACL entry
                del self._acls[key]
                self._subject_index[subject].discard(resource)
                self._resource_index[resource].discard(subject)
            else:
                # Remove specific permissions
                self._acls[key].permissions.difference_update(permissions)
                # If no permissions left, remove entry
                if not self._acls[key].permissions:
                    del self._acls[key]
                    self._subject_index[subject].discard(resource)
                    self._resource_index[resource].discard(subject)

    def check_access(
        self,
        subject: Subject,
        resource: Resource,
        permission: Permission,
    ) -> bool:
        """Check if subject has permission for resource.

        Supports pattern matching: if resource is a fragment, check:
          1. Direct fragment permission
          2. Tier-level permission
          3. Pattern-based permission (e.g., 'task:123:*')
        """
        with self._lock:
            # Direct match
            key = (subject, resource)
            if key in self._acls and self._acls[key].has_permission(permission):
                return True

            # Tier-level match (if resource is a fragment)
            if resource.type == "fragment":
                # Extract tier from fragment_id (format: "tier:type:uuid")
                # Map short tier prefix to full MemoryTier enum value
                tier_map = {
                    "t0": MemoryTier.T0_WORKING,
                    "t1": MemoryTier.T1_SESSION,
                    "t2": MemoryTier.T2_SEMANTIC,  # or T2_PROCEDURAL
                    "t3": MemoryTier.T3_USER,  # or T3_TEAM
                }
                parts = resource.id.split(":", 1)
                if len(parts) >= 1 and parts[0] in tier_map:
                    tier_resource = Resource.tier(tier_map[parts[0]])
                    tier_key = (subject, tier_resource)
                    if tier_key in self._acls and self._acls[tier_key].has_permission(
                        permission
                    ):
                        return True

            # Pattern-based match
            for (subj, res), entry in self._acls.items():
                if subj != subject:
                    continue
                if res.type == "pattern" and self._matches_pattern(
                    resource.id, res.id
                ):
                    if entry.has_permission(permission):
                        return True

            return False

    def list_permissions(self, subject: Subject) -> list[ACLEntry]:
        """Get all ACL entries for a subject."""
        with self._lock:
            return [
                entry
                for (subj, _), entry in self._acls.items()
                if subj == subject
            ]

    def list_subjects(self, resource: Resource) -> list[Subject]:
        """Get all subjects with access to a resource."""
        with self._lock:
            return list(self._resource_index.get(resource, set()))

    def clear(self) -> None:
        """Clear all ACL entries (test isolation)."""
        with self._lock:
            self._acls.clear()
            self._subject_index.clear()
            self._resource_index.clear()

    @staticmethod
    def _matches_pattern(resource_id: str, pattern: str) -> bool:
        """Check if resource_id matches a wildcard pattern.

        Supports:
          - 'task:123:*' matches 'task:123:fragment-1', 'task:123:fragment-2'
          - 'agent:*' matches 'agent:1', 'agent:2'
          - '*' matches everything
        """
        if pattern == "*":
            return True
        if "*" not in pattern:
            return resource_id == pattern

        # Simple prefix matching for 'prefix:*' patterns
        if pattern.endswith(":*"):
            prefix = pattern[:-2]
            return resource_id.startswith(prefix + ":")

        # More complex patterns (not implemented yet)
        return False


# ---------------------------------------------------------------------------
# Promotion gates
# ---------------------------------------------------------------------------


@dataclass
class PromotionRequest:
    """A request to promote a fragment from one tier to another."""

    fragment_id: str
    from_tier: MemoryTier
    to_tier: MemoryTier
    requested_by: str
    requested_at: datetime = field(default_factory=datetime.now)
    status: Literal["pending", "approved", "rejected"] = "pending"
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class PromotionGate:
    """Manages promotion requests and approval workflows.

    Promotion gates enforce human-in-the-loop approval for:
      - T1 (Session) → T2 (Semantic/Procedural)
      - T2 (Semantic/Procedural) → T3 (User/Team)

    T0 (Working) → T1 (Session) is automatic (no gate).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # fragment_id → PromotionRequest
        self._requests: dict[str, PromotionRequest] = {}

    def request_promotion(
        self,
        fragment_id: str,
        from_tier: MemoryTier,
        to_tier: MemoryTier,
        requested_by: str,
    ) -> PromotionRequest:
        """Submit a promotion request."""
        with self._lock:
            request = PromotionRequest(
                fragment_id=fragment_id,
                from_tier=from_tier,
                to_tier=to_tier,
                requested_by=requested_by,
            )
            self._requests[fragment_id] = request
            return request

    def approve(
        self,
        fragment_id: str,
        approved_by: str,
    ) -> PromotionRequest | None:
        """Approve a promotion request."""
        with self._lock:
            request = self._requests.get(fragment_id)
            if request is None or request.status != "pending":
                return None
            request.status = "approved"
            request.approved_by = approved_by
            request.approved_at = datetime.now()
            return request

    def reject(
        self,
        fragment_id: str,
        rejected_by: str,
        reason: str,
    ) -> PromotionRequest | None:
        """Reject a promotion request."""
        with self._lock:
            request = self._requests.get(fragment_id)
            if request is None or request.status != "pending":
                return None
            request.status = "rejected"
            request.approved_by = rejected_by
            request.approved_at = datetime.now()
            request.rejection_reason = reason
            return request

    def get_request(self, fragment_id: str) -> PromotionRequest | None:
        """Get a promotion request by fragment_id."""
        with self._lock:
            return self._requests.get(fragment_id)

    def list_pending(self) -> list[PromotionRequest]:
        """List all pending promotion requests."""
        with self._lock:
            return [
                req for req in self._requests.values() if req.status == "pending"
            ]

    def clear(self) -> None:
        """Clear all promotion requests (test isolation)."""
        with self._lock:
            self._requests.clear()


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------


_POLICY_GRAPH: PolicyGraph | None = None
_PROMOTION_GATE: PromotionGate | None = None
_LOCK = threading.Lock()


def get_policy_graph() -> PolicyGraph:
    """Return the global singleton PolicyGraph, creating it on first call."""
    global _POLICY_GRAPH
    if _POLICY_GRAPH is None:
        with _LOCK:
            if _POLICY_GRAPH is None:
                _POLICY_GRAPH = PolicyGraph()
    return _POLICY_GRAPH


def get_promotion_gate() -> PromotionGate:
    """Return the global singleton PromotionGate, creating it on first call."""
    global _PROMOTION_GATE
    if _PROMOTION_GATE is None:
        with _LOCK:
            if _PROMOTION_GATE is None:
                _PROMOTION_GATE = PromotionGate()
    return _PROMOTION_GATE


def reset_policy_graph() -> None:
    """Reset the global singleton (test isolation only)."""
    global _POLICY_GRAPH
    with _LOCK:
        _POLICY_GRAPH = None


def reset_promotion_gate() -> None:
    """Reset the global singleton (test isolation only)."""
    global _PROMOTION_GATE
    with _LOCK:
        _PROMOTION_GATE = None


__all__ = [
    "Permission",
    "Subject",
    "Resource",
    "ACLEntry",
    "PolicyGraph",
    "PromotionRequest",
    "PromotionGate",
    "get_policy_graph",
    "get_promotion_gate",
    "reset_policy_graph",
    "reset_promotion_gate",
]

