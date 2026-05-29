"""
Research Knowledge Graph.

MERMAID-style entity-anchored hybrid retrieval with typed entity relationships,
graph traversal, contradiction detection, and knowledge merging.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchEntity:
    """A named entity in the research knowledge graph.

    Attributes:
        id: Unique entity identifier.
        name: Human-readable entity name.
        entity_type: Category (person, organization, concept, event, technology).
        aliases: Alternative names for the entity.
        metadata: Arbitrary key-value properties.
    """

    id: str
    name: str
    entity_type: str  # person, organization, concept, event, technology
    aliases: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def matches_name(self, query: str) -> bool:
        """Check whether *query* matches this entity by name or alias."""
        lowered = query.lower().strip()
        if lowered == self.name.lower():
            return True
        return any(lowered == a.lower() for a in self.aliases)


@dataclass(frozen=True)
class EntityRelation:
    """A typed, optionally weighted relationship between two entities.

    Attributes:
        source_id: ID of the source entity.
        target_id: ID of the target entity.
        relation_type: Relationship type (e.g. "cites", "contradicts", "uses").
        weight: Edge weight (0.0-1.0).
        evidence: Textual evidence supporting the relationship.
        source_citation: Where the relationship was observed.
    """

    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    evidence: str = ""
    source_citation: str = ""


# ---------------------------------------------------------------------------
# ResearchKG
# ---------------------------------------------------------------------------


class ResearchKG:
    """MERMAID-style entity-anchored knowledge graph for research.

    Supports entity extraction, typed relationship linking, neighbourhood
    traversal, shortest-path search, contradiction detection, and merging
    with other knowledge graphs.
    """

    def __init__(self, name: str = "research_kg") -> None:
        """Initialize an empty knowledge graph.

        Args:
            name: Optional human-readable label for the graph.
        """
        self.name = name
        self._entities: dict[str, ResearchEntity] = {}
        self._relations: list[EntityRelation] = []
        # Adjacency index: entity_id -> list of relation indices
        self._adj: dict[str, list[int]] = defaultdict(list)

    # -- entity management ---------------------------------------------------

    def add_entity(self, entity: ResearchEntity) -> None:
        """Insert or overwrite an entity in the graph."""
        self._entities[entity.id] = entity
        logger.debug("KG[%s] added entity %s (%s)", self.name, entity.id, entity.entity_type)

    def get_entity(self, entity_id: str) -> ResearchEntity | None:
        """Return the entity with *entity_id* or ``None``."""
        return self._entities.get(entity_id)

    def list_entities(self) -> list[ResearchEntity]:
        """Return all entities stored in the graph."""
        return list(self._entities.values())

    def find_entity_by_name(self, name: str) -> ResearchEntity | None:
        """Look up an entity by its canonical name or an alias."""
        lowered = name.lower().strip()
        for entity in self._entities.values():
            if lowered == entity.name.lower():
                return entity
            if any(lowered == a.lower() for a in entity.aliases):
                return entity
        return None

    # -- relation management -------------------------------------------------

    def add_relation(
        self,
        entity_a_id: str,
        entity_b_id: str,
        relation_type: str,
        weight: float = 1.0,
        evidence: str = "",
        source_citation: str = "",
    ) -> EntityRelation | None:
        """Create a typed relation between two entities.

        Returns ``None`` if either entity does not exist in the graph.
        """
        if entity_a_id not in self._entities or entity_b_id not in self._entities:
            logger.warning(
                "KG[%s] cannot link %s -> %s: one or both entities missing",
                self.name,
                entity_a_id,
                entity_b_id,
            )
            return None

        relation = EntityRelation(
            source_id=entity_a_id,
            target_id=entity_b_id,
            relation_type=relation_type,
            weight=weight,
            evidence=evidence,
            source_citation=source_citation,
        )
        idx = len(self._relations)
        self._relations.append(relation)
        self._adj[entity_a_id].append(idx)
        self._adj[entity_b_id].append(idx)  # undirected for traversal
        logger.debug(
            "KG[%s] linked %s -[%s]-> %s", self.name, entity_a_id, relation_type, entity_b_id,
        )
        return relation

    def link_entities(
        self,
        entity_a: ResearchEntity,
        entity_b: ResearchEntity,
        relation_type: str,
        weight: float = 1.0,
        evidence: str = "",
    ) -> EntityRelation | None:
        """Convenience wrapper around ``add_relation`` that accepts entity objects."""
        return self.add_relation(
            entity_a.id,
            entity_b.id,
            relation_type,
            weight=weight,
            evidence=evidence,
        )

    def list_relations(self) -> list[EntityRelation]:
        """Return all relations in the graph."""
        return list(self._relations)

    def get_relations_for(self, entity_id: str) -> list[EntityRelation]:
        """Return every relation incident to *entity_id*."""
        indices = self._adj.get(entity_id, [])
        return [self._relations[i] for i in indices]

    # -- extraction ----------------------------------------------------------

    def extract_entities(self, text: str) -> list[ResearchEntity]:
        """Extract entities from research text using simple heuristics.

        This is a lightweight rule-based extractor that identifies capitalized
        n-grams and known patterns.  For production use, integrate with spaCy
        or a dedicated NER model.

        Args:
            text: Raw research text.

        Returns:
            Newly created entities (they are NOT automatically added to the
            graph — call ``add_entity`` separately).
        """
        import re

        entities: list[ResearchEntity] = []

        # Heuristic: capitalized multi-word phrases (2-4 words)
        pattern = r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){1,3})\b"
        seen: set[str] = set()
        for match in re.finditer(pattern, text):
            phrase = match.group(1).strip()
            lowered = phrase.lower()
            if lowered in seen:
                continue
            seen.add(lowered)

            # Classify entity type heuristically
            etype = _classify_entity(phrase)

            entity_id = f"ent_{len(self._entities) + len(entities):04d}"
            entities.append(
                ResearchEntity(
                    id=entity_id,
                    name=phrase,
                    entity_type=etype,
                )
            )

        logger.debug("KG[%s] extracted %d entities from text", self.name, len(entities))
        return entities

    # -- traversal -----------------------------------------------------------

    def traverse(self, entity_id: str, depth: int = 1) -> list[ResearchEntity]:
        """Return all entities within *depth* hops of *entity_id* (BFS).

        Args:
            entity_id: Starting entity.
            depth: Maximum number of hops (>= 0).

        Returns:
            Entities in the neighbourhood, excluding the starting entity.
        """
        if depth < 0:
            return []
        if entity_id not in self._entities:
            return []

        visited: set[str] = {entity_id}
        result: list[ResearchEntity] = []
        queue: deque = deque([(entity_id, 0)])

        while queue:
            current, dist = queue.popleft()
            if dist > 0:
                ent = self._entities[current]
                result.append(ent)

            if dist < depth:
                for rel_idx in self._adj.get(current, []):
                    rel = self._relations[rel_idx]
                    for nid in (rel.source_id, rel.target_id):
                        if nid not in visited:
                            visited.add(nid)
                            queue.append((nid, dist + 1))

        logger.debug(
            "KG[%s] traverse(%s, depth=%d) -> %d entities",
            self.name,
            entity_id,
            depth,
            len(result),
        )
        return result

    def find_path(
        self, source_id: str, target_id: str, max_depth: int = 6
    ) -> list[str] | None:
        """Return the shortest path (by edges) between *source* and *target*.

        Args:
            source_id: Starting entity ID.
            target_id: Destination entity ID.
            max_depth: Maximum search depth.

        Returns:
            List of entity IDs from source to target (inclusive), or ``None``.
        """
        if source_id not in self._entities or target_id not in self._entities:
            return None
        if source_id == target_id:
            return [source_id]

        queue: deque = deque([(source_id, [source_id])])
        visited: set[str] = {source_id}

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth + 1:
                continue

            for rel_idx in self._adj.get(current, []):
                rel = self._relations[rel_idx]
                for nid in (rel.source_id, rel.target_id):
                    if nid == target_id:
                        return path + [target_id]
                    if nid not in visited:
                        visited.add(nid)
                        queue.append((nid, path + [nid]))

        logger.debug(
            "KG[%s] no path found between %s and %s within depth %d",
            self.name,
            source_id,
            target_id,
            max_depth,
        )
        return None

    # -- contradiction detection ---------------------------------------------

    def detect_contradictions(self) -> list[tuple[str, str, str]]:
        """Find pairs of entities connected by "contradicts" relations.

        Returns:
            List of (entity_a_name, entity_b_name, evidence) tuples.
        """
        contradictions: list[tuple[str, str, str]] = []
        for rel in self._relations:
            if rel.relation_type == "contradicts":
                a = self._entities.get(rel.source_id)
                b = self._entities.get(rel.target_id)
                if a and b:
                    contradictions.append((a.name, b.name, rel.evidence))
        logger.debug(
            "KG[%s] detected %d contradictions", self.name, len(contradictions),
        )
        return contradictions

    # -- merging -------------------------------------------------------------

    def merge_knowledge(self, other: ResearchKG) -> int:
        """Merge entities and relations from *other* into this graph.

        Entities are matched by ID; relations are appended.

        Returns:
            Number of new entities added.
        """
        added = 0
        for entity in other._entities.values():
            if entity.id not in self._entities:
                self._entities[entity.id] = entity
                added += 1

        offset = len(self._relations)
        for i, rel in enumerate(other._relations):
            self._relations.append(rel)
            self._adj[rel.source_id].append(offset + i)
            self._adj[rel.target_id].append(offset + i)

        logger.info(
            "KG[%s] merged %s: +%d entities, +%d relations",
            self.name,
            other.name,
            added,
            len(other._relations),
        )
        return added

    # -- introspection -------------------------------------------------------

    def __len__(self) -> int:
        return len(self._entities)

    @property
    def entity_count(self) -> int:
        """Number of entities in the graph."""
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        """Number of relations in the graph."""
        return len(self._relations)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENTITY_CLASSIFICATION_PATTERNS: list[tuple[str, list[str]]] = [
    ("person", ["University", "Institute", "Lab", "Professor", "Dr.", "Research"]),
    ("organization", ["Inc", "Corp", "Corporation", "LLC", "Labs", "AI", "OpenAI", "Google", "Meta", "Microsoft"]),
    ("technology", ["Model", "Framework", "Algorithm", "Architecture", "Transformer", "Neural", "BERT", "GPT"]),
    ("concept", ["Learning", "Theory", "Optimization", "Regularization", "Attention", "Gradient"]),
    ("event", ["Conference", "Workshop", "Symposium", "Challenge", "Competition", "Benchmark"]),
]


def _classify_entity(name: str) -> str:
    """Guess the entity type from its name using keyword heuristics."""
    for etype, keywords in _ENTITY_CLASSIFICATION_PATTERNS:
        for kw in keywords:
            if kw.lower() in name.lower():
                return etype
    return "concept"
