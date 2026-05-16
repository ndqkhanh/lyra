"""
Skill Library with Mandatory Verification and Evolution Tracking.

All skills must have verification tests. Tracks evolution and success rates.
Target: 80% reduction in repeated errors.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import json


@dataclass
class VerificationTest:
    """A verification test for a skill."""

    test_id: str
    description: str
    test_function: Optional[Callable] = None  # Actual test function
    expected_output: Optional[str] = None
    last_run: Optional[str] = None
    last_result: Optional[bool] = None


@dataclass
class SkillExecution:
    """Record of a skill execution."""

    execution_id: str
    timestamp: str
    input_context: Dict[str, Any]
    output: Any
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class Skill:
    """A reusable skill with verification tests."""

    skill_id: str
    name: str
    description: str
    category: str  # "code", "analysis", "debugging", etc.
    implementation: str  # Code or description of the skill
    verification_tests: List[VerificationTest] = field(default_factory=list)
    executions: List[SkillExecution] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None
    version: int = 1

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def add_execution(
        self,
        input_context: Dict[str, Any],
        output: Any,
        success: bool,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> str:
        """Record a skill execution."""
        execution = SkillExecution(
            execution_id=f"{self.skill_id}_exec_{len(self.executions):04d}",
            timestamp=datetime.now().isoformat(),
            input_context=input_context,
            output=output,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )

        self.executions.append(execution)

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.last_used = datetime.now().isoformat()

        return execution.execution_id

    def needs_improvement(self, threshold: float = 0.7) -> bool:
        """Check if skill needs improvement based on success rate."""
        if self.success_count + self.failure_count < 5:
            return False  # Not enough data

        return self.get_success_rate() < threshold


class SkillLibrary:
    """
    Skill library with mandatory verification and evolution tracking.

    Features:
    - All skills must have verification tests
    - Automatic evolution tracking
    - Success rate monitoring
    - Error pattern detection
    - Skill improvement suggestions
    """

    def __init__(self, data_dir: str = "./data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.skills: Dict[str, Skill] = {}

        # Error patterns for repeated error detection
        self.error_patterns: Dict[str, int] = {}

        # Statistics
        self.stats = {
            "total_skills": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "skills_improved": 0,
            "repeated_errors_prevented": 0,
        }

        self._load_state()

    def _load_state(self):
        """Load skill library from disk."""
        state_file = self.data_dir / "skill_library.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)

                # Load skills (without test functions)
                for skill_id, skill_data in data.get("skills", {}).items():
                    # Convert verification tests
                    tests = [
                        VerificationTest(
                            test_id=t["test_id"],
                            description=t["description"],
                            expected_output=t.get("expected_output"),
                            last_run=t.get("last_run"),
                            last_result=t.get("last_result"),
                        )
                        for t in skill_data.get("verification_tests", [])
                    ]

                    # Convert executions
                    executions = [
                        SkillExecution(**e)
                        for e in skill_data.get("executions", [])
                    ]

                    skill = Skill(
                        skill_id=skill_data["skill_id"],
                        name=skill_data["name"],
                        description=skill_data["description"],
                        category=skill_data["category"],
                        implementation=skill_data["implementation"],
                        verification_tests=tests,
                        executions=executions,
                        success_count=skill_data.get("success_count", 0),
                        failure_count=skill_data.get("failure_count", 0),
                        created_at=skill_data.get("created_at", datetime.now().isoformat()),
                        last_used=skill_data.get("last_used"),
                        version=skill_data.get("version", 1),
                    )

                    self.skills[skill_id] = skill

                # Load error patterns
                self.error_patterns = data.get("error_patterns", {})

                # Load stats
                self.stats = data.get("stats", self.stats)

    def _save_state(self):
        """Save skill library to disk."""
        data = {
            "skills": {
                skill_id: {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "implementation": s.implementation,
                    "verification_tests": [
                        {
                            "test_id": t.test_id,
                            "description": t.description,
                            "expected_output": t.expected_output,
                            "last_run": t.last_run,
                            "last_result": t.last_result,
                        }
                        for t in s.verification_tests
                    ],
                    "executions": [
                        {
                            "execution_id": e.execution_id,
                            "timestamp": e.timestamp,
                            "input_context": e.input_context,
                            "output": str(e.output),  # Convert to string for JSON
                            "success": e.success,
                            "error": e.error,
                            "duration_ms": e.duration_ms,
                        }
                        for e in s.executions
                    ],
                    "success_count": s.success_count,
                    "failure_count": s.failure_count,
                    "created_at": s.created_at,
                    "last_used": s.last_used,
                    "version": s.version,
                }
                for skill_id, s in self.skills.items()
            },
            "error_patterns": self.error_patterns,
            "stats": self.stats,
        }

        with open(self.data_dir / "skill_library.json", "w") as f:
            json.dump(data, f, indent=2)

    def add_skill(
        self,
        name: str,
        description: str,
        category: str,
        implementation: str,
        verification_tests: List[VerificationTest]
    ) -> str:
        """
        Add a new skill to the library.

        Args:
            name: Skill name
            description: Skill description
            category: Skill category
            implementation: Skill implementation
            verification_tests: Mandatory verification tests

        Returns:
            Skill ID
        """
        if not verification_tests:
            raise ValueError("Skills must have at least one verification test")

        skill = Skill(
            skill_id=f"skill_{len(self.skills):06d}",
            name=name,
            description=description,
            category=category,
            implementation=implementation,
            verification_tests=verification_tests,
        )

        self.skills[skill.skill_id] = skill
        self.stats["total_skills"] += 1

        self._save_state()

        return skill.skill_id

    def execute_skill(
        self,
        skill_id: str,
        input_context: Dict[str, Any]
    ) -> tuple[bool, Any, Optional[str]]:
        """
        Execute a skill and record the result.

        Args:
            skill_id: Skill to execute
            input_context: Input context

        Returns:
            (success, output, error)
        """
        if skill_id not in self.skills:
            return False, None, f"Skill {skill_id} not found"

        skill = self.skills[skill_id]

        # Check for repeated error patterns
        error_signature = f"{skill_id}_{str(input_context)}"
        if error_signature in self.error_patterns:
            self.stats["repeated_errors_prevented"] += 1
            return False, None, "Repeated error pattern detected - execution prevented"

        # Execute skill (placeholder - actual execution would happen here)
        # For now, we'll simulate execution
        success = True
        output = f"Executed {skill.name}"
        error = None

        # Record execution
        skill.add_execution(input_context, output, success, error)

        self.stats["total_executions"] += 1
        if success:
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1
            # Record error pattern
            self.error_patterns[error_signature] = self.error_patterns.get(error_signature, 0) + 1

        self._save_state()

        return success, output, error

    def improve_skill(self, skill_id: str, new_implementation: str) -> bool:
        """
        Improve a skill with a new implementation.

        Args:
            skill_id: Skill to improve
            new_implementation: New implementation

        Returns:
            Success status
        """
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]
        skill.implementation = new_implementation
        skill.version += 1

        self.stats["skills_improved"] += 1

        self._save_state()

        return True

    def get_skills_needing_improvement(self, threshold: float = 0.7) -> List[Skill]:
        """Get skills that need improvement based on success rate."""
        return [
            skill for skill in self.skills.values()
            if skill.needs_improvement(threshold)
        ]

    def get_error_reduction_rate(self) -> float:
        """
        Calculate error reduction rate.

        Measures how many repeated errors were prevented.
        """
        total_potential_errors = (
            self.stats["repeated_errors_prevented"] +
            self.stats["failed_executions"]
        )

        if total_potential_errors == 0:
            return 0.0

        return self.stats["repeated_errors_prevented"] / total_potential_errors

    def get_stats(self) -> Dict[str, Any]:
        """Get skill library statistics."""
        error_reduction = self.get_error_reduction_rate()

        return {
            **self.stats,
            "error_reduction_rate": error_reduction,
            "num_skills": len(self.skills),
            "num_error_patterns": len(self.error_patterns),
        }
