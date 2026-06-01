"""Site Reliability Engineer Skill — SRE practices and operational excellence validation.

Analyzes systems for:
- Service Level Objectives (SLOs) and SLIs
- Monitoring and observability
- Incident response procedures
- Capacity planning
- Automation and toil reduction
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SRESeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SRECategory(StrEnum):
    RELIABILITY = "reliability"
    MONITORING = "monitoring"
    AUTOMATION = "automation"
    CAPACITY = "capacity"
    INCIDENT_RESPONSE = "incident_response"


@dataclass(frozen=True)
class SREIssue:
    category: SRECategory
    severity: SRESeverity
    component: str
    message: str
    suggestion: str


class SiteReliabilitySkill:
    """Validates SRE practices and operational excellence."""

    def __init__(self) -> None:
        self._issues: list[SREIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run SRE practices analysis.

        Args:
            input_data: Dictionary with keys:
                - services: List of services to evaluate
                - slos: Service Level Objectives configuration
                - monitoring: Monitoring setup
                - runbooks: Runbook availability
                - automation_level: Percentage of automated operations

        Returns:
            Dictionary with analysis report data.
        """
        services = input_data.get("services", [])
        slos = input_data.get("slos", {})
        monitoring = input_data.get("monitoring", {})
        runbooks = input_data.get("runbooks", {})
        automation_level = input_data.get("automation_level", 0)

        self._issues.clear()

        self._check_slos_and_slis(services, slos)
        self._check_monitoring(services, monitoring)
        self._check_alerting(monitoring)
        self._check_incident_response(runbooks, services)
        self._check_automation(automation_level, services, input_data)
        self._check_error_budgets(slos)

        score = self._compute_score()

        return {
            "services_count": len(services),
            "automation_level": automation_level,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_slos_and_slis(self, services: list, slos: dict) -> None:
        """Check Service Level Objectives and Indicators."""
        if not slos:
            self._issues.append(
                SREIssue(
                    category=SRECategory.RELIABILITY,
                    severity=SRESeverity.CRITICAL,
                    component="slos",
                    message="No SLOs defined for any service",
                    suggestion="Define SLOs for availability, latency, and error rate",
                )
            )
            return

        # Check if all critical services have SLOs
        critical_services = [s for s in services if s.get("criticality") == "critical"]
        services_with_slos = slos.get("services", [])

        missing_slos = [
            s.get("name") for s in critical_services if s.get("name") not in services_with_slos
        ]

        if missing_slos:
            self._issues.append(
                SREIssue(
                    category=SRECategory.RELIABILITY,
                    severity=SRESeverity.HIGH,
                    component="slos",
                    message=f"Critical services without SLOs: {', '.join(missing_slos)}",
                    suggestion="Define SLOs for all critical services",
                )
            )

        # Check SLO targets
        for service_name, slo_config in slos.items():
            if isinstance(slo_config, dict):
                availability_target = slo_config.get("availability_target", 0)
                if availability_target < 99.0:
                    self._issues.append(
                        SREIssue(
                            category=SRECategory.RELIABILITY,
                            severity=SRESeverity.MEDIUM,
                            component=service_name,
                            message=f"Low availability target ({availability_target}%)",
                            suggestion="Consider 99.9% (three nines) for production services",
                        )
                    )

                # Check if SLIs are defined
                has_slis = slo_config.get("has_slis", False)
                if not has_slis:
                    self._issues.append(
                        SREIssue(
                            category=SRECategory.RELIABILITY,
                            severity=SRESeverity.HIGH,
                            component=service_name,
                            message="SLO defined without SLIs",
                            suggestion="Define SLIs (metrics) to measure SLO compliance",
                        )
                    )

    def _check_monitoring(self, services: list, monitoring: dict) -> None:
        """Check monitoring and observability setup."""
        if not monitoring:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.CRITICAL,
                    component="monitoring",
                    message="No monitoring system configured",
                    suggestion="Implement monitoring with Prometheus, Datadog, or similar",
                )
            )
            return

        # Check the four golden signals
        golden_signals = ["latency", "traffic", "errors", "saturation"]
        monitored_signals = monitoring.get("golden_signals", [])

        missing_signals = [s for s in golden_signals if s not in monitored_signals]
        if missing_signals:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.HIGH,
                    component="monitoring",
                    message=f"Missing golden signals: {', '.join(missing_signals)}",
                    suggestion="Monitor all four golden signals: latency, traffic, errors, saturation",
                )
            )

        # Check distributed tracing
        has_tracing = monitoring.get("has_distributed_tracing", False)
        if len(services) > 3 and not has_tracing:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.MEDIUM,
                    component="monitoring",
                    message="No distributed tracing for microservices",
                    suggestion="Implement distributed tracing (Jaeger, Zipkin, OpenTelemetry)",
                )
            )

        # Check log aggregation
        has_log_aggregation = monitoring.get("has_log_aggregation", False)
        if not has_log_aggregation:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.HIGH,
                    component="monitoring",
                    message="No centralized log aggregation",
                    suggestion="Implement log aggregation (ELK, Loki, CloudWatch)",
                )
            )

        # Check metrics retention
        metrics_retention_days = monitoring.get("metrics_retention_days", 0)
        if metrics_retention_days < 30:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.MEDIUM,
                    component="monitoring",
                    message=f"Short metrics retention ({metrics_retention_days} days)",
                    suggestion="Retain metrics for at least 30 days for trend analysis",
                )
            )

    def _check_alerting(self, monitoring: dict) -> None:
        """Check alerting configuration."""
        has_alerts = monitoring.get("has_alerts", False)
        if not has_alerts:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.CRITICAL,
                    component="alerting",
                    message="No alerts configured",
                    suggestion="Configure alerts for SLO violations and critical errors",
                )
            )
            return

        # Check alert routing
        has_on_call = monitoring.get("has_on_call_rotation", False)
        if not has_on_call:
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.HIGH,
                    component="alerting",
                    message="No on-call rotation defined",
                    suggestion="Establish on-call rotation with PagerDuty or similar",
                )
            )

        # Check alert fatigue
        alert_volume = monitoring.get("alerts_per_day", 0)
        if alert_volume > 50:
            self._issues.append(
                SREIssue(
                    category=SRECategory.MONITORING,
                    severity=SRESeverity.HIGH,
                    component="alerting",
                    message=f"High alert volume ({alert_volume}/day) - alert fatigue risk",
                    suggestion="Reduce noise by tuning thresholds and using alert aggregation",
                )
            )

        # Check alert actionability
        has_runbook_links = monitoring.get("alerts_have_runbook_links", False)
        if not has_runbook_links:
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.MEDIUM,
                    component="alerting",
                    message="Alerts don't link to runbooks",
                    suggestion="Add runbook links to all alerts for faster response",
                )
            )

    def _check_incident_response(self, runbooks: dict, services: list) -> None:
        """Check incident response readiness."""
        if not runbooks:
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.CRITICAL,
                    component="runbooks",
                    message="No runbooks available",
                    suggestion="Create runbooks for common incidents and maintenance tasks",
                )
            )
            return

        # Check runbook coverage
        runbook_count = runbooks.get("count", 0)
        if runbook_count < len(services):
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.HIGH,
                    component="runbooks",
                    message=f"Only {runbook_count} runbooks for {len(services)} services",
                    suggestion="Create at least one runbook per service",
                )
            )

        # Check incident response plan
        has_incident_plan = runbooks.get("has_incident_response_plan", False)
        if not has_incident_plan:
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.HIGH,
                    component="incident_response",
                    message="No incident response plan documented",
                    suggestion="Document incident response process and roles",
                )
            )

        # Check postmortem process
        has_postmortem_process = runbooks.get("has_postmortem_process", False)
        if not has_postmortem_process:
            self._issues.append(
                SREIssue(
                    category=SRECategory.INCIDENT_RESPONSE,
                    severity=SRESeverity.MEDIUM,
                    component="incident_response",
                    message="No postmortem process defined",
                    suggestion="Establish blameless postmortem process for learning",
                )
            )

    def _check_automation(self, automation_level: int, services: list, input_data: dict) -> None:
        """Check automation and toil reduction."""
        if automation_level < 50:
            self._issues.append(
                SREIssue(
                    category=SRECategory.AUTOMATION,
                    severity=SRESeverity.HIGH,
                    component="automation",
                    message=f"Low automation level ({automation_level}%)",
                    suggestion="Automate repetitive tasks - target 70%+ automation",
                )
            )

        # Check deployment automation
        has_ci_cd = input_data.get("has_ci_cd", False)
        if not has_ci_cd:
            self._issues.append(
                SREIssue(
                    category=SRECategory.AUTOMATION,
                    severity=SRESeverity.CRITICAL,
                    component="deployment",
                    message="No CI/CD pipeline",
                    suggestion="Implement automated deployment pipeline",
                )
            )

        # Check infrastructure as code
        has_iac = input_data.get("has_infrastructure_as_code", False)
        if not has_iac:
            self._issues.append(
                SREIssue(
                    category=SRECategory.AUTOMATION,
                    severity=SRESeverity.HIGH,
                    component="infrastructure",
                    message="No infrastructure as code",
                    suggestion="Manage infrastructure with Terraform, CloudFormation, or similar",
                )
            )

        # Check automated rollback
        has_auto_rollback = input_data.get("has_automated_rollback", False)
        if not has_auto_rollback:
            self._issues.append(
                SREIssue(
                    category=SRECategory.AUTOMATION,
                    severity=SRESeverity.MEDIUM,
                    component="deployment",
                    message="No automated rollback on deployment failure",
                    suggestion="Implement automated rollback for failed deployments",
                )
            )

    def _check_error_budgets(self, slos: dict) -> None:
        """Check error budget tracking."""
        has_error_budget = slos.get("has_error_budget_tracking", False)
        if not has_error_budget and slos:
            self._issues.append(
                SREIssue(
                    category=SRECategory.RELIABILITY,
                    severity=SRESeverity.MEDIUM,
                    component="error_budget",
                    message="No error budget tracking",
                    suggestion="Track error budgets to balance reliability and velocity",
                )
            )

        # Check error budget policy
        has_policy = slos.get("has_error_budget_policy", False)
        if not has_policy and slos:
            self._issues.append(
                SREIssue(
                    category=SRECategory.RELIABILITY,
                    severity=SRESeverity.LOW,
                    component="error_budget",
                    message="No error budget policy defined",
                    suggestion="Define policy for when error budget is exhausted",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall SRE maturity score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == SRESeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == SRESeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == SRESeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == SRESeverity.LOW]) * 3,
        )
