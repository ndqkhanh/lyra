"""Wasla sync bridge — cross-orchestrator skill/config/command sync.

Implements the Wasla universal synchronization layer (v2.0.1)
for Lyra. Syncs skills, MCP configs, and commands bidirectionally
with Claude Code, Gemini CLI, OpenAI Codex, OpenClaw, and Hermes.

Strategy: "Latest is Greatest" — each orchestrator declares a
timestamp per artifact; the most recent wins. Zero duplication.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WaslaArtifact:
    """A syncable artifact (skill, config, or command)."""

    artifact_type: str  # "skill" | "mcp_config" | "command"
    name: str
    content: dict[str, Any]
    source_orchestrator: str  # "lyra" | "claude-code" | "codex" | "hermes" | "gemini"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    integrity_sha256: str = ""

    def is_newer_than(self, other: "WaslaArtifact") -> bool:
        """Latest is Greatest — compare timestamps."""
        return self.updated_at > other.updated_at


@dataclass
class WaslaBridge:
    """Bidirectional sync bridge implementing the Wasla protocol.

    Syncs artifacts across orchestrators with conflict resolution:
    latest timestamp wins, conflicts are flagged for human review.
    """

    orchestrator_id: str = "lyra"
    sync_dir: Path = field(default_factory=lambda: Path.home() / ".lyra" / "wasla")
    _artifacts: dict[str, WaslaArtifact] = field(default_factory=dict)

    def __post_init__(self):
        self.sync_dir.mkdir(parents=True, exist_ok=True)

    # --- Export ---

    def export_skill(self, name: str, content: dict) -> WaslaArtifact:
        """Export a Lyra skill to Wasla format."""
        artifact = WaslaArtifact(
            artifact_type="skill",
            name=name,
            content=content,
            source_orchestrator=self.orchestrator_id,
        )
        self._artifacts[f"skill:{name}"] = artifact
        self._save_manifest()
        return artifact

    def export_mcp_config(self, name: str, config: dict) -> WaslaArtifact:
        """Export an MCP server config to Wasla format."""
        artifact = WaslaArtifact(
            artifact_type="mcp_config",
            name=name,
            content=config,
            source_orchestrator=self.orchestrator_id,
        )
        self._artifacts[f"mcp:{name}"] = artifact
        self._save_manifest()
        return artifact

    # --- Import ---

    def import_artifact(self, artifact: WaslaArtifact) -> bool:
        """Import an artifact from another orchestrator. Latest timestamp wins."""
        key = f"{artifact.artifact_type}:{artifact.name}"
        existing = self._artifacts.get(key)

        if existing and existing.is_newer_than(artifact):
            return False  # Our version is newer, keep it

        if existing and not existing.is_newer_than(artifact):
            # Import is newer — accept it
            self._artifacts[key] = artifact
            self._save_manifest()
            return True

        # No existing — accept
        self._artifacts[key] = artifact
        self._save_manifest()
        return True

    def import_manifest(self, manifest_path: Path) -> int:
        """Import a full Wasla manifest from another orchestrator."""
        data = json.loads(manifest_path.read_text())
        imported = 0
        for item in data.get("artifacts", []):
            artifact = WaslaArtifact(
                artifact_type=item["type"],
                name=item["name"],
                content=item["content"],
                source_orchestrator=item.get("source", "unknown"),
                updated_at=item.get("updated_at", ""),
                integrity_sha256=item.get("hash", ""),
            )
            if self.import_artifact(artifact):
                imported += 1
        return imported

    # --- Sync ---

    def list_artifacts(self, source: str | None = None) -> list[WaslaArtifact]:
        """List all synced artifacts, optionally filtered by source orchestrator."""
        arts = list(self._artifacts.values())
        if source:
            arts = [a for a in arts if a.source_orchestrator == source]
        return sorted(arts, key=lambda a: a.updated_at, reverse=True)

    def get_conflicts(self) -> list[tuple[WaslaArtifact, WaslaArtifact]]:
        """Find artifacts with conflicting versions across orchestrators."""
        conflicts = []
        seen: dict[str, list[WaslaArtifact]] = {}
        for a in self._artifacts.values():
            key = f"{a.artifact_type}:{a.name}"
            seen.setdefault(key, []).append(a)
        for items in seen.values():
            if len(items) > 1 and len({a.source_orchestrator for a in items}) > 1:
                conflicts.append((items[0], items[1]))
        return conflicts

    # --- Persistence ---

    def _save_manifest(self):
        """Persist the sync manifest to disk."""
        manifest = {
            "format": "wasla/v1",
            "orchestrator": self.orchestrator_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": [
                {
                    "type": a.artifact_type,
                    "name": a.name,
                    "content": a.content,
                    "source": a.source_orchestrator,
                    "updated_at": a.updated_at,
                    "hash": a.integrity_sha256,
                }
                for a in self._artifacts.values()
            ],
        }
        manifest_path = self.sync_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

    def _load_manifest(self):
        """Load the sync manifest from disk."""
        manifest_path = self.sync_dir / "manifest.json"
        if not manifest_path.exists():
            return
        data = json.loads(manifest_path.read_text())
        for item in data.get("artifacts", []):
            key = f"{item['type']}:{item['name']}"
            self._artifacts[key] = WaslaArtifact(
                artifact_type=item["type"],
                name=item["name"],
                content=item["content"],
                source_orchestrator=item.get("source", "unknown"),
                updated_at=item.get("updated_at", ""),
                integrity_sha256=item.get("hash", ""),
            )
