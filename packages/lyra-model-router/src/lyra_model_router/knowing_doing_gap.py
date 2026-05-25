"""Detect when an agent should use tools but may skip them.

Analyzes task requirements against available tools to identify knowing-doing gaps
where the agent is likely to attempt a task without using necessary tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .capability_analyzer import DomainType, TaskProfile


class ToolCategory(Enum):
    """Categories of tools that agents may need."""
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    FILE_OPERATIONS = "file_operations"
    DATA_QUERY = "data_query"
    API_CALL = "api_call"
    COMPUTATION = "computation"
    VERIFICATION = "verification"
    EXTERNAL_KNOWLEDGE = "external_knowledge"
    DOCUMENT_PARSING = "document_parsing"
    IMAGE_PROCESSING = "image_processing"


@dataclass(frozen=True)
class ToolNecessitySignal:
    """A signal indicating a specific tool category is needed for a task."""
    category: ToolCategory
    confidence: float  # 0.0-1.0
    signal_source: str  # What triggered this signal
    recommended_tools: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GapRecommendation:
    """Recommendation to address a knowing-doing gap."""
    tool_category: ToolCategory
    gap_severity: float  # 0.0-1.0
    reason: str
    suggested_action: str
    confidence: float = 0.0

    def __lt__(self, other: GapRecommendation) -> bool:
        return self.gap_severity < other.gap_severity


# Patterns that suggest tool usage is needed
_TOOL_NEEDS_PATTERNS: dict[ToolCategory, list[re.Pattern[str]]] = {
    ToolCategory.WEB_SEARCH: [
        re.compile(r"(get|fetch|search|look up|find)\s.*(latest|current|recent|news|price|weather)"),
        re.compile(r"(who|what|when|where)\s+(is|are|was|were)\s+(the|a|an)"),
        re.compile(r"internet\s+(search|lookup|query)"),
        re.compile(r"real.?time\s+(data|info|information|price|stock)"),
    ],
    ToolCategory.CODE_EXECUTION: [
        re.compile(r"(run|execute|compile|interpret)\s.*(code|script|program)"),
        re.compile(r"calculate\s+"),
        re.compile(r"compute\s+"),
        re.compile(r"algorithm"),
        re.compile(r"simulat"),
    ],
    ToolCategory.DATA_QUERY: [
        re.compile(r"(query|search|lookup|find)\s.*(database|db|data|record)"),
        re.compile(r"(get|retrieve|fetch)\s.*(user|customer|order|transaction)"),
        re.compile(r"SELECT\s+.*\s+FROM"),
    ],
    ToolCategory.COMPUTATION: [
        re.compile(r"(calculate|compute|solve|evaluate)\s+(the|this|an)"),
        re.compile(r"\d+\s*[+\-*/]\s*\d+"),
        re.compile(r"equation"),
        re.compile(r"formula"),
    ],
    ToolCategory.VERIFICATION: [
        re.compile(r"(verify|validate|check|confirm|ensure)\s+(the|that|if)"),
        re.compile(r"(double.?check|cross.?reference|fact.?check)"),
        re.compile(r"test\s+(the|this|that)"),
    ],
    ToolCategory.EXTERNAL_KNOWLEDGE: [
        re.compile(r"(research|analyze|investigate|study)\s+(the|this)"),
        re.compile(r"compare\s+"),
        re.compile(r"what\s+is\s+(the|a|an)"),
        re.compile(r"tell\s+me\s+about"),
    ],
    ToolCategory.FILE_OPERATIONS: [
        re.compile(r"(read|write|save|load|open|create)\s.*file"),
        re.compile(r"files?\.(txt|json|csv|yaml|toml|md)"),
        re.compile(r"(read|parse|process)\s.*document"),
    ],
    ToolCategory.API_CALL: [
        re.compile(r"call\s+(an\s+)?api"),
        re.compile(r"(get|post|put|delete)\s+https?://"),
        re.compile(r"(fetch|request)\s+data\s+from"),
    ],
    ToolCategory.DOCUMENT_PARSING: [
        re.compile(r"(parse|extract|read)\s.*(pdf|docx|xlsx|html|xml)"),
        re.compile(r"(summarize|summarise)\s.*(document|article|page)"),
    ],
    ToolCategory.IMAGE_PROCESSING: [
        re.compile(r"(analyze|process|read)\s.*(image|picture|photo|screenshot)"),
        re.compile(r"(ocr|extract text from image)"),
    ],
}

# Task domain to tool category mapping
_DOMAIN_TOOL_MAPPING: dict[DomainType, set[ToolCategory]] = {
    DomainType.CODING: {ToolCategory.CODE_EXECUTION, ToolCategory.FILE_OPERATIONS, ToolCategory.VERIFICATION},
    DomainType.REASONING: {ToolCategory.EXTERNAL_KNOWLEDGE, ToolCategory.COMPUTATION},
    DomainType.RESEARCH: {ToolCategory.WEB_SEARCH, ToolCategory.EXTERNAL_KNOWLEDGE, ToolCategory.DOCUMENT_PARSING, ToolCategory.DATA_QUERY},
    DomainType.ANALYSIS: {ToolCategory.COMPUTATION, ToolCategory.DATA_QUERY, ToolCategory.VERIFICATION},
    DomainType.CREATIVE: {ToolCategory.FILE_OPERATIONS, ToolCategory.IMAGE_PROCESSING},
    DomainType.SUMMARIZATION: {ToolCategory.DOCUMENT_PARSING, ToolCategory.FILE_OPERATIONS},
    DomainType.EXTRACTION: {ToolCategory.DOCUMENT_PARSING, ToolCategory.DATA_QUERY},
    DomainType.CLASSIFICATION: {ToolCategory.COMPUTATION, ToolCategory.VERIFICATION},
    DomainType.PLANNING: {ToolCategory.EXTERNAL_KNOWLEDGE, ToolCategory.WEB_SEARCH, ToolCategory.COMPUTATION},
    DomainType.CONVERSATION: set(),
}


class KnowingDoingGapDetector:
    """Detects knowing-doing gaps where agents should use tools but might skip them.

    Analyzes task descriptions and profiles to identify tool categories that would
    be beneficial, generates severity-scored recommendations, and provides a
    composite gap severity assessment.
    """

    def __init__(self, available_tools: set[ToolCategory] | None = None) -> None:
        self._available_tools: set[ToolCategory] = available_tools or set()
        self._detection_patterns = _TOOL_NEEDS_PATTERNS.copy()
        self._domain_mapping = _DOMAIN_TOOL_MAPPING.copy()

    @property
    def available_tools(self) -> set[ToolCategory]:
        return self._available_tools.copy()

    def register_tool(self, category: ToolCategory) -> None:
        """Register an available tool category."""
        self._available_tools.add(category)

    def register_tools(self, categories: set[ToolCategory]) -> None:
        """Register multiple available tool categories."""
        self._available_tools.update(categories)

    def remove_tool(self, category: ToolCategory) -> bool:
        """Remove a tool from available set. Returns True if was present."""
        if category in self._available_tools:
            self._available_tools.discard(category)
            return True
        return False

    def detect_tool_signals(self, task_description: str) -> list[ToolNecessitySignal]:
        """Scan a task description for signals that tools are needed."""
        signals: list[ToolNecessitySignal] = []
        seen: set[ToolCategory] = set()
        lower_desc = task_description.lower()

        for category, patterns in self._detection_patterns.items():
            match_count = 0
            for pattern in patterns:
                if pattern.search(lower_desc):
                    match_count += 1
            if match_count > 0:
                confidence = min(1.0, match_count * 0.4)
                signals.append(ToolNecessitySignal(
                    category=category,
                    confidence=confidence,
                    signal_source=f"pattern_match_{category.value}",
                    recommended_tools=(category.value,),
                ))
                seen.add(category)
        return signals

    def detect_domain_gaps(
        self,
        task: TaskProfile,
    ) -> list[GapRecommendation]:
        """Detect gaps between domain tool requirements and available tools."""
        recommendations: list[GapRecommendation] = []
        needed_tools = self._domain_mapping.get(task.domain, set())
        for needed in needed_tools:
            if needed not in self._available_tools:
                severity = self._compute_gap_severity(task, needed)
                recommendations.append(GapRecommendation(
                    tool_category=needed,
                    gap_severity=severity,
                    reason=f"Task domain '{task.domain.value}' typically requires '{needed.value}' tool",
                    suggested_action=f"Ensure '{needed.value}' tool is available for this task",
                    confidence=min(1.0, severity + 0.2),
                ))
        recommendations.sort(reverse=True)
        return recommendations

    def detect_text_gaps(
        self,
        task_description: str,
    ) -> list[GapRecommendation]:
        """Detect gaps by analyzing task description text for tool signals."""
        signals = self.detect_tool_signals(task_description)
        recommendations: list[GapRecommendation] = []
        for signal in signals:
            if signal.category not in self._available_tools:
                gap_severity = 0.3 + signal.confidence * 0.5
                recommendations.append(GapRecommendation(
                    tool_category=signal.category,
                    gap_severity=min(1.0, gap_severity),
                    reason=f"Task text suggests '{signal.category.value}' tool is needed but unavailable",
                    suggested_action=f"Add '{signal.category.value}' tool capability",
                    confidence=signal.confidence,
                ))
        recommendations.sort(reverse=True)
        return recommendations

    def analyze(
        self,
        task: TaskProfile,
        task_description: str = "",
    ) -> list[GapRecommendation]:
        """Full gap analysis combining domain and text analysis."""
        domain_gaps = self.detect_domain_gaps(task)
        text_gaps = self.detect_text_gaps(task_description) if task_description else []
        merged = self._merge_recommendations(domain_gaps, text_gaps)
        merged.sort(reverse=True)
        return merged

    def composite_gap_score(self, recommendations: list[GapRecommendation]) -> float:
        """Compute a composite gap severity score across all recommendations."""
        if not recommendations:
            return 0.0
        return sum(r.gap_severity * r.confidence for r in recommendations) / len(recommendations)

    def top_gaps(self, recommendations: list[GapRecommendation], k: int = 3) -> list[GapRecommendation]:
        """Return the top-k most severe gaps."""
        return sorted(recommendations, reverse=True)[:k]

    def _compute_gap_severity(self, task: TaskProfile, category: ToolCategory) -> float:
        """Compute gap severity for a specific tool category and task."""
        base = 0.5
        if task.complexity_score > 0.6:
            base += 0.2
        if category in (
            ToolCategory.CODE_EXECUTION,
            ToolCategory.WEB_SEARCH,
            ToolCategory.DATA_QUERY,
        ):
            base += 0.15
        return min(1.0, base)

    @staticmethod
    def _merge_recommendations(
        domain_gaps: list[GapRecommendation],
        text_gaps: list[GapRecommendation],
    ) -> list[GapRecommendation]:
        """Merge domain and text gap recommendations, deduplicating by category."""
        merged: dict[ToolCategory, GapRecommendation] = {}
        for rec in domain_gaps + text_gaps:
            if rec.tool_category not in merged or rec.gap_severity > merged[rec.tool_category].gap_severity:
                merged[rec.tool_category] = rec
        return list(merged.values())
