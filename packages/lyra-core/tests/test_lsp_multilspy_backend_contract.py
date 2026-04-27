"""Contract tests for the v1.7.3 LSP backend layer.

Two concrete backends land under ``lyra_core.lsp_backend``:

- :class:`MockLSPBackend` — canned diagnostics/hover/references for
  unit tests that need to exercise ``make_lsp_tool`` end-to-end
  without installing ``multilspy`` or a real language server.
- :class:`MultilspyBackend` — real bridge to ``multilspy``. When the
  package is not importable, constructing it raises
  :class:`FeatureUnavailable` with an install hint.

Invariants tested:

- :class:`MockLSPBackend` satisfies the :class:`LSPBackend` adapter
  protocol (has the four callables + ``language`` attr).
- ``make_lsp_tool(backend=MockLSPBackend(...))`` wires correctly:
  dispatch of each op returns the mock's canned payload.
- :class:`MultilspyBackend` imports as a name from the package but
  raises :class:`FeatureUnavailable` at construction time when
  ``multilspy`` is not installed.
- The error carries the standard ``pip install lyra[lsp]`` guidance.
- Swapping backends on ``make_lsp_tool`` does not require any code
  change in the tool (backend injection).
"""
from __future__ import annotations

import sys
from unittest import mock

import pytest

from lyra_core.lsp_backend import (
    FeatureUnavailable,
    MockLSPBackend,
    MultilspyBackend,
)
from lyra_core.tools.lsp import LSPBackend, make_lsp_tool


# ---- MockLSPBackend satisfies adapter shape ----------------------- #


def test_mock_backend_satisfies_adapter_shape() -> None:
    mb = MockLSPBackend()

    assert callable(mb.diagnostics)
    assert callable(mb.hover)
    assert callable(mb.references)
    assert callable(mb.definition)
    assert hasattr(mb, "language")


def test_mock_backend_round_trips_canned_values() -> None:
    mb = MockLSPBackend(
        diagnostics_for={"foo.py": [{"line": 3, "severity": "error", "message": "boom"}]},
        hover_for={("foo.py", 3, 0): "foo(x: int)"},
        references_for={("foo.py", 3, 0): [{"file": "bar.py", "line": 10, "char": 0}]},
        definition_for={("foo.py", 3, 0): {"file": "foo.py", "line": 1, "char": 4}},
        language="python",
    )

    assert mb.diagnostics(file="foo.py") == [
        {"line": 3, "severity": "error", "message": "boom"}
    ]
    assert mb.hover(file="foo.py", line=3, char=0) == "foo(x: int)"
    assert mb.references(file="foo.py", line=3, char=0) == [
        {"file": "bar.py", "line": 10, "char": 0}
    ]
    assert mb.definition(file="foo.py", line=3, char=0) == {
        "file": "foo.py",
        "line": 1,
        "char": 4,
    }


def test_mock_backend_defaults_to_empty_for_missing_keys() -> None:
    mb = MockLSPBackend()

    assert mb.diagnostics(file="unknown.py") == []
    assert mb.hover(file="unknown.py", line=0, char=0) == ""
    assert mb.references(file="unknown.py", line=0, char=0) == []
    assert mb.definition(file="unknown.py", line=0, char=0) is None


# ---- tool wiring via injected backend ----------------------------- #


def test_tool_wiring_with_mock_backend_end_to_end() -> None:
    mb = MockLSPBackend(
        diagnostics_for={
            "a.py": [{"line": 1, "severity": "error", "message": "bad"}]
        },
    )
    tool = make_lsp_tool(backend=mb)

    result = tool(operation="diagnostics", file="a.py")

    assert result["file"] == "a.py"
    assert "<diagnostics" in result["xml"]
    assert result["raw"] == [
        {"line": 1, "severity": "error", "message": "bad"}
    ]


# ---- MultilspyBackend raises FeatureUnavailable cleanly ----------- #


def test_multilspy_backend_raises_feature_unavailable_without_package() -> None:
    """With ``multilspy`` not importable, constructing the backend
    surfaces :class:`FeatureUnavailable` (not a raw ImportError) so the
    caller can branch on a known sentinel.
    """
    # Force the multilspy import to fail deterministically.
    saved = sys.modules.get("multilspy")
    sys.modules["multilspy"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable) as excinfo:
            MultilspyBackend(language="python", repo_root=".")
        # Error must mention how to fix it.
        msg = str(excinfo.value).lower()
        assert "multilspy" in msg or "lyra[lsp]" in msg
    finally:
        if saved is None:
            sys.modules.pop("multilspy", None)
        else:
            sys.modules["multilspy"] = saved


# ---- adapter Protocol compatibility ------------------------------- #


def test_mock_backend_plugs_into_lspbackend_protocol() -> None:
    """Any callable-set that matches :class:`LSPBackend` is acceptable —
    we verify the mock is a drop-in replacement via a plain isinstance-free
    structural check that the tool constructor relies on.
    """
    mb = MockLSPBackend(language="python")
    # Demonstrate that the tool accepts the mock as-is — no cast needed.
    tool = make_lsp_tool(backend=mb)
    assert callable(tool)
