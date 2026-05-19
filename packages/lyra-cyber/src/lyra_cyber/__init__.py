"""
Lyra Cyber - Cyber-specific enhancements.

This package provides:
- Red team automation
- Blue team defense
- Threat intelligence
"""

from lyra_cyber.blue_team import (
    BlueTeamDefense,
    Incident,
    IncidentStatus,
    SecurityAlert,
    ThreatSeverity,
)
from lyra_cyber.red_team import (
    AttackChain,
    AttackPhase,
    AttackTechnique,
    RedTeamAutomation,
)
from lyra_cyber.threat_intel import IOC, IOCType, ThreatActor, ThreatIntelligence

__version__ = "0.1.0"

__all__ = [
    # Red Team
    "RedTeamAutomation",
    "AttackChain",
    "AttackPhase",
    "AttackTechnique",
    # Blue Team
    "BlueTeamDefense",
    "SecurityAlert",
    "Incident",
    "ThreatSeverity",
    "IncidentStatus",
    # Threat Intel
    "ThreatIntelligence",
    "IOC",
    "IOCType",
    "ThreatActor",
]
