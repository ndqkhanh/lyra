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

from src.security.agent_shield import (
    AgentShield,
    CommandInjectionScanner,
    PathTraversalScanner,
    SQLInjectionScanner,
    SecretsScanner,
    SecurityCategory,
    SecurityIssue,
    SecurityReport,
    SecuritySeverity,
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
