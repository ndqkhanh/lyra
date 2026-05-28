"""
Cloud Architect Skill - Cloud architecture design and analysis.

Given requirements, produces:
- Cloud service recommendations (AWS/GCP/Azure)
- Architecture diagram description (ASCII art)
- Cost estimates
- High-availability design
- Security considerations

Outputs structured cloud architecture plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CloudProvider(StrEnum):
    """Supported cloud providers."""

    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"
    MULTI = "Multi-Cloud"
    HYBRID = "Hybrid"


class ComputeTier(StrEnum):
    """Compute tier classifications."""

    SERVERLESS = "serverless"
    CONTAINER = "container"
    VM = "virtual_machine"
    BATCH = "batch"
    EDGE = "edge"


class DatabaseType(StrEnum):
    """Database type recommendations."""

    RELATIONAL = "relational"
    NOSQL_KEY_VALUE = "nosql_key_value"
    NOSQL_DOCUMENT = "nosql_document"
    NOSQL_WIDE_COLUMN = "nosql_wide_column"
    CACHE = "cache"
    SEARCH = "search"
    DATA_WAREHOUSE = "data_warehouse"
    TIME_SERIES = "time_series"
    GRAPH = "graph"


@dataclass(frozen=True)
class CloudServiceRecommendation:
    """A single cloud service recommendation."""

    service_name: str
    provider: CloudProvider
    purpose: str
    estimated_monthly_cost: str
    alternative: str
    rationale: str


@dataclass(frozen=True)
class ArchitectureComponent:
    """A component in the architecture diagram."""

    name: str
    type: str
    provider_service: str
    tier: str
    scaling_strategy: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class AvailabilityTier:
    """High-availability configuration tier."""

    sla_percentage: str
    multi_az: bool
    multi_region: bool
    backup_strategy: str
    failover_time: str
    rpo: str
    rto: str


@dataclass(frozen=True)
class SecurityControl:
    """A security control or recommendation."""

    category: str
    control: str
    implementation: str
    priority: str
    compliance_mapping: str


@dataclass(frozen=True)
class CostBreakdown:
    """Monthly cost breakdown by category."""

    compute: str
    storage: str
    networking: str
    database: str
    managed_services: str
    data_transfer: str
    total_estimated: str
    currency: str


@dataclass(frozen=True)
class CloudArchitectureDesign:
    """Complete cloud architecture design."""

    title: str
    provider: CloudProvider
    components: tuple[ArchitectureComponent, ...]
    services: tuple[CloudServiceRecommendation, ...]
    ascii_diagram: str
    availability: AvailabilityTier
    security_controls: tuple[SecurityControl, ...]
    cost: CostBreakdown
    considerations: tuple[str, ...]


# ---------------------------------------------------------------------------
# Cloud service catalog for recommendations
# ---------------------------------------------------------------------------
_SERVICE_CATALOG: dict[str, dict[str, str]] = {
    "compute": {
        "AWS": "EC2 / ECS / EKS / Lambda",
        "GCP": "Compute Engine / GKE / Cloud Run / Cloud Functions",
        "Azure": "VM / AKS / App Service / Azure Functions",
    },
    "storage": {
        "AWS": "S3 / EBS / EFS",
        "GCP": "Cloud Storage / Persistent Disk / Filestore",
        "Azure": "Blob Storage / Disk Storage / Files",
    },
    "database_relational": {
        "AWS": "RDS / Aurora",
        "GCP": "Cloud SQL / Spanner",
        "Azure": "Azure SQL / Cosmos DB (SQL API)",
    },
    "database_nosql": {
        "AWS": "DynamoDB / ElastiCache",
        "GCP": "Firestore / Memorystore / Bigtable",
        "Azure": "Cosmos DB / Azure Cache for Redis",
    },
    "cdn": {
        "AWS": "CloudFront",
        "GCP": "Cloud CDN",
        "Azure": "Azure CDN",
    },
    "lb": {
        "AWS": "ALB / NLB",
        "GCP": "Cloud Load Balancing",
        "Azure": "Azure Load Balancer / Application Gateway",
    },
    "queue": {
        "AWS": "SQS / SNS / EventBridge",
        "GCP": "Pub/Sub",
        "Azure": "Queue Storage / Service Bus / Event Grid",
    },
    "monitoring": {
        "AWS": "CloudWatch / X-Ray",
        "GCP": "Cloud Monitoring / Cloud Trace",
        "Azure": "Azure Monitor / Application Insights",
    },
}


class CloudArchitect:
    """Cloud architecture skill producing structured designs."""

    def __init__(self) -> None:
        self._provider: CloudProvider = CloudProvider.AWS

    def run(self, input_data: dict) -> dict:
        """Run cloud architecture design.

        Args:
            input_data: Dictionary with keys:
                - requirements: Description of system requirements
                - project_name: Optional project name (default "Cloud Architecture")
                - provider: Optional provider preference (default "AWS")
                - budget_monthly: Optional monthly budget constraint (default "TBD")

        Returns:
            Dictionary with architecture design data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project_name = input_data.get("project_name", "Cloud Architecture")
        provider_str = input_data.get("provider", "AWS").upper()
        budget = input_data.get("budget_monthly", "TBD")

        try:
            self._provider = CloudProvider(provider_str)
        except ValueError:
            self._provider = CloudProvider.AWS

        reqs_lower = requirements.lower()

        components = self._design_components(reqs_lower, project_name)
        ascii_diagram = self._build_diagram(components)
        services = self._recommend_services(reqs_lower, project_name)
        availability = self._design_availability(reqs_lower)
        security = self._design_security(reqs_lower)
        cost = self._estimate_cost(
            services, availability, budget, self._provider
        )
        considerations = self._list_considerations(reqs_lower)

        return CloudArchitectureDesign(
            title=project_name,
            provider=self._provider,
            components=tuple(components),
            services=tuple(services),
            ascii_diagram=ascii_diagram,
            availability=availability,
            security_controls=tuple(security),
            cost=cost,
            considerations=tuple(considerations),
        ).__dict__ | {
            "components": [c.__dict__ for c in components],
            "services": [s.__dict__ for s in services],
            "availability": availability.__dict__,
            "cost": cost.__dict__,
            "security_controls": [s.__dict__ for s in security],
        }

    def _design_components(
        self, requirements: str, project: str
    ) -> list[ArchitectureComponent]:
        needs_db = any(kw in requirements for kw in ["database", "sql", "nosql", "persist"])
        needs_cache = "cache" in requirements or "redis" in requirements
        needs_queue = any(kw in requirements for kw in ["queue", "async", "event", "message"])
        needs_auth = any(kw in requirements for kw in ["auth", "login", "user", "oauth"])
        needs_cdn = any(kw in requirements for kw in ["cdn", "global", "static", "worldwide"])

        components: list[ArchitectureComponent] = [
            ArchitectureComponent(
                name=f"{project}-lb",
                type="load_balancer",
                provider_service=_SERVICE_CATALOG["lb"][self._provider.value],
                tier="frontend",
                scaling_strategy="auto-scaling group / multi-AZ",
                dependencies=(),
            ),
            ArchitectureComponent(
                name=f"{project}-web",
                type="compute",
                provider_service=_SERVICE_CATALOG["compute"][self._provider.value],
                tier="application",
                scaling_strategy="horizontal auto-scaling (CPU/memory based)",
                dependencies=(f"{project}-lb",),
            ),
        ]

        if needs_db:
            db_type = "database_relational"
            for t in ("nosql", "document", "key-value", "dynamo"):
                if t in requirements:
                    db_type = "database_nosql"
                    break
            components.append(
                ArchitectureComponent(
                    name=f"{project}-db",
                    type="database",
                    provider_service=_SERVICE_CATALOG[db_type][self._provider.value],
                    tier="data",
                    scaling_strategy="read replicas / sharding",
                    dependencies=(f"{project}-web",),
                )
            )

        if needs_cache:
            cache_service = {
                "AWS": "ElastiCache (Redis)",
                "GCP": "Memorystore (Redis)",
                "Azure": "Azure Cache for Redis",
            }
            components.append(
                ArchitectureComponent(
                    name=f"{project}-cache",
                    type="cache",
                    provider_service=cache_service.get(self._provider.value, "Redis"),
                    tier="data",
                    scaling_strategy="cluster mode / read replicas",
                    dependencies=(f"{project}-web",),
                )
            )

        if needs_queue:
            queue_service = _SERVICE_CATALOG["queue"][self._provider.value]
            components.append(
                ArchitectureComponent(
                    name=f"{project}-queue",
                    type="message_queue",
                    provider_service=queue_service,
                    tier="integration",
                    scaling_strategy="partition-based throughput scaling",
                    dependencies=(),
                )
            )

        if needs_auth:
            auth_service = {
                "AWS": "Cognito / IAM",
                "GCP": "Identity Platform / Cloud IAM",
                "Azure": "Azure AD / Managed Identity",
            }
            components.append(
                ArchitectureComponent(
                    name=f"{project}-auth",
                    type="auth",
                    provider_service=auth_service.get(self._provider.value, "OIDC Provider"),
                    tier="security",
                    scaling_strategy="managed (auto-scaling)",
                    dependencies=(f"{project}-web",),
                )
            )

        if needs_cdn:
            cdn_service = _SERVICE_CATALOG["cdn"][self._provider.value]
            components.append(
                ArchitectureComponent(
                    name=f"{project}-cdn",
                    type="cdn",
                    provider_service=cdn_service,
                    tier="frontend",
                    scaling_strategy="global edge network",
                    dependencies=(f"{project}-lb",),
                )
            )

        return components

    @staticmethod
    def _build_diagram(components: list[ArchitectureComponent]) -> str:
        if not components:
            return "(No components to diagram)"

        lines: list[str] = [
            "+" + "-" * 60 + "+",
            "|  CLOUD ARCHITECTURE DIAGRAM",
            "+" + "-" * 60 + "+",
            "",
        ]

        tiers = ["frontend", "security", "application", "integration", "data"]
        tier_labels = {
            "frontend": "PRESENTATION TIER",
            "security": "SECURITY TIER",
            "application": "APPLICATION TIER",
            "integration": "INTEGRATION TIER",
            "data": "DATA TIER",
        }

        for tier in tiers:
            tier_comps = [c for c in components if c.tier == tier]
            if not tier_comps:
                continue

            label = tier_labels.get(tier, tier.upper())
            lines.append(f"  [{label}]")
            lines.append("  " + "+" + "-" * 56 + "+")

            for comp in tier_comps:
                dep_line = ""
                if comp.dependencies:
                    arrows = ", ".join(f"--> {d}" for d in comp.dependencies)
                    dep_line = f"  {arrows}"
                lines.append(f"  |  {comp.name:30s} | {comp.provider_service}")
                if dep_line:
                    lines.append(f"  |  {dep_line:56s} |")
            lines.append("  " + "+" + "-" * 56 + "+")
            lines.append("")

        return "\n".join(lines)

    def _recommend_services(
        self, requirements: str, project: str
    ) -> list[CloudServiceRecommendation]:
        needs_compute = True
        needs_storage = True
        needs_db = any(kw in requirements for kw in ["database", "sql", "nosql", "persist"])
        needs_monitoring = True

        services: list[CloudServiceRecommendation] = []

        if needs_compute:
            services.append(
                CloudServiceRecommendation(
                    service_name=f"{project}-compute",
                    provider=self._provider,
                    purpose="Application compute (containers or serverless)",
                    estimated_monthly_cost="$200-$2,000 (varies by load)",
                    alternative=_SERVICE_CATALOG["compute"]["GCP"]
                    if self._provider == CloudProvider.AWS
                    else _SERVICE_CATALOG["compute"]["AWS"],
                    rationale="Chosen for scalability and managed operations",
                )
            )

        if needs_storage:
            services.append(
                CloudServiceRecommendation(
                    service_name=f"{project}-storage",
                    provider=self._provider,
                    purpose="Object storage for assets and backups",
                    estimated_monthly_cost="$50-$500 (per TB)",
                    alternative=_SERVICE_CATALOG["storage"]["GCP"]
                    if self._provider == CloudProvider.AWS
                    else _SERVICE_CATALOG["storage"]["AWS"],
                    rationale="Durable, cost-effective object storage with lifecycle policies",
                )
            )

        if needs_db:
            db_purpose = "Relational database for structured data"
            db_cost = "$100-$1,000 (per instance)"
            services.append(
                CloudServiceRecommendation(
                    service_name=f"{project}-db",
                    provider=self._provider,
                    purpose=db_purpose,
                    estimated_monthly_cost=db_cost,
                    alternative="Self-managed PostgreSQL on EC2",
                    rationale="Managed DB reduces operational overhead",
                )
            )

        if needs_monitoring:
            services.append(
                CloudServiceRecommendation(
                    service_name=f"{project}-monitoring",
                    provider=self._provider,
                    purpose="Observability (logs, metrics, traces)",
                    estimated_monthly_cost="$50-$300",
                    alternative=_SERVICE_CATALOG["monitoring"]["GCP"]
                    if self._provider == CloudProvider.AWS
                    else _SERVICE_CATALOG["monitoring"]["AWS"],
                    rationale="Native integration with other cloud services",
                )
            )

        return services

    @staticmethod
    def _design_availability(requirements: str) -> AvailabilityTier:
        needs_high_avail = any(
            kw in requirements for kw in
            ["high availability", "ha", "fault tolerant", "redundant", "multi-region"]
        )
        needs_disaster_recovery = any(
            kw in requirements for kw in
            ["disaster recovery", "dr", "backup", "rpo", "rto"]
        )

        if needs_high_avail and needs_disaster_recovery:
            return AvailabilityTier(
                sla_percentage="99.99%",
                multi_az=True,
                multi_region=True,
                backup_strategy="Cross-region replication + daily snapshots",
                failover_time="< 1 minute (active-active); < 5 minutes (active-passive)",
                rpo="< 1 minute",
                rto="< 5 minutes",
            )
        if needs_high_avail:
            return AvailabilityTier(
                sla_percentage="99.95%",
                multi_az=True,
                multi_region=False,
                backup_strategy="Multi-AZ with automatic failover",
                failover_time="< 30 seconds (DNS / LB failover)",
                rpo="< 5 minutes",
                rto="< 15 minutes",
            )
        return AvailabilityTier(
            sla_percentage="99.5%",
            multi_az=False,
            multi_region=False,
            backup_strategy="Daily snapshots + backup retention (30 days)",
            failover_time="Manual intervention required",
            rpo="24 hours",
            rto="< 4 hours",
        )

    @staticmethod
    def _design_security(requirements: str) -> list[SecurityControl]:
        compliance_needed = any(
            kw in requirements for kw in
            ["hipaa", "pci", "gdpr", "sox", "soc2", "compliance"]
        )

        controls: list[SecurityControl] = [
            SecurityControl(
                category="Network",
                control="VPC with private/public subnets",
                implementation="NAT gateway for outbound; security groups for inbound",
                priority="HIGH",
                compliance_mapping="NIST CSF (PR.AC-5)",
            ),
            SecurityControl(
                category="Identity",
                control="IAM with least privilege",
                implementation="Role-based access control (RBAC) per service",
                priority="HIGH",
                compliance_mapping="NIST CSF (PR.AC-4)",
            ),
            SecurityControl(
                category="Data",
                control="Encryption at rest and in transit",
                implementation="TLS 1.3 + KMS-managed encryption keys",
                priority="HIGH",
                compliance_mapping="NIST CSF (PR.DS-2)",
            ),
            SecurityControl(
                category="Monitoring",
                control="CloudTrail / Audit Logs + SIEM integration",
                implementation="Centralized logging with alerting",
                priority="MEDIUM",
                compliance_mapping="NIST CSF (DE.CM-3)",
            ),
        ]

        if compliance_needed:
            controls.append(
                SecurityControl(
                    category="Compliance",
                    control="Automated compliance scanning",
                    implementation="AWS Config / Azure Policy / GCP Org Policies",
                    priority="HIGH",
                    compliance_mapping="NIST CSF (ID.GV-3)",
                )
            )

        return controls

    @staticmethod
    def _estimate_cost(
        services: list[CloudServiceRecommendation],
        availability: AvailabilityTier,
        budget: str,
        provider: CloudProvider,
    ) -> CostBreakdown:
        total_str = "TBD"
        if budget != "TBD":
            total_str = f"Up to ${budget}/month"

        return CostBreakdown(
            compute="$200 - $2,000",
            storage="$50 - $500",
            networking="$50 - $300",
            database="$100 - $1,000",
            managed_services="$50 - $300",
            data_transfer="$20 - $200" if availability.multi_region else "$10 - $100",
            total_estimated=total_str or "$500 - $4,500",
            currency="USD",
        )

    @staticmethod
    def _list_considerations(requirements: str) -> list[str]:
        considerations: list[str] = [
            "Lock-in: Evaluate multi-cloud strategy for critical components",
            "Cost governance: Set budgets and alerts to avoid cost overruns",
            "Scalability: Design for horizontal scaling from day one",
            "Observability: Implement logging, metrics, and tracing",
        ]

        if "migration" in requirements or "migrate" in requirements:
            considerations.append(
                "Migration: Use a phased approach (Rehost -> Replatform -> Refactor)"
            )
        if "global" in requirements or "multi-region" in requirements:
            considerations.append(
                "Global: Consider edge caching and regional deployment for latency"
            )
        if "serverless" in requirements:
            considerations.append(
                "Serverless: Watch for cold starts and concurrent execution limits"
            )
        if "kubernetes" in requirements or "k8s" in requirements:
            considerations.append(
                "Kubernetes: Plan cluster autoscaling, node pools, and cost optimization"
            )

        return considerations
