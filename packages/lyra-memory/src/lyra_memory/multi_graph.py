"""
Multi-graph knowledge store (MAGMA-inspired).

Represents memories across four orthogonal graph dimensions:
1. Semantic graph - concept relationships (IS-A, PART-OF, RELATED-TO)
2. Temporal graph - time-ordered events (BEFORE, AFTER, DURING)
3. Causal graph - cause-effect chains (CAUSES, ENABLES, PREVENTS)
4. Entity graph - who/what/where connections (USES, WORKS-WITH, LOCATED-AT)

Based on MAGMA (Multi-Graph Memory Architecture) research from Jan 2026.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class GraphType(str, Enum):
    """Types of relationship graphs."""
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    ENTITY = "entity"


class SemanticRelation(str, Enum):
    """Semantic relationship types."""
    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    INSTANCE_OF = "instance_of"
    PROPERTY_OF = "property_of"


class TemporalRelation(str, Enum):
    """Temporal relationship types."""
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    CONCURRENT = "concurrent"


class CausalRelation(str, Enum):
    """Causal relationship types."""
    CAUSES = "causes"
    ENABLES = "enables"
    PREVENTS = "prevents"
    REQUIRES = "requires"


class EntityRelation(str, Enum):
    """Entity relationship types."""
    USES = "uses"
    WORKS_WITH = "works_with"
    LOCATED_AT = "located_at"
    OWNS = "owns"
    MEMBER_OF = "member_of"


@dataclass
class GraphEdge:
    """
    An edge in a knowledge graph.
    
    Attributes:
        source_id: Source memory ID
        target_id: Target memory ID
        relation: Type of relationship
        weight: Edge weight (0.0-1.0)
        metadata: Additional edge data
    """
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MultiGraphStore:
    """
    Multi-graph knowledge store for memory relationships.
    
    Maintains four separate graphs for different relationship types.
    Supports graph traversal and query-adaptive retrieval.
    """
    
    def __init__(self):
        """Initialize empty graphs."""
        # Adjacency lists for each graph type
        self._semantic_graph: Dict[str, List[GraphEdge]] = {}
        self._temporal_graph: Dict[str, List[GraphEdge]] = {}
        self._causal_graph: Dict[str, List[GraphEdge]] = {}
        self._entity_graph: Dict[str, List[GraphEdge]] = {}
        
        # Reverse indices for bidirectional traversal
        self._semantic_reverse: Dict[str, List[GraphEdge]] = {}
        self._temporal_reverse: Dict[str, List[GraphEdge]] = {}
        self._causal_reverse: Dict[str, List[GraphEdge]] = {}
        self._entity_reverse: Dict[str, List[GraphEdge]] = {}
    
    def add_edge(
        self,
        graph_type: GraphType,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> GraphEdge:
        """
        Add an edge to a graph.
        
        Args:
            graph_type: Which graph to add to
            source_id: Source memory ID
            target_id: Target memory ID
            relation: Relationship type
            weight: Edge weight
            metadata: Additional data
            
        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            metadata=metadata or {},
        )
        
        # Get appropriate graph
        graph, reverse = self._get_graph_pair(graph_type)
        
        # Add to forward graph
        if source_id not in graph:
            graph[source_id] = []
        graph[source_id].append(edge)
        
        # Add to reverse graph
        if target_id not in reverse:
            reverse[target_id] = []
        reverse[target_id].append(edge)
        
        return edge
    
    def get_neighbors(
        self,
        memory_id: str,
        graph_type: GraphType,
        direction: str = "outbound",
        relation_filter: Optional[str] = None,
    ) -> List[GraphEdge]:
        """
        Get neighboring edges for a memory.
        
        Args:
            memory_id: Memory to get neighbors for
            graph_type: Which graph to query
            direction: "outbound", "inbound", or "both"
            relation_filter: Optional relation type filter
            
        Returns:
            List of edges
        """
        graph, reverse = self._get_graph_pair(graph_type)
        
        edges = []
        
        # Outbound edges
        if direction in ("outbound", "both"):
            edges.extend(graph.get(memory_id, []))
        
        # Inbound edges
        if direction in ("inbound", "both"):
            edges.extend(reverse.get(memory_id, []))
        
        # Filter by relation if specified
        if relation_filter:
            edges = [e for e in edges if e.relation == relation_filter]
        
        return edges
    
    def traverse(
        self,
        start_id: str,
        graph_type: GraphType,
        max_depth: int = 2,
        relation_filter: Optional[str] = None,
    ) -> List[str]:
        """
        Traverse graph from a starting memory.
        
        Args:
            start_id: Starting memory ID
            graph_type: Which graph to traverse
            max_depth: Maximum traversal depth
            relation_filter: Optional relation type filter
            
        Returns:
            List of reachable memory IDs
        """
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(start_id, 0)]
        reachable = []
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            if current_id != start_id:
                reachable.append(current_id)
            
            # Get neighbors
            edges = self.get_neighbors(
                memory_id=current_id,
                graph_type=graph_type,
                direction="outbound",
                relation_filter=relation_filter,
            )
            
            # Add to queue
            for edge in edges:
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))
        
        return reachable
    
    def find_path(
        self,
        start_id: str,
        end_id: str,
        graph_type: GraphType,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """
        Find shortest path between two memories.
        
        Args:
            start_id: Starting memory ID
            end_id: Target memory ID
            graph_type: Which graph to search
            max_depth: Maximum path length
            
        Returns:
            List of memory IDs forming path, or None if no path
        """
        if start_id == end_id:
            return [start_id]
        
        visited: Set[str] = set()
        queue: List[Tuple[str, List[str]]] = [(start_id, [start_id])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # Get neighbors
            edges = self.get_neighbors(
                memory_id=current_id,
                graph_type=graph_type,
                direction="outbound",
            )
            
            for edge in edges:
                if edge.target_id == end_id:
                    return path + [end_id]
                
                if edge.target_id not in visited:
                    queue.append((edge.target_id, path + [edge.target_id]))
        
        return None
    
    def get_related_memories(
        self,
        memory_id: str,
        max_results: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Get related memories across all graphs.
        
        Combines results from all four graphs with weighted scoring.
        
        Args:
            memory_id: Memory to find relations for
            max_results: Maximum results to return
            
        Returns:
            List of (memory_id, relevance_score) tuples
        """
        # Collect neighbors from all graphs
        all_neighbors: Dict[str, float] = {}
        
        # Semantic graph (weight: 0.3)
        for edge in self.get_neighbors(memory_id, GraphType.SEMANTIC, "both"):
            target = edge.target_id if edge.source_id == memory_id else edge.source_id
            all_neighbors[target] = all_neighbors.get(target, 0.0) + 0.3 * edge.weight
        
        # Temporal graph (weight: 0.2)
        for edge in self.get_neighbors(memory_id, GraphType.TEMPORAL, "both"):
            target = edge.target_id if edge.source_id == memory_id else edge.source_id
            all_neighbors[target] = all_neighbors.get(target, 0.0) + 0.2 * edge.weight
        
        # Causal graph (weight: 0.3)
        for edge in self.get_neighbors(memory_id, GraphType.CAUSAL, "both"):
            target = edge.target_id if edge.source_id == memory_id else edge.source_id
            all_neighbors[target] = all_neighbors.get(target, 0.0) + 0.3 * edge.weight
        
        # Entity graph (weight: 0.2)
        for edge in self.get_neighbors(memory_id, GraphType.ENTITY, "both"):
            target = edge.target_id if edge.source_id == memory_id else edge.source_id
            all_neighbors[target] = all_neighbors.get(target, 0.0) + 0.2 * edge.weight
        
        # Sort by score and return top results
        sorted_neighbors = sorted(
            all_neighbors.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return sorted_neighbors[:max_results]
    
    def _get_graph_pair(
        self,
        graph_type: GraphType,
    ) -> Tuple[Dict[str, List[GraphEdge]], Dict[str, List[GraphEdge]]]:
        """Get forward and reverse graph for a type."""
        if graph_type == GraphType.SEMANTIC:
            return self._semantic_graph, self._semantic_reverse
        elif graph_type == GraphType.TEMPORAL:
            return self._temporal_graph, self._temporal_reverse
        elif graph_type == GraphType.CAUSAL:
            return self._causal_graph, self._causal_reverse
        elif graph_type == GraphType.ENTITY:
            return self._entity_graph, self._entity_reverse
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")
    
    def clear(self) -> None:
        """Clear all graphs."""
        self._semantic_graph.clear()
        self._temporal_graph.clear()
        self._causal_graph.clear()
        self._entity_graph.clear()
        self._semantic_reverse.clear()
        self._temporal_reverse.clear()
        self._causal_reverse.clear()
        self._entity_reverse.clear()


__all__ = [
    "GraphType",
    "SemanticRelation",
    "TemporalRelation",
    "CausalRelation",
    "EntityRelation",
    "GraphEdge",
    "MultiGraphStore",
]
