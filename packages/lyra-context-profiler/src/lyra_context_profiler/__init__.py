"""Context Profiler — Real-time environment analysis for optimal skill selection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextProfile:
    task_type: str
    complexity: float
    tools_available: list[str]
    user_preferences: dict[str, float]
    environment_tags: list[str]
    codebase_stats: dict[str, Any] = field(default_factory=dict)


class ContextProfiler:
    """Real-time analysis of task environment."""

    def __init__(self):
        self.history: list[ContextProfile] = []
        self._current: Optional[ContextProfile] = None

    async def analyze(self, task: str, tools: list[str], codebase: dict[str, Any]) -> ContextProfile:
        profile = ContextProfile(
            task_type=self._classify_task(task),
            complexity=self._estimate_complexity(task),
            tools_available=tools,
            user_preferences=self._extract_preferences(codebase),
            environment_tags=self._extract_tags(task, codebase),
            codebase_stats=codebase,
        )
        self._current = profile
        self.history.append(profile)
        return profile

    def _classify_task(self, task: str) -> str:
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["code", "implement", "write", "function", "api"]):
            return "code_generation"
        elif any(kw in task_lower for kw in ["research", "find", "search", "analyze"]):
            return "research"
        elif any(kw in task_lower for kw in ["fix", "bug", "error", "debug"]):
            return "debugging"
        elif any(kw in task_lower for kw in ["plan", "design", "architect"]):
            return "planning"
        else:
            return "general"

    def _estimate_complexity(self, task: str) -> float:
        long_words = len([w for w in task.split() if len(w) > 8])
        return min(1.0, 0.1 + long_words * 0.05)

    def _extract_preferences(self, codebase: dict[str, Any]) -> dict[str, float]:
        prefs = {"verbosity": 0.5, "creativity": 0.5, "conservatism": 0.5}
        if "language" in codebase:
            prefs["language_specificity"] = 0.3
        return prefs

    def _extract_tags(self, task: str, codebase: dict[str, Any]) -> list[str]:
        tags = []
        if "python" in task.lower() or codebase.get("language") == "python":
            tags.append("python")
        if "web" in task.lower():
            tags.append("web")
        if "data" in task.lower():
            tags.append("data")
        return tags

    @property
    def current(self) -> Optional[ContextProfile]:
        return self._current

    def recent_profiles(self, n: int = 5) -> list[ContextProfile]:
        return self.history[-n:]


class ProfileMatcher:
    """Matches context profiles to optimal skill compositions."""

    def __init__(self):
        self.patterns: dict[str, dict[str, float]] = {}

    def register_pattern(self, task_type: str, profile_signature: dict[str, float]) -> None:
        self.patterns[task_type] = profile_signature

    def match(self, profile: ContextProfile) -> str:
        best_type = "general"
        best_score = 0.0
        for task_type, signature in self.patterns.items():
            score = 0.0
            for key, val in signature.items():
                profile_val = getattr(profile, key, 0.0)
                if isinstance(profile_val, (int, float)):
                    score += 1.0 - abs(val - profile_val)
                elif isinstance(profile_val, list):
                    score += sum(1 for x in val if x in profile_val)
            if score > best_score:
                best_score = score
                best_type = task_type
        return best_type
