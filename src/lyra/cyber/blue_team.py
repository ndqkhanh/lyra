"""
Blue Team Defense - Defensive security automation.

Features:
- Threat detection
- Incident response automation
- Security monitoring
- Alert triage
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ThreatSeverity(Enum):
    """Threat severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Incident response status."""

    NEW = "new"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


@dataclass
class SecurityAlert:
    """Security alert."""

    alert_id: str
    title: str
    severity: ThreatSeverity
    source: str
    timestamp: datetime
    indicators: list[str]
    description: str
    false_positive_score: float = 0.0


@dataclass
class Incident:
    """Security incident."""

    incident_id: str
    title: str
    severity: ThreatSeverity
    status: IncidentStatus
    alerts: list[SecurityAlert]
    affected_systems: list[str]
    timeline: list[dict[str, str]] = field(default_factory=list)
    containment_actions: list[str] = field(default_factory=list)


class BlueTeamDefense:
    """
    Blue team defense automation.

    Features:
    - Alert triage
    - Incident response
    - Threat detection
    """

    def __init__(self):
        """Initialize blue team defense."""
        self.alerts: dict[str, SecurityAlert] = {}
        self.incidents: dict[str, Incident] = {}

    def triage_alert(self, alert: SecurityAlert) -> dict[str, any]:
        """
        Triage security alert.

        Args:
            alert: Security alert

        Returns:
            Triage result
        """
        self.alerts[alert.alert_id] = alert

        # Calculate priority
        priority_score = self._calculate_priority(alert)

        # Check for false positive
        is_false_positive = alert.false_positive_score > 0.7

        return {
            "alert_id": alert.alert_id,
            "priority_score": priority_score,
            "is_false_positive": is_false_positive,
            "recommended_action": self._recommend_action(alert, is_false_positive),
        }

    def _calculate_priority(self, alert: SecurityAlert) -> float:
        """
        Calculate alert priority.

        Args:
            alert: Security alert

        Returns:
            Priority score (0.0-1.0)
        """
        severity_scores = {
            ThreatSeverity.LOW: 0.25,
            ThreatSeverity.MEDIUM: 0.50,
            ThreatSeverity.HIGH: 0.75,
            ThreatSeverity.CRITICAL: 1.0,
        }

        base_score = severity_scores[alert.severity]

        # Adjust for false positive likelihood
        adjusted_score = base_score * (1 - alert.false_positive_score)

        return adjusted_score

    def _recommend_action(
        self,
        alert: SecurityAlert,
        is_false_positive: bool,
    ) -> str:
        """
        Recommend action for alert.

        Args:
            alert: Security alert
            is_false_positive: Whether alert is likely false positive

        Returns:
            Recommended action
        """
        if is_false_positive:
            return "dismiss"

        if alert.severity == ThreatSeverity.CRITICAL:
            return "escalate_immediately"
        elif alert.severity == ThreatSeverity.HIGH:
            return "investigate"
        else:
            return "monitor"

    def create_incident(
        self,
        title: str,
        severity: ThreatSeverity,
        alert_ids: list[str],
    ) -> Incident:
        """
        Create security incident.

        Args:
            title: Incident title
            severity: Severity level
            alert_ids: Related alert IDs

        Returns:
            Created incident
        """
        # Gather related alerts
        alerts = [self.alerts[aid] for aid in alert_ids if aid in self.alerts]

        # Extract affected systems
        affected_systems = []
        for alert in alerts:
            for indicator in alert.indicators:
                if ":" in indicator:  # IP:port format
                    ip = indicator.split(":")[0]
                    if ip not in affected_systems:
                        affected_systems.append(ip)

        incident = Incident(
            incident_id=f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            title=title,
            severity=severity,
            status=IncidentStatus.NEW,
            alerts=alerts,
            affected_systems=affected_systems,
        )

        self.incidents[incident.incident_id] = incident
        return incident

    def respond_to_incident(
        self,
        incident_id: str,
        action: str,
    ) -> dict[str, any]:
        """
        Execute incident response action.

        Args:
            incident_id: Incident ID
            action: Response action

        Returns:
            Action result
        """
        if incident_id not in self.incidents:
            raise ValueError(f"Incident not found: {incident_id}")

        incident = self.incidents[incident_id]

        # Update status based on action
        if action == "contain":
            incident.status = IncidentStatus.CONTAINED
            incident.containment_actions.append(f"Contained at {datetime.now()}")
        elif action == "eradicate":
            incident.status = IncidentStatus.ERADICATED
        elif action == "recover":
            incident.status = IncidentStatus.RECOVERED

        # Add to timeline
        incident.timeline.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "status": incident.status.value,
            }
        )

        return {
            "incident_id": incident_id,
            "action": action,
            "new_status": incident.status.value,
            "success": True,
        }

    def get_incident_summary(self, incident_id: str) -> dict[str, any]:
        """
        Get incident summary.

        Args:
            incident_id: Incident ID

        Returns:
            Incident summary
        """
        if incident_id not in self.incidents:
            raise ValueError(f"Incident not found: {incident_id}")

        incident = self.incidents[incident_id]

        return {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "alert_count": len(incident.alerts),
            "affected_systems": incident.affected_systems,
            "timeline_events": len(incident.timeline),
        }
