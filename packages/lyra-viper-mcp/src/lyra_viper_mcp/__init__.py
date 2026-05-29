"""VIPER-MCP — Taint-Style Vulnerability Detection for MCP Servers.

Two-pass static analysis + feedback-driven prompt evolution for PoC generation.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "TaintSource",
    "Vulnerability",
    "TaintAnalyzer",
    "PromptEvolver",
    "VulnerabilityScanner",
]


@dataclass
class TaintSource:
    name: str
    tool_handler: str
    parameters: list[str]
    risk_level: str = "medium"


@dataclass
class Vulnerability:
    mcp_server: str
    tool_name: str
    vulnerability_type: str
    severity: str
    description: str
    proof_of_concept: str = ""
    anchor: str = ""
    query: str = ""


class TaintAnalyzer:
    """Two-pass static analysis resolving artifacts to MCP tool handlers."""

    def __init__(self):
        self.sources: list[TaintSource] = []
        self.vulnerabilities: list[Vulnerability] = []

    def register_source(self, source: TaintSource) -> None:
        self.sources.append(source)

    async def pass1_anchor_query(self, mcp_code: str) -> list[dict[str, Any]]:
        """First pass: resolve artifacts to specific MCP tool handlers (anchor-query)."""
        anchors = []
        try:
            tree = ast.parse(mcp_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    decorator_names = []
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and hasattr(decorator.func, "id"):
                            decorator_names.append(decorator.func.id)
                        elif isinstance(decorator, ast.Attribute):
                            decorator_names.append(decorator.attr)

                    if any("tool" in d.lower() or "mcp" in d.lower() for d in decorator_names):
                        params = [arg.arg for arg in node.args.args]
                        risk_params = [
                            p
                            for p in params
                            if any(
                                kw in p.lower()
                                for kw in ["cmd", "exec", "shell", "path", "file", "sql", "query"]
                            )
                        ]
                        anchors.append(
                            {
                                "handler": node.name,
                                "params": params,
                                "risk_params": risk_params,
                                "risk_level": "high" if risk_params else "low",
                                "line": node.lineno,
                            }
                        )
        except SyntaxError:
            anchors.append({"handler": "parse_error", "params": [], "risk_level": "unknown"})
        return anchors

    async def pass2_prompt_evolution(self, handler: dict[str, Any]) -> str:
        """Second pass: feedback-driven prompt evolution for PoC generation."""
        if handler["risk_level"] == "high":
            param_hints = ", ".join(handler["risk_params"])
            return (
                f"You are testing {handler['handler']}. "
                f"Generate a prompt that exploits parameter: {param_hints}. "
                f"Attempt: path traversal, command injection, and parameter pollution."
            )
        return f"Test {handler['handler']} for standard injection patterns."

    async def scan(self, mcp_code: str, server_name: str) -> list[Vulnerability]:
        """Full vulnerability scan of an MCP server."""
        anchors = await self.pass1_anchor_query(mcp_code)
        for anchor in anchors:
            poc = await self.pass2_prompt_evolution(anchor)
            if anchor["risk_level"] == "high":
                vuln = Vulnerability(
                    mcp_server=server_name,
                    tool_name=anchor["handler"],
                    vulnerability_type="taint_injection",
                    severity="high",
                    description=(
                        f"High-risk parameters in {anchor['handler']}: {anchor['risk_params']}"
                    ),
                    proof_of_concept=poc,
                    anchor=anchor["handler"],
                    query=",".join(anchor["risk_params"]),
                )
                self.vulnerabilities.append(vuln)
        return self.vulnerabilities


class PromptEvolver:
    """Feedback-driven prompt evolution for generating proof-of-concept exploits."""

    def __init__(self):
        self.evolution_history: list[dict[str, Any]] = []

    async def evolve(self, base_prompt: str, feedback: str = "") -> str:
        """Evolve a prompt based on previous feedback."""
        if feedback:
            evolved = f"{base_prompt}\n[Feedback: {feedback}]\nTry a different attack vector."
        else:
            evolved = f"{base_prompt}\n[Initial attempt]"
        self.evolution_history.append(
            {"base": base_prompt, "evolved": evolved, "feedback": feedback}
        )
        return evolved


class VulnerabilityScanner:
    """End-to-end MCP vulnerability scanner."""

    def __init__(self):
        self.analyzer = TaintAnalyzer()
        self.evolver = PromptEvolver()

    async def scan_server(self, mcp_code: str, server_name: str) -> dict[str, Any]:
        """Scan an MCP server for vulnerabilities."""
        vulnerabilities = await self.analyzer.scan(mcp_code, server_name)
        return {
            "server": server_name,
            "vulnerabilities": [
                {
                    "tool": v.tool_name,
                    "type": v.vulnerability_type,
                    "severity": v.severity,
                    "description": v.description,
                }
                for v in vulnerabilities
            ],
            "total": len(vulnerabilities),
            "high_severity": sum(1 for v in vulnerabilities if v.severity == "high"),
        }
