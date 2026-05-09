"""Gemini CLI target — emits ``.gemini/extensions/{bundle}/`` layout.

Reference: Google's Gemini CLI extensions consume a directory with a
``gemini-extension.json`` manifest plus per-extension Markdown skills.
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
class GeminiCLIExporter(Exporter):
    target = "gemini-cli"

    def export(self, bundle: SourceBundle, *, target: Path) -> ExportManifest:
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest(target=self.target, target_root=target)
        bundle_slug = _slug(bundle.manifest.name)
        ext_root = f".gemini/extensions/{bundle_slug}"

        # 1. gemini-extension.json — Gemini CLI manifest.
        ext_meta = {
            "name": bundle.manifest.name,
            "version": bundle.manifest.version,
            "description": bundle.manifest.description,
            "contextFileName": "GEMINI.md",
            "mcpServers": {
                f"{bundle_slug}-{_slug(t.name)}": (
                    {"command": t.server[len('stdio:'):]}
                    if (t.server or "").startswith("stdio:")
                    else {"httpUrl": t.server}
                )
                for t in bundle.tools
                if t.kind == "mcp" and t.server
            },
        }
        manifest.add(
            self._write(
                target,
                f"{ext_root}/gemini-extension.json",
                json.dumps(ext_meta, indent=2),
            )
        )

        # 2. GEMINI.md — persona / context file.
        manifest.add(
            self._write(
                target,
                f"{ext_root}/GEMINI.md",
                self._render_context(bundle),
            )
        )

        # 3. one skill per bundle skill.
        for i, skill in enumerate(bundle.skills, start=1):
            rel = f"{ext_root}/skills/{i:02d}-{_slug(skill.name)}.md"
            src = (bundle.root / skill.path).read_text(encoding="utf-8")
            manifest.add(self._write(target, rel, src))

        # 4. MANIFEST.
        man_path = target / f"MANIFEST.gemini-cli.{bundle_slug}.txt"
        man_path.write_text(manifest.render(), encoding="utf-8")
        manifest.add(man_path)
        return manifest

    def _render_context(self, bundle: SourceBundle) -> str:
        return (
            f"# {bundle.manifest.name} v{bundle.manifest.version}\n\n"
            f"_(exported from Lyra bundle at v3.11)_\n\n"
            f"{bundle.persona.text.strip()}\n"
        )
