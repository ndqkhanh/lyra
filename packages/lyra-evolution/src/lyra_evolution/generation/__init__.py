"""Code generation module for optimization patches and refactoring."""

from __future__ import annotations

from .generator import CodeGenerator
from .models import GeneratedPatch, RefactoringSuggestion

__all__ = [
    "CodeGenerator",
    "GeneratedPatch",
    "RefactoringSuggestion",
]
