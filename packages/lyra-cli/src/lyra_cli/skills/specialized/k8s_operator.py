"""
Kubernetes Operator Skill - K8s cluster management and operations.

Given requirements, produces:
- Kubernetes resource manifests
- Deployment strategies
- Monitoring and observability setup
- Security best practices
- Scaling and performance tuning

Outputs structured K8s operational plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class K8sResource(StrEnum):
    """Kubernetes resource types."""

    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    SERVICE = "Service"
    INGRESS = "Ingress"
    CONFIGMAP = "ConfigMap"
    SECRET = "Secret"
    PVC = "PersistentVolumeClaim"
    HPA = "HorizontalPodAutoscaler"


class DeploymentStrategy(StrEnum):
    """Deployment strategies."""

    ROLLING_UPDATE = "rolling_update"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


@dataclass(frozen=True)
class K8sResourceSpec:
    """Kubernetes resource specification."""

    resource_type: K8sResource
    name: str
    purpose: str
    configuration: str
    best_practices: tuple[str, ...]


@dataclass(frozen=True)
class MonitoringSetup:
    """Monitoring and observability setup."""

    tool: str
    metrics: tuple[str, ...]
    alerts: tuple[str, ...]
    dashboards: tuple[str, ...]


@dataclass(frozen=True)
class SecurityControl:
    """Kubernetes security control."""

    control_name: str
    implementation: str
    rationale: str


@dataclass(frozen=True)
class K8sOperationalPlan:
    """Complete Kubernetes operational plan."""

    cluster_name: str
    resources: tuple[K8sResourceSpec, ...]
    deployment_strategy: DeploymentStrategy
    monitoring: MonitoringSetup
    security_controls: tuple[SecurityControl, ...]
    scaling_strategy: str
    backup_strategy: str
    operational_runbook: tuple[str, ...]


class K8sOperator:
    """Kubernetes operator skill producing operational plans."""

    def run(self, input_data: dict) -> dict:
        """Run K8s operational planning.

        Args:
            input_data: Dictionary with keys:
                - application_description: Description of the application
                - cluster_name: Optional cluster name (default "k8s-cluster")
                - deployment_strategy: Optional strategy (default "rolling_update")

        Returns:
            Dictionary with K8s operational plan data.
        """
        description = input_data.get("application_description", "")
        if not description:
            return {"error": "No application description provided"}

        cluster_name = input_data.get("cluster_name", "k8s-cluster")
        strategy_str = input_data.get("deployment_strategy", "rolling_update").lower()

        try:
            strategy = DeploymentStrategy(strategy_str)
        except ValueError:
            strategy = DeploymentStrategy.ROLLING_UPDATE

        desc_lower = description.lower()

        resources = self._define_resources(desc_lower, cluster_name)
        monitoring = self._setup_monitoring()
        security = self._define_security_controls()
        scaling = self._define_scaling_strategy(desc_lower)
        backup = self._define_backup_strategy()
        runbook = self._create_runbook()

        return K8sOperationalPlan(
            cluster_name=cluster_name,
            resources=tuple(resources),
            deployment_strategy=strategy,
            monitoring=monitoring,
            security_controls=tuple(security),
            scaling_strategy=scaling,
            backup_strategy=backup,
            operational_runbook=tuple(runbook),
        ).__dict__ | {
            "resources": [r.__dict__ for r in resources],
            "monitoring": monitoring.__dict__,
            "security_controls": [s.__dict__ for s in security],
        }

    @staticmethod
    def _define_resources(description: str, cluster: str) -> list[K8sResourceSpec]:
        resources: list[K8sResourceSpec] = [
            K8sResourceSpec(
                resource_type=K8sResource.DEPLOYMENT,
                name=f"{cluster}-app",
                purpose="Application deployment with rolling updates",
                configuration="replicas: 3, strategy: RollingUpdate, maxSurge: 1, maxUnavailable: 0",
                best_practices=(
                    "Set resource requests and limits",
                    "Use readiness and liveness probes",
                    "Implement graceful shutdown",
                ),
            ),
            K8sResourceSpec(
                resource_type=K8sResource.SERVICE,
                name=f"{cluster}-app-svc",
                purpose="Internal service for pod discovery",
                configuration="type: ClusterIP, port: 80, targetPort: 8080",
                best_practices=(
                    "Use headless service for StatefulSets",
                    "Set sessionAffinity if needed",
                ),
            ),
            K8sResourceSpec(
                resource_type=K8sResource.INGRESS,
                name=f"{cluster}-ingress",
                purpose="External access with TLS termination",
                configuration="ingressClassName: nginx, TLS enabled, path-based routing",
                best_practices=(
                    "Use cert-manager for automatic TLS",
                    "Configure rate limiting",
                    "Enable CORS if needed",
                ),
            ),
            K8sResourceSpec(
                resource_type=K8sResource.CONFIGMAP,
                name=f"{cluster}-config",
                purpose="Application configuration",
                configuration="Environment-specific settings as key-value pairs",
                best_practices=(
                    "Separate config per environment",
                    "Use immutable ConfigMaps for production",
                ),
            ),
            K8sResourceSpec(
                resource_type=K8sResource.SECRET,
                name=f"{cluster}-secrets",
                purpose="Sensitive data storage",
                configuration="Opaque type, base64 encoded values",
                best_practices=(
                    "Use external secret management (Vault, Sealed Secrets)",
                    "Enable encryption at rest",
                    "Rotate secrets regularly",
                ),
            ),
            K8sResourceSpec(
                resource_type=K8sResource.HPA,
                name=f"{cluster}-hpa",
                purpose="Horizontal pod autoscaling",
                configuration="minReplicas: 3, maxReplicas: 10, targetCPU: 70%",
                best_practices=(
                    "Use custom metrics for better scaling decisions",
                    "Set appropriate scale-up/down policies",
                ),
            ),
        ]

        if "stateful" in description or "database" in description:
            resources.append(
                K8sResourceSpec(
                    resource_type=K8sResource.STATEFULSET,
                    name=f"{cluster}-stateful",
                    purpose="Stateful application with persistent storage",
                    configuration="replicas: 3, volumeClaimTemplates, podManagementPolicy: OrderedReady",
                    best_practices=(
                        "Use StatefulSet for databases and caches",
                        "Configure PodDisruptionBudget",
                        "Implement backup and restore procedures",
                    ),
                )
            )

        return resources

    @staticmethod
    def _setup_monitoring() -> MonitoringSetup:
        return MonitoringSetup(
            tool="Prometheus + Grafana",
            metrics=(
                "CPU and memory usage per pod",
                "Request rate and latency (p50, p95, p99)",
                "Error rate and HTTP status codes",
                "Pod restart count",
                "Network I/O",
            ),
            alerts=(
                "Pod crash loop (restarts > 5 in 10 minutes)",
                "High CPU usage (> 80% for 5 minutes)",
                "High memory usage (> 90% for 5 minutes)",
                "High error rate (> 5% for 5 minutes)",
                "Pod not ready (> 5 minutes)",
            ),
            dashboards=(
                "Cluster overview (nodes, pods, resources)",
                "Application metrics (requests, latency, errors)",
                "Resource utilization (CPU, memory, disk, network)",
            ),
        )

    @staticmethod
    def _define_security_controls() -> list[SecurityControl]:
        return [
            SecurityControl(
                control_name="Network Policies",
                implementation="Restrict pod-to-pod communication with NetworkPolicy resources",
                rationale="Implement zero-trust networking within the cluster",
            ),
            SecurityControl(
                control_name="Pod Security Standards",
                implementation="Enforce restricted Pod Security Standards cluster-wide",
                rationale="Prevent privileged containers and host access",
            ),
            SecurityControl(
                control_name="RBAC",
                implementation="Role-based access control with least privilege",
                rationale="Limit user and service account permissions",
            ),
            SecurityControl(
                control_name="Image Scanning",
                implementation="Scan container images for vulnerabilities (Trivy, Clair)",
                rationale="Prevent deployment of vulnerable images",
            ),
            SecurityControl(
                control_name="Secrets Management",
                implementation="Use external secrets operator (Vault, AWS Secrets Manager)",
                rationale="Avoid storing secrets in etcd",
            ),
        ]

    @staticmethod
    def _define_scaling_strategy(description: str) -> str:
        if "high traffic" in description or "variable load" in description:
            return (
                "Horizontal Pod Autoscaler (HPA) based on CPU/memory + custom metrics. "
                "Cluster Autoscaler for node scaling. "
                "Vertical Pod Autoscaler (VPA) for right-sizing."
            )
        return (
            "Horizontal Pod Autoscaler (HPA) based on CPU utilization (target: 70%). "
            "Manual cluster scaling or Cluster Autoscaler for node management."
        )

    @staticmethod
    def _define_backup_strategy() -> str:
        return (
            "Velero for cluster backup and disaster recovery. "
            "Daily backups of etcd and persistent volumes. "
            "Retention: 30 days. "
            "Test restore procedures monthly."
        )

    @staticmethod
    def _create_runbook() -> list[str]:
        return [
            "Pod crash loop: Check logs with kubectl logs, inspect events, verify resource limits",
            "High CPU/memory: Scale horizontally with HPA, or vertically with VPA",
            "Service unavailable: Check service endpoints, verify pod readiness, inspect ingress",
            "Persistent volume issues: Check PVC status, verify storage class, inspect node capacity",
            "Node not ready: Drain node, inspect node logs, check kubelet status",
            "Certificate expiration: Renew certificates with cert-manager or kubeadm",
            "Cluster upgrade: Drain nodes one by one, upgrade control plane, upgrade worker nodes",
        ]
