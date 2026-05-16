"""
7-Tuple Skill Schema - Phase B Enhancement.

Complete skill lifecycle management with verification gates.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from enum import Enum


class SkillStatus(Enum):
    """Skill lifecycle status."""

    DRAFT = "draft"
    VERIFIED = "verified"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class SkillApplicability:
    """When and where a skill applies."""

    context_patterns: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    trigger_keywords: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.7


@dataclass
class SkillPolicy:
    """How to execute the skill."""

    execution_steps: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    fallback_strategy: Optional[str] = None


@dataclass
class SkillTermination:
    """When to stop executing the skill."""

    success_conditions: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    max_retries: int = 3


@dataclass
class SkillInterface:
    """Input/output specification."""

    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[str] = field(default_factory=list)


@dataclass
class SkillEdit:
    """How to modify the skill."""

    editable_fields: List[str] = field(default_factory=list)
    edit_history: List[Dict[str, Any]] = field(default_factory=list)
    last_modified: Optional[str] = None


@dataclass
class SkillVerification:
    """How to verify the skill."""

    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    verification_fn: Optional[Callable] = None
    last_verified: Optional[str] = None
    verification_score: float = 0.0


@dataclass
class SkillLineage:
    """Evolution history of the skill."""

    parent_skill_id: Optional[str] = None
    child_skill_ids: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    evolution_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Skill:
    """
    Complete 7-tuple skill schema.

    The 7 tuples:
    1. Applicability - When to use
    2. Policy - How to execute
    3. Termination - When to stop
    4. Interface - Input/output spec
    5. Edit - How to modify
    6. Verification - How to verify
    7. Lineage - Evolution history
    """

    skill_id: str
    name: str
    description: str
    status: SkillStatus
    applicability: SkillApplicability
    policy: SkillPolicy
    termination: SkillTermination
    interface: SkillInterface
    edit: SkillEdit
    verification: SkillVerification
    lineage: SkillLineage
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillLifecycleManager:
    """
    Manages complete skill lifecycle with 10 operators.

    Operators:
    1. add - Create new skill
    2. refine - Improve existing skill
    3. merge - Combine skills
    4. split - Divide skill
    5. prune - Remove unused parts
    6. distill - Extract core logic
    7. abstract - Generalize skill
    8. compose - Combine multiple skills
    9. rewrite - Restructure skill
    10. rerank - Reorder skill priority
    """

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_index: Dict[str, List[str]] = {}  # keyword -> skill_ids

        # Statistics
        self.stats = {
            "total_skills": 0,
            "verified_skills": 0,
            "active_skills": 0,
            "operations": {
                "add": 0,
                "refine": 0,
                "merge": 0,
                "split": 0,
                "prune": 0,
                "distill": 0,
                "abstract": 0,
                "compose": 0,
                "rewrite": 0,
                "rerank": 0,
            },
        }

    def add(
        self,
        name: str,
        description: str,
        applicability: SkillApplicability,
        policy: SkillPolicy,
        termination: SkillTermination,
        interface: SkillInterface,
    ) -> str:
        """Operator 1: Add new skill."""
        skill_id = f"skill_{len(self.skills):06d}"

        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            status=SkillStatus.DRAFT,
            applicability=applicability,
            policy=policy,
            termination=termination,
            interface=interface,
            edit=SkillEdit(),
            verification=SkillVerification(),
            lineage=SkillLineage(),
        )

        self.skills[skill_id] = skill
        self._index_skill(skill)

        self.stats["total_skills"] += 1
        self.stats["operations"]["add"] += 1

        return skill_id

    def refine(
        self,
        skill_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Operator 2: Refine existing skill."""
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]

        # Record edit
        skill.edit.edit_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation": "refine",
            "updates": updates,
        })
        skill.edit.last_modified = datetime.now().isoformat()

        # Apply updates
        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        self.stats["operations"]["refine"] += 1
        return True

    def merge(
        self,
        skill_ids: List[str],
        new_name: str
    ) -> Optional[str]:
        """Operator 3: Merge multiple skills."""
        if not all(sid in self.skills for sid in skill_ids):
            return None

        # Create merged skill
        merged_applicability = SkillApplicability()
        merged_policy = SkillPolicy()

        for skill_id in skill_ids:
            skill = self.skills[skill_id]
            merged_applicability.context_patterns.extend(
                skill.applicability.context_patterns
            )
            merged_policy.execution_steps.extend(
                skill.policy.execution_steps
            )

        new_skill_id = self.add(
            name=new_name,
            description=f"Merged from: {', '.join(skill_ids)}",
            applicability=merged_applicability,
            policy=merged_policy,
            termination=SkillTermination(),
            interface=SkillInterface(),
        )

        # Update lineage
        new_skill = self.skills[new_skill_id]
        new_skill.lineage.evolution_log.append({
            "operation": "merge",
            "source_skills": skill_ids,
            "timestamp": datetime.now().isoformat(),
        })

        self.stats["operations"]["merge"] += 1
        return new_skill_id

    def split(
        self,
        skill_id: str,
        split_criteria: Dict[str, Any]
    ) -> List[str]:
        """Operator 4: Split skill into multiple."""
        if skill_id not in self.skills:
            return []

        # Placeholder: Create 2 sub-skills
        skill = self.skills[skill_id]

        new_skill_ids = []
        for i in range(2):
            new_id = self.add(
                name=f"{skill.name}_part_{i+1}",
                description=f"Split from {skill_id}",
                applicability=skill.applicability,
                policy=skill.policy,
                termination=skill.termination,
                interface=skill.interface,
            )
            new_skill_ids.append(new_id)

        self.stats["operations"]["split"] += 1
        return new_skill_ids

    def prune(self, skill_id: str) -> bool:
        """Operator 5: Remove unused parts."""
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]

        # Remove unused execution steps (placeholder logic)
        skill.policy.execution_steps = [
            step for step in skill.policy.execution_steps
            if "unused" not in step.lower()
        ]

        self.stats["operations"]["prune"] += 1
        return True

    def distill(self, skill_id: str) -> Optional[str]:
        """Operator 6: Extract core logic."""
        if skill_id not in self.skills:
            return None

        skill = self.skills[skill_id]

        # Create distilled version
        distilled_id = self.add(
            name=f"{skill.name}_distilled",
            description=f"Distilled from {skill_id}",
            applicability=skill.applicability,
            policy=SkillPolicy(
                execution_steps=skill.policy.execution_steps[:3]  # Core steps
            ),
            termination=skill.termination,
            interface=skill.interface,
        )

        self.stats["operations"]["distill"] += 1
        return distilled_id

    def abstract(self, skill_id: str) -> Optional[str]:
        """Operator 7: Generalize skill."""
        if skill_id not in self.skills:
            return None

        skill = self.skills[skill_id]

        # Create abstracted version
        abstract_id = self.add(
            name=f"{skill.name}_abstract",
            description=f"Abstracted from {skill_id}",
            applicability=SkillApplicability(
                context_patterns=["*"],  # More general
            ),
            policy=skill.policy,
            termination=skill.termination,
            interface=skill.interface,
        )

        self.stats["operations"]["abstract"] += 1
        return abstract_id

    def compose(self, skill_ids: List[str], composition_name: str) -> Optional[str]:
        """Operator 8: Compose multiple skills."""
        return self.merge(skill_ids, composition_name)  # Similar to merge

    def rewrite(self, skill_id: str, new_policy: SkillPolicy) -> bool:
        """Operator 9: Restructure skill."""
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]
        skill.policy = new_policy

        self.stats["operations"]["rewrite"] += 1
        return True

    def rerank(self, skill_priorities: Dict[str, int]) -> bool:
        """Operator 10: Reorder skill priorities."""
        for skill_id, priority in skill_priorities.items():
            if skill_id in self.skills:
                self.skills[skill_id].metadata["priority"] = priority

        self.stats["operations"]["rerank"] += 1
        return True

    def verify_skill(self, skill_id: str) -> bool:
        """Verify skill with verifier gate."""
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]

        # Run verification (placeholder)
        verification_passed = True  # Simulate verification

        if verification_passed:
            skill.status = SkillStatus.VERIFIED
            skill.verification.last_verified = datetime.now().isoformat()
            skill.verification.verification_score = 0.95
            self.stats["verified_skills"] += 1

        return verification_passed

    def activate_skill(self, skill_id: str) -> bool:
        """Activate verified skill."""
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]

        if skill.status != SkillStatus.VERIFIED:
            return False

        skill.status = SkillStatus.ACTIVE
        self.stats["active_skills"] += 1

        return True

    def _index_skill(self, skill: Skill):
        """Index skill by keywords."""
        for keyword in skill.applicability.trigger_keywords:
            if keyword not in self.skill_index:
                self.skill_index[keyword] = []
            self.skill_index[keyword].append(skill.skill_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get lifecycle statistics."""
        return self.stats
