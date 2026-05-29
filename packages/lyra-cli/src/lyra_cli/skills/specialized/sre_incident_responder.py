"""
SRE Incident Responder Skill - Structured incident response analysis.

Analyzes incident descriptions to produce:
- Severity assessment (SEV1-SEV5)
- Impact analysis
- Recommended runbooks
- Escalation paths
- Post-mortem templates

Outputs structured incident response plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IncidentSeverity(StrEnum):
    """Incident severity levels aligned with standard SRE practice."""

    SEV1 = "SEV1"  # Critical production outage
    SEV2 = "SEV2"  # Major feature degradation
    SEV3 = "SEV3"  # Minor feature degradation
    SEV4 = "SEV4"  # Non-critical issue
    SEV5 = "SEV5"  # Cosmetic / low impact


class ServiceCategory(StrEnum):
    """Categories of affected services."""

    DATABASE = "database"
    NETWORK = "network"
    COMPUTE = "compute"
    STORAGE = "storage"
    AUTH = "authentication"
    API = "api"
    CACHE = "cache"
    MESSAGING = "messaging"
    CDN = "cdn"
    DNS = "dns"
    OTHER = "other"


@dataclass(frozen=True)
class ImpactScope:
    """Scope and scale of incident impact."""

    affected_services: tuple[str, ...]
    affected_users_percentage: str
    geographic_scope: str
    revenue_impact: str
    data_integrity_risk: bool


@dataclass(frozen=True)
class RunbookStep:
    """A single step in an incident response runbook."""

    step_number: int
    action: str
    expected_outcome: str
    estimated_duration: str
    rollback_command: str | None = None


@dataclass(frozen=True)
class Runbook:
    """Complete runbook for this incident type."""

    name: str
    description: str
    steps: tuple[RunbookStep, ...]
    prerequisites: tuple[str, ...]
    owner_team: str


@dataclass(frozen=True)
class EscalationEntry:
    """An escalation contact or team."""

    level: int
    team: str
    contact_channel: str
    response_sla: str
    after_hours_contact: str | None = None


@dataclass(frozen=True)
class PostMortemTemplate:
    """Template for post-incident review document."""

    incident_id: str
    severity: IncidentSeverity
    duration: str
    root_cause_section: str
    timeline_section: str
    action_items_section: str
    lessons_learned_section: str
    follow_up_owner: str


@dataclass(frozen=True)
class IncidentResponsePlan:
    """Complete incident response plan."""

    incident_title: str
    severity: IncidentSeverity
    description: str
    impact: ImpactScope
    runbook: Runbook
    escalation_path: tuple[EscalationEntry, ...]
    post_mortem_template: PostMortemTemplate
    tags: tuple[str, ...]


# ---------------------------------------------------------------------------
# Severity patterns: keywords that hint at the incident severity level
# ---------------------------------------------------------------------------
_SEVERITY_KEYWORDS: dict[IncidentSeverity, list[str]] = {
    IncidentSeverity.SEV1: [
        "down",
        "outage",
        "data loss",
        "security breach",
        "p0",
        "critical",
        "complete failure",
        "all users",
        "production down",
    ],
    IncidentSeverity.SEV2: [
        "degraded",
        "slow",
        "high error",
        "p1",
        "major",
        "partial outage",
        "feature broken",
        "increased latency",
    ],
    IncidentSeverity.SEV3: [
        "minor",
        "p2",
        "non-critical",
        "single user",
        "cosmetic",
        "unable to access",
        "intermittent",
    ],
    IncidentSeverity.SEV4: [
        "p3",
        "low priority",
        "enhancement",
        "documentation",
    ],
    IncidentSeverity.SEV5: [
        "p4",
        "trivial",
        "cosmetic",
        "typo",
        "visual",
    ],
}


class SREIncidentResponder:
    """SRE incident response skill producing structured response plans."""

    def __init__(self) -> None:
        self._affected_services: list[str] = []
        self._keywords_found: list[str] = []

    def run(self, input_data: dict) -> dict:
        """Run incident response analysis.

        Args:
            input_data: Dictionary with keys:
                - incident_description: Free-text incident description
                - incident_title: Optional title (default auto-generated)
                - environment: Optional environment name (default "production")

        Returns:
            Dictionary with incident response plan data.
        """
        description = input_data.get("incident_description", "")
        if not description:
            return {"error": "No incident description provided"}

        title = input_data.get("incident_title", self._extract_title(description))
        environment = input_data.get("environment", "production")

        severity = self._assess_severity(description)
        self._affected_services = self._identify_services(description)
        impact = self._assess_impact(description, severity, environment)
        runbook = self._generate_runbook(severity, environment)
        escalation = self._build_escalation_path(severity, environment)
        tags = self._extract_tags(description, severity)
        postmortem = self._build_post_mortem(title, severity, description)

        return IncidentResponsePlan(
            incident_title=title,
            severity=severity,
            description=description,
            impact=impact,
            runbook=runbook,
            escalation_path=tuple(escalation),
            post_mortem_template=postmortem,
            tags=tuple(tags),
        ).__dict__ | {
            "impact": impact.__dict__,
            "runbook": self._serialize_runbook(runbook),
            "escalation_path": [e.__dict__ for e in escalation],
            "post_mortem_template": postmortem.__dict__,
        }

    @staticmethod
    def _serialize_runbook(runbook: Runbook) -> dict:
        return {
            "name": runbook.name,
            "description": runbook.description,
            "steps": [s.__dict__ for s in runbook.steps],
            "prerequisites": list(runbook.prerequisites),
            "owner_team": runbook.owner_team,
        }

    @staticmethod
    def _extract_title(description: str) -> str:
        words = description.split()[:8]
        return " ".join(words).rstrip(".,!?;:") + ("..." if len(words) == 8 else "")

    def _assess_severity(self, description: str) -> IncidentSeverity:
        desc_lower = description.lower()
        self._keywords_found.clear()

        for _severity, keywords in _SEVERITY_KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    self._keywords_found.append(kw)

        for severity in (
            IncidentSeverity.SEV1,
            IncidentSeverity.SEV2,
            IncidentSeverity.SEV3,
            IncidentSeverity.SEV4,
            IncidentSeverity.SEV5,
        ):
            for kw in _SEVERITY_KEYWORDS[severity]:
                if kw in desc_lower:
                    return severity

        # Default to SEV3 if no keywords match
        return IncidentSeverity.SEV3

    def _identify_services(self, description: str) -> list[str]:
        desc_lower = description.lower()
        service_map: dict[str, ServiceCategory] = {
            "database": ServiceCategory.DATABASE,
            "db": ServiceCategory.DATABASE,
            "postgres": ServiceCategory.DATABASE,
            "mysql": ServiceCategory.DATABASE,
            "redis": ServiceCategory.CACHE,
            "cache": ServiceCategory.CACHE,
            "api": ServiceCategory.API,
            "gateway": ServiceCategory.API,
            "auth": ServiceCategory.AUTH,
            "login": ServiceCategory.AUTH,
            "authentication": ServiceCategory.AUTH,
            "network": ServiceCategory.NETWORK,
            "load balancer": ServiceCategory.NETWORK,
            "storage": ServiceCategory.STORAGE,
            "s3": ServiceCategory.STORAGE,
            "disk": ServiceCategory.STORAGE,
            "queue": ServiceCategory.MESSAGING,
            "kafka": ServiceCategory.MESSAGING,
            "rabbitmq": ServiceCategory.MESSAGING,
            "dns": ServiceCategory.DNS,
            "cdn": ServiceCategory.CDN,
            "compute": ServiceCategory.COMPUTE,
            "kubernetes": ServiceCategory.COMPUTE,
            "pod": ServiceCategory.COMPUTE,
            "worker": ServiceCategory.COMPUTE,
        }

        found: list[str] = []
        for service_name in service_map:
            if service_name in desc_lower and service_name not in found:
                found.append(service_name)
        return found or ["unknown/unspecified"]

    def _assess_impact(
        self, description: str, severity: IncidentSeverity, environment: str
    ) -> ImpactScope:
        desc_lower = description.lower()

        data_risk = any(
            kw in desc_lower for kw in ["data loss", "corruption", "integrity", "rollback"]
        )

        if severity == IncidentSeverity.SEV1:
            user_pct = "100%"
            geo = "Global"
            revenue = "Critical revenue impact"
        elif severity == IncidentSeverity.SEV2:
            user_pct = "25-75%"
            geo = "Regional"
            revenue = "Moderate revenue impact"
        elif severity == IncidentSeverity.SEV3:
            user_pct = "5-25%"
            geo = "Single region"
            revenue = "Low revenue impact"
        else:
            user_pct = "<5%"
            geo = "Limited scope"
            revenue = "Minimal or no revenue impact"

        return ImpactScope(
            affected_services=tuple(self._affected_services),
            affected_users_percentage=user_pct,
            geographic_scope=geo,
            revenue_impact=revenue,
            data_integrity_risk=data_risk,
        )

    def _generate_runbook(self, severity: IncidentSeverity, environment: str) -> Runbook:
        common_steps: list[RunbookStep] = [
            RunbookStep(
                step_number=1,
                action=f"Acknowledge incident in {environment} with severity {severity.value}",
                expected_outcome="Incident acknowledged and assigned",
                estimated_duration="5 min",
            ),
            RunbookStep(
                step_number=2,
                action="Assess current impact: check dashboards, logs, and alerts",
                expected_outcome="Impact scope determined",
                estimated_duration="10 min",
            ),
            RunbookStep(
                step_number=3,
                action="Identify affected services and notify stakeholders",
                expected_outcome="Stakeholders informed",
                estimated_duration="10 min",
                rollback_command="N/A",
            ),
        ]

        severity_steps: list[RunbookStep] = []
        if severity in (IncidentSeverity.SEV1, IncidentSeverity.SEV2):
            severity_steps = [
                RunbookStep(
                    step_number=4,
                    action="Declare incident in incident management system",
                    expected_outcome="Incident declared with severity level",
                    estimated_duration="5 min",
                ),
                RunbookStep(
                    step_number=5,
                    action="Engage on-call rotation and form response team",
                    expected_outcome="Response team assembled",
                    estimated_duration="10 min",
                ),
                RunbookStep(
                    step_number=6,
                    action=(
                        "Attempt mitigation: rollback, scale out, or failover "
                        f"{self._affected_services[0] if self._affected_services else 'affected services'}"  # noqa: E501
                    ),
                    expected_outcome="Mitigation in progress",
                    estimated_duration="30 min",
                ),
                RunbookStep(
                    step_number=7,
                    action="Verify system recovery and monitor for 15 min",
                    expected_outcome="System stable",
                    estimated_duration="15 min",
                ),
                RunbookStep(
                    step_number=8,
                    action="Resolve incident and document timeline",
                    expected_outcome="Incident resolved, timeline recorded",
                    estimated_duration="15 min",
                ),
            ]
            prerequisites = (
                "Runbook access",
                "On-call roster",
                "VPN access",
                f"{environment} dashboard access",
            )
            owner = "SRE Team (on-call)"
        else:
            severity_steps = [
                RunbookStep(
                    step_number=4,
                    action="Open ticket in issue tracker with severity classification",
                    expected_outcome="Ticket created",
                    estimated_duration="10 min",
                ),
                RunbookStep(
                    step_number=5,
                    action="Assign to appropriate team for investigation",
                    expected_outcome="Team assigned",
                    estimated_duration="10 min",
                ),
                RunbookStep(
                    step_number=6,
                    action="Implement fix and deploy to environment",
                    expected_outcome="Fix deployed",
                    estimated_duration="60 min",
                ),
            ]
            prerequisites = ("Issue tracker access", "Deployment pipeline access")
            owner = "Engineering Team"

        all_steps = common_steps + severity_steps
        return Runbook(
            name=f"{severity.value} Incident Response - {environment}",
            description=f"Standard runbook for {severity.value} incidents in {environment}",
            steps=tuple(all_steps),
            prerequisites=tuple(prerequisites),
            owner_team=owner,
        )

    def _build_escalation_path(
        self, severity: IncidentSeverity, environment: str
    ) -> list[EscalationEntry]:
        base_path: list[EscalationEntry] = [
            EscalationEntry(
                level=1,
                team="On-call SRE",
                contact_channel="PagerDuty / OpsGenie",
                response_sla="5 min" if severity == IncidentSeverity.SEV1 else "15 min",
                after_hours_contact="On-call rotation",
            ),
        ]

        if severity in (IncidentSeverity.SEV1, IncidentSeverity.SEV2):
            base_path.extend(
                [
                    EscalationEntry(
                        level=2,
                        team="SRE Lead",
                        contact_channel="Slack / Phone",
                        response_sla="15 min",
                        after_hours_contact="On-call escalation",
                    ),
                    EscalationEntry(
                        level=3,
                        team="Engineering Manager",
                        contact_channel="Phone",
                        response_sla="30 min",
                    ),
                    EscalationEntry(
                        level=4,
                        team="VP of Engineering / CTO",
                        contact_channel="Emergency bridge",
                        response_sla="60 min",
                    ),
                ]
            )
        else:
            base_path.append(
                EscalationEntry(
                    level=2,
                    team="Engineering Team Lead",
                    contact_channel="Slack",
                    response_sla="1 hour",
                ),
            )

        return base_path

    @staticmethod
    def _build_post_mortem(
        title: str, severity: IncidentSeverity, description: str
    ) -> PostMortemTemplate:
        return PostMortemTemplate(
            incident_id=f"INC-{hash(title) % 10**6:06d}",
            severity=severity,
            duration="TBD (update after resolution)",
            root_cause_section=(
                "## Root Cause Analysis\n\n"
                "1. **Trigger**: What caused the incident?\n"
                "2. **Contributing Factors**: What conditions enabled it?\n"
                "3. **5 Whys Analysis**:\n"
                "   - Why?\n"
                "   - Why?\n"
                "   - Why?\n"
                "   - Why?\n"
                "   - Why?\n"
                "4. **Detection**: How was this discovered?\n"
            ),
            timeline_section=(
                "## Incident Timeline\n\n"
                "| Time (UTC) | Event |\n"
                "|------------|-------|\n"
                "| T-00:00 | Incident detected |\n"
                "| T+00:05 | Incident acknowledged |\n"
                "| T+00:15 | Impact assessed |\n"
                "| T+01:00 | Mitigation applied |\n"
                "| T+01:30 | System verified stable |\n"
                "| T+02:00 | Incident resolved |\n"
            ),
            action_items_section=(
                "## Action Items\n\n"
                "| Priority | Action | Owner | Due |\n"
                "|----------|--------|-------|-----|\n"
                "| P0 | | | |\n"
                "| P1 | | | |\n"
                "| P2 | | | |\n"
            ),
            lessons_learned_section=(
                "## Lessons Learned\n\n"
                "### What went well\n"
                "- \n\n"
                "### What went wrong\n"
                "- \n\n"
                "### What can be improved\n"
                "- \n"
            ),
            follow_up_owner="SRE Team",
        )

    @staticmethod
    def _extract_tags(description: str, severity: IncidentSeverity) -> list[str]:
        tags = [severity.value.lower()]
        desc_lower = description.lower()

        tag_map = [
            ("production", "production"),
            ("staging", "staging"),
            ("database", "database"),
            ("network", "network"),
            ("security", "security"),
            ("performance", "performance"),
            ("deployment", "deployment"),
            ("config", "configuration"),
        ]

        for keyword, tag in tag_map:
            if keyword in desc_lower:
                tags.append(tag)

        return tags
