"""secrets-scan hook.

Blocks tool calls whose args contain common secret patterns. Pre-tool-use only.
Intentionally conservative: false positives are preferable to leaking.

Patterns covered (Phase 1):
    - AWS Access Key (AKIA... / ASIA... / AIDA...)
    - GitHub personal access token (ghp_, gho_, ghu_, ghs_, ghr_)
    - Slack bot token (xoxb-)
    - Generic RSA private key block
    - Stripe secret key (sk_live_, sk_test_)
    - Google API key (AIza...)
    - Generic bearer token in shell args (heuristic)
"""
from __future__ import annotations

import re

from harness_core.hooks import HookDecision
from harness_core.messages import ToolCall, ToolResult

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AIDA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("slack_bot_token", re.compile(r"\bxox[bpaor]-[A-Za-z0-9-]{10,}\b")),
    ("rsa_private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----")),
    ("stripe_secret", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    (
        "generic_bearer",
        re.compile(r"[Bb]earer\s+[A-Za-z0-9_\-\.=]{20,}", re.MULTILINE),
    ),
)


def _scan_blob(blob: str) -> tuple[str, str] | None:
    for name, pat in _PATTERNS:
        m = pat.search(blob)
        if m:
            return name, m.group(0)[:24] + "…"
    return None


def secrets_scan_hook(call: ToolCall, _result: ToolResult | None) -> HookDecision:
    """Block the call if any arg value contains a known secret pattern."""
    for key, value in call.args.items():
        if not isinstance(value, (str, bytes)):
            # JSON dumps will render but flatten — scan via a coarse string render
            value = repr(value)
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", "replace")
            except Exception:
                continue
        hit = _scan_blob(value)
        if hit:
            name, sample = hit
            return HookDecision(
                block=True,
                reason=f"secrets-scan: detected {name} in arg {key!r} (sample={sample!r})",
            )
    return HookDecision(block=False)
