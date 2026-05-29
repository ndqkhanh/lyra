"""
Solution Architect Skill - Solution architecture design and analysis.

Given business requirements, produces:
- System design with components
- Trade-off analysis (CAP theorem, consistency vs availability)
- Technology stack recommendations
- Integration patterns
- Sequence diagrams in text

Outputs structured solution architecture document.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapTheorem(StrEnum):
    """CAP theorem trade-off choices."""

    CP = "CP"  # Consistency + Partition Tolerance
    AP = "AP"  # Availability + Partition Tolerance
    CA = "CA"  # Consistency + Availability (no partition tolerance)


class ConsistencyModel(StrEnum):
    """Consistency model options."""

    STRONG = "strong"
    EVENTUAL = "eventual"
    CAUSAL = "causal"
    READ_YOUR_WRITES = "read_your_writes"
    SESSION = "session"
    MONOTONIC_READS = "monotonic_reads"


class IntegrationPattern(StrEnum):
    """Enterprise integration patterns."""

    REQUEST_REPLY = "request_reply"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    EVENT_SOURCING = "event_sourcing"
    SAGA = "saga"
    STRANGER_FIG = "strangler_fig"
    BULKHEAD = "bulkhead"
    CIRCUIT_BREAKER = "circuit_breaker"
    PUB_SUB = "pub_sub"
    DEAD_LETTER = "dead_letter_queue"


@dataclass(frozen=True)
class SystemComponent:
    """A system component in the solution architecture."""

    name: str
    role: str
    technology: str
    scaling_approach: str
    data_stores: tuple[str, ...]
    apis_exposed: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class TradeOffDecision:
    """A documented trade-off decision."""

    id: str
    title: str
    options: tuple[str, ...]
    chosen: str
    rationale: str
    consequences: str
    cap_alignment: CapTheorem | None


@dataclass(frozen=True)
class TechStackRecommendation:
    """A technology stack recommendation."""

    layer: str
    recommended: str
    alternatives: tuple[str, ...]
    rationale: str
    maturity: str


@dataclass(frozen=True)
class SequenceStep:
    """A step in a sequence diagram."""

    step: int
    source: str
    target: str
    action: str
    protocol: str
    data_summary: str


@dataclass(frozen=True)
class IntegrationSpec:
    """Integration pattern specification."""

    pattern: IntegrationPattern
    description: str
    components_involved: tuple[str, ...]
    protocol: str
    data_format: str
    error_handling: str


@dataclass(frozen=True)
class SolutionArchitectureDoc:
    """Complete solution architecture document."""

    title: str
    business_context: str
    components: tuple[SystemComponent, ...]
    trade_offs: tuple[TradeOffDecision, ...]
    tech_stack: tuple[TechStackRecommendation, ...]
    sequence_diagrams: dict[str, tuple[SequenceStep, ...]]
    integration_specs: tuple[IntegrationSpec, ...]
    constraints: tuple[str, ...]
    assumptions: tuple[str, ...]


class SolutionArchitect:
    """Solution architecture skill producing structured architecture documents."""

    def __init__(self) -> None:
        self._detected_patterns: list[str] = []

    def run(self, input_data: dict) -> dict:
        """Run solution architecture design.

        Args:
            input_data: Dictionary with keys:
                - requirements: Business requirements description
                - project_name: Optional project name (default "Solution Architecture")
                - constraints: Optional list of constraints
                - cap_preference: Optional CAP preference ("CP", "AP", "CA")

        Returns:
            Dictionary with solution architecture data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project = input_data.get("project_name", "Solution Architecture")
        raw_constraints = input_data.get("constraints", [])
        constraints = list(raw_constraints) if raw_constraints else []
        cap_pref = input_data.get("cap_preference", None)

        reqs_lower = requirements.lower()

        components = self._design_components(reqs_lower, project)
        trade_offs = self._analyze_trade_offs(reqs_lower, cap_pref)
        tech_stack = self._recommend_tech_stack(reqs_lower)
        sequence_diagrams = self._build_sequence_diagrams(reqs_lower, components)
        integrations = self._define_integrations(reqs_lower)
        all_constraints = self._derive_constraints(reqs_lower) + constraints
        assumptions = self._define_assumptions(reqs_lower)

        return SolutionArchitectureDoc(
            title=project,
            business_context=requirements,
            components=tuple(components),
            trade_offs=tuple(trade_offs),
            tech_stack=tuple(tech_stack),
            sequence_diagrams={
                name: tuple(steps)
                for name, steps in sequence_diagrams.items()
            },
            integration_specs=tuple(integrations),
            constraints=tuple(all_constraints),
            assumptions=tuple(assumptions),
        ).__dict__ | {
            "components": [c.__dict__ for c in components],
            "trade_offs": [t.__dict__ for t in trade_offs],
            "tech_stack": [t.__dict__ for t in tech_stack],
            "sequence_diagrams": {
                name: [s.__dict__ for s in steps]
                for name, steps in sequence_diagrams.items()
            },
            "integration_specs": [i.__dict__ for i in integrations],
        }

    @staticmethod
    def _design_components(
        requirements: str, project: str
    ) -> list[SystemComponent]:
        has_ui = any(kw in requirements for kw in ["ui", "frontend", "web", "dashboard"])
        has_event = any(
            kw in requirements for kw in
            ["event", "async", "queue", "message", "kafka", "pubsub"]
        )
        has_reporting = any(
            kw in requirements for kw in
            ["report", "analytics", "dashboard", "bi", "olap"]
        )
        has_file = any(
            kw in requirements for kw in ["file", "upload", "document", "blob", "asset"]
        )

        components: list[SystemComponent] = [
            SystemComponent(
                name=f"{project}-api",
                role="API Gateway / Backend API",
                technology="REST/gRPC API (FastAPI / Spring Boot / Express)",
                scaling_approach="Horizontal auto-scaling",
                data_stores=("user_sessions",),
                apis_exposed=("/api/v1/*",),
                dependencies=(),
            ),
        ]

        if has_ui:
            components.insert(0, SystemComponent(
                name=f"{project}-ui",
                role="User Interface / Web Application",
                technology="React / Vue / Angular with SSR",
                scaling_approach="CDN + static hosting, auto-scale web tier",
                data_stores=("client_cache",),
                apis_exposed=(),
                dependencies=(f"{project}-api",),
            ))

        if has_event:
            components.append(
                SystemComponent(
                    name=f"{project}-eventbus",
                    role="Event Bus / Message Broker",
                    technology="Apache Kafka / RabbitMQ / AWS SQS+SNS",
                    scaling_approach="Partition-based scaling",
                    data_stores=("event_log", "dead_letter"),
                    apis_exposed=("produce", "consume", "topics"),
                    dependencies=(),
                )
            )

        components.append(
            SystemComponent(
                name=f"{project}-db",
                role="Primary Data Store",
                technology="PostgreSQL / MySQL / Aurora",
                scaling_approach="Read replicas + connection pooling",
                data_stores=("main_db",),
                apis_exposed=("SQL",),
                dependencies=(f"{project}-api",),
            )
        )

        if has_reporting:
            components.append(
                SystemComponent(
                    name=f"{project}-analytics",
                    role="Analytics / Reporting Engine",
                    technology="ClickHouse / BigQuery / Snowflake",
                    scaling_approach="Columnar storage, MPP scaling",
                    data_stores=("analytics_warehouse",),
                    apis_exposed=("SQL", "REST"),
                    dependencies=(f"{project}-db", f"{project}-eventbus" if has_event else f"{project}-db"),
                )
            )

        if has_file:
            components.append(
                SystemComponent(
                    name=f"{project}-storage",
                    role="File / Asset Storage",
                    technology="AWS S3 / GCP Cloud Storage / MinIO",
                    scaling_approach="Object storage (infinite scaling)",
                    data_stores=("assets", "uploads"),
                    apis_exposed=("S3-compatible API",),
                    dependencies=(f"{project}-api",),
                )
            )

        return components

    @staticmethod
    def _analyze_trade_offs(
        requirements: str, cap_pref: str | None
    ) -> list[TradeOffDecision]:
        decisions: list[TradeOffDecision] = []

        # CAP trade-off
        if cap_pref == "CP" or (not cap_pref and "financial" in requirements):
            chosen_cap = CapTheorem.CP
            rationale = "Financial/transactional data requires strong consistency"
        elif cap_pref == "AP" or (not cap_pref and "social" in requirements):
            chosen_cap = CapTheorem.AP
            rationale = "Social/real-time systems prioritize availability"
        else:
            chosen_cap = CapTheorem.CP
            rationale = "Default to consistency for data integrity"

        decisions.append(
            TradeOffDecision(
                id="TRD-001",
                title="CAP Theorem Trade-off",
                options=("CP (Consistency + Partition Tolerance)",
                         "AP (Availability + Partition Tolerance)"),
                chosen=chosen_cap.value,
                rationale=rationale,
                consequences=(
                    "Strong consistency limits write throughput; "
                    "consider read replicas for read scale"
                ),
                cap_alignment=chosen_cap,
            )
        )

        # Monolith vs Microservices
        use_micro = any(
            kw in requirements for kw in
            ["scalable", "microservice", "team", "independent", "deploy"]
        )
        decisions.append(
            TradeOffDecision(
                id="TRD-002",
                title="Architecture Style: Monolith vs Microservices",
                options=("Monolithic", "Modular Monolith", "Microservices"),
                chosen="Modular Monolith" if not use_micro else "Microservices",
                rationale="Matched to team structure and scaling requirements",
                consequences=(
                    "Microservices add complexity in deployment, monitoring, and data consistency"
                ),
                cap_alignment=None,
            )
        )

        # Sync vs Async
        has_async = any(
            kw in requirements for kw in
            ["realtime", "async", "event", "streaming", "notification"]
        )
        decisions.append(
            TradeOffDecision(
                id="TRD-003",
                title="Communication Pattern: Sync vs Async",
                options=("Synchronous (REST/gRPC)",
                         "Asynchronous (Events/Messaging)"),
                chosen="Hybrid: sync for queries, async for commands",
                rationale="Optimizes for both low-latency queries and decoupled command processing",
                consequences="Increased system complexity but better resilience and scalabilty",
                cap_alignment=None,
            )
        )

        if has_async:
            decisions.append(
                TradeOffDecision(
                    id="TRD-004",
                    title="Eventual Consistency Tolerance",
                    options=("Strong consistency everywhere",
                             "Eventual consistency for non-critical paths"),
                    chosen="Eventual consistency for async flows",
                    rationale="Async processing inherently involves latency;"
                             " strong consistency would negate benefits",
                    consequences="Application must handle stale reads",
                    cap_alignment=None,
                )
            )

        return decisions

    @staticmethod
    def _recommend_tech_stack(
        requirements: str,
    ) -> list[TechStackRecommendation]:
        has_realtime = any(
            kw in requirements for kw in
            ["realtime", "websocket", "stream", "live"]
        )
        has_ml = any(kw in requirements for kw in ["ml", "ai", "machine learning", "model"])
        has_mobile = any(kw in requirements for kw in ["mobile", "ios", "android", "app"])

        stack: list[TechStackRecommendation] = [
            TechStackRecommendation(
                layer="Frontend",
                recommended="React 18+ with TypeScript",
                alternatives=("Vue 3", "Svelte", "Angular"),
                rationale="Strong ecosystem, server components, and TypeScript support",
                maturity="Mature",
            ),
            TechStackRecommendation(
                layer="Backend",
                recommended="Python (FastAPI) or Node.js (Express/NestJS)",
                alternatives=("Go (Gin)", "Java (Spring Boot)", "Rust (Actix)"),
                rationale="Rapid development with strong async support",
                maturity="Mature",
            ),
            TechStackRecommendation(
                layer="Database",
                recommended="PostgreSQL 16+",
                alternatives=("MySQL 8", "CockroachDB", "SQLite"),
                rationale="Rich feature set: JSON, full-text search, extensions, strong consistency",
                maturity="Mature",
            ),
            TechStackRecommendation(
                layer="Cache",
                recommended="Redis 7+",
                alternatives=("Memcached", "Dragonfly"),
                rationale="Multi-purpose: caching, rate limiting, pub/sub, session store",
                maturity="Mature",
            ),
            TechStackRecommendation(
                layer="Container Orchestration",
                recommended="Kubernetes (EKS/GKE/AKS)",
                alternatives=("AWS ECS", "Docker Swarm", "Nomad"),
                rationale="Industry standard for container orchestration",
                maturity="Mature",
            ),
            TechStackRecommendation(
                layer="CI/CD",
                recommended="GitHub Actions",
                alternatives=("GitLab CI", "CircleCI", "ArgoCD"),
                rationale="Native GitHub integration, large marketplace, cost-effective",
                maturity="Mature",
            ),
        ]

        if has_realtime:
            stack.append(
                TechStackRecommendation(
                    layer="Real-time",
                    recommended="WebSockets (Socket.IO) / Server-Sent Events",
                    alternatives=("gRPC streaming", "WebRTC"),
                    rationale="Bi-directional real-time communication",
                    maturity="Mature",
                )
            )
        if has_ml:
            stack.append(
                TechStackRecommendation(
                    layer="ML/AI",
                    recommended="Python (PyTorch / scikit-learn) + MLflow",
                    alternatives=("TensorFlow", "JAX", "ONNX Runtime"),
                    rationale="Python ecosystem dominance in ML/AI",
                    maturity="Mature",
                )
            )
        if has_mobile:
            stack.append(
                TechStackRecommendation(
                    layer="Mobile",
                    recommended="React Native (cross-platform)",
                    alternatives=("Flutter", "Native (Swift/Kotlin)"),
                    rationale="Code sharing between web and mobile",
                    maturity="Mature",
                )
            )

        return stack

    @staticmethod
    def _build_sequence_diagrams(
        requirements: str, components: list[SystemComponent]
    ) -> dict[str, list[SequenceStep]]:
        diagrams: dict[str, list[SequenceStep]] = {}

        # Main request flow
        main_flow: list[SequenceStep] = [
            SequenceStep(
                step=1, source="Client", target="API Gateway",
                action="HTTP Request", protocol="HTTPS/REST",
                data_summary="Request payload with auth token",
            ),
            SequenceStep(
                step=2, source="API Gateway", target="Backend Service",
                action="Route request", protocol="HTTP/gRPC",
                data_summary="Validated request with identity context",
            ),
            SequenceStep(
                step=3, source="Backend Service", target="Database",
                action="Query / Mutate data", protocol="SQL",
                data_summary="Parameterized query",
            ),
            SequenceStep(
                step=4, source="Database", target="Backend Service",
                action="Return result", protocol="SQL",
                data_summary="Result set or affected rows",
            ),
            SequenceStep(
                step=5, source="Backend Service", target="Client",
                action="HTTP Response", protocol="HTTPS/REST",
                data_summary="Response body with status code",
            ),
        ]
        diagrams["main_request_flow"] = main_flow

        # Error handling flow
        error_flow: list[SequenceStep] = [
            SequenceStep(
                step=1, source="Client", target="API Gateway",
                action="HTTP Request", protocol="HTTPS/REST",
                data_summary="Invalid / malformed request",
            ),
            SequenceStep(
                step=2, source="API Gateway", target="Backend Service",
                action="Validate & route", protocol="HTTP",
                data_summary="Request with validation context",
            ),
            SequenceStep(
                step=3, source="Backend Service", target="Dead Letter Queue",
                action="Enqueue failed request", protocol="Queue protocol",
                data_summary="Error context + original payload",
            ),
            SequenceStep(
                step=4, source="Backend Service", target="Client",
                action="Error Response", protocol="HTTPS",
                data_summary="4xx/5xx with correlation ID",
            ),
        ]
        diagrams["error_handling_flow"] = error_flow

        return diagrams

    @staticmethod
    def _define_integrations(requirements: str) -> list[IntegrationSpec]:
        has_third_party = any(
            kw in requirements for kw in
            ["third", "external", "integration", "api", "partner"]
        )
        has_events = any(
            kw in requirements for kw in
            ["event", "async", "message", "stream"]
        )

        specs: list[IntegrationSpec] = [
            IntegrationSpec(
                pattern=IntegrationPattern.CIRCUIT_BREAKER,
                description="Protect downstream services from cascading failures",
                components_involved=("API Gateway", "Backend Service"),
                protocol="HTTP",
                data_format="JSON",
                error_handling="Circuit trips after N failures; fallback response returned",
            ),
            IntegrationSpec(
                pattern=IntegrationPattern.BULKHEAD,
                description="Isolate critical resources to prevent systemic failure",
                components_involved=("Backend Service", "Database", "Queue"),
                protocol="Resource pool",
                data_format="N/A",
                error_handling="Resource exhaustion isolated to one pool; other pools unaffected",
            ),
        ]

        if has_third_party:
            specs.append(
                IntegrationSpec(
                    pattern=IntegrationPattern.STRANGER_FIG,
                    description="Gradually migrate from legacy to new system",
                    components_involved=("API Gateway", "Legacy System", "New System"),
                    protocol="HTTP / Message Queue",
                    data_format="JSON / XML",
                    error_handling="Route to legacy system if new system fails",
                )
            )

        if has_events:
            specs.append(
                IntegrationSpec(
                    pattern=IntegrationPattern.EVENT_DRIVEN,
                    description="Decoupled communication via event bus",
                    components_involved=("Producer", "Event Bus", "Consumer(s)"),
                    protocol="Kafka / RabbitMQ / PubSub",
                    data_format="Avro / Protobuf / JSON",
                    error_handling="Dead letter queue + retry with exponential backoff",
                )
            )

        return specs

    @staticmethod
    def _derive_constraints(requirements: str) -> list[str]:
        constraints: list[str] = [
            "Must support horizontal scaling for increased load",
            "Must maintain data integrity across all transactions",
            "Must implement idempotency for all mutating operations",
            "Must provide observability (logging, metrics, tracing)",
        ]
        if "compliance" in requirements or "regulatory" in requirements:
            constraints.append("Must maintain audit trail for all data changes")
        if "performance" in requirements or "latency" in requirements:
            constraints.append("P95 latency must remain under 500ms")
        return constraints

    @staticmethod
    def _define_assumptions(requirements: str) -> list[str]:
        return [
            "System will be deployed on cloud infrastructure (AWS/GCP/Azure)",
            "Team has experience with the recommended technology stack",
            "Sufficient CI/CD pipeline and automated testing in place",
            "Budget allows for managed services where recommended",
            "Security review will be conducted before production deployment",
        ]
