"""Cross-channel evidence checks: catch sabotage (e.g., commented-out
assertions in tests that claim to pass).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_COMMENTED_ASSERT = re.compile(r"^\s*#\s*assert\b", re.MULTILINE)
_COMMENTED_RAISE = re.compile(r"^\s*#\s*raise\b", re.MULTILINE)
_BARE_PASS_BODY = re.compile(r"\bdef\s+test_\w+\s*\([^)]*\)\s*:\s*\n(?:\s*#[^\n]*\n)*\s*pass\s*$", re.MULTILINE)


@dataclass
class CrossChannelFinding:
    test_id: str
    reason: str


def cross_channel_check(
    *, acceptance_tests_passed: list[str], repo_root: Path
) -> list[CrossChannelFinding]:
    findings: list[CrossChannelFinding] = []
    for tid in acceptance_tests_passed:
        if "::" not in tid:
            continue
        path_str, _node = tid.split("::", 1)
        p = Path(path_str)
        if not p.is_absolute():
            p = repo_root / p
        if not p.exists():
            findings.append(
                CrossChannelFinding(
                    test_id=tid, reason=f"test file not found: {p}"
                )
            )
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            findings.append(
                CrossChannelFinding(
                    test_id=tid, reason=f"cannot read test file {p}: {e}"
                )
            )
            continue
        if _COMMENTED_ASSERT.search(body):
            findings.append(
                CrossChannelFinding(
                    test_id=tid,
                    reason=(
                        "commented-out assertion detected; "
                        "test may pass vacuously"
                    ),
                )
            )
            continue
        if _COMMENTED_RAISE.search(body):
            findings.append(
                CrossChannelFinding(
                    test_id=tid,
                    reason="commented-out raise detected; test body disabled",
                )
            )
            continue
        if _BARE_PASS_BODY.search(body):
            findings.append(
                CrossChannelFinding(
                    test_id=tid, reason="test body is `pass`; no assertion"
                )
            )
    return findings
