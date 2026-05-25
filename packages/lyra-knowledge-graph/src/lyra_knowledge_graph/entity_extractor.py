"""Entity extraction from text using keyword/pattern matching (no spaCy dependency).

Extracts typed entities with confidence scoring and batch processing
for research documents and codebases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityKind(Enum):
    """Entity types recognized by the extractor."""
    PERSON = "person"
    ORG = "org"
    TECH = "tech"
    CONCEPT = "concept"
    CODE = "code"
    DATA = "data"


# Default pattern libraries for each entity kind
DEFAULT_PATTERNS: dict[EntityKind, list[str]] = {
    EntityKind.PERSON: [
        r"\b[A-Z][a-z]+ (?:(?:van|von|de|le|du|d[aeiou]) )?[A-Z][a-z]+\b",
    ],
    EntityKind.ORG: [
        r"\b[A-Z][a-z]*(?:inc|corp|llc|ltd|gmbh|sa|plc|co)\b",
        r"\b[A-Z]{2,}\b(?!\s+[a-z])",
    ],
    EntityKind.TECH: [
        r"\b(?:python|react|kubernetes|docker|tensorflow|pytorch|llm|gpt|bert)\b",
        r"\b[A-Z][a-z]+(?:QL|ML|JS|TS|UI|API|SDK|DB)\b",
        r"\b\w+(?:framework|engine|platform|server|client)\b",
    ],
    EntityKind.CONCEPT: [
        r"\b(?:immutability|concurrency|encapsulation|polymorphism|abstraction)\b",
        r"\b(?:recursion|iteration|optimization|parallelism|synchronization)\b",
        r"\b[A-Z][a-z]+(?:Theory|Principle|Paradigm|Pattern|Approach)\b",
    ],
    EntityKind.CODE: [
        r"\b\w+\(\)\b",
        r"\b[A-Z][a-zA-Z]+(?:Factory|Builder|Manager|Service|Controller|Repository|Handler|Provider|Registry|Adapter)\b",
    ],
    EntityKind.DATA: [
        r"\b\w+\.(?:csv|json|xml|yaml|yml|parquet|avro|tsv)\b",
        r"\b(?:dataset|dataframe|table|schema|index|corpus)\b",
    ],
}

# Common words to filter out (false positive reduction)
STOP_WORDS: set[str] = {
    "the", "this", "that", "these", "those", "which", "what", "when",
    "where", "there", "their", "they", "them", "have", "has", "had",
    "with", "from", "about", "into", "over", "after", "before",
}


@dataclass(frozen=True)
class ExtractedEntity:
    """A single entity extracted from text."""
    name: str
    kind: EntityKind
    confidence: float
    occurrence_count: int = 1
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "confidence": self.confidence,
            "occurrence_count": self.occurrence_count,
            "context": self.context,
            "metadata": dict(self.metadata),
        }


class EntityExtractor:
    """Extract typed entities from text using regex pattern matching.

    Maintains a configurable pattern library per entity kind and
    produces confidence-scored extractions.
    """

    def __init__(self, patterns: dict[EntityKind, list[str]] | None = None) -> None:
        self._patterns: dict[EntityKind, list[re.Pattern[str]]] = {}
        for kind, pat_list in (patterns or DEFAULT_PATTERNS).items():
            self._patterns[kind] = [re.compile(p, re.IGNORECASE) for p in pat_list]

    # ── Configuration ───────────────────────────────────────────────────────

    def add_pattern(self, kind: EntityKind, pattern: str) -> EntityExtractor:
        """Add a custom pattern for an entity kind. Returns self for chaining."""
        new_patterns = {k: list(v) for k, v in self._patterns.items()}
        new_patterns.setdefault(kind, [])
        new_patterns[kind] = list(new_patterns[kind]) + [re.compile(pattern, re.IGNORECASE)]
        result = EntityExtractor.__new__(EntityExtractor)
        result._patterns = new_patterns
        return result

    def remove_pattern(self, kind: EntityKind, index: int) -> EntityExtractor:
        """Remove a pattern by index. Returns updated extractor."""
        if kind not in self._patterns or index >= len(self._patterns[kind]):
            return self
        new_patterns = {k: list(v) for k, v in self._patterns.items()}
        new_patterns[kind] = [p for i, p in enumerate(new_patterns[kind]) if i != index]
        result = EntityExtractor.__new__(EntityExtractor)
        result._patterns = new_patterns
        return result

    # ── Extraction ──────────────────────────────────────────────────────────

    def extract(self, text: str, context_window: int = 40) -> list[ExtractedEntity]:
        """Extract entities from a single text string."""
        found: dict[str, dict[str, Any]] = {}

        for kind, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    name = match.group(0).strip()
                    if name.lower() in STOP_WORDS or len(name) < 2:
                        continue
                    # Confidence: longer matches and uppercase-heavy are more reliable
                    base_conf = self._compute_confidence(name, kind)
                    start = max(0, match.start() - context_window)
                    end = min(len(text), match.end() + context_window)
                    snippet = text[start:end].replace("\n", " ")

                    if name not in found:
                        found[name] = {
                            "name": name,
                            "kind": kind,
                            "confidence": base_conf,
                            "occurrence_count": 1,
                            "context": snippet,
                            "metadata": {"match_start": match.start()},
                        }
                    else:
                        found[name]["occurrence_count"] += 1
                        found[name]["confidence"] = max(
                            found[name]["confidence"], base_conf
                        )
                        if len(found[name]["context"]) < len(snippet):
                            found[name]["context"] = snippet

        return [
            ExtractedEntity(
                name=entry["name"],
                kind=entry["kind"],
                confidence=min(entry["confidence"], 1.0),
                occurrence_count=entry["occurrence_count"],
                context=entry["context"],
                metadata={"match_start": entry["metadata"]["match_start"]},
            )
            for entry in sorted(
                found.values(), key=lambda x: x["confidence"], reverse=True
            )
        ]

    def extract_batch(self, documents: list[str]) -> list[list[ExtractedEntity]]:
        """Extract entities from multiple documents."""
        return [self.extract(doc) for doc in documents]

    def extract_to_graph(self, text: str,
                         graph: Any,
                         node_label_prefix: str = "entity") -> Any:
        """Extract entities and add them as nodes to a KnowledgeGraph."""
        from .graph_builder import KnowledgeNode, NodeType

        entities = self.extract(text)
        result = graph
        for ent in entities:
            node = KnowledgeNode(
                node_id=f"{node_label_prefix}:{ent.name}",
                node_type=NodeType.ENTITY,
                label=ent.name,
                properties={
                    "kind": ent.kind.value,
                    "occurrence_count": ent.occurrence_count,
                    "context": ent.context,
                },
                confidence=ent.confidence,
            )
            result = result.add_node(node)
        return result

    # ── Internal ────────────────────────────────────────────────────────────

    def _compute_confidence(self, name: str, kind: EntityKind) -> float:
        """Compute extraction confidence based on name characteristics."""
        score = 0.5
        # Longer names suggest more specific entities
        if len(name) >= 10:
            score += 0.2
        elif len(name) >= 5:
            score += 0.1
        # Acronyms (uppercase) boost confidence
        if name.isupper() and len(name) <= 6:
            score += 0.2
        # Mixed case with uppercase start suggests proper noun
        if name[0].isupper() and any(c.islower() for c in name[1:]):
            score += 0.15
        # Contains numbers adds specificity
        if any(c.isdigit() for c in name):
            score += 0.1
        # CODE type has lower base confidence (function calls are noisy)
        if kind == EntityKind.CODE and "()" not in name:
            score -= 0.2
        if name.endswith("()"):
            score += 0.1
        return min(score, 1.0)

    @property
    def patterns(self) -> dict[EntityKind, list[str]]:
        """Return current patterns (as source strings)."""
        return {
            kind: [p.pattern for p in pats]
            for kind, pats in self._patterns.items()
        }
