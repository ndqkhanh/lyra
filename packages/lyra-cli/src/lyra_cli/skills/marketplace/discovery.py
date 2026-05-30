"""
Skill Discovery - Search and filtering for skills.

Provides:
- Search by name, tags, category, author
- Filter by rating, downloads, recency
- Trending skills detection
- Recommendation engine based on usage patterns
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from lyra_cli.skills.marketplace.registry import SkillPackage, SkillRegistry


class SortBy(StrEnum):
    """Sort options for search results."""

    RELEVANCE = "relevance"
    DOWNLOADS = "downloads"
    RATING = "rating"
    RECENT = "recent"
    NAME = "name"


@dataclass
class SearchFilter:
    """Filter criteria for skill search."""

    query: str | None = None
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    author: str | None = None
    min_rating: float | None = None
    min_downloads: int | None = None
    verified_only: bool = False
    max_results: int = 50


@dataclass
class SearchResult:
    """Single search result with relevance score."""

    package: SkillPackage
    relevance_score: float
    match_reasons: list[str] = field(default_factory=list)


@dataclass
class TrendingSkill:
    """Trending skill with growth metrics."""

    package: SkillPackage
    download_growth_pct: float
    recent_downloads: int
    trending_score: float


class SkillDiscovery:
    """
    Skill discovery and search system.

    Features:
    - Full-text search across name, description, tags
    - Multi-criteria filtering
    - Relevance scoring
    - Trending detection
    - Usage-based recommendations
    """

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        # Usage tracking for recommendations
        self._usage_history: dict[str, list[str]] = {}  # {user_id: [skill_names]}

    def search(
        self,
        filter: SearchFilter,
        sort_by: SortBy = SortBy.RELEVANCE,
    ) -> list[SearchResult]:
        """
        Search for skills with filtering and sorting.

        Args:
            filter: Search filter criteria
            sort_by: Sort order

        Returns:
            List of search results
        """
        results = []

        # Get all packages
        for name in self.registry.list_all():
            package = self.registry.get(name)
            if not package:
                continue

            # Apply filters
            if not self._matches_filter(package, filter):
                continue

            # Calculate relevance score
            score = self._calculate_relevance(package, filter)
            match_reasons = self._get_match_reasons(package, filter)

            results.append(
                SearchResult(
                    package=package,
                    relevance_score=score,
                    match_reasons=match_reasons,
                )
            )

        # Sort results
        results = self._sort_results(results, sort_by)

        # Limit results
        return results[: filter.max_results]

    def _matches_filter(self, package: SkillPackage, filter: SearchFilter) -> bool:
        """Check if package matches filter criteria."""
        # Verified only
        if filter.verified_only and not package.metadata.verified:
            return False

        # Category filter
        if filter.category and package.category.lower() != filter.category.lower():
            return False

        # Author filter
        if filter.author and filter.author.lower() not in package.author.lower():
            return False

        # Tag filter (must match all tags)
        if filter.tags:
            package_tags_lower = [t.lower() for t in package.tags]
            for tag in filter.tags:
                if tag.lower() not in package_tags_lower:
                    return False

        # Min downloads
        if (
            filter.min_downloads is not None
            and package.metadata.total_downloads < filter.min_downloads
        ):
            return False

        return True

    def _calculate_relevance(
        self,
        package: SkillPackage,
        filter: SearchFilter,
    ) -> float:
        """Calculate relevance score for a package."""
        if not filter.query:
            return 1.0

        query_lower = filter.query.lower()
        score = 0.0

        # Exact name match (highest weight)
        if package.name.lower() == query_lower:
            score += 10.0
        elif query_lower in package.name.lower():
            score += 5.0

        # Description match
        if query_lower in package.description.lower():
            # Count occurrences
            count = package.description.lower().count(query_lower)
            score += min(count * 2.0, 5.0)

        # Tag match
        for tag in package.tags:
            if query_lower in tag.lower():
                score += 3.0

        # Category match
        if query_lower in package.category.lower():
            score += 2.0

        # Author match
        if query_lower in package.author.lower():
            score += 1.0

        # Boost for verified packages
        if package.metadata.verified:
            score *= 1.2

        # Boost for popular packages
        if package.metadata.total_downloads > 100:
            score *= 1.1

        return score

    def _get_match_reasons(
        self,
        package: SkillPackage,
        filter: SearchFilter,
    ) -> list[str]:
        """Get human-readable match reasons."""
        reasons = []

        if not filter.query:
            return reasons

        query_lower = filter.query.lower()

        if query_lower in package.name.lower():
            reasons.append("Name match")

        if query_lower in package.description.lower():
            reasons.append("Description match")

        for tag in package.tags:
            if query_lower in tag.lower():
                reasons.append(f"Tag: {tag}")
                break

        if query_lower in package.category.lower():
            reasons.append(f"Category: {package.category}")

        if package.metadata.verified:
            reasons.append("Verified")

        return reasons

    def _sort_results(
        self,
        results: list[SearchResult],
        sort_by: SortBy,
    ) -> list[SearchResult]:
        """Sort search results."""
        if sort_by == SortBy.RELEVANCE:
            results.sort(key=lambda r: r.relevance_score, reverse=True)
        elif sort_by == SortBy.DOWNLOADS:
            results.sort(
                key=lambda r: r.package.metadata.total_downloads,
                reverse=True,
            )
        elif sort_by == SortBy.RECENT:
            results.sort(
                key=lambda r: r.package.metadata.last_updated,
                reverse=True,
            )
        elif sort_by == SortBy.NAME:
            results.sort(key=lambda r: r.package.name)

        return results

    def get_trending(
        self,
        days: int = 7,
        limit: int = 10,
    ) -> list[TrendingSkill]:
        """
        Get trending skills based on recent growth.

        Args:
            days: Number of days to analyze
            limit: Maximum number to return

        Returns:
            List of trending skills
        """
        # In a real implementation, this would track download history
        # For now, we'll use a simplified heuristic based on total downloads
        # and recent update activity

        trending = []
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        for name in self.registry.list_all():
            package = self.registry.get(name)
            if not package:
                continue

            # Skip if not recently updated
            if package.metadata.last_updated < cutoff_date:
                continue

            # Simplified trending score
            # In production, this would use actual download deltas
            recent_downloads = package.metadata.total_downloads
            download_growth_pct = 50.0  # Placeholder

            # Calculate trending score
            # Factors: recent downloads, growth rate, verification
            score = recent_downloads * 0.5 + download_growth_pct * 0.3
            if package.metadata.verified:
                score *= 1.2

            trending.append(
                TrendingSkill(
                    package=package,
                    download_growth_pct=download_growth_pct,
                    recent_downloads=recent_downloads,
                    trending_score=score,
                )
            )

        # Sort by trending score
        trending.sort(key=lambda t: t.trending_score, reverse=True)
        return trending[:limit]

    def recommend(
        self,
        user_id: str,
        limit: int = 5,
    ) -> list[SkillPackage]:
        """
        Recommend skills based on user's usage patterns.

        Args:
            user_id: User identifier
            limit: Maximum number to return

        Returns:
            List of recommended packages
        """
        # Get user's usage history
        used_skills = set(self._usage_history.get(user_id, []))

        if not used_skills:
            # No history, return popular skills
            return self.registry.get_most_downloaded(limit)

        # Find similar skills based on tags and categories
        recommendations = []
        seen_names = set()

        for skill_name in used_skills:
            package = self.registry.get(skill_name)
            if not package:
                continue

            # Find skills with similar tags
            for name in self.registry.list_all():
                if name in used_skills or name in seen_names:
                    continue

                candidate = self.registry.get(name)
                if not candidate:
                    continue

                # Calculate similarity
                similarity = self._calculate_similarity(package, candidate)
                if similarity > 0.3:  # Threshold
                    recommendations.append((candidate, similarity))
                    seen_names.add(name)

        # Sort by similarity
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return [pkg for pkg, _ in recommendations[:limit]]

    def _calculate_similarity(
        self,
        pkg1: SkillPackage,
        pkg2: SkillPackage,
    ) -> float:
        """Calculate similarity between two packages."""
        score = 0.0

        # Same category
        if pkg1.category == pkg2.category:
            score += 0.4

        # Shared tags
        tags1 = set(t.lower() for t in pkg1.tags)
        tags2 = set(t.lower() for t in pkg2.tags)
        shared_tags = tags1 & tags2
        if shared_tags:
            score += 0.3 * (len(shared_tags) / max(len(tags1), len(tags2)))

        # Same author
        if pkg1.author == pkg2.author:
            score += 0.2

        # Description similarity (simple word overlap)
        words1 = set(re.findall(r"\w+", pkg1.description.lower()))
        words2 = set(re.findall(r"\w+", pkg2.description.lower()))
        common_words = words1 & words2
        if common_words:
            score += 0.1 * (len(common_words) / max(len(words1), len(words2)))

        return min(score, 1.0)

    def record_usage(self, user_id: str, skill_name: str) -> None:
        """
        Record skill usage for recommendations.

        Args:
            user_id: User identifier
            skill_name: Skill name
        """
        if user_id not in self._usage_history:
            self._usage_history[user_id] = []

        if skill_name not in self._usage_history[user_id]:
            self._usage_history[user_id].append(skill_name)

    def search_by_keywords(self, keywords: list[str]) -> list[SkillPackage]:
        """
        Search by multiple keywords (OR logic).

        Args:
            keywords: List of keywords

        Returns:
            List of matching packages
        """
        results = set()

        for keyword in keywords:
            filter = SearchFilter(query=keyword, max_results=100)
            search_results = self.search(filter)
            for result in search_results:
                results.add(result.package.name)

        # Convert back to packages
        packages = []
        for name in results:
            package = self.registry.get(name)
            if package:
                packages.append(package)

        return packages

    def get_related_skills(
        self,
        skill_name: str,
        limit: int = 5,
    ) -> list[SkillPackage]:
        """
        Get skills related to a given skill.

        Args:
            skill_name: Skill name
            limit: Maximum number to return

        Returns:
            List of related packages
        """
        package = self.registry.get(skill_name)
        if not package:
            return []

        related = []
        for name in self.registry.list_all():
            if name == skill_name:
                continue

            candidate = self.registry.get(name)
            if not candidate:
                continue

            similarity = self._calculate_similarity(package, candidate)
            if similarity > 0.2:
                related.append((candidate, similarity))

        # Sort by similarity
        related.sort(key=lambda x: x[1], reverse=True)
        return [pkg for pkg, _ in related[:limit]]
