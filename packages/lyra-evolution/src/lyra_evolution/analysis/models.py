"""Data models for code analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ComplexityMetrics:
    """Complexity metrics for code."""

    cyclomatic_complexity: int
    cognitive_complexity: int
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    lines_of_code: int = 0
    comment_ratio: float = 0.0


@dataclass(frozen=True)
class Bottleneck:
    """Represents a performance bottleneck."""

    function_name: str
    type: str  # "recursive", "inefficient_loop", "nested_loop", etc.
    severity: str  # "low", "medium", "high", "critical"
    line_number: int
    description: str
    suggestion: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    """Result of analyzing a file."""

    file_path: Path
    metrics: ComplexityMetrics
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    timestamp: float = 0.0
