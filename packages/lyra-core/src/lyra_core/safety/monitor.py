"""Continuous safety monitor.

v1 is a rule-based scanner. Each observation is matched against a pattern
set; duplicates inside the rolling window are suppressed. A future v1.5 can
swap in an LLM classifier without changing this surface.
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass

_INJECTION_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore (?:all )?previous instructions", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
)
_SABOTAGE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"commented-out", re.IGNORECASE),
    re.compile(r"-\s*assert\b.*->\s*commented", re.IGNORECASE),
    re.compile(r"disabled\s+test\b", re.IGNORECASE),
    re.compile(r"skip(?:ped)?\s+the\s+test", re.IGNORECASE),
)
_SECRET_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----"),
)


@dataclass
class SafetyFlag:
    kind: str            # prompt_injection | sabotage_pattern | secret_exposure
    confidence: float    # 0..1
    evidence: str        # substring or summary

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "confidence": self.confidence, "evidence": self.evidence}


class SafetyMonitor:
    def __init__(self, *, window: int = 5) -> None:
        self._window: collections.deque[str] = collections.deque(maxlen=window)
        self._flags: list[SafetyFlag] = []
        self._seen: set[tuple[str, str]] = set()  # (kind, evidence)

    # ------------------------------------------------------------------ scan
    def observe(self, text: str) -> None:
        self._window.append(text)
        for pat in _INJECTION_RES:
            m = pat.search(text)
            if m:
                self._maybe_flag(
                    SafetyFlag(
                        kind="prompt_injection",
                        confidence=0.9,
                        evidence=m.group(0),
                    )
                )
        for pat in _SABOTAGE_RES:
            m = pat.search(text)
            if m:
                self._maybe_flag(
                    SafetyFlag(
                        kind="sabotage_pattern",
                        confidence=0.75,
                        evidence=m.group(0),
                    )
                )
        for pat in _SECRET_RES:
            m = pat.search(text)
            if m:
                self._maybe_flag(
                    SafetyFlag(
                        kind="secret_exposure",
                        confidence=0.95,
                        evidence="<redacted-credential>",
                    )
                )

    def _maybe_flag(self, flag: SafetyFlag) -> None:
        key = (flag.kind, flag.evidence)
        if key in self._seen:
            return
        self._seen.add(key)
        self._flags.append(flag)

    # ------------------------------------------------------------------ read
    def flags(self) -> list[SafetyFlag]:
        return list(self._flags)
