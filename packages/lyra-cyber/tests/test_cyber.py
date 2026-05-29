"""Tests for cyber-specific capabilities."""

from datetime import datetime

from lyra_cyber import (
    IOC,
    AttackPhase,
    BlueTeamDefense,
    IncidentStatus,
    IOCType,
    RedTeamAutomation,
    SecurityAlert,
    ThreatActor,
    ThreatIntelligence,
    ThreatSeverity,
)


def test_red_team_init():
    """Test red team initialization."""
    red_team = RedTeamAutomation()
    assert len(red_team.technique_library) > 0


def test_red_team_attack_planning():
    """Test attack chain planning."""
    red_team = RedTeamAutomation()

    chain = red_team.plan_attack_chain("192.168.1.100", objective="full_compromise")

    assert chain.target == "192.168.1.100"
    assert len(chain.phases) > 0
    assert chain.current_phase == AttackPhase.RECONNAISSANCE


def test_red_team_phase_execution():
    """Test phase execution in safe mode."""
    red_team = RedTeamAutomation()

    chain = red_team.plan_attack_chain("192.168.1.100")
    result = red_team.execute_phase(chain.chain_id, safe_mode=True)

    assert result["success"] is True
    assert result["safe_mode"] is True


def test_red_team_phase_advancement():
    """Test advancing through phases."""
    red_team = RedTeamAutomation()

    chain = red_team.plan_attack_chain("192.168.1.100")
    initial_phase = chain.current_phase

    red_team.advance_phase(chain.chain_id)

    assert chain.current_phase != initial_phase


def test_blue_team_init():
    """Test blue team initialization."""
    blue_team = BlueTeamDefense()
    assert len(blue_team.alerts) == 0


def test_blue_team_alert_triage():
    """Test alert triage."""
    blue_team = BlueTeamDefense()

    alert = SecurityAlert(
        alert_id="ALERT-001",
        title="Suspicious login",
        severity=ThreatSeverity.HIGH,
        source="SIEM",
        timestamp=datetime.now(),
        indicators=["192.168.1.100:22"],
        description="Multiple failed login attempts",
        false_positive_score=0.2,
    )

    result = blue_team.triage_alert(alert)

    assert result["alert_id"] == "ALERT-001"
    assert result["priority_score"] > 0
    assert result["is_false_positive"] is False


def test_blue_team_incident_creation():
    """Test incident creation."""
    blue_team = BlueTeamDefense()

    # Create alert first
    alert = SecurityAlert(
        alert_id="ALERT-001",
        title="Test alert",
        severity=ThreatSeverity.CRITICAL,
        source="SIEM",
        timestamp=datetime.now(),
        indicators=["192.168.1.100:22"],
        description="Test",
    )
    blue_team.triage_alert(alert)

    # Create incident
    incident = blue_team.create_incident(
        title="Security breach",
        severity=ThreatSeverity.CRITICAL,
        alert_ids=["ALERT-001"],
    )

    assert incident.status == IncidentStatus.NEW
    assert len(incident.alerts) == 1


def test_blue_team_incident_response():
    """Test incident response."""
    blue_team = BlueTeamDefense()

    alert = SecurityAlert(
        alert_id="ALERT-001",
        title="Test",
        severity=ThreatSeverity.HIGH,
        source="SIEM",
        timestamp=datetime.now(),
        indicators=[],
        description="Test",
    )
    blue_team.triage_alert(alert)

    incident = blue_team.create_incident("Test incident", ThreatSeverity.HIGH, ["ALERT-001"])

    result = blue_team.respond_to_incident(incident.incident_id, "contain")

    assert result["success"] is True
    assert incident.status == IncidentStatus.CONTAINED


def test_threat_intel_init():
    """Test threat intelligence initialization."""
    threat_intel = ThreatIntelligence()
    assert len(threat_intel.iocs) == 0


def test_threat_intel_ioc_management():
    """Test IOC management."""
    threat_intel = ThreatIntelligence()

    ioc = IOC(
        ioc_id="IOC-001",
        ioc_type=IOCType.IP_ADDRESS,
        value="192.168.1.100",
        confidence=0.9,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        tags=["malware", "c2"],
    )

    threat_intel.add_ioc(ioc)

    found = threat_intel.check_ioc("192.168.1.100", IOCType.IP_ADDRESS)
    assert found is not None
    assert found.ioc_id == "IOC-001"


def test_threat_intel_enrichment():
    """Test IOC enrichment."""
    threat_intel = ThreatIntelligence()

    ioc = IOC(
        ioc_id="IOC-001",
        ioc_type=IOCType.DOMAIN,
        value="evil.com",
        confidence=0.95,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
    )
    threat_intel.add_ioc(ioc)

    enriched = threat_intel.enrich_ioc("IOC-001")

    assert enriched["value"] == "evil.com"
    assert enriched["confidence"] == 0.95


def test_threat_intel_actor_profiling():
    """Test threat actor profiling."""
    threat_intel = ThreatIntelligence()

    actor = ThreatActor(
        actor_id="APT-001",
        name="Test APT",
        aliases=["APT1", "Group1"],
        motivation="espionage",
        sophistication="advanced",
        ttps=["T1059.001", "T1078"],
    )

    threat_intel.add_threat_actor(actor)

    profile = threat_intel.get_actor_profile("APT-001")

    assert profile["name"] == "Test APT"
    assert len(profile["aliases"]) == 2


def test_threat_intel_correlation():
    """Test IOC correlation."""
    threat_intel = ThreatIntelligence()

    ioc1 = IOC(
        ioc_id="IOC-001",
        ioc_type=IOCType.IP_ADDRESS,
        value="192.168.1.100",
        confidence=0.9,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        tags=["malware"],
    )

    ioc2 = IOC(
        ioc_id="IOC-002",
        ioc_type=IOCType.DOMAIN,
        value="evil.com",
        confidence=0.85,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        tags=["malware", "c2"],
    )

    threat_intel.add_ioc(ioc1)
    threat_intel.add_ioc(ioc2)

    correlation = threat_intel.correlate_iocs(["IOC-001", "IOC-002"])

    assert correlation["ioc_count"] == 2
    assert "malware" in correlation["common_tags"]
