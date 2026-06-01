"""System Designer Skill — system architecture and design patterns validation.

Analyzes system designs for:
- Architecture patterns (microservices, monolith, serverless)
- Scalability and performance considerations
- Data flow and state management
- Service boundaries and coupling
- Resilience and fault tolerance
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SystemDesignSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SystemDesignCategory(StrEnum):
    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass(frozen=True)
class SystemDesignIssue:
    category: SystemDesignCategory
    severity: SystemDesignSeverity
    component: str
    message: str
    suggestion: str


class SystemDesignerSkill:
    """Validates system architecture and design patterns."""

    def __init__(self) -> None:
        self._issues: list[SystemDesignIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run system design analysis.

        Args:
            input_data: Dictionary with keys:
                - architecture_type: Architecture pattern (microservices, monolith, etc.)
                - services: List of services/components
                - data_stores: List of data storage systems
                - communication_patterns: Service communication methods
                - scale_requirements: Expected scale (users, requests, data)

        Returns:
            Dictionary with analysis report data.
        """
        arch_type = input_data.get("architecture_type", "unknown")
        services = input_data.get("services", [])
        data_stores = input_data.get("data_stores", [])
        communication = input_data.get("communication_patterns", [])
        scale = input_data.get("scale_requirements", {})

        self._issues.clear()

        self._check_architecture_pattern(arch_type, services)
        self._check_service_boundaries(services)
        self._check_data_architecture(data_stores, services)
        self._check_communication_patterns(communication, services)
        self._check_scalability(scale, arch_type, services)
        self._check_reliability(input_data)
        self._check_security_design(input_data)

        score = self._compute_score()

        return {
            "architecture_type": arch_type,
            "services_count": len(services),
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_architecture_pattern(self, arch_type: str, services: list) -> None:
        """Check architecture pattern appropriateness."""
        service_count = len(services)

        if arch_type == "microservices" and service_count < 3:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="architecture",
                    message=f"Microservices with only {service_count} services - overhead may not be justified",
                    suggestion="Consider monolith or modular monolith for simpler systems",
                )
            )

        if arch_type == "monolith" and service_count > 10:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.HIGH,
                    component="architecture",
                    message=f"Monolith with {service_count} modules - may be too complex",
                    suggestion="Consider splitting into microservices or modular monolith",
                )
            )

        if arch_type == "unknown":
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.CRITICAL,
                    component="architecture",
                    message="Architecture pattern not defined",
                    suggestion="Define clear architecture pattern (microservices, monolith, serverless)",
                )
            )

    def _check_service_boundaries(self, services: list) -> None:
        """Check service boundaries and coupling."""
        # Check for circular dependencies
        dependencies = {}
        for service in services:
            service_name = service.get("name", "")
            deps = service.get("dependencies", [])
            dependencies[service_name] = deps

        # Simple cycle detection
        for service_name, deps in dependencies.items():
            for dep in deps:
                if dep in dependencies and service_name in dependencies[dep]:
                    self._issues.append(
                        SystemDesignIssue(
                            category=SystemDesignCategory.ARCHITECTURE,
                            severity=SystemDesignSeverity.CRITICAL,
                            component=service_name,
                            message=f"Circular dependency between {service_name} and {dep}",
                            suggestion="Refactor to remove circular dependencies",
                        )
                    )

        # Check for too many dependencies
        for service in services:
            service_name = service.get("name", "")
            deps = service.get("dependencies", [])
            if len(deps) > 5:
                self._issues.append(
                    SystemDesignIssue(
                        category=SystemDesignCategory.ARCHITECTURE,
                        severity=SystemDesignSeverity.HIGH,
                        component=service_name,
                        message=f"Service has {len(deps)} dependencies - high coupling",
                        suggestion="Reduce dependencies or introduce event-driven patterns",
                    )
                )

        # Check for shared database
        db_users = {}
        for service in services:
            service_name = service.get("name", "")
            db = service.get("database", "")
            if db:
                if db not in db_users:
                    db_users[db] = []
                db_users[db].append(service_name)

        for db, users in db_users.items():
            if len(users) > 1:
                self._issues.append(
                    SystemDesignIssue(
                        category=SystemDesignCategory.ARCHITECTURE,
                        severity=SystemDesignSeverity.HIGH,
                        component=db,
                        message=f"Database {db} shared by {len(users)} services: {', '.join(users)}",
                        suggestion="Each service should own its data - use database per service pattern",
                    )
                )

    def _check_data_architecture(self, data_stores: list, services: list) -> None:
        """Check data architecture patterns."""
        if not data_stores:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.CRITICAL,
                    component="data",
                    message="No data stores defined",
                    suggestion="Define data storage strategy",
                )
            )
            return

        # Check for appropriate data store types
        has_cache = any(ds.get("type") == "cache" for ds in data_stores)
        has_relational = any(ds.get("type") == "relational" for ds in data_stores)
        has_document = any(ds.get("type") == "document" for ds in data_stores)

        if len(services) > 3 and not has_cache:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.PERFORMANCE,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="data",
                    message="No caching layer defined",
                    suggestion="Add Redis/Memcached for frequently accessed data",
                )
            )

        # Check for backup strategy
        has_backup = any(ds.get("has_backup") for ds in data_stores)
        if not has_backup:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.RELIABILITY,
                    severity=SystemDesignSeverity.CRITICAL,
                    component="data",
                    message="No backup strategy defined",
                    suggestion="Implement automated backups for all data stores",
                )
            )

    def _check_communication_patterns(self, communication: list, services: list) -> None:
        """Check service communication patterns."""
        if not communication and len(services) > 1:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.HIGH,
                    component="communication",
                    message="No communication patterns defined",
                    suggestion="Define how services communicate (REST, gRPC, events)",
                )
            )
            return

        has_sync = any(c.get("type") in ("rest", "grpc") for c in communication)
        has_async = any(c.get("type") in ("events", "message_queue") for c in communication)

        if has_sync and not has_async and len(services) > 5:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SCALABILITY,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="communication",
                    message="Only synchronous communication - limits scalability",
                    suggestion="Add async messaging for non-critical operations",
                )
            )

        # Check for API gateway
        has_gateway = any(s.get("type") == "api_gateway" for s in services)
        if len(services) > 3 and not has_gateway:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.ARCHITECTURE,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="communication",
                    message="No API gateway for multiple services",
                    suggestion="Add API gateway for routing, auth, and rate limiting",
                )
            )

    def _check_scalability(self, scale: dict, arch_type: str, services: list) -> None:
        """Check scalability considerations."""
        expected_users = scale.get("expected_users", 0)
        expected_rps = scale.get("expected_rps", 0)

        # Check for load balancing
        has_load_balancer = any(s.get("has_load_balancer") for s in services)
        if expected_users > 10000 and not has_load_balancer:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SCALABILITY,
                    severity=SystemDesignSeverity.CRITICAL,
                    component="infrastructure",
                    message=f"Expected {expected_users} users without load balancing",
                    suggestion="Add load balancer for horizontal scaling",
                )
            )

        # Check for auto-scaling
        has_auto_scaling = scale.get("has_auto_scaling", False)
        if expected_rps > 1000 and not has_auto_scaling:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SCALABILITY,
                    severity=SystemDesignSeverity.HIGH,
                    component="infrastructure",
                    message=f"Expected {expected_rps} RPS without auto-scaling",
                    suggestion="Implement auto-scaling based on metrics",
                )
            )

        # Check for CDN
        has_cdn = scale.get("has_cdn", False)
        if expected_users > 50000 and not has_cdn:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.PERFORMANCE,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="infrastructure",
                    message="Large user base without CDN",
                    suggestion="Add CDN for static assets and global distribution",
                )
            )

    def _check_reliability(self, input_data: dict) -> None:
        """Check reliability and fault tolerance."""
        has_health_checks = input_data.get("has_health_checks", False)
        if not has_health_checks:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.RELIABILITY,
                    severity=SystemDesignSeverity.HIGH,
                    component="monitoring",
                    message="No health checks defined",
                    suggestion="Implement health check endpoints for all services",
                )
            )

        has_circuit_breaker = input_data.get("has_circuit_breaker", False)
        services = input_data.get("services", [])
        if len(services) > 2 and not has_circuit_breaker:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.RELIABILITY,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="resilience",
                    message="No circuit breaker pattern for service calls",
                    suggestion="Implement circuit breakers to prevent cascade failures",
                )
            )

        has_retry_logic = input_data.get("has_retry_logic", False)
        if not has_retry_logic:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.RELIABILITY,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="resilience",
                    message="No retry logic for transient failures",
                    suggestion="Implement exponential backoff retry for external calls",
                )
            )

    def _check_security_design(self, input_data: dict) -> None:
        """Check security architecture."""
        has_auth = input_data.get("has_authentication", False)
        if not has_auth:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SECURITY,
                    severity=SystemDesignSeverity.CRITICAL,
                    component="security",
                    message="No authentication mechanism defined",
                    suggestion="Implement authentication (OAuth2, JWT, etc.)",
                )
            )

        has_encryption = input_data.get("has_encryption", False)
        if not has_encryption:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SECURITY,
                    severity=SystemDesignSeverity.HIGH,
                    component="security",
                    message="No encryption strategy defined",
                    suggestion="Implement TLS for transit and encryption at rest",
                )
            )

        has_rate_limiting = input_data.get("has_rate_limiting", False)
        if not has_rate_limiting:
            self._issues.append(
                SystemDesignIssue(
                    category=SystemDesignCategory.SECURITY,
                    severity=SystemDesignSeverity.MEDIUM,
                    component="security",
                    message="No rate limiting defined",
                    suggestion="Implement rate limiting to prevent abuse",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall system design quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == SystemDesignSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == SystemDesignSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == SystemDesignSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == SystemDesignSeverity.LOW]) * 3,
        )
