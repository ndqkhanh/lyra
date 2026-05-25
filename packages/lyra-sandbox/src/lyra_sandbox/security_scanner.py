"""Pre-execution security scanning of code and dependencies."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import Language, SecurityScanError


class FindingSeverity(str, Enum):
    """Severity level of a security finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class SecurityFinding:
    """A single security issue discovered during scanning."""

    line_number: int
    severity: FindingSeverity
    pattern: str
    description: str
    recommendation: str = ""


@dataclass(frozen=True)
class ScanResult:
    """Outcome of a security scan."""

    passed: bool
    risk_score: float = 0.0
    findings: tuple[SecurityFinding, ...] = ()
    blocked_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class SecurityPolicy:
    """Configuration for security scanning behaviour."""

    blocked_imports: tuple[str, ...] = (
        "subprocess",
        "os",
        "socket",
        "ctypes",
        "multiprocessing",
        "signal",
        "syscall",
        "fcntl",
    )
    blocked_patterns: tuple[str, ...] = (
        "eval(",
        "exec(",
        "__import__(",
        "open('/etc",
        "open('/proc",
        "open('\\x2fetc",
        "requests.post(",
        "requests.get(",
        "urllib.request",
        "os.system(",
        "os.popen(",
        "subprocess.call(",
        "subprocess.Popen(",
        "subprocess.run(",
        "shutil.rmtree(",
        "os.remove(",
        "os.unlink(",
        "os.chmod(",
        "os.chown(",
        "pty.spawn(",
        "ctypes.CDLL(",
        "ctypes.c_",
        "socket.socket(",
    )
    max_complexity: int = 20
    allowed_syscalls: tuple[str, ...] = (
        "read",
        "write",
        "open",
        "close",
        "exit",
        "brk",
    )


@dataclass(frozen=True)
class ScanConfig:
    """Runtime configuration for the security scanner."""

    enabled: bool = True
    strict_mode: bool = True
    patterns_file: str | None = None
    auto_block_critical: bool = True


class SecurityScanner:
    """Scans source code for dangerous patterns before execution."""

    _severity_scores: dict[FindingSeverity, int] = {
        FindingSeverity.CRITICAL: 10,
        FindingSeverity.HIGH: 7,
        FindingSeverity.MEDIUM: 4,
        FindingSeverity.LOW: 2,
        FindingSeverity.INFO: 0,
    }

    @classmethod
    def scan_code(
        cls,
        code: str,
        language: Language = Language.PYTHON,
        policy: SecurityPolicy | None = None,
    ) -> ScanResult:
        """Scan source code for dangerous patterns."""
        if not code.strip():
            return ScanResult(passed=True)
        policy = policy or SecurityPolicy()
        findings: list[SecurityFinding] = []
        blocked: list[str] = []

        # Pattern-based scan (all languages)
        for pattern in policy.blocked_patterns:
            for lineno, line in enumerate(code.splitlines(), start=1):
                if pattern in line:
                    severity = FindingSeverity.CRITICAL if _is_critical_pattern(pattern) else FindingSeverity.HIGH
                    findings.append(
                        SecurityFinding(
                            line_number=lineno,
                            severity=severity,
                            pattern=pattern,
                            description=f"Dangerous pattern detected: {pattern}",
                            recommendation=f"Avoid using {pattern} in sandboxed code",
                        )
                    )
                    blocked.append(pattern)

        # AST analysis for Python
        if language == Language.PYTHON:
            findings.extend(cls._ast_scan(code, policy))

        # Blocked import scan
        if language == Language.PYTHON:
            for imp in policy.blocked_imports:
                pattern = f"import {imp}" if imp != "os" else None
                if pattern and pattern in code:
                    blocked.append(imp)

        total_score = sum(cls._severity_scores.get(f.severity, 0) for f in findings)
        passed = len(findings) == 0

        return ScanResult(
            passed=passed,
            risk_score=min(total_score / 100.0, 1.0),
            findings=tuple(findings),
            blocked_patterns=tuple(set(blocked)),
        )

    @classmethod
    def scan_dependencies(
        cls,
        packages: list[str],
    ) -> ScanResult:
        """Scan a list of package names for known dangerous dependencies."""
        findings: list[SecurityFinding] = []
        blocked: list[str] = []
        dangerous_prefixes = ("pwn", "exploit", "hack", "crack", "malware")

        for pkg in packages:
            pkg_lower = pkg.lower()
            if any(pkg_lower.startswith(p) for p in dangerous_prefixes):
                findings.append(
                    SecurityFinding(
                        line_number=0,
                        severity=FindingSeverity.CRITICAL,
                        pattern=pkg,
                        description=f"Suspicious package name: {pkg}",
                        recommendation=f"Remove {pkg} from dependencies",
                    )
                )
                blocked.append(pkg)

        return ScanResult(
            passed=len(blocked) == 0,
            risk_score=len(blocked) / max(len(packages), 1),
            findings=tuple(findings),
            blocked_patterns=tuple(blocked),
        )

    @staticmethod
    def _ast_scan(code: str, policy: SecurityPolicy) -> list[SecurityFinding]:
        """Run AST-based static analysis on Python code."""
        findings: list[SecurityFinding] = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ("os", "subprocess", "shutil", "socket", "ctypes"):
                            findings.append(
                                SecurityFinding(
                                    line_number=node.lineno,
                                    severity=FindingSeverity.HIGH,
                                    pattern=f"{node.func.value.id}.{node.func.attr}",
                                    description=f"Potentially dangerous call: {node.func.value.id}.{node.func.attr}",
                                )
                            )
        except SyntaxError:
            findings.append(
                SecurityFinding(
                    line_number=1,
                    severity=FindingSeverity.MEDIUM,
                    pattern="syntax_error",
                    description="Code contains syntax errors",
                )
            )
        return findings


def _is_critical_pattern(pattern: str) -> bool:
    """Determine whether a blocked pattern is critical severity."""
    critical = (
        "subprocess",
        "os.system",
        "os.popen",
        "socket.socket",
        "ctypes.CDLL",
        "open('/etc",
        "open('/proc",
    )
    return any(c in pattern for c in critical)
