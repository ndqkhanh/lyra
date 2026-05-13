"""Pinned decision store — decisions that survive compaction.

Extracts decisions, rationale, and project conventions from assistant
turns and stores them in a persistent "core memory tier" that is
injected back into the stable prefix after compaction.

Research grounding: §3.5 (CoALA working/episodic/semantic/procedural
memory taxonomy), §9 (frequency+recency+importance hybrid forgetting),
§10 "decision/rationale preservation across compactions — every community
report agrees this is where summarisation fails hardest."
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Decision markers — patterns that signal a decision was made
# ---------------------------------------------------------------------------

_DECISION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwe(?:'ll| will| should| decided to| are going to)\b", re.I),
    re.compile(r"\bgoing with\b", re.I),
    re.compile(r"\bthe (?:convention|pattern|approach|rule|standard) is\b", re.I),
    re.compile(r"\b(?:always|never|do not|don't|must not|should not)\b", re.I),
    re.compile(r"\bchose? (?:to |not to )?\b", re.I),
    re.compile(r"\bdecided?\b", re.I),
    re.compile(r"\bavoiding?\b", re.I),
    re.compile(r"\buse (?:instead|rather)\b", re.I),
    re.compile(r"\bthis means\b", re.I),
]

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class PinnedDecision:
    """A single pinned decision extracted from the conversation."""

    id: str
    text: str
    source_turn: int
    confidence: float  # 0.0–1.0 based on number of markers matched
    tags: list[str]
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PinnedDecision":
        return cls(**d)


class DecisionExtractor:
    """Extract decisions from assistant turn text using pattern matching.

    Scans each sentence for decision markers and returns
    :class:`PinnedDecision` instances for sentences that match.

    Usage::
        extractor = DecisionExtractor()
        decisions = extractor.extract(text="We decided to use SQLite.", turn=3)
    """

    def extract(
        self,
        text: str,
        *,
        turn: int = 0,
        tags: list[str] | None = None,
    ) -> list[PinnedDecision]:
        """Extract decisions from *text*. Returns one decision per matched sentence."""
        sentences = _SENTENCE_SPLIT_RE.split(text.strip())
        results: list[PinnedDecision] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            matches = sum(1 for p in _DECISION_PATTERNS if p.search(sentence))
            if matches == 0:
                continue
            confidence = min(1.0, matches / 3)
            results.append(
                PinnedDecision(
                    id=str(uuid.uuid4()),
                    text=sentence,
                    source_turn=turn,
                    confidence=confidence,
                    tags=list(tags or []),
                )
            )
        return results

    def extract_from_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        min_confidence: float = 0.0,
    ) -> list[PinnedDecision]:
        """Extract decisions from all assistant messages in a list."""
        results: list[PinnedDecision] = []
        for i, msg in enumerate(messages):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict)
                )
            else:
                text = str(content)
            for dec in self.extract(text, turn=i):
                if dec.confidence >= min_confidence:
                    results.append(dec)
        return results


class PinnedDecisionStore:
    """Persist pinned decisions across sessions and compactions.

    Usage::
        store = PinnedDecisionStore(store_path=Path("~/.lyra/decisions.json"))
        store.add(decision)
        recent = store.recall(top_k=5)
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._decisions: list[PinnedDecision] = []
        self._store_path = store_path
        if store_path and store_path.exists():
            self._load(store_path)

    def add(self, decision: PinnedDecision) -> None:
        self._decisions.append(decision)
        if self._store_path:
            self._save(self._store_path)

    def add_all(self, decisions: list[PinnedDecision]) -> None:
        self._decisions.extend(decisions)
        if self._store_path:
            self._save(self._store_path)

    def remove(self, decision_id: str) -> bool:
        before = len(self._decisions)
        self._decisions = [d for d in self._decisions if d.id != decision_id]
        changed = len(self._decisions) < before
        if changed and self._store_path:
            self._save(self._store_path)
        return changed

    def recall(
        self,
        *,
        top_k: int = 10,
        min_confidence: float = 0.0,
        tags: list[str] | None = None,
    ) -> list[PinnedDecision]:
        """Return up to *top_k* decisions, newest first.

        Filters by *min_confidence* and optionally by *tags* (any-match).
        """
        filtered = [
            d for d in self._decisions
            if d.confidence >= min_confidence
            and (tags is None or any(t in d.tags for t in tags))
        ]
        return sorted(filtered, key=lambda d: d.created_at, reverse=True)[:top_k]

    def as_context_block(self, *, top_k: int = 10) -> str:
        """Format top decisions as a compact system-message block."""
        decisions = self.recall(top_k=top_k)
        if not decisions:
            return ""
        lines = ["## Pinned Decisions (survive compaction)\n"]
        for d in decisions:
            lines.append(f"- {d.text}  [turn {d.source_turn}]")
        return "\n".join(lines)

    def all(self) -> list[PinnedDecision]:
        return list(self._decisions)

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([d.to_dict() for d in self._decisions], indent=2))

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text())
            self._decisions = [PinnedDecision.from_dict(d) for d in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._decisions = []


__all__ = [
    "PinnedDecision",
    "DecisionExtractor",
    "PinnedDecisionStore",
]
