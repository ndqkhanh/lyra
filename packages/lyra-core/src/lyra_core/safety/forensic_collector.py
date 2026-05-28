"""Forensic trace collector for Lyra safety incident investigation.

Provides immutable forensic snapshots capturing the full execution context
at the moment of a safety incident — tool calls, agent state, permissions,
model outputs, and environmental context. Snapshots are content-addressed
(SHA-256) and form a tamper-evident chain for post-incident analysis.

Architecture:
    - ForensicSnapshot: frozen, content-addressed incident capture
    - ForensicCollector: main collector with chain verification
    - SnapshotChain: append-only linked list of snapshots
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class IncidentCategory(StrEnum):
    """Classification of safety incidents for forensic analysis."""

    PROMPT_INJECTION = "prompt_injection"
    TOOL_MISUSE = "tool_misuse"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MODEL_HALLUCINATION = "model_hallucination"
    SAFETY_POLICY_VIOLATION = "safety_policy_violation"
    RATE_LIMIT_BREACH = "rate_limit_breach"
    CREDENTIAL_EXPOSURE = "credential_exposure"
    DESTRUCTIVE_OPERATION = "destructive_operation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ForensicSnapshot:
    """Immutable forensic snapshot of an incident.

    Attributes:
        snapshot_id: content-addressable identifier (SHA-256 of key fields)
        incident_category: classification of the incident
        timestamp: when the incident was captured
        agent_id: identifier of the agent involved
        session_id: session in which the incident occurred
        tool_name: the tool being invoked (if applicable)
        tool_args: arguments passed to the tool (sanitized)
        model_id: the model being used at time of incident
        model_output: the model's output at time of incident (truncated)
        permissions_state: permission state at time of incident
        safety_flags: safety flags that were triggered
        stack_trace: error traceback if applicable
        environment_summary: key environment context (no secrets)
        previous_snapshot_hash: hash of previous snapshot in chain
    """

    snapshot_id: str
    incident_category: IncidentCategory
    timestamp: float
    agent_id: str
    session_id: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    model_id: str | None
    model_output: str | None
    permissions_state: dict[str, Any] | None
    safety_flags: list[str] | None
    stack_trace: str | None
    environment_summary: dict[str, str] | None
    previous_snapshot_hash: str | None

    @property
    def age_sec(self) -> float:
        return time.time() - self.timestamp


class SnapshotChain:
    """Append-only chain of forensic snapshots with integrity verification."""

    def __init__(self) -> None:
        self._snapshots: list[ForensicSnapshot] = []
        self._by_id: dict[str, ForensicSnapshot] = {}

    def append(self, snapshot: ForensicSnapshot) -> None:
        self._snapshots.append(snapshot)
        self._by_id[snapshot.snapshot_id] = snapshot

    def verify(self) -> bool:
        """Verify the hash chain integrity."""
        for i in range(1, len(self._snapshots)):
            current = self._snapshots[i]
            previous = self._snapshots[i - 1]
            expected_prev = hashlib.sha256(
                f"{previous.snapshot_id}|{previous.timestamp}".encode()
            ).hexdigest()
            if current.previous_snapshot_hash != expected_prev:
                return False
        return True

    @property
    def count(self) -> int:
        return len(self._snapshots)

    def get(self, snapshot_id: str) -> ForensicSnapshot | None:
        return self._by_id.get(snapshot_id)

    def query(
        self,
        category: IncidentCategory | None = None,
        agent_id: str | None = None,
        since: float | None = None,
    ) -> list[ForensicSnapshot]:
        results = self._snapshots
        if category is not None:
            results = [s for s in results if s.incident_category == category]
        if agent_id is not None:
            results = [s for s in results if s.agent_id == agent_id]
        if since is not None:
            results = [s for s in results if s.timestamp >= since]
        return results


class ForensicCollector:
    """Collects forensic traces for safety incident investigation.

    Creates immutable, content-addressed snapshots of the execution
    context at the moment an incident is detected. Maintains an
    append-only chain with cryptographic integrity verification.

    Usage::

        collector = ForensicCollector()
        collector.capture(
            category=IncidentCategory.PROMPT_INJECTION,
            agent_id="agent-7",
            session_id="sess-42",
            tool_name="execute_code",
            tool_args={"code": "..."},
            model_id="claude-sonnet-4-6",
            model_output="I'll execute that...",
            safety_flags=["injection_pattern_detected"],
        )
        snapshots = collector.query(category=IncidentCategory.PROMPT_INJECTION)
    """

    def __init__(self, max_chain_length: int = 1000) -> None:
        self.max_chain_length = max_chain_length
        self._chain = SnapshotChain()
        self._capture_count: dict[str, int] = {}

    def capture(
        self,
        category: IncidentCategory,
        agent_id: str,
        session_id: str,
        *,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        model_id: str | None = None,
        model_output: str | None = None,
        permissions_state: dict[str, Any] | None = None,
        safety_flags: list[str] | None = None,
        stack_trace: str | None = None,
        environment_summary: dict[str, str] | None = None,
    ) -> ForensicSnapshot:
        """Capture a forensic snapshot of an incident."""
        ts = time.time()
        previous_hash = None
        if self._chain.count > 0:
            last = self._chain._snapshots[-1]
            previous_hash = hashlib.sha256(
                f"{last.snapshot_id}|{last.timestamp}".encode()
            ).hexdigest()

        content = (
            f"{category.value}|{agent_id}|{session_id}|{tool_name}|{ts}|"
            f"{previous_hash or 'genesis'}"
        )
        snapshot_id = hashlib.sha256(content.encode()).hexdigest()[:24]

        if model_output and len(model_output) > 2000:
            model_output = model_output[:2000] + "…"

        snapshot = ForensicSnapshot(
            snapshot_id=snapshot_id,
            incident_category=category,
            timestamp=ts,
            agent_id=agent_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            model_id=model_id,
            model_output=model_output,
            permissions_state=permissions_state,
            safety_flags=safety_flags,
            stack_trace=stack_trace,
            environment_summary=environment_summary,
            previous_snapshot_hash=previous_hash,
        )

        self._chain.append(snapshot)
        self._capture_count[category.value] = (
            self._capture_count.get(category.value, 0) + 1
        )

        if self._chain.count > self.max_chain_length:
            self._chain._snapshots = self._chain._snapshots[-self.max_chain_length:]

        return snapshot

    def verify_chain(self) -> bool:
        return self._chain.verify()

    def query(
        self,
        category: IncidentCategory | None = None,
        agent_id: str | None = None,
        since: float | None = None,
    ) -> list[ForensicSnapshot]:
        return self._chain.query(category=category, agent_id=agent_id, since=since)

    def get_snapshot(self, snapshot_id: str) -> ForensicSnapshot | None:
        return self._chain.get(snapshot_id)

    def stats(self) -> dict[str, Any]:
        return {
            "total_snapshots": self._chain.count,
            "chain_verified": self.verify_chain(),
            "by_category": dict(self._capture_count),
        }
