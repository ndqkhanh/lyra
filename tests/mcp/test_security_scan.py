"""Comprehensive tests for MCP security scanning — VIPER-MCP integration."""

import pytest

from lyra.mcp.security_scan import (
    MCPTaintAnalyzer,
    MCPSecurityScanner,
    MCPVulnerability,
)


# =============================================================================
# Tests: MCPVulnerability
# =============================================================================


class TestMCPVulnerability:
    def test_minimal(self):
        v = MCPVulnerability(
            tool_name="search",
            vulnerability_type="taint_injection",
            severity="high",
            description="High-risk parameter detected",
        )
        assert v.tool_name == "search"
        assert v.vulnerability_type == "taint_injection"
        assert v.severity == "high"
        assert v.line_number == 0
        assert v.proof_of_concept == ""

    def test_full(self):
        v = MCPVulnerability(
            tool_name="exec",
            vulnerability_type="command_injection",
            severity="critical",
            description="Command injection via cmd parameter",
            line_number=42,
            proof_of_concept="Exploit via cmd parameter injection",
        )
        assert v.tool_name == "exec"
        assert v.severity == "critical"
        assert v.line_number == 42
        assert v.proof_of_concept == "Exploit via cmd parameter injection"


# =============================================================================
# Tests: MCPTaintAnalyzer
# =============================================================================


class TestMCPTaintAnalyzer:
    def test_risky_params_are_defined(self):
        expected = {"cmd", "exec", "shell", "path", "file", "sql", "query", "command", "code"}
        assert MCPTaintAnalyzer.RISKY_PARAMS == expected

    def test_analyze_tool_handler_with_risky_params(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def search_tool(cmd: str, path: str) -> str:
    result = run(cmd, path)
    return result
"""
        vulns = analyzer.analyze_tool_handler(source, "search_tool")
        assert len(vulns) == 1
        assert vulns[0].tool_name == "search_tool"
        assert vulns[0].vulnerability_type == "taint_injection"
        assert vulns[0].severity == "high"
        assert "cmd" in vulns[0].description
        assert "path" in vulns[0].description

    def test_analyze_tool_handler_no_risky_params(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def safe_tool(name: str, age: int) -> str:
    return f"Hello {name}, age {age}"
"""
        vulns = analyzer.analyze_tool_handler(source, "safe_tool")
        assert vulns == []

    def test_analyze_tool_handler_syntax_error(self):
        analyzer = MCPTaintAnalyzer()
        source = "def invalid_syntax(::"
        vulns = analyzer.analyze_tool_handler(source, "invalid_syntax")
        assert vulns == []

    def test_analyze_tool_handler_function_not_found(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def unrelated(x: int) -> int:
    return x * 2
"""
        vulns = analyzer.analyze_tool_handler(source, "not_found")
        assert vulns == []

    def test_analyze_tool_handler_single_risky_param(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def query_db(sql: str) -> list:
    return execute(sql)
"""
        vulns = analyzer.analyze_tool_handler(source, "query_db")
        assert len(vulns) == 1
        assert "sql" in vulns[0].description

    def test_analyze_tool_handler_multiple_risky_params(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def dangerous(cmd: str, shell: bool, file: str) -> None:
    subprocess.run(cmd, shell=shell)
"""
        vulns = analyzer.analyze_tool_handler(source, "dangerous")
        assert len(vulns) == 1
        # Should list all 3 risky params
        assert "cmd" in vulns[0].description
        assert "shell" in vulns[0].description
        assert "file" in vulns[0].description

    def test_analyze_tool_handler_empty_source(self):
        analyzer = MCPTaintAnalyzer()
        vulns = analyzer.analyze_tool_handler("", "empty_fn")
        assert vulns == []

    def test_analyze_tool_handler_with_method_definition(self):
        analyzer = MCPTaintAnalyzer()
        source = """
class MyHandler:
    def handle(self, cmd: str, request: dict) -> str:
        return subprocess.run(cmd, shell=True)
"""
        vulns = analyzer.analyze_tool_handler(source, "handle")
        # The analyzer checks FunctionDef nodes; method `handle` inside class
        # still gets matched as a FunctionDef
        assert len(vulns) == 1

    def test_analyze_tool_handler_param_named_similarly_to_risky(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def my_command_handler(command_id: int, command_text: str) -> str:
    return process(command_id, command_text)
"""
        vulns = analyzer.analyze_tool_handler(source, "my_command_handler")
        # "command_id" and "command_text" are NOT exact matches for "command" in RISKY_PARAMS
        assert len(vulns) == 0

    def test_analyze_tool_handler_case_sensitivity(self):
        analyzer = MCPTaintAnalyzer()
        source = """
def handler(Cmd: str, Path: str) -> str:
    return f"{Cmd} {Path}"
"""
        vulns = analyzer.analyze_tool_handler(source, "handler")
        # RISKY_PARAMS are lowercase, so "Cmd" and "Path" won't match
        assert vulns == []

    def test_scan_server_multiple_tools(self):
        analyzer = MCPTaintAnalyzer()
        handlers = {
            "safe_tool": "def safe_tool(name: str) -> str: return name",
            "risky_tool": "def risky_tool(cmd: str, path: str) -> str: return cmd",
            "another_tool": "def another_tool(query: str) -> str: return query",
        }
        result = analyzer.scan_server("my_server", handlers)
        assert result["server"] == "my_server"
        assert result["tools_scanned"] == 3
        assert result["high_severity_count"] >= 2  # risky_tool and another_tool
        assert len(result["vulnerabilities"]) >= 2

    def test_scan_server_empty_handlers(self):
        analyzer = MCPTaintAnalyzer()
        result = analyzer.scan_server("empty_server", {})
        assert result["server"] == "empty_server"
        assert result["tools_scanned"] == 0
        assert result["high_severity_count"] == 0
        assert result["vulnerabilities"] == []


# =============================================================================
# Tests: MCPSecurityScanner
# =============================================================================


class TestMCPSecurityScanner:
    @pytest.fixture
    def scanner(self):
        return MCPSecurityScanner()

    def test_init(self, scanner):
        assert isinstance(scanner.analyzer, MCPTaintAnalyzer)
        assert scanner.scan_results == {}

    async def test_scan_registered_servers_empty(self, scanner):
        summary = await scanner.scan_registered_servers({})
        assert summary["total_servers"] == 0
        assert summary["total_vulnerabilities"] == 0
        assert summary["servers"] == {}

    async def test_scan_registered_servers_single(self, scanner):
        handlers = {
            "search": "def search(query: str) -> str: return query",
        }
        summary = await scanner.scan_registered_servers({"server1": handlers})
        assert summary["total_servers"] == 1
        assert summary["total_vulnerabilities"] == 1
        assert "server1" in summary["servers"]

    async def test_scan_registered_servers_multiple(self, scanner):
        servers = {
            "server1": {
                "safe": "def safe(name: str) -> str: return name",
            },
            "server2": {
                "dangerous": "def dangerous(cmd: str, path: str) -> str: return cmd",
            },
        }
        summary = await scanner.scan_registered_servers(servers)
        assert summary["total_servers"] == 2
        assert summary["total_vulnerabilities"] == 1  # only server2
        assert "server1" in summary["servers"]
        assert "server2" in summary["servers"]

    async def test_scan_stores_results(self, scanner):
        handlers = {
            "tool1": "def tool1(path: str) -> str: return path",
        }
        await scanner.scan_registered_servers({"svr": handlers})
        assert "svr" in scanner.scan_results
        assert scanner.scan_results["svr"]["tools_scanned"] == 1

    async def test_scan_no_vulnerabilities(self, scanner):
        servers = {
            "safe_server": {
                "greet": "def greet(name: str, age: int) -> str: return f'Hi {name}'",
                "add": "def add(a: int, b: int) -> int: return a + b",
            },
        }
        summary = await scanner.scan_registered_servers(servers)
        assert summary["total_vulnerabilities"] == 0
        assert len(scanner.scan_results["safe_server"]["vulnerabilities"]) == 0

    async def test_scan_all_risky_param_types(self, scanner):
        handlers = {
            f"tool_{param}": f"def tool_{param}({param}: str) -> str: return {param}"
            for param in sorted(MCPTaintAnalyzer.RISKY_PARAMS)
        }
        summary = await scanner.scan_registered_servers({"all_risky": handlers})
        assert summary["total_vulnerabilities"] == len(MCPTaintAnalyzer.RISKY_PARAMS)

    async def test_scan_with_non_string_source(self, scanner):
        """Test with handlers that have empty source code (edge case)."""
        servers = {
            "empty": {},
        }
        summary = await scanner.scan_registered_servers(servers)
        assert summary["total_servers"] == 1
        assert summary["total_vulnerabilities"] == 0
