"""
Rating System - User ratings and reviews for skills.

Provides:
- 5-star rating system
- Review text with moderation
- Aggregate ratings
- User reputation tracking
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class Rating:
    """User rating for a skill."""

    skill_name: str
    user_id: str
    stars: int  # 1-5
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    review_id: str | None = None


@dataclass
class Review:
    """User review for a skill."""

    review_id: str
    skill_name: str
    user_id: str
    rating: int  # 1-5
    title: str
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    helpful_count: int = 0
    flagged: bool = False
    moderation_status: str = "pending"  # pending, approved, rejected


@dataclass
class AggregateRating:
    """Aggregate rating statistics for a skill."""

    skill_name: str
    average_rating: float
    total_ratings: int
    rating_distribution: dict[int, int]  # {stars: count}
    total_reviews: int


@dataclass
class UserReputation:
    """User reputation based on review quality."""

    user_id: str
    total_reviews: int
    helpful_reviews: int
    reputation_score: float  # 0.0-1.0
    verified_reviewer: bool = False


class RatingStorage(Protocol):
    """Protocol for rating storage backends."""

    def save_rating(self, rating: Rating) -> None:
        """Save a rating."""
        ...

    def save_review(self, review: Review) -> None:
        """Save a review."""
        ...

    def get_ratings(self, skill_name: str) -> list[Rating]:
        """Get all ratings for a skill."""
        ...

    def get_reviews(self, skill_name: str) -> list[Review]:
        """Get all reviews for a skill."""
        ...

    def get_user_rating(self, skill_name: str, user_id: str) -> Rating | None:
        """Get user's rating for a skill."""
        ...


class InMemoryRatingStorage:
    """In-memory rating storage for testing."""

    def __init__(self):
        self._ratings: list[Rating] = []
        self._reviews: list[Review] = []

    def save_rating(self, rating: Rating) -> None:
        """Save a rating."""
        # Remove existing rating from same user
        self._ratings = [
            r
            for r in self._ratings
            if not (r.skill_name == rating.skill_name and r.user_id == rating.user_id)
        ]
        self._ratings.append(rating)

    def save_review(self, review: Review) -> None:
        """Save a review."""
        # Remove existing review with same ID
        self._reviews = [r for r in self._reviews if r.review_id != review.review_id]
        self._reviews.append(review)

    def get_ratings(self, skill_name: str) -> list[Rating]:
        """Get all ratings for a skill."""
        return [r for r in self._ratings if r.skill_name == skill_name]

    def get_reviews(self, skill_name: str) -> list[Review]:
        """Get all reviews for a skill."""
        return [r for r in self._reviews if r.skill_name == skill_name]

    def get_user_rating(self, skill_name: str, user_id: str) -> Rating | None:
        """Get user's rating for a skill."""
        for rating in self._ratings:
            if rating.skill_name == skill_name and rating.user_id == user_id:
                return rating
        return None


class RatingSystem:
    """
    Rating and review system for skills.

    Features:
    - 5-star rating system
    - Text reviews with moderation
    - Aggregate statistics
    - User reputation tracking
    - Helpful vote system
    """

    def __init__(self, storage: RatingStorage | None = None):
        self.storage = storage or InMemoryRatingStorage()
        self._user_reputations: dict[str, UserReputation] = {}

    def rate_skill(
        self,
        skill_name: str,
        user_id: str,
        stars: int,
    ) -> bool:
        """
        Rate a skill.

        Args:
            skill_name: Skill name
            user_id: User identifier
            stars: Rating (1-5)

        Returns:
            True if successful
        """
        if not 1 <= stars <= 5:
            return False

        rating = Rating(
            skill_name=skill_name,
            user_id=user_id,
            stars=stars,
        )

        self.storage.save_rating(rating)
        return True

    def submit_review(
        self,
        review_id: str,
        skill_name: str,
        user_id: str,
        rating: int,
        title: str,
        text: str,
    ) -> bool:
        """
        Submit a review.

        Args:
            review_id: Unique review ID
            skill_name: Skill name
            user_id: User identifier
            rating: Rating (1-5)
            title: Review title
            text: Review text

        Returns:
            True if successful
        """
        if not 1 <= rating <= 5:
            return False

        if len(text.strip()) < 10:
            return False  # Minimum review length

        # Check for spam/abuse
        if self._is_spam(text):
            return False

        review = Review(
            review_id=review_id,
            skill_name=skill_name,
            user_id=user_id,
            rating=rating,
            title=title,
            text=text,
            moderation_status="approved",  # Auto-approve for now
        )

        self.storage.save_review(review)

        # Also save rating
        self.rate_skill(skill_name, user_id, rating)

        # Update user reputation
        self._update_user_reputation(user_id)

        return True

    def get_aggregate_rating(self, skill_name: str) -> AggregateRating | None:
        """
        Get aggregate rating for a skill.

        Args:
            skill_name: Skill name

        Returns:
            AggregateRating or None if no ratings
        """
        ratings = self.storage.get_ratings(skill_name)
        if not ratings:
            return None

        # Calculate distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            distribution[rating.stars] += 1

        # Calculate average
        total_stars = sum(r.stars for r in ratings)
        average = total_stars / len(ratings)

        # Count reviews
        reviews = self.storage.get_reviews(skill_name)

        return AggregateRating(
            skill_name=skill_name,
            average_rating=average,
            total_ratings=len(ratings),
            rating_distribution=distribution,
            total_reviews=len(reviews),
        )

    def get_reviews(
        self,
        skill_name: str,
        sort_by: str = "recent",
        limit: int = 10,
    ) -> list[Review]:
        """
        Get reviews for a skill.

        Args:
            skill_name: Skill name
            sort_by: Sort order (recent, helpful, rating)
            limit: Maximum number to return

        Returns:
            List of reviews
        """
        reviews = self.storage.get_reviews(skill_name)

        # Filter out flagged/rejected
        reviews = [
            r for r in reviews if not r.flagged and r.moderation_status == "approved"
        ]

        # Sort
        if sort_by == "recent":
            reviews.sort(key=lambda r: r.timestamp, reverse=True)
        elif sort_by == "helpful":
            reviews.sort(key=lambda r: r.helpful_count, reverse=True)
        elif sort_by == "rating":
            reviews.sort(key=lambda r: r.rating, reverse=True)

        return reviews[:limit]

    def mark_helpful(self, review_id: str) -> bool:
        """
        Mark a review as helpful.

        Args:
            review_id: Review ID

        Returns:
            True if successful
        """
        # Find review
        for review in self.storage._reviews:  # type: ignore
            if review.review_id == review_id:
                review.helpful_count += 1
                self.storage.save_review(review)
                return True
        return False

    def flag_review(self, review_id: str, reason: str) -> bool:
        """
        Flag a review for moderation.

        Args:
            review_id: Review ID
            reason: Reason for flagging

        Returns:
            True if successful
        """
        # Find review
        for review in self.storage._reviews:  # type: ignore
            if review.review_id == review_id:
                review.flagged = True
                review.moderation_status = "pending"
                self.storage.save_review(review)
                return True
        return False

    def get_user_reputation(self, user_id: str) -> UserReputation:
        """
        Get user reputation.

        Args:
            user_id: User identifier

        Returns:
            UserReputation
        """
        if user_id in self._user_reputations:
            return self._user_reputations[user_id]

        # Calculate reputation
        return self._calculate_reputation(user_id)

    def _calculate_reputation(self, user_id: str) -> UserReputation:
        """Calculate user reputation based on review quality."""
        # Count user's reviews across all known skills
        all_reviews = list(self.storage._reviews)  # type: ignore[attr-defined]

        user_reviews = [r for r in all_reviews if r.user_id == user_id]
        total_reviews = len(user_reviews)

        if total_reviews == 0:
            return UserReputation(
                user_id=user_id,
                total_reviews=0,
                helpful_reviews=0,
                reputation_score=0.5,  # Neutral
            )

        # Count helpful reviews
        helpful_reviews = sum(1 for r in user_reviews if r.helpful_count > 0)

        # Calculate score
        # Factors: review count, helpful ratio, not flagged
        helpful_ratio = helpful_reviews / total_reviews if total_reviews > 0 else 0
        flagged_count = sum(1 for r in user_reviews if r.flagged)
        flagged_penalty = flagged_count * 0.1

        score = min(1.0, helpful_ratio * 0.7 + min(total_reviews / 10, 0.3))
        score = max(0.0, score - flagged_penalty)

        reputation = UserReputation(
            user_id=user_id,
            total_reviews=total_reviews,
            helpful_reviews=helpful_reviews,
            reputation_score=score,
            verified_reviewer=(total_reviews >= 5 and score >= 0.7),
        )

        self._user_reputations[user_id] = reputation
        return reputation

    def _update_user_reputation(self, user_id: str) -> None:
        """Update user reputation after new review."""
        self._user_reputations[user_id] = self._calculate_reputation(user_id)

    def _is_spam(self, text: str) -> bool:
        """Check if text is spam."""
        # Simple spam detection
        spam_patterns = [
            "buy now",
            "click here",
            "free money",
            "limited time",
            "act now",
        ]

        text_lower = text.lower()
        for pattern in spam_patterns:
            if pattern in text_lower:
                return True

        # Check for excessive caps
        if len(text) > 20:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                return True

        return False

    def get_top_reviewers(self, limit: int = 10) -> list[UserReputation]:
        """
        Get top reviewers by reputation.

        Args:
            limit: Maximum number to return

        Returns:
            List of user reputations
        """
        reputations = list(self._user_reputations.values())
        reputations.sort(key=lambda r: r.reputation_score, reverse=True)
        return reputations[:limit]

    def get_rating_summary(self, skill_name: str) -> dict:
        """
        Get comprehensive rating summary.

        Args:
            skill_name: Skill name

        Returns:
            Dictionary with rating statistics
        """
        aggregate = self.get_aggregate_rating(skill_name)
        if not aggregate:
            return {"error": "No ratings available"}

        reviews = self.get_reviews(skill_name, limit=5)

        return {
            "skill_name": skill_name,
            "average_rating": f"{aggregate.average_rating:.2f}",
            "total_ratings": aggregate.total_ratings,
            "total_reviews": aggregate.total_reviews,
            "distribution": aggregate.rating_distribution,
            "recent_reviews": [
                {
                    "title": r.title,
                    "rating": r.rating,
                    "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
                    "helpful_count": r.helpful_count,
                }
                for r in reviews
            ],
        }

    def has_user_rated(self, skill_name: str, user_id: str) -> bool:
        """
        Check if user has rated a skill.

        Args:
            skill_name: Skill name
            user_id: User identifier

        Returns:
            True if user has rated
        """
        return self.storage.get_user_rating(skill_name, user_id) is not None

    def get_user_rating(self, skill_name: str, user_id: str) -> int | None:
        """
        Get user's rating for a skill.

        Args:
            skill_name: Skill name
            user_id: User identifier

        Returns:
            Rating (1-5) or None
        """
        rating = self.storage.get_user_rating(skill_name, user_id)
        return rating.stars if rating else None
