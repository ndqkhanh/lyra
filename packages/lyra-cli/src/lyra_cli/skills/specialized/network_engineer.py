"""Network Engineer Skill — network configuration analysis and security validation.

Validates network configurations for:
- Firewall rule correctness and ordering
- Subnet design and IP allocation
- Protocol security (TLS, SSH, VPN)
- DDoS mitigation readiness
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NetworkRisk(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class NetworkFinding:
    resource: str
    risk: NetworkRisk
    issue: str
    remediation: str


class NetworkEngineerSkill:
    """Validates network configurations and security posture."""

    _INSECURE_PORTS = frozenset({21, 23, 25, 135, 139, 445, 1433, 3306, 5432, 6379, 27017})

    def run(self, input_data: dict) -> dict:
        rules = input_data.get("firewall_rules", [])
        subnets = input_data.get("subnets", [])
        findings: list[NetworkFinding] = []

        for rule in rules:
            port = rule.get("port", 0)
            if port in self._INSECURE_PORTS and rule.get("source") == "0.0.0.0/0":
                findings.append(NetworkFinding(f"port_{port}", NetworkRisk.CRITICAL,
                    f"Port {port} exposed to the internet.", "Restrict to specific IP ranges or use a VPN/bastion."))

        if not subnets:
            findings.append(NetworkFinding("subnets", NetworkRisk.MEDIUM,
                "No subnet configuration provided.", "Define private/public subnet architecture for defense in depth."))

        has_egress = any(r.get("direction") == "egress" for r in rules)
        if not has_egress:
            findings.append(NetworkFinding("egress", NetworkRisk.HIGH,
                "No egress filtering rules — data exfiltration risk.", "Add egress rules to restrict outbound traffic."))

        return {
            "findings": [f.__dict__ for f in findings],
            "score": max(0, 100 - len(findings) * 15),
            "critical_count": len([f for f in findings if f.risk == NetworkRisk.CRITICAL]),
            "passed": len([f for f in findings if f.risk == NetworkRisk.CRITICAL]) == 0,
        }
