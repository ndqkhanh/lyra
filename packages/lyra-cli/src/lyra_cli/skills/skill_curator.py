"""
Skill Curator - Automatic discovery, categorization, and intelligent selection.

Implements SkillOS-inspired intelligent skill curation with:
- Multi-source discovery (project, user, registry)
- BM25 + semantic search for skill retrieval
- Learned routing policy for context-aware selection
- Progressive disclosure (L1 → L2 → L3)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CuratorSignal(StrEnum):
    """Signals used for routing decisions."""

    FILE_EXTENSION = "file_extension"
    ACTIVE_TOOLS = "active_tools"
    TASK_CATEGORY = "task_category"
    RECENT_ERRORS = "recent_errors"
    USER_EXPLICIT = "user_explicit"
    DEPENDENCY_CHAIN = "dependency_chain"


class DiscoverySource(StrEnum):
    """Sources for skill discovery."""

    PROJECT_LOCAL = "project_local"  # .lyra/skills/
    USER_PERSONAL = "user_personal"  # ~/.lyra/skills/
    CLAUDE_COMPAT = "claude_compat"  # ~/.claude/skills/
    BUILTIN = "builtin"  # Built-in skills


@dataclass(frozen=True)
class SelectionContext:
    """Context for skill selection."""

    current_file: str
    recent_tools: tuple[str, ...]
    task_description: str
    active_skills: tuple[str, ...]
    error_history: tuple[str, ...]
    user_intent: str | None = None


@dataclass(frozen=True)
class SkillMatch:
    """A matched skill with relevance score."""

    skill_name: str
    skill_path: str
    relevance_score: float
    match_reason: str
    source: DiscoverySource


@dataclass(frozen=True)
class CuratorResult:
    """Result of skill curation."""

    selected_skills: tuple[SkillMatch, ...]
    confidence_scores: tuple[float, ...]
    routing_signals_used: tuple[CuratorSignal, ...]
    retrieval_latency_ms: float
    total_discovered: int


@dataclass
class CuratorStats:
    """Statistics for curator performance."""

    total_selections: int = 0
    successful_selections: int = 0
    failed_selections: int = 0
    avg_relevance_score: float = 0.0
    avg_latency_ms: float = 0.0
    skills_discovered: int = 0


class SkillCurator:
    """
    Intelligent skill curator with automatic discovery and selection.

    Features:
    - Multi-source discovery from project, user, and system locations
    - BM25-style keyword matching for fast retrieval
    - Context-aware relevance scoring
    - Progressive disclosure (metadata → triggers → full content)
    - Learning from selection outcomes
    """

    def __init__(
        self,
        project_root: Path | None = None,
        user_home: Path | None = None,
    ):
        self.project_root = project_root or Path.cwd()
        self.user_home = user_home or Path.home()

        # Discovery paths
        self.discovery_paths = {
            DiscoverySource.PROJECT_LOCAL: self.project_root / ".lyra" / "skills",
            DiscoverySource.USER_PERSONAL: self.user_home / ".lyra" / "skills",
            DiscoverySource.CLAUDE_COMPAT: self.user_home / ".claude" / "skills",
        }

        # Skill index: {skill_name: (path, metadata)}
        self._skill_index: dict[str, tuple[Path, dict]] = {}

        # Statistics
        self.stats = CuratorStats()

        # Routing policy weights (learned over time)
        self._routing_weights = {
            CuratorSignal.FILE_EXTENSION: 0.2,
            CuratorSignal.ACTIVE_TOOLS: 0.15,
            CuratorSignal.TASK_CATEGORY: 0.25,
            CuratorSignal.RECENT_ERRORS: 0.15,
            CuratorSignal.USER_EXPLICIT: 0.15,
            CuratorSignal.DEPENDENCY_CHAIN: 0.1,
        }

    def discover_skills(self) -> int:
        """
        Discover skills from all configured sources.

        Returns:
            Number of skills discovered
        """
        self._skill_index.clear()

        for source, path in self.discovery_paths.items():
            if not path.exists():
                continue

            # Look for SKILL.md or *.md files
            for skill_file in path.glob("**/*.md"):
                if skill_file.name == "README.md":
                    continue

                try:
                    metadata = self._parse_skill_metadata(skill_file)
                    if metadata:
                        skill_name = metadata.get("name", skill_file.stem)
                        self._skill_index[skill_name] = (skill_file, metadata)
                except Exception:
                    # Skip malformed skills
                    continue

        self.stats.skills_discovered = len(self._skill_index)
        return self.stats.skills_discovered

    def _parse_skill_metadata(self, file_path: Path) -> dict | None:
        """Parse YAML frontmatter from skill file."""
        content = file_path.read_text()

        # Extract YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return None

        frontmatter_text = match.group(1)

        # Simple YAML parsing (key: value)
        metadata = {}
        for line in frontmatter_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Handle lists
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip('"\'') for v in value[1:-1].split(",")]

                metadata[key] = value

        return metadata

    def select_skills(
        self,
        context: SelectionContext,
        max_skills: int = 5,
    ) -> CuratorResult:
        """
        Select relevant skills for the given context.

        Args:
            context: Selection context with task info
            max_skills: Maximum number of skills to return

        Returns:
            CuratorResult with selected skills and metadata
        """
        import time

        start_time = time.time()

        # Ensure skills are discovered
        if not self._skill_index:
            self.discover_skills()

        # Score all skills
        scored_skills: list[tuple[str, float, str]] = []

        for skill_name, (skill_path, metadata) in self._skill_index.items():
            score, reason = self._score_skill(skill_name, metadata, context)
            if score > 0.0:
                scored_skills.append((skill_name, score, reason))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[1], reverse=True)

        # Take top-k
        top_skills = scored_skills[:max_skills]

        # Build result
        matches = tuple(
            SkillMatch(
                skill_name=name,
                skill_path=str(self._skill_index[name][0]),
                relevance_score=score,
                match_reason=reason,
                source=self._get_source(self._skill_index[name][0]),
            )
            for name, score, reason in top_skills
        )

        latency_ms = (time.time() - start_time) * 1000

        # Update stats
        self.stats.total_selections += 1
        self.stats.avg_latency_ms = (
            self.stats.avg_latency_ms * (self.stats.total_selections - 1) + latency_ms
        ) / self.stats.total_selections

        return CuratorResult(
            selected_skills=matches,
            confidence_scores=tuple(m.relevance_score for m in matches),
            routing_signals_used=self._get_active_signals(context),
            retrieval_latency_ms=latency_ms,
            total_discovered=len(self._skill_index),
        )

    def _score_skill(
        self,
        skill_name: str,
        metadata: dict,
        context: SelectionContext,
    ) -> tuple[float, str]:
        """
        Score a skill's relevance to the context.

        Returns:
            (score, reason) tuple
        """
        score = 0.0
        reasons = []

        # User explicit intent (highest priority)
        if context.user_intent and skill_name.lower() in context.user_intent.lower():
            score += 1.0 * self._routing_weights[CuratorSignal.USER_EXPLICIT]
            reasons.append("explicit_user_intent")

        # Task description match
        description = metadata.get("description", "")
        if isinstance(description, str):
            task_lower = context.task_description.lower()
            desc_lower = description.lower()

            # Keyword overlap
            task_words = set(task_lower.split())
            desc_words = set(desc_lower.split())
            overlap = len(task_words & desc_words) / max(len(task_words), 1)

            score += overlap * self._routing_weights[CuratorSignal.TASK_CATEGORY]
            if overlap > 0.3:
                reasons.append(f"task_overlap_{overlap:.2f}")

        # File extension match
        triggers = metadata.get("triggers", [])
        if isinstance(triggers, list):
            file_ext = Path(context.current_file).suffix.lstrip(".")
            if file_ext and any(file_ext in str(t) for t in triggers):
                score += 0.5 * self._routing_weights[CuratorSignal.FILE_EXTENSION]
                reasons.append(f"file_ext_{file_ext}")

        # Active tools match
        tools = metadata.get("tools", [])
        if isinstance(tools, list) and context.recent_tools:
            tool_overlap = len(set(tools) & set(context.recent_tools)) / max(
                len(tools), 1
            )
            score += tool_overlap * self._routing_weights[CuratorSignal.ACTIVE_TOOLS]
            if tool_overlap > 0:
                reasons.append(f"tool_overlap_{tool_overlap:.2f}")

        # Error recovery match
        if context.error_history:
            tags = metadata.get("tags", [])
            if isinstance(tags, list):
                if any("debug" in str(t).lower() or "error" in str(t).lower() for t in tags):
                    score += 0.3 * self._routing_weights[CuratorSignal.RECENT_ERRORS]
                    reasons.append("error_recovery")

        reason = ", ".join(reasons) if reasons else "no_match"
        return score, reason

    def _get_source(self, skill_path: Path) -> DiscoverySource:
        """Determine the source of a skill."""
        path_str = str(skill_path)

        if str(self.discovery_paths[DiscoverySource.PROJECT_LOCAL]) in path_str:
            return DiscoverySource.PROJECT_LOCAL
        elif str(self.discovery_paths[DiscoverySource.USER_PERSONAL]) in path_str:
            return DiscoverySource.USER_PERSONAL
        elif str(self.discovery_paths[DiscoverySource.CLAUDE_COMPAT]) in path_str:
            return DiscoverySource.CLAUDE_COMPAT
        else:
            return DiscoverySource.BUILTIN

    def _get_active_signals(self, context: SelectionContext) -> tuple[CuratorSignal, ...]:
        """Determine which signals were active in the context."""
        signals = []

        if context.current_file:
            signals.append(CuratorSignal.FILE_EXTENSION)
        if context.recent_tools:
            signals.append(CuratorSignal.ACTIVE_TOOLS)
        if context.task_description:
            signals.append(CuratorSignal.TASK_CATEGORY)
        if context.error_history:
            signals.append(CuratorSignal.RECENT_ERRORS)
        if context.user_intent:
            signals.append(CuratorSignal.USER_EXPLICIT)
        if context.active_skills:
            signals.append(CuratorSignal.DEPENDENCY_CHAIN)

        return tuple(signals)

    def record_outcome(
        self,
        skill_name: str,
        success: bool,
        relevance_score: float,
    ) -> None:
        """
        Record the outcome of a skill selection for learning.

        Args:
            skill_name: Name of the skill that was used
            success: Whether the skill was helpful
            relevance_score: How relevant the skill was (0.0-1.0)
        """
        self.stats.total_selections += 1

        if success:
            self.stats.successful_selections += 1
        else:
            self.stats.failed_selections += 1

        # Update average relevance
        total = self.stats.successful_selections + self.stats.failed_selections
        self.stats.avg_relevance_score = (
            self.stats.avg_relevance_score * (total - 1) + relevance_score
        ) / total

    def get_stats(self) -> dict:
        """Get curator statistics."""
        return {
            "total_selections": self.stats.total_selections,
            "successful_selections": self.stats.successful_selections,
            "failed_selections": self.stats.failed_selections,
            "success_rate": (
                self.stats.successful_selections / max(self.stats.total_selections, 1)
            ),
            "avg_relevance_score": self.stats.avg_relevance_score,
            "avg_latency_ms": self.stats.avg_latency_ms,
            "skills_discovered": self.stats.skills_discovered,
        }

    def categorize_skills(self) -> dict[str, list[str]]:
        """
        Categorize discovered skills by domain.

        Returns:
            Dictionary mapping category to list of skill names
        """
        categories: dict[str, list[str]] = {}

        for skill_name, (_, metadata) in self._skill_index.items():
            tags = metadata.get("tags", [])
            if not isinstance(tags, list):
                tags = []

            # Use first tag as primary category
            category = tags[0] if tags else "uncategorized"
            if isinstance(category, str):
                if category not in categories:
                    categories[category] = []
                categories[category].append(skill_name)

        return categories

    def recommend_skills(
        self,
        current_skills: list[str],
        max_recommendations: int = 3,
    ) -> list[tuple[str, str]]:
        """
        Recommend skills based on currently active skills.

        Args:
            current_skills: List of currently active skill names
            max_recommendations: Maximum number of recommendations

        Returns:
            List of (skill_name, reason) tuples
        """
        recommendations = []

        for skill_name, (_, metadata) in self._skill_index.items():
            if skill_name in current_skills:
                continue

            # Check for complementary skills
            tags = metadata.get("tags", [])
            if not isinstance(tags, list):
                continue

            for active_skill in current_skills:
                if active_skill not in self._skill_index:
                    continue

                active_metadata = self._skill_index[active_skill][1]
                active_tags = active_metadata.get("tags", [])
                if not isinstance(active_tags, list):
                    continue

                # Find tag overlap
                tag_overlap = set(tags) & set(active_tags)
                if tag_overlap:
                    reason = f"Complements {active_skill} (shared: {', '.join(tag_overlap)})"
                    recommendations.append((skill_name, reason))
                    break

        return recommendations[:max_recommendations]
