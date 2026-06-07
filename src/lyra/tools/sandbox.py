"""
Sandbox configuration and safety checks for tool execution.

Provides ``SandboxConfig`` for per-execution constraints and helper functions
for validating commands, file paths, and network access against allow/deny
lists.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Pattern, Sequence


# ---------------------------------------------------------------------------
# Deny-list patterns for shell commands
#
# These catch the most common destructive / injection patterns without
# blocking legitimate usage.
# ---------------------------------------------------------------------------

DENYLIST_PATTERNS: List[Pattern[str]] = [
    # Full-filesystem recursion
    re.compile(r"\brm\s+(-[rf]+)?\s*/\s*"),
    re.compile(r"\brm\s+-rf\s+--no-preserve-root\b"),
    re.compile(r"\brm\s+-rf\s+/"),
    # Package-manager destructive flags
    re.compile(r"\b(brew|apt|apt-get|yum|dnf|pacman)\s+(remove|purge|autoremove)"),
    # Curl-to-shell — a classic injection vector
    re.compile(r"\bcurl\s+.*\|\s*(ba?sh|zsh|sh)\b"),
    re.compile(r"\bwget\s+.*\|\s*(ba?sh|zsh|sh)\b"),
    re.compile(r"\b(ba?sh|zsh|sh)\s+[<(<]\s*\(?\s*curl\s+"),
    # Raw mounts and disk operations
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bmkswap\b"),
    # Sudo with destructive flags
    re.compile(r"\bsudo\s+(rm|mkfs|dd|shutdown|reboot|poweroff|chmod\s+777)"),
    # Chmod recursive dangerous
    re.compile(r"\bchmod\s+-R\s+777\b"),
    # Chown recursive
    re.compile(r"\bchown\s+-R\b"),
]

# Default file path denylist (glob-style)
DENY_FILE_PATTERNS: List[str] = [
    "/etc/**",
    "/dev/**",
    "/proc/**",
    "/sys/**",
    "/boot/**",
    "/var/db/**",
]

# Default allow list (tools can only touch these unless overridden)
ALLOW_FILE_PATTERNS: List[str] = [
    "**",
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxConfig:
    """Immutable sandbox constraints for tool execution.

    Attributes:
        workspace_dir: Root directory for file-tool operations.
        allowed_domains: List of domain globs for network tools (e.g. ``*.example.com``).
        timeout_seconds: Default timeout for each tool invocation.
        max_output_bytes: Maximum bytes of stdout/stderr retained.
        allowed_file_patterns: Glob patterns for readable/writable paths.
        denied_file_patterns: Glob patterns for explicitly forbidden paths.
    """

    workspace_dir: str = "."
    allowed_domains: List[str] = field(default_factory=lambda: ["*"])
    timeout_seconds: int = 30
    max_output_bytes: int = 1_048_576  # 1 MiB
    allowed_file_patterns: List[str] = field(default_factory=lambda: ALLOW_FILE_PATTERNS[:])
    denied_file_patterns: List[str] = field(default_factory=lambda: DENY_FILE_PATTERNS[:])


# ---------------------------------------------------------------------------
# Safety check helpers
# ---------------------------------------------------------------------------


def check_path_safety(
    path: str,
    config: SandboxConfig,
    *,
    resolve: bool = True,
) -> Optional[str]:
    """Validate a file path against sandbox rules.

    Returns ``None`` if the path is allowed, or an error message string if
    denied.

    The check resolves ``path`` relative to ``config.workspace_dir`` and then
    runs the result against both the allowed and denied glob lists.
    """
    workspace = Path(config.workspace_dir).resolve()
    target = (workspace / path).resolve() if resolve else Path(path).resolve()

    # Must stay within the workspace
    try:
        target.relative_to(workspace)
    except ValueError:
        return f"Path '{path}' resolves outside workspace '{workspace}'"

    # Check denied patterns first
    for pattern in config.denied_file_patterns:
        if fnmatch.fnmatch(str(target), pattern) or fnmatch.fnmatch(str(target.relative_to(workspace)), pattern):
            return f"Path '{path}' matches denied pattern '{pattern}'"

    # Check allowed patterns
    for pattern in config.allowed_file_patterns:
        if fnmatch.fnmatch(str(target), pattern) or fnmatch.fnmatch(str(target.relative_to(workspace)), pattern):
            return None  # allowed

    return f"Path '{path}' does not match any allowed pattern"


def check_command_safety(command: str, config: SandboxConfig) -> Optional[str]:
    """Check a shell command against the denylist patterns.

    Returns ``None`` if the command is allowed, or an error message if denied.
    """
    for pattern in DENYLIST_PATTERNS:
        if pattern.search(command):
            return f"Command matches denylist pattern: {pattern.pattern}"
    return None


def check_domain_safety(domain: str, config: SandboxConfig) -> Optional[str]:
    """Check a domain/hostname against allowed domains list.

    Supports glob matching (``*``, ``?``).

    Returns ``None`` if allowed, or an error message if denied.
    """
    if "*" in config.allowed_domains:
        return None
    for allowed in config.allowed_domains:
        if fnmatch.fnmatch(domain, allowed):
            return None
    return f"Domain '{domain}' is not in the allowed list: {config.allowed_domains}"
