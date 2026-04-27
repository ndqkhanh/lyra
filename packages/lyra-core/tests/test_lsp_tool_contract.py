"""Contract tests for the optional LSP tool (opencode parity, v1 Phase 7).

The ``lsp`` tool is off by default and built via
:func:`lyra_core.tools.lsp.make_lsp_tool`. When called with an injected
:class:`~lyra_core.tools.lsp.LSPBackend`, the resulting callable must:

1. Expose a JSON schema via ``__tool_schema__`` so the agent loop's
   ``_tool_defs`` can advertise it to the LLM.
2. Route operations (``diagnostics`` / ``hover`` / ``references`` /
   ``definition``) to the backend.
3. Format diagnostics into opencode's ``<diagnostics file="..."> ...
   </diagnostics>`` XML envelope so the result injects cleanly into
   the model's context.

The RED-first shape also includes the explicit failure mode:
:class:`~lyra_core.tools.lsp.LSPUnavailable` is raised when no backend
can be auto-detected AND the caller did not supply one — this is what
makes the tool safe to register only when the user actually opts in.
"""
from __future__ import annotations

import pytest

from lyra_core.tools.lsp import LSPBackend, LSPUnavailable, make_lsp_tool


def _fake_backend() -> LSPBackend:
    return LSPBackend(
        diagnostics=lambda file: [
            {"line": 3, "severity": "error", "message": "Missing semicolon"},
            {"line": 8, "severity": "warning", "message": "Unused import"},
        ],
        hover=lambda file, line, char: f"hover:{file}:{line}:{char}",
        references=lambda file, line, char: [
            {"file": file, "line": line + 1, "char": 0},
            {"file": file, "line": line + 5, "char": 2},
        ],
        definition=lambda file, line, char: {
            "file": file, "line": 42, "char": 0
        },
        language="python",
    )


def test_tool_exposes_schema_for_agent_loop() -> None:
    """The tool must ship a ``__tool_schema__`` so ``_tool_defs`` sees it."""
    tool = make_lsp_tool(backend=_fake_backend())
    schema = getattr(tool, "__tool_schema__", None)
    assert schema is not None, "lsp tool must expose __tool_schema__"
    assert schema["name"] == "lsp"
    params = schema["parameters"]
    assert "file" in params["required"]
    assert set(params["properties"]["operation"]["enum"]) == {
        "diagnostics", "hover", "references", "definition",
    }


def test_diagnostics_returns_opencode_style_xml_envelope() -> None:
    """Diagnostics result must include the ``<diagnostics file=...>`` XML.

    This is what lets the agent loop drop the result straight into the
    next LLM prompt without reformatting — opencode's contract.
    """
    tool = make_lsp_tool(backend=_fake_backend())
    result = tool(operation="diagnostics", file="src/foo.py")
    assert result["operation"] == "diagnostics"
    assert result["file"] == "src/foo.py"
    xml = result["xml"]
    assert xml.startswith('<diagnostics file="src/foo.py">'), xml
    assert 'severity="error"' in xml
    assert "Missing semicolon" in xml
    # Raw list is still available for programmatic callers.
    assert len(result["raw"]) == 2


def test_hover_references_definition_delegate_to_backend() -> None:
    tool = make_lsp_tool(backend=_fake_backend())

    hover = tool(operation="hover", file="a.py", line=1, char=0)
    assert hover["text"] == "hover:a.py:1:0"

    refs = tool(operation="references", file="a.py", line=2, char=0)
    assert len(refs["results"]) == 2
    assert refs["results"][0]["line"] == 3

    defn = tool(operation="definition", file="a.py", line=10, char=3)
    assert defn["result"]["line"] == 42


def test_unknown_operation_surfaces_error_not_crash() -> None:
    """Unknown operations return ``{"error": ...}`` so the loop records them.

    If this ever started raising, the agent loop's ``post_tool_call``
    would see the synthesised error dict, which is still observable —
    but returning a plain dict lets the LLM self-correct rather than
    the loop aborting the turn.
    """
    tool = make_lsp_tool(backend=_fake_backend())
    result = tool(operation="gibberish", file="a.py")  # type: ignore[arg-type]
    assert "error" in result


def test_no_backend_and_no_auto_detection_raises_unavailable() -> None:
    """Opt-in contract: without a backend, the factory must raise.

    Auto-detection only finds a backend when ``multilspy`` or ``pygls``
    is installed; on the bare pytest env (no LSP deps), the factory
    must raise :class:`LSPUnavailable` so the CLI can gracefully skip
    registering the tool.
    """
    # We can't reliably monkey-patch the auto-detection without making
    # the test env-sensitive, but we can assert the exception exists as
    # a public symbol and that the factory honours the explicit None.
    assert issubclass(LSPUnavailable, RuntimeError)
    # If the backend arg is missing AND auto-detect returns None, the
    # factory must raise. We simulate auto-detect returning None by
    # monkey-patching via the module namespace.
    import lyra_core.tools.lsp as _lsp

    original = _lsp._auto_backend
    try:
        _lsp._auto_backend = lambda: None  # type: ignore[assignment]
        with pytest.raises(LSPUnavailable):
            make_lsp_tool()
    finally:
        _lsp._auto_backend = original  # type: ignore[assignment]
