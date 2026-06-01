"""
GCP Architect Skill - Google Cloud Platform architecture design.

Given requirements, produces:
- GCP service recommendations
- Best practices alignment
- Cost optimization strategies
- Security design
- High availability architecture

Outputs structured GCP architecture plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GCPService(StrEnum):
    """Common GCP services."""

    COMPUTE_ENGINE = "Compute Engine"
    GKE = "GKE"
    CLOUD_RUN = "Cloud Run"
    CLOUD_FUNCTIONS = "Cloud Functions"
    CLOUD_STORAGE = "Cloud Storage"
    CLOUD_SQL = "Cloud SQL"
    FIRESTORE = "Firestore"
    CLOUD_CDN = "Cloud CDN"
    CLOUD_LOAD_BALANCING = "Cloud Load Balancing"


@dataclass(frozen=True)
class GCPServiceRecommendation:
    """GCP service recommendation."""

    service: GCPService
    purpose: str
    configuration: str
    estimated_cost: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class GCPArchitecturePlan:
    """Complete GCP architecture plan."""

    project_name: str
    services: tuple[GCPServiceRecommendation, ...]
    architecture_diagram: str
    security_controls: tuple[str, ...]
    cost_optimizations: tuple[str, ...]
    deployment_steps: tuple[str, ...]


class GCPArchitect:
    """GCP architecture skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run GCP architecture design.

        Args:
            input_data: Dictionary with keys:
                - requirements: System requirements description
                - project_name: Optional project name (default "GCP Project")

        Returns:
            Dictionary with GCP architecture plan data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project_name = input_data.get("project_name", "GCP Project")
        reqs_lower = requirements.lower()

        services = self._recommend_services(reqs_lower)
        diagram = self._build_diagram(services)
        security = self._design_security()
        cost_opts = self._recommend_cost_optimizations()
        deployment = self._plan_deployment()

        return GCPArchitecturePlan(
            project_name=project_name,
            services=tuple(services),
            architecture_diagram=diagram,
            security_controls=tuple(security),
            cost_optimizations=tuple(cost_opts),
            deployment_steps=tuple(deployment),
        ).__dict__ | {
            "services": [s.__dict__ for s in services],
        }

    @staticmethod
    def _recommend_services(requirements: str) -> list[GCPServiceRecommendation]:
        services: list[GCPServiceRecommendation] = []

        if "serverless" in requirements:
            services.append(
                GCPServiceRecommendation(
                    service=GCPService.CLOUD_RUN,
                    purpose="Serverless containers with auto-scaling",
                    configuration="2 vCPU, 4GB RAM, min instances: 0, max: 100",
                    estimated_cost="$0.00002400 per vCPU-second + $0.00000250 per GiB-second",
                    alternatives=("Cloud Functions", "GKE Autopilot"),
                )
            )
        elif "kubernetes" in requirements:
            services.append(
                GCPServiceRecommendation(
                    service=GCPService.GKE,
                    purpose="Managed Kubernetes for container orchestration",
                    configuration="Autopilot mode with 3-node cluster",
                    estimated_cost="$0.10 per cluster per hour + compute costs",
                    alternatives=("Cloud Run", "Compute Engine"),
                )
            )
        else:
            services.append(
                GCPServiceRecommendation(
                    service=GCPService.COMPUTE_ENGINE,
                    purpose="Virtual machines for application hosting",
                    configuration="n1-standard-2 instances in managed instance group",
                    estimated_cost="$0.095 per hour per instance",
                    alternatives=("Cloud Run", "GKE"),
                )
            )

        services.append(
            GCPServiceRecommendation(
                service=GCPService.CLOUD_STORAGE,
                purpose="Object storage for assets and backups",
                configuration="Standard storage class with lifecycle management",
                estimated_cost="$0.020 per GB per month",
                alternatives=("Persistent Disk", "Filestore"),
            )
        )

        if "nosql" in requirements:
            services.append(
                GCPServiceRecommendation(
                    service=GCPService.FIRESTORE,
                    purpose="Managed NoSQL document database",
                    configuration="Native mode with automatic scaling",
                    estimated_cost="$0.18 per GB stored + $0.06 per 100K reads",
                    alternatives=("Bigtable", "Cloud SQL"),
                )
            )
        else:
            services.append(
                GCPServiceRecommendation(
                    service=GCPService.CLOUD_SQL,
                    purpose="Managed relational database (PostgreSQL/MySQL)",
                    configuration="db-n1-standard-2 with high availability",
                    estimated_cost="$0.0965 per hour (HA doubles cost)",
                    alternatives=("Cloud Spanner", "Self-managed on Compute Engine"),
                )
            )

        services.append(
            GCPServiceRecommendation(
                service=GCPService.CLOUD_LOAD_BALANCING,
                purpose="Global load balancing with SSL termination",
                configuration="HTTPS load balancer with Cloud CDN",
                estimated_cost="$0.025 per hour + $0.008 per GB processed",
                alternatives=("Regional load balancer",),
            )
        )

        return services

    @staticmethod
    def _build_diagram(services: list[GCPServiceRecommendation]) -> str:
        lines = [
            "+" + "-" * 60 + "+",
            "|  GCP ARCHITECTURE DIAGRAM",
            "+" + "-" * 60 + "+",
            "",
            "  [Internet] --> [Cloud Load Balancing]",
            "                      |",
            "                      v",
            "  [VPC Network]",
        ]

        for svc in services:
            if svc.service in (GCPService.COMPUTE_ENGINE, GCPService.GKE, GCPService.CLOUD_RUN):
                lines.append(f"      +-- [{svc.service}]")

        lines.append("      |")
        lines.append("      v")

        for svc in services:
            if svc.service in (GCPService.CLOUD_SQL, GCPService.FIRESTORE):
                lines.append(f"      +-- [{svc.service}]")

        return "\n".join(lines)

    @staticmethod
    def _design_security() -> list[str]:
        return [
            "VPC with private subnets and Cloud NAT for outbound traffic",
            "IAM with least privilege and service accounts",
            "Encryption at rest with Cloud KMS",
            "Cloud Armor for DDoS protection",
            "Cloud Audit Logs for compliance monitoring",
        ]

    @staticmethod
    def _recommend_cost_optimizations() -> list[str]:
        return [
            "Use committed use discounts (1-3 year) for predictable workloads",
            "Enable Cloud Storage lifecycle policies to move to Nearline/Coldline",
            "Use preemptible VMs for batch workloads (up to 80% savings)",
            "Implement auto-scaling to match demand",
        ]

    @staticmethod
    def _plan_deployment() -> list[str]:
        return [
            "1. Set up GCP project and enable required APIs",
            "2. Configure VPC network with subnets",
            "3. Set up IAM roles and service accounts",
            "4. Deploy database layer with encryption",
            "5. Deploy compute layer with managed instance groups",
            "6. Configure Cloud Load Balancing with SSL",
            "7. Set up Cloud Monitoring and alerting",
            "8. Enable Cloud Audit Logs",
            "9. Deploy application via Cloud Build/Cloud Deploy",
            "10. Conduct security review",
        ]
