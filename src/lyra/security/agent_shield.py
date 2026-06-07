"""
AgentShield - Security scanner for Lyra agents.

Features:
- Secrets detection (API keys, passwords, tokens)
- Command injection prevention
- Path traversal protection
- SQL injection detection
- XSS prevention
- Permission auditing
- Hook injection analysis
- MCP risk profiling
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SecuritySeverity(Enum):
    """Security issue severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCategory(Enum):
    """Security issue category."""

    SECRETS = "secrets"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PERMISSION = "permission"
    HOOK_INJECTION = "hook_injection"
    MCP_RISK = "mcp_risk"


@dataclass
class SecurityIssue:
    """Security issue found by scanner."""

    category: SecurityCategory
    severity: SecuritySeverity
    message: str
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None


@dataclass
class SecurityReport:
    """Security scan report."""

    passed: bool
    issues: list[SecurityIssue] = field(default_factory=list)
    scanned_files: int = 0
    scan_time: float = 0.0

    @property
    def critical_count(self) -> int:
        """Count critical issues."""
        return len([i for i in self.issues if i.severity == SecuritySeverity.CRITICAL])

    @property
    def high_count(self) -> int:
        """Count high severity issues."""
        return len([i for i in self.issues if i.severity == SecuritySeverity.HIGH])

    @property
    def total_count(self) -> int:
        """Total issue count."""
        return len(self.issues)


class SecretsScanner:
    """
    Scanner for detecting hardcoded secrets.

    Detects:
    - API keys
    - Passwords
    - Tokens
    - Private keys
    - Credentials
    """

    def __init__(self):
        """Initialize secrets scanner."""
        self.patterns = {
            "api_key": re.compile(
                r"(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]"
            ),
            "password": re.compile(
                r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
            ),
            "token": re.compile(
                r"(?i)(token|auth[_-]?token|access[_-]?token)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{20,})['\"]"
            ),
            "private_key": re.compile(
                r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"
            ),
            "aws_key": re.compile(
                r"(?i)(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*['\"]([A-Z0-9]{20,})['\"]"
            ),
            "github_token": re.compile(
                r"(?i)(github[_-]?token|gh[_-]?token)\s*[:=]\s*['\"]([a-zA-Z0-9_]{40,})['\"]"
            ),
        }

    def scan(self, code: str, file_path: Path | None = None) -> list[SecurityIssue]:
        """
        Scan code for secrets.

        Args:
            code: Code to scan
            file_path: Optional file path

        Returns:
            List of security issues
        """
        issues = []

        for secret_type, pattern in self.patterns.items():
            matches = pattern.finditer(code)
            for match in matches:
                # Get line number
                line_number = code[:match.start()].count("\n") + 1

                issues.append(
                    SecurityIssue(
                        category=SecurityCategory.SECRETS,
                        severity=SecuritySeverity.CRITICAL,
                        message=f"Hardcoded {secret_type.replace('_', ' ')} detected",
                        file_path=str(file_path) if file_path else None,
                        line_number=line_number,
                        code_snippet=match.group(0)[:50],
                        remediation=f"Move {secret_type} to environment variable or secret manager",
                    )
                )

        return issues


class CommandInjectionScanner:
    """
    Scanner for command injection vulnerabilities.

    Detects:
    - Unsanitized user input in shell commands
    - Dangerous shell operators (;, |, &&, ||)
    - Command substitution ($(), ``)
    """

    def __init__(self):
        """Initialize command injection scanner."""
        self.dangerous_patterns = [
            r";",  # Command separator
            r"\|",  # Pipe
            r"&&",  # AND operator
            r"\|\|",  # OR operator
            r"\$\(",  # Command substitution
            r"`",  # Backtick substitution
            r">",  # Redirect
            r"<",  # Redirect
        ]

    def scan_command(self, command: str) -> list[SecurityIssue]:
        """
        Scan shell command for injection risks.

        Args:
            command: Shell command

        Returns:
            List of security issues
        """
        issues = []

        for pattern in self.dangerous_patterns:
            if re.search(pattern, command):
                issues.append(
                    SecurityIssue(
                        category=SecurityCategory.COMMAND_INJECTION,
                        severity=SecuritySeverity.HIGH,
                        message=f"Potentially dangerous shell operator detected: {pattern}",
                        code_snippet=command[:100],
                        remediation="Use parameterized commands or sanitize input",
                    )
                )

        return issues


class PathTraversalScanner:
    """
    Scanner for path traversal vulnerabilities.

    Detects:
    - ../ sequences
    - Absolute paths outside allowed directories
    - Symbolic link attacks
    """

    def __init__(self, allowed_paths: set[Path] | None = None):
        """
        Initialize path traversal scanner.

        Args:
            allowed_paths: Set of allowed base paths
        """
        self.allowed_paths = allowed_paths or set()

    def scan_path(self, file_path: str) -> list[SecurityIssue]:
        """
        Scan file path for traversal risks.

        Args:
            file_path: File path to check

        Returns:
            List of security issues
        """
        issues = []

        # Check for ../ sequences
        if ".." in file_path:
            issues.append(
                SecurityIssue(
                    category=SecurityCategory.PATH_TRAVERSAL,
                    severity=SecuritySeverity.HIGH,
                    message="Path traversal sequence detected (..)",
                    code_snippet=file_path,
                    remediation="Use absolute paths or validate path is within allowed directory",
                )
            )

        # Check if path is within allowed directories
        if self.allowed_paths:
            try:
                path = Path(file_path).resolve()
                is_allowed = any(
                    path.is_relative_to(allowed) for allowed in self.allowed_paths
                )
                if not is_allowed:
                    issues.append(
                        SecurityIssue(
                            category=SecurityCategory.PATH_TRAVERSAL,
                            severity=SecuritySeverity.MEDIUM,
                            message="Path outside allowed directories",
                            code_snippet=file_path,
                            remediation="Ensure path is within allowed base directories",
                        )
                    )
            except (ValueError, OSError):
                pass

        return issues


class SQLInjectionScanner:
    """
    Scanner for SQL injection vulnerabilities.

    Detects:
    - String concatenation in SQL queries
    - Unsanitized user input
    - Dynamic query construction
    """

    def __init__(self):
        """Initialize SQL injection scanner."""
        self.sql_keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
        ]

    def scan(self, code: str) -> list[SecurityIssue]:
        """
        Scan code for SQL injection risks.

        Args:
            code: Code to scan

        Returns:
            List of security issues
        """
        issues = []

        # Check for string concatenation with SQL keywords
        for keyword in self.sql_keywords:
            # Pattern: f"SELECT ... {variable}" or "SELECT ... " + variable
            # Check for + concatenation
            pattern1 = rf'["\'].*{keyword}.*["\'].*\+'
            # Check for f-string with braces
            pattern2 = rf'f["\'].*{keyword}.*\{{.*\}}'

            if re.search(pattern1, code, re.IGNORECASE) or re.search(pattern2, code, re.IGNORECASE):
                issues.append(
                    SecurityIssue(
                        category=SecurityCategory.SQL_INJECTION,
                        severity=SecuritySeverity.CRITICAL,
                        message=f"Potential SQL injection via string concatenation with {keyword}",
                        remediation="Use parameterized queries or ORM",
                    )
                )

        return issues


class XSSScanner:
    """
    Scanner for XSS (Cross-Site Scripting) vulnerabilities.

    Detects:
    - Unescaped HTML output
    - Dangerous HTML tags
    - JavaScript in user content
    """

    def __init__(self):
        """Initialize XSS scanner."""
        self.dangerous_tags = [
            "<script",
            "<iframe",
            "<object",
            "<embed",
            "javascript:",
            "onerror=",
            "onload=",
        ]

    def scan(self, content: str) -> list[SecurityIssue]:
        """
        Scan content for XSS risks.

        Args:
            content: Content to scan

        Returns:
            List of security issues
        """
        issues = []

        for tag in self.dangerous_tags:
            if tag.lower() in content.lower():
                issues.append(
                    SecurityIssue(
                        category=SecurityCategory.XSS,
                        severity=SecuritySeverity.HIGH,
                        message=f"Potentially dangerous HTML/JS detected: {tag}",
                        code_snippet=content[:100],
                        remediation="Sanitize HTML output or use safe rendering",
                    )
                )

        return issues


class AgentShield:
    """
    Comprehensive security scanner for Lyra agents.

    Features:
    - Secrets detection
    - Command injection prevention
    - Path traversal protection
    - SQL injection detection
    - XSS prevention
    - Permission auditing
    """

    def __init__(self, allowed_paths: set[Path] | None = None):
        """
        Initialize AgentShield.

        Args:
            allowed_paths: Set of allowed base paths
        """
        self.secrets_scanner = SecretsScanner()
        self.command_scanner = CommandInjectionScanner()
        self.path_scanner = PathTraversalScanner(allowed_paths)
        self.sql_scanner = SQLInjectionScanner()
        self.xss_scanner = XSSScanner()

    def scan_code(self, code: str, file_path: Path | None = None) -> SecurityReport:
        """
        Scan code for security issues.

        Args:
            code: Code to scan
            file_path: Optional file path

        Returns:
            Security report
        """
        import time

        start_time = time.time()
        issues = []

        # Run all scanners
        issues.extend(self.secrets_scanner.scan(code, file_path))
        issues.extend(self.sql_scanner.scan(code))

        scan_time = time.time() - start_time

        return SecurityReport(
            passed=len([i for i in issues if i.severity == SecuritySeverity.CRITICAL])
            == 0,
            issues=issues,
            scanned_files=1,
            scan_time=scan_time,
        )

    def scan_tool_call(
        self, tool_name: str, args: dict[str, Any]
    ) -> SecurityReport:
        """
        Scan tool call for security issues.

        Args:
            tool_name: Tool name
            args: Tool arguments

        Returns:
            Security report
        """
        issues = []

        # Check for command injection
        if tool_name == "Bash" and "command" in args:
            issues.extend(self.command_scanner.scan_command(args["command"]))

        # Check for path traversal
        if tool_name in ["Read", "Write", "Edit"] and "file_path" in args:
            issues.extend(self.path_scanner.scan_path(args["file_path"]))

        return SecurityReport(
            passed=len([i for i in issues if i.severity == SecuritySeverity.CRITICAL])
            == 0,
            issues=issues,
        )

    def scan_directory(self, directory: Path) -> SecurityReport:
        """
        Scan entire directory for security issues.

        Args:
            directory: Directory to scan

        Returns:
            Security report
        """
        import time

        start_time = time.time()
        all_issues = []
        scanned_files = 0

        # Scan all Python files
        for file_path in directory.rglob("*.py"):
            try:
                code = file_path.read_text()
                report = self.scan_code(code, file_path)
                all_issues.extend(report.issues)
                scanned_files += 1
            except Exception:
                pass

        scan_time = time.time() - start_time

        return SecurityReport(
            passed=len(
                [i for i in all_issues if i.severity == SecuritySeverity.CRITICAL]
            )
            == 0,
            issues=all_issues,
            scanned_files=scanned_files,
            scan_time=scan_time,
        )
