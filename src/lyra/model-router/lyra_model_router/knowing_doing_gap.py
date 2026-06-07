"""Detect when a model knows about tools but fails to use them."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GapReport:
    """Report on a detected knowing-doing gap.

    Attributes:
        has_gap: Whether a gap was detected.
        missing_tools: Tuple of tool names that should have been called.
        recommendation: Suggested action to address the gap.
    """
    has_gap: bool
    missing_tools: tuple[str, ...]
    recommendation: str


# Keywords that suggest particular tools should be called
_TOOL_SIGNALS: dict[str, tuple[str, ...]] = {
    "web_search": (
        "search", "find", "look up", "latest", "current", "news",
        "what is", "who is", "internet",
    ),
    "code_execution": (
        "run", "execute", "calculate", "compute", "compile",
        "simulate", "benchmark",
    ),
    "file_operations": (
        "read file", "write file", "save", "load", "create file",
        "open", "parse file",
    ),
    "data_query": (
        "query", "database", "select", "fetch", "retrieve",
        "get data", "lookup",
    ),
    "verification": (
        "verify", "validate", "check", "confirm", "double-check",
        "fact-check", "cross-reference",
    ),
    "api_call": (
        "call api", "api request", "http", "post request",
        "get request", "rest",
    ),
}


class KnowingDoingGapDetector:
    """Detects gaps between what a model knows and what it does.

    Analyzes task descriptions against expected tool usage to identify
    situations where tools should have been invoked but weren't.
    """

    async def detect_gap(
        self,
        task_description: str,
        tool_calls_made: tuple[str, ...] = (),
        expected_tools: tuple[str, ...] = (),
    ) -> GapReport:
        """Detect whether a knowing-doing gap exists.

        Args:
            task_description: Description of the task.
            tool_calls_made: Tuple of tool names that were actually called.
            expected_tools: Tuple of tools that were expected. If empty,
                tool signals are inferred from the task description.

        Returns:
            A GapReport indicating whether a gap was found.
        """
        # Determine expected tools if not provided
        if not expected_tools:
            expected_tools = self._infer_expected_tools(task_description)

        if not expected_tools:
            return GapReport(
                has_gap=False,
                missing_tools=(),
                recommendation="No tools appear necessary for this task.",
            )

        # Find which expected tools were not called
        made_set = set(tool_calls_made)
        missing: tuple[str, ...] = tuple(
            tool for tool in expected_tools if tool not in made_set
        )

        if not missing:
            return GapReport(
                has_gap=False,
                missing_tools=(),
                recommendation="All expected tools were called.",
            )

        recommendation = self._build_recommendation(missing)
        return GapReport(
            has_gap=True,
            missing_tools=missing,
            recommendation=recommendation,
        )

    def _infer_expected_tools(self, description: str) -> tuple[str, ...]:
        """Infer expected tools from a task description using keyword matching."""
        lower = description.lower()
        expected: list[str] = []
        for tool, keywords in _TOOL_SIGNALS.items():
            for kw in keywords:
                if kw in lower:
                    expected.append(tool)
                    break
        return tuple(expected)

    @staticmethod
    def _build_recommendation(missing: tuple[str, ...]) -> str:
        """Build a human-readable recommendation."""
        if len(missing) == 1:
            return f"Consider calling the '{missing[0]}' tool to complete this task."
        tools_list = ", ".join(f"'{t}'" for t in missing)
        return (
            f"Consider calling these tools to complete this task: {tools_list}. "
            "The task description suggests they are needed."
        )
