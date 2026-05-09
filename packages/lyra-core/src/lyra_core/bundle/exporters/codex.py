"""Codex target — emits ``~/.codex/skills/{bundle}/`` layout.

OpenAI Codex CLI consumes Markdown skill files in ``~/.codex/skills/``;
each subdirectory is a "skill bundle" that Codex picks up automatically.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..source_bundle import SourceBundle
from .base import Exporter, ExportManifest, register


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    return _SLUG_RE.sub("-", s.lower()).strip("-") or "bundle"


@register
class CodexExporter(Exporter):
    target = "codex"

    def export(self, bundle: SourceBundle, *, target: Path) -> ExportManifest:
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest(target=self.target, target_root=target)
        bundle_slug = _slug(bundle.manifest.name)

        # 1. skills/<bundle>/AGENTS.md (Codex's persona convention).
        manifest.add(
            self._write(
                target,
                f"skills/{bundle_slug}/AGENTS.md",
                self._render_agents_md(bundle),
            )
        )
        # 2. one skill file per bundle skill.
        for i, skill in enumerate(bundle.skills, start=1):
            rel = f"skills/{bundle_slug}/{i:02d}-{_slug(skill.name)}.md"
            src = (bundle.root / skill.path).read_text(encoding="utf-8")
            manifest.add(self._write(target, rel, src))

        # 3. config/mcp.{bundle}.json — Codex MCP registry sidecar.
        mcp_entries = []
        for tool in bundle.tools:
            if tool.kind != "mcp" or not tool.server:
                continue
            mcp_entries.append(
                {
                    "name": f"{bundle_slug}-{_slug(tool.name)}",
                    "server": tool.server,
                }
            )
        if mcp_entries:
            manifest.add(
                self._write(
                    target,
                    f"config/mcp.{bundle_slug}.json",
                    json.dumps({"servers": mcp_entries}, indent=2),
                )
            )

        # 4. MANIFEST.
        man_path = target / f"MANIFEST.codex.{bundle_slug}.txt"
        man_path.write_text(manifest.render(), encoding="utf-8")
        manifest.add(man_path)
        return manifest

    def _render_agents_md(self, bundle: SourceBundle) -> str:
        return (
            f"# {bundle.manifest.name} v{bundle.manifest.version}\n\n"
            f"_(exported from Lyra bundle at v3.11)_\n\n"
            f"{bundle.persona.text.strip()}\n\n"
            "## Skills in this bundle\n\n"
            + "\n".join(f"- **{s.name}** — {s.description}" for s in bundle.skills)
            + "\n"
        )
