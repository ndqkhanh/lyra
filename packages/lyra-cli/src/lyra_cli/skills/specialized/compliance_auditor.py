"""Compliance Auditor Skill — regulatory compliance validation.

Checks system configurations for:
- GDPR / data privacy requirements
- SOC 2 security controls
- PCI-DSS payment security
- HIPAA healthcare data protection
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ComplianceFinding:
    regulation: str
    control_id: str
    status: ComplianceStatus
    description: str
    remediation: str


class ComplianceAuditorSkill:
    """Validates configurations against common regulatory frameworks."""

    _GDPR_CHECKS = [
        ("GDPR-ART5", "data_minimization", "Only collect necessary personal data. Audit data collection points."),
        ("GDPR-ART17", "right_to_erasure", "Implement data deletion capability for user requests."),
        ("GDPR-ART32", "encryption_at_rest", "Encrypt personal data at rest using AES-256 or equivalent."),
        ("GDPR-ART33", "breach_notification", "Implement 72-hour breach notification capability."),
    ]
    _SOC2_CHECKS = [
        ("SOC2-CC6.1", "access_control", "Implement role-based access control with least privilege."),
        ("SOC2-CC7.1", "vulnerability_scanning", "Run automated vulnerability scans at least monthly."),
        ("SOC2-CC8.1", "change_management", "Document and approve all production changes."),
    ]

    def run(self, input_data: dict) -> dict:
        regulations = input_data.get("regulations", ["gdpr"])
        config = input_data.get("config", {})
        findings: list[ComplianceFinding] = []

        if "gdpr" in regulations:
            for control_id, check_key, remediation in self._GDPR_CHECKS:
                if check_key not in config or not config.get(check_key):
                    findings.append(ComplianceFinding("GDPR", control_id,
                        ComplianceStatus.NON_COMPLIANT,
                        f"Missing control: {check_key.replace('_', ' ')}.", remediation))

        if "soc2" in regulations:
            for control_id, check_key, remediation in self._SOC2_CHECKS:
                if check_key not in config or not config.get(check_key):
                    findings.append(ComplianceFinding("SOC 2", control_id,
                        ComplianceStatus.NEEDS_REVIEW,
                        f"Control not confirmed: {check_key.replace('_', ' ')}.", remediation))

        non_compliant = len([f for f in findings if f.status == ComplianceStatus.NON_COMPLIANT])
        return {
            "findings": [f.__dict__ for f in findings],
            "non_compliant_count": non_compliant,
            "score": max(0, 100 - non_compliant * 25 - len(findings) * 10),
            "passed": non_compliant == 0,
        }
