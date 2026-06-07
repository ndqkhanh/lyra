"""
User profile manager for Lyra personalization system.

Provides the UserProfileManager class that handles profile lifecycle,
interaction processing, skill assessment, and preference extraction.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from lyra.personalization.models import (
    CommunicationStyle,
    InteractionRecord,
    RichRepresentation,
    SkillLevel,
    UserProfile,
)

logger = logging.getLogger(__name__)


class UserProfileManager:
    """
    Manages user profiles: creation, updates, skill assessment,
    preference extraction, and communication style detection.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def create_profile(self, user_id: str) -> UserProfile:
        """
        Create a new user profile with the given user ID.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            A new UserProfile instance.

        Raises:
            ValueError: If a profile for this user_id already exists.
        """
        if user_id in self._profiles:
            raise ValueError(f"Profile already exists for user: {user_id}")

        rich_repr = RichRepresentation(user_id=user_id)
        profile = UserProfile(
            user_id=user_id,
            rich_repr=rich_repr,
        )
        self._profiles[user_id] = profile
        logger.info("Created profile for user: %s", user_id)
        return profile

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Retrieve a user profile by user ID."""
        return self._profiles.get(user_id)

    def update_from_interaction(
        self,
        profile: UserProfile,
        interaction: InteractionRecord,
    ) -> UserProfile:
        """
        Update a user profile based on a new interaction.

        Incorporates the interaction into the rich representation
        history and triggers incremental updates to preferences,
        skill levels, and communication style.

        Args:
            profile: The current user profile.
            interaction: The interaction to incorporate.

        Returns:
            Updated UserProfile with new interaction incorporated.
        """
        logger.debug(
            "Updating profile %s from interaction %s",
            profile.user_id,
            interaction.id,
        )

        new_history = list(profile.rich_repr.interaction_history)
        new_history.append(interaction)

        updated_rich = self._rebuild_rich_repr(profile, new_history)

        updated_profile = UserProfile(
            user_id=profile.user_id,
            rich_repr=updated_rich,
            compact_embedding=profile.compact_embedding,
            working_memory=profile.working_memory,
            episodic_memory=profile.episodic_memory,
            semantic_memory=profile.semantic_memory,
            autonomy_level=profile.autonomy_level,
            trust_score=profile.trust_score,
            created_at=profile.created_at,
            metadata=profile.metadata,
        )

        self._profiles[profile.user_id] = updated_profile
        logger.info(
            "Updated profile %s (%d interactions)",
            profile.user_id,
            len(new_history),
        )
        return updated_profile

    def compute_skill_level(
        self,
        profile: UserProfile,
        domain: str,
    ) -> SkillLevel:
        """
        Assess the user's skill level in a given domain.

        Uses interaction history, explicit skill tags, and
        outcome patterns to produce an estimated skill level.

        Args:
            profile: The user profile to assess.
            domain: The domain to assess (e.g., "python", "devops").

        Returns:
            Assessed SkillLevel for the domain.
        """
        explicit_level = profile.rich_repr.skill_levels.get(domain)
        if explicit_level is not None:
            return explicit_level

        domain_interactions = [
            i for i in profile.rich_repr.interaction_history
            if domain.lower() in i.content.lower()
        ]

        if not domain_interactions:
            logger.debug(
                "No domain interactions for %s in profile %s",
                domain,
                profile.user_id,
            )
            return SkillLevel.NOVICE

        recent = domain_interactions[-20:]
        positive_outcomes = sum(
            1 for i in recent
            if i.outcome and "success" in i.outcome.lower()
        )
        ratio = positive_outcomes / len(recent) if recent else 0.0

        if ratio >= 0.9:
            return SkillLevel.EXPERT
        if ratio >= 0.7:
            return SkillLevel.ADVANCED
        if ratio >= 0.5:
            return SkillLevel.INTERMEDIATE
        if ratio >= 0.3:
            return SkillLevel.BEGINNER
        return SkillLevel.NOVICE

    def extract_preferences(
        self,
        interactions: list[InteractionRecord],
    ) -> dict[str, Any]:
        """
        Infer user preferences from interaction history.

        Analyzes interaction content and outcomes to extract
        preference signals such as preferred tools, languages,
        frameworks, and work patterns.

        Args:
            interactions: List of interaction records to analyze.

        Returns:
            Dictionary of inferred preferences.
        """
        preferences: dict[str, Any] = {}
        if not interactions:
            return preferences

        content_strings = [i.content.lower() for i in interactions]
        tools_keywords = [
            "cli", "ide", "terminal", "gui", "web", "api"
        ]
        tool_mentions: Counter = Counter()
        for content in content_strings:
            for keyword in tools_keywords:
                if keyword in content:
                    tool_mentions[keyword] += 1

        if tool_mentions:
            preferences["preferred_tool_category"] = tool_mentions.most_common(1)[0][0]

        successful = [
            i for i in interactions
            if i.outcome and "success" in i.outcome.lower()
        ]
        if successful:
            quality_keywords = [
                "fast", "clear", "detailed", "concise", "thorough", "minimal"
            ]
            quality_mentions: Counter = Counter()
            for content in [s.content.lower() for s in successful]:
                for kw in quality_keywords:
                    if kw in content:
                        quality_mentions[kw] += 1
            if quality_mentions:
                preferences["preferred_quality"] = quality_mentions.most_common(1)[0][0]

        return preferences

    def detect_communication_style(
        self,
        interactions: list[InteractionRecord],
    ) -> CommunicationStyle:
        """
        Detect the user's communication style from interactions.

        Analyzes verbosity, formality, and technical language
        to classify communication into one of the predefined styles.

        Args:
            interactions: List of interaction records to analyze.

        Returns:
            Detected CommunicationStyle.
        """
        if not interactions:
            return CommunicationStyle.BALANCED

        total_words = sum(len(i.content.split()) for i in interactions)
        avg_length = total_words / len(interactions)

        tech_keywords = [
            "function", "class", "import", "def", "var", "const",
            "api", "endpoint", "schema", "type", "interface",
        ]
        tech_count = sum(
            1 for i in interactions
            for kw in tech_keywords
            if kw in i.content.lower()
        )
        tech_ratio = tech_count / len(interactions)

        educational_keywords = [
            "why", "how", "explain", "meaning", "purpose", "difference"
        ]
        educ_count = sum(
            1 for i in interactions
            for kw in educational_keywords
            if kw in i.content.lower()
        )

        if avg_length > 50 and tech_ratio > 0.3:
            return CommunicationStyle.VERBOSE
        if tech_ratio > 0.5:
            return CommunicationStyle.TECHNICAL
        if educ_count > len(interactions) * 0.3:
            return CommunicationStyle.EDUCATIONAL
        if avg_length < 15:
            return CommunicationStyle.CONCISE
        return CommunicationStyle.BALANCED

    def _rebuild_rich_repr(
        self,
        profile: UserProfile,
        history: list[InteractionRecord],
    ) -> RichRepresentation:
        """
        Rebuild the rich representation from profile data and new history.

        Args:
            profile: Existing user profile.
            history: Updated interaction history.

        Returns:
            Updated RichRepresentation.
        """
        inferred_style = self.detect_communication_style(history)
        inferred_prefs = self.extract_preferences(history)

        merged_preferences = dict(profile.rich_repr.preferences)
        merged_preferences.update(inferred_prefs)

        return RichRepresentation(
            user_id=profile.user_id,
            preferences=merged_preferences,
            skill_levels=dict(profile.rich_repr.skill_levels),
            communication_style=inferred_style,
            goals=list(profile.rich_repr.goals),
            interaction_history=history,
            conventions=list(profile.rich_repr.conventions),
            created_at=profile.rich_repr.created_at,
        )
