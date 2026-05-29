"""KnowingDoingDetector — identifies when the model knows about a tool but fails to use it.

Based on the Knowing-Doing Gap research (arXiv 2605.14038): LLMs exhibit a
26.5-54.0% mismatch between knowing a tool exists and actually invoking it.
"""

from .models import GapType, KnowingDoingGap, ViolationSeverity


class KnowingDoingDetector:
    """Detects gaps between tool knowledge and tool execution."""

    _SIGNAL_TOOLS = {
        "search": ["search", "look up", "find", "query", "retrieve"],
        "read": ["read", "open", "load", "fetch", "get file"],
        "write": ["write", "save", "create file", "store", "persist"],
        "execute": ["run", "execute", "compile", "test", "build"],
        "analyze": ["analyze", "examine", "inspect", "review", "check"],
    }

    def __init__(self, sensitivity: float = 0.6):
        self._gaps: dict[str, KnowingDoingGap] = {}
        self._sensitivity = sensitivity

    def analyze(
        self,
        tool_registry: set[str],
        tool_calls_made: set[str],
        context: str = "",
    ) -> list[KnowingDoingGap]:
        """Detect gaps between available tools and tools actually called."""
        import uuid

        gaps: list[KnowingDoingGap] = []
        context_lower = context.lower()

        for tool_name, signals in self._SIGNAL_TOOLS.items():
            if tool_name in tool_calls_made:
                continue

            tool_available = any(t for t in tool_registry if tool_name in t.lower())
            if not tool_available:
                continue

            for signal in signals:
                if signal in context_lower:
                    gap = KnowingDoingGap(
                        id=str(uuid.uuid4()),
                        gap_type=GapType.MISSED_TOOL,
                        tool_name=tool_name,
                        context=context[:300],
                        expected_call=f"{tool_name}(...)",
                        actual_behavior=(
                            f"Context mentions '{signal}' but {tool_name} was not called"
                        ),
                        severity=ViolationSeverity.HIGH,
                    )
                    self._gaps[gap.id] = gap
                    gaps.append(gap)
                    break

        return gaps

    def detect_wrong_tool(
        self,
        intent: str,
        called_tool: str,
        available_tools: set[str],
    ) -> KnowingDoingGap | None:
        """Detect when the wrong tool was called for a given intent."""
        import uuid

        intent_lower = intent.lower()
        best_match = None
        best_signal_count = 0

        for tool_name, signals in self._SIGNAL_TOOLS.items():
            signal_count = sum(1 for s in signals if s in intent_lower)
            if signal_count > best_signal_count and tool_name != called_tool:
                best_signal_count = signal_count
                best_match = tool_name

        if best_match and best_match in available_tools and best_signal_count >= 2:
            gap = KnowingDoingGap(
                id=str(uuid.uuid4()),
                gap_type=GapType.WRONG_TOOL,
                tool_name=best_match,
                context=f"Intent: {intent[:200]}",
                expected_call=f"{best_match}(...)",
                actual_behavior=f"Called {called_tool} instead of {best_match}",
                severity=ViolationSeverity.MEDIUM,
            )
            self._gaps[gap.id] = gap
            return gap
        return None

    def gap_summary(self) -> dict:
        """Return aggregate gap statistics."""
        if not self._gaps:
            return {"total_gaps": 0, "by_type": {}, "by_severity": {}}

        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for gap in self._gaps.values():
            by_type[gap.gap_type.value] = by_type.get(gap.gap_type.value, 0) + 1
            by_severity[gap.severity.value] = by_severity.get(gap.severity.value, 0) + 1

        return {
            "total_gaps": len(self._gaps),
            "by_type": by_type,
            "by_severity": by_severity,
        }

    @property
    def gap_count(self) -> int:
        return len(self._gaps)
