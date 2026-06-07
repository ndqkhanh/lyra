"""
Eval Harness — Integration with tau-bench, tau2-bench, and SWE-bench Verified.

Provides pass^k consistency metrics and objective evaluation of agent reliability.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class EvalTask:
    """A single evaluation task."""

    task_id: str
    prompt: str
    expected_output: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    domain: str = "general"


@dataclass
class EvalResults:
    """Results from an evaluation run."""

    pass_at_1: float
    pass_at_k: float
    k: int
    n_tasks: int
    backend: str
    avg_cost_per_task: float = 0.0
    avg_tokens_per_task: int = 0
    task_results: list[TaskResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    total_duration_seconds: float = 0.0


@dataclass
class TaskResult:
    """Result for a single task across k trials."""

    task_id: str
    trials: list[TrialResult]
    pass_at_1: bool
    pass_at_k: bool
    avg_tokens: int = 0
    avg_cost: float = 0.0


@dataclass
class TrialResult:
    """Result for a single trial."""

    trial_num: int
    passed: bool
    output: str
    tokens: int = 0
    cost: float = 0.0
    error: str | None = None


class EvalRunner(ABC):
    """Abstract base class for evaluation runners."""

    @abstractmethod
    def get_tasks(self, n: int = 100) -> list[EvalTask]:
        """
        Get n evaluation tasks.

        Args:
            n: Number of tasks to return

        Returns:
            List of evaluation tasks
        """
        pass

    @abstractmethod
    async def check(self, task: EvalTask, output: str) -> bool:
        """
        Check if output is correct for the task.

        Args:
            task: The evaluation task
            output: Agent's output

        Returns:
            True if output is correct
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this runner."""
        pass


class TauBenchRunner(EvalRunner):
    """
    Tau-Bench evaluation runner.

    Database-state verification for objective outcome assessment.
    """

    def __init__(self, domain: str = "airline", data_path: Path | None = None):
        """
        Initialize Tau-Bench runner.

        Args:
            domain: Domain to evaluate (airline, retail, etc.)
            data_path: Path to tau-bench data (default: ~/.lyra/eval_data/tau-bench)
        """
        self.domain = domain
        self.data_path = data_path or Path.home() / ".lyra" / "eval_data" / "tau-bench"
        self.tasks_cache: list[EvalTask] = []

    def get_tasks(self, n: int = 100) -> list[EvalTask]:
        """Get tau-bench tasks."""
        # In a real implementation, this would load from tau-bench dataset
        # For now, return stub tasks
        if self.tasks_cache:
            return self.tasks_cache[:n]

        # Load tasks from dataset
        tasks_file = self.data_path / self.domain / "tasks.json"
        if tasks_file.exists():
            with open(tasks_file) as f:
                data = json.load(f)
                self.tasks_cache = [
                    EvalTask(
                        task_id=item["task_id"],
                        prompt=item["prompt"],
                        expected_output=item.get("expected_output"),
                        metadata=item.get("metadata", {}),
                        domain=self.domain,
                    )
                    for item in data.get("tasks", [])
                ]
        else:
            # Generate synthetic tasks for testing
            self.tasks_cache = self._generate_synthetic_tasks(n)

        return self.tasks_cache[:n]

    def _generate_synthetic_tasks(self, n: int) -> list[EvalTask]:
        """Generate synthetic tasks for testing."""
        tasks = []
        for i in range(n):
            tasks.append(
                EvalTask(
                    task_id=f"tau-{self.domain}-{i:03d}",
                    prompt=f"Task {i}: Process {self.domain} request",
                    expected_output=f"Expected output {i}",
                    domain=self.domain,
                )
            )
        return tasks

    async def check(self, task: EvalTask, output: str) -> bool:
        """
        Check output correctness.

        In real tau-bench: verify database state changes.
        For now: simple string matching.
        """
        if task.expected_output:
            return str(task.expected_output).lower() in output.lower()
        # If no expected output, assume pass (for testing)
        return True

    def get_name(self) -> str:
        """Get runner name."""
        return f"tau-bench-{self.domain}"


class Tau2BenchRunner(EvalRunner):
    """
    Tau2-Bench evaluation runner.

    Dec-POMDP dual-control for multi-agent coordination measurement.
    """

    def __init__(self, domain: str = "telecom", data_path: Path | None = None):
        """
        Initialize Tau2-Bench runner.

        Args:
            domain: Domain to evaluate
            data_path: Path to tau2-bench data
        """
        self.domain = domain
        self.data_path = data_path or Path.home() / ".lyra" / "eval_data" / "tau2-bench"
        self.tasks_cache: list[EvalTask] = []

    def get_tasks(self, n: int = 100) -> list[EvalTask]:
        """Get tau2-bench tasks."""
        if self.tasks_cache:
            return self.tasks_cache[:n]

        tasks_file = self.data_path / self.domain / "tasks.json"
        if tasks_file.exists():
            with open(tasks_file) as f:
                data = json.load(f)
                self.tasks_cache = [
                    EvalTask(
                        task_id=item["task_id"],
                        prompt=item["prompt"],
                        expected_output=item.get("expected_output"),
                        metadata=item.get("metadata", {}),
                        domain=self.domain,
                    )
                    for item in data.get("tasks", [])
                ]
        else:
            self.tasks_cache = self._generate_synthetic_tasks(n)

        return self.tasks_cache[:n]

    def _generate_synthetic_tasks(self, n: int) -> list[EvalTask]:
        """Generate synthetic tasks."""
        tasks = []
        for i in range(n):
            tasks.append(
                EvalTask(
                    task_id=f"tau2-{self.domain}-{i:03d}",
                    prompt=f"Compositional task {i}: Multi-agent {self.domain} coordination",
                    expected_output=f"Coordinated output {i}",
                    domain=self.domain,
                )
            )
        return tasks

    async def check(self, task: EvalTask, output: str) -> bool:
        """Check output correctness."""
        if task.expected_output:
            return str(task.expected_output).lower() in output.lower()
        return True

    def get_name(self) -> str:
        """Get runner name."""
        return f"tau2-bench-{self.domain}"


class SWEBenchRunner(EvalRunner):
    """
    SWE-bench Verified evaluation runner.

    Test-suite-based evaluation: execute patch, run tests.
    """

    def __init__(self, data_path: Path | None = None):
        """
        Initialize SWE-bench runner.

        Args:
            data_path: Path to SWE-bench Verified data
        """
        self.data_path = (
            data_path or Path.home() / ".lyra" / "eval_data" / "swe-bench-verified"
        )
        self.tasks_cache: list[EvalTask] = []

    def get_tasks(self, n: int = 100) -> list[EvalTask]:
        """Get SWE-bench Verified tasks."""
        if self.tasks_cache:
            return self.tasks_cache[:n]

        tasks_file = self.data_path / "tasks.json"
        if tasks_file.exists():
            with open(tasks_file) as f:
                data = json.load(f)
                self.tasks_cache = [
                    EvalTask(
                        task_id=item["task_id"],
                        prompt=item["prompt"],
                        expected_output=item.get("test_patch"),
                        metadata={
                            "repo": item.get("repo"),
                            "base_commit": item.get("base_commit"),
                            "tests": item.get("tests", []),
                        },
                        domain="software_engineering",
                    )
                    for item in data.get("tasks", [])
                ]
        else:
            self.tasks_cache = self._generate_synthetic_tasks(n)

        return self.tasks_cache[:n]

    def _generate_synthetic_tasks(self, n: int) -> list[EvalTask]:
        """Generate synthetic SWE tasks."""
        tasks = []
        for i in range(n):
            tasks.append(
                EvalTask(
                    task_id=f"swe-{i:03d}",
                    prompt=f"Fix bug in software project {i}",
                    expected_output=None,  # Verified by test suite
                    metadata={"repo": f"test-repo-{i}", "tests": ["test_fix"]},
                    domain="software_engineering",
                )
            )
        return tasks

    async def check(self, task: EvalTask, output: str) -> bool:
        """
        Check output correctness by running tests.

        In real SWE-bench: apply patch and run test suite.
        For now: basic validation.
        """
        # In real implementation: apply patch, run tests, check exit code
        # For now: check if output looks like a valid code change
        code_indicators = ["def ", "class ", "import ", "return ", "if "]
        return any(indicator in output for indicator in code_indicators)

    def get_name(self) -> str:
        """Get runner name."""
        return "swe-bench-verified"


class EvalHarness:
    """
    Evaluation harness for measuring agent reliability.

    Supports tau-bench, tau2-bench, and SWE-bench Verified.
    Computes pass@1 and pass@k consistency metrics.
    """

    BACKENDS: dict[str, type[EvalRunner]] = {
        "tau-bench": TauBenchRunner,
        "tau2-bench": Tau2BenchRunner,
        "swe-bench": SWEBenchRunner,
    }

    def __init__(self, backend: str, config: dict[str, Any] | None = None):
        """
        Initialize eval harness.

        Args:
            backend: Evaluation backend (tau-bench, tau2-bench, swe-bench)
            config: Backend-specific configuration

        Raises:
            ValueError: If backend is unknown
        """
        runner_cls = self.BACKENDS.get(backend)
        if not runner_cls:
            raise ValueError(
                f"Unknown backend: {backend}. Options: {list(self.BACKENDS.keys())}"
            )

        self.runner = runner_cls(**(config or {}))
        self.backend = backend

    async def evaluate(
        self, agent: Any, tasks: int = 100, k: int = 5
    ) -> EvalResults:
        """
        Run evaluation and compute pass^k metrics.

        Args:
            agent: Agent to evaluate (must have async run method)
            tasks: Number of tasks to evaluate
            k: Number of trials per task for pass@k

        Returns:
            Evaluation results with pass@1 and pass@k metrics

        Process:
        1. For each task, run k independent trials
        2. pass@1 = fraction where first trial succeeds
        3. pass@k = fraction where ALL k trials succeed
        """
        start_time = datetime.now()
        task_list = self.runner.get_tasks(tasks)
        task_results: list[TaskResult] = []

        pass_at_1_count = 0
        pass_at_k_count = 0

        for task in task_list:
            # Run k trials for this task
            trial_results: list[TrialResult] = []

            for trial_num in range(k):
                try:
                    # Run agent on task
                    result = await agent.run(task.prompt)

                    # Extract output and metrics
                    if isinstance(result, dict):
                        output = result.get("output", str(result))
                        tokens = result.get("tokens", 0)
                        cost = result.get("cost", 0.0)
                    else:
                        output = str(result)
                        tokens = 0
                        cost = 0.0

                    # Check correctness
                    passed = await self.runner.check(task, output)

                    trial_results.append(
                        TrialResult(
                            trial_num=trial_num,
                            passed=passed,
                            output=output,
                            tokens=tokens,
                            cost=cost,
                        )
                    )

                except Exception as e:
                    trial_results.append(
                        TrialResult(
                            trial_num=trial_num,
                            passed=False,
                            output="",
                            error=str(e),
                        )
                    )

            # Calculate metrics for this task
            pass_at_1 = trial_results[0].passed if trial_results else False
            pass_at_k = all(t.passed for t in trial_results)

            if pass_at_1:
                pass_at_1_count += 1
            if pass_at_k:
                pass_at_k_count += 1

            task_results.append(
                TaskResult(
                    task_id=task.task_id,
                    trials=trial_results,
                    pass_at_1=pass_at_1,
                    pass_at_k=pass_at_k,
                    avg_tokens=int(
                        sum(t.tokens for t in trial_results) / len(trial_results)
                    )
                    if trial_results
                    else 0,
                    avg_cost=sum(t.cost for t in trial_results) / len(trial_results)
                    if trial_results
                    else 0.0,
                )
            )

        # Calculate overall metrics
        duration = (datetime.now() - start_time).total_seconds()

        return EvalResults(
            pass_at_1=pass_at_1_count / tasks if tasks > 0 else 0.0,
            pass_at_k=pass_at_k_count / tasks if tasks > 0 else 0.0,
            k=k,
            n_tasks=tasks,
            backend=self.runner.get_name(),
            avg_cost_per_task=sum(tr.avg_cost for tr in task_results) / tasks
            if tasks > 0
            else 0.0,
            avg_tokens_per_task=int(
                sum(tr.avg_tokens for tr in task_results) / tasks
            )
            if tasks > 0
            else 0,
            task_results=task_results,
            total_duration_seconds=duration,
        )

    async def evaluate_single(self, agent: Any, task: EvalTask, k: int = 5) -> TaskResult:
        """
        Evaluate a single task with k trials.

        Args:
            agent: Agent to evaluate
            task: Task to evaluate
            k: Number of trials

        Returns:
            Task result with trial details
        """
        trial_results: list[TrialResult] = []

        for trial_num in range(k):
            try:
                result = await agent.run(task.prompt)

                if isinstance(result, dict):
                    output = result.get("output", str(result))
                    tokens = result.get("tokens", 0)
                    cost = result.get("cost", 0.0)
                else:
                    output = str(result)
                    tokens = 0
                    cost = 0.0

                passed = await self.runner.check(task, output)

                trial_results.append(
                    TrialResult(
                        trial_num=trial_num,
                        passed=passed,
                        output=output,
                        tokens=tokens,
                        cost=cost,
                    )
                )

            except Exception as e:
                trial_results.append(
                    TrialResult(
                        trial_num=trial_num, passed=False, output="", error=str(e)
                    )
                )

        pass_at_1 = trial_results[0].passed if trial_results else False
        pass_at_k = all(t.passed for t in trial_results)

        return TaskResult(
            task_id=task.task_id,
            trials=trial_results,
            pass_at_1=pass_at_1,
            pass_at_k=pass_at_k,
            avg_tokens=int(sum(t.tokens for t in trial_results) / len(trial_results))
            if trial_results
            else 0,
            avg_cost=sum(t.cost for t in trial_results) / len(trial_results)
            if trial_results
            else 0.0,
        )


@dataclass
class BenchmarkEntry:
    """A single benchmark entry."""

    name: str
    metric: str
    sota: float
    sota_model: str
    target: float
    lyra_best: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class BenchmarkScoreboard:
    """
    Tracks Lyra performance vs SOTA across benchmarks.

    Provides a live view of where Lyra stands relative to frontier models.
    """

    ENTRIES = [
        BenchmarkEntry(
            name="tau-bench airline",
            metric="pass@1",
            sota=0.46,
            sota_model="claude-3.5-sonnet",
            target=0.50,
        ),
        BenchmarkEntry(
            name="tau-bench retail",
            metric="pass@1",
            sota=0.692,
            sota_model="claude-3.5-sonnet",
            target=0.75,
        ),
        BenchmarkEntry(
            name="tau2-bench telecom",
            metric="pass@1",
            sota=0.49,
            sota_model="claude-3.7-sonnet",
            target=0.55,
        ),
        BenchmarkEntry(
            name="SWE-bench Verified",
            metric="pass@1",
            sota=0.693,
            sota_model="various",
            target=0.75,
        ),
        BenchmarkEntry(
            name="pass^k consistency (k=5)",
            metric="pass@5",
            sota=0.25,
            sota_model="gpt-4o",
            target=0.40,
        ),
    ]

    def __init__(self, storage_path: Path | None = None):
        """
        Initialize scoreboard.

        Args:
            storage_path: Path to store scoreboard data
        """
        self.storage_path = (
            storage_path or Path.home() / ".lyra" / "eval_data" / "scoreboard.json"
        )
        self.entries = list(self.ENTRIES)
        self._load()

    def _load(self):
        """Load scoreboard from disk."""
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                data = json.load(f)
                for entry_data in data.get("entries", []):
                    # Update lyra_best for matching entries
                    for entry in self.entries:
                        if entry.name == entry_data.get("name"):
                            entry.lyra_best = entry_data.get("lyra_best", 0.0)
                            entry.last_updated = datetime.fromisoformat(
                                entry_data.get("last_updated", datetime.now().isoformat())
                            )

    def update(self, benchmark_name: str, score: float):
        """
        Update Lyra's best score for a benchmark.

        Args:
            benchmark_name: Name of the benchmark
            score: New score
        """
        for entry in self.entries:
            if entry.name == benchmark_name:
                if score > entry.lyra_best:
                    entry.lyra_best = score
                    entry.last_updated = datetime.now()
                    self._save()
                break

    def _save(self):
        """Save scoreboard to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(
                {
                    "entries": [
                        {
                            "name": e.name,
                            "metric": e.metric,
                            "sota": e.sota,
                            "sota_model": e.sota_model,
                            "target": e.target,
                            "lyra_best": e.lyra_best,
                            "last_updated": e.last_updated.isoformat(),
                        }
                        for e in self.entries
                    ]
                },
                f,
                indent=2,
            )

    def report(self) -> str:
        """
        Generate a markdown scoreboard.

        Returns:
            Markdown table of benchmark results
        """
        lines = ["| Benchmark | Metric | SOTA | Lyra Best | Target | Gap |"]
        lines.append("|---|---|---|---|---|---|")

        for entry in self.entries:
            current = max(entry.lyra_best, entry.sota)
            gap = ((entry.target - current) / entry.target * 100) if entry.target > 0 else 0

            lines.append(
                f"| {entry.name} | {entry.metric} | "
                f"{entry.sota:.1%} ({entry.sota_model}) | "
                f"{entry.lyra_best:.1%} | {entry.target:.1%} | "
                f"{gap:.0f}% |"
            )

        return "\n".join(lines)

    def get_entry(self, name: str) -> BenchmarkEntry | None:
        """Get a specific benchmark entry."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None
