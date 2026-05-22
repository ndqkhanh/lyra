"""Cybersecurity Agent — threat hunting, vulnerability assessment, incident response."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["ThreatLevel", "Vulnerability", "ThreatIntel", "CyberSecurityAgent"]

class ThreatLevel(Enum):
    CRITICAL = auto(); HIGH = auto(); MEDIUM = auto(); LOW = auto()

@dataclass
class Vulnerability:
    cve: str; severity: ThreatLevel; description: str; affected_component: str = ""

@dataclass
class ThreatIntel:
    source: str; indicator: str; confidence: float; last_seen: float = 0.0

class CyberSecurityAgent:
    def __init__(self):
        self.vulnerabilities: list[Vulnerability] = []
        self.threats: list[ThreatIntel] = []
        self.incidents: list[dict] = []

    def register_vulnerability(self, cve: str, severity: str, description: str) -> Vulnerability:
        level = ThreatLevel[severity.upper()] if severity.upper() in ThreatLevel.__members__ else ThreatLevel.MEDIUM
        vuln = Vulnerability(cve=cve, severity=level, description=description)
        self.vulnerabilities.append(vuln)
        return vuln

    def add_threat_intel(self, source: str, indicator: str, confidence: float) -> ThreatIntel:
        intel = ThreatIntel(source=source, indicator=indicator, confidence=confidence, last_seen=time.time())
        self.threats.append(intel)
        return intel

    def scan(self, target: str) -> list[dict]:
        findings = [{"target": target, "vulns_found": len(self.vulnerabilities), "threats_crossed": sum(1 for t in self.threats if t.confidence > 0.7)}]
        self.incidents.append({"target": target, "timestamp": time.time(), "findings": findings})
        return findings

    @property
    def stats(self) -> dict[str, Any]:
        return {"vulnerabilities": len(self.vulnerabilities), "threats": len(self.threats), "critical": sum(1 for v in self.vulnerabilities if v.severity == ThreatLevel.CRITICAL), "scans": len(self.incidents)}
