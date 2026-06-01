"""
Azure Architect Skill - Microsoft Azure architecture design.

Given requirements, produces:
- Azure service recommendations
- Well-Architected Framework alignment
- Cost optimization strategies
- Security design
- High availability architecture

Outputs structured Azure architecture plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AzureService(StrEnum):
    """Common Azure services."""

    VIRTUAL_MACHINES = "Virtual Machines"
    AKS = "AKS"
    APP_SERVICE = "App Service"
    FUNCTIONS = "Azure Functions"
    BLOB_STORAGE = "Blob Storage"
    SQL_DATABASE = "Azure SQL Database"
    COSMOS_DB = "Cosmos DB"
    CDN = "Azure CDN"
    APPLICATION_GATEWAY = "Application Gateway"


@dataclass(frozen=True)
class AzureServiceRecommendation:
    """Azure service recommendation."""

    service: AzureService
    purpose: str
    configuration: str
    estimated_cost: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class AzureArchitecturePlan:
    """Complete Azure architecture plan."""

    project_name: str
    services: tuple[AzureServiceRecommendation, ...]
    architecture_diagram: str
    security_controls: tuple[str, ...]
    cost_optimizations: tuple[str, ...]
    deployment_steps: tuple[str, ...]


class AzureArchitect:
    """Azure architecture skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run Azure architecture design.

        Args:
            input_data: Dictionary with keys:
                - requirements: System requirements description
                - project_name: Optional project name (default "Azure Project")

        Returns:
            Dictionary with Azure architecture plan data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project_name = input_data.get("project_name", "Azure Project")
        reqs_lower = requirements.lower()

        services = self._recommend_services(reqs_lower)
        diagram = self._build_diagram(services)
        security = self._design_security()
        cost_opts = self._recommend_cost_optimizations()
        deployment = self._plan_deployment()

        return AzureArchitecturePlan(
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
    def _recommend_services(requirements: str) -> list[AzureServiceRecommendation]:
        services: list[AzureServiceRecommendation] = []

        if "serverless" in requirements:
            services.append(
                AzureServiceRecommendation(
                    service=AzureService.FUNCTIONS,
                    purpose="Serverless compute for event-driven workloads",
                    configuration="Consumption plan with 1GB memory",
                    estimated_cost="$0.20 per million executions + $0.000016 per GB-s",
                    alternatives=("App Service", "Container Instances"),
                )
            )
        elif "kubernetes" in requirements:
            services.append(
                AzureServiceRecommendation(
                    service=AzureService.AKS,
                    purpose="Managed Kubernetes for container orchestration",
                    configuration="3-node cluster with Standard_D2s_v3 VMs",
                    estimated_cost="$0.10 per cluster per hour + VM costs",
                    alternatives=("App Service", "Virtual Machines"),
                )
            )
        else:
            services.append(
                AzureServiceRecommendation(
                    service=AzureService.VIRTUAL_MACHINES,
                    purpose="Virtual machines for application hosting",
                    configuration="Standard_D2s_v3 in availability set",
                    estimated_cost="$0.096 per hour per VM",
                    alternatives=("App Service", "AKS"),
                )
            )

        services.append(
            AzureServiceRecommendation(
                service=AzureService.BLOB_STORAGE,
                purpose="Object storage for assets and backups",
                configuration="Hot tier with lifecycle management",
                estimated_cost="$0.0184 per GB per month",
                alternatives=("Files", "Disk Storage"),
            )
        )

        if "nosql" in requirements:
            services.append(
                AzureServiceRecommendation(
                    service=AzureService.COSMOS_DB,
                    purpose="Globally distributed NoSQL database",
                    configuration="Serverless mode with automatic scaling",
                    estimated_cost="$0.25 per million RUs consumed",
                    alternatives=("Table Storage", "Azure SQL"),
                )
            )
        else:
            services.append(
                AzureServiceRecommendation(
                    service=AzureService.SQL_DATABASE,
                    purpose="Managed relational database",
                    configuration="General Purpose, 2 vCores with zone redundancy",
                    estimated_cost="$0.54 per hour",
                    alternatives=("Cosmos DB", "PostgreSQL"),
                )
            )

        services.append(
            AzureServiceRecommendation(
                service=AzureService.APPLICATION_GATEWAY,
                purpose="Application load balancing with WAF",
                configuration="Standard_v2 with SSL termination",
                estimated_cost="$0.246 per hour + $0.008 per GB processed",
                alternatives=("Load Balancer", "Front Door"),
            )
        )

        return services

    @staticmethod
    def _build_diagram(services: list[AzureServiceRecommendation]) -> str:
        lines = [
            "+" + "-" * 60 + "+",
            "|  AZURE ARCHITECTURE DIAGRAM",
            "+" + "-" * 60 + "+",
            "",
            "  [Internet] --> [Application Gateway]",
            "                      |",
            "                      v",
            "  [Virtual Network]",
        ]

        for svc in services:
            if svc.service in (AzureService.VIRTUAL_MACHINES, AzureService.AKS, AzureService.APP_SERVICE):
                lines.append(f"      +-- [{svc.service}]")

        lines.append("      |")
        lines.append("      v")

        for svc in services:
            if svc.service in (AzureService.SQL_DATABASE, AzureService.COSMOS_DB):
                lines.append(f"      +-- [{svc.service}]")

        return "\n".join(lines)

    @staticmethod
    def _design_security() -> list[str]:
        return [
            "Virtual Network with NSGs for network isolation",
            "Azure AD with RBAC and managed identities",
            "Encryption at rest with Azure Key Vault",
            "Azure Firewall for network security",
            "Azure Monitor and Log Analytics for auditing",
        ]

    @staticmethod
    def _recommend_cost_optimizations() -> list[str]:
        return [
            "Use Azure Reserved Instances (1-3 year) for predictable workloads",
            "Enable auto-shutdown for dev/test VMs",
            "Use Azure Hybrid Benefit for Windows Server licenses",
            "Implement auto-scaling to match demand",
        ]

    @staticmethod
    def _plan_deployment() -> list[str]:
        return [
            "1. Set up Azure subscription and resource groups",
            "2. Configure Virtual Network with subnets",
            "3. Set up Azure AD and RBAC",
            "4. Deploy database layer with encryption",
            "5. Deploy compute layer with availability sets",
            "6. Configure Application Gateway with WAF",
            "7. Set up Azure Monitor and alerts",
            "8. Enable Azure Security Center",
            "9. Deploy application via Azure DevOps",
            "10. Conduct security review",
        ]
