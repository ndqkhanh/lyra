"""
Lyra ECC Integration Package

ECC (Enhanced Claude Code) compatibility layer for Lyra.
"""

__version__ = "4.0.0"

from lyra_ecc.agents import AgentCategory, AgentDefinition, UnifiedAgentRegistry
from lyra_ecc.code_review import (
    CodeReviewResult,
    EnhancedRulesEngine,
    create_code_review_engine,
)
from lyra_ecc.compatibility import ECCCompatibilityLayer
from lyra_ecc.hooks import ECCHooksEngine, HookContext, HookResult, HookType
from lyra_ecc.importer import ECCImporter
from lyra_ecc.lifecycle_integration import ECCLifecycleIntegration, setup_ecc_hooks
from lyra_ecc.rules import RulesEngine, RuleSeverity, RuleViolation

__all__ = [
    # Core
    "ECCCompatibilityLayer",
    "ECCImporter",
    # Agents
    "UnifiedAgentRegistry",
    "AgentDefinition",
    "AgentCategory",
    # Hooks
    "ECCHooksEngine",
    "HookType",
    "HookContext",
    "HookResult",
    "ECCLifecycleIntegration",
    "setup_ecc_hooks",
    # Rules
    "RulesEngine",
    "RuleSeverity",
    "RuleViolation",
    # Code Review
    "EnhancedRulesEngine",
    "CodeReviewResult",
    "create_code_review_engine",
    # Version
    "__version__",
]
