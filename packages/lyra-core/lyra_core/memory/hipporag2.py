"""
HippoRAG 2: Personalized PageRank Fusion Retrieval

Implements PPR over entity knowledge graph + dense embedding fusion.
SOTA on factual + multi-hop + sense-making simultaneously.

Based on research: arXiv:2502.14802 (ICML 2025), docs/316
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np


@dataclass
class Entity:
    """Entity in the knowledge graph."""
    name: str
    entity_type: str  # person, organization, concept, etc.
    mentions: List[str]  # Memory entry IDs where this entity appears


@dataclass
class EntityRelation:
    """Relation between two entities."""
    source: str
    target: str
    relation_type: str
    weight: float


class EntityGraph:
    """
    Entity knowledge graph for HippoRAG 2.

    Nodes: Entities extracted from memory
    Edges: Co-occurrence relationships
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[EntityRelation] = []
        self.adjacency: Dict[str, Dict[str, float]] = defaultdict(dict)

    def add_entity(self, name: str, entity_type: str, mention_id: str) -> None:
        """
        Add or update an entity.

        Args:
            name: Entity name
            entity_type: Type of entity
            mention_id: Memory entry ID where entity appears
        """
        if name not in self.entities:
            self.entities[name] = Entity(
                name=name,
                entity_type=entity_type,
                mentions=[mention_id]
            )
        else:
            if mention_id not in self.entities[name].mentions:
                self.entities[name].mentions.append(mention_id)

    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: str = "co-occurs",
        weight: float = 1.0
    ) -> None:
        """
        Add a relation between entities.

        Args:
            source: Source entity name
            target: Target entity name
            relation_type: Type of relation
            weight: Relation weight
        """
        self.relations.append(EntityRelation(
            source=source,
            target=target,
            relation_type=relation_type,
            weight=weight
        ))

        # Update adjacency matrix
        self.adjacency[source][target] = weight
        self.adjacency[target][source] = weight  # Undirected graph

    def get_neighbors(self, entity: str) -> List[Tuple[str, float]]:
        """
        Get neighbors of an entity.

        Args:
            entity: Entity name

        Returns:
            List of (neighbor_name, edge_weight) tuples
        """
        if entity not in self.adjacency:
            return []

        return [(neighbor, weight) for neighbor, weight in self.adjacency[entity].items()]

    def get_entity_mentions(self, entity: str) -> List[str]:
        """
        Get memory entry IDs where entity is mentioned.

        Args:
            entity: Entity name

        Returns:
            List of memory entry IDs
        """
        if entity not in self.entities:
            return []

        return self.entities[entity].mentions

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'num_entities': len(self.entities),
            'num_relations': len(self.relations),
            'avg_degree': sum(len(neighbors) for neighbors in self.adjacency.values()) / len(self.adjacency) if self.adjacency else 0
        }


class PersonalizedPageRank:
    """
    Personalized PageRank algorithm for entity graph.

    Computes importance scores for entities based on random walk
    with restart, seeded by query entities.
    """

    def __init__(self, graph: EntityGraph, alpha: float = 0.15):
        """
        Initialize PPR.

        Args:
            graph: Entity knowledge graph
            alpha: Teleport probability (default: 0.15)
        """
        self.graph = graph
        self.alpha = alpha

    def compute_ppr(
        self,
        seed_entities: List[str],
        max_iter: int = 100,
        tol: float = 1e-6
    ) -> Dict[str, float]:
        """
        Compute Personalized PageRank scores.

        Args:
            seed_entities: Query entities to seed the walk
            max_iter: Maximum iterations
            tol: Convergence tolerance

        Returns:
            Dictionary mapping entity names to PPR scores
        """
        # Initialize scores
        entities = list(self.graph.entities.keys())
        n = len(entities)

        if n == 0:
            return {}

        entity_to_idx = {e: i for i, e in enumerate(entities)}

        # Initialize uniform distribution over seed entities
        seed_prob = np.zeros(n)
        for entity in seed_entities:
            if entity in entity_to_idx:
                seed_prob[entity_to_idx[entity]] = 1.0 / len(seed_entities)

        # Initialize scores
        scores = seed_prob.copy()

        # Build transition matrix
        transition = np.zeros((n, n))
        for i, entity in enumerate(entities):
            neighbors = self.graph.get_neighbors(entity)
            if neighbors:
                total_weight = sum(weight for _, weight in neighbors)
                for neighbor, weight in neighbors:
                    j = entity_to_idx[neighbor]
                    transition[j, i] = weight / total_weight

        # Power iteration
        for iteration in range(max_iter):
            old_scores = scores.copy()

            # PPR update: (1-α) * transition * scores + α * seed_prob
            scores = (1 - self.alpha) * transition.dot(scores) + self.alpha * seed_prob

            # Check convergence
            if np.linalg.norm(scores - old_scores, 1) < tol:
                break

        # Convert to dictionary
        ppr_scores = {entity: scores[entity_to_idx[entity]] for entity in entities}

        return ppr_scores


class HippoRAG2Retriever:
    """
    HippoRAG 2: PPR over entity graph + dense embedding fusion.

    Combines:
    1. Personalized PageRank over entity knowledge graph
    2. Dense embedding similarity
    3. Fusion scoring: α·PPR + (1-α)·embedding
    """

    def __init__(
        self,
        entity_graph: EntityGraph,
        embedder,
        alpha: float = 0.6,
        ppr_alpha: float = 0.15
    ):
        """
        Initialize HippoRAG 2 retriever.

        Args:
            entity_graph: Entity knowledge graph
            embedder: Dense embedding model (BGE-M3, Voyage-3.5, etc.)
            alpha: Fusion weight (α·PPR + (1-α)·embedding)
            ppr_alpha: PPR teleport probability
        """
        self.graph = entity_graph
        self.embedder = embedder
        self.alpha = alpha
        self.ppr = PersonalizedPageRank(entity_graph, alpha=ppr_alpha)

    def extract_entities(self, text: str) -> List[str]:
        """
        Extract entities from text.

        Simple implementation: use NER or keyword matching.
        For production, use spaCy, BERT-NER, or LLM extraction.

        Args:
            text: Input text

        Returns:
            List of entity names
        """
        # Simple keyword matching against known entities
        entities = []
        text_lower = text.lower()

        for entity_name in self.graph.entities.keys():
            if entity_name.lower() in text_lower:
                entities.append(entity_name)

        return entities

    def retrieve(
        self,
        query: str,
        memory_entries: List[Dict[str, Any]],
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using HippoRAG 2: PPR + embedding fusion.

        Args:
            query: Search query
            memory_entries: List of memory entries with 'id', 'content', 'embedding'
            k: Number of results

        Returns:
            List of memory entries with fusion scores
        """
        # Step 1: Extract query entities
        query_entities = self.extract_entities(query)

        if not query_entities:
            # Fallback to pure embedding similarity
            return self._embedding_only_retrieval(query, memory_entries, k)

        # Step 2: Compute PPR scores
        ppr_scores = self.ppr.compute_ppr(query_entities)

        # Step 3: Compute embedding similarity
        query_embedding = self.embedder.encode(query)

        # Step 4: Fusion scoring
        results = []
        for entry in memory_entries:
            # Get PPR score for this entry
            entry_entities = self.extract_entities(entry['content'])
            ppr_score = max(
                [ppr_scores.get(e, 0.0) for e in entry_entities],
                default=0.0
            )

            # Get embedding score
            entry_embedding = entry.get('embedding')
            if entry_embedding is None:
                entry_embedding = self.embedder.encode(entry['content'])

            embedding_score = self._cosine_similarity(query_embedding, entry_embedding)

            # Fusion: α·PPR + (1-α)·embedding
            fusion_score = self.alpha * ppr_score + (1 - self.alpha) * embedding_score

            results.append({
                **entry,
                'ppr_score': ppr_score,
                'embedding_score': embedding_score,
                'fusion_score': fusion_score
            })

        # Sort by fusion score
        results.sort(key=lambda x: x['fusion_score'], reverse=True)

        return results[:k]

    def _embedding_only_retrieval(
        self,
        query: str,
        memory_entries: List[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """Fallback to pure embedding similarity."""
        query_embedding = self.embedder.encode(query)

        results = []
        for entry in memory_entries:
            entry_embedding = entry.get('embedding')
            if entry_embedding is None:
                entry_embedding = self.embedder.encode(entry['content'])

            score = self._cosine_similarity(query_embedding, entry_embedding)

            results.append({
                **entry,
                'ppr_score': 0.0,
                'embedding_score': score,
                'fusion_score': score
            })

        results.sort(key=lambda x: x['fusion_score'], reverse=True)
        return results[:k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# Entity graph builder
def build_entity_graph_from_memory(
    memory_entries: List[Dict[str, Any]],
    entity_extractor
) -> EntityGraph:
    """
    Build entity knowledge graph from memory entries.

    Args:
        memory_entries: List of memory entries with 'id' and 'content'
        entity_extractor: Function to extract entities from text

    Returns:
        EntityGraph instance
    """
    graph = EntityGraph()

    # Extract entities from each entry
    entry_entities: Dict[str, List[str]] = {}

    for entry in memory_entries:
        entities = entity_extractor(entry['content'])
        entry_entities[entry['id']] = entities

        # Add entities to graph
        for entity in entities:
            graph.add_entity(
                name=entity,
                entity_type="unknown",  # TODO: Add entity typing
                mention_id=entry['id']
            )

    # Build co-occurrence edges
    for entry_id, entities in entry_entities.items():
        # Add edges between entities that co-occur in same entry
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1:]:
                graph.add_relation(entity1, entity2, "co-occurs", weight=1.0)

    return graph
