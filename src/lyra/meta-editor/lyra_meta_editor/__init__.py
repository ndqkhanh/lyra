"""Lyra Meta Editor — Self-modifying code editor with safe rewrite, AST transformation, mutation
testing, and evolution metrics."""

from __future__ import annotations

from lyra.meta_editor.ast_transformer import (
    ASTNode,
    ASTTransformer,
    TransformConfig,
    TransformResult,
)
from lyra.meta_editor.code_analyzer import (
    AnalysisConfig,
    CodeAnalyzer,
    CodeMetrics,
    HotspotReport,
)
from lyra.meta_editor.diff_generator import (
    DiffConfig,
    DiffGenerator,
    DiffHunk,
    DiffResult,
)
from lyra.meta_editor.evolution_metrics import (
    EvolutionConfig,
    EvolutionCycle,
    EvolutionMetrics,
    EvolutionReport,
)
from lyra.meta_editor.exceptions import (
    ASTTransformationError,
    CodeAnalysisError,
    EvolutionMetricsError,
    MetaEditorError,
    MutationTestError,
    RewriteError,
    RollbackError,
    ValidationError,
)
from lyra.meta_editor.mutation_tester import (
    Mutant,
    MutationConfig,
    MutationTester,
    MutationTestResult,
)
from lyra.meta_editor.rollback_manager import (
    BackupRecord,
    RollbackManager,
    RollbackResult,
)
from lyra.meta_editor.safe_rewriter import (
    RewriteConfig,
    RewritePlan,
    RewriteResult,
    SafeRewriter,
)

__all__ = [
    # exceptions
    "MetaEditorError",
    "CodeAnalysisError",
    "ASTTransformationError",
    "RewriteError",
    "RollbackError",
    "ValidationError",
    "MutationTestError",
    "EvolutionMetricsError",
    # code_analyzer
    "AnalysisConfig",
    "CodeMetrics",
    "HotspotReport",
    "CodeAnalyzer",
    # ast_transformer
    "TransformConfig",
    "ASTNode",
    "TransformResult",
    "ASTTransformer",
    # safe_rewriter
    "RewriteConfig",
    "RewritePlan",
    "RewriteResult",
    "SafeRewriter",
    # rollback_manager
    "BackupRecord",
    "RollbackResult",
    "RollbackManager",
    # diff_generator
    "DiffConfig",
    "DiffHunk",
    "DiffResult",
    "DiffGenerator",
    # mutation_tester
    "MutationConfig",
    "Mutant",
    "MutationTestResult",
    "MutationTester",
    # evolution_metrics
    "EvolutionConfig",
    "EvolutionCycle",
    "EvolutionReport",
    "EvolutionMetrics",
]
