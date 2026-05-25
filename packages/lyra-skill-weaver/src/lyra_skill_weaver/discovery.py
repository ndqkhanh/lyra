"""Skill discovery: scanning, gap analysis, quality evaluation, import, registration.

Automatically discovers new skills from various sources, evaluates their quality,
identifies capability gaps, and imports them into the registry.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import pkgutil
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from .skill_weaver import (
    SkillDefinition,
    SkillMetadata,
    SkillIO,
    SkillType,
    SkillStatus,
    SkillRegistry,
)
from .exceptions import DiscoveryError, ValidationError

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class DiscoveryMethod(Enum):
    """Methods for discovering skills."""

    FILESYSTEM_SCAN = auto()
    PACKAGE_IMPORT = auto()
    API_REGISTRY = auto()
    MANIFEST_FILE = auto()
    CODE_ANALYSIS = auto()


class QualityTier(Enum):
    """Quality tiers for discovered skills."""

    PRODUCTION = auto()
    BETA = auto()
    EXPERIMENTAL = auto()
    UNTESTED = auto()


@dataclass
class QualityReport:
    """Quality evaluation report for a discovered skill.

    Attributes:
        skill_id: The skill being evaluated.
        tier: Overall quality tier.
        test_coverage: Fraction of code covered by tests (0-1).
        doc_completeness: Fraction of documented parameters (0-1).
        has_examples: Whether usage examples exist.
        dependency_health: Fraction of dependencies that exist.
        performance_score: Composite performance score (0-1).
        issues: List of quality issues found.
        recommendations: Suggested improvements.
    """

    skill_id: str
    tier: QualityTier = QualityTier.UNTESTED
    test_coverage: float = 0.0
    doc_completeness: float = 0.0
    has_examples: bool = False
    dependency_health: float = 0.0
    performance_score: float = 0.5
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Compute overall quality score (0-1)."""
        return (
            self.test_coverage * 0.3
            + self.doc_completeness * 0.2
            + (1.0 if self.has_examples else 0.0) * 0.1
            + self.dependency_health * 0.2
            + self.performance_score * 0.2
        )


@dataclass
class GapAnalysis:
    """Capability gap analysis results.

    Attributes:
        missing_capabilities: Outputs that no existing skill produces.
        weak_capabilities: Outputs with low-quality producers.
        surplus_capabilities: Outputs with redundant producers.
        recommendations: Recommended actions to address gaps.
    """

    missing_capabilities: list[str] = field(default_factory=list)
    weak_capabilities: list[tuple[str, float]] = field(default_factory=list)
    surplus_capabilities: list[tuple[str, int]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Skill Discovery Engine ─────────────────────────────────────────────


class SkillDiscoveryEngine:
    """Discovers skills from various sources and imports them.

    Supports filesystem scanning, package imports, manifest files,
    and runtime code analysis for automatic skill registration.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self._discovery_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._skip_patterns: list[str] = [
            "__pycache__", "test_", "conftest", ".pyc", "__init__",
        ]

    async def discover_from_directory(
        self,
        directory: Path,
        recursive: bool = True,
    ) -> list[SkillDefinition]:
        """Scan a directory for skill definitions.

        Looks for Python files with skill annotations or conventions.

        Args:
            directory: Directory to scan.
            recursive: Whether to scan subdirectories.

        Returns:
            List of discovered skill definitions.
        """
        discovered: list[SkillDefinition] = []
        pattern = "**/*.py" if recursive else "*.py"

        for py_file in directory.glob(pattern):
            if any(skip in str(py_file) for skip in self._skip_patterns):
                continue

            try:
                skills = await self._extract_skills_from_file(py_file)
                discovered.extend(skills)
            except Exception as exc:
                logger.debug("Could not extract skills from %s: %s", py_file, exc)

        self._discovery_history.append({
            "source": str(directory),
            "method": DiscoveryMethod.FILESYSTEM_SCAN.name,
            "found": len(discovered),
            "timestamp": time.time(),
        })

        if discovered:
            logger.info("Discovered %d skills from %s", len(discovered), directory)

        return discovered

    async def _extract_skills_from_file(self, filepath: Path) -> list[SkillDefinition]:
        """Extract skill definitions from a Python file.

        Looks for:
        - Classes decorated with @skill
        - Functions decorated with @skill
        - Classes with SKILL_META attribute
        - Well-structured classes implementing skill patterns
        """
        skills: list[SkillDefinition] = []
        try:
            source_code = filepath.read_text(encoding="utf-8")
        except Exception:
            return skills

        # Heuristic: detect skill definitions via AST-like pattern matching
        # Look for class or function names suggesting skill definitions
        lines = source_code.split("\n")
        current_class: Optional[str] = None
        in_docstring = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("class ") and "Skill" in stripped:
                current_class = stripped.split("(")[0].replace("class ", "").strip()
                # Create a basic skill definition from class analysis
                skill = self._create_skill_from_class_heuristic(
                    current_class, filepath, source_code
                )
                if skill:
                    skills.append(skill)

        return skills

    def _create_skill_from_class_heuristic(
        self,
        class_name: str,
        filepath: Path,
        source_code: str,
    ) -> Optional[SkillDefinition]:
        """Create a SkillDefinition from heuristic analysis of a class."""
        skill_id = f"discovered_{class_name.lower()}_{filepath.stem}"
        lines = source_code.split("\n")

        # Extract docstring
        description = ""
        inputs: list[SkillIO] = []
        outputs: list[SkillIO] = []
        has_execute = "def execute" in source_code or "async def execute" in source_code
        has_run = "def run" in source_code or "async def run" in source_code

        # Extract docstring from class
        in_class = False
        for line in lines:
            if f"class {class_name}" in line:
                in_class = True
                continue
            if in_class:
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    description = stripped.strip('"""').strip("'''")
                    break

        # Heuristic input/output detection
        if "input" in source_code.lower() and "output" in source_code.lower():
            inputs.append(SkillIO(name="input", type_hint="Any"))
            outputs.append(SkillIO(name="output", type_hint="Any"))

        if has_execute or has_run:
            skill_type = SkillType.PRIMITIVE
        else:
            skill_type = SkillType.COMPOSITE

        meta = SkillMetadata(
            skill_id=skill_id,
            name=class_name,
            version="0.1.0",
            description=description or f"Auto-discovered skill: {class_name}",
            tags=["discovered", filepath.stem],
            status=SkillStatus.EXPERIMENTAL,
        )

        return SkillDefinition(
            metadata=meta,
            skill_type=skill_type,
            inputs=inputs,
            outputs=outputs,
            source_code=source_code[:1000],
        )

    async def discover_from_package(
        self,
        package_name: str,
        skill_base_class: Optional[str] = None,
    ) -> list[SkillDefinition]:
        """Discover skills by importing a Python package.

        Args:
            package_name: Fully qualified package name to scan.
            skill_base_class: Optional base class name to filter by.

        Returns:
            List of discovered skill definitions.
        """
        discovered: list[SkillDefinition] = []
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent if package.__file__ else None
            if package_path:
                discovered = await self.discover_from_directory(package_path)
        except ImportError as exc:
            raise DiscoveryError(package_name, f"Import failed: {exc}")

        self._discovery_history.append({
            "source": package_name,
            "method": DiscoveryMethod.PACKAGE_IMPORT.name,
            "found": len(discovered),
            "timestamp": time.time(),
        })

        return discovered

    async def discover_from_manifest(self, manifest_path: Path) -> list[SkillDefinition]:
        """Discover skills from a JSON manifest file.

        Manifest format:
        {
            "skills": [
                {
                    "id": "...",
                    "name": "...",
                    "version": "...",
                    "description": "...",
                    "inputs": [{"name": "...", "type": "..."}],
                    "outputs": [{"name": "...", "type": "..."}],
                    "dependencies": [...],
                    "tags": [...]
                }
            ]
        }

        Args:
            manifest_path: Path to the JSON manifest.

        Returns:
            List of parsed skill definitions.
        """
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as exc:
            raise DiscoveryError(str(manifest_path), f"Failed to read manifest: {exc}")

        discovered: list[SkillDefinition] = []
        for skill_data in data.get("skills", []):
            try:
                skill = self._parse_manifest_entry(skill_data)
                discovered.append(skill)
            except Exception as exc:
                logger.warning("Failed to parse manifest entry: %s", exc)

        self._discovery_history.append({
            "source": str(manifest_path),
            "method": DiscoveryMethod.MANIFEST_FILE.name,
            "found": len(discovered),
            "timestamp": time.time(),
        })

        return discovered

    def _parse_manifest_entry(self, data: dict[str, Any]) -> SkillDefinition:
        """Parse a single skill entry from a manifest."""
        meta = SkillMetadata(
            skill_id=data.get("id", f"manifest_{int(time.time())}"),
            name=data.get("name", "unnamed"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )

        inputs = [
            SkillIO(
                name=i.get("name", "input"),
                type_hint=i.get("type", "Any"),
                required=i.get("required", True),
                default=i.get("default"),
                description=i.get("description", ""),
            )
            for i in data.get("inputs", [])
        ]

        outputs = [
            SkillIO(
                name=o.get("name", "output"),
                type_hint=o.get("type", "Any"),
                required=True,
                description=o.get("description", ""),
            )
            for o in data.get("outputs", [])
        ]

        return SkillDefinition(
            metadata=meta,
            skill_type=SkillType(data.get("skill_type", "PRIMITIVE").upper()),
            inputs=inputs,
            outputs=outputs,
            dependencies=data.get("dependencies", []),
            conflicts=data.get("conflicts", []),
            context_requirements=data.get("context_requirements", {}),
            quality_score=data.get("quality_score", 0.5),
            estimated_cost=data.get("estimated_cost", 0.0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
        )

    # ── Auto-registration ──────────────────────────────────────────────

    async def discover_and_register(
        self,
        source: Path | str,
        method: DiscoveryMethod = DiscoveryMethod.FILESYSTEM_SCAN,
        min_quality: float = 0.3,
    ) -> int:
        """Discover skills and automatically register those above quality threshold.

        Args:
            source: Source to discover from.
            method: Discovery method.
            min_quality: Minimum quality score for auto-registration.

        Returns:
            Number of skills registered.
        """
        if method == DiscoveryMethod.FILESYSTEM_SCAN:
            skills = await self.discover_from_directory(Path(source))
        elif method == DiscoveryMethod.MANIFEST_FILE:
            skills = await self.discover_from_manifest(Path(source))
        elif method == DiscoveryMethod.PACKAGE_IMPORT:
            skills = await self.discover_from_package(str(source))
        else:
            raise DiscoveryError(str(source), f"Unsupported method: {method}")

        registered = 0
        for skill in skills:
            quality = self.evaluate_quality(skill)
            if quality.overall_score >= min_quality:
                try:
                    self.registry.register(skill)
                    registered += 1
                except ValidationError as exc:
                    logger.warning("Auto-registration skipped for %s: %s", skill.skill_id, exc)

        logger.info("Auto-registered %d/%d skills from %s", registered, len(skills), source)
        return registered

    # ── Quality evaluation ─────────────────────────────────────────────

    def evaluate_quality(self, skill: SkillDefinition) -> QualityReport:
        """Evaluate the quality of a skill.

        Args:
            skill: The skill to evaluate.

        Returns:
            A quality report with scores and recommendations.
        """
        issues: list[str] = []
        recommendations: list[str] = []

        # Doc completeness
        inputs_documented = sum(1 for i in skill.inputs if i.description)
        outputs_documented = sum(1 for o in skill.outputs if o.description)
        total_io = max(len(skill.inputs) + len(skill.outputs), 1)
        doc_completeness = (inputs_documented + outputs_documented) / total_io

        if doc_completeness < 0.5:
            issues.append("Insufficient documentation for I/O parameters")
            recommendations.append("Add descriptions to all input/output parameters")

        # Has examples
        has_examples = bool(skill.examples)
        if not has_examples:
            recommendations.append("Add usage examples")

        # Dependency health
        if skill.dependencies:
            existing = sum(1 for d in skill.dependencies if self.registry.get(d))
            dependency_health = existing / len(skill.dependencies)
            if dependency_health < 1.0:
                missing = [d for d in skill.dependencies if not self.registry.get(d)]
                issues.append(f"Missing dependencies: {missing}")
        else:
            dependency_health = 1.0

        # Performance score (based on latency estimate)
        if skill.avg_latency_ms > 5000:
            performance_score = 0.3
            issues.append(f"High latency: {skill.avg_latency_ms}ms")
        elif skill.avg_latency_ms > 1000:
            performance_score = 0.6
        else:
            performance_score = 0.9

        # Test coverage heuristic
        test_coverage = 0.5 if skill.source_code else 0.0

        # Determine tier
        overall = (
            test_coverage * 0.3
            + doc_completeness * 0.2
            + (1.0 if has_examples else 0.0) * 0.1
            + dependency_health * 0.2
            + performance_score * 0.2
        )

        if overall >= 0.8 and not issues:
            tier = QualityTier.PRODUCTION
        elif overall >= 0.6:
            tier = QualityTier.BETA
        elif overall >= 0.4:
            tier = QualityTier.EXPERIMENTAL
        else:
            tier = QualityTier.UNTESTED

        return QualityReport(
            skill_id=skill.skill_id,
            tier=tier,
            test_coverage=test_coverage,
            doc_completeness=doc_completeness,
            has_examples=has_examples,
            dependency_health=dependency_health,
            performance_score=performance_score,
            issues=issues,
            recommendations=recommendations,
        )

    def evaluate_all(self) -> dict[str, QualityReport]:
        """Evaluate quality for all registered skills."""
        reports = {}
        for skill_id in self.registry._by_id:
            skill = self.registry.get(skill_id)
            if skill:
                reports[skill_id] = self.evaluate_quality(skill)
        return reports

    # ── Gap analysis ───────────────────────────────────────────────────

    def analyze_gaps(self, required_capabilities: list[str]) -> GapAnalysis:
        """Analyze capability gaps in the registry.

        Args:
            required_capabilities: List of capability/output names needed.

        Returns:
            GapAnalysis with missing and weak capabilities.
        """
        existing = {}
        for output_name, skill_ids in self.registry._by_output.items():
            existing[output_name] = skill_ids

        missing: list[str] = []
        weak: list[tuple[str, float]] = []
        surplus: list[tuple[str, int]] = []

        for cap in required_capabilities:
            producers = existing.get(cap, [])
            if not producers:
                missing.append(cap)
            else:
                best_quality = max(
                    (self.registry.get(sid).quality_score for sid in producers if self.registry.get(sid)),
                    default=0.0,
                )
                if best_quality < 0.5:
                    weak.append((cap, best_quality))
                if len(producers) > 5:
                    surplus.append((cap, len(producers)))

        recommendations = []
        if missing:
            recommendations.append(f"Build skills for: {', '.join(missing)}")
        if weak:
            recommendations.append(f"Improve quality for: {', '.join(c for c, _ in weak)}")
        if surplus:
            recommendations.append(f"Consider consolidating: {', '.join(c for c, _ in surplus)}")

        return GapAnalysis(
            missing_capabilities=missing,
            weak_capabilities=weak,
            surplus_capabilities=surplus,
            recommendations=recommendations,
        )

    @property
    def discovery_stats(self) -> dict[str, Any]:
        """Get discovery statistics."""
        return {
            "total_discoveries": len(self._discovery_history),
            "recent_sources": [d["source"] for d in list(self._discovery_history)[-5:]],
            "by_method": {},
        }
