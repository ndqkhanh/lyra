"""Trust banners + injection guard for third-party MCP output."""
from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_RE = re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE)
_IGNORE_RE = re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE)


@dataclass
class TrustBanner:
    server_name: str
    tier: str = "third-party"


@dataclass
class GuardResult:
    blocked: bool
    reason: str = ""


def wrap_with_trust_banner(*, server_name: str, content: str) -> str:
    return f"[third-party server: {server_name}] {content}"


def guard_third_party_content(content: str) -> GuardResult:
    if _INJECTION_RE.search(content):
        return GuardResult(blocked=True, reason="contains <system> tag")
    if _IGNORE_RE.search(content):
        return GuardResult(blocked=True, reason="contains 'ignore previous instructions'")
    return GuardResult(blocked=False)
