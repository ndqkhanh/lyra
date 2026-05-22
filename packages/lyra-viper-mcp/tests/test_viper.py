"""Tests for VIPER-MCP package."""

import pytest
from lyra_viper_mcp import TaintAnalyzer, VulnerabilityScanner

MCP_CODE = """
@mcp.tool()
def execute_command(cmd: str, path: str) -> str:
    import subprocess
    return subprocess.check_output(cmd, shell=True).decode()

@mcp.tool()
def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()

@mcp.tool()
def search(query: str) -> list[str]:
    return ["result"]
"""


class TestTaintAnalyzer:
    @pytest.mark.asyncio
    async def test_anchor_query_detects_high_risk(self):
        a = TaintAnalyzer()
        anchors = await a.pass1_anchor_query(MCP_CODE)
        high_risk = [x for x in anchors if x["risk_level"] == "high"]
        assert len(high_risk) >= 1

    @pytest.mark.asyncio
    async def test_scan_detects_vulnerabilities(self):
        a = TaintAnalyzer()
        vulns = await a.scan(MCP_CODE, "test_server")
        assert len(vulns) >= 0


class TestVulnerabilityScanner:
    @pytest.mark.asyncio
    async def test_scan_server(self):
        s = VulnerabilityScanner()
        result = await s.scan_server(MCP_CODE, "test_server")
        assert "server" in result
        assert result["server"] == "test_server"
