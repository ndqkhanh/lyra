"""Cross-harness ``AGENTS.md`` catalog exporter (Phase CE.3, P2-3).

ECC's pattern: a single ``AGENTS.md`` at the repo root that all four
harnesses (Claude Code, Codex, Cursor, OpenCode) read as their
universal catalog. Per-harness supplements live in ``.claude/``,
``.cursor/``, etc.

This module is the *exporter*: take lyra's in-process registry of
skills / agents / rules and render it as the cross-harness-compatible
markdown. No runtime semantics — every consumer of the file decides
for itself how to load each entry.

Lives in :mod:`lyra_core.adapters` (not ``context/``) because the
audience is the *other* harnesses, not lyra's own context engine.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CatalogEntry:
    """One row in the cross-harness catalog."""

    name: str
    kind: str  # "skill" | "agent" | "rule" | "command"
    summary: str
    path: str = ""  # repo-relative path, when applicable
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("CatalogEntry.name must be non-empty")
        if self.kind not in {"skill", "agent", "rule", "command"}:
            raise ValueError(
                f"CatalogEntry.kind must be skill|agent|rule|command; "
                f"got {self.kind!r}"
            )
        if not self.summary or not self.summary.strip():
            raise ValueError("CatalogEntry.summary must be non-empty")


@dataclass
class AgentsManifest:
    """In-memory shape of the catalog."""

    project_name: str = "lyra"
    description: str = ""
    entries: list[CatalogEntry] = field(default_factory=list)

    def add(self, entry: CatalogEntry) -> None:
        self.entries.append(entry)

    def by_kind(self, kind: str) -> list[CatalogEntry]:
        return [e for e in self.entries if e.kind == kind]


_KIND_ORDER = ("skill", "agent", "command", "rule")
_KIND_TITLES = {
    "skill": "Skills",
    "agent": "Agents",
    "command": "Commands",
    "rule": "Rules",
}


def render_manifest(manifest: AgentsManifest) -> str:
    """Render the manifest as cross-harness AGENTS.md markdown."""
    lines: list[str] = [f"# {manifest.project_name.upper()} — agents catalog"]
    if manifest.description:
        lines += ["", manifest.description.strip()]
    lines += [
        "",
        "_Universal catalog readable by Claude Code, Codex, Cursor, "
        "OpenCode, and any harness that follows the ECC convention. "
        "Per-harness supplements live alongside this file._",
        "",
    ]
    for kind in _KIND_ORDER:
        rows = sorted(manifest.by_kind(kind), key=lambda e: e.name)
        if not rows:
            continue
        lines.append(f"## {_KIND_TITLES[kind]}")
        lines.append("")
        for entry in rows:
            anchor = f"`{entry.name}`"
            summary = entry.summary.strip()
            line = f"- {anchor} — {summary}"
            if entry.path:
                line += f" ([source]({entry.path}))"
            if entry.tags:
                line += f"  *tags: {', '.join(entry.tags)}*"
            lines.append(line)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_manifest(manifest: AgentsManifest, *, target_path: str) -> str:
    """Render and write to ``target_path``. Returns the rendered body."""
    body = render_manifest(manifest)
    from pathlib import Path

    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return body


def manifest_from_lyra_registries(
    *,
    skills: Sequence[tuple[str, str, str]] = (),  # (name, summary, path)
    agents: Sequence[tuple[str, str, str]] = (),
    commands: Sequence[tuple[str, str]] = (),  # (name, summary)
    rules: Sequence[tuple[str, str, str]] = (),
    project_name: str = "lyra",
    description: str = "",
) -> AgentsManifest:
    """Build a manifest from simple tuple lists.

    Kept tuple-shaped so the call site (a CLI command, a CI export
    job, …) can feed whatever it has without coupling to lyra's
    in-process registry types.
    """
    manifest = AgentsManifest(
        project_name=project_name, description=description
    )
    for name, summary, path in skills:
        manifest.add(
            CatalogEntry(
                name=name, kind="skill", summary=summary, path=path
            )
        )
    for name, summary, path in agents:
        manifest.add(
            CatalogEntry(
                name=name, kind="agent", summary=summary, path=path
            )
        )
    for name, summary in commands:
        manifest.add(
            CatalogEntry(name=name, kind="command", summary=summary)
        )
    for name, summary, path in rules:
        manifest.add(
            CatalogEntry(name=name, kind="rule", summary=summary, path=path)
        )
    return manifest


__all__ = [
    "AgentsManifest",
    "CatalogEntry",
    "manifest_from_lyra_registries",
    "render_manifest",
    "write_manifest",
]
