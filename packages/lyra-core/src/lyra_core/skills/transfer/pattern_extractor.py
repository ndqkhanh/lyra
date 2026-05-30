"""Pattern Extractor - Extracts reusable patterns from skill implementations.

Identifies and extracts transferable code patterns, structural idioms,
and best practices from skill source code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class PatternType(StrEnum):
    """Types of extractable patterns."""

    IMPORT = "import"
    FUNCTION = "function"
    CLASS = "class"
    DECORATOR = "decorator"
    ERROR_HANDLING = "error_handling"
    VALIDATION = "validation"
    TEMPLATE = "template"
    STRUCTURE = "structure"


@dataclass(frozen=True)
class ExtractedPattern:
    """A pattern extracted from skill source code."""

    pattern_type: PatternType
    name: str
    content: str
    line_count: int
    complexity: float  # 0.0-1.0
    reusability_score: float  # 0.0-1.0
    source_skill: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ExtractionResult:
    """Result of pattern extraction from a skill."""

    skill_name: str
    patterns: tuple[ExtractedPattern, ...]
    total_lines: int
    extraction_time_ms: float = 0.0


class PatternExtractor:
    """Extracts transferable patterns from skill source code.

    Analyzes source code structure to identify reusable patterns
    that can be transferred between skill domains.

    Features:
    - Multi-type pattern extraction (imports, functions, classes, decorators)
    - Reusability scoring based on pattern characteristics
    - Error handling and validation pattern detection
    - Structural template identification
    """

    def __init__(self, min_reusability: float = 0.3):
        self.min_reusability = min_reusability
        self._history: list[ExtractionResult] = []

    def extract(self, skill_name: str, source_code: str) -> ExtractionResult:
        """Extract all transferable patterns from skill source code.

        Args:
            skill_name: Name of the skill being analyzed
            source_code: Source code to extract patterns from

        Returns:
            ExtractionResult with discovered patterns
        """
        patterns: list[ExtractedPattern] = []
        total_lines = len(source_code.splitlines())

        # Extract import patterns
        patterns.extend(self._extract_imports(skill_name, source_code))

        # Extract function patterns
        patterns.extend(self._extract_functions(skill_name, source_code))

        # Extract class patterns
        patterns.extend(self._extract_classes(skill_name, source_code))

        # Extract decorator patterns
        patterns.extend(self._extract_decorators(skill_name, source_code))

        # Extract error handling patterns
        patterns.extend(self._extract_error_handling(skill_name, source_code))

        # Extract validation patterns
        patterns.extend(self._extract_validation(skill_name, source_code))

        # Filter by reusability threshold
        patterns = [p for p in patterns if p.reusability_score >= self.min_reusability]

        result = ExtractionResult(
            skill_name=skill_name,
            patterns=tuple(patterns),
            total_lines=total_lines,
        )
        self._history.append(result)
        return result

    def extract_multiple(self, skills: dict[str, str]) -> list[ExtractionResult]:
        """Extract patterns from multiple skills.

        Args:
            skills: Dict of {skill_name: source_code}

        Returns:
            List of ExtractionResult
        """
        return [self.extract(name, code) for name, code in skills.items()]

    def get_cross_domain_patterns(
        self, source_domain: str, all_patterns: list[ExtractionResult]
    ) -> list[ExtractedPattern]:
        """Get patterns from a source domain suitable for cross-domain transfer.

        Args:
            source_domain: Source domain filter
            all_patterns: All extraction results

        Returns:
            List of patterns with high cross-domain applicability
        """
        all_extracted: list[ExtractedPattern] = []
        for result in all_patterns:
            all_extracted.extend(result.patterns)

        # Sort by reusability for cross-domain applicability
        return sorted(
            all_extracted,
            key=lambda p: (p.reusability_score, p.complexity),
            reverse=True,
        )

    # ── Private Extractors ────────────────────────────────────────

    def _extract_imports(self, skill_name: str, code: str) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        import_lines = re.findall(
            r"^(?:import\s+[\w.]+|from\s+[\w.]+\s+import\s+[\w,\s*]+)",
            code, re.MULTILINE,
        )
        for imp in import_lines:
            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.IMPORT,
                    name=imp.strip()[:60],
                    content=imp.strip(),
                    line_count=1,
                    complexity=0.1,
                    reusability_score=0.9,
                    source_skill=skill_name,
                    tags=("import", "dependency"),
                )
            )
        return patterns

    def _extract_functions(self, skill_name: str, code: str) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        func_matches = re.finditer(
            r"def\s+(\w+)\s*\([^)]*\)(?:\s*->.*?)?:",
            code, re.MULTILINE,
        )
        for match in func_matches:
            func_name = match.group(1)
            if func_name.startswith("_"):
                continue

            func_code = match.group(0)
            complexity = min(1.0, len(func_code) / 200.0)
            reusability = 0.8 if len(func_name) > 3 else 0.4

            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.FUNCTION,
                    name=func_name,
                    content=func_code,
                    line_count=1,
                    complexity=complexity,
                    reusability_score=reusability,
                    source_skill=skill_name,
                    tags=("function", func_name),
                )
            )
        return patterns

    def _extract_classes(self, skill_name: str, code: str) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        class_matches = re.finditer(
            r"class\s+(\w+)\s*(?:\([^)]*\))?\s*:",
            code, re.MULTILINE,
        )
        for match in class_matches:
            class_name = match.group(1)
            if class_name.startswith("_"):
                continue

            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.CLASS,
                    name=class_name,
                    content=match.group(0),
                    line_count=1,
                    complexity=0.5,
                    reusability_score=0.7,
                    source_skill=skill_name,
                    tags=("class", class_name.lower()),
                )
            )
        return patterns

    def _extract_decorators(self, skill_name: str, code: str) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        deco_matches = re.finditer(
            r"@(\w+(?:\.\w+)?)(?:\([^)]*\))?",
            code, re.MULTILINE,
        )
        seen: set[str] = set()
        for match in deco_matches:
            deco = match.group(1)
            if deco in seen:
                continue
            seen.add(deco)

            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.DECORATOR,
                    name=f"@{deco}",
                    content=match.group(0),
                    line_count=1,
                    complexity=0.2,
                    reusability_score=0.6,
                    source_skill=skill_name,
                    tags=("decorator", deco),
                )
            )
        return patterns

    def _extract_error_handling(
        self, skill_name: str, code: str
    ) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        if re.search(r"try\s*:.*?except", code, re.DOTALL):
            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.ERROR_HANDLING,
                    name="try_except_block",
                    content="try/except error handling pattern",
                    line_count=4,
                    complexity=0.3,
                    reusability_score=0.85,
                    source_skill=skill_name,
                    tags=("error", "exception", "try", "except"),
                )
            )
        if re.search(r"raise\s+\w+Error", code):
            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.ERROR_HANDLING,
                    name="custom_error_raising",
                    content="Custom error raising pattern",
                    line_count=2,
                    complexity=0.2,
                    reusability_score=0.75,
                    source_skill=skill_name,
                    tags=("error", "raise", "custom"),
                )
            )
        return patterns

    def _extract_validation(
        self, skill_name: str, code: str
    ) -> list[ExtractedPattern]:
        patterns: list[ExtractedPattern] = []
        if re.search(r"\b(?:validate|verify|check|assert)\b", code):
            name = "validation_pattern"
            if "validate" in code:
                name = "validate_pattern"
            elif "verify" in code:
                name = "verify_pattern"
            elif "assert" in code:
                name = "assert_pattern"
            patterns.append(
                ExtractedPattern(
                    pattern_type=PatternType.VALIDATION,
                    name=name,
                    content="Input validation / assertion pattern",
                    line_count=3,
                    complexity=0.2,
                    reusability_score=0.8,
                    source_skill=skill_name,
                    tags=("validation", "input", "guard"),
                )
            )
        return patterns

    def clear(self) -> None:
        """Clear extraction history."""
        self._history.clear()
