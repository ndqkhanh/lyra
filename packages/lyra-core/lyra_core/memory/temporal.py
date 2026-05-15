"""
Graphiti Temporal Validity for Lyra Memory

Implements temporal validity windows for facts: valid_at / invalid_at timestamps.
Handles time-dependent information natively.

Based on research: docs/182 (memory-frontiers-2026.md), Zep/Graphiti
Impact: +15pts on LongMemEval (63.8% vs 49.0%)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class TemporalFact:
    """Fact with temporal validity window."""
    id: str
    fact: str
    valid_at: datetime
    invalid_at: Optional[datetime]
    source: str
    confidence: float
    tags: List[str]
    metadata: Dict[str, Any]

    def is_valid_at(self, query_time: datetime) -> bool:
        """
        Check if fact is valid at a specific time.

        Args:
            query_time: Time to check validity

        Returns:
            True if fact is valid at query_time
        """
        if query_time < self.valid_at:
            return False

        if self.invalid_at is not None and query_time >= self.invalid_at:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'fact': self.fact,
            'valid_at': self.valid_at.isoformat(),
            'invalid_at': self.invalid_at.isoformat() if self.invalid_at else None,
            'source': self.source,
            'confidence': self.confidence,
            'tags': self.tags,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemporalFact':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            fact=data['fact'],
            valid_at=datetime.fromisoformat(data['valid_at']),
            invalid_at=datetime.fromisoformat(data['invalid_at']) if data['invalid_at'] else None,
            source=data['source'],
            confidence=data['confidence'],
            tags=data['tags'],
            metadata=data['metadata']
        )


class TemporalMemoryStore:
    """
    Storage for temporal facts with validity windows.

    Supports:
    - Point-in-time queries
    - Temporal range queries
    - Fact invalidation
    - Temporal conflict resolution
    """

    def __init__(self, store_path: str):
        """
        Initialize temporal memory store.

        Args:
            store_path: Path to JSON storage file
        """
        self.store_path = store_path
        self.facts: List[TemporalFact] = self._load_facts()

    def _load_facts(self) -> List[TemporalFact]:
        """Load facts from disk."""
        try:
            with open(self.store_path, 'r') as f:
                data = json.load(f)
                return [TemporalFact.from_dict(f) for f in data]
        except FileNotFoundError:
            return []

    def _save_facts(self) -> None:
        """Save facts to disk."""
        with open(self.store_path, 'w') as f:
            json.dump([f.to_dict() for f in self.facts], f, indent=2)

    def add_fact(
        self,
        fact: str,
        valid_at: Optional[datetime] = None,
        invalid_at: Optional[datetime] = None,
        source: str = "user",
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalFact:
        """
        Add a temporal fact.

        Args:
            fact: Fact text
            valid_at: When fact becomes valid (default: now)
            invalid_at: When fact becomes invalid (default: None = still valid)
            source: Source of fact
            confidence: Confidence score
            tags: Tags for categorization
            metadata: Additional metadata

        Returns:
            Created TemporalFact
        """
        import uuid

        if valid_at is None:
            valid_at = datetime.now()

        temporal_fact = TemporalFact(
            id=f"tf_{uuid.uuid4().hex[:12]}",
            fact=fact,
            valid_at=valid_at,
            invalid_at=invalid_at,
            source=source,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {}
        )

        self.facts.append(temporal_fact)
        self._save_facts()

        return temporal_fact

    def invalidate_fact(self, fact_id: str, invalid_at: Optional[datetime] = None) -> bool:
        """
        Mark a fact as invalid.

        Args:
            fact_id: Fact ID to invalidate
            invalid_at: When fact becomes invalid (default: now)

        Returns:
            True if fact was found and invalidated
        """
        if invalid_at is None:
            invalid_at = datetime.now()

        for fact in self.facts:
            if fact.id == fact_id:
                fact.invalid_at = invalid_at
                self._save_facts()
                return True

        return False

    def query_at_time(
        self,
        query_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> List[TemporalFact]:
        """
        Query facts valid at a specific time.

        Args:
            query_time: Time to query (default: now)
            tags: Optional tag filter

        Returns:
            List of facts valid at query_time
        """
        if query_time is None:
            query_time = datetime.now()

        results = []
        for fact in self.facts:
            if not fact.is_valid_at(query_time):
                continue

            if tags and not any(tag in fact.tags for tag in tags):
                continue

            results.append(fact)

        return results

    def query_range(
        self,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[List[str]] = None
    ) -> List[TemporalFact]:
        """
        Query facts valid during a time range.

        Args:
            start_time: Range start
            end_time: Range end
            tags: Optional tag filter

        Returns:
            List of facts valid during the range
        """
        results = []
        for fact in self.facts:
            # Fact is valid during range if:
            # 1. It becomes valid before range ends
            # 2. It doesn't become invalid before range starts

            if fact.valid_at > end_time:
                continue

            if fact.invalid_at is not None and fact.invalid_at < start_time:
                continue

            if tags and not any(tag in fact.tags for tag in tags):
                continue

            results.append(fact)

        return results

    def get_fact_history(self, subject: str) -> List[TemporalFact]:
        """
        Get temporal history of facts about a subject.

        Args:
            subject: Subject to search for (keyword in fact text)

        Returns:
            List of facts mentioning subject, sorted by valid_at
        """
        subject_lower = subject.lower()
        results = [
            fact for fact in self.facts
            if subject_lower in fact.fact.lower()
        ]

        results.sort(key=lambda f: f.valid_at)
        return results

    def resolve_conflicts(self, subject: str, query_time: Optional[datetime] = None) -> Optional[TemporalFact]:
        """
        Resolve temporal conflicts for a subject.

        Returns the most recent valid fact about the subject.

        Args:
            subject: Subject to resolve
            query_time: Time to query (default: now)

        Returns:
            Most recent valid fact, or None
        """
        if query_time is None:
            query_time = datetime.now()

        valid_facts = [
            fact for fact in self.get_fact_history(subject)
            if fact.is_valid_at(query_time)
        ]

        if not valid_facts:
            return None

        # Return most recently valid fact
        return max(valid_facts, key=lambda f: f.valid_at)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about temporal facts."""
        now = datetime.now()

        currently_valid = sum(1 for f in self.facts if f.is_valid_at(now))
        invalidated = sum(1 for f in self.facts if f.invalid_at is not None)

        return {
            'total_facts': len(self.facts),
            'currently_valid': currently_valid,
            'invalidated': invalidated,
            'never_invalid': len(self.facts) - invalidated
        }


# LLM-based temporal extraction
def extract_temporal_facts(text: str, context_time: datetime, llm) -> List[Dict[str, Any]]:
    """
    Extract facts with temporal validity from text using LLM.

    Args:
        text: Input text
        context_time: Time context for extraction
        llm: LLM instance

    Returns:
        List of extracted facts with temporal metadata
    """
    prompt = f"""Extract facts with temporal validity from this text.
Context time: {context_time.isoformat()}

For each fact, determine:
- valid_at: When this fact became true (ISO format)
- invalid_at: When this fact stopped being true, or null if still valid
- confidence: Confidence score (0.0-1.0)

Text: {text}

Output JSON array:
[
  {{
    "fact": "Alice lived in New York",
    "valid_at": "2024-01-01T00:00:00",
    "invalid_at": "2025-01-01T00:00:00",
    "confidence": 0.9
  }},
  {{
    "fact": "Alice lives in Los Angeles",
    "valid_at": "2025-01-01T00:00:00",
    "invalid_at": null,
    "confidence": 0.95
  }}
]
"""

    try:
        response = llm.generate(prompt)
        facts = json.loads(response)
        return facts
    except Exception as e:
        print(f"Error extracting temporal facts: {e}")
        return []


# Integration with semantic consolidator
def add_temporal_to_semantic_facts(
    semantic_consolidator,
    temporal_store: TemporalMemoryStore,
    llm
) -> None:
    """
    Add temporal validity to existing semantic facts.

    Args:
        semantic_consolidator: SemanticConsolidator instance
        temporal_store: TemporalMemoryStore instance
        llm: LLM instance for extraction
    """
    for semantic_fact in semantic_consolidator.facts:
        # Extract temporal information
        temporal_facts = extract_temporal_facts(
            semantic_fact.fact,
            semantic_fact.extracted_at,
            llm
        )

        for tf in temporal_facts:
            temporal_store.add_fact(
                fact=tf['fact'],
                valid_at=datetime.fromisoformat(tf['valid_at']),
                invalid_at=datetime.fromisoformat(tf['invalid_at']) if tf['invalid_at'] else None,
                source=f"semantic_{semantic_fact.id}",
                confidence=tf['confidence'],
                tags=semantic_fact.tags
            )


# Usage example
"""
from lyra_core.memory.temporal import TemporalMemoryStore

# Initialize store
temporal = TemporalMemoryStore("~/.lyra/memory/temporal_facts.json")

# Add temporal facts
temporal.add_fact(
    "Alice lived in New York",
    valid_at=datetime(2024, 1, 1),
    invalid_at=datetime(2025, 1, 1),
    tags=["person", "location"]
)

temporal.add_fact(
    "Alice lives in Los Angeles",
    valid_at=datetime(2025, 1, 1),
    invalid_at=None,  # Still valid
    tags=["person", "location"]
)

# Query at specific time
facts_2024 = temporal.query_at_time(datetime(2024, 6, 1))
# Returns: "Alice lived in New York"

facts_2025 = temporal.query_at_time(datetime(2025, 6, 1))
# Returns: "Alice lives in Los Angeles"

# Resolve conflicts
current_location = temporal.resolve_conflicts("Alice", datetime.now())
# Returns most recent valid fact
"""
