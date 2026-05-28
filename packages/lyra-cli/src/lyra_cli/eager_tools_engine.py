"""Eager Tools - Proactive tool suggestions and recommendations.

Provides context-aware tool suggestions, proactive recommendations,
and intelligent tool chaining.

Features:
- Context analysis
- Tool recommendation
- Proactive suggestions
- Tool chaining
- Usage learning
- Pattern recognition

Usage:
    # Automatic suggestions based on context
    eager = EagerToolEngine()
    suggestions = eager.suggest_tools(context)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ToolCategory(Enum):
    """Tool categories."""

    FILE_OPS = "file_operations"
    CODE_ANALYSIS = "code_analysis"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    SEARCH = "search"


@dataclass
class Tool:
    """A tool definition."""

    name: str
    description: str
    category: ToolCategory
    triggers: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    follows: list[str] = field(default_factory=list)  # Tools that typically follow this one
    confidence: float = 1.0


@dataclass
class ToolSuggestion:
    """A tool suggestion."""

    tool: Tool
    reason: str
    confidence: float
    context_match: float
    urgency: float = 0.5  # 0-1, higher = more urgent


@dataclass
class ToolChain:
    """A sequence of tools that work together."""

    name: str
    tools: list[str]
    description: str
    success_rate: float = 1.0
    usage_count: int = 0


class ContextAnalyzer:
    """
    Analyzes context to understand what the user is trying to do.
    
    Features:
    - Intent detection
    - Entity extraction
    - Pattern matching
    - Context scoring
    """

    def __init__(self):
        """Initialize the context analyzer."""
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> dict[str, list[str]]:
        """Load context patterns.
        
        Returns:
            Dictionary of patterns by intent
        """
        return {
            "testing": [
                r"\btest\b",
                r"\bunit test\b",
                r"\bintegration test\b",
                r"\bfailing\b",
                r"\berror\b",
                r"\bbug\b",
            ],
            "debugging": [
                r"\bdebug\b",
                r"\bbreakpoint\b",
                r"\btrace\b",
                r"\bstack trace\b",
                r"\bcrash\b",
            ],
            "deployment": [
                r"\bdeploy\b",
                r"\brelease\b",
                r"\bproduction\b",
                r"\bstaging\b",
            ],
            "refactoring": [
                r"\brefactor\b",
                r"\bclean up\b",
                r"\breorganize\b",
                r"\bimprove\b",
            ],
            "documentation": [
                r"\bdocument\b",
                r"\bcomment\b",
                r"\bexplain\b",
                r"\bREADME\b",
            ],
            "search": [
                r"\bfind\b",
                r"\bsearch\b",
                r"\blook for\b",
                r"\bwhere is\b",
            ],
        }

    def analyze(self, context: str) -> dict[str, float]:
        """Analyze context and return intent scores.
        
        Args:
            context: Context text
            
        Returns:
            Dictionary of intent scores (0-1)
        """
        scores = {}
        context_lower = context.lower()

        for intent, patterns in self.patterns.items():
            score = 0.0
            matches = 0

            for pattern in patterns:
                if re.search(pattern, context_lower):
                    matches += 1

            if matches > 0:
                score = min(1.0, matches / len(patterns) * 2)

            scores[intent] = score

        return scores

    def extract_entities(self, context: str) -> dict[str, list[str]]:
        """Extract entities from context.
        
        Args:
            context: Context text
            
        Returns:
            Dictionary of entities by type
        """
        entities = {
            "files": [],
            "functions": [],
            "errors": [],
            "commands": [],
        }

        # Extract file paths
        file_pattern = r'\b[\w/.-]+\.(py|js|ts|rs|go|java|cpp|h)\b'
        entities["files"] = re.findall(file_pattern, context)

        # Extract function names
        func_pattern = r'\b[a-z_][a-z0-9_]*\(\)'
        entities["functions"] = re.findall(func_pattern, context)

        # Extract error messages
        error_pattern = r'Error: .+'
        entities["errors"] = re.findall(error_pattern, context)

        # Extract commands
        command_pattern = r'/\w+'
        entities["commands"] = re.findall(command_pattern, context)

        return entities


class ToolRecommender:
    """
    Recommends tools based on context and history.
    
    Features:
    - Context-based recommendations
    - History-based suggestions
    - Tool chaining
    - Confidence scoring
    """

    def __init__(self):
        """Initialize the tool recommender."""
        self.tools = self._load_tools()
        self.chains = self._load_chains()
        self.usage_history: list[tuple[str, datetime]] = []
        self.analyzer = ContextAnalyzer()

    def _load_tools(self) -> list[Tool]:
        """Load available tools.
        
        Returns:
            List of tools
        """
        return [
            Tool(
                name="run_tests",
                description="Run test suite",
                category=ToolCategory.TESTING,
                triggers=["test", "failing", "error"],
                follows=["fix_bug", "refactor"],
            ),
            Tool(
                name="debug",
                description="Start debugger",
                category=ToolCategory.DEBUGGING,
                triggers=["debug", "crash", "error"],
                follows=["run_tests"],
            ),
            Tool(
                name="deploy",
                description="Deploy application",
                category=ToolCategory.DEPLOYMENT,
                triggers=["deploy", "release", "production"],
                prerequisites=["run_tests"],
            ),
            Tool(
                name="refactor",
                description="Refactor code",
                category=ToolCategory.REFACTORING,
                triggers=["refactor", "clean", "improve"],
                follows=["run_tests"],
            ),
            Tool(
                name="document",
                description="Generate documentation",
                category=ToolCategory.DOCUMENTATION,
                triggers=["document", "comment", "explain"],
            ),
            Tool(
                name="search",
                description="Search codebase",
                category=ToolCategory.SEARCH,
                triggers=["find", "search", "where"],
            ),
        ]

    def _load_chains(self) -> list[ToolChain]:
        """Load tool chains.
        
        Returns:
            List of tool chains
        """
        return [
            ToolChain(
                name="test_fix_deploy",
                tools=["run_tests", "fix_bug", "run_tests", "deploy"],
                description="Test, fix, verify, deploy",
            ),
            ToolChain(
                name="refactor_test",
                tools=["refactor", "run_tests"],
                description="Refactor and verify",
            ),
            ToolChain(
                name="debug_fix_test",
                tools=["debug", "fix_bug", "run_tests"],
                description="Debug, fix, verify",
            ),
        ]

    def recommend(self, context: str, limit: int = 5) -> list[ToolSuggestion]:
        """Recommend tools based on context.
        
        Args:
            context: Context text
            limit: Maximum suggestions
            
        Returns:
            List of tool suggestions
        """
        # Analyze context
        intent_scores = self.analyzer.analyze(context)
        entities = self.analyzer.extract_entities(context)

        # Score tools
        suggestions = []

        for tool in self.tools:
            score = self._score_tool(tool, context, intent_scores, entities)

            if score > 0.3:  # Threshold
                suggestion = ToolSuggestion(
                    tool=tool,
                    reason=self._generate_reason(tool, intent_scores, entities),
                    confidence=score,
                    context_match=score,
                )
                suggestions.append(suggestion)

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        return suggestions[:limit]

    def _score_tool(
        self,
        tool: Tool,
        context: str,
        intent_scores: dict[str, float],
        entities: dict[str, list[str]],
    ) -> float:
        """Score a tool for the given context.
        
        Args:
            tool: Tool to score
            context: Context text
            intent_scores: Intent scores
            entities: Extracted entities
            
        Returns:
            Score (0-1)
        """
        score = 0.0
        context_lower = context.lower()

        # Check triggers
        for trigger in tool.triggers:
            if trigger in context_lower:
                score += 0.3

        # Check category match with intents
        category_name = tool.category.value.replace("_", " ")
        for intent, intent_score in intent_scores.items():
            if intent in category_name or category_name in intent:
                score += intent_score * 0.5

        # Boost if recently used
        recent_tools = [t for t, _ in self.usage_history[-5:]]
        if tool.name in recent_tools:
            score += 0.2

        # Boost if follows recent tool
        if recent_tools:
            last_tool = recent_tools[-1]
            for t in self.tools:
                if t.name == last_tool and tool.name in t.follows:
                    score += 0.4

        return min(1.0, score)

    def _generate_reason(
        self,
        tool: Tool,
        intent_scores: dict[str, float],
        entities: dict[str, list[str]],
    ) -> str:
        """Generate reason for suggestion.
        
        Args:
            tool: Tool
            intent_scores: Intent scores
            entities: Extracted entities
            
        Returns:
            Reason string
        """
        reasons = []

        # Check intents
        for intent, score in intent_scores.items():
            if score > 0.5:
                reasons.append(f"Context suggests {intent}")

        # Check entities
        if entities["errors"]:
            reasons.append("Errors detected")

        if entities["files"]:
            reasons.append(f"Working with {len(entities['files'])} files")

        if not reasons:
            reasons.append("Commonly used in this context")

        return "; ".join(reasons)

    def record_usage(self, tool_name: str) -> None:
        """Record tool usage.
        
        Args:
            tool_name: Name of tool used
        """
        self.usage_history.append((tool_name, datetime.now()))

        # Trim history
        if len(self.usage_history) > 100:
            self.usage_history = self.usage_history[-100:]

    def suggest_chain(self, current_tool: str) -> ToolChain | None:
        """Suggest a tool chain based on current tool.
        
        Args:
            current_tool: Current tool being used
            
        Returns:
            Suggested chain or None
        """
        for chain in self.chains:
            if current_tool in chain.tools:
                return chain

        return None


class EagerToolEngine:
    """
    Main engine for eager tool suggestions.
    
    Combines context analysis, tool recommendation, and learning
    to provide proactive tool suggestions.
    """

    def __init__(self):
        """Initialize the eager tool engine."""
        self.recommender = ToolRecommender()
        self.enabled = True

    def suggest_tools(self, context: str, limit: int = 5) -> list[ToolSuggestion]:
        """Suggest tools for the given context.
        
        Args:
            context: Context text
            limit: Maximum suggestions
            
        Returns:
            List of tool suggestions
        """
        if not self.enabled:
            return []

        return self.recommender.recommend(context, limit)

    def record_tool_usage(self, tool_name: str) -> None:
        """Record that a tool was used.
        
        Args:
            tool_name: Name of tool
        """
        self.recommender.record_usage(tool_name)

    def suggest_next_tool(self, current_tool: str) -> ToolSuggestion | None:
        """Suggest next tool in a chain.
        
        Args:
            current_tool: Current tool
            
        Returns:
            Suggestion or None
        """
        chain = self.recommender.suggest_chain(current_tool)

        if chain:
            # Find current position in chain
            try:
                idx = chain.tools.index(current_tool)
                if idx < len(chain.tools) - 1:
                    next_tool_name = chain.tools[idx + 1]

                    # Find tool
                    for tool in self.recommender.tools:
                        if tool.name == next_tool_name:
                            return ToolSuggestion(
                                tool=tool,
                                reason=f"Next step in {chain.name} workflow",
                                confidence=0.9,
                                context_match=0.9,
                                urgency=0.8,
                            )
            except ValueError:
                pass

        return None

    def enable(self) -> None:
        """Enable eager suggestions."""
        self.enabled = True

    def disable(self) -> None:
        """Disable eager suggestions."""
        self.enabled = False


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ToolCategory",
    "Tool",
    "ToolSuggestion",
    "ToolChain",
    "ContextAnalyzer",
    "ToolRecommender",
    "EagerToolEngine",
]
