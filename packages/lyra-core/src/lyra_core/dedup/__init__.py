"""
Semantic Deduplication System

Detects and merges semantically similar content to reduce redundancy.

Features:
- Embedding-based similarity detection
- Automatic content merging
- Configurable similarity thresholds
- Batch processing support
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
import hashlib
from collections import defaultdict


@dataclass
class ContentBlock:
    """A block of content with metadata"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)

    def get_hash(self) -> str:
        """Get content hash for exact duplicate detection"""
        return hashlib.sha256(self.content.encode()).hexdigest()


@dataclass
class DuplicateGroup:
    """Group of duplicate/similar content blocks"""
    representative: ContentBlock
    duplicates: List[ContentBlock] = field(default_factory=list)
    similarity_scores: List[float] = field(default_factory=list)

    def get_merged_content(self) -> str:
        """Get merged content from all blocks"""
        # Use representative as base
        return self.representative.content

    def get_total_size(self) -> int:
        """Get total size of all content"""
        return sum(len(b.content) for b in [self.representative] + self.duplicates)


class SemanticDeduplicator:
    """
    Semantic deduplication system

    Detects and merges semantically similar content using:
    - Exact hash matching for identical content
    - Embedding similarity for near-duplicates
    - Configurable similarity thresholds
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.exact_duplicates: Dict[str, List[ContentBlock]] = defaultdict(list)
        self.semantic_groups: List[DuplicateGroup] = []

    def add_content(self, block: ContentBlock):
        """Add content block for deduplication"""
        content_hash = block.get_hash()
        self.exact_duplicates[content_hash].append(block)

    def find_exact_duplicates(self) -> List[DuplicateGroup]:
        """Find exact duplicate groups"""
        groups = []

        for content_hash, blocks in self.exact_duplicates.items():
            if len(blocks) > 1:
                group = DuplicateGroup(
                    representative=blocks[0],
                    duplicates=blocks[1:],
                    similarity_scores=[1.0] * (len(blocks) - 1)
                )
                groups.append(group)

        return groups

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def find_semantic_duplicates(self, blocks: List[ContentBlock]) -> List[DuplicateGroup]:
        """Find semantically similar content groups"""
        if not blocks:
            return []

        # Filter blocks with embeddings
        blocks_with_embeddings = [b for b in blocks if b.embedding]
        if not blocks_with_embeddings:
            return []

        groups = []
        processed: Set[str] = set()

        for i, block1 in enumerate(blocks_with_embeddings):
            if block1.id in processed:
                continue

            group = DuplicateGroup(representative=block1)
            processed.add(block1.id)

            for block2 in blocks_with_embeddings[i+1:]:
                if block2.id in processed:
                    continue

                similarity = self.cosine_similarity(block1.embedding, block2.embedding)

                if similarity >= self.similarity_threshold:
                    group.duplicates.append(block2)
                    group.similarity_scores.append(similarity)
                    processed.add(block2.id)

            if group.duplicates:
                groups.append(group)

        return groups

    def deduplicate(self, blocks: List[ContentBlock]) -> Tuple[List[ContentBlock], Dict]:
        """
        Deduplicate content blocks

        Returns:
            Tuple of (deduplicated_blocks, stats)
        """
        # Add all blocks
        for block in blocks:
            self.add_content(block)

        # Find exact duplicates
        exact_groups = self.find_exact_duplicates()

        # Find semantic duplicates (excluding exact duplicates)
        all_block_ids = {b.id for b in blocks}
        exact_duplicate_ids = {
            b.id for group in exact_groups
            for b in group.duplicates
        }
        remaining_blocks = [b for b in blocks if b.id not in exact_duplicate_ids]
        semantic_groups = self.find_semantic_duplicates(remaining_blocks)

        # Build deduplicated list
        deduplicated = []
        removed_ids = exact_duplicate_ids | {
            b.id for group in semantic_groups
            for b in group.duplicates
        }

        for block in blocks:
            if block.id not in removed_ids:
                deduplicated.append(block)

        # Calculate stats
        original_size = sum(len(b.content) for b in blocks)
        deduplicated_size = sum(len(b.content) for b in deduplicated)

        stats = {
            'original_count': len(blocks),
            'deduplicated_count': len(deduplicated),
            'removed_count': len(blocks) - len(deduplicated),
            'exact_duplicate_groups': len(exact_groups),
            'semantic_duplicate_groups': len(semantic_groups),
            'original_size': original_size,
            'deduplicated_size': deduplicated_size,
            'size_reduction': original_size - deduplicated_size,
            'reduction_percentage': (1 - deduplicated_size / original_size) * 100 if original_size > 0 else 0
        }

        return deduplicated, stats


def create_simple_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Create simple embedding for testing

    In production, use proper embedding models like:
    - sentence-transformers
    - OpenAI embeddings
    - Cohere embeddings
    """
    # Simple hash-based embedding for testing
    hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)

    embedding = []
    for i in range(dim):
        # Generate pseudo-random values based on hash
        val = ((hash_val >> i) & 0xFF) / 255.0
        embedding.append(val)

    # Normalize
    norm = sum(x * x for x in embedding) ** 0.5
    if norm > 0:
        embedding = [x / norm for x in embedding]

    return embedding
