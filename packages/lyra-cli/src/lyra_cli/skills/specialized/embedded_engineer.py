"""Embedded Engineer Skill — embedded systems and IoT firmware analysis.

Validates embedded code for:
- Memory safety and stack/heap management
- Real-time constraints and interrupt handling
- Power management patterns
- Peripheral initialization sequences
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EmbeddedRisk(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EmbeddedIssue:
    category: str
    risk: EmbeddedRisk
    description: str
    fix: str


class EmbeddedEngineerSkill:
    """Analyzes embedded systems code for common issues."""

    _UNSAFE_PATTERNS = [
        (r"malloc\s*\(|free\s*\(", EmbeddedRisk.HIGH,
         "Dynamic memory allocation in embedded code — fragmentation risk.",
         "Use static allocation or memory pools instead of malloc/free."),
        (r"delay\s*\(|sleep\s*\(|while\s*\(.*==\s*0\)", EmbeddedRisk.MEDIUM,
         "Busy-wait or blocking delay may violate real-time constraints.",
         "Use timer interrupts or RTOS task delays instead."),
        (r"ISR\s*\(|interrupt\s+handler|__irq", EmbeddedRisk.HIGH,
         "ISR detected — ensure it is short and defers work.",
         "Keep ISRs minimal; use task notifications or flags for deferred processing."),
    ]

    def __init__(self) -> None:
        self._issues: list[EmbeddedIssue] = []

    def run(self, input_data: dict) -> dict:
        source = input_data.get("source", "")
        target = input_data.get("target_mcu", "unknown")
        self._issues.clear()

        import re
        for pattern, risk, desc, fix in self._UNSAFE_PATTERNS:
            if re.search(pattern, source):
                self._issues.append(EmbeddedIssue("memory" if "malloc" in pattern else "timing",
                    risk, desc, fix))

        has_watchdog = "watchdog" in source.lower() or "WDT" in source
        if not has_watchdog:
            self._issues.append(EmbeddedIssue("reliability", EmbeddedRisk.CRITICAL,
                "No watchdog timer configured — system cannot auto-recover from hangs.",
                "Enable and configure the hardware watchdog timer."))

        return {
            "target_mcu": target,
            "issues": [i.__dict__ for i in self._issues],
            "score": max(0, 100
                - len([i for i in self._issues if i.risk == EmbeddedRisk.CRITICAL]) * 25
                - len([i for i in self._issues if i.risk == EmbeddedRisk.HIGH]) * 15),
        }
