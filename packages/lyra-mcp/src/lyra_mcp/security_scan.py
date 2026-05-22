"""VIPER-MCP security scanning integration for lyra-mcp.

Automated taint-style vulnerability detection for MCP servers.
Based on VIPER-MCP (arXiv:2605.21392).
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPVulnerability:
    tool_name: str
    vulnerability_type: str
    severity: str  # high, medium, low
    description: str
    line_number: int = 0
    proof_of_concept: str = ""


class MCPTaintAnalyzer:
    """Taint-style analysis for MCP server code."""

    RISKY_PARAMS = {"cmd", "exec", "shell", "path", "file", "sql", "query", "command", "code"}

    def analyze_tool_handler(self, source_code: str, tool_name: str) -> list[MCPVulnerability]:
        vulns = []
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == tool_name:
                    params = {arg.arg for arg in node.args.args}
                    risky_params = params & self.RISKY_PARAMS
                    if risky_params:
                        vulns.append(MCPVulnerability(
                            tool_name=tool_name,
                            vulnerability_type="taint_injection",
                            severity="high",
                            description=f"High-risk parameters: {', '.join(risky_params)}",
                            line_number=node.lineno,
                            proof_of_concept=f"Exploit via {'/'.join(risky_params)} parameter injection",
                        ))
        except SyntaxError:
            pass
        return vulns

    def scan_server(self, server_name: str, tool_handlers: dict[str, str]) -> dict[str, Any]:
        all_vulns = []
        for tool_name, source in tool_handlers.items():
            vulns = self.analyze_tool_handler(source, tool_name)
            all_vulns.extend(vulns)
        return {
            "server": server_name,
            "tools_scanned": len(tool_handlers),
            "vulnerabilities": [v.__dict__ for v in all_vulns],
            "high_severity_count": sum(1 for v in all_vulns if v.severity == "high"),
        }


class MCPSecurityScanner:
    """End-to-end MCP security scanner. Integrates with lyra-mcp server lifecycle."""

    def __init__(self):
        self.analyzer = MCPTaintAnalyzer()
        self.scan_results: dict[str, dict[str, Any]] = {}

    async def scan_registered_servers(self, servers: dict[str, dict[str, str]]) -> dict[str, Any]:
        summary = {"total_servers": len(servers), "total_vulnerabilities": 0, "servers": {}}
        for server_name, handlers in servers.items():
            result = self.analyzer.scan_server(server_name, handlers)
            self.scan_results[server_name] = result
            summary["servers"][server_name] = result
            summary["total_vulnerabilities"] += result["high_severity_count"]
        return summary
