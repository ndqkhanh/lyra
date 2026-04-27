"""Real :class:`LSPBackend` backed by ``multilspy``.

``multilspy`` is a thin cross-language LSP client supporting pyright,
rust-analyzer, gopls, etc. We deliberately import it inside the
constructor so a default ``pip install lyra`` does not pull the dep.

When the package is not importable or fails to spin up (e.g. missing
language-server binary) we raise :class:`FeatureUnavailable` with an
install hint — callers can catch it and either fall back to
``MockLSPBackend`` or skip registering the ``lsp`` tool.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import FeatureUnavailable


class MultilspyBackend:
    """``multilspy`` bridge implementing :class:`LSPBackend`."""

    def __init__(
        self,
        *,
        language: str,
        repo_root: str | Path,
    ) -> None:
        try:
            import multilspy  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - depends on install
            raise FeatureUnavailable(
                "multilspy is not installed. "
                "Install the LSP extra with `pip install 'lyra[lsp]'` "
                f"(underlying error: {type(exc).__name__}: {exc})"
            ) from exc

        self._module = multilspy
        self._language = language
        self._repo_root = Path(repo_root)
        # The real multilspy session is started lazily on first op
        # so that construction never hits the filesystem or the
        # network (makes this class cheap to instantiate in tests).
        self._server: Any = None

    @property
    def language(self) -> str:
        return self._language

    # -- callable surface ------------------------------------------------- #

    def diagnostics(self, *, file: str, **_: Any) -> list[dict]:  # pragma: no cover
        self._ensure_started()
        return self._server.request_diagnostics(file)  # type: ignore[union-attr]

    def hover(self, *, file: str, line: int = 0, char: int = 0, **_: Any) -> str:  # pragma: no cover
        self._ensure_started()
        return self._server.request_hover(file, line, char) or ""  # type: ignore[union-attr]

    def references(
        self, *, file: str, line: int = 0, char: int = 0, **_: Any
    ) -> list[dict]:  # pragma: no cover
        self._ensure_started()
        return list(self._server.request_references(file, line, char) or [])  # type: ignore[union-attr]

    def definition(
        self, *, file: str, line: int = 0, char: int = 0, **_: Any
    ) -> dict | None:  # pragma: no cover
        self._ensure_started()
        return self._server.request_definition(file, line, char)  # type: ignore[union-attr]

    # -- internal -------------------------------------------------------- #

    def _ensure_started(self) -> None:  # pragma: no cover - runtime path
        if self._server is not None:
            return
        try:
            LanguageServer = self._module.LanguageServer  # type: ignore[attr-defined]
            self._server = LanguageServer.create(
                language=self._language,
                repository_root_path=str(self._repo_root),
            )
            self._server.start_server()
        except Exception as exc:
            raise FeatureUnavailable(
                f"Failed to start multilspy server for {self._language}: "
                f"{type(exc).__name__}: {exc}. "
                "Ensure the corresponding language server binary is on PATH."
            ) from exc


__all__ = ["MultilspyBackend"]
