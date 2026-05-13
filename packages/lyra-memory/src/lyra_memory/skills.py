"""
Skills system for Lyra - Procedural memory as executable capabilities.

Implements 7-tuple skill formalism:
1. Name: Unique identifier
2. Applicability: When to use this skill
3. Policy: How to execute (code or workflow)
4. Termination: When it's done
5. Interface: Input/output schema
6. Verifier: Admission test
7. Lineage: Provenance graph
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json


class SkillType(str, Enum):
    """Type of skill."""
    CODE = "code"  # Executable Python code
    WORKFLOW = "workflow"  # Multi-step procedure
    TOOL = "tool"  # MCP server wrapper
    REASONING = "reasoning"  # Problem-solving strategy


class SkillStatus(str, Enum):
    """Skill verification status."""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class SkillLineage:
    """Provenance tracking for skills."""
    parent_id: Optional[str] = None
    created_from: str = "manual"  # "manual", "trajectory", "merge", "split"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    version: int = 1


@dataclass
class Skill:
    """
    A reusable capability with verification.

    7-tuple formalism:
    - name: Unique identifier
    - applicability: When to use
    - policy: How to execute
    - termination: When done
    - interface: I/O schema
    - verifier: Admission test
    - lineage: Provenance
    """

    name: str
    applicability: str  # Description of when to use
    policy: str  # Code or workflow description
    termination: str  # Completion criteria
    interface: Dict[str, Any]  # {"input": schema, "output": schema}
    type: SkillType = SkillType.CODE
    status: SkillStatus = SkillStatus.UNVERIFIED
    lineage: SkillLineage = field(default_factory=SkillLineage)

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None

    # Verification
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    safety_level: str = "safe"  # "safe", "medium", "high-risk"

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "applicability": self.applicability,
            "policy": self.policy,
            "termination": self.termination,
            "interface": self.interface,
            "type": self.type.value,
            "status": self.status.value,
            "lineage": {
                "parent_id": self.lineage.parent_id,
                "created_from": self.lineage.created_from,
                "created_at": self.lineage.created_at.isoformat(),
                "modified_at": self.lineage.modified_at.isoformat(),
                "version": self.lineage.version,
            },
            "description": self.description,
            "tags": self.tags,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "test_cases": self.test_cases,
            "safety_level": self.safety_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Create from dictionary."""
        lineage_data = data.get("lineage", {})
        lineage = SkillLineage(
            parent_id=lineage_data.get("parent_id"),
            created_from=lineage_data.get("created_from", "manual"),
            created_at=datetime.fromisoformat(lineage_data["created_at"]) if "created_at" in lineage_data else datetime.now(),
            modified_at=datetime.fromisoformat(lineage_data["modified_at"]) if "modified_at" in lineage_data else datetime.now(),
            version=lineage_data.get("version", 1),
        )

        return cls(
            name=data["name"],
            applicability=data["applicability"],
            policy=data["policy"],
            termination=data["termination"],
            interface=data["interface"],
            type=SkillType(data.get("type", "code")),
            status=SkillStatus(data.get("status", "unverified")),
            lineage=lineage,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            use_count=data.get("use_count", 0),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            test_cases=data.get("test_cases", []),
            safety_level=data.get("safety_level", "safe"),
        )


class SkillLibrary:
    """
    Library of verified skills with lifecycle management.

    Operations:
    - ADD: Create from trajectory
    - REFINE: Improve based on failure
    - MERGE: Combine redundant skills
    - SPLIT: Divide broad skill
    - PRUNE: Remove stale/unsafe
    - DISTILL: Compress trajectory
    - COMPOSE: Chain skills
    """

    def __init__(self, library_path: Path):
        """
        Initialize skill library.

        Args:
            library_path: Path to skills directory
        """
        self.library_path = library_path
        self.skills: Dict[str, Skill] = {}
        self._load()

    def add(self, skill: Skill, verify: bool = True) -> bool:
        """
        Add a skill to the library.

        Args:
            skill: Skill to add
            verify: Whether to verify before adding

        Returns:
            True if added successfully
        """
        if verify:
            if not self._verify_skill(skill):
                skill.status = SkillStatus.REJECTED
                return False

        skill.status = SkillStatus.VERIFIED
        self.skills[skill.name] = skill
        self._save()
        return True

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def search(self, query: str, limit: int = 10) -> List[Skill]:
        """
        Search for relevant skills.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching skills
        """
        query_lower = query.lower()
        scored = []

        for skill in self.skills.values():
            if skill.status != SkillStatus.VERIFIED:
                continue

            score = 0.0

            # Match name
            if query_lower in skill.name.lower():
                score += 3.0

            # Match tags
            for tag in skill.tags:
                if tag.lower() in query_lower:
                    score += 2.0

            # Match applicability
            if query_lower in skill.applicability.lower():
                score += 1.0

            # Weight by success rate
            score *= skill.success_rate

            if score > 0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in scored[:limit]]

    def refine(self, name: str, failure_info: Dict[str, Any]) -> Skill:
        """
        Refine a skill based on failure.

        Args:
            name: Skill name
            failure_info: Information about the failure

        Returns:
            Refined skill
        """
        skill = self.skills[name]

        # Increment version
        skill.lineage.version += 1
        skill.lineage.modified_at = datetime.now()

        # Add failure as test case
        skill.test_cases.append({
            "type": "failure",
            "input": failure_info.get("input"),
            "expected_error": failure_info.get("error"),
        })

        self._save()
        return skill

    def merge(self, skill1_name: str, skill2_name: str, new_name: str) -> Skill:
        """
        Merge two skills into one.

        Args:
            skill1_name: First skill
            skill2_name: Second skill
            new_name: Name for merged skill

        Returns:
            Merged skill
        """
        skill1 = self.skills[skill1_name]
        skill2 = self.skills[skill2_name]

        merged = Skill(
            name=new_name,
            applicability=f"{skill1.applicability} OR {skill2.applicability}",
            policy=f"{skill1.policy}\n\n{skill2.policy}",
            termination=skill1.termination,
            interface=skill1.interface,
            type=skill1.type,
            lineage=SkillLineage(
                parent_id=skill1_name,
                created_from="merge",
            ),
            tags=list(set(skill1.tags + skill2.tags)),
            test_cases=skill1.test_cases + skill2.test_cases,
        )

        self.add(merged, verify=False)
        return merged

    def prune(self, min_success_rate: float = 0.3, min_use_count: int = 5) -> List[str]:
        """
        Remove low-quality skills.

        Args:
            min_success_rate: Minimum success rate
            min_use_count: Minimum use count before pruning

        Returns:
            List of pruned skill names
        """
        pruned = []

        for name, skill in list(self.skills.items()):
            if skill.use_count >= min_use_count and skill.success_rate < min_success_rate:
                skill.status = SkillStatus.DEPRECATED
                pruned.append(name)

        self._save()
        return pruned

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        return {
            "total_skills": len(self.skills),
            "by_type": self._count_by_type(),
            "by_status": self._count_by_status(),
            "avg_success_rate": self._avg_success_rate(),
            "most_used": self._most_used(5),
        }

    def _verify_skill(self, skill: Skill) -> bool:
        """
        Verify a skill before admission.

        Checks:
        - Has required fields
        - Policy is not empty
        - Test cases exist (for code skills)
        - Safety level is appropriate
        """
        # Basic checks
        if not skill.name or not skill.policy:
            return False

        # Code skills need test cases
        if skill.type == SkillType.CODE and not skill.test_cases:
            return False

        # High-risk skills need explicit approval (simulated here)
        if skill.safety_level == "high-risk":
            return False  # Would require human review

        return True

    def _count_by_type(self) -> Dict[str, int]:
        """Count skills by type."""
        counts = {}
        for skill in self.skills.values():
            counts[skill.type.value] = counts.get(skill.type.value, 0) + 1
        return counts

    def _count_by_status(self) -> Dict[str, int]:
        """Count skills by status."""
        counts = {}
        for skill in self.skills.values():
            counts[skill.status.value] = counts.get(skill.status.value, 0) + 1
        return counts

    def _avg_success_rate(self) -> float:
        """Calculate average success rate."""
        if not self.skills:
            return 0.0
        return sum(s.success_rate for s in self.skills.values()) / len(self.skills)

    def _most_used(self, limit: int) -> List[Dict[str, Any]]:
        """Get most used skills."""
        sorted_skills = sorted(
            self.skills.values(),
            key=lambda s: s.use_count,
            reverse=True
        )[:limit]

        return [
            {
                "name": s.name,
                "use_count": s.use_count,
                "success_rate": s.success_rate,
            }
            for s in sorted_skills
        ]

    def _load(self) -> None:
        """Load skills from disk."""
        if not self.library_path.exists():
            return

        for skill_file in self.library_path.glob("*.json"):
            with open(skill_file) as f:
                data = json.load(f)
                skill = Skill.from_dict(data)
                self.skills[skill.name] = skill

    def _save(self) -> None:
        """Save skills to disk."""
        self.library_path.mkdir(parents=True, exist_ok=True)

        for skill in self.skills.values():
            skill_file = self.library_path / f"{skill.name}.json"
            with open(skill_file, "w") as f:
                json.dump(skill.to_dict(), f, indent=2)
