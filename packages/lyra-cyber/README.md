# Lyra Cyber - Phase 7: Cyber-Specific Enhancements

## Overview

Phase 7 implements cyber-specific capabilities including red team automation, blue team defense, and threat intelligence.

## Features

### 1. Red Team Automation (`red_team.py`)

Offensive security automation with MITRE ATT&CK:

```python
from lyra_cyber import RedTeamAutomation, AttackPhase

red_team = RedTeamAutomation()

# Plan attack chain
chain = red_team.plan_attack_chain(
    target="192.168.1.100",
    objective="full_compromise"
)

print(f"Attack phases: {len(chain.phases)}")
print(f"Current phase: {chain.current_phase.value}")

# Execute phase (safe mode)
result = red_team.execute_phase(chain.chain_id, safe_mode=True)
print(f"Success: {result['success']}")

# Advance to next phase
red_team.advance_phase(chain.chain_id)

# Get status
status = red_team.get_chain_status(chain.chain_id)
print(f"Progress: {status['completed_phases']}/{status['total_phases']}")
```

**Attack Phases** (MITRE ATT&CK):
- Reconnaissance
- Initial Access
- Execution
- Persistence
- Privilege Escalation
- Defense Evasion
- Credential Access
- Discovery
- Lateral Movement
- Collection
- Exfiltration

### 2. Blue Team Defense (`blue_team.py`)

Defensive security automation:

```python
from lyra_cyber import BlueTeamDefense, SecurityAlert, ThreatSeverity
from datetime import datetime

blue_team = BlueTeamDefense()

# Triage alert
alert = SecurityAlert(
    alert_id="ALERT-001",
    title="Suspicious login attempt",
    severity=ThreatSeverity.HIGH,
    source="SIEM",
    timestamp=datetime.now(),
    indicators=["192.168.1.100:22"],
    description="Multiple failed SSH login attempts",
    false_positive_score=0.1,
)

result = blue_team.triage_alert(alert)
print(f"Priority: {result['priority_score']:.2f}")
print(f"Action: {result['recommended_action']}")

# Create incident
incident = blue_team.create_incident(
    title="Brute force attack",
    severity=ThreatSeverity.HIGH,
    alert_ids=["ALERT-001"],
)

# Respond to incident
response = blue_team.respond_to_incident(incident.incident_id, "contain")
print(f"Status: {response['new_status']}")
```

**Threat Severity Levels**:
- LOW
- MEDIUM
- HIGH
- CRITICAL

**Incident Response Actions**:
- contain
- eradicate
- recover

### 3. Threat Intelligence (`threat_intel.py`)

IOC management and threat actor profiling:

```python
from lyra_cyber import ThreatIntelligence, IOC, IOCType, ThreatActor
from datetime import datetime

threat_intel = ThreatIntelligence()

# Add IOC
ioc = IOC(
    ioc_id="IOC-001",
    ioc_type=IOCType.IP_ADDRESS,
    value="192.168.1.100",
    confidence=0.95,
    first_seen=datetime.now(),
    last_seen=datetime.now(),
    tags=["malware", "c2"],
)
threat_intel.add_ioc(ioc)

# Check IOC
found = threat_intel.check_ioc("192.168.1.100", IOCType.IP_ADDRESS)
if found:
    print(f"Known IOC: {found.value} (confidence: {found.confidence})")

# Enrich IOC
enriched = threat_intel.enrich_ioc("IOC-001")
print(f"Tags: {enriched['tags']}")

# Add threat actor
actor = ThreatActor(
    actor_id="APT-001",
    name="Advanced Persistent Threat 1",
    aliases=["APT1", "Comment Crew"],
    motivation="espionage",
    sophistication="advanced",
    ttps=["T1059.001", "T1078", "T1021.001"],
)
threat_intel.add_threat_actor(actor)

# Get actor profile
profile = threat_intel.get_actor_profile("APT-001")
print(f"Actor: {profile['name']}")
print(f"TTPs: {profile['ttps']}")
```

**IOC Types**:
- IP Address
- Domain
- URL
- File Hash
- Email
- CVE

## Architecture

```
┌─────────────────────────────────────────┐
│    Red Team Automation                  │
│  (Offensive Security)                   │
│                                         │
│  Plan → Execute → Advance              │
│  MITRE ATT&CK techniques               │
│  Safe mode for testing                 │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Blue Team Defense                    │
│  (Defensive Security)                   │
│                                         │
│  Alert → Triage → Incident → Respond   │
│  Priority scoring                      │
│  False positive detection              │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│  Threat Intelligence                    │
│  (IOC & Actor Tracking)                 │
│                                         │
│  IOC → Enrich → Correlate              │
│  Threat actor profiling                │
│  Intelligence feeds                    │
└─────────────────────────────────────────┘
```

## Use Cases

### Automated Red Team Exercise

```python
red_team = RedTeamAutomation()

# Plan full compromise
chain = red_team.plan_attack_chain("target.com", "full_compromise")

# Execute each phase
for phase in chain.phases:
    result = red_team.execute_phase(chain.chain_id, safe_mode=True)
    print(f"Phase {phase.value}: {result['message']}")
    red_team.advance_phase(chain.chain_id)
```

### Incident Response Workflow

```python
blue_team = BlueTeamDefense()

# Multiple alerts
alerts = [...]  # List of SecurityAlert objects

# Triage all alerts
for alert in alerts:
    result = blue_team.triage_alert(alert)
    if result['recommended_action'] == 'escalate_immediately':
        # Create incident
        incident = blue_team.create_incident(
            title=f"Critical: {alert.title}",
            severity=alert.severity,
            alert_ids=[alert.alert_id],
        )
        
        # Respond
        blue_team.respond_to_incident(incident.incident_id, "contain")
```

### Threat Intelligence Correlation

```python
threat_intel = ThreatIntelligence()

# Add multiple IOCs
iocs = [...]  # List of IOC objects
for ioc in iocs:
    threat_intel.add_ioc(ioc)

# Correlate
correlation = threat_intel.correlate_iocs([ioc.ioc_id for ioc in iocs])
print(f"Common threat actors: {correlation['common_threat_actors']}")
print(f"Common tags: {correlation['common_tags']}")
```

## Testing

Run tests:
```bash
cd packages/lyra-cyber
pip install -e .
pytest tests/ -v
```

Tests: 14 tests covering all components

## Next Steps (Phase 8)

- Desktop application (Tauri + React)
- GUI for Lyra
- Real-time monitoring dashboard

## Version

Current version: **0.1.0**

## Changes

- Added `RedTeamAutomation` for offensive security
- Added `BlueTeamDefense` for defensive security
- Added `ThreatIntelligence` for IOC tracking
- MITRE ATT&CK integration
- Incident response automation
- Threat actor profiling
- Comprehensive tests

## References

- MITRE ATT&CK: https://attack.mitre.org/
- Lyra Ultra Plan: `.omc/research/LYRA_ULTRA_ENHANCEMENT_PLAN.md`
