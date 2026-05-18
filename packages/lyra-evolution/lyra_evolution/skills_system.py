"""
Lyra Skills System: 7-Tuple Skill Formalism

Implements verifiable, reusable skills with admission gates.

Based on: Skills research (doc 320)
Phase: 0 - Foundation Acceleration
Task: T003 - Skills Foundation
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Literal
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib


@dataclass
class SkillLineage:
    """Skill provenance and evolution history."""
    created_from: Optional[str] = None  # Parent skill ID
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1
    modifications: List[str] = field(default_factory=list)


@dataclass
class Skill:
    """
    7-tuple skill formalism.

    Components:
    1. name: Skill identifier
    2. applicability: When to use this skill
    3. policy: How to execute (code or description)
    4. termination: When it's done
    5. interface: Input/output schema
    6. verifier: Admission test
    7. lineage: Provenance graph
    """
    name: str
    applicability: str
    policy: str  # Code or description
    termination: str  # Completion condition
    interface: Dict[str, Any]  # {"inputs": [...], "outputs": [...]}
    verifier: Optional[str] = None  # Verification code
    lineage: SkillLineage = field(default_factory=SkillLineage)
    metadata: Dict[str, Any] = field(default_factory=dict)
    skill_type: Literal["code", "workflow", "tool", "reasoning"] = "code"
    risk_level: Literal["low", "medium", "high"] = "low"
    verified: bool = False


class SkillRegistry:
    """
    Skill registry with verifier-gated admission.

    Features:
    - Skill storage and retrieval
    - Verifier-gated admission
    - Skill lifecycle operations
    - Lineage tracking
    """

    def __init__(self, skills_dir: Path):
        """
        Initialize skill registry.

        Args:
            skills_dir: Directory for skill storage
        """
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self.skills: Dict[str, Skill] = {}

        # Load existing skills
        self._load_skills()

    def _load_skills(self):
        """Load skills from disk."""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file) as f:
                    data = json.load(f)
                    skill = self._deserialize_skill(data)
                    self.skills[skill.name] = skill
            except Exception as e:
                print(f"Warning: Failed to load {skill_file}: {e}")

    def add_skill(self, skill: Skill, verify: bool = True) -> bool:
        """
        Add skill to registry with optional verification.

        Args:
            skill: Skill to add
            verify: Whether to run verifier

        Returns:
            True if skill admitted
        """
        # Run verifier if requested
        if verify and skill.verifier:
            if not self._run_verifier(skill):
                return False

        # Mark as verified
        skill.verified = verify

        # Add to registry
        self.skills[skill.name] = skill

        # Persist to disk
        self._save_skill(skill)

        return True

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        Retrieve skill by name.

        Args:
            name: Skill name

        Returns:
            Skill or None
        """
        return self.skills.get(name)

    def search_skills(
        self,
        query: Optional[str] = None,
        skill_type: Optional[str] = None,
        verified_only: bool = False
    ) -> List[Skill]:
        """
        Search skills with filters.

        Args:
            query: Text query (matches name or applicability)
            skill_type: Filter by type
            verified_only: Only return verified skills

        Returns:
            List of matching skills
        """
        results = []

        for skill in self.skills.values():
            # Filter by verification
            if verified_only and not skill.verified:
                continue

            # Filter by type
            if skill_type and skill.skill_type != skill_type:
                continue

            # Filter by query
            if query:
                if query.lower() not in skill.name.lower() and \
                   query.lower() not in skill.applicability.lower():
                    continue

            results.append(skill)

        return results

    def update_skill(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update skill fields.

        Args:
            name: Skill name
            updates: Fields to update

        Returns:
            True if updated
        """
        skill = self.skills.get(name)
        if not skill:
            return False

        # Update fields
        for field, value in updates.items():
            if hasattr(skill, field):
                setattr(skill, field, value)

        # Update lineage
        skill.lineage.modified_at = datetime.now().isoformat()
        skill.lineage.version += 1
        skill.lineage.modifications.append(
            f"Updated {', '.join(updates.keys())} at {skill.lineage.modified_at}"
        )

        # Re-verify if policy changed
        if "policy" in updates and skill.verifier:
            skill.verified = self._run_verifier(skill)

        # Persist
        self._save_skill(skill)

        return True

    def delete_skill(self, name: str) -> bool:
        """
        Delete skill from registry.

        Args:
            name: Skill name

        Returns:
            True if deleted
        """
        if name not in self.skills:
            return False

        # Remove from memory
        del self.skills[name]

        # Remove from disk
        skill_file = self.skills_dir / f"{self._sanitize_name(name)}.json"
        if skill_file.exists():
            skill_file.unlink()

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.skills)
        by_type = {}
        by_risk = {}
        verified_count = 0

        for skill in self.skills.values():
            # Count by type
            by_type[skill.skill_type] = by_type.get(skill.skill_type, 0) + 1

            # Count by risk
            by_risk[skill.risk_level] = by_risk.get(skill.risk_level, 0) + 1

            # Count verified
            if skill.verified:
                verified_count += 1

        return {
            "total": total,
            "verified": verified_count,
            "unverified": total - verified_count,
            "by_type": by_type,
            "by_risk": by_risk
        }

    def _run_verifier(self, skill: Skill) -> bool:
        """
        Run skill verifier.

        Args:
            skill: Skill to verify

        Returns:
            True if verification passes
        """
        # Placeholder: In production, this would:
        # 1. Run static analysis
        # 2. Execute unit tests
        # 3. Run in sandbox
        # 4. Check security constraints

        # For now, simple checks
        if not skill.name or not skill.policy:
            return False

        if skill.risk_level == "high":
            # High-risk skills need explicit verification code
            if not skill.verifier:
                return False

        return True

    def _save_skill(self, skill: Skill):
        """Save skill to disk."""
        skill_file = self.skills_dir / f"{self._sanitize_name(skill.name)}.json"
        with open(skill_file, "w") as f:
            json.dump(self._serialize_skill(skill), f, indent=2)

    def _serialize_skill(self, skill: Skill) -> Dict[str, Any]:
        """Serialize skill to dict."""
        return {
            "name": skill.name,
            "applicability": skill.applicability,
            "policy": skill.policy,
            "termination": skill.termination,
            "interface": skill.interface,
            "verifier": skill.verifier,
            "lineage": {
                "created_from": skill.lineage.created_from,
                "created_at": skill.lineage.created_at,
                "modified_at": skill.lineage.modified_at,
                "version": skill.lineage.version,
                "modifications": skill.lineage.modifications
            },
            "metadata": skill.metadata,
            "skill_type": skill.skill_type,
            "risk_level": skill.risk_level,
            "verified": skill.verified
        }

    def _deserialize_skill(self, data: Dict[str, Any]) -> Skill:
        """Deserialize skill from dict."""
        lineage = SkillLineage(
            created_from=data["lineage"].get("created_from"),
            created_at=data["lineage"]["created_at"],
            modified_at=data["lineage"]["modified_at"],
            version=data["lineage"]["version"],
            modifications=data["lineage"]["modifications"]
        )

        return Skill(
            name=data["name"],
            applicability=data["applicability"],
            policy=data["policy"],
            termination=data["termination"],
            interface=data["interface"],
            verifier=data.get("verifier"),
            lineage=lineage,
            metadata=data.get("metadata", {}),
            skill_type=data.get("skill_type", "code"),
            risk_level=data.get("risk_level", "low"),
            verified=data.get("verified", False)
        )

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize skill name for filename."""
        return name.replace(" ", "_").replace("/", "_").lower()


# Example usage
if __name__ == "__main__":
    # Create skill registry
    registry = SkillRegistry(skills_dir=Path(".lyra/skills"))

    # Create a code skill
    skill = Skill(
        name="parallel_exploration",
        applicability="When exploring multiple agent variants simultaneously",
        policy="""
def explore_parallel(variants, n_workers=10):
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(evaluate, v) for v in variants]
        return [f.result() for f in futures]
        """,
        termination="All variants evaluated",
        interface={
            "inputs": ["variants: List[AgentConfig]", "n_workers: int"],
            "outputs": ["results: List[EvaluationResult]"]
        },
        verifier="assert len(variants) > 0",
        skill_type="code",
        risk_level="low"
    )

    # Add skill with verification
    admitted = registry.add_skill(skill, verify=True)
    print(f"✅ Skill admitted: {admitted}")

    # Create a workflow skill
    workflow = Skill(
        name="ablation_study",
        applicability="When validating harness effectiveness",
        policy="""
1. Run 10 experiments with harness enabled
2. Run 10 experiments with harness disabled
3. Compare reward-hacking attempts
4. Document results
        """,
        termination="All experiments complete and documented",
        interface={
            "inputs": ["harness_config: Dict", "num_runs: int"],
            "outputs": ["report: AblationReport"]
        },
        skill_type="workflow",
        risk_level="low"
    )

    registry.add_skill(workflow, verify=True)
    print(f"✅ Workflow skill added: {workflow.name}")

    # Search skills
    code_skills = registry.search_skills(skill_type="code", verified_only=True)
    print(f"✅ Found {len(code_skills)} verified code skills")

    # Get statistics
    stats = registry.get_statistics()
    print(f"✅ Registry statistics:")
    print(f"   Total: {stats['total']}")
    print(f"   Verified: {stats['verified']}")
    print(f"   By type: {stats['by_type']}")
