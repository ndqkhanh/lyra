"""
Terraform Engineer Skill - Infrastructure as Code with Terraform.

Given requirements, produces:
- Terraform module structure
- Resource definitions
- State management strategy
- CI/CD integration
- Best practices and conventions

Outputs structured Terraform plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TerraformProvider(StrEnum):
    """Terraform providers."""

    AWS = "aws"
    AZURE = "azurerm"
    GCP = "google"
    KUBERNETES = "kubernetes"
    HELM = "helm"


class StateBackend(StrEnum):
    """Terraform state backends."""

    S3 = "s3"
    AZURE_BLOB = "azurerm"
    GCS = "gcs"
    TERRAFORM_CLOUD = "remote"


@dataclass(frozen=True)
class TerraformModule:
    """Terraform module specification."""

    module_name: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    resources: tuple[str, ...]


@dataclass(frozen=True)
class StateManagement:
    """State management configuration."""

    backend: StateBackend
    configuration: str
    locking: bool
    encryption: bool


@dataclass(frozen=True)
class CICDIntegration:
    """CI/CD pipeline integration."""

    tool: str
    stages: tuple[str, ...]
    approval_gates: tuple[str, ...]


@dataclass(frozen=True)
class TerraformPlan:
    """Complete Terraform infrastructure plan."""

    project_name: str
    providers: tuple[TerraformProvider, ...]
    modules: tuple[TerraformModule, ...]
    state_management: StateManagement
    cicd_integration: CICDIntegration
    directory_structure: str
    best_practices: tuple[str, ...]
    example_code: str


class TerraformEngineer:
    """Terraform engineering skill producing IaC plans."""

    def run(self, input_data: dict) -> dict:
        """Run Terraform planning.

        Args:
            input_data: Dictionary with keys:
                - infrastructure_description: Description of infrastructure
                - project_name: Optional project name (default "terraform-project")
                - provider: Optional provider (default "aws")

        Returns:
            Dictionary with Terraform plan data.
        """
        description = input_data.get("infrastructure_description", "")
        if not description:
            return {"error": "No infrastructure description provided"}

        project_name = input_data.get("project_name", "terraform-project")
        provider_str = input_data.get("provider", "aws").lower()

        try:
            primary_provider = TerraformProvider(provider_str)
        except ValueError:
            primary_provider = TerraformProvider.AWS

        desc_lower = description.lower()

        providers = self._identify_providers(primary_provider, desc_lower)
        modules = self._design_modules(desc_lower, primary_provider)
        state = self._configure_state_management(primary_provider)
        cicd = self._design_cicd_integration()
        structure = self._define_directory_structure()
        best_practices = self._list_best_practices()
        example = self._generate_example_code(primary_provider)

        return TerraformPlan(
            project_name=project_name,
            providers=tuple(providers),
            modules=tuple(modules),
            state_management=state,
            cicd_integration=cicd,
            directory_structure=structure,
            best_practices=tuple(best_practices),
            example_code=example,
        ).__dict__ | {
            "modules": [m.__dict__ for m in modules],
            "state_management": state.__dict__,
            "cicd_integration": cicd.__dict__,
        }

    @staticmethod
    def _identify_providers(primary: TerraformProvider, description: str) -> list[TerraformProvider]:
        providers = [primary]

        if "kubernetes" in description or "k8s" in description:
            providers.append(TerraformProvider.KUBERNETES)

        if "helm" in description:
            providers.append(TerraformProvider.HELM)

        return providers

    @staticmethod
    def _design_modules(description: str, provider: TerraformProvider) -> list[TerraformModule]:
        modules: list[TerraformModule] = [
            TerraformModule(
                module_name="networking",
                purpose="VPC, subnets, routing, and security groups",
                inputs=("vpc_cidr", "availability_zones", "environment"),
                outputs=("vpc_id", "private_subnet_ids", "public_subnet_ids"),
                resources=("VPC", "Subnets", "Route Tables", "NAT Gateway", "Security Groups"),
            ),
            TerraformModule(
                module_name="compute",
                purpose="Compute resources (VMs, containers, serverless)",
                inputs=("instance_type", "ami_id", "subnet_ids", "security_group_ids"),
                outputs=("instance_ids", "private_ips", "public_ips"),
                resources=("EC2 Instances", "Auto Scaling Groups", "Launch Templates"),
            ),
            TerraformModule(
                module_name="database",
                purpose="Managed database services",
                inputs=("db_instance_class", "db_name", "subnet_ids"),
                outputs=("db_endpoint", "db_connection_string"),
                resources=("RDS Instance", "DB Subnet Group", "Parameter Group"),
            ),
            TerraformModule(
                module_name="storage",
                purpose="Object storage and file systems",
                inputs=("bucket_name", "versioning_enabled", "lifecycle_rules"),
                outputs=("bucket_id", "bucket_arn"),
                resources=("S3 Bucket", "Bucket Policy", "Lifecycle Rules"),
            ),
        ]

        if "kubernetes" in description:
            modules.append(
                TerraformModule(
                    module_name="kubernetes",
                    purpose="Kubernetes cluster and node groups",
                    inputs=("cluster_name", "kubernetes_version", "node_instance_type"),
                    outputs=("cluster_endpoint", "cluster_ca_certificate"),
                    resources=("EKS Cluster", "Node Groups", "IAM Roles"),
                )
            )

        return modules

    @staticmethod
    def _configure_state_management(provider: TerraformProvider) -> StateManagement:
        if provider == TerraformProvider.AWS:
            return StateManagement(
                backend=StateBackend.S3,
                configuration="bucket: terraform-state, key: terraform.tfstate, region: us-east-1, dynamodb_table: terraform-locks",
                locking=True,
                encryption=True,
            )
        elif provider == TerraformProvider.AZURE:
            return StateManagement(
                backend=StateBackend.AZURE_BLOB,
                configuration="storage_account_name: tfstate, container_name: tfstate, key: terraform.tfstate",
                locking=True,
                encryption=True,
            )
        elif provider == TerraformProvider.GCP:
            return StateManagement(
                backend=StateBackend.GCS,
                configuration="bucket: terraform-state, prefix: terraform/state",
                locking=True,
                encryption=True,
            )
        else:
            return StateManagement(
                backend=StateBackend.TERRAFORM_CLOUD,
                configuration="organization: my-org, workspaces: { name: my-workspace }",
                locking=True,
                encryption=True,
            )

    @staticmethod
    def _design_cicd_integration() -> CICDIntegration:
        return CICDIntegration(
            tool="GitHub Actions / GitLab CI / Jenkins",
            stages=(
                "terraform fmt -check (validate formatting)",
                "terraform validate (validate configuration)",
                "terraform plan (generate plan)",
                "Manual approval for production",
                "terraform apply (apply changes)",
            ),
            approval_gates=(
                "Require manual approval for production deployments",
                "Require code review for all Terraform changes",
                "Run security scanning (tfsec, checkov) before apply",
            ),
        )

    @staticmethod
    def _define_directory_structure() -> str:
        return """
terraform-project/
├── modules/
│   ├── networking/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   ├── database/
│   └── storage/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── production/
├── .terraform.lock.hcl
└── README.md
"""

    @staticmethod
    def _list_best_practices() -> list[str]:
        return [
            "Use remote state with locking to prevent concurrent modifications",
            "Separate environments (dev/staging/prod) into different state files",
            "Use modules for reusable infrastructure components",
            "Pin provider versions in terraform.lock.hcl",
            "Use variables and tfvars files for environment-specific configuration",
            "Enable state encryption at rest",
            "Use terraform fmt and terraform validate in CI/CD",
            "Run security scanning (tfsec, checkov) before apply",
            "Use data sources instead of hardcoding values",
            "Tag all resources for cost tracking and management",
            "Use terraform plan before apply to review changes",
            "Implement proper IAM roles with least privilege",
        ]

    @staticmethod
    def _generate_example_code(provider: TerraformProvider) -> str:
        if provider == TerraformProvider.AWS:
            return '''
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "./modules/networking"
  vpc_cidr = var.vpc_cidr
  availability_zones = var.availability_zones
  environment = var.environment
}

module "compute" {
  source = "./modules/compute"
  subnet_ids = module.networking.private_subnet_ids
  security_group_ids = [module.networking.app_security_group_id]
}
'''
        else:
            return "# Example code for selected provider (see Terraform documentation)"
