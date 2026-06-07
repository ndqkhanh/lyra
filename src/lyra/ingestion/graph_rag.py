"""
Graph-based RAG — entity extraction from documents and graph-aware retrieval.

Provides the GraphRAGExtractor for extracting entities and relations from
document text, building an EntityGraph that can be used for graph-enhanced
retrieval in the HybridSearch pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from lyra.ingestion.pipeline import Document


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entity:
    """A named entity extracted from document text.

    Attributes:
        name: Canonical entity name.
        type: Entity type (e.g. "person", "organization", "concept", "technology").
        mentions: List of surface-form mentions found in text.
    """

    name: str
    type: str
    mentions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Relation:
    """A typed relation between two entities.

    Attributes:
        source: Name of the source entity.
        target: Name of the target entity.
        relation_type: Type of relation (e.g. "works_at", "depends_on").
        weight: Strength of the relation in [0, 1].
    """

    source: str
    target: str
    relation_type: str
    weight: float = 1.0


@dataclass
class EntityGraph:
    """A graph of entities and their relations extracted from a document.

    Attributes:
        entities: List of extracted entities.
        relations: List of extracted relationships.
        source_doc_id: Document ID this graph was extracted from.
    """

    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    source_doc_id: str = ""

    def get_entity(self, name: str) -> Entity | None:
        """Look up an entity by canonical name."""
        for e in self.entities:
            if e.name == name:
                return e
        return None

    def get_relations(self, entity_name: str) -> list[Relation]:
        """Get all relations involving a given entity."""
        return [
            r
            for r in self.relations
            if r.source == entity_name or r.target == entity_name
        ]

    def merge(self, other: EntityGraph) -> None:
        """Merge another EntityGraph into this one."""
        existing_names = {e.name for e in self.entities}
        for e in other.entities:
            if e.name not in existing_names:
                self.entities.append(e)
                existing_names.add(e.name)
        existing_pairs = {(r.source, r.target, r.relation_type) for r in self.relations}
        for r in other.relations:
            key = (r.source, r.target, r.relation_type)
            if key not in existing_pairs:
                self.relations.append(r)
                existing_pairs.add(key)

    def entity_count(self) -> int:
        """Number of unique entities."""
        return len(self.entities)

    def relation_count(self) -> int:
        """Number of unique relations."""
        return len(self.relations)


# ---------------------------------------------------------------------------
# Extraction protocols
# ---------------------------------------------------------------------------


class EntityExtractor(Protocol):
    """Protocol for extracting entities from text."""

    def extract(self, text: str) -> EntityGraph:
        """Extract entities and relations from text.

        Args:
            text: Document text.

        Returns:
            EntityGraph containing extracted entities and relations.
        """
        ...


# ---------------------------------------------------------------------------
# GraphRAGExtractor
# ---------------------------------------------------------------------------


class GraphRAGExtractor:
    """Extracts entities and relations from document text to build an EntityGraph.

    Uses a configurable extraction strategy (e.g. regex patterns, NLP pipeline,
    or LLM-based extraction). This implementation provides a rule-based
    extractor suitable for development and testing; swap in an LLM-based
    extractor for production use.
    """

    def __init__(self, extractor: EntityExtractor | None = None):
        """Initialize GraphRAGExtractor.

        Args:
            extractor: Optional custom EntityExtractor. Uses a built-in
                pattern-based extractor if None.
        """
        self._extractor = extractor or _RuleBasedExtractor()

    def extract(self, text: str) -> EntityGraph:
        """Extract an entity graph from raw text.

        Args:
            text: Document text.

        Returns:
            EntityGraph extracted from the text.
        """
        return self._extractor.extract(text)

    def extract_from_document(self, document: Document) -> EntityGraph:
        """Extract an entity graph from a Document object.

        Args:
            document: A Document instance.

        Returns:
            EntityGraph with source_doc_id set.
        """
        graph = self.extract(document.content)
        graph.source_doc_id = document.doc_id
        return graph

    def extract_batch(self, texts: list[str]) -> list[EntityGraph]:
        """Extract entity graphs from a batch of texts.

        Args:
            texts: List of document texts.

        Returns:
            List of EntityGraph instances, one per text.
        """
        return [self.extract(t) for t in texts]


# ---------------------------------------------------------------------------
# Built-in rule-based extractor
# ---------------------------------------------------------------------------


class _RuleBasedExtractor:
    """Simple rule-based entity extractor using regex heuristics.

    Detects:
      - Capitalised phrases (proper nouns) as entities
      - Co-occurrence within sentences as relations
    Suitable for prototyping and testing; not for production use.
    """

    # Common entity types hinted by surrounding words
    _TYPE_HINTS: dict[str, str] = {
        "ai": "technology",
        "model": "technology",
        "system": "technology",
        "tool": "technology",
        "framework": "technology",
        "library": "technology",
        "api": "technology",
        "dr": "person",
        "mr": "person",
        "mrs": "person",
        "ms": "person",
        "prof": "person",
        "ceo": "person",
        "cto": "person",
    }

    def extract(self, text: str) -> EntityGraph:
        """Extract entities using capitalised-phrase heuristics."""
        import re

        graph = EntityGraph()

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentence_entities: list[list[str]] = []

        seen: dict[str, str] = {}

        for sentence in sentences:
            # Find capitalised phrases (2+ words, or single capitalised word)
            entities_in_sentence: list[str] = []
            # Match capitalised words/phrases
            for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", sentence):
                name = match.group().strip()
                if len(name) < 2:
                    continue
                if name not in seen:
                    seen[name] = self._infer_type(name, sentence)
                entities_in_sentence.append(name)

            # Add entities (only once)
            for name in entities_in_sentence:
                if not graph.get_entity(name):
                    graph.entities.append(
                        Entity(name=name, type=seen[name], mentions=(name,))
                    )

            sentence_entities.append(entities_in_sentence)

        # Build relations from co-occurrence within sentences
        added_pairs: set[tuple[str, str]] = set()
        for entities in sentence_entities:
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    a, b = entities[i], entities[j]
                    pair = (a, b) if a < b else (b, a)
                    if pair not in added_pairs:
                        graph.relations.append(
                            Relation(
                                source=pair[0],
                                target=pair[1],
                                relation_type="co_occurs",
                                weight=0.5,
                            )
                        )
                        added_pairs.add(pair)

        return graph

    @staticmethod
    def _infer_type(name: str, context: str) -> str:
        """Infer entity type from context words."""
        lower_context = context.lower()
        for keyword, etype in _RuleBasedExtractor._TYPE_HINTS.items():
            if keyword in lower_context:
                return etype
        # Default: organisation if multi-word, concept if single
        return "organization" if " " in name else "concept"


__all__ = [
    "Entity",
    "Relation",
    "EntityGraph",
    "EntityExtractor",
    "GraphRAGExtractor",
]
