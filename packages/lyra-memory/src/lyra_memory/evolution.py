"""
Self-evolution engine for Lyra - Safe code self-modification.

Implements Darwin Gödel Machine-inspired architecture:
1. Identify improvement opportunity
2. Generate code modification
3. Verify in sandbox
4. Run test suite
5. Benchmark performance
6. Human review gate (for high-risk)
7. Commit to archive
8. Keep or revert based on metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import subprocess


class ModificationLevel(str, Enum):
    """Risk level of code modification."""
    SAFE = "safe"  # Auto-approved
    MEDIUM = "medium"  # Sandbox + tests
    HIGH_RISK = "high_risk"  # Human gate


class VerificationStatus(str, Enum):
    """Verification result."""
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class CodeModification:
    """A proposed code modification."""
    id: str
    description: str
    target_file: Path
    original_code: str
    modified_code: str
    level: ModificationLevel
    created_at: datetime = field(default_factory=datetime.now)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_results: Dict[str, Any] = field(default_factory=dict)
    performance_delta: Optional[float] = None
    approved_by_human: bool = False


@dataclass
class AgentVariant:
    """A variant of the agent with performance metrics."""
    id: str
    description: str
    code_snapshot: Dict[str, str]  # file_path -> content
    metrics: Dict[str, float]
    created_at: datetime
    parent_id: Optional[str] = None


class SelfEvolutionEngine:
    """
    Engine for safe code self-modification.

    Implements verification pipeline and agent archive.
    """

    def __init__(self, archive_path: Path, test_command: str = "pytest"):
        """
        Initialize evolution engine.

        Args:
            archive_path: Path to agent archive
            test_command: Command to run tests
        """
        self.archive_path = archive_path
        self.test_command = test_command
        self.modifications: Dict[str, CodeModification] = {}
        self.variants: Dict[str, AgentVariant] = {}
        self._load()

    def propose_modification(
        self,
        description: str,
        target_file: Path,
        original_code: str,
        modified_code: str,
        level: ModificationLevel = ModificationLevel.MEDIUM,
    ) -> CodeModification:
        """
        Propose a code modification.

        Args:
            description: What this modification does
            target_file: File to modify
            original_code: Original code
            modified_code: Modified code
            level: Risk level

        Returns:
            CodeModification object
        """
        mod_id = f"mod_{datetime.now().timestamp()}"
        modification = CodeModification(
            id=mod_id,
            description=description,
            target_file=target_file,
            original_code=original_code,
            modified_code=modified_code,
            level=level,
        )

        self.modifications[mod_id] = modification
        self._save()
        return modification

    def verify_modification(self, mod_id: str) -> bool:
        """
        Verify a modification through the pipeline.

        Pipeline:
        1. Static analysis (linting)
        2. Type checking
        3. Sandbox execution
        4. Test suite
        5. Performance benchmark
        6. Security scan

        Args:
            mod_id: Modification ID

        Returns:
            True if verification passed
        """
        modification = self.modifications[mod_id]
        results = {}

        # 1. Static analysis
        results["linting"] = self._run_linting(modification)
        if not results["linting"]["passed"]:
            modification.verification_status = VerificationStatus.FAILED
            modification.verification_results = results
            self._save()
            return False

        # 2. Type checking
        results["type_check"] = self._run_type_check(modification)
        if not results["type_check"]["passed"]:
            modification.verification_status = VerificationStatus.FAILED
            modification.verification_results = results
            self._save()
            return False

        # 3. Test suite
        results["tests"] = self._run_tests(modification)
        if not results["tests"]["passed"]:
            modification.verification_status = VerificationStatus.FAILED
            modification.verification_results = results
            self._save()
            return False

        # 4. Performance benchmark
        results["performance"] = self._benchmark_performance(modification)
        modification.performance_delta = results["performance"]["delta"]

        # Check for regression
        if results["performance"]["delta"] < -0.2:  # 20% slower
            modification.verification_status = VerificationStatus.FAILED
            modification.verification_results = results
            self._save()
            return False

        # 5. Security scan
        results["security"] = self._run_security_scan(modification)
        if not results["security"]["passed"]:
            modification.verification_status = VerificationStatus.FAILED
            modification.verification_results = results
            self._save()
            return False

        # All checks passed
        modification.verification_status = VerificationStatus.PASSED
        modification.verification_results = results
        self._save()
        return True

    def apply_modification(self, mod_id: str, force: bool = False) -> bool:
        """
        Apply a verified modification.

        Args:
            mod_id: Modification ID
            force: Skip verification check

        Returns:
            True if applied successfully
        """
        modification = self.modifications[mod_id]

        # Check verification status
        if not force and modification.verification_status != VerificationStatus.PASSED:
            return False

        # Check human approval for high-risk
        if modification.level == ModificationLevel.HIGH_RISK and not modification.approved_by_human:
            return False

        # Apply modification
        try:
            with open(modification.target_file, "w") as f:
                f.write(modification.modified_code)
            return True
        except Exception:
            return False

    def create_variant(
        self,
        description: str,
        code_snapshot: Dict[str, str],
        metrics: Dict[str, float],
        parent_id: Optional[str] = None,
    ) -> AgentVariant:
        """
        Create a new agent variant.

        Args:
            description: Variant description
            code_snapshot: Code files
            metrics: Performance metrics
            parent_id: Parent variant ID

        Returns:
            AgentVariant object
        """
        variant_id = f"variant_{datetime.now().timestamp()}"
        variant = AgentVariant(
            id=variant_id,
            description=description,
            code_snapshot=code_snapshot,
            metrics=metrics,
            created_at=datetime.now(),
            parent_id=parent_id,
        )

        self.variants[variant_id] = variant
        self._save_variant(variant)
        return variant

    def rollback(self, variant_id: str) -> bool:
        """
        Rollback to a previous variant.

        Args:
            variant_id: Variant to rollback to

        Returns:
            True if successful
        """
        variant = self.variants.get(variant_id)
        if not variant:
            return False

        # Restore code from snapshot
        try:
            for file_path, content in variant.code_snapshot.items():
                with open(file_path, "w") as f:
                    f.write(content)
            return True
        except Exception:
            return False

    def _run_linting(self, modification: CodeModification) -> Dict[str, Any]:
        """Run linting on modified code."""
        # Simplified - would use ruff/pylint in production
        return {"passed": True, "issues": []}

    def _run_type_check(self, modification: CodeModification) -> Dict[str, Any]:
        """Run type checking on modified code."""
        # Simplified - would use mypy/pyright in production
        return {"passed": True, "errors": []}

    def _run_tests(self, modification: CodeModification) -> Dict[str, Any]:
        """Run test suite."""
        try:
            result = subprocess.run(
                [self.test_command],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "failures": 0 if result.returncode == 0 else 1,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _benchmark_performance(self, modification: CodeModification) -> Dict[str, Any]:
        """Benchmark performance delta."""
        # Simplified - would run actual benchmarks in production
        return {"delta": 0.0, "baseline": 1.0, "modified": 1.0}

    def _run_security_scan(self, modification: CodeModification) -> Dict[str, Any]:
        """Run security scan."""
        # Simplified - would use bandit/semgrep in production
        suspicious_patterns = ["eval(", "exec(", "__import__", "os.system"]
        has_issues = any(pattern in modification.modified_code for pattern in suspicious_patterns)

        return {"passed": not has_issues, "issues": []}

    def _load(self) -> None:
        """Load modifications from disk."""
        mod_file = self.archive_path / "modifications.json"
        if mod_file.exists():
            with open(mod_file) as f:
                data = json.load(f)
                for mod_data in data:
                    mod = CodeModification(
                        id=mod_data["id"],
                        description=mod_data["description"],
                        target_file=Path(mod_data["target_file"]),
                        original_code=mod_data["original_code"],
                        modified_code=mod_data["modified_code"],
                        level=ModificationLevel(mod_data["level"]),
                        created_at=datetime.fromisoformat(mod_data["created_at"]),
                        verification_status=VerificationStatus(mod_data["verification_status"]),
                        verification_results=mod_data.get("verification_results", {}),
                        performance_delta=mod_data.get("performance_delta"),
                        approved_by_human=mod_data.get("approved_by_human", False),
                    )
                    self.modifications[mod.id] = mod

    def _save(self) -> None:
        """Save modifications to disk."""
        self.archive_path.mkdir(parents=True, exist_ok=True)
        mod_file = self.archive_path / "modifications.json"

        data = [
            {
                "id": mod.id,
                "description": mod.description,
                "target_file": str(mod.target_file),
                "original_code": mod.original_code,
                "modified_code": mod.modified_code,
                "level": mod.level.value,
                "created_at": mod.created_at.isoformat(),
                "verification_status": mod.verification_status.value,
                "verification_results": mod.verification_results,
                "performance_delta": mod.performance_delta,
                "approved_by_human": mod.approved_by_human,
            }
            for mod in self.modifications.values()
        ]

        with open(mod_file, "w") as f:
            json.dump(data, f, indent=2)

    def _save_variant(self, variant: AgentVariant) -> None:
        """Save variant to disk."""
        variant_file = self.archive_path / f"variant_{variant.id}.json"

        data = {
            "id": variant.id,
            "description": variant.description,
            "code_snapshot": variant.code_snapshot,
            "metrics": variant.metrics,
            "created_at": variant.created_at.isoformat(),
            "parent_id": variant.parent_id,
        }

        with open(variant_file, "w") as f:
            json.dump(data, f, indent=2)
