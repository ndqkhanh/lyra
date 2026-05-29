"""
Skill registry for managing and retrieving skills.
"""

import json
from pathlib import Path

from .skill import Skill, SkillCategory, SkillSearchResult


class SkillRegistry:
    """
    Registry for managing skills.

    Provides CRUD operations and search functionality for skills.
    """

    def __init__(self):
        """Initialize skill registry."""
        self.skills: dict[str, Skill] = {}
        self._category_index: dict[SkillCategory, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._language_index: dict[str, set[str]] = {}

    def register(self, skill: Skill) -> None:
        """
        Register a skill.

        Args:
            skill: Skill to register
        """
        self.skills[skill.name] = skill

        # Update category index
        if skill.category not in self._category_index:
            self._category_index[skill.category] = set()
        self._category_index[skill.category].add(skill.name)

        # Update tag index
        for tag in skill.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(skill.name)

        # Update language index
        if skill.language:
            if skill.language not in self._language_index:
                self._language_index[skill.language] = set()
            self._language_index[skill.language].add(skill.name)

    def unregister(self, skill_name: str) -> bool:
        """
        Unregister a skill.

        Args:
            skill_name: Name of skill to unregister

        Returns:
            True if skill was unregistered, False if not found
        """
        if skill_name not in self.skills:
            return False

        skill = self.skills[skill_name]

        # Remove from category index
        if skill.category in self._category_index:
            self._category_index[skill.category].discard(skill_name)

        # Remove from tag index
        for tag in skill.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(skill_name)

        # Remove from language index
        if skill.language and skill.language in self._language_index:
            self._language_index[skill.language].discard(skill_name)

        del self.skills[skill_name]
        return True

    def get(self, skill_name: str) -> Skill | None:
        """
        Get a skill by name.

        Args:
            skill_name: Name of skill

        Returns:
            Skill if found, None otherwise
        """
        return self.skills.get(skill_name)

    def find_by_trigger(self, text: str, limit: int = 10) -> list[SkillSearchResult]:
        """
        Find skills matching trigger patterns.

        Args:
            text: Text to match
            limit: Maximum number of results

        Returns:
            List of matching skills with scores
        """
        results = []
        for skill in self.skills.values():
            if skill.matches_trigger(text):
                # Calculate score based on number of matching patterns
                matches = sum(1 for p in skill.trigger_patterns if p.lower() in text.lower())
                score = matches / len(skill.trigger_patterns) if skill.trigger_patterns else 0
                results.append(SkillSearchResult(
                    skill=skill,
                    score=score,
                    match_reason=f"Matched {matches} trigger pattern(s)"
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def find_by_category(self, category: SkillCategory) -> list[Skill]:
        """
        Find skills by category.

        Args:
            category: Skill category

        Returns:
            List of skills in category
        """
        skill_names = self._category_index.get(category, set())
        return [self.skills[name] for name in skill_names]

    def find_by_tags(self, tags: set[str], match_all: bool = False) -> list[Skill]:
        """
        Find skills by tags.

        Args:
            tags: Tags to match
            match_all: If True, skill must match all tags. If False, any tag.

        Returns:
            List of matching skills
        """
        if not tags:
            return []

        if match_all:
            # Find skills that have all tags
            skill_sets = [self._tag_index.get(tag, set()) for tag in tags]
            if not skill_sets:
                return []
            matching_names = set.intersection(*skill_sets)
        else:
            # Find skills that have any tag
            matching_names = set()
            for tag in tags:
                matching_names.update(self._tag_index.get(tag, set()))

        return [self.skills[name] for name in matching_names]

    def find_by_language(self, language: str) -> list[Skill]:
        """
        Find skills by programming language.

        Args:
            language: Programming language

        Returns:
            List of skills for language
        """
        skill_names = self._language_index.get(language, set())
        return [self.skills[name] for name in skill_names]

    def search(
        self,
        query: str,
        category: SkillCategory | None = None,
        tags: set[str] | None = None,
        language: str | None = None,
        limit: int = 10,
    ) -> list[SkillSearchResult]:
        """
        Search for skills with multiple filters.

        Args:
            query: Search query (matches name, description, content)
            category: Filter by category
            tags: Filter by tags
            language: Filter by language
            limit: Maximum results

        Returns:
            List of matching skills with scores
        """
        candidates = list(self.skills.values())

        # Apply filters
        if category:
            candidates = [s for s in candidates if s.category == category]

        if tags:
            candidates = [s for s in candidates if s.matches_tags(tags)]

        if language:
            candidates = [s for s in candidates if s.language == language]

        # Score by query match
        results = []
        query_lower = query.lower()
        for skill in candidates:
            score = 0.0
            match_reasons = []

            # Name match (highest weight)
            if query_lower in skill.name.lower():
                score += 1.0
                match_reasons.append("name")

            # Description match
            if query_lower in skill.description.lower():
                score += 0.5
                match_reasons.append("description")

            # Content match (lowest weight)
            if query_lower in skill.content.lower():
                score += 0.2
                match_reasons.append("content")

            # Tag match
            if any(query_lower in tag.lower() for tag in skill.tags):
                score += 0.7
                match_reasons.append("tags")

            if score > 0:
                results.append(SkillSearchResult(
                    skill=skill,
                    score=score,
                    match_reason=f"Matched in: {', '.join(match_reasons)}"
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get_statistics(self) -> dict[str, any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_skills": len(self.skills),
            "by_category": {
                cat.value: len(names)
                for cat, names in self._category_index.items()
            },
            "by_language": {
                lang: len(names)
                for lang, names in self._language_index.items()
            },
            "total_tags": len(self._tag_index),
            "sources": {
                "lyra": sum(1 for s in self.skills.values() if s.source == "lyra"),
                "ecc": sum(1 for s in self.skills.values() if s.source == "ecc"),
            },
        }

    def save(self, path: Path) -> None:
        """
        Save registry to JSON file.

        Args:
            path: Path to save file
        """
        data = {
            "skills": [skill.to_dict() for skill in self.skills.values()],
            "version": "1.0.0",
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path) -> int:
        """
        Load registry from JSON file.

        Args:
            path: Path to load file

        Returns:
            Number of skills loaded
        """
        with open(path) as f:
            data = json.load(f)

        count = 0
        for skill_data in data.get("skills", []):
            skill = Skill.from_dict(skill_data)
            self.register(skill)
            count += 1

        return count

    def clear(self) -> None:
        """Clear all skills from registry."""
        self.skills.clear()
        self._category_index.clear()
        self._tag_index.clear()
        self._language_index.clear()
