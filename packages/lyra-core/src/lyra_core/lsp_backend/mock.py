"""In-memory :class:`LSPBackend` with canned payloads for unit tests.

The adapter surface defined by :class:`lyra_core.tools.lsp.LSPBackend`
is a dataclass with four callables. This mock is a thin wrapper that
returns pre-seeded values so tests can exercise ``make_lsp_tool``
end-to-end without running a real language server.
"""
from __future__ import annotations

from typing import Any, Mapping


class MockLSPBackend:
    """Canned-response LSP backend.

    Args:
        diagnostics_for: ``{file: [diagnostic_dict, ...]}`` lookup.
        hover_for: ``{(file, line, char): hover_text}`` lookup.
        references_for: ``{(file, line, char): [ref_dict, ...]}``.
        definition_for: ``{(file, line, char): def_dict | None}``.
        language: Optional language hint surfaced on the adapter.
    """

    def __init__(
        self,
        *,
        diagnostics_for: Mapping[str, list[dict]] | None = None,
        hover_for: Mapping[tuple[str, int, int], str] | None = None,
        references_for: Mapping[tuple[str, int, int], list[dict]] | None = None,
        definition_for: Mapping[tuple[str, int, int], dict | None] | None = None,
        language: str = "",
    ) -> None:
        self._diagnostics = dict(diagnostics_for or {})
        self._hover = dict(hover_for or {})
        self._references = dict(references_for or {})
        self._definition = dict(definition_for or {})
        self.language = language

    # Callable attributes — must match the LSPBackend dataclass shape.

    def diagnostics(self, *, file: str, **_: Any) -> list[dict]:
        return list(self._diagnostics.get(file, []))

    def hover(self, *, file: str, line: int = 0, char: int = 0, **_: Any) -> str:
        return self._hover.get((file, line, char), "")

    def references(
        self, *, file: str, line: int = 0, char: int = 0, **_: Any
    ) -> list[dict]:
        return list(self._references.get((file, line, char), []))

    def definition(
        self, *, file: str, line: int = 0, char: int = 0, **_: Any
    ) -> dict | None:
        return self._definition.get((file, line, char))


__all__ = ["MockLSPBackend"]
