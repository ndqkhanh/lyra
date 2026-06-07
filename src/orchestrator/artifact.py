"""
Artifact protocol for the Orchestrator module.

Defines the artifact data structure that workers produce and the orchestrator
consumes. Supports file-system-based JSON/markdown output and compression.
"""

import base64
import gzip
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class CompressionLevel(str, Enum):
    """Compression level for artifact content."""

    NONE = "none"
    LIGHT = "light"
    FULL = "full"


@dataclass
class Artifact:
    """
    Represents the output of a single worker sub-task.

    Attributes:
        task_id: Unique identifier for the sub-task that produced this artifact.
        content: The full output content (JSON or markdown string).
        summary: A concise summary (2-3 sentences) of the artifact.
        confidence: Confidence score (0.0 - 1.0) in the artifact's accuracy.
        sources: List of source references (URLs, file paths, citations).
        worker_id: Identifier of the worker that produced this artifact.
        created_at: Timestamp when the artifact was created.
        metadata: Arbitrary metadata key-value pairs.
    """

    task_id: str
    content: str
    summary: str = ""
    confidence: float = 1.0
    sources: list[str] = field(default_factory=list)
    worker_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate artifact after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to a dictionary."""
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artifact":
        """Deserialize artifact from a dictionary."""
        data = dict(data)
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """Serialize artifact to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_json(cls, payload: str) -> "Artifact":
        """Deserialize artifact from a JSON string."""
        return cls.from_dict(json.loads(payload))

    def to_markdown(self) -> str:
        """Render artifact as a markdown string."""
        lines: list[str] = [
            f"## Task: {self.task_id}",
            "",
            f"**Worker**: {self.worker_id}",
            f"**Confidence**: {self.confidence:.2f}",
            f"**Created**: {self.created_at.isoformat()}",
            "",
            "### Summary",
            "",
            self.summary,
            "",
            "### Content",
            "",
            self.content,
        ]
        if self.sources:
            lines.extend(["", "### Sources", ""])
            lines.extend(f"- {src}" for src in self.sources)
        return "\n".join(lines)

    def write_json(self, path: str | Path) -> Path:
        """Write artifact to a JSON file on disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
        return path

    def write_markdown(self, path: str | Path) -> Path:
        """Write artifact to a markdown file on disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown())
        return path


def compress_artifact(artifact: Artifact, level: CompressionLevel = CompressionLevel.FULL) -> str:
    """
    Compress an artifact into a compact string representation.

    At FULL compression, the artifact is serialized to JSON, gzip-compressed,
    and base64-encoded. At LIGHT, the summary is kept and content is
    truncated. At NONE, the raw JSON is returned.
    """
    if level == CompressionLevel.NONE:
        return artifact.to_json()

    if level == CompressionLevel.LIGHT:
        compressed = Artifact(
            task_id=artifact.task_id,
            content=artifact.content[:200] + ("..." if len(artifact.content) > 200 else ""),
            summary=artifact.summary,
            confidence=artifact.confidence,
            sources=artifact.sources,
            worker_id=artifact.worker_id,
            created_at=artifact.created_at,
            metadata={"compression": "light", **artifact.metadata},
        )
        return compressed.to_json()

    # FULL compression
    raw = artifact.to_json().encode("utf-8")
    compressed_bytes = gzip.compress(raw)
    return base64.b64encode(compressed_bytes).decode("ascii")


def decompress_artifact(payload: str) -> Artifact:
    """
    Decompress a string back into an Artifact.

    Attempts base64 + gzip decoding first. Falls back to plain JSON.
    """
    # Try base64 + gzip first
    try:
        raw = base64.b64decode(payload)
        decompressed = gzip.decompress(raw)
        return Artifact.from_json(decompressed.decode("utf-8"))
    except (ValueError, OSError, base64.binascii.Error):
        pass

    # Fallback to plain JSON
    try:
        return Artifact.from_json(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Cannot decompress artifact payload: {exc}") from exc
