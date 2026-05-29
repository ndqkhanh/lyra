"""Multi-tenant bridge — tenant context propagation, credential vaults, and metadata tagging.

Lightweight module providing tenant isolation primitives:
  - TenantContext: propagates tenant identity through agent calls and workflows
  - TenantVault: per-tenant credential isolation wrapping the auth store
  - TenantMetadata: namespace-aware key-value tagging for routing/filtering
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TenantTier(str, Enum):
    """Service tier for resource allocation and rate limiting."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    INTERNAL = "internal"  # System-level tenants


@dataclass
class TenantMetadata:
    """Arbitrary key-value metadata attached to a tenant.

    Keys follow reverse-DNS convention (e.g. ``com.acme.department``)
    to prevent collisions across integrations.
    """

    data: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        return self.data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def delete(self, key: str) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False

    def prefixed(self, prefix: str) -> dict[str, str]:
        """Return all keys matching a namespace prefix."""
        return {k: v for k, v in self.data.items() if k.startswith(prefix)}

    def to_dict(self) -> dict[str, str]:
        return dict(self.data)


@dataclass
class TenantContext:
    """Propagated tenant identity through agent calls and workflows.

    Lightweight context object that flows alongside agent state.
    The tenant_id is immutable once set; metadata is mutable for
    runtime tagging.
    """

    tenant_id: str
    tier: TenantTier = TenantTier.FREE
    metadata: TenantMetadata = field(default_factory=TenantMetadata)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        tenant_id: str | None = None,
        *,
        tier: TenantTier = TenantTier.FREE,
        metadata: dict[str, str] | None = None,
    ) -> TenantContext:
        """Create a new tenant context.

        If tenant_id is omitted, a unique ID is generated.
        """
        tid = tenant_id or f"tenant_{uuid.uuid4().hex[:12]}"
        tmd = TenantMetadata(data=dict(metadata or {}))
        return cls(tenant_id=tid, tier=tier, metadata=tmd)

    @property
    def is_internal(self) -> bool:
        return self.tier == TenantTier.INTERNAL

    @property
    def is_enterprise(self) -> bool:
        return self.tier in (TenantTier.ENTERPRISE, TenantTier.INTERNAL)

    def tag(self, key: str, value: str) -> None:
        """Add a runtime metadata tag."""
        self.metadata.set(key, value)

    def has_tag(self, key: str) -> bool:
        return bool(self.metadata.get(key))

    def summary(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "tier": self.tier.value,
            "metadata_keys": list(self.metadata.data.keys()),
            "created_at": self.created_at,
        }


class TenantVault:
    """Per-tenant credential isolation.

    Wraps the file-based auth store with tenant-scoped credential
    resolution. Each tenant gets its own sub-directory under
    ``~/.lyra/tenants/{tenant_id}/``.

    Credential resolution order:
      1. ``{PROVIDER}_API_KEY`` env var (global override)
      2. Tenant-specific ``~/.lyra/tenants/{tenant_id}/auth.json``
      3. Global ``~/.lyra/auth.json`` (fallback)
    """

    def __init__(self, tenant_id: str, base_dir: str | None = None) -> None:
        self.tenant_id = tenant_id
        self._base_dir = base_dir or self._default_base()

    @staticmethod
    def _default_base() -> str:
        lyra_home = os.environ.get("LYRA_HOME", os.path.expanduser("~/.lyra"))
        return os.path.join(lyra_home, "tenants")

    @property
    def tenant_dir(self) -> str:
        return os.path.join(self._base_dir, self.tenant_id)

    @property
    def auth_path(self) -> str:
        return os.path.join(self.tenant_dir, "auth.json")

    @property
    def metadata_path(self) -> str:
        return os.path.join(self.tenant_dir, "metadata.json")

    def ensure_dir(self) -> str:
        """Create the tenant directory if it doesn't exist."""
        os.makedirs(self.tenant_dir, mode=0o700, exist_ok=True)
        return self.tenant_dir

    def exists(self) -> bool:
        return os.path.isdir(self.tenant_dir)

    def delete(self) -> bool:
        """Remove the tenant vault entirely. Returns False if it didn't exist."""
        import shutil

        if not self.exists():
            return False
        shutil.rmtree(self.tenant_dir)
        return True

    def list_tenants(self) -> list[str]:
        """List all tenant IDs that have vault directories."""
        try:
            return sorted(os.listdir(self._base_dir))
        except FileNotFoundError:
            return []


class TenantBridge:
    """Lightweight bridge for tenant-aware context propagation.

    Manages tenant registration, lookup, and cross-tenant routing.
    In-memory registry with optional persistence via TenantVault.

    Usage::

        bridge = TenantBridge()
        ctx = bridge.register("acme-corp", tier=TenantTier.ENTERPRISE)
        assert bridge.resolve("acme-corp") is ctx
        bridge.tag(ctx, "com.acme.department", "engineering")
    """

    def __init__(self) -> None:
        self._tenants: dict[str, TenantContext] = {}

    def register(
        self,
        tenant_id: str,
        *,
        tier: TenantTier = TenantTier.FREE,
        metadata: dict[str, str] | None = None,
    ) -> TenantContext:
        """Register a new tenant or return existing."""
        if tenant_id in self._tenants:
            return self._tenants[tenant_id]
        ctx = TenantContext.create(tenant_id, tier=tier, metadata=metadata)
        self._tenants[tenant_id] = ctx
        return ctx

    def resolve(self, tenant_id: str) -> TenantContext | None:
        """Look up a tenant by ID."""
        return self._tenants.get(tenant_id)

    def remove(self, tenant_id: str) -> bool:
        """Remove a tenant from the registry."""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            return True
        return False

    def tag(self, ctx: TenantContext, key: str, value: str) -> None:
        """Tag a tenant context with metadata."""
        ctx.tag(key, value)

    def find_by_tag(self, key: str, value: str) -> list[TenantContext]:
        """Find all tenants matching a metadata tag."""
        return [
            ctx for ctx in self._tenants.values()
            if ctx.metadata.get(key) == value
        ]

    def find_by_tier(self, tier: TenantTier) -> list[TenantContext]:
        """Find all tenants at a given tier."""
        return [ctx for ctx in self._tenants.values() if ctx.tier == tier]

    def count(self) -> int:
        return len(self._tenants)

    def list_ids(self) -> list[str]:
        return sorted(self._tenants.keys())

    def summary(self) -> dict[str, Any]:
        return {
            "total_tenants": len(self._tenants),
            "by_tier": {
                tier.value: len(self.find_by_tier(tier))
                for tier in TenantTier
            },
            "tenant_ids": self.list_ids(),
        }
