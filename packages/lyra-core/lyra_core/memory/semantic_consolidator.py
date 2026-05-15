"""
Semantic Consolidation Daemon - MEMTIER Implementation

Async LLM extraction of durable facts from episodic clusters.
Achieves 164× fact reduction (509 heuristic → 3.1 LLM facts per query)
with 51× F1 improvement.

Based on research: docs/153 (memtier-llm-distillation-and-the-three-invariants.md)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib


@dataclass
class SemanticFact:
    """Distilled semantic fact from episodic memory."""
    id: str
    fact: str
    source_sessions: List[str]
    source_entry_ids: List[str]
    extracted_at: datetime
    cognitive_weight: float
    tags: List[str]
    confidence: float  # LLM confidence in this fact


class SemanticConsolidator:
    """
    Consolidates episodic entries into semantic facts using LLM distillation.

    Runs as async daemon (daily/hourly) to extract durable facts from
    episodic clusters.
    """

    def __init__(
        self,
        episodic_memory,
        semantic_store_path: Optional[Path] = None,
        llm_model: str = "deepseek-v4-flash"
    ):
        """
        Initialize semantic consolidator.

        Args:
            episodic_memory: EpisodicMemory instance
            semantic_store_path: Path to semantic facts JSON file
            llm_model: LLM model for fact extraction
        """
        self.episodic = episodic_memory

        if semantic_store_path is None:
            semantic_store_path = Path.home() / ".lyra" / "memory" / "semantic_facts.json"

        self.semantic_store_path = Path(semantic_store_path)
        self.semantic_store_path.parent.mkdir(parents=True, exist_ok=True)

        self.llm_model = llm_model
        self.facts: List[SemanticFact] = self._load_facts()

    def _load_facts(self) -> List[SemanticFact]:
        """Load existing semantic facts from disk."""
        if not self.semantic_store_path.exists():
            return []

        with open(self.semantic_store_path, 'r') as f:
            facts_data = json.load(f)

        facts = []
        for fact_dict in facts_data:
            fact_dict['extracted_at'] = datetime.fromisoformat(fact_dict['extracted_at'])
            facts.append(SemanticFact(**fact_dict))

        return facts

    def _save_facts(self) -> None:
        """Save semantic facts to disk."""
        facts_data = []
        for fact in self.facts:
            fact_dict = {
                'id': fact.id,
                'fact': fact.fact,
                'source_sessions': fact.source_sessions,
                'source_entry_ids': fact.source_entry_ids,
                'extracted_at': fact.extracted_at.isoformat(),
                'cognitive_weight': fact.cognitive_weight,
                'tags': fact.tags,
                'confidence': fact.confidence
            }
            facts_data.append(fact_dict)

        with open(self.semantic_store_path, 'w') as f:
            json.dump(facts_data, f, indent=2)

    def _cluster_entries(
        self,
        entries: List[Any]
    ) -> List[List[Any]]:
        """
        Cluster episodic entries by session and time window.

        Simple clustering: group by session, then by 1-hour time windows.

        Args:
            entries: List of EpisodicEntry objects

        Returns:
            List of entry clusters
        """
        # Group by session
        session_groups: Dict[str, List[Any]] = {}
        for entry in entries:
            if entry.session_id not in session_groups:
                session_groups[entry.session_id] = []
            session_groups[entry.session_id].append(entry)

        # Further cluster by time windows within each session
        clusters = []
        for session_entries in session_groups.values():
            # Sort by timestamp
            session_entries.sort(key=lambda e: e.timestamp)

            current_cluster = []
            cluster_start = None

            for entry in session_entries:
                if cluster_start is None:
                    cluster_start = entry.timestamp
                    current_cluster = [entry]
                elif (entry.timestamp - cluster_start) < timedelta(hours=1):
                    current_cluster.append(entry)
                else:
                    # Start new cluster
                    if current_cluster:
                        clusters.append(current_cluster)
                    cluster_start = entry.timestamp
                    current_cluster = [entry]

            if current_cluster:
                clusters.append(current_cluster)

        return clusters

    def _extract_facts_from_cluster(
        self,
        cluster: List[Any],
        llm
    ) -> List[Dict[str, Any]]:
        """
        Extract semantic facts from a cluster using LLM.

        Args:
            cluster: List of EpisodicEntry objects
            llm: LLM instance for fact extraction

        Returns:
            List of extracted facts with metadata
        """
        # Format cluster for LLM
        events_text = []
        for entry in cluster:
            events_text.append(
                f"[{entry.timestamp.strftime('%H:%M')}] {entry.event_type}: {entry.content}"
            )

        prompt = f"""Extract durable, factual statements from these session events.

Focus on:
- Decisions made
- Patterns discovered
- User preferences
- Technical facts
- Important outcomes

Ignore:
- Transient state
- Debugging steps
- Exploratory queries
- Temporary errors

Events:
{chr(10).join(events_text)}

Output format (JSON array):
[
  {{
    "fact": "Present tense, declarative sentence",
    "tags": ["category1", "category2"],
    "confidence": 0.9
  }}
]

Extract only novel, durable facts. Be concise."""

        try:
            response = llm.generate(prompt, model=self.llm_model)
            facts = json.loads(response)
            return facts
        except Exception as e:
            print(f"Error extracting facts: {e}")
            return []

    def _jaccard_similarity(self, fact1: str, fact2: str) -> float:
        """Compute Jaccard similarity between two facts."""
        words1 = set(fact1.lower().split())
        words2 = set(fact2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _is_duplicate(self, new_fact: str, threshold: float = 0.7) -> bool:
        """Check if a fact is duplicate using Jaccard similarity."""
        for existing_fact in self.facts:
            similarity = self._jaccard_similarity(new_fact, existing_fact.fact)
            if similarity >= threshold:
                return True
        return False

    def consolidate(
        self,
        llm,
        days_back: int = 1,
        dedup_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run consolidation: extract facts from recent episodic entries.

        Args:
            llm: LLM instance for fact extraction
            days_back: Number of days to consolidate (default: 1)
            dedup_threshold: Jaccard similarity threshold for deduplication

        Returns:
            Consolidation statistics
        """
        # Get unpromoted entries from last N days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        unpromoted = self.episodic.get_unpromoted_entries()

        # Filter by date range
        entries = [
            e for e in unpromoted
            if start_date <= e.timestamp <= end_date
        ]

        if not entries:
            return {
                'entries_processed': 0,
                'clusters_formed': 0,
                'facts_extracted': 0,
                'facts_deduplicated': 0,
                'facts_added': 0
            }

        # Cluster entries
        clusters = self._cluster_entries(entries)

        # Extract facts from each cluster
        total_extracted = 0
        total_deduplicated = 0
        total_added = 0

        for cluster in clusters:
            extracted_facts = self._extract_facts_from_cluster(cluster, llm)

            for fact_data in extracted_facts:
                total_extracted += 1

                # Deduplicate
                if self._is_duplicate(fact_data['fact'], dedup_threshold):
                    total_deduplicated += 1
                    continue

                # Create semantic fact
                fact_id = f"sem_{hashlib.md5(fact_data['fact'].encode()).hexdigest()[:12]}"

                semantic_fact = SemanticFact(
                    id=fact_id,
                    fact=fact_data['fact'],
                    source_sessions=list(set(e.session_id for e in cluster)),
                    source_entry_ids=[e.id for e in cluster],
                    extracted_at=datetime.now(),
                    cognitive_weight=0.0,
                    tags=fact_data.get('tags', []),
                    confidence=fact_data.get('confidence', 0.8)
                )

                self.facts.append(semantic_fact)
                total_added += 1

                # Mark source entries as promoted
                for entry in cluster:
                    self.episodic.mark_promoted(entry.id)

        # Save updated facts
        self._save_facts()

        return {
            'entries_processed': len(entries),
            'clusters_formed': len(clusters),
            'facts_extracted': total_extracted,
            'facts_deduplicated': total_deduplicated,
            'facts_added': total_added,
            'total_facts': len(self.facts)
        }

    def search_facts(
        self,
        query: str,
        k: int = 5,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search semantic facts (simple keyword matching).

        For production, use dense embeddings or BM25.

        Args:
            query: Search query
            k: Number of results
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching facts with scores
        """
        query_words = set(query.lower().split())

        results = []
        for fact in self.facts:
            if fact.confidence < min_confidence:
                continue

            # Simple keyword matching
            fact_words = set(fact.fact.lower().split())
            score = len(query_words.intersection(fact_words)) / len(query_words)

            if score > 0:
                results.append({
                    'id': fact.id,
                    'fact': fact.fact,
                    'score': score,
                    'confidence': fact.confidence,
                    'tags': fact.tags,
                    'cognitive_weight': fact.cognitive_weight
                })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results[:k]
