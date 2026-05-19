"""Tests for advanced capabilities."""

from datetime import datetime

import pytest

from lyra_advanced import (
    AnalysisType,
    ExploitDevelopment,
    ExploitType,
    MalwareAnalysis,
    MalwareSample,
    MalwareType,
    Vulnerability,
)


def test_exploit_dev_init():
    """Test exploit development initialization."""
    exploit_dev = ExploitDevelopment()
    assert len(exploit_dev.templates) > 0


def test_exploit_dev_analyze_vulnerability():
    """Test vulnerability analysis."""
    exploit_dev = ExploitDevelopment()

    vuln = Vulnerability(
        vuln_id="VULN-001",
        cve="CVE-2021-44228",
        name="Log4Shell",
        description="RCE in Log4j",
        affected_software="Apache Log4j",
        affected_version="2.14.1",
        exploit_type=ExploitType.RCE,
        severity="CRITICAL",
    )

    analysis = exploit_dev.analyze_vulnerability(vuln)

    assert analysis["exploitable"] is True
    assert "recommended_approach" in analysis


def test_exploit_dev_generate_exploit():
    """Test exploit generation."""
    exploit_dev = ExploitDevelopment()

    vuln = Vulnerability(
        vuln_id="VULN-002",
        cve=None,
        name="Buffer Overflow",
        description="Stack overflow",
        affected_software="Custom App",
        affected_version="1.0",
        exploit_type=ExploitType.BUFFER_OVERFLOW,
        severity="HIGH",
    )

    exploit = exploit_dev.generate_exploit(vuln)

    assert exploit.exploit_id == "exploit_VULN-002"
    assert len(exploit.exploit_code) > 0
    assert len(exploit.payload) > 0


def test_exploit_dev_test_exploit():
    """Test exploit testing."""
    exploit_dev = ExploitDevelopment()

    vuln = Vulnerability(
        vuln_id="VULN-003",
        cve=None,
        name="SQL Injection",
        description="SQL injection",
        affected_software="Web App",
        affected_version="1.0",
        exploit_type=ExploitType.SQL_INJECTION,
        severity="HIGH",
    )

    exploit = exploit_dev.generate_exploit(vuln)
    result = exploit_dev.test_exploit(exploit.exploit_id, safe_mode=True)

    assert result["success"] is True
    assert result["safe_mode"] is True


def test_exploit_dev_stats():
    """Test exploit statistics."""
    exploit_dev = ExploitDevelopment()

    # Generate some exploits
    for i in range(3):
        vuln = Vulnerability(
            vuln_id=f"VULN-{i}",
            cve=None,
            name=f"Vuln {i}",
            description="Test",
            affected_software="Test",
            affected_version="1.0",
            exploit_type=ExploitType.RCE,
            severity="HIGH",
        )
        exploit_dev.generate_exploit(vuln)

    stats = exploit_dev.get_exploit_stats()

    assert stats["total_exploits"] == 3


def test_malware_analysis_init():
    """Test malware analysis initialization."""
    malware_analysis = MalwareAnalysis()
    assert len(malware_analysis.samples) == 0


def test_malware_analysis_submit_sample():
    """Test sample submission."""
    malware_analysis = MalwareAnalysis()

    sample = MalwareSample(
        sample_id="SAMPLE-001",
        file_hash="abc123",
        file_name="malware.exe",
        file_size=1024000,
        file_type="PE",
    )

    sample_id = malware_analysis.submit_sample(sample)

    assert sample_id == "SAMPLE-001"
    assert sample_id in malware_analysis.samples


def test_malware_analysis_static():
    """Test static analysis."""
    malware_analysis = MalwareAnalysis()

    sample = MalwareSample(
        sample_id="SAMPLE-002",
        file_hash="def456",
        file_name="ransomware.exe",
        file_size=2048000,
        file_type="PE",
    )

    malware_analysis.submit_sample(sample)
    result = malware_analysis.analyze_static("SAMPLE-002")

    assert result.analysis_type == AnalysisType.STATIC
    assert result.malware_type == MalwareType.RANSOMWARE
    assert len(result.iocs) > 0


def test_malware_analysis_dynamic():
    """Test dynamic analysis."""
    malware_analysis = MalwareAnalysis()

    sample = MalwareSample(
        sample_id="SAMPLE-003",
        file_hash="ghi789",
        file_name="trojan.exe",
        file_size=512000,
        file_type="PE",
    )

    malware_analysis.submit_sample(sample)
    result = malware_analysis.analyze_dynamic("SAMPLE-003")

    assert result.analysis_type == AnalysisType.DYNAMIC
    assert len(result.behaviors) > 0


def test_malware_analysis_report():
    """Test analysis report generation."""
    malware_analysis = MalwareAnalysis()

    sample = MalwareSample(
        sample_id="SAMPLE-004",
        file_hash="jkl012",
        file_name="malware.exe",
        file_size=1024000,
        file_type="PE",
    )

    malware_analysis.submit_sample(sample)
    malware_analysis.analyze_static("SAMPLE-004")

    report = malware_analysis.get_analysis_report("SAMPLE-004")

    assert "sample" in report
    assert "analysis" in report
    assert "iocs" in report


def test_malware_analysis_statistics():
    """Test analysis statistics."""
    malware_analysis = MalwareAnalysis()

    # Submit and analyze multiple samples
    for i in range(3):
        sample = MalwareSample(
            sample_id=f"SAMPLE-{i}",
            file_hash=f"hash{i}",
            file_name=f"malware{i}.exe",
            file_size=1024000,
            file_type="PE",
        )
        malware_analysis.submit_sample(sample)
        malware_analysis.analyze_static(f"SAMPLE-{i}")

    stats = malware_analysis.get_statistics()

    assert stats["total_samples"] == 3
    assert stats["analyzed_samples"] == 3
    assert stats["avg_threat_score"] > 0
