"""
Graph Memory Layer - Entity-relation knowledge graph with multi-hop retrieval.

Implements hybrid LightRAG + HippoRAG approach:
- LightRAG: Incremental graph updates
- HippoRAG: Personalized PageRank for multi-hop retrieval
- Graphiti: Temporal validity windows
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from pathlib import Path
import json
import math


@dataclass
class GraphEntity:
    """An entity node in the knowledge graph."""

    entity_id: str
    name: str
    entity_type: str  # "person", "concept", "event", etc.
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GraphRelation:
    """A relation edge in the knowledge graph."""

    relation_id: str
    source_id: str
    target_id: str
    relation_type: str  # "causes", "related_to", "part_of", etc.
    confidence: float = 1.0  # 0.0 to 1.0
    valid_from: Optional[str] = None  # Temporal validity
    valid_until: Optional[str] = None
    supersedes: List[str] = field(default_factory=list)  # Superseded relation IDs
    superseded_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class GraphMemoryStore:
    """
    Knowledge graph with multi-hop retrieval.

    Features:
    - Incremental updates (LightRAG-style)
    - Personalized PageRank for multi-hop (HippoRAG-style)
    - Temporal validity windows (Graphiti-style)
    - Confidence scores on edges
    """

    def __init__(self, data_dir: str = "./data/graph_memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.entities: Dict[str, GraphEntity] = {}
        self.relations: Dict[str, GraphRelation] = {}

        # Adjacency lists for fast traversal
        self.outgoing: Dict[str, List[str]] = {}  # entity_id -> [relation_ids]
        self.incoming: Dict[str, List[str]] = {}  # entity_id -> [relation_ids]

        # PageRank scores (computed on demand)
        self.pagerank_scores: Dict[str, float] = {}
        self.pagerank_dirty = True

        self._load_graph()

    def _load_graph(self):
        """Load graph from disk."""
        entities_file = self.data_dir / "entities.json"
        relations_file = self.data_dir / "relations.json"

        if entities_file.exists():
            with open(entities_file, "r") as f:
                data = json.load(f)
                self.entities = {
                    eid: GraphEntity(**edata)
                    for eid, edata in data.items()
                }

        if relations_file.exists():
            with open(relations_file, "r") as f:
                data = json.load(f)
                self.relations = {
                    rid: GraphRelation(**rdata)
                    for rid, rdata in data.items()
                }

        # Rebuild adjacency lists
        self._rebuild_adjacency()

    def _save_graph(self):
        """Save graph to disk."""
        entities_data = {
            eid: {
                "entity_id": e.entity_id,
                "name": e.name,
                "entity_type": e.entity_type,
                "embedding": e.embedding,
                "metadata": e.metadata,
                "created_at": e.created_at,
            }
            for eid, e in self.entities.items()
        }

        relations_data = {
            rid: {
                "relation_id": r.relation_id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "relation_type": r.relation_type,
                "confidence": r.confidence,
                "valid_from": r.valid_from,
                "valid_until": r.valid_until,
                "supersedes": r.supersedes,
                "superseded_by": r.superseded_by,
                "metadata": r.metadata,
                "created_at": r.created_at,
            }
            for rid, r in self.relations.items()
        }

        with open(self.data_dir / "entities.json", "w") as f:
            json.dump(entities_data, f, indent=2)

        with open(self.data_dir / "relations.json", "w") as f:
            json.dump(relations_data, f, indent=2)

    def _rebuild_adjacency(self):
        """Rebuild adjacency lists from relations."""
        self.outgoing.clear()
        self.incoming.clear()

        for rid, rel in self.relations.items():
            # Outgoing edges
            if rel.source_id not in self.outgoing:
                self.outgoing[rel.source_id] = []
            self.outgoing[rel.source_id].append(rid)

            # Incoming edges
            if rel.target_id not in self.incoming:
                self.incoming[rel.target_id] = []
            self.incoming[rel.target_id].append(rid)

    def add_entity(self, entity: GraphEntity) -> str:
        """Add entity to graph (incremental update)."""
        self.entities[entity.entity_id] = entity
        self.pagerank_dirty = True
        self._save_graph()
        return entity.entity_id

    def add_relation(self, relation: GraphRelation) -> str:
        """Add relation to graph (incremental update)."""
        # Verify entities exist
        if relation.source_id not in self.entities:
            raise ValueError(f"Source entity {relation.source_id} not found")
        if relation.target_id not in self.entities:
            raise ValueError(f"Target entity {relation.target_id} not found")

        self.relations[relation.relation_id] = relation

        # Update adjacency lists
        if relation.source_id not in self.outgoing:
            self.outgoing[relation.source_id] = []
        self.outgoing[relation.source_id].append(relation.relation_id)

        if relation.target_id not in self.incoming:
            self.incoming[relation.target_id] = []
        self.incoming[relation.target_id].append(relation.relation_id)

        self.pagerank_dirty = True
        self._save_graph()
        return relation.relation_id

    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_relation(self, relation_id: str) -> Optional[GraphRelation]:
        """Get relation by ID."""
        return self.relations.get(relation_id)

    def find_entities(
        self,
        name_pattern: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[GraphEntity]:
        """Find entities by name pattern or type."""
        results = []

        for entity in self.entities.values():
            if name_pattern and name_pattern.lower() not in entity.name.lower():
                continue
            if entity_type and entity.entity_type != entity_type:
                continue
            results.append(entity)

        return results[:limit]

    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "outgoing",
        relation_type: Optional[str] = None
    ) -> List[Tuple[GraphEntity, GraphRelation]]:
        """
        Get neighboring entities.

        Args:
            entity_id: Source entity
            direction: "outgoing", "incoming", or "both"
            relation_type: Filter by relation type

        Returns:
            List of (neighbor_entity, relation) tuples
        """
        neighbors = []

        relation_ids = []
        if direction in ("outgoing", "both"):
            relation_ids.extend(self.outgoing.get(entity_id, []))
        if direction in ("incoming", "both"):
            relation_ids.extend(self.incoming.get(entity_id, []))

        for rid in relation_ids:
            rel = self.relations.get(rid)
            if not rel:
                continue

            if relation_type and rel.relation_type != relation_type:
                continue

            # Get neighbor entity
            if rel.source_id == entity_id:
                neighbor_id = rel.target_id
            else:
                neighbor_id = rel.source_id

            neighbor = self.entities.get(neighbor_id)
            if neighbor:
                neighbors.append((neighbor, rel))

        return neighbors

    def multi_hop_search(
        self,
        start_entity_id: str,
        max_hops: int = 3,
        min_confidence: float = 0.5
    ) -> List[Tuple[GraphEntity, float, List[str]]]:
        """
        Multi-hop search using Personalized PageRank.

        Returns:
            List of (entity, score, path) tuples
        """
        if start_entity_id not in self.entities:
            return []

        # Compute PPR scores
        ppr_scores = self._personalized_pagerank(
            start_entity_id,
            max_hops=max_hops,
            min_confidence=min_confidence
        )

        # Convert to results
        results = []
        for entity_id, score in ppr_scores.items():
            if entity_id == start_entity_id:
                continue
            entity = self.entities.get(entity_id)
            if entity:
                # TODO: Track actual path
                path = [start_entity_id, entity_id]
                results.append((entity, score, path))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def _personalized_pagerank(
        self,
        start_entity_id: str,
        max_hops: int = 3,
        min_confidence: float = 0.5,
        damping: float = 0.85,
        iterations: int = 20
    ) -> Dict[str, float]:
        """
        Compute Personalized PageRank scores.

        Args:
            start_entity_id: Starting entity
            max_hops: Maximum hops from start
            min_confidence: Minimum edge confidence
            damping: Damping factor (0.85 standard)
            iterations: Number of iterations

        Returns:
            Dict of entity_id -> score
        """
        # Initialize scores
        scores = {eid: 0.0 for eid in self.entities.keys()}
        scores[start_entity_id] = 1.0

        # Iterative computation
        for _ in range(iterations):
            new_scores = {eid: 0.0 for eid in self.entities.keys()}

            for entity_id in self.entities.keys():
                # Teleport probability
                new_scores[entity_id] += (1 - damping) * (
                    1.0 if entity_id == start_entity_id else 0.0
                )

                # Propagate from neighbors
                for neighbor, rel in self.get_neighbors(entity_id, direction="incoming"):
                    if rel.confidence < min_confidence:
                        continue

                    # Weight by confidence
                    out_degree = len(self.outgoing.get(neighbor.entity_id, []))
                    if out_degree > 0:
                        contribution = scores[neighbor.entity_id] / out_degree
                        new_scores[entity_id] += damping * contribution * rel.confidence

            scores = new_scores

        return scores

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_entities": len(self.entities),
            "num_relations": len(self.relations),
            "avg_degree": (
                sum(len(rels) for rels in self.outgoing.values()) / len(self.entities)
                if self.entities else 0
            ),
            "entity_types": list(set(e.entity_type for e in self.entities.values())),
            "relation_types": list(set(r.relation_type for r in self.relations.values())),
        }
