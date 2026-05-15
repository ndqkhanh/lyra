"""
Contradiction Checker for Semantic Memory

Detects and resolves contradictions before consolidation.
Implements doc 316 lifecycle requirement: "Rerank and check for contradictions"

Based on research: Doc 316 (LLM Agent Memory Systems)
Impact: Prevents conflicting facts in semantic memory
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class Contradiction:
    """Detected contradiction between facts."""
    fact1_id: str
    fact2_id: str
    fact1_text: str
    fact2_text: str
    contradiction_type: str  # "direct", "temporal", "logical"
    confidence: float
    explanation: str
    resolution: Optional[str] = None  # "keep_fact1", "keep_fact2", "keep_both", "reject_both"


class ContradictionChecker:
    """
    Checks for contradictions between facts before consolidation.

    Contradiction types:
    - Direct: "Alice lives in NYC" vs "Alice lives in LA" (same time)
    - Temporal: Resolved by temporal validity
    - Logical: "Alice is 25" vs "Alice was born in 1990" (in 2010)
    """

    def __init__(self, llm):
        """
        Initialize contradiction checker.

        Args:
            llm: LLM instance for contradiction detection
        """
        self.llm = llm

    def check_pair(
        self,
        fact1: str,
        fact2: str,
        fact1_time: Optional[datetime] = None,
        fact2_time: Optional[datetime] = None
    ) -> Optional[Contradiction]:
        """
        Check if two facts contradict each other.

        Args:
            fact1: First fact text
            fact2: Second fact text
            fact1_time: When fact1 is valid
            fact2_time: When fact2 is valid

        Returns:
            Contradiction if detected, None otherwise
        """
        # If facts have different valid times, they may not contradict
        if fact1_time and fact2_time and fact1_time != fact2_time:
            # Temporal facts can coexist
            return None

        prompt = f"""Check if these two facts contradict each other.

Fact 1: {fact1}
Fact 2: {fact2}

Determine:
1. Do they contradict? (yes/no)
2. Type: direct, temporal, or logical
3. Confidence: 0.0-1.0
4. Explanation: Why they contradict

Output JSON:
{{
  "contradicts": true/false,
  "type": "direct",
  "confidence": 0.9,
  "explanation": "Both facts claim different locations for the same person at the same time"
}}
"""

        try:
            response = self.llm.generate(prompt)
            result = json.loads(response)

            if not result.get('contradicts', False):
                return None

            return Contradiction(
                fact1_id="",  # Will be filled by caller
                fact2_id="",
                fact1_text=fact1,
                fact2_text=fact2,
                contradiction_type=result.get('type', 'direct'),
                confidence=result.get('confidence', 0.5),
                explanation=result.get('explanation', 'No explanation provided')
            )

        except Exception as e:
            print(f"Error checking contradiction: {e}")
            return None

    def check_batch(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[Contradiction]:
        """
        Check for contradictions in a batch of facts.

        Args:
            facts: List of fact dicts with 'id', 'fact', 'valid_at'

        Returns:
            List of detected contradictions
        """
        contradictions = []

        # Check all pairs
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                fact1 = facts[i]
                fact2 = facts[j]

                contradiction = self.check_pair(
                    fact1['fact'],
                    fact2['fact'],
                    fact1.get('valid_at'),
                    fact2.get('valid_at')
                )

                if contradiction:
                    contradiction.fact1_id = fact1['id']
                    contradiction.fact2_id = fact2['id']
                    contradictions.append(contradiction)

        return contradictions

    def resolve_contradiction(
        self,
        contradiction: Contradiction,
        fact1_confidence: float,
        fact2_confidence: float,
        fact1_source: str,
        fact2_source: str
    ) -> str:
        """
        Resolve a contradiction using confidence and source.

        Args:
            contradiction: Detected contradiction
            fact1_confidence: Confidence of fact1
            fact2_confidence: Confidence of fact2
            fact1_source: Source of fact1
            fact2_source: Source of fact2

        Returns:
            Resolution: "keep_fact1", "keep_fact2", "keep_both", "reject_both"
        """
        # If contradiction confidence is low, keep both
        if contradiction.confidence < 0.7:
            return "keep_both"

        # If one fact has much higher confidence, keep it
        if fact1_confidence > fact2_confidence + 0.2:
            return "keep_fact1"
        if fact2_confidence > fact1_confidence + 0.2:
            return "keep_fact2"

        # If confidences are similar, use source priority
        source_priority = {
            "user": 3,
            "verified": 2,
            "extracted": 1,
            "inferred": 0
        }

        priority1 = source_priority.get(fact1_source, 0)
        priority2 = source_priority.get(fact2_source, 0)

        if priority1 > priority2:
            return "keep_fact1"
        if priority2 > priority1:
            return "keep_fact2"

        # If all else equal, reject both to be safe
        return "reject_both"

    def filter_contradictions(
        self,
        facts: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Contradiction]]:
        """
        Filter out contradicting facts from a batch.

        Args:
            facts: List of fact dicts

        Returns:
            (filtered_facts, detected_contradictions)
        """
        contradictions = self.check_batch(facts)

        if not contradictions:
            return facts, []

        # Build rejection set
        rejected_ids = set()

        for contradiction in contradictions:
            fact1 = next(f for f in facts if f['id'] == contradiction.fact1_id)
            fact2 = next(f for f in facts if f['id'] == contradiction.fact2_id)

            resolution = self.resolve_contradiction(
                contradiction,
                fact1.get('confidence', 0.5),
                fact2.get('confidence', 0.5),
                fact1.get('source', 'unknown'),
                fact2.get('source', 'unknown')
            )

            contradiction.resolution = resolution

            if resolution == "keep_fact1":
                rejected_ids.add(contradiction.fact2_id)
            elif resolution == "keep_fact2":
                rejected_ids.add(contradiction.fact1_id)
            elif resolution == "reject_both":
                rejected_ids.add(contradiction.fact1_id)
                rejected_ids.add(contradiction.fact2_id)
            # "keep_both" means no rejection

        # Filter facts
        filtered_facts = [f for f in facts if f['id'] not in rejected_ids]

        return filtered_facts, contradictions


# Integration with semantic consolidator
def add_contradiction_checking_to_consolidator(
    semantic_consolidator,
    llm
) -> None:
    """
    Add contradiction checking to semantic consolidator.

    This should be called before consolidation writes facts.

    Args:
        semantic_consolidator: SemanticConsolidator instance
        llm: LLM instance
    """
    checker = ContradictionChecker(llm)

    # Convert facts to dict format
    facts_dicts = [
        {
            'id': f.id,
            'fact': f.fact,
            'confidence': f.confidence,
            'source': f.source,
            'valid_at': getattr(f, 'valid_at', None)
        }
        for f in semantic_consolidator.facts
    ]

    # Filter contradictions
    filtered_facts, contradictions = checker.filter_contradictions(facts_dicts)

    # Update consolidator facts
    filtered_ids = {f['id'] for f in filtered_facts}
    semantic_consolidator.facts = [
        f for f in semantic_consolidator.facts
        if f.id in filtered_ids
    ]

    # Log contradictions
    if contradictions:
        print(f"Detected and resolved {len(contradictions)} contradictions")
        for c in contradictions:
            print(f"  {c.contradiction_type}: {c.explanation}")
            print(f"  Resolution: {c.resolution}")


# Usage example
"""
from lyra_core.memory.contradiction_checker import ContradictionChecker
from lyra_core.llm import build_llm

# Initialize
llm = build_llm("deepseek-v4-pro")
checker = ContradictionChecker(llm)

# Check pair
contradiction = checker.check_pair(
    "Alice lives in New York",
    "Alice lives in Los Angeles"
)

if contradiction:
    print(f"Contradiction detected: {contradiction.explanation}")
    print(f"Confidence: {contradiction.confidence}")

# Check batch
facts = [
    {'id': '1', 'fact': 'Alice is 25 years old', 'confidence': 0.9, 'source': 'user'},
    {'id': '2', 'fact': 'Alice is 30 years old', 'confidence': 0.8, 'source': 'extracted'},
]

filtered_facts, contradictions = checker.filter_contradictions(facts)
print(f"Filtered {len(facts) - len(filtered_facts)} contradicting facts")
"""
