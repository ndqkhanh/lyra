"""
Security Auditor Skill - Security audit with OWASP Top 10 coverage.

Scans for:
- Secrets and hardcoded credentials
- SQL injection vulnerabilities
- Cross-site scripting (XSS)
- Path traversal
- Insecure deserialization

Returns vulnerability report with severity scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class VulnerabilitySeverity(StrEnum):
    """CVSS-inspired severity levels."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OwaspCategory(StrEnum):
    """OWASP Top 10 categories mapped to findings."""

    A01_BROKEN_ACCESS_CONTROL = "A01: Broken Access Control"
    A02_CRYPTOGRAPHIC_FAILURES = "A02: Cryptographic Failures"
    A03_INJECTION = "A03: Injection"
    A04_INSECURE_DESIGN = "A04: Insecure Design"
    A05_SECURITY_MISCONFIG = "A05: Security Misconfiguration"
    A06_VULNERABLE_COMPONENTS = "A06: Vulnerable Components"
    A07_AUTH_FAILURES = "A07: Identification and Authentication Failures"
    A08_DATA_INTEGRITY = "A08: Software and Data Integrity Failures"
    A09_LOGGING_FAILURES = "A09: Security Logging and Monitoring Failures"
    A10_SSRF = "A10: Server-Side Request Forgery"


@dataclass(frozen=True)
class Vulnerability:
    """A single vulnerability finding."""

    line: int
    severity: VulnerabilitySeverity
    owasp_category: OwaspCategory
    title: str
    description: str
    remediation: str
    code_snippet: str
    cwe_id: str


@dataclass(frozen=True)
class AuditReport:
    """Complete security audit report."""

    file_path: str
    total_lines: int
    vulnerabilities: tuple[Vulnerability, ...]
    summary: dict[str, int]

    @property
    def critical_count(self) -> int:
        return self.summary.get("CRITICAL", 0)

    @property
    def high_count(self) -> int:
        return self.summary.get("HIGH", 0)


class SecurityAuditorSkill:
    """Security audit skill scanning for OWASP Top 10 vulnerabilities."""

    def __init__(self) -> None:
        self._vulnerabilities: list[Vulnerability] = []

    def run(self, input_data: dict) -> dict:
        """Run security audit on the provided source code.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to audit
                - file_path: Optional file path for context (default "unknown")

        Returns:
            Dictionary with audit report data.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "vulnerabilities": [], "summary": {}}

        file_path = input_data.get("file_path", "unknown")
        self._vulnerabilities.clear()

        self._scan_secrets(source)
        self._scan_sql_injection(source)
        self._scan_xss(source)
        self._scan_path_traversal(source)
        self._scan_insecure_deserialization(source)
        self._scan_ssrf(source)
        self._scan_crypto_failures(source)
        self._scan_auth_failures(source)

        summary = self._compute_summary()
        return AuditReport(
            file_path=file_path,
            total_lines=len(source.splitlines()),
            vulnerabilities=tuple(self._vulnerabilities),
            summary=summary,
        ).__dict__ | {"vulnerabilities": [v.__dict__ for v in self._vulnerabilities]}

    def _add_vuln(
        self,
        line: int,
        severity: VulnerabilitySeverity,
        owasp: OwaspCategory,
        title: str,
        description: str,
        remediation: str,
        code_snippet: str,
        cwe_id: str,
    ) -> None:
        self._vulnerabilities.append(
            Vulnerability(
                line=line,
                severity=severity,
                owasp_category=owasp,
                title=title,
                description=description,
                remediation=remediation,
                code_snippet=code_snippet,
                cwe_id=cwe_id,
            )
        )

    def _scan_secrets(self, source: str) -> None:
        """Scan for hardcoded secrets and credentials."""
        patterns: list[tuple[str, str, VulnerabilitySeverity, str, str]] = [
            (
                r'(?:api[_-]?key|apikey|api[_-]?secret)\s*=\s*["\'][A-Za-z0-9_\-]{16,}',
                "Hardcoded API Key",
                VulnerabilitySeverity.CRITICAL,
                "Credentials hardcoded in source code. Use environment variables or a secret manager.",
                "CWE-798",
            ),
            (
                r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{4,}',
                "Hardcoded Password",
                VulnerabilitySeverity.CRITICAL,
                "Password exposed in source code. Store secrets in environment variables.",
                "CWE-798",
            ),
            (
                r'(?:secret|token|auth[_-]?token)\s*=\s*["\'][A-Za-z0-9_\-.\/=+]{16,}',
                "Hardcoded Secret or Token",
                VulnerabilitySeverity.CRITICAL,
                "Authentication token hardcoded. Use vault or environment variables.",
                "CWE-798",
            ),
            (
                r'(?:private[_-]?key|secret[_-]?key)\s*=\s*["\']',
                "Hardcoded Private Key",
                VulnerabilitySeverity.CRITICAL,
                "Private cryptographic key found in source. Store in a secrets vault.",
                "CWE-522",
            ),
        ]
        for pattern, title, severity, description, cwe in patterns:
            for match in re.finditer(pattern, source, re.IGNORECASE):
                line_num = source[: match.start()].count("\n") + 1
                snippet = source.splitlines()[line_num - 1].strip()
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A02_CRYPTOGRAPHIC_FAILURES,
                    title=title,
                    description=description,
                    remediation="Move secrets to environment variables or a secrets manager like HashiCorp Vault.",
                    code_snippet=snippet[:80],
                    cwe_id=cwe,
                )

    def _scan_sql_injection(self, source: str) -> None:
        """Scan for SQL injection vulnerabilities."""
        patterns: list[tuple[str, re.Pattern, VulnerabilitySeverity]] = [
            (
                "String-based SQL query construction",
                re.compile(r'execute\s*\(\s*[f"\'"].*\b(?:SELECT|INSERT|UPDATE|DELETE)\b.*["\']\s*[+%]'),
                VulnerabilitySeverity.CRITICAL,
            ),
            (
                "f-string in SQL query",
                re.compile(r'execute\s*\(\s*f["\']'),
                VulnerabilitySeverity.CRITICAL,
            ),
        ]
        for title, pattern, severity in patterns:
            for match in pattern.finditer(source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A03_INJECTION,
                    title=title,
                    description="SQL query built with string interpolation is vulnerable to injection.",
                    remediation="Use parameterized queries or an ORM. Never concatenate user input into SQL.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-89",
                )

    def _scan_xss(self, source: str) -> None:
        """Scan for cross-site scripting vulnerabilities."""
        patterns: list[tuple[str, str, VulnerabilitySeverity]] = [
            (
                r"innerHTML\s*=",
                "Risky innerHTML assignment",
                VulnerabilitySeverity.HIGH,
            ),
            (
                r"dangerouslySetInnerHTML",
                "React dangerouslySetInnerHTML usage",
                VulnerabilitySeverity.HIGH,
            ),
            (
                r"mark_safe\s*\(",
                "Django mark_safe() usage",
                VulnerabilitySeverity.MEDIUM,
            ),
            (
                r"\|\s*safe\b",
                "Django |safe filter allows raw HTML",
                VulnerabilitySeverity.MEDIUM,
            ),
        ]
        for pattern, title, severity in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A03_INJECTION,
                    title=title,
                    description="Unescaped HTML output may lead to XSS attacks.",
                    remediation="Use safe templating with auto-escaping. Sanitize user input before rendering.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-79",
                )

    def _scan_path_traversal(self, source: str) -> None:
        """Scan for path traversal vulnerabilities."""
        patterns = [
            (
                r"open\s*\(\s*[f\"\'].*[+%]",
                "Path traversal via string concatenation in open()",
                VulnerabilitySeverity.HIGH,
            ),
            (
                r"Path\s*\(\s*[f\"\'].*[+%]",
                "Path traversal via string concatenation in Path()",
                VulnerabilitySeverity.HIGH,
            ),
        ]
        for pattern, title, severity in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A01_BROKEN_ACCESS_CONTROL,
                    title=title,
                    description="User-controlled file path may allow directory traversal.",
                    remediation="Use os.path.realpath() and validate the resolved path is within an allowed directory.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-22",
                )

    def _scan_insecure_deserialization(self, source: str) -> None:
        """Scan for insecure deserialization."""
        patterns = [
            (r"pickle\.loads?\s*\(", "pickle deserialization", VulnerabilitySeverity.CRITICAL),
            (r"yaml\.load\s*\((?![^)]*Loader=SafeLoader)", "Unsafe yaml.load()", VulnerabilitySeverity.CRITICAL),
            (r"marshal\.loads?\s*\(", "marshal deserialization", VulnerabilitySeverity.CRITICAL),
            (r"jsonpickle\.decode\s*\(", "jsonpickle deserialization", VulnerabilitySeverity.HIGH),
        ]
        for pattern, title, severity in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A08_DATA_INTEGRITY,
                    title=title,
                    description="Insecure deserialization can lead to remote code execution.",
                    remediation="Use safe serialization formats (JSON) or restrict allowed classes.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-502",
                )

    def _scan_ssrf(self, source: str) -> None:
        """Scan for server-side request forgery patterns."""
        patterns = [
            (
                r"requests\.(get|post|put|delete)\s*\(\s*[f\"\'].*[+%]",
                "SSRF via string interpolation in HTTP request",
                VulnerabilitySeverity.HIGH,
            ),
            (
                r"urllib\.request\.urlopen\s*\(\s*[f\"\'].*[+%]",
                "SSRF via urllib with dynamic URL",
                VulnerabilitySeverity.HIGH,
            ),
        ]
        for pattern, title, severity in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A10_SSRF,
                    title=title,
                    description="Dynamic URL construction allows SSRF attacks.",
                    remediation="Validate URLs against an allowlist. Restrict outbound network access.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-918",
                )

    def _scan_crypto_failures(self, source: str) -> None:
        """Scan for cryptographic failures."""
        patterns = [
            (
                r"hashlib\.md5\b",
                "Weak hash algorithm (MD5)",
                VulnerabilitySeverity.MEDIUM,
            ),
            (
                r"hashlib\.sha1\b",
                "Weak hash algorithm (SHA-1)",
                VulnerabilitySeverity.MEDIUM,
            ),
            (
                r"Crypto\.Cipher\.(DES|ARC4)",
                "Weak encryption algorithm",
                VulnerabilitySeverity.HIGH,
            ),
        ]
        for pattern, title, severity in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                self._add_vuln(
                    line=line_num,
                    severity=severity,
                    owasp=OwaspCategory.A02_CRYPTOGRAPHIC_FAILURES,
                    title=title,
                    description=f"{title} detected. Cryptographically broken algorithms should not be used.",
                    remediation="Use SHA-256/SHA-3 for hashing and AES-256 for encryption.",
                    code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                    cwe_id="CWE-327",
                )

    def _scan_auth_failures(self, source: str) -> None:
        """Scan for authentication failures."""
        patterns = [
            (r"@login_required", "Django login_required decorator", VulnerabilitySeverity.LOW, False),
            (r"permission_classes\s*=\s*\[\s*\]", "Empty DRF permission classes", VulnerabilitySeverity.HIGH, True),
        ]
        for pattern, title, severity, _ in patterns:
            for match in re.finditer(pattern, source):
                line_num = source[: match.start()].count("\n") + 1
                if severity == VulnerabilitySeverity.HIGH:
                    self._add_vuln(
                        line=line_num,
                        severity=severity,
                        owasp=OwaspCategory.A01_BROKEN_ACCESS_CONTROL,
                        title=title,
                        description="Missing authentication/authorization on endpoint.",
                        remediation="Add proper authentication and permission checks.",
                        code_snippet=source.splitlines()[line_num - 1].strip()[:80],
                        cwe_id="CWE-862",
                    )

    def _compute_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self._vulnerabilities:
            key = v.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts
