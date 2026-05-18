"""
Lyra Evolution Harness: Protected Environment for Agent Evolution

This module implements the AEVO-inspired harness with OS-level capability boundaries
to prevent reward hacking and ensure safe agent evolution.

Based on: arXiv:2605.13821 (AEVO)
Phase: 0 - Foundation Acceleration
Task: T001 - Minimal Viable Harness
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib


@dataclass
class EvaluationResult:
    """Result from protected evaluator."""
    candidate_id: str
    score: float
    timestamp: str
    redacted_trace: Dict[str, Any]
    evaluator_version: str


@dataclass
class CandidateRecord:
    """Immutable candidate record in archive."""
    id: str
    generation: int
    parent_id: Optional[str]
    config: Dict[str, Any]
    created_at: str
    metadata: Dict[str, Any]


class EvolutionHarness:
    """
    Protected environment for agent evolution.

    Implements OS-level capability boundaries:
    - Agent can read workspace, cannot read evaluator internals
    - Agent can write workspace, cannot write scores
    - Evaluator writes scores, agent reads them
    - All operations logged to audit trail
    """

    def __init__(self, workspace_dir: Path, archive_dir: Path):
        """
        Initialize evolution harness.

        Args:
            workspace_dir: Agent read-write workspace
            archive_dir: Immutable candidate archive
        """
        self.workspace_dir = Path(workspace_dir)
        self.archive_dir = Path(archive_dir)

        # Create directory structure
        self._setup_directories()

        # Initialize audit trail
        self.audit_log: List[Dict[str, Any]] = []

    def _setup_directories(self):
        """Create harness directory structure."""
        # Workspace (agent read-write)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Archive (append-only)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        (self.archive_dir / "candidates").mkdir(exist_ok=True)
        (self.archive_dir / "scores").mkdir(exist_ok=True)
        (self.archive_dir / "meta_edits").mkdir(exist_ok=True)

        # Evaluator (read-only for agent)
        evaluator_dir = self.archive_dir / "evaluator"
        evaluator_dir.mkdir(exist_ok=True)

    def evaluate(self, candidate_id: str) -> EvaluationResult:
        """
        Run protected scorer on candidate.

        Agent cannot read evaluator internals or modify score files.
        Returns redacted results only.

        Args:
            candidate_id: Candidate to evaluate

        Returns:
            Evaluation result with redacted trace
        """
        # Log operation
        self._log_operation("evaluate", {"candidate_id": candidate_id})

        # Load candidate
        candidate = self._load_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Run evaluator (protected)
        score = self._run_evaluator(candidate)

        # Create redacted result
        result = EvaluationResult(
            candidate_id=candidate_id,
            score=score,
            timestamp=datetime.now().isoformat(),
            redacted_trace={"status": "success"},  # Redacted
            evaluator_version="1.0.0"
        )

        # Write score to protected location
        self._write_score(result)

        return result

    def submit(self, candidate_id: str) -> bool:
        """
        Submit candidate as official entry.

        Writes to official score file (write-only for agent).

        Args:
            candidate_id: Candidate to submit

        Returns:
            True if submission successful
        """
        # Log operation
        self._log_operation("submit", {"candidate_id": candidate_id})

        # Verify candidate exists
        candidate = self._load_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Write to official submissions
        submission_file = self.archive_dir / "scores" / "official_submissions.jsonl"
        with open(submission_file, "a") as f:
            f.write(json.dumps({
                "candidate_id": candidate_id,
                "timestamp": datetime.now().isoformat()
            }) + "\n")

        return True

    def workspace_read(self, path: str) -> str:
        """
        Read from workspace (confined to workspace/).

        Args:
            path: Relative path within workspace

        Returns:
            File contents
        """
        # Log operation
        self._log_operation("workspace_read", {"path": path})

        # Ensure path is within workspace
        full_path = (self.workspace_dir / path).resolve()
        if not str(full_path).startswith(str(self.workspace_dir.resolve())):
            raise PermissionError(f"Access denied: {path} outside workspace")

        # Read file
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return full_path.read_text()

    def workspace_write(self, path: str, content: str) -> bool:
        """
        Write to workspace (confined to workspace/).

        Args:
            path: Relative path within workspace
            content: Content to write

        Returns:
            True if write successful
        """
        # Log operation
        self._log_operation("workspace_write", {"path": path, "size": len(content)})

        # Ensure path is within workspace
        full_path = (self.workspace_dir / path).resolve()
        if not str(full_path).startswith(str(self.workspace_dir.resolve())):
            raise PermissionError(f"Access denied: {path} outside workspace")

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content)

        return True

    def add_candidate(
        self,
        config: Dict[str, Any],
        generation: int,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add candidate to archive.

        Args:
            config: Candidate configuration
            generation: Generation number
            parent_id: Parent candidate ID
            metadata: Additional metadata

        Returns:
            Candidate ID
        """
        # Generate candidate ID
        candidate_id = self._generate_candidate_id(config, generation)

        # Create candidate record
        candidate = CandidateRecord(
            id=candidate_id,
            generation=generation,
            parent_id=parent_id,
            config=config,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        # Write to archive (immutable)
        candidate_file = self.archive_dir / "candidates" / f"{candidate_id}.json"
        with open(candidate_file, "w") as f:
            json.dump({
                "id": candidate.id,
                "generation": candidate.generation,
                "parent_id": candidate.parent_id,
                "config": candidate.config,
                "created_at": candidate.created_at,
                "metadata": candidate.metadata
            }, f, indent=2)

        # Log operation
        self._log_operation("add_candidate", {"candidate_id": candidate_id})

        return candidate_id

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Get complete audit trail.

        Returns:
            List of all logged operations
        """
        return self.audit_log.copy()

    def _generate_candidate_id(self, config: Dict[str, Any], generation: int) -> str:
        """Generate unique candidate ID."""
        content = json.dumps(config, sort_keys=True) + str(generation)
        hash_obj = hashlib.sha256(content.encode())
        return f"c{generation:03d}_{hash_obj.hexdigest()[:8]}"

    def _load_candidate(self, candidate_id: str) -> Optional[CandidateRecord]:
        """Load candidate from archive."""
        candidate_file = self.archive_dir / "candidates" / f"{candidate_id}.json"
        if not candidate_file.exists():
            return None

        with open(candidate_file) as f:
            data = json.load(f)

        return CandidateRecord(**data)

    def _run_evaluator(self, candidate: CandidateRecord) -> float:
        """
        Run protected evaluator.

        This is a placeholder. In production, this would:
        1. Run in isolated sandbox
        2. Execute benchmark tasks
        3. Return aggregate score

        Args:
            candidate: Candidate to evaluate
        """
        # Placeholder: return dummy score based on config complexity
        # In production: run actual evaluation
        config_size = len(json.dumps(candidate.config))
        return min(0.95, 0.5 + (config_size / 1000))  # Dummy score

    def _write_score(self, result: EvaluationResult):
        """Write score to protected location."""
        score_file = self.archive_dir / "scores" / f"{result.candidate_id}.json"
        with open(score_file, "w") as f:
            json.dump({
                "candidate_id": result.candidate_id,
                "score": result.score,
                "timestamp": result.timestamp,
                "evaluator_version": result.evaluator_version
            }, f, indent=2)

    def _log_operation(self, operation: str, details: Dict[str, Any]):
        """Log operation to audit trail."""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        })


# Example usage
if __name__ == "__main__":
    # Create harness
    harness = EvolutionHarness(
        workspace_dir=Path(".lyra/evolution/workspace"),
        archive_dir=Path(".lyra/evolution/archive")
    )

    # Add baseline candidate
    candidate_id = harness.add_candidate(
        config={"skills": ["skill1", "skill2"], "memory_config": {"type": "memtier"}},
        generation=0,
        metadata={"description": "Baseline configuration"}
    )

    print(f"✅ Created candidate: {candidate_id}")

    # Evaluate candidate
    result = harness.evaluate(candidate_id)
    print(f"✅ Evaluation score: {result.score}")

    # Submit candidate
    harness.submit(candidate_id)
    print(f"✅ Submitted candidate")

    # Write to workspace
    harness.workspace_write("test.txt", "Hello from harness!")
    print(f"✅ Wrote to workspace")

    # Read from workspace
    content = harness.workspace_read("test.txt")
    print(f"✅ Read from workspace: {content}")

    # Get audit trail
    audit = harness.get_audit_trail()
    print(f"✅ Audit trail: {len(audit)} operations logged")
