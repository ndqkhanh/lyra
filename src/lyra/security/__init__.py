"""
Security module for Lyra.

Provides comprehensive security scanning and protection:
- Secrets detection
- Command injection prevention
- Path traversal protection
- SQL injection detection
- XSS prevention
- Permission auditing
"""

from lyra.security.agent_shield import (
    AgentShield,
    CommandInjectionScanner,
    PathTraversalScanner,
    SecretsScanner,
    SecurityCategory,
    SecurityIssue,
    SecurityReport,
    SecuritySeverity,
    SQLInjectionScanner,
    XSSScanner,
)

__version__ = "0.1.0"

__all__ = [
    # Main shield
    "AgentShield",
    # Scanners
    "SecretsScanner",
    "CommandInjectionScanner",
    "PathTraversalScanner",
    "SQLInjectionScanner",
    "XSSScanner",
    # Data types
    "SecurityIssue",
    "SecurityReport",
    "SecuritySeverity",
    "SecurityCategory",
]
