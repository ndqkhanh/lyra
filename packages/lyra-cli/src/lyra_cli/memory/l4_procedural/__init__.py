"""
L4: Procedural Memory Layer - Reusable skills and workflows with verification.

This layer stores executable skills that can be reused across sessions.
Each skill must have a verifier test to ensure correctness.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


@dataclass
class ProceduralSkill:
    """A reusable skill with verification."""

    skill_id: str
    skill_name: str
    code: str
    interface: Dict[str, Any]  # Input/output schema
    verifier_test: str  # Test code that verifies the skill
    success_rate: float = 0.0
    cost: float = 0.0  # Average cost in USD
    latency: float = 0.0  # Average latency in seconds
    last_used: Optional[str] = None
    usage_count: int = 0
    lineage: Optional[str] = None  # Parent skill ID
    evolution_round: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "code": self.code,
            "interface": self.interface,
            "verifier_test": self.verifier_test,
            "success_rate": self.success_rate,
            "cost": self.cost,
            "latency": self.latency,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
            "lineage": self.lineage,
            "evolution_round": self.evolution_round,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProceduralSkill":
        """Create from dictionary."""
        return cls(**data)


class ProceduralMemoryStore:
    """Storage for procedural skills."""

    def __init__(self, data_dir: str = "./data/l4_procedural"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skills_file = self.data_dir / "skills.json"
        self._load_skills()

    def _load_skills(self):
        """Load skills from disk."""
        if self.skills_file.exists():
            with open(self.skills_file, "r") as f:
                data = json.load(f)
                self.skills = {
                    skill_id: ProceduralSkill.from_dict(skill_data)
                    for skill_id, skill_data in data.items()
                }
        else:
            self.skills = {}

    def _save_skills(self):
        """Save skills to disk."""
        data = {
            skill_id: skill.to_dict()
            for skill_id, skill in self.skills.items()
        }
        with open(self.skills_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_skill(self, skill: ProceduralSkill) -> str:
        """Add a new skill."""
        self.skills[skill.skill_id] = skill
        self._save_skills()
        return skill.skill_id

    def get_skill(self, skill_id: str) -> Optional[ProceduralSkill]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)

    def update_skill(self, skill_id: str, **updates):
        """Update skill metrics."""
        if skill_id in self.skills:
            skill = self.skills[skill_id]
            for key, value in updates.items():
                if hasattr(skill, key):
                    setattr(skill, key, value)
            self._save_skills()

    def search_skills(
        self,
        query: str,
        min_success_rate: float = 0.0,
        limit: int = 10
    ) -> List[ProceduralSkill]:
        """Search skills by name or description."""
        results = []
        query_lower = query.lower()

        for skill in self.skills.values():
            if skill.success_rate < min_success_rate:
                continue

            if (query_lower in skill.skill_name.lower() or
                query_lower in skill.code.lower()):
                results.append(skill)

        # Sort by success rate and usage
        results.sort(
            key=lambda s: (s.success_rate, s.usage_count),
            reverse=True
        )

        return results[:limit]

    def get_top_skills(self, limit: int = 10) -> List[ProceduralSkill]:
        """Get top skills by success rate and usage."""
        skills = list(self.skills.values())
        skills.sort(
            key=lambda s: (s.success_rate, s.usage_count),
            reverse=True
        )
        return skills[:limit]

    def record_usage(self, skill_id: str, success: bool, cost: float, latency: float):
        """Record skill usage and update metrics."""
        if skill_id not in self.skills:
            return

        skill = self.skills[skill_id]

        # Update success rate (exponential moving average)
        alpha = 0.1
        skill.success_rate = (
            alpha * (1.0 if success else 0.0) +
            (1 - alpha) * skill.success_rate
        )

        # Update cost and latency (exponential moving average)
        skill.cost = alpha * cost + (1 - alpha) * skill.cost
        skill.latency = alpha * latency + (1 - alpha) * skill.latency

        # Update usage stats
        skill.usage_count += 1
        skill.last_used = datetime.now().isoformat()

        self._save_skills()
