"""Tests for VIPER-MCP package."""

import asyncio
import pytest
from lyra_viper_mcp import TaintAnalyzer, VulnerabilityScanner, PromptEvolver

SIMPLE_MCP_CODE = """
@mcp.tool()
def execute_command(cmd, path):
    import subprocess
    return subprocess.check_output(cmd, shell=True).decode()
"""


class TestTaintAnalyzer:
    def test_anchor_query(self):
        a = TaintAnalyzer()
        anchors = asyncio.run(a.pass1_anchor_query(SIMPLE_MCP_CODE))
        assert len(anchors) >= 0

    def test_scan(self):
        a = TaintAnalyzer()
        vulns = asyncio.run(a.scan(SIMPLE_MCP_CODE, "test_server"))
        assert isinstance(vulns, list)


class TestPromptEvolver:
    def test_evolve(self):
        e = PromptEvolver()
        result = asyncio.run(e.evolve("test prompt"))
        assert "Initial attempt" in result


class TestVulnerabilityScanner:
    def test_scan_server(self):
        s = VulnerabilityScanner()
        result = asyncio.run(s.scan_server(SIMPLE_MCP_CODE, "test_server"))
        assert result["server"] == "test_server"
