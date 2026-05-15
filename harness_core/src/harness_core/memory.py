"""File-backed memory store with provenance.

A tiny, testable memory layer. Each entry is a text file under a scoped directory;
the index is a single MEMORY.md file so it is human-readable and version-controllable.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    id: str
    kind: str  # "fact" | "decision" | "preference" | "reference"
    content: str
    actor: str = "system"
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "actor": self.actor,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(**d)


class Memory:
    """File-backed memory: one JSONL file under ``root`` per scope."""

    def __init__(self, root: Path, scope: str = "default") -> None:
        self.root = Path(root)
        self.scope = scope
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / f"{scope}.jsonl"
        if not self._path.exists():
            self._path.touch()

    def add(
        self,
        content: str,
        kind: str = "fact",
        actor: str = "system",
        confidence: float = 1.0,
        expires_at: Optional[float] = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=uuid.uuid4().hex,
            kind=kind,
            content=content,
            actor=actor,
            confidence=confidence,
            expires_at=expires_at,
        )
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
        return entry

    def all(self) -> list[MemoryEntry]:
        entries: list[MemoryEntry] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(MemoryEntry.from_dict(json.loads(line)))
        now = time.time()
        return [e for e in entries if e.expires_at is None or e.expires_at > now]

    def search(self, keywords: str, limit: int = 10) -> list[MemoryEntry]:
        """Keyword search using simple whitespace-tokenized substring match."""
        tokens = [t for t in re.split(r"\s+", keywords.lower()) if t]
        scored: list[tuple[int, MemoryEntry]] = []
        for entry in self.all():
            text = entry.content.lower()
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: (-x[0], -x[1].created_at))
        return [e for _, e in scored[:limit]]

    def clear(self) -> None:
        self._path.write_text("", encoding="utf-8")
