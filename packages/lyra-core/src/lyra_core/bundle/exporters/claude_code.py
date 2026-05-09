"""Claude Code target — emits ``~/.claude/{skills,agents,settings}/`` layout.

Reference: [`docs/04-skills.md`](../../../../../../../docs/04-skills.md),
[`docs/02-subagent-delegation.md`](../../../../../../../docs/02-subagent-delegation.md),
[`docs/06-permission-modes.md`](../../../../../../../docs/06-permission-modes.md),
[`docs/07-model-context-protocol.md`](../../../../../../../docs/07-model-context-protocol.md).

Layout written under ``target``::

    skills/{bundle.name}/
      00-bundle.md            # bundle persona as a top-level skill
      01-{slug}.md ...         # one file per bundle skill, frontmatter retained
    agents/{bundle.name}.md   # Claude Code subagent definition
    settings.local.json       # patched MCP server registry (idempotent merge)
    MANIFEST.txt              # files emitted by this run
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..source_bundle import SourceBundle, ToolSpec
from .base import Exporter, ExportManifest, register


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    return _SLUG_RE.sub("-", s.lower()).strip("-") or "bundle"


@register
class ClaudeCodeExporter(Exporter):
    target = "claude-code"

    def export(self, bundle: SourceBundle, *, target: Path) -> ExportManifest:
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest(target=self.target, target_root=target)
        bundle_slug = _slug(bundle.manifest.name)

        # 1. skills/{name}/00-bundle.md — bundle-level persona as skill 00.
        bundle_skill_dir = target / "skills" / bundle_slug
        manifest.add(
            self._write(
                target,
                f"skills/{bundle_slug}/00-bundle.md",
                self._render_bundle_skill(bundle),
            )
        )

        # 2. skills/{name}/<idx>-<slug>.md per bundle skill.
        for i, skill in enumerate(bundle.skills, start=1):
            rel = f"skills/{bundle_slug}/{i:02d}-{_slug(skill.name)}.md"
            src = (bundle.root / skill.path).read_text(encoding="utf-8")
            manifest.add(self._write(target, rel, src))

        # 3. agents/<name>.md subagent definition (Claude Code subagent shape).
        manifest.add(
            self._write(
                target,
                f"agents/{bundle_slug}.md",
                self._render_subagent(bundle, bundle_slug),
            )
        )

        # 4. settings.local.json idempotent merge — adds MCP servers to the
        # mcpServers section.
        settings_path = target / "settings.local.json"
        merged = self._merge_settings(settings_path, bundle, bundle_slug)
        settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        manifest.add(settings_path)

        # 5. MANIFEST.txt audit trail.
        man_path = target / f"MANIFEST.{bundle_slug}.txt"
        man_path.write_text(manifest.render(), encoding="utf-8")
        manifest.add(man_path)
        return manifest

    # ---- renderers ----------------------------------------------

    def _render_bundle_skill(self, bundle: SourceBundle) -> str:
        return (
            "---\n"
            f"name: {bundle.manifest.name}\n"
            f"description: {bundle.manifest.description or bundle.manifest.name}\n"
            "---\n\n"
            f"# {bundle.manifest.name} (v{bundle.manifest.version})\n\n"
            f"{bundle.persona.text.strip()}\n"
        )

    def _render_subagent(self, bundle: SourceBundle, bundle_slug: str) -> str:
        skill_names = ", ".join(s.name for s in bundle.skills) or "—"
        tool_lines = [
            f"- {t.kind}:{t.name}"
            + (f" (via `{t.server}`)" if t.server else "")
            for t in bundle.tools
        ]
        return (
            "---\n"
            f"name: {bundle_slug}\n"
            f"description: {bundle.manifest.description or bundle.manifest.name}\n"
            "---\n\n"
            f"# {bundle.manifest.name}\n\n"
            f"{bundle.persona.text.strip()}\n\n"
            "## Skills available\n"
            f"{skill_names}\n\n"
            "## Tools wired\n"
            + ("\n".join(tool_lines) or "—")
            + "\n"
        )

    def _merge_settings(
        self, settings_path: Path, bundle: SourceBundle, bundle_slug: str
    ) -> dict:
        existing: dict = {}
        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        servers = existing.setdefault("mcpServers", {})
        for tool in bundle.tools:
            if tool.kind != "mcp" or not tool.server:
                continue
            key = f"{bundle_slug}-{_slug(tool.name)}"
            servers[key] = self._mcp_server_entry(tool)
        return existing

    def _mcp_server_entry(self, tool: ToolSpec) -> dict:
        # Server descriptors look like "stdio:./mcp/server.py" or
        # "http://host:port/mcp". We keep the raw form under "url" /
        # "command" keys so Claude Code recognises both.
        server = tool.server or ""
        if server.startswith("stdio:"):
            return {"command": server[len("stdio:"):]}
        return {"url": server}
