"""
Research strategies for intelligent search and filtering.

Implements search strategies, query expansion, and intelligent filtering.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
import re


class SearchStrategy(str, Enum):
    """Search strategy type."""
    BREADTH_FIRST = "breadth_first"  # Survey approach
    DEPTH_FIRST = "depth_first"  # Deep dive
    CITATION_FORWARD = "citation_forward"  # Papers citing this
    CITATION_BACKWARD = "citation_backward"  # Papers cited by this
    SNOWBALL = "snowball"  # Iterative expansion
    SYSTEMATIC = "systematic"  # Comprehensive review


@dataclass
class SearchPlan:
    """A research search plan."""
    query: str
    strategy: SearchStrategy
    max_results: int = 100
    filters: Dict = field(default_factory=dict)
    expansion_terms: List[str] = field(default_factory=list)


@dataclass
class RankedResult:
    """A ranked search result."""
    source_id: str
    title: str
    relevance_score: float
    quality_score: float
    novelty_score: float
    overall_score: float
    rank: int = 0


class QueryExpander:
    """Expand search queries with related terms."""

    def __init__(self):
        """Initialize query expander."""
        # Common synonyms for research terms
        self.synonyms = {
            'neural network': ['neural net', 'deep learning', 'artificial neural network'],
            'machine learning': ['ML', 'statistical learning', 'automated learning'],
            'natural language processing': ['NLP', 'language understanding', 'text processing'],
            'computer vision': ['CV', 'image processing', 'visual recognition'],
            'reinforcement learning': ['RL', 'reward learning', 'policy learning'],
        }

        # Common acronyms
        self.acronyms = {
            'CNN': 'convolutional neural network',
            'RNN': 'recurrent neural network',
            'LSTM': 'long short-term memory',
            'GAN': 'generative adversarial network',
            'BERT': 'bidirectional encoder representations from transformers',
            'GPT': 'generative pre-trained transformer',
        }

    def expand(self, query: str, max_expansions: int = 5) -> List[str]:
        """
        Expand query with related terms.

        Args:
            query: Original query
            max_expansions: Maximum expansion terms

        Returns:
            List of expansion terms
        """
        expansions = []
        query_lower = query.lower()

        # Add synonyms
        for term, syns in self.synonyms.items():
            if term in query_lower:
                expansions.extend(syns[:2])

        # Expand acronyms
        for acronym, full_form in self.acronyms.items():
            if acronym in query:
                expansions.append(full_form)

        # Add related terms (simplified - would use word embeddings in production)
        related = self._find_related_terms(query_lower)
        expansions.extend(related)

        return list(set(expansions))[:max_expansions]

    def _find_related_terms(self, query: str) -> List[str]:
        """Find related terms (simplified)."""
        related = []

        # If query mentions "learning", add related learning types
        if 'learning' in query:
            related.extend(['supervised', 'unsupervised', 'semi-supervised'])

        # If query mentions "model", add model types
        if 'model' in query:
            related.extend(['architecture', 'framework', 'algorithm'])

        # If query mentions "data", add data-related terms
        if 'data' in query:
            related.extend(['dataset', 'corpus', 'benchmark'])

        return related[:3]


class ResultFilter:
    """Filter and rank search results."""

    def filter_by_quality(
        self,
        results: List[Dict],
        min_quality: float = 0.5,
    ) -> List[Dict]:
        """
        Filter results by quality score.

        Args:
            results: List of results with quality scores
            min_quality: Minimum quality threshold

        Returns:
            Filtered results
        """
        return [
            r for r in results
            if r.get('quality_score', 0.0) >= min_quality
        ]

    def filter_by_recency(
        self,
        results: List[Dict],
        max_age_years: int = 5,
    ) -> List[Dict]:
        """
        Filter results by recency.

        Args:
            results: List of results with publication dates
            max_age_years: Maximum age in years

        Returns:
            Filtered results
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=max_age_years * 365)

        filtered = []
        for r in results:
            pub_date = r.get('published_date')
            if pub_date and pub_date >= cutoff:
                filtered.append(r)
            elif not pub_date:
                # Include if no date (better than excluding)
                filtered.append(r)

        return filtered

    def filter_by_citations(
        self,
        results: List[Dict],
        min_citations: int = 10,
    ) -> List[Dict]:
        """
        Filter results by citation count.

        Args:
            results: List of results with citation counts
            min_citations: Minimum citations

        Returns:
            Filtered results
        """
        return [
            r for r in results
            if r.get('citations', 0) >= min_citations
        ]

    def deduplicate(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate results.

        Args:
            results: List of results

        Returns:
            Deduplicated results
        """
        seen_ids = set()
        seen_titles = set()
        unique = []

        for r in results:
            result_id = r.get('id')
            title = r.get('title', '').lower()

            # Check ID
            if result_id and result_id in seen_ids:
                continue

            # Check title similarity (exact match)
            if title in seen_titles:
                continue

            seen_ids.add(result_id)
            seen_titles.add(title)
            unique.append(r)

        return unique


class ResultRanker:
    """Rank search results by multiple criteria."""

    def rank(
        self,
        results: List[Dict],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[RankedResult]:
        """
        Rank results by weighted criteria.

        Args:
            results: List of results to rank
            weights: Weights for each criterion

        Returns:
            Ranked results
        """
        if weights is None:
            weights = {
                'relevance': 0.4,
                'quality': 0.3,
                'novelty': 0.2,
                'recency': 0.1,
            }

        ranked = []

        for r in results:
            # Calculate scores
            relevance = r.get('relevance_score', 0.5)
            quality = r.get('quality_score', 0.5)
            novelty = self._calculate_novelty(r)
            recency = self._calculate_recency(r)

            # Weighted overall score
            overall = (
                weights.get('relevance', 0.4) * relevance +
                weights.get('quality', 0.3) * quality +
                weights.get('novelty', 0.2) * novelty +
                weights.get('recency', 0.1) * recency
            )

            ranked.append(RankedResult(
                source_id=r.get('id', ''),
                title=r.get('title', ''),
                relevance_score=relevance,
                quality_score=quality,
                novelty_score=novelty,
                overall_score=overall,
            ))

        # Sort by overall score
        ranked.sort(key=lambda x: x.overall_score, reverse=True)

        # Assign ranks
        for i, result in enumerate(ranked, 1):
            result.rank = i

        return ranked

    def _calculate_novelty(self, result: Dict) -> float:
        """Calculate novelty score."""
        # Simplified - would use citation patterns in production
        citations = result.get('citations', 0)

        # Very high citations might indicate well-known work (less novel)
        if citations > 1000:
            return 0.3
        elif citations > 100:
            return 0.5
        else:
            return 0.8  # Newer work is potentially more novel

    def _calculate_recency(self, result: Dict) -> float:
        """Calculate recency score."""
        from datetime import datetime

        pub_date = result.get('published_date')
        if not pub_date:
            return 0.5

        age_days = (datetime.now() - pub_date).days
        age_years = age_days / 365.0

        # Exponential decay
        if age_years < 1:
            return 1.0
        elif age_years < 2:
            return 0.8
        elif age_years < 3:
            return 0.6
        elif age_years < 5:
            return 0.4
        else:
            return 0.2


class ResearchPlanner:
    """Plan research strategies based on query and goals."""

    def plan(
        self,
        query: str,
        goal: str = "survey",
        max_results: int = 100,
    ) -> SearchPlan:
        """
        Create a research plan.

        Args:
            query: Research query
            goal: Research goal (survey, deep_dive, comparison, trend)
            max_results: Maximum results to retrieve

        Returns:
            Search plan
        """
        # Select strategy based on goal
        if goal == "survey":
            strategy = SearchStrategy.BREADTH_FIRST
            filters = {'min_quality': 0.6, 'max_age_years': 10}
        elif goal == "deep_dive":
            strategy = SearchStrategy.DEPTH_FIRST
            filters = {'min_quality': 0.7, 'min_citations': 50}
        elif goal == "comparison":
            strategy = SearchStrategy.SYSTEMATIC
            filters = {'min_quality': 0.6, 'max_age_years': 5}
        elif goal == "trend":
            strategy = SearchStrategy.BREADTH_FIRST
            filters = {'max_age_years': 2, 'min_quality': 0.5}
        else:
            strategy = SearchStrategy.BREADTH_FIRST
            filters = {}

        # Expand query
        expander = QueryExpander()
        expansion_terms = expander.expand(query)

        return SearchPlan(
            query=query,
            strategy=strategy,
            max_results=max_results,
            filters=filters,
            expansion_terms=expansion_terms,
        )

    def decompose_query(self, query: str) -> List[str]:
        """
        Decompose complex query into sub-queries.

        Args:
            query: Complex research query

        Returns:
            List of sub-queries
        """
        sub_queries = []

        # Split on "and"
        if ' and ' in query.lower():
            parts = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)
            sub_queries.extend(parts)
        else:
            sub_queries.append(query)

        # Extract specific aspects
        if 'comparison' in query.lower() or 'vs' in query.lower():
            # Extract items being compared
            items = re.findall(r'(\w+)\s+vs\s+(\w+)', query, re.IGNORECASE)
            for item1, item2 in items:
                sub_queries.append(item1)
                sub_queries.append(item2)

        return list(set(sub_queries))

    def estimate_time(self, plan: SearchPlan) -> Dict[str, float]:
        """
        Estimate time required for research plan.

        Args:
            plan: Search plan

        Returns:
            Time estimates in minutes
        """
        # Base time per result
        time_per_result = {
            SearchStrategy.BREADTH_FIRST: 0.5,  # Quick scan
            SearchStrategy.DEPTH_FIRST: 2.0,  # Deep read
            SearchStrategy.CITATION_FORWARD: 1.0,
            SearchStrategy.CITATION_BACKWARD: 1.0,
            SearchStrategy.SNOWBALL: 1.5,
            SearchStrategy.SYSTEMATIC: 3.0,  # Most thorough
        }

        base_time = time_per_result.get(plan.strategy, 1.0)
        total_time = base_time * plan.max_results

        return {
            'discovery': total_time * 0.2,  # 20% for discovery
            'analysis': total_time * 0.5,  # 50% for analysis
            'synthesis': total_time * 0.3,  # 30% for synthesis
            'total': total_time,
        }


class StoppingCriteria:
    """Determine when to stop research."""

    def should_stop(
        self,
        results_found: int,
        target_results: int,
        quality_threshold: float,
        current_quality: float,
        iterations: int,
        max_iterations: int = 10,
    ) -> bool:
        """
        Determine if research should stop.

        Args:
            results_found: Number of results found
            target_results: Target number of results
            quality_threshold: Minimum quality threshold
            current_quality: Current average quality
            iterations: Current iteration count
            max_iterations: Maximum iterations

        Returns:
            True if should stop
        """
        # Stop if target reached
        if results_found >= target_results:
            return True

        # Stop if quality is too low
        if current_quality < quality_threshold and iterations > 3:
            return True

        # Stop if max iterations reached
        if iterations >= max_iterations:
            return True

        return False

    def calculate_saturation(
        self,
        new_results: List[Dict],
        existing_results: List[Dict],
    ) -> float:
        """
        Calculate result saturation (diminishing returns).

        Args:
            new_results: Newly found results
            existing_results: Previously found results

        Returns:
            Saturation score (0.0-1.0)
        """
        if not new_results:
            return 1.0

        # Count truly new results
        existing_ids = {r.get('id') for r in existing_results}
        new_ids = {r.get('id') for r in new_results}
        truly_new = len(new_ids - existing_ids)

        # Saturation = proportion of duplicates
        saturation = 1.0 - (truly_new / len(new_results))

        return saturation
