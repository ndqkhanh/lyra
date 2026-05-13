"""
Knowledge synthesis engine for research.

Builds citation networks, extracts concepts, and creates knowledge graphs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import re
from collections import defaultdict


@dataclass
class Concept:
    """A research concept."""
    name: str
    category: str  # method, dataset, metric, problem, etc.
    mentions: int = 0
    sources: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)


@dataclass
class Relationship:
    """A relationship between research sources or concepts."""
    source_id: str
    target_id: str
    relationship_type: str  # cites, uses, extends, contradicts, etc.
    strength: float = 1.0  # 0.0-1.0
    evidence: str = ""


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    type: str  # paper, repo, concept, author, etc.
    label: str
    properties: Dict = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    source: str
    target: str
    type: str
    weight: float = 1.0


class ConceptExtractor:
    """Extract concepts from research content."""

    def __init__(self):
        """Initialize concept extractor."""
        # Common research concepts
        self.method_patterns = [
            r'\b(?:transformer|CNN|RNN|LSTM|GAN|VAE|BERT|GPT)\b',
            r'\b(?:attention|convolution|pooling|dropout|batch normalization)\b',
        ]

        self.dataset_patterns = [
            r'\b(?:ImageNet|COCO|MNIST|CIFAR|SQuAD|GLUE|SuperGLUE)\b',
        ]

        self.metric_patterns = [
            r'\b(?:accuracy|precision|recall|F1|BLEU|ROUGE|perplexity)\b',
        ]

    def extract(self, content: str, source_id: str) -> List[Concept]:
        """
        Extract concepts from content.

        Args:
            content: Text content
            source_id: Source identifier

        Returns:
            List of extracted concepts
        """
        concepts = []

        # Extract methods
        for pattern in self.method_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in set(matches):
                concepts.append(Concept(
                    name=match.lower(),
                    category='method',
                    mentions=matches.count(match),
                    sources=[source_id],
                ))

        # Extract datasets
        for pattern in self.dataset_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in set(matches):
                concepts.append(Concept(
                    name=match,
                    category='dataset',
                    mentions=matches.count(match),
                    sources=[source_id],
                ))

        # Extract metrics
        for pattern in self.metric_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in set(matches):
                concepts.append(Concept(
                    name=match.lower(),
                    category='metric',
                    mentions=matches.count(match),
                    sources=[source_id],
                ))

        return concepts


class CitationNetworkBuilder:
    """Build citation networks from papers."""

    def __init__(self):
        """Initialize citation network builder."""
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []

    def add_paper(self, paper_id: str, title: str, metadata: Dict) -> None:
        """
        Add a paper to the network.

        Args:
            paper_id: Paper identifier
            title: Paper title
            metadata: Paper metadata
        """
        self.nodes[paper_id] = KnowledgeNode(
            id=paper_id,
            type='paper',
            label=title,
            properties={
                'citations': metadata.get('citations', 0),
                'year': metadata.get('year'),
                'authors': metadata.get('authors', []),
            },
        )

    def add_citation(self, citing_paper: str, cited_paper: str) -> None:
        """
        Add a citation relationship.

        Args:
            citing_paper: Paper that cites
            cited_paper: Paper being cited
        """
        self.edges.append(KnowledgeEdge(
            source=citing_paper,
            target=cited_paper,
            type='cites',
            weight=1.0,
        ))

    def get_influential_papers(self, top_k: int = 10) -> List[Tuple[str, int]]:
        """
        Get most influential papers by citation count.

        Args:
            top_k: Number of papers to return

        Returns:
            List of (paper_id, citation_count) tuples
        """
        # Count incoming citations
        citation_counts = defaultdict(int)
        for edge in self.edges:
            if edge.type == 'cites':
                citation_counts[edge.target] += 1

        # Sort by count
        sorted_papers = sorted(
            citation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_papers[:top_k]

    def get_citation_chain(self, paper_id: str, max_depth: int = 3) -> List[str]:
        """
        Get citation chain (papers that cite this paper).

        Args:
            paper_id: Starting paper
            max_depth: Maximum chain depth

        Returns:
            List of paper IDs in citation chain
        """
        chain = []
        visited = {paper_id}
        current_level = [paper_id]

        for _ in range(max_depth):
            next_level = []
            for current_paper in current_level:
                # Find papers that cite current paper
                for edge in self.edges:
                    if edge.type == 'cites' and edge.target == current_paper:
                        if edge.source not in visited:
                            visited.add(edge.source)
                            next_level.append(edge.source)
                            chain.append(edge.source)

            if not next_level:
                break
            current_level = next_level

        return chain


class RelationshipDiscovery:
    """Discover relationships between research sources."""

    def discover_paper_relationships(
        self,
        papers: List[Dict],
        concepts: Dict[str, List[Concept]],
    ) -> List[Relationship]:
        """
        Discover relationships between papers.

        Args:
            papers: List of paper metadata
            concepts: Concepts extracted from each paper

        Returns:
            List of discovered relationships
        """
        relationships = []

        # Find papers with shared concepts
        for i, paper1 in enumerate(papers):
            for paper2 in papers[i+1:]:
                paper1_id = paper1['id']
                paper2_id = paper2['id']

                # Get concepts for each paper
                concepts1 = {c.name for c in concepts.get(paper1_id, [])}
                concepts2 = {c.name for c in concepts.get(paper2_id, [])}

                # Calculate overlap
                shared = concepts1 & concepts2
                if shared:
                    strength = len(shared) / max(len(concepts1), len(concepts2))

                    relationships.append(Relationship(
                        source_id=paper1_id,
                        target_id=paper2_id,
                        relationship_type='shares_concepts',
                        strength=strength,
                        evidence=f"Shared concepts: {', '.join(list(shared)[:5])}",
                    ))

        return relationships

    def detect_contradictions(
        self,
        papers: List[Dict],
        analyses: Dict[str, any],
    ) -> List[Relationship]:
        """
        Detect contradictions between papers.

        Args:
            papers: List of paper metadata
            analyses: Paper analyses

        Returns:
            List of contradiction relationships
        """
        contradictions = []

        # Look for contradictory claims
        contradiction_patterns = [
            (r'outperforms?', r'underperforms?'),
            (r'improves?', r'degrades?'),
            (r'increases?', r'decreases?'),
        ]

        for i, paper1 in enumerate(papers):
            for paper2 in papers[i+1:]:
                paper1_id = paper1['id']
                paper2_id = paper2['id']

                # Get findings
                analysis1 = analyses.get(paper1_id)
                analysis2 = analyses.get(paper2_id)

                if not analysis1 or not analysis2:
                    continue

                findings1 = ' '.join(analysis1.key_findings)
                findings2 = ' '.join(analysis2.key_findings)

                # Check for contradictory patterns
                for pos_pattern, neg_pattern in contradiction_patterns:
                    if (re.search(pos_pattern, findings1, re.IGNORECASE) and
                        re.search(neg_pattern, findings2, re.IGNORECASE)):

                        contradictions.append(Relationship(
                            source_id=paper1_id,
                            target_id=paper2_id,
                            relationship_type='contradicts',
                            strength=0.5,
                            evidence="Contradictory performance claims",
                        ))
                        break

        return contradictions

    def identify_consensus(
        self,
        papers: List[Dict],
        concepts: Dict[str, List[Concept]],
    ) -> Dict[str, List[str]]:
        """
        Identify consensus on concepts.

        Args:
            papers: List of paper metadata
            concepts: Concepts from each paper

        Returns:
            Dictionary mapping concepts to supporting papers
        """
        concept_support = defaultdict(list)

        # Count papers supporting each concept
        for paper_id, paper_concepts in concepts.items():
            for concept in paper_concepts:
                concept_support[concept.name].append(paper_id)

        # Filter to concepts with multiple supporters
        consensus = {
            concept: papers
            for concept, papers in concept_support.items()
            if len(papers) >= 3
        }

        return consensus


class KnowledgeGraph:
    """
    Knowledge graph for research synthesis.

    Combines papers, repos, concepts, and relationships.
    """

    def __init__(self):
        """Initialize knowledge graph."""
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self.concepts: Dict[str, Concept] = {}

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def add_concept(self, concept: Concept) -> None:
        """Add or merge a concept."""
        if concept.name in self.concepts:
            # Merge with existing
            existing = self.concepts[concept.name]
            existing.mentions += concept.mentions
            existing.sources.extend(concept.sources)
            existing.sources = list(set(existing.sources))
        else:
            self.concepts[concept.name] = concept

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[str]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node identifier
            edge_type: Optional edge type filter

        Returns:
            List of neighbor node IDs
        """
        neighbors = []

        for edge in self.edges:
            if edge_type and edge.type != edge_type:
                continue

            if edge.source == node_id:
                neighbors.append(edge.target)
            elif edge.target == node_id:
                neighbors.append(edge.source)

        return list(set(neighbors))

    def get_subgraph(self, node_ids: List[str], max_hops: int = 2) -> 'KnowledgeGraph':
        """
        Extract a subgraph around given nodes.

        Args:
            node_ids: Starting nodes
            max_hops: Maximum hops from starting nodes

        Returns:
            Subgraph
        """
        subgraph = KnowledgeGraph()

        # BFS to find nodes within max_hops
        visited = set(node_ids)
        current_level = set(node_ids)

        for _ in range(max_hops):
            next_level = set()
            for node_id in current_level:
                neighbors = self.get_neighbors(node_id)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)

            current_level = next_level
            if not current_level:
                break

        # Add nodes
        for node_id in visited:
            if node_id in self.nodes:
                subgraph.add_node(self.nodes[node_id])

        # Add edges between included nodes
        for edge in self.edges:
            if edge.source in visited and edge.target in visited:
                subgraph.add_edge(edge)

        return subgraph

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            'num_nodes': len(self.nodes),
            'num_edges': len(self.edges),
            'num_concepts': len(self.concepts),
            'node_types': self._count_node_types(),
            'edge_types': self._count_edge_types(),
        }

    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in self.nodes.values():
            counts[node.type] += 1
        return dict(counts)

    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        counts = defaultdict(int)
        for edge in self.edges:
            counts[edge.type] += 1
        return dict(counts)
