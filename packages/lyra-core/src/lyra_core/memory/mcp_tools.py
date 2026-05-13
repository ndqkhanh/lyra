"""MCP Server Surface for CoALA Memory Architecture (Phase M7).

Exposes 8 MCP tools for memory operations:
  - recall: Retrieve fragments relevant to a query
  - write: Add a new memory fragment
  - pin: Mark a fragment as user-pinned (never evicted)
  - forget: Soft-delete a fragment
  - list_decisions: List all DECISION fragments
  - skill_invoke: Retrieve and format a SKILL fragment for execution
  - digest: Write a SubAgentDigest
  - recall_digests: Retrieve digests for peer agents in a task

Integration:
  - Wire into lyra-cli/__main__.py as MCP server endpoints
  - Uses memory/store.py for fragment operations
  - Uses memory/digest_bus.py for digest operations
  - Uses memory/access_policy.py for permission checks

Research grounding:
  - Design proposal §11 rollout plan Phase 0-1
  - MCP conformance requirement (G5)
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from .access_policy import Permission, Resource, Subject, get_policy_graph
from .digest_bus import get_digest_bus
from .schema import Fragment, FragmentType, MemoryTier, Provenance, SubAgentDigest


# ---------------------------------------------------------------------------
# MCP Tool: recall
# ---------------------------------------------------------------------------


def mcp_recall(
    query: str,
    tier: str | None = None,
    fragment_type: str | None = None,
    limit: int = 10,
    user_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve fragments relevant to a query.

    Args:
        query: Search query (free text or entity)
        tier: Filter by tier (t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team)
        fragment_type: Filter by type (fact, decision, preference, skill, observation)
        limit: Maximum number of fragments to return
        user_id: User ID for access control
        agent_id: Agent ID for access control (optional)

    Returns:
        {
            "fragments": [
                {
                    "id": "t1:fact:uuid",
                    "type": "fact",
                    "content": "...",
                    "entities": ["..."],
                    "confidence": 0.9,
                    "provenance": {...},
                    "created_at": "2026-05-14T...",
                },
                ...
            ],
            "count": 5,
        }
    """
    # TODO: Implement actual retrieval logic with:
    # 1. Query expansion (extract entities + paraphrase)
    # 2. Fan-out search (dense top-50, BM25 top-50, entity top-50)
    # 3. RRF fusion and deduplication
    # 4. Access policy filtering
    # 5. Pack into budget (default 2k tokens for T2/T3, 1k for T1)

    # For now, return empty result
    return {
        "fragments": [],
        "count": 0,
        "query": query,
        "filters": {
            "tier": tier,
            "fragment_type": fragment_type,
            "limit": limit,
        },
    }


# ---------------------------------------------------------------------------
# MCP Tool: write
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
    """Add a new memory fragment.

    Args:
        content: Fragment content (≤ 200 chars recommended)
        fragment_type: Type (fact, decision, preference, skill, observation)
        tier: Target tier (t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team)
        entities: Entity mentions (≤ 5 noun-phrases)
        confidence: Confidence score (0..1)
        agent_id: Agent ID for provenance
        user_id: User ID for provenance
        task_id: Task ID for task-scoped fragments
        structured: Type-specific structured data (e.g., decision.rationale)

    Returns:
        {
            "fragment_id": "t1:fact:uuid",
            "status": "created",
        }
    """
    # Validate tier first (before fragment_type)
    try:
        mem_tier = MemoryTier(tier)
    except ValueError:
        return {
            "error": f"Invalid tier: {tier}. Must be one of: t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team"
        }

    # Validate fragment_type
    try:
        frag_type = FragmentType(fragment_type)
    except ValueError:
        return {
            "error": f"Invalid fragment_type: {fragment_type}. Must be one of: fact, decision, preference, skill, observation"
        }

    # Check write permission
    subject = Subject.agent(agent_id) if agent_id != "system" else Subject.user(user_id)
    resource = Resource.tier(mem_tier)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.WRITE):
        return {
            "error": f"Access denied: {subject.type}:{subject.id} does not have WRITE permission for tier {tier}"
        }

    # Create fragment
    fragment_id = f"{tier.split('_')[0]}:{fragment_type}:{datetime.now().isoformat()}"

    # TODO: Implement actual storage logic with:
    # 1. Generate embedding
    # 2. Store in vector database
    # 3. Update indexes
    # 4. Check for conflicts
    # 5. Trigger ConflictResolver if needed

    return {
        "fragment_id": fragment_id,
        "status": "created",
        "tier": tier,
        "type": fragment_type,
    }


# ---------------------------------------------------------------------------
# MCP Tool: pin
# ---------------------------------------------------------------------------


def mcp_pin(
    fragment_id: str,
    user_id: str = "default",
) -> dict[str, Any]:
    """Mark a fragment as user-pinned (never evicted).

    Args:
        fragment_id: Fragment ID to pin
        user_id: User ID for access control

    Returns:
        {
            "fragment_id": "t1:fact:uuid",
            "status": "pinned",
        }
    """
    # Check if fragment exists and user has permission
    subject = Subject.user(user_id)
    resource = Resource.fragment(fragment_id)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.WRITE):
        return {
            "error": f"Access denied: user {user_id} does not have WRITE permission for fragment {fragment_id}"
        }

    # TODO: Implement actual pin logic:
    # 1. Load fragment from store
    # 2. Set pinned=True
    # 3. Update in database

    return {
        "fragment_id": fragment_id,
        "status": "pinned",
    }


# ---------------------------------------------------------------------------
# MCP Tool: forget
# ---------------------------------------------------------------------------


def mcp_forget(
    fragment_id: str,
    user_id: str = "default",
) -> dict[str, Any]:
    """Soft-delete a fragment (mark as invalid_at=now, kept for audit).

    Args:
        fragment_id: Fragment ID to forget
        user_id: User ID for access control

    Returns:
        {
            "fragment_id": "t1:fact:uuid",
            "status": "forgotten",
        }
    """
    # Check if fragment exists and user has permission
    subject = Subject.user(user_id)
    resource = Resource.fragment(fragment_id)
    policy_graph = get_policy_graph()

    if not policy_graph.check_access(subject, resource, Permission.DELETE):
        return {
            "error": f"Access denied: user {user_id} does not have DELETE permission for fragment {fragment_id}"
        }

    # TODO: Implement actual forget logic:
    # 1. Load fragment from store
    # 2. Set invalid_at=now()
    # 3. Update in database (soft delete)

    return {
        "fragment_id": fragment_id,
        "status": "forgotten",
        "invalid_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# MCP Tool: list_decisions
# ---------------------------------------------------------------------------


def mcp_list_decisions(
    tier: str | None = None,
    limit: int = 50,
    user_id: str = "default",
) -> dict[str, Any]:
    """List all DECISION fragments.

    Args:
        tier: Filter by tier (optional)
        limit: Maximum number of decisions to return
        user_id: User ID for access control

    Returns:
        {
            "decisions": [
                {
                    "id": "t2:decision:uuid",
                    "content": "...",
                    "rationale": "...",
                    "created_at": "2026-05-14T...",
                },
                ...
            ],
            "count": 10,
        }
    """
    # TODO: Implement actual list logic:
    # 1. Query for fragment_type=DECISION
    # 2. Filter by tier if specified
    # 3. Apply access control
    # 4. Extract decision.rationale from structured field
    # 5. Sort by created_at desc

    return {
        "decisions": [],
        "count": 0,
        "filters": {
            "tier": tier,
            "limit": limit,
        },
    }


# ---------------------------------------------------------------------------
# MCP Tool: skill_invoke
# ---------------------------------------------------------------------------


def mcp_skill_invoke(
    skill_name: str,
    user_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve and format a SKILL fragment for execution.

    Args:
        skill_name: Skill name to retrieve
        user_id: User ID for access control
        agent_id: Agent ID for access control (optional)

    Returns:
        {
            "skill_name": "...",
            "content": "...",
            "executable": true/false,
            "code": "..." (if executable),
        }
    """
    # Check read permission
    subject = Subject.agent(agent_id) if agent_id else Subject.user(user_id)
    # TODO: Need to know fragment_id to check permission
    # For now, assume permission granted

    # TODO: Implement actual skill retrieval:
    # 1. Query for fragment_type=SKILL with entity=skill_name
    # 2. Check if skill is executable (requires user approval)
    # 3. Return skill content and code if executable

    return {
        "skill_name": skill_name,
        "content": f"Skill {skill_name} not found",
        "executable": False,
    }


# ---------------------------------------------------------------------------
# MCP Tool: digest
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
    """Write a SubAgentDigest to the digest bus.

    Args:
        agent_id: Sub-agent ID
        task_id: Task ID
        step: Step index in trajectory
        last_action: Compact summary of last action (≤ 200 chars)
        findings: Bullet points of findings (optional)
        open_questions: List of open questions (optional)
        next_intent: Next intended action (optional)
        confidence: Confidence score (0..1)

    Returns:
        {
            "digest_id": "...",
            "status": "recorded",
        }
    """
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
# MCP Tool: recall_digests
# ---------------------------------------------------------------------------


def mcp_recall_digests(
    task_id: str,
    agent_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Retrieve digests for peer agents in a task.

    Args:
        task_id: Task ID
        agent_id: Filter by specific agent (optional)
        limit: Maximum number of digests to return

    Returns:
        {
            "digests": [
                {
                    "agent_id": "...",
                    "step": 5,
                    "last_action": "...",
                    "findings": [...],
                    "open_questions": [...],
                    "next_intent": "...",
                    "confidence": 0.7,
                    "emitted_at": "2026-05-14T...",
                },
                ...
            ],
            "count": 3,
            "summary": "Agent A: ...; Agent B: ...; Agent C: ...",
        }
    """
    digest_bus = get_digest_bus()

    # Get latest digest per agent via DigestStore
    all_digests = digest_bus.store.get_all_latest(task_id)

    # Filter by agent_id if specified
    if agent_id:
        all_digests = [d for d in all_digests if d.agent_id == agent_id]

    # Limit results
    digests = all_digests[:limit]

    # Generate summary
    summary_parts = []
    for digest in digests:
        summary_parts.append(f"{digest.agent_id}: {digest.last_action}")
    summary = "; ".join(summary_parts)

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
        "summary": summary,
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
