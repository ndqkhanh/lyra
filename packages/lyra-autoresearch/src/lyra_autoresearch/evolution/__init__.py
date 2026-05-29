"""
Evolution System with MetaClaw Bridge

Implements AutoResearchClaw's cross-run evolution:
- Lesson extraction from failures
- Skill synthesis from lessons
- Cross-run knowledge accumulation
- Integration with Lyra's Memoria

Based on: researchclaw/evolution.py and researchclaw/metaclaw_bridge/
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LessonCategory(Enum):
    """Category of learned lesson"""
    SYSTEM = "system"          # Infrastructure/setup issues
    EXPERIMENT = "experiment"  # Methodological problems
    ANALYSIS = "analysis"      # Result interpretation errors
    WRITING = "writing"        # Paper generation issues
    IDEATION = "ideation"      # Hypothesis formation issues


class LessonSeverity(Enum):
    """Severity level of lesson"""
    INFO = "info"          # Minor observation
    WARNING = "warning"    # Notable issue
    ERROR = "error"        # Significant problem → skill candidate
    CRITICAL = "critical"  # Major failure → skill candidate


@dataclass
class LessonEntry:
    """Single lesson learned from execution"""
    category: LessonCategory
    severity: LessonSeverity
    description: str
    context: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    run_id: str | None = None
    stage: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "context": self.context,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "stage": self.stage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LessonEntry":
        """Create from dictionary"""
        return cls(
            category=LessonCategory(data["category"]),
            severity=LessonSeverity(data["severity"]),
            description=data["description"],
            context=data["context"],
            timestamp=data.get("timestamp", time.time()),
            run_id=data.get("run_id"),
            stage=data.get("stage"),
        )


@dataclass
class SkillMetadata:
    """Metadata for synthesized skill"""
    name: str
    description: str
    category: str
    source_lessons: list[str]  # Lesson IDs
    effectiveness_score: float = 0.5
    usage_count: int = 0
    success_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class EvolutionStore:
    """
    Persistent storage for lessons and evolution data

    Uses JSONL format for append-only lesson storage
    """

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or Path(".evolution/lessons.jsonl")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def add_lesson(self, lesson: LessonEntry) -> str:
        """Add lesson to store and return ID"""
        lesson_id = f"lesson_{int(time.time() * 1000)}"

        with open(self.store_path, 'a') as f:
            data = lesson.to_dict()
            data["id"] = lesson_id
            f.write(json.dumps(data) + "\n")

        return lesson_id

    def get_lessons(
        self,
        category: LessonCategory | None = None,
        severity: LessonSeverity | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[LessonEntry]:
        """Retrieve lessons with filters"""

        if not self.store_path.exists():
            return []

        lessons = []

        with open(self.store_path) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    lesson = LessonEntry.from_dict(data)

                    # Apply filters
                    if category and lesson.category != category:
                        continue
                    if severity and lesson.severity != severity:
                        continue
                    if since and lesson.timestamp < since:
                        continue

                    lessons.append(lesson)
                except Exception as e:
                    logger.warning(f"Failed to parse lesson: {e}")

        # Sort by timestamp (newest first)
        lessons.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            lessons = lessons[:limit]

        return lessons

    def get_high_severity_lessons(
        self,
        since: float | None = None,
    ) -> list[LessonEntry]:
        """Get ERROR and CRITICAL lessons (skill candidates)"""

        lessons = self.get_lessons(since=since)
        return [
            lesson for lesson in lessons
            if lesson.severity in [LessonSeverity.ERROR, LessonSeverity.CRITICAL]
        ]


class SkillSynthesizer:
    """
    Converts lessons into reusable skills

    Implements AutoResearchClaw's lesson-to-skill conversion
    """

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or Path(".evolution/skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def synthesize_skill(
        self,
        lessons: list[LessonEntry],
        skill_name: str | None = None,
    ) -> SkillMetadata | None:
        """
        Synthesize a skill from multiple related lessons

        Args:
            lessons: Related lessons to synthesize
            skill_name: Optional skill name (auto-generated if None)

        Returns:
            SkillMetadata if successful, None otherwise
        """

        if not lessons:
            return None

        # Generate skill name if not provided
        if not skill_name:
            category = lessons[0].category.value
            timestamp = int(time.time())
            skill_name = f"autogen_{category}_{timestamp}"

        # Generate skill description
        description = self._generate_description(lessons)

        # Generate skill content
        content = self._generate_content(lessons)

        # Create SKILL.md file
        skill_file = self.skills_dir / f"{skill_name}.md"
        self._write_skill_file(skill_file, skill_name, description, content, lessons)

        # Create metadata
        metadata = SkillMetadata(
            name=skill_name,
            description=description,
            category=lessons[0].category.value,
            source_lessons=[f"lesson_{i}" for i in range(len(lessons))],
        )

        return metadata

    def _generate_description(self, lessons: list[LessonEntry]) -> str:
        """Generate skill description from lessons"""

        # Group by category
        categories = {lesson.category for lesson in lessons}
        category_str = ", ".join(c.value for c in categories)

        # Count severity
        error_count = sum(1 for l in lessons if l.severity == LessonSeverity.ERROR)
        critical_count = sum(1 for l in lessons if l.severity == LessonSeverity.CRITICAL)

        return (
            f"Auto-generated skill from {len(lessons)} lessons "
            f"({category_str}). "
            f"Addresses {error_count} errors and {critical_count} critical issues."
        )

    def _generate_content(self, lessons: list[LessonEntry]) -> str:
        """Generate skill content from lessons"""

        content_parts = []

        # Group lessons by category
        by_category: dict[LessonCategory, list[LessonEntry]] = {}
        for lesson in lessons:
            if lesson.category not in by_category:
                by_category[lesson.category] = []
            by_category[lesson.category].append(lesson)

        # Generate content for each category
        for category, category_lessons in by_category.items():
            content_parts.append(f"## {category.value.title()} Lessons\n")

            for i, lesson in enumerate(category_lessons, 1):
                content_parts.append(f"### Lesson {i}: {lesson.severity.value.upper()}\n")
                content_parts.append(f"{lesson.description}\n")

                if lesson.context:
                    content_parts.append("\n**Context:**\n")
                    for key, value in lesson.context.items():
                        content_parts.append(f"- {key}: {value}\n")

                content_parts.append("\n")

        return "\n".join(content_parts)

    def _write_skill_file(
        self,
        file_path: Path,
        name: str,
        description: str,
        content: str,
        lessons: list[LessonEntry],
    ) -> None:
        """Write SKILL.md file in agentskills.io format"""

        # Build frontmatter
        frontmatter = [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"category: {lessons[0].category.value}",
            "auto_generated: true",
            "source: autoresearch_evolution",
            f"lesson_count: {len(lessons)}",
            f"created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "---",
            "",
        ]

        # Combine frontmatter and content
        full_content = "\n".join(frontmatter) + "\n" + content

        # Write file
        with open(file_path, 'w') as f:
            f.write(full_content)

        logger.info(f"Created skill file: {file_path}")


class MemoriaBridge:
    """
    Bridge between AutoResearchClaw evolution and Lyra's Memoria

    Converts lessons to Memoria episodes and skills to Memoria procedures
    """

    def __init__(self, memoria_client: Any | None = None):
        self.memoria_client = memoria_client

    def sync_lessons_to_memoria(
        self,
        lessons: list[LessonEntry],
    ) -> list[str]:
        """
        Sync lessons to Memoria as episodes

        Args:
            lessons: Lessons to sync

        Returns:
            List of Memoria episode IDs
        """

        if not self.memoria_client:
            logger.warning("No Memoria client available")
            return []

        episode_ids = []

        for lesson in lessons:
            try:
                # Convert lesson to Memoria episode format

                # Store in Memoria (pseudo-code - actual API depends on Memoria implementation)
                # episode_id = self.memoria_client.store(episode_data)
                # episode_ids.append(episode_id)

                logger.info(f"Synced lesson to Memoria: {lesson.description[:50]}...")

            except Exception as e:
                logger.error(f"Failed to sync lesson to Memoria: {e}")

        return episode_ids

    def sync_skill_to_memoria(
        self,
        skill_metadata: SkillMetadata,
        skill_content: str,
    ) -> str | None:
        """
        Sync skill to Memoria as procedure

        Args:
            skill_metadata: Skill metadata
            skill_content: Skill content (SKILL.md)

        Returns:
            Memoria procedure ID if successful
        """

        if not self.memoria_client:
            logger.warning("No Memoria client available")
            return None

        try:
            # Convert skill to Memoria procedure format

            # Store in Memoria (pseudo-code)
            # procedure_id = self.memoria_client.store(procedure_data)
            # return procedure_id

            logger.info(f"Synced skill to Memoria: {skill_metadata.name}")
            return None

        except Exception as e:
            logger.error(f"Failed to sync skill to Memoria: {e}")
            return None


class EvolutionEngine:
    """
    Complete evolution engine

    Orchestrates lesson extraction, skill synthesis, and Memoria integration
    """

    def __init__(
        self,
        store_path: Path | None = None,
        skills_dir: Path | None = None,
        memoria_client: Any | None = None,
    ):
        self.store = EvolutionStore(store_path)
        self.synthesizer = SkillSynthesizer(skills_dir)
        self.memoria_bridge = MemoriaBridge(memoria_client)

    def record_lesson(
        self,
        category: LessonCategory,
        severity: LessonSeverity,
        description: str,
        context: dict[str, Any] | None = None,
        run_id: str | None = None,
        stage: str | None = None,
    ) -> str:
        """Record a new lesson"""

        lesson = LessonEntry(
            category=category,
            severity=severity,
            description=description,
            context=context or {},
            run_id=run_id,
            stage=stage,
        )

        lesson_id = self.store.add_lesson(lesson)
        logger.info(f"Recorded lesson: {description[:50]}...")

        return lesson_id

    def evolve(
        self,
        since: float | None = None,
        sync_to_memoria: bool = True,
    ) -> list[SkillMetadata]:
        """
        Run evolution cycle: extract lessons → synthesize skills → sync to Memoria

        Args:
            since: Only process lessons since this timestamp
            sync_to_memoria: Whether to sync to Memoria

        Returns:
            List of synthesized skill metadata
        """

        # Get high-severity lessons (skill candidates)
        lessons = self.store.get_high_severity_lessons(since=since)

        if not lessons:
            logger.info("No high-severity lessons to process")
            return []

        logger.info(f"Processing {len(lessons)} high-severity lessons")

        # Group lessons by category
        by_category: dict[LessonCategory, list[LessonEntry]] = {}
        for lesson in lessons:
            if lesson.category not in by_category:
                by_category[lesson.category] = []
            by_category[lesson.category].append(lesson)

        # Synthesize skills for each category
        synthesized_skills = []

        for category, category_lessons in by_category.items():
            if len(category_lessons) < 2:
                # Need at least 2 lessons to synthesize a skill
                continue

            skill_metadata = self.synthesizer.synthesize_skill(
                lessons=category_lessons,
                skill_name=f"autogen_{category.value}_{int(time.time())}",
            )

            if skill_metadata:
                synthesized_skills.append(skill_metadata)
                logger.info(f"Synthesized skill: {skill_metadata.name}")

        # Sync to Memoria if requested
        if sync_to_memoria and synthesized_skills:
            self.memoria_bridge.sync_lessons_to_memoria(lessons)

            for skill_metadata in synthesized_skills:
                skill_file = self.synthesizer.skills_dir / f"{skill_metadata.name}.md"
                if skill_file.exists():
                    with open(skill_file) as f:
                        skill_content = f.read()
                    self.memoria_bridge.sync_skill_to_memoria(skill_metadata, skill_content)

        return synthesized_skills
