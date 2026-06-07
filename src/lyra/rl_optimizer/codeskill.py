"""
CODESKILL — Self-evolving coding skills via reinforcement learning.

Integrates RL into the skill evolution pipeline so that coding skills
improve over time through repeated cycles of code generation, testing,
reward assignment, and policy update.

Components
----------
- SkillEnvironment: A coding task environment that provides rewards
  from test pass/fail rates and code quality metrics.
- SkillAgent: An RL agent that learns to generate better code over
  time by updating its policy based on environmental rewards.
- EvolutionLoop: Orchestrates the full cycle of generating code,
  running tests, computing rewards, and updating the policy.

References
----------
- MetaAgent-X: End-to-End RL for Multi-Agent Workflow Optimization
  arXiv:2605.14212v1
- GEPA: Genetic-Pareto Evolutionary Prompt Optimisation
  arXiv:2507.19457
- SkillOpt: Validation-Gated Text Optimization for LLM Skills
  Microsoft Research, arXiv:2605.23904v2
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# -- types ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodingTask:
    """A coding task for the RL environment.

    Attributes:
        task_id: Unique identifier.
        description: Natural language description of the task.
        test_cases: List of (input, expected_output) pairs.
        language: Target programming language.
        constraints: Additional constraints (e.g., "no external deps").
        difficulty: Task difficulty rating in [0, 1].
    """

    task_id: str = ""
    description: str = ""
    test_cases: tuple[tuple[str, str], ...] = ()
    language: str = "python"
    constraints: str = ""
    difficulty: float = 0.5


@dataclass(frozen=True)
class SkillExecution:
    """A single execution of a coding skill against a task.

    Attributes:
        code: The generated code.
        passed: Whether all tests passed.
        tests_passed: Number of tests that passed.
        tests_total: Total number of tests.
        quality_score: Code quality score in [0, 1].
        reward: The computed reward for this execution.
        cost_usd: Estimated execution cost.
        error: Error message if execution failed.
    """

    code: str = ""
    passed: bool = False
    tests_passed: int = 0
    tests_total: int = 0
    quality_score: float = 0.0
    reward: float = 0.0
    cost_usd: float = 0.0
    error: str = ""


@dataclass(frozen=True)
class EvolutionRecord:
    """A record of one evolution iteration.

    Attributes:
        iteration: Iteration number.
        task_id: Task that was attempted.
        executions: History of executions within this iteration.
        best_reward: Best reward achieved.
        avg_reward: Average reward across executions.
        policy_update_loss: Loss from the policy update step.
    """

    iteration: int = 0
    task_id: str = ""
    executions: tuple[SkillExecution, ...] = ()
    best_reward: float = 0.0
    avg_reward: float = 0.0
    policy_update_loss: float = 0.0


# ---------------------------------------------------------------------------
# -- Reward shaping ---------------------------------------------------------
# ---------------------------------------------------------------------------


def compute_reward(
    passed: bool,
    tests_passed: int,
    tests_total: int,
    quality_score: float,
    difficulty: float = 0.5,
    cost_usd: float = 0.0,
) -> float:
    """Compute a shaped reward from execution outcomes.

    Reward components:
        - **Pass bonus**: +1.0 if all tests pass, -0.5 otherwise.
        - **Partial credit**: weighted fraction of tests passed.
        - **Quality bonus**: up to +0.5 from code quality.
        - **Difficulty scaling**: multiply by (1 + difficulty).
        - **Cost penalty**: subtract normalized cost.

    Args:
        passed: Whether all tests passed.
        tests_passed: Number of tests that passed.
        tests_total: Total number of tests.
        quality_score: Code quality in [0, 1].
        difficulty: Task difficulty in [0, 1].
        cost_usd: Execution cost in USD.

    Returns:
        The shaped reward value.
    """
    n = max(tests_total, 1)

    if passed:
        pass_bonus = 1.0
    else:
        pass_bonus = -0.5

    partial_credit = (tests_passed / n) * 0.5
    quality_bonus = quality_score * 0.5
    cost_penalty = min(cost_usd * 10.0, 0.3)
    scale = 1.0 + difficulty

    reward = (pass_bonus + partial_credit + quality_bonus - cost_penalty) * scale
    return max(reward, -5.0)  # clamp


# ---------------------------------------------------------------------------
# -- Skill Environment ------------------------------------------------------
# ---------------------------------------------------------------------------


class SkillEnvironment:
    """Coding task environment that provides rewards from test outcomes.

    The environment simulates code execution against a set of test cases
    and returns rewards based on pass/fail rates and code quality.

    Usage::

        env = SkillEnvironment()
        task = CodingTask(description="sort a list", ...)
        execution = env.evaluate(task, generated_code)
        print(execution.reward)  # shaped reward
    """

    def __init__(
        self,
        executor_fn: Callable[[str, tuple[tuple[str, str], ...]], tuple[bool, int, str]] | None = None,
        quality_fn: Callable[[str, str], float] | None = None,
    ) -> None:
        """Initialise the environment.

        Args:
            executor_fn: Optional custom test executor. Signature:
                ``(code, test_cases) -> (passed, tests_passed, error)``.
            quality_fn: Optional custom code quality scorer. Signature:
                ``(code, language) -> score``.
        """
        self._executor = executor_fn or self._default_executor
        self._quality_scorer = quality_fn or self._default_quality_scorer
        self._total_cost: float = 0.0
        self._eval_count: int = 0

    def evaluate(
        self,
        code: str,
        task: CodingTask,
    ) -> SkillExecution:
        """Evaluate generated code against a coding task.

        Runs the code through the test executor, scores quality, and
        computes the shaped reward.

        Args:
            code: The generated code.
            task: The coding task to evaluate against.

        Returns:
            A ``SkillExecution`` with the evaluation outcome.
        """
        self._eval_count += 1

        passed, tests_passed, error = self._executor(code, task.test_cases)
        tests_total = len(task.test_cases)
        quality = self._quality_scorer(code, task.language)

        cost = self._estimate_cost(code)
        self._total_cost += cost

        reward = compute_reward(
            passed=passed,
            tests_passed=tests_passed,
            tests_total=tests_total,
            quality_score=quality,
            difficulty=task.difficulty,
            cost_usd=cost,
        )

        return SkillExecution(
            code=code,
            passed=passed,
            tests_passed=tests_passed,
            tests_total=tests_total,
            quality_score=quality,
            reward=reward,
            cost_usd=cost,
            error=error,
        )

    @property
    def total_cost(self) -> float:
        """Total compute cost of all evaluations."""
        return self._total_cost

    @property
    def eval_count(self) -> int:
        """Total number of evaluations performed."""
        return self._eval_count

    def reset(self) -> None:
        """Reset cumulative cost and evaluation counters."""
        self._total_cost = 0.0
        self._eval_count = 0

    # ------------------------------------------------------------------
    # Default implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _default_executor(
        code: str,
        test_cases: tuple[tuple[str, str], ...],
    ) -> tuple[bool, int, str]:
        """Default test executor: simulates test execution.

        Uses a heuristic pass rate modulated by code length and
        complexity as a proxy for real test execution.

        Args:
            code: The generated code.
            test_cases: List of (input, expected) pairs.

        Returns:
            (passed, tests_passed, error_message) tuple.
        """
        if not code.strip():
            return False, 0, "empty code"

        tests_total = max(len(test_cases), 1)
        # Heuristic: longer, more complex code is more likely to fail
        complexity_penalty = min(len(code) / 2000.0, 0.4)
        base_pass_rate = 0.8 - complexity_penalty

        tests_passed = sum(
            1 for _ in range(tests_total) if random.random() < base_pass_rate
        )
        passed = tests_passed == tests_total
        error = "" if passed else f"{tests_total - tests_passed} test(s) failed"
        return passed, tests_passed, error

    @staticmethod
    def _default_quality_scorer(code: str, language: str) -> float:
        """Default code quality scorer: heuristic based on static analysis.

        Scores based on:
            - Presence of function/class definitions
            - Type annotations (Python) or type hints
            - Docstrings / comments
            - Reasonable length
            - Language-appropriate structure

        Args:
            code: The generated code.
            language: Programming language.

        Returns:
            Quality score in [0, 1].
        """
        score = 0.3  # base score
        lines = code.strip().split("\n")
        n_lines = len(lines)

        # Has function or class definitions
        if any(line.strip().startswith(("def ", "class ", "fn ", "func ")) for line in lines):
            score += 0.2

        # Has docstring or block comment
        if '"""' in code or "'''" in code or "/**" in code or "///" in code:
            score += 0.15

        # Has type annotations (Python : syntax or TypeScript/Java style)
        if ": " in code and ("def " in code or "fn " in code):
            score += 0.1

        # Has return statement or expression
        if "return" in code or "=>" in code:
            score += 0.1

        # Reasonable length (not too short, not too long)
        if 5 <= n_lines <= 200:
            score += 0.1
        elif n_lines < 5:
            score -= 0.1

        # Has imports or use statements
        if any(line.strip().startswith(("import ", "from ", "use ", "require ")) for line in lines):
            score += 0.05

        return max(0.0, min(1.0, score))

    @staticmethod
    def _estimate_cost(code: str) -> float:
        """Estimate execution cost based on code length and complexity.

        Returns:
            Cost in USD (approximate).
        """
        token_estimate = len(code) / 4.0  # rough: 4 chars per token
        input_cost = token_estimate * 3e-6  # $3 per million tokens
        output_cost = 50 * 15e-6  # ~50 output tokens at $15/M
        return input_cost + output_cost


# ---------------------------------------------------------------------------
# -- Skill Agent ------------------------------------------------------------
# ---------------------------------------------------------------------------


class SkillAgent:
    """RL agent that learns to write better code over time.

    The agent maintains a policy that maps task descriptions to code
    generation strategies. It updates its policy based on the rewards
    received from the environment.

    This is a **learnable policy stub**. Real deployments replace
    ``_generate_fn`` with an actual model-based code generation policy.
    """

    def __init__(
        self,
        generate_fn: Callable[[CodingTask], str] | None = None,
        learning_rate: float = 0.01,
    ) -> None:
        """Initialise the skill agent.

        Args:
            generate_fn: Optional custom code generation function.
            learning_rate: Learning rate for policy updates.
        """
        self._generate_fn = generate_fn or self._heuristic_generate
        self._learning_rate = learning_rate
        self._params: dict[str, float] = {
            "temperature": 0.8,
            "style_weight": 0.5,
        }
        self._generations: int = 0
        self._total_reward: float = 0.0
        self._policy_losses: list[float] = []

    def generate(self, task: CodingTask) -> str:
        """Generate code for a given task.

        Args:
            task: The coding task to solve.

        Returns:
            Generated code as a string.
        """
        code = self._generate_fn(task)
        self._generations += 1
        return code

    def update(
        self,
        task: CodingTask,
        execution: SkillExecution,
    ) -> float:
        """Update the agent's policy based on execution feedback.

        **Stub implementation.** Updates policy parameters in the
        direction of the reward using a simple gradient estimate.

        Args:
            task: The task that was attempted.
            execution: The execution outcome with reward.

        Returns:
            The policy update loss (scalar).
        """
        self._total_reward += execution.reward

        # Simple REINFORCE-style update (stub)
        reward_signal = max(execution.reward, -1.0)
        lr = self._learning_rate

        # Adjust policy parameters based on reward
        if reward_signal > 0.5:
            self._params["temperature"] = max(0.1, self._params["temperature"] - lr * 0.5)
            self._params["style_weight"] = min(1.0, self._params["style_weight"] + lr * 0.3)
        elif reward_signal < -0.2:
            self._params["temperature"] = min(2.0, self._params["temperature"] + lr * 1.0)
            self._params["style_weight"] = max(0.0, self._params["style_weight"] - lr * 0.5)

        # Compute a synthetic policy loss
        loss = -math.log(max(execution.reward + 1.1, 0.1)) / 10.0
        self._policy_losses.append(loss)

        logger.debug(
            "policy updated",
            reward=round(execution.reward, 3),
            loss=round(loss, 6),
            temperature=round(self._params["temperature"], 3),
        )

        return loss

    @property
    def params(self) -> dict[str, float]:
        """Current policy parameters."""
        return dict(self._params)

    @property
    def generations(self) -> int:
        """Total number of code generations."""
        return self._generations

    @property
    def total_reward(self) -> float:
        """Cumulative reward across all updates."""
        return self._total_reward

    @property
    def avg_loss(self) -> float:
        """Average policy update loss."""
        if not self._policy_losses:
            return 0.0
        return sum(self._policy_losses) / len(self._policy_losses)

    @staticmethod
    def _heuristic_generate(task: CodingTask) -> str:
        """Heuristic code generation fallback.

        Produces a simple function skeleton based on the task description.
        """
        language = task.language.lower()
        if language == "python":
            return _generate_python_stub(task)
        elif language in ("javascript", "typescript", "js", "ts"):
            return _generate_javascript_stub(task)
        else:
            return f"// {task.description}\n// Language: {language}\n// Stub implementation\n"


def _generate_python_stub(task: CodingTask) -> str:
    """Generate a Python function stub for a given task."""
    name_parts = task.description.lower().split()
    fn_name = "solve"
    if name_parts:
        safe = "".join(c for c in name_parts[0] if c.isalnum() or c == "_")
        if safe:
            fn_name = safe

    return (
        f'"""\n{task.description}\n\nLanguage: {task.language}\n'
        f'Difficulty: {task.difficulty}\n"""\n\n\n'
        f"def {fn_name}():\n"
        f'    """Implement this function."""\n'
        f"    pass\n"
    )


def _generate_javascript_stub(task: CodingTask) -> str:
    """Generate a JavaScript/TypeScript function stub."""
    name_parts = task.description.lower().split()
    fn_name = "solve"
    if name_parts:
        safe = "".join(c for c in name_parts[0] if c.isalnum() or c == "_")
        if safe:
            fn_name = safe

    return (
        f"/**\n * {task.description}\n *\n"
        f" * Language: {task.language}\n"
        f" * Difficulty: {task.difficulty}\n */\n\n"
        f"function {fn_name}() {{\n"
        f"  // Implement this function.\n"
        f"}}\n"
    )


# ---------------------------------------------------------------------------
# -- Evolution Loop ---------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class EvolutionLoopConfig:
    """Configuration for the CODESKILL evolution loop.

    Attributes:
        max_iterations: Maximum number of evolution iterations.
        executions_per_iteration: Number of executions per iteration.
        improvement_threshold: Minimum reward improvement to consider.
        max_failures: Maximum consecutive failures before early stop.
    """

    max_iterations: int = 20
    executions_per_iteration: int = 4
    improvement_threshold: float = 0.05
    max_failures: int = 5


@dataclass
class EvolutionLoop:
    """Orchestrates the full CODESKILL evolution cycle.

    The loop:
        1. Samples a coding task.
        2. Agent generates code.
        3. Environment evaluates code against test cases.
        4. Reward is computed from test pass/fail + quality.
        5. Agent updates policy based on reward.
        6. Metrics are recorded.
        7. Loop terminates when convergence or max iterations.

    Usage::

        env = SkillEnvironment()
        agent = SkillAgent()
        loop = EvolutionLoop(config)
        results = loop.run(env, agent, [task1, task2, ...])
    """

    config: EvolutionLoopConfig = field(default_factory=EvolutionLoopConfig)
    records: list[EvolutionRecord] = field(default_factory=list)

    def run(
        self,
        env: SkillEnvironment,
        agent: SkillAgent,
        tasks: list[CodingTask],
    ) -> list[EvolutionRecord]:
        """Run the full evolution loop.

        Args:
            env: The coding task environment.
            agent: The RL agent.
            tasks: List of coding tasks to evolve on.

        Returns:
            List of ``EvolutionRecord`` (one per iteration).
        """
        cfg = self.config
        records: list[EvolutionRecord] = []
        consecutive_failures = 0
        best_reward_so_far = -float("inf")

        for iteration in range(cfg.max_iterations):
            # Pick a task (round-robin or random)
            task = tasks[iteration % len(tasks)]

            # Generate and execute multiple times per iteration
            executions: list[SkillExecution] = []
            for _ in range(cfg.executions_per_iteration):
                code = agent.generate(task)
                execution = env.evaluate(code, task)
                executions.append(execution)

            # Aggregate rewards
            rewards = [ex.reward for ex in executions]
            avg_reward = sum(rewards) / max(len(rewards), 1)
            best_reward = max(rewards)

            # Update policy with the best execution
            best_execution = max(executions, key=lambda ex: ex.reward)
            policy_loss = agent.update(task, best_execution)

            # Track improvement
            improved = best_reward > best_reward_so_far + cfg.improvement_threshold
            if improved:
                best_reward_so_far = best_reward
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            # Record
            record = EvolutionRecord(
                iteration=iteration,
                task_id=task.task_id,
                executions=tuple(executions),
                best_reward=best_reward,
                avg_reward=avg_reward,
                policy_update_loss=policy_loss,
            )
            records.append(record)
            self.records.append(record)

            logger.info(
                "evolution iteration",
                iteration=iteration,
                task=task.task_id,
                avg_reward=round(avg_reward, 4),
                best_reward=round(best_reward, 4),
                loss=round(policy_loss, 6),
                improved=improved,
            )

            # Early stopping
            if consecutive_failures >= cfg.max_failures:
                logger.info(
                    "early stopping: consecutive failures",
                    n=consecutive_failures,
                )
                break

        return records

    @property
    def iteration_count(self) -> int:
        """Number of completed evolution iterations."""
        return len(self.records)

    def get_best_performance(self) -> float:
        """Return the best average reward across all iterations."""
        if not self.records:
            return 0.0
        return max(r.avg_reward for r in self.records)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for the evolution process.

        Returns:
            Dict with iteration count, best reward, avg reward, and loss.
        """
        if not self.records:
            return {"iterations": 0}

        avg_rewards = [r.avg_reward for r in self.records]
        best_rewards = [r.best_reward for r in self.records]
        losses = [r.policy_update_loss for r in self.records]

        return {
            "iterations": len(self.records),
            "best_avg_reward": max(avg_rewards),
            "final_avg_reward": avg_rewards[-1],
            "best_overall_reward": max(best_rewards),
            "avg_policy_loss": sum(losses) / max(len(losses), 1),
            "improvement": avg_rewards[-1] - avg_rewards[0] if len(avg_rewards) > 1 else 0.0,
        }


__all__ = [
    "CodingTask",
    "SkillExecution",
    "EvolutionRecord",
    "SkillEnvironment",
    "SkillAgent",
    "EvolutionLoop",
    "EvolutionLoopConfig",
    "compute_reward",
]
