"""
Harness Tree — git-backed multi-branch evolution with solve-time routing.

Implements the Adaptive Auto-Harness architecture (arXiv 2606.01770):
instead of a single evolving harness that inevitably peaks and declines
on open-ended task streams, maintain a git-backed harness tree with
branch-per-task-regime and solve-time routing.

Key insight from the paper: loss = L_evo (evolution capacity) + L_adapt
(adaptation to current task) + HITL (human-in-the-loop for missing
external signal). A single harness optimizes L_adapt at the expense of
L_evo — the tree splits the difference by specializing branches.

Architecture
------------
Each branch in the harness tree contains:
- A full Lyra workspace (prompts, skills, memory config, router weights)
- Branch metadata: task regime, performance history, evolution lineage
- A parent pointer for inheritance

At solve time:
1. Classify incoming task into a regime
2. Route to the best-performing branch for that regime
3. If no branch matches, fork from the closest ancestor
4. Periodically merge improvements back to parent branches

References
----------
- Adaptive Auto-Harness (Liu et al., arXiv 2606.01770v1)
- Darwin Gödel Machine (arXiv 2505.22954v3)
- Meta-Harness (arXiv 2603.28052v1)
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskRegime(str, Enum):
    """Broad task categories for branch specialization."""

    CODING = "coding"
    RESEARCH = "research"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    WRITING = "writing"
    DEVOPS = "devops"
    REVIEW = "review"
    UNKNOWN = "unknown"


@dataclass
class BranchMetadata:
    """Metadata for a single branch in the harness tree.

    Attributes:
        branch_name: Git branch name (e.g. ``harness/coding-v3``).
        regime: Task regime this branch specializes in.
        parent: Parent branch name (for inheritance).
        created_at: Unix timestamp of branch creation.
        tasks_completed: Number of tasks processed on this branch.
        avg_score: Rolling average of task success scores (0-1).
        last_used: Unix timestamp of last solve-time routing to this branch.
        frozen: If True, branch is read-only (archived after peak).
    """

    branch_name: str
    regime: TaskRegime
    parent: str = "main"
    created_at: float = field(default_factory=time.time)
    tasks_completed: int = 0
    avg_score: float = 0.0
    last_used: float = field(default_factory=time.time)
    frozen: bool = False


@dataclass
class RoutingDecision:
    """Result of solve-time routing.

    Attributes:
        branch: Selected branch name.
        regime: Classified task regime.
        is_new_fork: Whether a new branch was forked.
        confidence: Routing confidence (0-1).
        reason: Human-readable explanation.
    """

    branch: str
    regime: TaskRegime
    is_new_fork: bool
    confidence: float
    reason: str


class HarnessTree:
    """Git-backed harness tree with regime-specialized branches.

    Usage::

        tree = HarnessTree(repo_root=Path("./lyra-workspace"))
        decision = tree.route("Debug the memory leak in the router module")
        tree.checkout(decision.branch)
        # ... agent does work on this branch ...
        tree.record_result(decision.branch, score=0.85)

        # Periodically: merge improvements back
        tree.propagate_improvements("harness/coding-v3")
    """

    # Branch naming convention
    BRANCH_PREFIX = "harness"

    # When to fork a new branch (confidence below this threshold)
    FORK_CONFIDENCE_THRESHOLD = 0.60

    # After how many tasks to consider freezing a peak branch
    FREEZE_AFTER_TASKS = 200

    def __init__(self, repo_root: Path) -> None:
        self._repo = repo_root
        self._metadata_file = repo_root / ".lyra" / "harness_tree.json"
        self._branches: dict[str, BranchMetadata] = {}
        self._load_metadata()

    # ------------------------------------------------------------------
    # Solve-time routing
    # ------------------------------------------------------------------

    def route(self, task_description: str) -> RoutingDecision:
        """Route a task to the best branch.

        Args:
            task_description: Natural language description of the task.

        Returns:
            RoutingDecision with selected branch.
        """
        regime = self._classify_regime(task_description)
        candidates = self._candidates_for_regime(regime)

        if not candidates:
            # No branch for this regime — fork from main
            branch = self._fork("main", regime)
            return RoutingDecision(
                branch=branch,
                regime=regime,
                is_new_fork=True,
                confidence=1.0,
                reason=f"No existing branch for {regime.value} regime — forked from main",
            )

        # Pick best candidate by avg_score
        best = max(candidates, key=lambda b: b.avg_score)

        if best.frozen:
            # Peak branch — fork a new one
            branch = self._fork(best.branch_name, regime)
            return RoutingDecision(
                branch=branch,
                regime=regime,
                is_new_fork=True,
                confidence=0.5,
                reason=f"Best branch {best.branch_name} is frozen (peaked) — forked new branch",
            )

        confidence = self._routing_confidence(best, regime, task_description)
        best.last_used = time.time()

        if confidence < self.FORK_CONFIDENCE_THRESHOLD:
            branch = self._fork(best.branch_name, regime)
            return RoutingDecision(
                branch=branch,
                regime=regime,
                is_new_fork=True,
                confidence=confidence,
                reason=f"Low confidence ({confidence:.2f}) on {best.branch_name} — forked",
            )

        return RoutingDecision(
            branch=best.branch_name,
            regime=regime,
            is_new_fork=False,
            confidence=confidence,
            reason=f"Routed to {best.branch_name} (avg_score={best.avg_score:.2f}, {best.tasks_completed} tasks)",
        )

    def record_result(
        self, branch_name: str, score: float, task_description: str = ""
    ) -> None:
        """Record a task result on a branch.

        Args:
            branch_name: The branch that handled the task.
            score: Success score (0-1).
            task_description: Optional task description for logging.
        """
        meta = self._branches.get(branch_name)
        if meta is None:
            return

        n = meta.tasks_completed
        meta.avg_score = (meta.avg_score * n + score) / (n + 1)
        meta.tasks_completed = n + 1
        meta.last_used = time.time()

        # Check if branch has peaked
        if meta.tasks_completed >= self.FREEZE_AFTER_TASKS:
            meta.frozen = True

        self._save_metadata()

    def propagate_improvements(self, branch_name: str) -> list[str]:
        """Merge a branch's improvements back to its parent lineage.

        Args:
            branch_name: The branch to propagate from.

        Returns:
            List of parent branches that received merges.
        """
        meta = self._branches.get(branch_name)
        if meta is None:
            return []

        merged = []
        current = meta.parent
        while current and current in self._branches:
            try:
                self._git("checkout", current)
                self._git("merge", "--no-edit", branch_name)
                merged.append(current)
            except subprocess.CalledProcessError:
                # Merge conflict — skip, human resolves later
                self._git("merge", "--abort")
                break
            current = self._branches[current].parent

        if merged:
            self._git("checkout", branch_name)

        return merged

    def checkout(self, branch_name: str) -> None:
        """Check out a harness branch for the agent to work on."""
        if branch_name not in self._branches:
            self._git("checkout", "-b", branch_name)
            return
        self._git("checkout", branch_name)

    def list_branches(self) -> list[BranchMetadata]:
        """List all harness branches with metadata."""
        return sorted(
            self._branches.values(),
            key=lambda b: (b.regime.value, -b.avg_score),
        )

    def get_branch(self, name: str) -> Optional[BranchMetadata]:
        """Get metadata for a specific branch."""
        return self._branches.get(name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _classify_regime(self, task: str) -> TaskRegime:
        """Classify a task into a regime based on keywords."""
        t = task.lower()

        # Order matters: check more specific patterns first
        if any(w in t for w in ("debug", "fix", "bug", "error", "crash", "traceback")):
            return TaskRegime.DEBUGGING
        if any(w in t for w in ("deploy", "ci", "cd", "pipeline", "docker", "infra", "server", "kubernetes")):
            return TaskRegime.DEVOPS
        if any(w in t for w in ("review", "pr", "pull request", "approve", "audit")):
            return TaskRegime.REVIEW
        if any(w in t for w in ("write", "document", "readme", "blog", "article", "docs", "documentation")):
            return TaskRegime.WRITING
        if any(w in t for w in ("research", "analyze", "investigate", "survey", "paper", "study")):
            return TaskRegime.RESEARCH
        if any(w in t for w in ("architecture", "design", "system", "pattern", "structure")):
            return TaskRegime.ARCHITECTURE
        if any(w in t for w in ("code", "implement", "build", "function", "class", "api", "refactor")):
            return TaskRegime.CODING

        return TaskRegime.UNKNOWN

    def _candidates_for_regime(self, regime: TaskRegime) -> list[BranchMetadata]:
        """Get all branches matching a regime, best first."""
        matches = [
            b for b in self._branches.values()
            if b.regime == regime and not b.frozen
        ]
        return sorted(matches, key=lambda b: -b.avg_score)

    def _routing_confidence(
        self,
        branch: BranchMetadata,
        regime: TaskRegime,
        task: str,
    ) -> float:
        """Estimate confidence that this branch will handle the task well."""
        # Base confidence from historical avg_score
        base = branch.avg_score if branch.tasks_completed > 5 else 0.5

        # Recency bonus: recently used branches get a boost
        hours_since = (time.time() - branch.last_used) / 3600
        recency = max(0.0, 1.0 - hours_since / 168)  # Decay over 1 week

        # Task count bonus: more experienced branches are more reliable
        experience = min(1.0, branch.tasks_completed / 50)

        return (base * 0.5 + recency * 0.2 + experience * 0.3)

    def _fork(self, parent: str, regime: TaskRegime) -> str:
        """Create a new branch forked from parent for the given regime."""
        suffix = _regime_suffix(regime)
        version = 1
        while True:
            name = f"{self.BRANCH_PREFIX}/{suffix}-v{version}"
            if name not in self._branches:
                break
            version += 1

        try:
            self._git("checkout", parent)
            self._git("checkout", "-b", name)
        except subprocess.CalledProcessError:
            # Best effort — if git fails, still track the branch
            pass

        meta = BranchMetadata(
            branch_name=name,
            regime=regime,
            parent=parent,
        )
        self._branches[name] = meta
        self._save_metadata()
        return name

    def _git(self, *args: str) -> None:
        """Run a git command in the repo root."""
        subprocess.run(
            ("git",) + args,
            cwd=str(self._repo),
            capture_output=True,
            check=True,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_metadata(self) -> None:
        """Load branch metadata from disk."""
        if not self._metadata_file.is_file():
            return
        with open(self._metadata_file, "r") as fh:
            data = json.load(fh)
        for item in data.get("branches", []):
            meta = BranchMetadata(
                branch_name=item["branch_name"],
                regime=TaskRegime(item["regime"]),
                parent=item.get("parent", "main"),
                created_at=item.get("created_at", 0),
                tasks_completed=item.get("tasks_completed", 0),
                avg_score=item.get("avg_score", 0.0),
                last_used=item.get("last_used", 0),
                frozen=item.get("frozen", False),
            )
            self._branches[meta.branch_name] = meta

    def _save_metadata(self) -> None:
        """Save branch metadata to disk."""
        self._metadata_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "branches": [
                {
                    "branch_name": b.branch_name,
                    "regime": b.regime.value,
                    "parent": b.parent,
                    "created_at": b.created_at,
                    "tasks_completed": b.tasks_completed,
                    "avg_score": round(b.avg_score, 4),
                    "last_used": b.last_used,
                    "frozen": b.frozen,
                }
                for b in self._branches.values()
            ],
        }
        with open(self._metadata_file, "w") as fh:
            json.dump(data, fh, indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _regime_suffix(regime: TaskRegime) -> str:
    """Short suffix for branch naming."""
    return {
        TaskRegime.CODING: "coding",
        TaskRegime.RESEARCH: "research",
        TaskRegime.DEBUGGING: "debug",
        TaskRegime.ARCHITECTURE: "arch",
        TaskRegime.WRITING: "writing",
        TaskRegime.DEVOPS: "devops",
        TaskRegime.REVIEW: "review",
        TaskRegime.UNKNOWN: "general",
    }[regime]
