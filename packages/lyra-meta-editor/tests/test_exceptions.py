"""Tests for the exceptions module."""

from __future__ import annotations

import pytest

from lyra_meta_editor import (
    ASTTransformationError,
    CodeAnalysisError,
    EvolutionMetricsError,
    MetaEditorError,
    MutationTestError,
    RewriteError,
    RollbackError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Verify the exception class hierarchy."""

    def test_all_are_meta_editor_error_subclasses(self) -> None:
        assert issubclass(CodeAnalysisError, MetaEditorError)
        assert issubclass(ASTTransformationError, MetaEditorError)
        assert issubclass(RewriteError, MetaEditorError)
        assert issubclass(RollbackError, MetaEditorError)
        assert issubclass(ValidationError, MetaEditorError)
        assert issubclass(MutationTestError, MetaEditorError)
        assert issubclass(EvolutionMetricsError, MetaEditorError)

    def test_meta_editor_error_is_base(self) -> None:
        assert issubclass(MetaEditorError, Exception)

    def test_can_raise_and_catch_base(self) -> None:
        with pytest.raises(MetaEditorError):
            raise CodeAnalysisError("test error")

    def test_can_raise_and_catch_specific(self) -> None:
        with pytest.raises(RewriteError):
            raise RewriteError("rewrite failed")

    def test_error_message_is_preserved(self) -> None:
        msg = "some descriptive message"
        exc = ValidationError(msg)
        assert str(exc) == msg

    def test_error_with_empty_message(self) -> None:
        exc = CodeAnalysisError()
        assert str(exc) == ""

    def test_chained_exception(self) -> None:
        inner = ValueError("inner")
        outer = ASTTransformationError("wrapped", inner)
        assert ValueError in [type(a) for a in outer.args]

    def test_exception_can_be_subclassed(self) -> None:
        class SpecificRewriteError(RewriteError):
            pass

        assert issubclass(SpecificRewriteError, RewriteError)
        assert issubclass(SpecificRewriteError, MetaEditorError)

    def test_all_exceptions_caught_by_parent(self) -> None:
        exceptions = [
            CodeAnalysisError("a"),
            ASTTransformationError("b"),
            RewriteError("c"),
            RollbackError("d"),
            ValidationError("e"),
            MutationTestError("f"),
            EvolutionMetricsError("g"),
        ]
        for exc in exceptions:
            assert isinstance(exc, MetaEditorError)

    def test_exceptions_are_hashable(self) -> None:
        exc = RollbackError("hashable")
        _ = {exc: True}

    def test_base_exception_is_not_abstract(self) -> None:
        MetaEditorError("direct instantiation works")

    def test_exception_repr(self) -> None:
        exc = MutationTestError("my message")
        r = repr(exc)
        assert "MutationTestError" in r
        assert "my message" in r

    def test_similar_names_are_distinct(self) -> None:
        assert CodeAnalysisError is not ASTTransformationError
        assert RewriteError is not RollbackError

    def test_multiple_args(self) -> None:
        exc = ValidationError("one", "two")
        assert exc.args == ("one", "two")

    def test_exception_with_none_message(self) -> None:
        exc = EvolutionMetricsError(None)
        assert exc.args == (None,)

    def test_exceptions_are_picklable(self) -> None:
        import pickle
        exc = CodeAnalysisError("pickle test")
        restored = pickle.loads(pickle.dumps(exc))
        assert str(restored) == "pickle test"

    def test_meta_editor_error_cannot_catch_unrelated(self) -> None:
        with pytest.raises(MetaEditorError):
            raise CodeAnalysisError("related")
        with pytest.raises(MetaEditorError):
            raise ASTTransformationError("related too")

    def test_exception_stores_traceback_on_raise(self) -> None:
        try:
            raise RewriteError("traceback test")
        except RewriteError as e:
            assert e.__traceback__ is not None

    def test_all_exported_in___all__(self) -> None:
        from lyra_meta_editor import __all__
        assert "MetaEditorError" in __all__
        assert "CodeAnalysisError" in __all__
        assert "ASTTransformationError" in __all__
        assert "RewriteError" in __all__
        assert "RollbackError" in __all__
        assert "ValidationError" in __all__
        assert "MutationTestError" in __all__
        assert "EvolutionMetricsError" in __all__
