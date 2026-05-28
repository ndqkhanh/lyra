"""Systems Architect Skill — distributed systems design validation.

Validates system architectures for:
- Scalability and fault tolerance
- Consistency and partition tolerance
- CAP theorem trade-offs
- Service decomposition and coupling
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ArchitectureConcern(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class ArchitectureIssue:
    component: str
    concern: ArchitectureConcern
    description: str
    recommendation: str


class SystemsArchitectSkill:
    """Validates distributed system architecture designs."""

    def run(self, input_data: dict) -> dict:
        components = input_data.get("components", [])
        issues: list[ArchitectureIssue] = []

        comp_names = {c.get("name", "") for c in components}

        has_db = any("db" in n.lower() or "database" in n.lower() or "store" in n.lower() for n in comp_names)
        has_cache = any("cache" in n.lower() or "redis" in n.lower() for n in comp_names)
        has_queue = any("queue" in n.lower() or "kafka" in n.lower() or "mq" in n.lower() for n in comp_names)
        has_lb = any("load" in n.lower() or "gateway" in n.lower() or "proxy" in n.lower() for n in comp_names)

        if has_db and not has_cache:
            issues.append(ArchitectureIssue("performance", ArchitectureConcern.IMPORTANT,
                "Database present but no caching layer — read-heavy workloads will hit DB directly.",
                "Add a caching layer (Redis/Memcached) in front of the database."))

        if len(components) > 3 and not has_queue:
            issues.append(ArchitectureIssue("resilience", ArchitectureConcern.IMPORTANT,
                "Multiple services but no message queue — tight coupling risk.",
                "Introduce a message queue (Kafka/RabbitMQ/SQS) for async communication."))

        if len(components) > 1 and not has_lb:
            issues.append(ArchitectureIssue("availability", ArchitectureConcern.CRITICAL,
                "No load balancer or API gateway defined.", "Add a load balancer or API gateway for traffic distribution."))

        single_points = [c for c in components if not c.get("replicas") or c.get("replicas", 1) < 2]
        if single_points and len(components) > 1:
            issues.append(ArchitectureIssue("fault_tolerance", ArchitectureConcern.CRITICAL,
                f"Single points of failure: {', '.join(c.get('name', '?') for c in single_points[:3])}.",
                "Add redundancy with at least 2 replicas for each critical service."))

        return {
            "issues": [i.__dict__ for i in issues],
            "score": max(0, 100
                - len([i for i in issues if i.concern == ArchitectureConcern.CRITICAL]) * 25
                - len([i for i in issues if i.concern == ArchitectureConcern.IMPORTANT]) * 10),
            "passed": len([i for i in issues if i.concern == ArchitectureConcern.CRITICAL]) == 0,
        }
