"""Cursor target — emits ``.cursor/{rules,mcp.json}`` layout.

Reference: Cursor's rules feature (``.cursor/rules/*.md``) and
``.cursor/mcp.json`` MCP registry. Per-skill files keep frontmatter so
Cursor's progressive-disclosure picks them up.
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
class CursorExporter(Exporter):
    target = "cursor"

    def export(self, bundle: SourceBundle, *, target: Path) -> ExportManifest:
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest(target=self.target, target_root=target)
        bundle_slug = _slug(bundle.manifest.name)

        # 1. .cursor/rules/00-{bundle}.md — bundle-level rule.
        manifest.add(
            self._write(
                target,
                f".cursor/rules/00-{bundle_slug}.md",
                self._render_persona_rule(bundle),
            )
        )
        # 2. one rule file per skill.
        for i, skill in enumerate(bundle.skills, start=1):
            rel = f".cursor/rules/{bundle_slug}-{i:02d}-{_slug(skill.name)}.md"
            src = (bundle.root / skill.path).read_text(encoding="utf-8")
            manifest.add(self._write(target, rel, src))

        # 3. .cursor/mcp.json — idempotent merge.
        mcp_path = target / ".cursor" / "mcp.json"
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if mcp_path.exists():
            try:
                existing = json.loads(mcp_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        servers = existing.setdefault("mcpServers", {})
        for tool in bundle.tools:
            if tool.kind != "mcp" or not tool.server:
                continue
            key = f"{bundle_slug}-{_slug(tool.name)}"
            srv = tool.server or ""
            if srv.startswith("stdio:"):
                servers[key] = {"command": srv[len("stdio:"):]}
            else:
                servers[key] = {"url": srv}
        mcp_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        manifest.add(mcp_path)

        # 4. MANIFEST.
        man_path = target / f"MANIFEST.cursor.{bundle_slug}.txt"
        man_path.write_text(manifest.render(), encoding="utf-8")
        manifest.add(man_path)
        return manifest

    def _render_persona_rule(self, bundle: SourceBundle) -> str:
        return (
            "---\n"
            f"description: {bundle.manifest.description or bundle.manifest.name}\n"
            f"globs: ['**/*']\n"
            "alwaysApply: false\n"
            "---\n\n"
            f"# {bundle.manifest.name} v{bundle.manifest.version}\n\n"
            f"{bundle.persona.text.strip()}\n"
        )
