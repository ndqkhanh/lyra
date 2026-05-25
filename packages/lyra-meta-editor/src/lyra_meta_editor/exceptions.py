"""Meta-editor exception hierarchy."""

from __future__ import annotations


class MetaEditorError(Exception):
    """Base exception for all meta-editor errors."""


class CodeAnalysisError(MetaEditorError):
    """Raised when static code analysis fails."""


class ASTTransformationError(MetaEditorError):
    """Raised when AST-level code transformation fails."""


class RewriteError(MetaEditorError):
    """Raised when safe code rewrite fails."""


class RollbackError(MetaEditorError):
    """Raised when rollback operations fail."""


class ValidationError(MetaEditorError):
    """Raised when validation checks fail."""


class MutationTestError(MetaEditorError):
    """Raised when mutation testing fails."""


class EvolutionMetricsError(MetaEditorError):
    """Raised when evolution metrics operations fail."""
