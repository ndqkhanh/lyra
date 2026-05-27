"""Data models for code generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedPatch:
    """Represents a generated code patch."""

    target_function: str
    original_code: str
    new_code: str
    description: str
    confidence: float  # 0.0 to 1.0
    patch_type: str = "optimization"  # "optimization", "refactoring", "type_hints"


@dataclass(frozen=True)
class RefactoringSuggestion:
    """Represents a refactoring suggestion."""

    function_name: str
    suggestion_type: str  # "list_comprehension", "generator", "extract_method", etc.
    description: str
    original_code: str
    suggested_code: str
    impact: str  # "low", "medium", "high"
    confidence: float
