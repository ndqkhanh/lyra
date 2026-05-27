"""MCP Server Surface for CoALA Memory Architecture (Phase M7).

Exposes 8 MCP tools for memory operations. Tools delegate to an
in-memory fragment store (shared across the process) so multiple MCP
servers and agent-loop callers see the same fragment set.

Tools:
  - recall: Retrieve fragments relevant to a query
  - write: Add a new memory fragment
  - pin: Mark a fragment as user-pinned (never evicted)
  - forget: Soft-delete a fragment
  - list_decisions: List all DECISION fragments
  - skill_invoke: Retrieve and format a SKILL fragment for execution
  - digest: Write a SubAgentDigest
  - recall_digests: Retrieve digests for peer agents in a task
"""
from __future__ import annotations

import threading
import uuid as _uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .access_policy import Permission, Resource, Subject, get_policy_graph
from .digest_bus import get_digest_bus
from .schema import Fragment, FragmentType, MemoryTier, Provenance, SubAgentDigest


# ---------------------------------------------------------------------------
# In-memory fragment store (process-global, thread-safe)
# ---------------------------------------------------------------------------


@dataclass
class _FragmentRow:
    fragment: Fragment
    pinned: bool = False
    invalid_at: str | None = None


class _FragmentStore:
    """Thread-safe in-memory store for MCP tool implementations."""

    def __init__(self) -> None:
        self._rows: dict[str, _FragmentRow] = {}
        self._by_type: dict[FragmentType, list[str]] = defaultdict(list)
        self._by_tier: dict[MemoryTier, list[str]] = defaultdict(list)
        self._by_entity: dict[str, list[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def put(self, fragment: Fragment) -> str:
        fid = fragment.id
        with self._lock:
            self._rows[fid] = _FragmentRow(fragment=fragment)
            self._by_type[fragment.type].append(fid)
            self._by_tier[fragment.tier].append(fid)
            for ent in fragment.entities:
                self._by_entity[ent.lower()].append(fid)
        return fid

    def get(self, fragment_id: str) -> _FragmentRow | None:
        with self._lock:
            return self._rows.get(fragment_id)

    def pin(self, fragment_id: str) -> bool:
        with self._lock:
            row = self._rows.get(fragment_id)
            if row is None:
                return False
            row.pinned = True
            return True

    def forget(self, fragment_id: str) -> str | None:
        with self._lock:
            row = self._rows.get(fragment_id)
            if row is None:
                return None
            now = datetime.now(timezone.utc).isoformat()
            row.invalid_at = now
            return now

    def search(
        self,
        *,
        query: str = "",
        tier: MemoryTier | None = None,
        fragment_type: FragmentType | None = None,
        limit: int = 10,
    ) -> list[Fragment]:
        with self._lock:
            results: list[Fragment] = []
            q = query.lower().strip()
            for row in self._rows.values():
                if row.invalid_at is not None:
                    continue
                f = row.fragment
                if tier is not None and f.tier != tier:
                    continue
                if fragment_type is not None and f.type != fragment_type:
                    continue
                if q and not (
                    q in f.content.lower()
                    or any(q in e.lower() for e in f.entities)
                ):
                    continue
                results.append(f)
            results.sort(key=lambda f: f.confidence, reverse=True)
            return results[:limit]

    def list_by_type(
        self, fragment_type: FragmentType, *, tier: MemoryTier | None = None, limit: int = 50
    ) -> list[Fragment]:
        with self._lock:
            ids = self._by_type.get(fragment_type, [])
            results: list[Fragment] = []
            for fid in ids:
                row = self._rows.get(fid)
                if row is None or row.invalid_at is not None:
                    continue
                f = row.fragment
                if tier is not None and f.tier != tier:
                    continue
                results.append(f)
            results.sort(key=lambda f: f.created_at, reverse=True)
            return results[:limit]


_store: _FragmentStore | None = None
_store_lock = threading.Lock()


def _get_store() -> _FragmentStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = _FragmentStore()
        return _store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fragment_to_dict(f: Fragment) -> dict[str, Any]:
    return {
        "id": f.id,
        "type": f.type.value if isinstance(f.type, FragmentType) else f.type,
        "content": f.content,
        "entities": f.entities,
        "confidence": f.confidence,
        "provenance": {
            "agent_id": f.provenance.agent_id,
            "user_id": f.provenance.user_id,
            "task_id": f.provenance.task_id,
        },
        "created_at": f.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# MCP Tool: recall (fully implemented)
# ---------------------------------------------------------------------------


def mcp_recall(
    query: str,
    tier: str | None = None,
    fragment_type: str | None = None,
    limit: int = 10,
    user_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve fragments relevant to a query."""
    store = _get_store()

    mem_tier = MemoryTier(tier) if tier else None
    frag_type = FragmentType(fragment_type) if fragment_type else None

    try:
        if tier and mem_tier is None:
            pass
    except ValueError:
        return {"fragments": [], "count": 0, "error": f"Invalid tier: {tier}"}

    fragments = store.search(
        query=query, tier=mem_tier, fragment_type=frag_type, limit=limit,
    )

    return {
        "fragments": [_fragment_to_dict(f) for f in fragments],
        "count": len(fragments),
        "query": query,
        "filters": {"tier": tier, "fragment_type": fragment_type, "limit": limit},
    }


# ---------------------------------------------------------------------------
# MCP Tool: write (already implemented with validation, now stores)
# ---------------------------------------------------------------------------


def mcp_write(
    content: str,
    fragment_type: str,
    tier: str,
    entities: list[str] | None = None,
    confidence: float = 0.8,
    agent_id: str = "system",
    user_id: str = "default",
    task_id: str | None = None,
    structured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a new memory fragment."""
    try:
        mem_tier = MemoryTier(tier)
    except ValueError:
        return {
            "error": f"Invalid tier: {tier}. Must be one of: t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team"
        }

    try:
        frag_type = FragmentType(fragment_type)
    except ValueError:
        return {
            "error": f"Invalid fragment_type: {fragment_type}. Must be one of: fact, decision, preference, skill, observation"
        }

    subject = Subject.agent(agent_id) if agent_id != "system" else Subject.user(user_id)
    resource = Resource.tier(mem_tier)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.WRITE):
        return {
            "error": f"Access denied: {subject.type}:{subject.id} does not have WRITE permission for tier {tier}"
        }

    now = datetime.now(timezone.utc)
    fragment = Fragment(
        id=f"{tier}:{frag_type.value}:{_uuid.uuid4().hex[:12]}",
        type=frag_type,
        tier=mem_tier,
        content=content,
        entities=entities or [],
        confidence=confidence,
        provenance=Provenance(
            agent_id=agent_id,
            session_id="mcp_write",
            user_id=user_id,
            task_id=task_id,
        ),
        structured=structured or {},
        created_at=now,
    )

    store = _get_store()
    fragment_id = store.put(fragment)

    return {
        "fragment_id": fragment_id,
        "status": "created",
        "tier": tier,
        "type": fragment_type,
    }


# ---------------------------------------------------------------------------
# MCP Tool: pin (implemented)
# ---------------------------------------------------------------------------


def mcp_pin(
    fragment_id: str,
    user_id: str = "default",
) -> dict[str, Any]:
    """Mark a fragment as user-pinned (never evicted)."""
    subject = Subject.user(user_id)
    resource = Resource.fragment(fragment_id)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.WRITE):
        return {
            "error": f"Access denied: user {user_id} does not have WRITE permission for fragment {fragment_id}"
        }

    store = _get_store()
    store.pin(fragment_id)  # idempotent — succeeds whether or not fragment exists

    return {
        "fragment_id": fragment_id,
        "status": "pinned",
    }


# ---------------------------------------------------------------------------
# MCP Tool: forget (implemented)
# ---------------------------------------------------------------------------


def mcp_forget(
    fragment_id: str,
    user_id: str = "default",
) -> dict[str, Any]:
    """Soft-delete a fragment (mark as invalid_at=now, kept for audit)."""
    subject = Subject.user(user_id)
    resource = Resource.fragment(fragment_id)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.DELETE):
        return {
            "error": f"Access denied: user {user_id} does not have DELETE permission for fragment {fragment_id}"
        }

    store = _get_store()
    now = datetime.now(timezone.utc).isoformat()
    invalid_at = store.forget(fragment_id) or now

    return {
        "fragment_id": fragment_id,
        "status": "forgotten",
        "invalid_at": invalid_at,
    }


# ---------------------------------------------------------------------------
# MCP Tool: list_decisions (implemented)
# ---------------------------------------------------------------------------


def mcp_list_decisions(
    tier: str | None = None,
    limit: int = 50,
    user_id: str = "default",
) -> dict[str, Any]:
    """List all DECISION fragments."""
    mem_tier = MemoryTier(tier) if tier else None
    store = _get_store()
    decisions = store.list_by_type(FragmentType.DECISION, tier=mem_tier, limit=limit)

    return {
        "decisions": [
            {
                "id": f.id,
                "content": f.content,
                "rationale": f.structured.get("rationale", ""),
                "created_at": f.created_at.isoformat(),
            }
            for f in decisions
        ],
        "count": len(decisions),
        "filters": {"tier": tier, "limit": limit},
    }


# ---------------------------------------------------------------------------
# MCP Tool: skill_invoke (implemented)
# ---------------------------------------------------------------------------


def mcp_skill_invoke(
    skill_name: str,
    user_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve and format a SKILL fragment for execution."""
    store = _get_store()
    # Search for skill fragments matching the name
    matches = store.search(
        query=skill_name,
        fragment_type=FragmentType.SKILL,
        limit=5,
    )

    # Find the best match by name or entity
    best = None
    for f in matches:
        if skill_name.lower() in f.content.lower() or any(
            skill_name.lower() in e.lower() for e in f.entities
        ):
            best = f
            break

    if best is None and matches:
        best = matches[0]

    if best is None:
        return {
            "skill_name": skill_name,
            "content": f"Skill '{skill_name}' not found in memory.",
            "executable": False,
        }

    executable = best.tier == MemoryTier.T2_PROCEDURAL
    return {
        "skill_name": skill_name,
        "content": best.content,
        "executable": executable,
        "code": best.structured.get("code") if executable else None,
        "fragment_id": best.id,
    }


# ---------------------------------------------------------------------------
# MCP Tool: digest (already implemented)
# ---------------------------------------------------------------------------


def mcp_digest(
    agent_id: str,
    task_id: str,
    step: int,
    last_action: str,
    findings: list[str] | None = None,
    open_questions: list[str] | None = None,
    next_intent: str | None = None,
    confidence: float = 0.7,
) -> dict[str, Any]:
    """Write a SubAgentDigest to the digest bus."""
    digest_bus = get_digest_bus()

    digest = SubAgentDigest(
        agent_id=agent_id,
        task_id=task_id,
        step=step,
        last_action=last_action,
        findings=findings or [],
        open_questions=open_questions or [],
        next_intent=next_intent,
        confidence=confidence,
    )

    digest_bus.emit(digest)

    return {
        "digest_id": f"{task_id}:{agent_id}:{step}",
        "status": "recorded",
        "last_action": last_action,
    }


# ---------------------------------------------------------------------------
# MCP Tool: recall_digests (already implemented)
# ---------------------------------------------------------------------------


def mcp_recall_digests(
    task_id: str,
    agent_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Retrieve digests for peer agents in a task."""
    digest_bus = get_digest_bus()

    all_digests = digest_bus.store.get_all_latest(task_id)

    if agent_id:
        all_digests = [d for d in all_digests if d.agent_id == agent_id]

    digests = all_digests[:limit]

    summary_parts = [f"{d.agent_id}: {d.last_action}" for d in digests]

    return {
        "digests": [
            {
                "agent_id": d.agent_id,
                "step": d.step,
                "last_action": d.last_action,
                "findings": d.findings,
                "open_questions": d.open_questions,
                "next_intent": d.next_intent,
                "confidence": d.confidence,
                "emitted_at": d.emitted_at.isoformat(),
            }
            for d in digests
        ],
        "count": len(digests),
        "summary": "; ".join(summary_parts),
    }


__all__ = [
    "mcp_recall",
    "mcp_write",
    "mcp_pin",
    "mcp_forget",
    "mcp_list_decisions",
    "mcp_skill_invoke",
    "mcp_digest",
    "mcp_recall_digests",
]
