"""Optional LSP tool (plan Phase 7, opencode pattern).

Wraps an LSP client (``multilspy`` preferred, ``pygls`` fallback) and
exposes the minimum surface an agent needs:

- ``lsp(operation="diagnostics", file=..., line=..., char=...)``
- ``lsp(operation="hover", file=..., line=..., char=...)``
- ``lsp(operation="references", file=..., line=..., char=...)``
- ``lsp(operation="definition", file=..., line=..., char=...)``

Diagnostics are wrapped in ``<diagnostics file="...">...</diagnostics>``
XML so they sit naturally next to the model's own text output (opencode's
context-injection convention).

**This tool is off by default.** Callers must opt in via
:func:`make_lsp_tool` (project config or ``--lsp`` flag); the builder
raises :class:`LSPUnavailable` if no LSP backend can be imported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping

LSPOperation = Literal["diagnostics", "hover", "references", "definition"]


class LSPUnavailable(RuntimeError):
    """Raised when no LSP backend is available to build the tool."""


@dataclass
class LSPBackend:
    """Thin adapter surface so tests can inject fakes."""

    diagnostics: Callable[..., list[dict]]
    hover: Callable[..., str]
    references: Callable[..., list[dict]]
    definition: Callable[..., dict | None]
    language: str = ""


def _format_diagnostics_xml(*, file: str, diagnostics: list[dict]) -> str:
    if not diagnostics:
        return f"<diagnostics file={file!r}/>"
    rows = []
    for d in diagnostics:
        line = d.get("line") or d.get("range", {}).get("start", {}).get("line", 0)
        severity = d.get("severity", "info")
        message = d.get("message", "")
        rows.append(
            f'  <diagnostic line="{int(line)}" severity="{severity}">{message}</diagnostic>'
        )
    body = "\n".join(rows)
    return f'<diagnostics file="{file}">\n{body}\n</diagnostics>'


def _auto_backend() -> LSPBackend | None:
    """Best-effort detection of a usable LSP backend.

    The lyra LSP surface is intentionally narrow; the returned
    backend just exposes enough of the protocol for the agent's
    in-context injection. If neither multilspy nor pygls is installed,
    returns ``None`` so the factory can raise :class:`LSPUnavailable`.
    """
    # multilspy first — higher-level, closer to our tool surface.
    try:
        import importlib

        importlib.import_module("multilspy")
    except Exception:
        pass
    else:  # pragma: no cover - depends on install
        return _build_multilspy_backend()

    try:
        import importlib

        importlib.import_module("pygls")
    except Exception:
        return None
    else:  # pragma: no cover - depends on install
        return _build_pygls_backend()


def _build_multilspy_backend() -> LSPBackend:  # pragma: no cover - depends on install
    """Real multilspy wiring — implemented lazily because the dep is optional."""

    def _not_impl(*_a: Any, **_k: Any) -> Any:
        raise LSPUnavailable(
            "multilspy detected but wiring not finalized in this build"
        )

    return LSPBackend(
        diagnostics=_not_impl,
        hover=_not_impl,
        references=_not_impl,
        definition=_not_impl,
        language="auto",
    )


def _build_pygls_backend() -> LSPBackend:  # pragma: no cover - depends on install
    def _not_impl(*_a: Any, **_k: Any) -> Any:
        raise LSPUnavailable("pygls backend not finalized in this build")

    return LSPBackend(
        diagnostics=_not_impl,
        hover=_not_impl,
        references=_not_impl,
        definition=_not_impl,
        language="auto",
    )


def make_lsp_tool(
    *,
    backend: LSPBackend | None = None,
) -> Callable[..., dict]:
    """Build the LLM-callable ``lsp`` tool.

    Args:
        backend: Injected adapter. When omitted, attempts auto-detection
            via :func:`_auto_backend`; raises :class:`LSPUnavailable` if
            none is installed — the caller (CLI flag handler) can then
            skip registering the tool.
    """
    adapter = backend if backend is not None else _auto_backend()
    if adapter is None:
        raise LSPUnavailable(
            "No LSP backend found. Install multilspy or pygls, or pass backend=..."
        )

    def lsp(
        operation: LSPOperation = "diagnostics",
        *,
        file: str,
        line: int = 0,
        char: int = 0,
    ) -> dict:
        """Run an LSP operation and return a dict the LLM can read."""
        if operation == "diagnostics":
            diags = adapter.diagnostics(file=file)
            return {
                "operation": operation,
                "file": file,
                "xml": _format_diagnostics_xml(file=file, diagnostics=diags),
                "raw": diags,
            }
        if operation == "hover":
            return {
                "operation": operation,
                "file": file,
                "text": adapter.hover(file=file, line=line, char=char),
            }
        if operation == "references":
            return {
                "operation": operation,
                "file": file,
                "results": adapter.references(file=file, line=line, char=char),
            }
        if operation == "definition":
            return {
                "operation": operation,
                "file": file,
                "result": adapter.definition(file=file, line=line, char=char),
            }
        return {"operation": operation, "error": f"unknown LSP operation {operation!r}"}

    lsp.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "lsp",
        "description": (
            "Query the language server (diagnostics, hover, references, "
            "definition). Off by default; enable with --lsp or config.toml."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["diagnostics", "hover", "references", "definition"],
                },
                "file": {"type": "string"},
                "line": {"type": "integer", "minimum": 0},
                "char": {"type": "integer", "minimum": 0},
            },
            "required": ["file"],
        },
    }
    return lsp


__all__ = [
    "LSPBackend",
    "LSPOperation",
    "LSPUnavailable",
    "make_lsp_tool",
]
