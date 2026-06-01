"""
AWS Architect Skill - AWS cloud architecture design and best practices.

Given requirements, produces:
- AWS service recommendations
- Well-Architected Framework alignment
- Cost optimization strategies
- Security and compliance design
- High availability architecture

Outputs structured AWS architecture plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AWSService(StrEnum):
    """Common AWS services."""

    EC2 = "EC2"
    ECS = "ECS"
    EKS = "EKS"
    LAMBDA = "Lambda"
    S3 = "S3"
    RDS = "RDS"
    DYNAMODB = "DynamoDB"
    CLOUDFRONT = "CloudFront"
    ROUTE53 = "Route53"
    ALB = "Application Load Balancer"
    API_GATEWAY = "API Gateway"


class WellArchitectedPillar(StrEnum):
    """AWS Well-Architected Framework pillars."""

    OPERATIONAL_EXCELLENCE = "operational_excellence"
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE_EFFICIENCY = "performance_efficiency"
    COST_OPTIMIZATION = "cost_optimization"
    SUSTAINABILITY = "sustainability"


@dataclass(frozen=True)
class ServiceRecommendation:
    """AWS service recommendation."""

    service: AWSService
    purpose: str
    configuration: str
    estimated_cost: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class WellArchitectedAlignment:
    """Alignment with Well-Architected Framework."""

    pillar: WellArchitectedPillar
    score: str
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]


@dataclass(frozen=True)
class CostOptimization:
    """Cost optimization recommendation."""

    category: str
    recommendation: str
    estimated_savings: str
    implementation_effort: str


@dataclass(frozen=True)
class SecurityControl:
    """AWS security control."""

    control_name: str
    aws_service: str
    implementation: str
    compliance_frameworks: tuple[str, ...]


@dataclass(frozen=True)
class AWSArchitecturePlan:
    """Complete AWS architecture plan."""

    project_name: str
    services: tuple[ServiceRecommendation, ...]
    well_architected: tuple[WellArchitectedAlignment, ...]
    cost_optimizations: tuple[CostOptimization, ...]
    security_controls: tuple[SecurityControl, ...]
    architecture_diagram: str
    deployment_steps: tuple[str, ...]


class AWSArchitect:
    """AWS architecture skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run AWS architecture design.

        Args:
            input_data: Dictionary with keys:
                - requirements: System requirements description
                - project_name: Optional project name (default "AWS Project")
                - budget_monthly: Optional monthly budget (default "TBD")

        Returns:
            Dictionary with AWS architecture plan data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project_name = input_data.get("project_name", "AWS Project")
        budget = input_data.get("budget_monthly", "TBD")

        reqs_lower = requirements.lower()

        services = self._recommend_services(reqs_lower, project_name)
        well_arch = self._assess_well_architected(reqs_lower)
        cost_opts = self._recommend_cost_optimizations(budget)
        security = self._design_security_controls(reqs_lower)
        diagram = self._build_diagram(services)
        deployment = self._plan_deployment(services)

        return AWSArchitecturePlan(
            project_name=project_name,
            services=tuple(services),
            well_architected=tuple(well_arch),
            cost_optimizations=tuple(cost_opts),
            security_controls=tuple(security),
            architecture_diagram=diagram,
            deployment_steps=tuple(deployment),
        ).__dict__ | {
            "services": [s.__dict__ for s in services],
            "well_architected": [w.__dict__ for w in well_arch],
            "cost_optimizations": [c.__dict__ for c in cost_opts],
            "security_controls": [s.__dict__ for s in security],
        }

    @staticmethod
    def _recommend_services(requirements: str, project: str) -> list[ServiceRecommendation]:
        services: list[ServiceRecommendation] = []

        # Compute
        if "serverless" in requirements or "lambda" in requirements:
            services.append(
                ServiceRecommendation(
                    service=AWSService.LAMBDA,
                    purpose="Serverless compute for event-driven workloads",
                    configuration="Memory: 1024MB, Timeout: 30s, Provisioned concurrency for critical paths",
                    estimated_cost="$0.20 per 1M requests + $0.0000166667 per GB-second",
                    alternatives=("Fargate", "EC2"),
                )
            )
        elif "container" in requirements or "docker" in requirements:
            services.append(
                ServiceRecommendation(
                    service=AWSService.ECS,
                    purpose="Container orchestration with Fargate",
                    configuration="Fargate launch type, 2 vCPU, 4GB RAM per task",
                    estimated_cost="$0.04048 per vCPU per hour + $0.004445 per GB per hour",
                    alternatives=("EKS", "EC2 with Docker"),
                )
            )
        else:
            services.append(
                ServiceRecommendation(
                    service=AWSService.EC2,
                    purpose="Virtual machines for application hosting",
                    configuration="t3.medium instances in Auto Scaling Group",
                    estimated_cost="$0.0416 per hour per instance",
                    alternatives=("ECS", "Lambda"),
                )
            )

        # Storage
        services.append(
            ServiceRecommendation(
                service=AWSService.S3,
                purpose="Object storage for assets, backups, and data lake",
                configuration="Standard storage class with lifecycle policies to Glacier",
                estimated_cost="$0.023 per GB per month (Standard)",
                alternatives=("EFS", "EBS"),
            )
        )

        # Database
        if "nosql" in requirements or "dynamodb" in requirements:
            services.append(
                ServiceRecommendation(
                    service=AWSService.DYNAMODB,
                    purpose="Managed NoSQL database for high-scale applications",
                    configuration="On-demand billing mode with DynamoDB Streams",
                    estimated_cost="$1.25 per million write requests, $0.25 per million read requests",
                    alternatives=("DocumentDB", "RDS"),
                )
            )
        else:
            services.append(
                ServiceRecommendation(
                    service=AWSService.RDS,
                    purpose="Managed relational database (PostgreSQL/MySQL)",
                    configuration="db.t3.medium Multi-AZ with automated backups",
                    estimated_cost="$0.068 per hour (Multi-AZ doubles cost)",
                    alternatives=("Aurora", "Self-managed on EC2"),
                )
            )

        # CDN
        if "cdn" in requirements or "global" in requirements:
            services.append(
                ServiceRecommendation(
                    service=AWSService.CLOUDFRONT,
                    purpose="Global CDN for low-latency content delivery",
                    configuration="Standard distribution with origin from S3/ALB",
                    estimated_cost="$0.085 per GB (first 10TB)",
                    alternatives=("Third-party CDN",),
                )
            )

        # Load Balancer
        services.append(
            ServiceRecommendation(
                service=AWSService.ALB,
                purpose="Application load balancing with path-based routing",
                configuration="Internet-facing ALB with SSL termination",
                estimated_cost="$0.0225 per hour + $0.008 per LCU-hour",
                alternatives=("NLB", "CloudFront"),
            )
        )

        return services

    @staticmethod
    def _assess_well_architected(requirements: str) -> list[WellArchitectedAlignment]:
        return [
            WellArchitectedAlignment(
                pillar=WellArchitectedPillar.SECURITY,
                score="GOOD",
                strengths=(
                    "VPC with private subnets",
                    "IAM roles with least privilege",
                    "Encryption at rest and in transit",
                ),
                improvements=(
                    "Enable AWS Config for compliance monitoring",
                    "Implement AWS WAF for application protection",
                ),
            ),
            WellArchitectedAlignment(
                pillar=WellArchitectedPillar.RELIABILITY,
                score="GOOD",
                strengths=(
                    "Multi-AZ deployment",
                    "Auto Scaling for compute",
                    "Automated backups",
                ),
                improvements=(
                    "Add multi-region failover for critical workloads",
                    "Implement chaos engineering tests",
                ),
            ),
            WellArchitectedAlignment(
                pillar=WellArchitectedPillar.COST_OPTIMIZATION,
                score="MODERATE",
                strengths=(
                    "Right-sized instances",
                    "S3 lifecycle policies",
                ),
                improvements=(
                    "Use Savings Plans or Reserved Instances",
                    "Implement auto-shutdown for non-prod environments",
                ),
            ),
        ]

    @staticmethod
    def _recommend_cost_optimizations(budget: str) -> list[CostOptimization]:
        return [
            CostOptimization(
                category="Compute",
                recommendation="Use Savings Plans for predictable workloads (1-year commitment)",
                estimated_savings="Up to 72% vs On-Demand",
                implementation_effort="LOW",
            ),
            CostOptimization(
                category="Storage",
                recommendation="Enable S3 Intelligent-Tiering for automatic cost optimization",
                estimated_savings="Up to 70% for infrequently accessed data",
                implementation_effort="LOW",
            ),
            CostOptimization(
                category="Database",
                recommendation="Use Aurora Serverless v2 for variable workloads",
                estimated_savings="Up to 90% vs provisioned capacity",
                implementation_effort="MEDIUM",
            ),
            CostOptimization(
                category="Monitoring",
                recommendation="Use CloudWatch Logs Insights instead of exporting to S3",
                estimated_savings="Reduce data transfer costs",
                implementation_effort="LOW",
            ),
        ]

    @staticmethod
    def _design_security_controls(requirements: str) -> list[SecurityControl]:
        controls = [
            SecurityControl(
                control_name="Network Isolation",
                aws_service="VPC",
                implementation="Private subnets for compute, public subnets for load balancers",
                compliance_frameworks=("SOC 2", "ISO 27001", "PCI DSS"),
            ),
            SecurityControl(
                control_name="Identity and Access Management",
                aws_service="IAM",
                implementation="Role-based access with MFA enforcement",
                compliance_frameworks=("SOC 2", "ISO 27001", "HIPAA"),
            ),
            SecurityControl(
                control_name="Data Encryption",
                aws_service="KMS",
                implementation="Encrypt all data at rest with KMS, TLS 1.3 in transit",
                compliance_frameworks=("HIPAA", "PCI DSS", "GDPR"),
            ),
            SecurityControl(
                control_name="Audit Logging",
                aws_service="CloudTrail",
                implementation="Enable CloudTrail for all regions with S3 log storage",
                compliance_frameworks=("SOC 2", "ISO 27001", "HIPAA"),
            ),
        ]

        if "compliance" in requirements or "hipaa" in requirements:
            controls.append(
                SecurityControl(
                    control_name="Compliance Monitoring",
                    aws_service="AWS Config",
                    implementation="Automated compliance rules with SNS alerting",
                    compliance_frameworks=("HIPAA", "PCI DSS", "SOC 2"),
                )
            )

        return controls

    @staticmethod
    def _build_diagram(services: list[ServiceRecommendation]) -> str:
        lines = [
            "+" + "-" * 60 + "+",
            "|  AWS ARCHITECTURE DIAGRAM",
            "+" + "-" * 60 + "+",
            "",
            "  [Internet]",
            "      |",
            "      v",
        ]

        for svc in services:
            if svc.service in (AWSService.CLOUDFRONT, AWSService.ROUTE53):
                lines.append(f"  [{svc.service}] - {svc.purpose[:40]}")
                lines.append("      |")
                lines.append("      v")

        for svc in services:
            if svc.service == AWSService.ALB:
                lines.append(f"  [{svc.service}] - {svc.purpose[:40]}")
                lines.append("      |")
                lines.append("      v")

        lines.append("  [VPC]")
        lines.append("      |")

        for svc in services:
            if svc.service in (AWSService.EC2, AWSService.ECS, AWSService.LAMBDA):
                lines.append(f"      +-- [{svc.service}] - {svc.purpose[:35]}")

        lines.append("      |")
        lines.append("      v")

        for svc in services:
            if svc.service in (AWSService.RDS, AWSService.DYNAMODB, AWSService.S3):
                lines.append(f"      +-- [{svc.service}] - {svc.purpose[:35]}")

        return "\n".join(lines)

    @staticmethod
    def _plan_deployment(services: list[ServiceRecommendation]) -> list[str]:
        return [
            "1. Set up VPC with public and private subnets across 3 AZs",
            "2. Configure IAM roles and policies for all services",
            "3. Deploy database layer (RDS/DynamoDB) with encryption",
            "4. Set up compute layer (EC2/ECS/Lambda) with Auto Scaling",
            "5. Configure Application Load Balancer with SSL certificate",
            "6. Set up CloudFront distribution (if applicable)",
            "7. Configure CloudWatch monitoring and alarms",
            "8. Enable CloudTrail and AWS Config for compliance",
            "9. Deploy application code via CodePipeline/CodeDeploy",
            "10. Conduct security review and penetration testing",
        ]
