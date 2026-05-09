"""Common base + manifest helpers shared by every exporter."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..source_bundle import SourceBundle


ExportTarget = Literal["claude-code", "cursor", "codex", "gemini-cli"]


class ExportError(RuntimeError):
    """Raised when an exporter cannot complete (e.g. target dir escape)."""


@dataclass
class ExportManifest:
    """Record of every file written by an exporter."""

    target: ExportTarget
    target_root: Path
    files: list[Path] = field(default_factory=list)

    def add(self, p: Path) -> None:
        self.files.append(p)

    def render(self) -> str:
        lines = [
            f"# Lyra bundle export — target {self.target}",
            f"# rooted at {self.target_root}",
            "",
        ]
        for p in self.files:
            try:
                rel = p.resolve().relative_to(self.target_root.resolve())
            except ValueError:
                rel = p  # pragma: no cover (LBL-EXPORT-NO-LEAK already enforces)
            lines.append(str(rel))
        return "\n".join(lines) + "\n"


class Exporter(abc.ABC):
    """ABC every cross-harness exporter implements."""

    target: ExportTarget = "claude-code"

    @abc.abstractmethod
    def export(self, bundle: SourceBundle, *, target: Path) -> ExportManifest:
        """Write the bundle's projection into ``target``. Returns a manifest."""

    # ---- shared helpers --------------------------------------------

    def _safe_within(self, target: Path, candidate: Path) -> Path:
        """Enforce ``LBL-EXPORT-NO-LEAK`` — candidate must resolve within target."""
        target_r = target.resolve()
        candidate_r = candidate.resolve()
        try:
            candidate_r.relative_to(target_r)
        except ValueError as e:
            raise ExportError(
                f"export path {candidate} escapes target {target} (LBL-EXPORT-NO-LEAK)"
            ) from e
        return candidate_r

    def _write(self, target_root: Path, rel_path: str, contents: str) -> Path:
        full = self._safe_within(target_root, target_root / rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(contents, encoding="utf-8")
        return full


_REGISTRY: dict[ExportTarget, type[Exporter]] = {}


def register(cls: type[Exporter]) -> type[Exporter]:
    """Decorator: registers an exporter so :func:`resolve_exporter` finds it."""
    _REGISTRY[cls.target] = cls
    return cls


def resolve_exporter(target: ExportTarget) -> Exporter:
    cls = _REGISTRY.get(target)
    if cls is None:
        raise ExportError(
            f"unknown export target {target!r}; known: {sorted(_REGISTRY)}"
        )
    return cls()


def list_exporters() -> tuple[ExportTarget, ...]:
    return tuple(sorted(_REGISTRY.keys()))


__all__ = [
    "ExportError",
    "ExportManifest",
    "ExportTarget",
    "Exporter",
    "list_exporters",
    "register",
    "resolve_exporter",
]
