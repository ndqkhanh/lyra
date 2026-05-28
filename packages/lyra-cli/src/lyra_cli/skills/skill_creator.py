"""
Skill Creator - Automatic skill generation from execution patterns.

Implements SkillX-inspired automatic skill construction with:
- Pattern extraction from execution traces
- SKILL.md generation with proper frontmatter
- Quality filtering and validation
- CASCADE-style cumulative building
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Optional
import hashlib
import re


class PatternType(StrEnum):
    """Types of patterns that can be extracted."""

    DECISION_POINT = "decision_point"
    ERROR_RECOVERY = "error_recovery"
    TOOL_SEQUENCE = "tool_sequence"
    DOMAIN_HEURISTIC = "domain_heuristic"
    COMMUNICATION = "communication"


class CreationSource(StrEnum):
    """Source of skill creation."""

    SINGLE_TRACE = "single_trace"
    MULTI_TRACE = "multi_trace"
    CASCADE_BUILT = "cascade_built"
    USER_INITIATED = "user_initiated"


@dataclass(frozen=True)
class ExecutionTrace:
    """A captured execution trace."""

    trace_id: str
    task_description: str
    steps: tuple[str, ...]
    tools_used: tuple[str, ...]
    success: bool
    duration_ms: float
    tokens_used: int
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ExtractedPattern:
    """A pattern extracted from execution traces."""

    pattern_type: PatternType
    description: str
    trigger_conditions: tuple[str, ...]
    steps: tuple[str, ...]
    confidence: float  # 0.0-1.0
    occurrence_count: int
    source_traces: tuple[str, ...]


@dataclass(frozen=True)
class SkillProposal:
    """A proposed new skill."""

    name: str
    description: str
    category: str
    patterns: tuple[ExtractedPattern, ...]
    triggers: tuple[str, ...]
    tags: tuple[str, ...]
    tools: tuple[str, ...]
    content: str  # Full SKILL.md content
    confidence: float
    novelty_score: float  # How different from existing skills
    source: CreationSource
    source_traces: tuple[str, ...]


@dataclass
class CreatorStats:
    """Statistics for skill creator."""

    total_traces_analyzed: int = 0
    patterns_extracted: int = 0
    skills_proposed: int = 0
    skills_accepted: int = 0
    skills_rejected: int = 0
    avg_confidence: float = 0.0


class SkillCreator:
    """
    Automatic skill creation from execution patterns.

    Features:
    - Extract reusable patterns from successful executions
    - Generate SKILL.md with proper frontmatter
    - Quality filtering (confidence, novelty, generality)
    - CASCADE-style cumulative building
    """

    def __init__(self, min_confidence: float = 0.7, min_novelty: float = 0.3):
        self.min_confidence = min_confidence
        self.min_novelty = min_novelty

        # Pattern database
        self._patterns: dict[str, ExtractedPattern] = {}

        # Existing skills (for novelty checking)
        self._existing_skills: set[str] = set()

        # Statistics
        self.stats = CreatorStats()

    def analyze_trace(self, trace: ExecutionTrace) -> list[ExtractedPattern]:
        """
        Analyze an execution trace and extract patterns.

        Args:
            trace: Execution trace to analyze

        Returns:
            List of extracted patterns
        """
        self.stats.total_traces_analyzed += 1

        if not trace.success:
            return []  # Only learn from successful executions

        patterns = []

        # Extract tool sequences
        if len(trace.tools_used) >= 2:
            pattern = self._extract_tool_sequence(trace)
            if pattern:
                patterns.append(pattern)

        # Extract decision points
        decision_patterns = self._extract_decision_points(trace)
        patterns.extend(decision_patterns)

        # Extract error recovery (if there were errors but still succeeded)
        if trace.error_message and trace.success:
            pattern = self._extract_error_recovery(trace)
            if pattern:
                patterns.append(pattern)

        # Extract domain heuristics
        heuristic_patterns = self._extract_domain_heuristics(trace)
        patterns.extend(heuristic_patterns)

        # Store patterns
        for pattern in patterns:
            pattern_id = self._generate_pattern_id(pattern)
            if pattern_id in self._patterns:
                # Increment occurrence count
                existing = self._patterns[pattern_id]
                self._patterns[pattern_id] = ExtractedPattern(
                    pattern_type=existing.pattern_type,
                    description=existing.description,
                    trigger_conditions=existing.trigger_conditions,
                    steps=existing.steps,
                    confidence=existing.confidence,
                    occurrence_count=existing.occurrence_count + 1,
                    source_traces=existing.source_traces + (trace.trace_id,),
                )
            else:
                self._patterns[pattern_id] = pattern

        self.stats.patterns_extracted += len(patterns)

        return patterns

    def _extract_tool_sequence(self, trace: ExecutionTrace) -> Optional[ExtractedPattern]:
        """Extract tool sequence pattern."""
        if len(trace.tools_used) < 2:
            return None

        # Look for repeated tool sequences
        tools = trace.tools_used
        sequence = " → ".join(tools[:3])  # First 3 tools

        return ExtractedPattern(
            pattern_type=PatternType.TOOL_SEQUENCE,
            description=f"Tool sequence: {sequence}",
            trigger_conditions=(f"task involves {tools[0]}",),
            steps=tuple(f"Use {tool}" for tool in tools[:3]),
            confidence=0.8,
            occurrence_count=1,
            source_traces=(trace.trace_id,),
        )

    def _extract_decision_points(self, trace: ExecutionTrace) -> list[ExtractedPattern]:
        """Extract decision point patterns."""
        patterns = []

        # Look for conditional logic in steps
        for i, step in enumerate(trace.steps):
            if any(keyword in step.lower() for keyword in ["if", "when", "check"]):
                patterns.append(
                    ExtractedPattern(
                        pattern_type=PatternType.DECISION_POINT,
                        description=f"Decision: {step[:50]}...",
                        trigger_conditions=(f"step {i+1}",),
                        steps=(step,),
                        confidence=0.7,
                        occurrence_count=1,
                        source_traces=(trace.trace_id,),
                    )
                )

        return patterns

    def _extract_error_recovery(self, trace: ExecutionTrace) -> Optional[ExtractedPattern]:
        """Extract error recovery pattern."""
        if not trace.error_message:
            return None

        return ExtractedPattern(
            pattern_type=PatternType.ERROR_RECOVERY,
            description=f"Recovered from: {trace.error_message[:50]}",
            trigger_conditions=("error occurred",),
            steps=tuple(trace.steps[-2:]),  # Last 2 steps (recovery)
            confidence=0.75,
            occurrence_count=1,
            source_traces=(trace.trace_id,),
        )

    def _extract_domain_heuristics(self, trace: ExecutionTrace) -> list[ExtractedPattern]:
        """Extract domain-specific heuristics."""
        patterns = []

        # Look for domain keywords in task description
        task_lower = trace.task_description.lower()

        domains = {
            "test": ["test", "verify", "check"],
            "refactor": ["refactor", "clean", "improve"],
            "debug": ["debug", "fix", "error"],
            "design": ["design", "architect", "plan"],
        }

        for domain, keywords in domains.items():
            if any(kw in task_lower for kw in keywords):
                patterns.append(
                    ExtractedPattern(
                        pattern_type=PatternType.DOMAIN_HEURISTIC,
                        description=f"{domain.title()} workflow",
                        trigger_conditions=(f"{domain} task",),
                        steps=trace.steps,
                        confidence=0.65,
                        occurrence_count=1,
                        source_traces=(trace.trace_id,),
                    )
                )

        return patterns

    def _generate_pattern_id(self, pattern: ExtractedPattern) -> str:
        """Generate unique ID for a pattern."""
        content = f"{pattern.pattern_type}:{pattern.description}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def propose_skill(
        self,
        patterns: list[ExtractedPattern],
        name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[SkillProposal]:
        """
        Create a skill proposal from extracted patterns.

        Args:
            patterns: List of patterns to combine
            name: Optional skill name (auto-generated if None)
            category: Optional category (inferred if None)

        Returns:
            SkillProposal or None if patterns insufficient
        """
        if not patterns:
            return None

        # Filter by confidence
        high_confidence = [p for p in patterns if p.confidence >= self.min_confidence]
        if not high_confidence:
            return None

        # Infer name and category
        if not name:
            # Use most common pattern type
            pattern_types = [p.pattern_type for p in high_confidence]
            most_common = max(set(pattern_types), key=pattern_types.count)
            name = f"{most_common.replace('_', '-')}-skill"

        if not category:
            # Infer from pattern types
            if any(p.pattern_type == PatternType.ERROR_RECOVERY for p in high_confidence):
                category = "debugging"
            elif any(p.pattern_type == PatternType.TOOL_SEQUENCE for p in high_confidence):
                category = "automation"
            else:
                category = "general"

        # Extract triggers
        triggers = set()
        for pattern in high_confidence:
            triggers.update(pattern.trigger_conditions)

        # Extract tools
        tools = set()
        for pattern in high_confidence:
            for step in pattern.steps:
                # Simple tool extraction (look for "Use X" patterns)
                if "use" in step.lower():
                    words = step.split()
                    if "use" in [w.lower() for w in words]:
                        idx = [w.lower() for w in words].index("use")
                        if idx + 1 < len(words):
                            tools.add(words[idx + 1])

        # Generate tags
        tags = {category, name.split("-")[0]}

        # Calculate confidence (average of patterns)
        avg_confidence = sum(p.confidence for p in high_confidence) / len(high_confidence)

        # Calculate novelty score
        novelty = self._calculate_novelty(name, high_confidence)

        if novelty < self.min_novelty:
            return None  # Too similar to existing skills

        # Generate SKILL.md content
        content = self._generate_skill_md(
            name=name,
            description=self._generate_description(high_confidence),
            category=category,
            triggers=tuple(triggers),
            tags=tuple(tags),
            tools=tuple(tools),
            patterns=high_confidence,
        )

        # Collect source traces
        source_traces = set()
        for pattern in high_confidence:
            source_traces.update(pattern.source_traces)

        proposal = SkillProposal(
            name=name,
            description=self._generate_description(high_confidence),
            category=category,
            patterns=tuple(high_confidence),
            triggers=tuple(triggers),
            tags=tuple(tags),
            tools=tuple(tools),
            content=content,
            confidence=avg_confidence,
            novelty_score=novelty,
            source=CreationSource.SINGLE_TRACE,
            source_traces=tuple(source_traces),
        )

        self.stats.skills_proposed += 1
        self.stats.avg_confidence = (
            self.stats.avg_confidence * (self.stats.skills_proposed - 1) + avg_confidence
        ) / self.stats.skills_proposed

        return proposal

    def _generate_description(self, patterns: list[ExtractedPattern]) -> str:
        """Generate skill description from patterns."""
        if not patterns:
            return "Auto-generated skill"

        # Use first pattern's description
        return patterns[0].description

    def _calculate_novelty(
        self,
        name: str,
        patterns: list[ExtractedPattern],
    ) -> float:
        """
        Calculate novelty score (how different from existing skills).

        Returns:
            Novelty score 0.0-1.0
        """
        if not self._existing_skills:
            return 1.0  # No existing skills, fully novel

        # Simple novelty: check name similarity
        name_lower = name.lower()
        for existing in self._existing_skills:
            existing_lower = existing.lower()

            # Calculate word overlap
            name_words = set(name_lower.split("-"))
            existing_words = set(existing_lower.split("-"))

            overlap = len(name_words & existing_words) / max(len(name_words), 1)

            if overlap > 0.7:
                return 0.2  # Very similar to existing skill

        return 0.8  # Reasonably novel

    def _generate_skill_md(
        self,
        name: str,
        description: str,
        category: str,
        triggers: tuple[str, ...],
        tags: tuple[str, ...],
        tools: tuple[str, ...],
        patterns: list[ExtractedPattern],
    ) -> str:
        """Generate SKILL.md content."""
        # YAML frontmatter
        frontmatter = f"""---
name: {name}
description: {description}
category: {category}
triggers: [{', '.join(f'"{t}"' for t in triggers)}]
tags: [{', '.join(f'"{t}"' for t in tags)}]
tools: [{', '.join(f'"{t}"' for t in tools)}]
origin: auto-generated
created: {datetime.now().isoformat()}
confidence: {sum(p.confidence for p in patterns) / len(patterns):.2f}
---

# {name.replace('-', ' ').title()}

{description}

## When to Use

This skill is automatically triggered when:
"""

        for trigger in triggers:
            frontmatter += f"\n- {trigger}"

        frontmatter += "\n\n## Workflow\n"

        # Add steps from patterns
        for i, pattern in enumerate(patterns, 1):
            frontmatter += f"\n### Step {i}: {pattern.description}\n"
            for step in pattern.steps:
                frontmatter += f"\n- {step}"

        frontmatter += "\n\n## Tools Used\n"
        for tool in tools:
            frontmatter += f"\n- {tool}"

        frontmatter += f"\n\n## Confidence Score\n\n{sum(p.confidence for p in patterns) / len(patterns):.0%}\n"

        frontmatter += "\n## Source\n\nAuto-generated from execution traces.\n"

        return frontmatter

    def register_existing_skill(self, skill_name: str) -> None:
        """Register an existing skill for novelty checking."""
        self._existing_skills.add(skill_name)

    def accept_proposal(self, proposal: SkillProposal) -> None:
        """Mark a proposal as accepted."""
        self.stats.skills_accepted += 1
        self._existing_skills.add(proposal.name)

    def reject_proposal(self, proposal: SkillProposal) -> None:
        """Mark a proposal as rejected."""
        self.stats.skills_rejected += 1

    def get_stats(self) -> dict:
        """Get creator statistics."""
        return {
            "total_traces_analyzed": self.stats.total_traces_analyzed,
            "patterns_extracted": self.stats.patterns_extracted,
            "skills_proposed": self.stats.skills_proposed,
            "skills_accepted": self.stats.skills_accepted,
            "skills_rejected": self.stats.skills_rejected,
            "acceptance_rate": (
                self.stats.skills_accepted
                / max(self.stats.skills_proposed, 1)
            ),
            "avg_confidence": self.stats.avg_confidence,
        }

    def get_patterns_by_type(
        self,
        pattern_type: PatternType,
    ) -> list[ExtractedPattern]:
        """Get all patterns of a specific type."""
        return [
            p for p in self._patterns.values()
            if p.pattern_type == pattern_type
        ]

    def get_high_confidence_patterns(
        self,
        min_occurrences: int = 3,
    ) -> list[ExtractedPattern]:
        """
        Get patterns that have occurred multiple times.

        Args:
            min_occurrences: Minimum occurrence count

        Returns:
            List of high-confidence patterns
        """
        return [
            p for p in self._patterns.values()
            if p.occurrence_count >= min_occurrences
        ]
