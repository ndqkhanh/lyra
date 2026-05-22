"""Tests for lyra-cybersecurity."""
from lyra_cybersecurity import CyberSecurityAgent

class TestCyberSecurityAgent:
    def test_register_vuln(self):
        c = CyberSecurityAgent()
        v = c.register_vulnerability("CVE-2026-1234", "HIGH", "Remote code execution")
        assert v.cve == "CVE-2026-1234"

    def test_scan(self):
        c = CyberSecurityAgent()
        c.register_vulnerability("CVE-2026-0001", "CRITICAL", "Zero-day")
        findings = c.scan("192.168.1.1")
        assert len(findings) > 0
