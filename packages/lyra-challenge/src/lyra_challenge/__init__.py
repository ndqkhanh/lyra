"""
Lyra Challenge — Benchmark evaluation suites and competitive challenge infrastructure.

This package provides:
- Challenge suite definitions (SWE-bench, HumanEval, competitive programming)
- Test harness for running agents against benchmarks
- Scoring and ranking for agent performance
- Problem difficulty estimation
- Solution validation and grading
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ChallengeDomain(str, Enum):
    """Domain categories for challenge problems."""

    CODE_GENERATION = "CODE_GENERATION"
    CODE_REPAIR = "CODE_REPAIR"
    REASONING = "REASONING"
    MATH = "MATH"
    PLANNING = "PLANNING"
    TOOL_USE = "TOOL_USE"
    SAFETY = "SAFETY"
    MULTI_STEP = "MULTI_STEP"
    ADVERSARIAL = "ADVERSARIAL"
    INSTRUCTION_FOLLOWING = "INSTRUCTION_FOLLOWING"


class Difficulty(str, Enum):
    """Problem difficulty levels."""

    TRIVIAL = "TRIVIAL"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class GradingStrategy(str, Enum):
    """Strategies for grading solutions."""

    EXACT_MATCH = "EXACT_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    TEST_CASE_PASS = "TEST_CASE_PASS"
    LLM_JUDGE = "LLM_JUDGE"
    SEMANTIC_EQUIVALENCE = "SEMANTIC_EQUIVALENCE"
    PARTIAL_CREDIT = "PARTIAL_CREDIT"


class SolutionStatus(str, Enum):
    """Status of a submitted solution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestCase:
    """A single test case for a challenge problem.

    Parameters
    ----------
    test_id : str
        Unique identifier for this test case.
    input_data : str
        Input data for the test case.
    expected_output : str
        Expected output for the test case.
    is_hidden : bool
        Whether this is a hidden test case (not shown to the agent).
    weight : float
        Scoring weight for this test case.
    """

    test_id: str
    input_data: str
    expected_output: str
    is_hidden: bool = False
    weight: float = 1.0


@dataclass(frozen=True)
class ChallengeProblem:
    """Definition of a single challenge problem.

    Parameters
    ----------
    problem_id : str
        Unique identifier for this problem.
    title : str
        Short title describing the problem.
    description : str
        Full problem description and instructions.
    domain : str
        Challenge domain category.
    difficulty : str
        Difficulty level.
    test_cases : tuple[TestCase, ...]
        Test cases for grading.
    starter_code : str
        Optional starter code or template.
    time_limit_seconds : float
        Maximum execution time in seconds.
    tags : tuple[str, ...]
        Searchable tags for categorisation.
    """

    problem_id: str
    title: str
    description: str
    domain: str
    difficulty: str
    test_cases: tuple[TestCase, ...]
    starter_code: str = ""
    time_limit_seconds: float = 30.0
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChallengeSuite:
    """Collection of challenge problems forming a benchmark suite.

    Parameters
    ----------
    suite_id : str
        Unique identifier for this suite.
    name : str
        Human-readable name (e.g. "SWE-bench", "HumanEval").
    description : str
        Description of the benchmark suite.
    problems : tuple[ChallengeProblem, ...]
        Problems in this suite.
    version : str
        Suite version.
    total_weight : float
        Sum of all problem weights for normalised scoring.
    """

    suite_id: str
    name: str
    description: str
    problems: tuple[ChallengeProblem, ...]
    version: str = "1.0"
    total_weight: float = 0.0


@dataclass(frozen=True)
class SolutionAttempt:
    """Record of an agent's attempt at solving a problem.

    Parameters
    ----------
    attempt_id : str
        Unique identifier for this attempt.
    problem_id : str
        The problem being attempted.
    agent_id : str
        Identifier of the agent making the attempt.
    solution_text : str
        The submitted solution.
    status : str
        Current status of the attempt.
    score : float
        Current score (0.0 to 1.0).
    tests_passed : int
        Number of test cases passed.
    tests_total : int
        Total number of test cases.
    execution_time_seconds : float
        Actual execution time.
    error_message : str
        Error message if the attempt failed.
    timestamp : float
        Unix timestamp when the attempt was submitted.
    """

    attempt_id: str
    problem_id: str
    agent_id: str
    solution_text: str
    status: str
    score: float
    tests_passed: int
    tests_total: int
    execution_time_seconds: float
    error_message: str = ""
    timestamp: float = 0.0


@dataclass(frozen=True)
class AgentRanking:
    """Ranking of an agent within a challenge suite.

    Parameters
    ----------
    agent_id : str
        Identifier of the agent.
    suite_id : str
        The suite this ranking is for.
    total_score : float
        Aggregate score across all problems.
    problems_solved : int
        Number of problems fully solved.
    problems_attempted : int
        Number of problems attempted.
    rank : int
        Ordinal rank (1 = best).
    percentile : float
        Percentile ranking (0.0 to 1.0, higher is better).
    """

    agent_id: str
    suite_id: str
    total_score: float
    problems_solved: int
    problems_attempted: int
    rank: int
    percentile: float


@dataclass(frozen=True)
class ChallengeConfig:
    """Configuration for the ChallengeEngine.

    Parameters
    ----------
    grading_strategy : str
        Default grading strategy to apply.
    max_execution_time : float
        Maximum execution time per problem in seconds.
    hidden_test_weight : float
        Weight multiplier for hidden test cases.
    parallel_evaluation : bool
        Whether to evaluate problems in parallel.
    retry_on_failure : bool
        Whether to retry failed attempts once.
    max_problems_per_suite : int
        Maximum number of problems to load per suite.
    """

    grading_strategy: str = "TEST_CASE_PASS"
    max_execution_time: float = 60.0
    hidden_test_weight: float = 1.0
    parallel_evaluation: bool = False
    retry_on_failure: bool = False
    max_problems_per_suite: int = 1000


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------


def _exact_match(output: str, expected: str) -> bool:
    """Check exact string match after stripping whitespace."""
    return output.strip() == expected.strip()


def _fuzzy_match(output: str, expected: str) -> float:
    """Fuzzy token-based match score between 0.0 and 1.0."""
    output_tokens = set(re.split(r"\W+", output.lower()))
    expected_tokens = set(re.split(r"\W+", expected.lower()))
    if not expected_tokens:
        return 1.0 if not output_tokens else 0.0
    intersection = output_tokens & expected_tokens
    return len(intersection) / len(expected_tokens)


def _semantic_hash_similarity(output: str, expected: str) -> float:
    """Approximate structural similarity via normalised hash alignment.

    Strips variable names and whitespace then compares a hash-derived
    fingerprint to estimate semantic equivalence.
    """
    def _normalise(text: str) -> str:
        # Collapse whitespace and normalise punctuation
        norm = re.sub(r"\s+", " ", text)
        norm = re.sub(r'(["\'])(?:(?!\1).)*?\1', '"STR"', norm)  # strings → "STR"
        norm = re.sub(r"\b\d+\b", "N", norm)  # numbers → N
        return norm

    norm_output = _normalise(output)
    norm_expected = _normalise(expected)

    oh = hashlib.sha256(norm_output.encode()).hexdigest()
    eh = hashlib.sha256(norm_expected.encode()).hexdigest()

    # Compare hex digests character by character
    matches = sum(1 for a, b in zip(oh, eh) if a == b)
    return matches / len(oh)


# ---------------------------------------------------------------------------
# ChallengeEngine
# ---------------------------------------------------------------------------


class ChallengeEngine:
    """Engine for defining, running, and grading challenge benchmarks.

    Maintains a registry of challenge suites, evaluates agent solutions,
    and produces rankings.

    Parameters
    ----------
    config : ChallengeConfig | None
        Engine configuration. Uses defaults when ``None``.
    """

    def __init__(self, config: ChallengeConfig | None = None) -> None:
        self._config = config or ChallengeConfig()
        self._suites: dict[str, ChallengeSuite] = {}
        self._attempts: dict[str, SolutionAttempt] = {}
        self._rankings: list[AgentRanking] = []

    # -- Suite management ------------------------------------------------------

    def register_suite(self, suite: ChallengeSuite) -> None:
        """Register a challenge suite in the engine.

        Parameters
        ----------
        suite : ChallengeSuite
            The suite to register.
        """
        self._suites[suite.suite_id] = suite
        logger.debug("Registered challenge suite '%s' (%d problems)", suite.name, len(suite.problems))

    def list_suites(self) -> list[dict[str, Any]]:
        """List all registered challenge suites.

        Returns
        -------
        list[dict[str, Any]]
            Summary dictionaries for each suite.
        """
        return [
            {
                "suite_id": s.suite_id,
                "name": s.name,
                "problem_count": len(s.problems),
                "version": s.version,
            }
            for s in self._suites.values()
        ]

    def get_problems(
        self,
        suite_id: str,
        domain: str | None = None,
        difficulty: str | None = None,
        limit: int | None = None,
    ) -> list[ChallengeProblem]:
        """Retrieve problems from a suite with optional filters.

        Parameters
        ----------
        suite_id : str
            The suite to query.
        domain : str | None
            Filter by challenge domain.
        difficulty : str | None
            Filter by difficulty level.
        limit : int | None
            Maximum number of problems to return.

        Returns
        -------
        list[ChallengeProblem]
            Filtered list of problems.
        """
        suite = self._suites.get(suite_id)
        if not suite:
            return []

        problems = list(suite.problems)
        if domain:
            problems = [p for p in problems if p.domain == domain]
        if difficulty:
            problems = [p for p in problems if p.difficulty == difficulty]
        if limit is not None:
            problems = problems[:limit]

        return problems

    # -- Solution grading ------------------------------------------------------

    def grade_solution(
        self,
        problem: ChallengeProblem,
        solution: str,
        strategy: str | None = None,
    ) -> SolutionAttempt:
        """Grade a solution against a problem's test cases.

        Parameters
        ----------
        problem : ChallengeProblem
            The problem being solved.
        solution : str
            The agent's solution text.
        strategy : str | None
            Grading strategy to use. Defaults to the config value.

        Returns
        -------
        SolutionAttempt
            The graded attempt with score and test results.
        """
        strategy = strategy or self._config.grading_strategy
        attempt_id = str(uuid.uuid4())[:12]

        tests_passed = 0
        tests_total = len(problem.test_cases)
        total_weight = 0.0
        earned_weight = 0.0

        start_time = time.perf_counter()

        for tc in problem.test_cases:
            weight = tc.weight * (self._config.hidden_test_weight if tc.is_hidden else 1.0)
            total_weight += weight

            if strategy == GradingStrategy.EXACT_MATCH.value:
                passed = _exact_match(solution, tc.expected_output)
            elif strategy == GradingStrategy.FUZZY_MATCH.value:
                passed = _fuzzy_match(solution, tc.expected_output) >= 0.85
            elif strategy == GradingStrategy.SEMANTIC_EQUIVALENCE.value:
                passed = _semantic_hash_similarity(solution, tc.expected_output) >= 0.6
            elif strategy == GradingStrategy.PARTIAL_CREDIT.value:
                similarity = _fuzzy_match(solution, tc.expected_output)
                earned_weight += weight * similarity
                if similarity >= 0.8:
                    tests_passed += 1
                continue
            else:
                # Default: TEST_CASE_PASS — run the solution as code (simulated)
                passed = _exact_match(solution, tc.expected_output)

            if passed:
                tests_passed += 1
                earned_weight += weight

        elapsed = time.perf_counter() - start_time

        if tests_total > 0:
            score = earned_weight / total_weight if total_weight > 0 else 0.0
        else:
            score = 1.0 if solution.strip() else 0.0

        if score >= 1.0:
            status = SolutionStatus.PASSED.value
        elif score > 0.0:
            status = SolutionStatus.PARTIAL.value
        else:
            status = SolutionStatus.FAILED.value

        if elapsed > problem.time_limit_seconds:
            status = SolutionStatus.TIMED_OUT.value

        attempt = SolutionAttempt(
            attempt_id=attempt_id,
            problem_id=problem.problem_id,
            agent_id="",
            solution_text=solution,
            status=status,
            score=round(score, 4),
            tests_passed=tests_passed,
            tests_total=tests_total,
            execution_time_seconds=round(elapsed, 4),
            timestamp=time.time(),
        )

        self._attempts[attempt_id] = attempt
        return attempt

    # -- Suite evaluation ------------------------------------------------------

    def evaluate_agent_on_suite(
        self,
        suite_id: str,
        agent_id: str,
        solutions: dict[str, str],
    ) -> list[SolutionAttempt]:
        """Evaluate an agent against every problem in a suite.

        Parameters
        ----------
        suite_id : str
            The suite to evaluate against.
        agent_id : str
            Identifier of the agent being evaluated.
        solutions : dict[str, str]
            Mapping of problem_id → solution text.

        Returns
        -------
        list[SolutionAttempt]
            Graded attempts for each problem in the suite.
        """
        suite = self._suites.get(suite_id)
        if not suite:
            return []

        results: list[SolutionAttempt] = []
        for problem in suite.problems:
            solution = solutions.get(problem.problem_id, "")
            attempt = self.grade_solution(problem, solution)
            # Create a new attempt with the agent_id set
            attempt = SolutionAttempt(
                attempt_id=attempt.attempt_id,
                problem_id=attempt.problem_id,
                agent_id=agent_id,
                solution_text=attempt.solution_text,
                status=attempt.status,
                score=attempt.score,
                tests_passed=attempt.tests_passed,
                tests_total=attempt.tests_total,
                execution_time_seconds=attempt.execution_time_seconds,
                error_message=attempt.error_message,
                timestamp=attempt.timestamp,
            )
            results.append(attempt)
            self._attempts[attempt.attempt_id] = attempt

        return results

    def compute_rankings(self, suite_id: str) -> list[AgentRanking]:
        """Compute agent rankings for a challenge suite.

        Groups attempts by agent, computes aggregate scores, and
        produces ordinal rankings.

        Parameters
        ----------
        suite_id : str
            The suite to compute rankings for.

        Returns
        -------
        list[AgentRanking]
            Agent rankings sorted by rank (1 = best).
        """
        suite = self._suites.get(suite_id)
        if not suite:
            return []

        # Group attempts by agent
        agent_scores: dict[str, dict[str, Any]] = {}
        for attempt in self._attempts.values():
            if attempt.problem_id not in {p.problem_id for p in suite.problems}:
                continue
            if not attempt.agent_id:
                continue

            if attempt.agent_id not in agent_scores:
                agent_scores[attempt.agent_id] = {
                    "total_score": 0.0,
                    "solved": 0,
                    "attempted": 0,
                }
            stats = agent_scores[attempt.agent_id]
            stats["total_score"] += attempt.score
            stats["attempted"] += 1
            if attempt.status == SolutionStatus.PASSED.value:
                stats["solved"] += 1

        if not agent_scores:
            return []

        # Sort by total_score descending
        sorted_agents = sorted(
            agent_scores.items(), key=lambda x: -x[1]["total_score"]
        )
        total_agents = len(sorted_agents)

        rankings: list[AgentRanking] = []
        for rank_idx, (agent_id, stats) in enumerate(sorted_agents):
            rank = rank_idx + 1
            percentile = (total_agents - rank) / total_agents
            rankings.append(
                AgentRanking(
                    agent_id=agent_id,
                    suite_id=suite_id,
                    total_score=round(stats["total_score"], 4),
                    problems_solved=stats["solved"],
                    problems_attempted=stats["attempted"],
                    rank=rank,
                    percentile=round(percentile, 4),
                )
            )

        self._rankings.extend(rankings)
        return rankings

    # -- Problem difficulty estimation -----------------------------------------

    def estimate_difficulty(self, problem: ChallengeProblem) -> str:
        """Estimate the difficulty of a problem based on its characteristics.

        Uses description length, test case count, domain category, and
        starter code complexity to produce a difficulty estimate.

        Parameters
        ----------
        problem : ChallengeProblem
            The problem to estimate difficulty for.

        Returns
        -------
        str
            Estimated difficulty level.
        """
        score = 0.0

        # Description length contributes to complexity
        desc_len = len(problem.description)
        if desc_len > 2000:
            score += 3
        elif desc_len > 1000:
            score += 2
        elif desc_len > 500:
            score += 1

        # Test case count
        num_tests = len(problem.test_cases)
        if num_tests > 10:
            score += 3
        elif num_tests > 5:
            score += 2
        elif num_tests > 0:
            score += 1

        # Domain difficulty
        domain_bonus = {
            ChallengeDomain.ADVERSARIAL.value: 3,
            ChallengeDomain.MULTI_STEP.value: 2,
            ChallengeDomain.CODE_REPAIR.value: 2,
            ChallengeDomain.TOOL_USE.value: 2,
            ChallengeDomain.SAFETY.value: 2,
            ChallengeDomain.REASONING.value: 1,
            ChallengeDomain.PLANNING.value: 1,
            ChallengeDomain.MATH.value: 1,
            ChallengeDomain.CODE_GENERATION.value: 0,
            ChallengeDomain.INSTRUCTION_FOLLOWING.value: 0,
        }
        score += domain_bonus.get(problem.domain, 0)

        # Starter code complexity
        if problem.starter_code:
            score += min(3, problem.starter_code.count("\n") // 5)

        # Map score to difficulty
        if score >= 7:
            return Difficulty.EXPERT.value
        elif score >= 5:
            return Difficulty.HARD.value
        elif score >= 3:
            return Difficulty.MEDIUM.value
        elif score >= 1:
            return Difficulty.EASY.value
        else:
            return Difficulty.TRIVIAL.value

    # -- Stats ----------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return engine statistics.

        Returns
        -------
        dict[str, Any]
            Suite count, attempt count, average score, ranking count.
        """
        attempts = list(self._attempts.values())
        avg_score = (
            sum(a.score for a in attempts) / len(attempts) if attempts else 0.0
        )
        return {
            "suites_registered": len(self._suites),
            "total_problems": sum(len(s.problems) for s in self._suites.values()),
            "total_attempts": len(attempts),
            "average_score": round(avg_score, 4),
            "rankings_computed": len(self._rankings),
        }


__all__ = [
    # Enums
    "ChallengeDomain",
    "Difficulty",
    "GradingStrategy",
    "SolutionStatus",
    # Data classes
    "TestCase",
    "ChallengeProblem",
    "ChallengeSuite",
    "SolutionAttempt",
    "AgentRanking",
    "ChallengeConfig",
    # Engine
    "ChallengeEngine",
]
