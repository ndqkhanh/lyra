"""
Rules engine for Lyra.

This module provides a rules engine for enforcing coding standards,
best practices, and project-specific guidelines.
"""

from .rule import Rule, RuleCategory, RuleSeverity, RuleViolation
from .rule_registry import RuleRegistry
from .rule_engine import RuleEngine
from .rule_parser import RuleParser

__all__ = [
    "Rule",
    "RuleCategory",
    "RuleSeverity",
    "RuleViolation",
    "RuleRegistry",
    "RuleEngine",
    "RuleParser",
]

__version__ = "1.0.0"
