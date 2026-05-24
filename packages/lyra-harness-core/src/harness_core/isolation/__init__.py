"""harness_core.isolation — per-namespace context isolation.

Per [docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md) §3.2
("system-as-user" projects use per-runbook context isolation in place of ICPEA
personal memory) and [docs/206-collaborative-ai-canon-2026.md]
(../../../../../../research/harness-engineering/docs/206-collaborative-ai-canon-2026.md) §1
(per-agent layer access control).

The structural answer to "no ICPEA" — context lives in named, scoped buckets;
cross-namespace reads require explicit permission grants; default behaviour is
fail-closed across boundaries.

Used by:
    Aegis-Ops — per-runbook isolation.
    Cipher-Sec — per-engagement scope.
    Multi-tenant deployments — per-tenant data isolation.
    Mentat-Learn channels — per-channel ICPEA layers (compose with isolation).
"""
from __future__ import annotations

from .context_namespace import (
    ContextNamespace,
    IsolatedContext,
    NamespacePermission,
    PermissionGrant,
    register_grant,
)

__all__ = [
    "ContextNamespace",
    "IsolatedContext",
    "NamespacePermission",
    "PermissionGrant",
    "register_grant",
]
