"""Tests for the lyra-challenge package."""

from __future__ import annotations

import pytest
from lyra_challenge import (
    AgentRanking,
    ChallengeConfig,
    ChallengeDomain,
    ChallengeEngine,
    ChallengeProblem,
    ChallengeSuite,
    Difficulty,
    GradingStrategy,
    SolutionAttempt,
    SolutionStatus,
    TestCase,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> ChallengeEngine:
    """Return a default ChallengeEngine instance."""
    return ChallengeEngine()


@pytest.fixture
def sample_test_cases() -> tuple[TestCase, ...]:
    return (
        TestCase(
            test_id="tc1",
            input_data="2 + 2",
            expected_output="4",
        ),
        TestCase(
            test_id="tc2",
            input_data="3 + 5",
            expected_output="8",
        ),
        TestCase(
            test_id="tc3_hidden",
            input_data="10 + 20",
            expected_output="30",
            is_hidden=True,
            weight=2.0,
        ),
    )


@pytest.fixture
def sample_problem(sample_test_cases: tuple[TestCase, ...]) -> ChallengeProblem:
    return ChallengeProblem(
        problem_id="prob_001",
        title="Simple Addition",
        description=(
            "Write a function that adds two numbers.\n\nGiven two integers a and b, return their"
            "sum."
        ),
        domain=ChallengeDomain.CODE_GENERATION.value,
        difficulty=Difficulty.EASY.value,
        test_cases=sample_test_cases,
    )


@pytest.fixture
def sample_suite(sample_problem: ChallengeProblem) -> ChallengeSuite:
    return ChallengeSuite(
        suite_id="suite_test",
        name="Test Suite",
        description="A test benchmark suite.",
        problems=(sample_problem,),
    )


@pytest.fixture
def multi_problem_suite() -> ChallengeSuite:
    problems: list[ChallengeProblem] = []
    for i in range(3):
        tc = (
            TestCase(
                test_id=f"tc_{i}_1",
                input_data=f"input_{i}",
                expected_output=f"output_{i}",
            ),
        )
        problems.append(
            ChallengeProblem(
                problem_id=f"prob_{i:03d}",
                title=f"Problem {i}",
                description=f"Solve problem {i}.\n\n" + ("X" * (i + 1) * 200),
                domain=ChallengeDomain.CODE_GENERATION.value,
                difficulty=Difficulty.EASY.value,
                test_cases=tc,
            )
        )
    return ChallengeSuite(
        suite_id="suite_multi",
        name="Multi-Problem Suite",
        description="A suite with multiple problems.",
        problems=tuple(problems),
    )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestChallengeDomain:
    def test_values(self) -> None:
        assert ChallengeDomain.CODE_GENERATION.value == "CODE_GENERATION"
        assert ChallengeDomain.CODE_REPAIR.value == "CODE_REPAIR"
        assert ChallengeDomain.REASONING.value == "REASONING"
        assert ChallengeDomain.MATH.value == "MATH"
        assert ChallengeDomain.SAFETY.value == "SAFETY"
        assert len(ChallengeDomain) == 10


class TestDifficulty:
    def test_values(self) -> None:
        assert Difficulty.TRIVIAL.value == "TRIVIAL"
        assert Difficulty.EASY.value == "EASY"
        assert Difficulty.MEDIUM.value == "MEDIUM"
        assert Difficulty.HARD.value == "HARD"
        assert Difficulty.EXPERT.value == "EXPERT"
        assert len(Difficulty) == 5


class TestGradingStrategy:
    def test_values(self) -> None:
        assert GradingStrategy.EXACT_MATCH.value == "EXACT_MATCH"
        assert GradingStrategy.FUZZY_MATCH.value == "FUZZY_MATCH"
        assert GradingStrategy.TEST_CASE_PASS.value == "TEST_CASE_PASS"
        assert GradingStrategy.PARTIAL_CREDIT.value == "PARTIAL_CREDIT"
        assert len(GradingStrategy) == 6


class TestSolutionStatus:
    def test_values(self) -> None:
        assert SolutionStatus.PASSED.value == "PASSED"
        assert SolutionStatus.FAILED.value == "FAILED"
        assert len(SolutionStatus) == 7


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


class TestTestCase:
    def test_create(self) -> None:
        tc = TestCase(test_id="t1", input_data="hello", expected_output="world")
        assert tc.test_id == "t1"
        assert tc.input_data == "hello"
        assert tc.expected_output == "world"
        assert tc.is_hidden is False
        assert tc.weight == 1.0

    def test_hidden_with_weight(self) -> None:
        tc = TestCase(
            test_id="t2",
            input_data="x",
            expected_output="y",
            is_hidden=True,
            weight=2.5,
        )
        assert tc.is_hidden is True
        assert tc.weight == 2.5

    def test_frozen_immutability(self) -> None:
        tc = TestCase(test_id="t1", input_data="", expected_output="")
        with pytest.raises(Exception):
            tc.is_hidden = True  # type: ignore[misc]


class TestChallengeProblem:
    def test_create(self, sample_problem: ChallengeProblem) -> None:
        assert sample_problem.problem_id == "prob_001"
        assert sample_problem.domain == ChallengeDomain.CODE_GENERATION.value
        assert len(sample_problem.test_cases) == 3

    def test_defaults(self) -> None:
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=(),
        )
        assert p.starter_code == ""
        assert p.time_limit_seconds == 30.0
        assert p.tags == ()

    def test_frozen_immutability(self, sample_problem: ChallengeProblem) -> None:
        with pytest.raises(Exception):
            sample_problem.title = "New Title"  # type: ignore[misc]


class TestChallengeSuite:
    def test_create(self, sample_suite: ChallengeSuite) -> None:
        assert sample_suite.suite_id == "suite_test"
        assert sample_suite.name == "Test Suite"
        assert len(sample_suite.problems) == 1

    def test_frozen_immutability(self, sample_suite: ChallengeSuite) -> None:
        with pytest.raises(Exception):
            sample_suite.name = "New Name"  # type: ignore[misc]


class TestSolutionAttempt:
    def test_create(self) -> None:
        sa = SolutionAttempt(
            attempt_id="a1",
            problem_id="p1",
            agent_id="agent1",
            solution_text="def add(a, b): return a + b",
            status="PASSED",
            score=1.0,
            tests_passed=3,
            tests_total=3,
            execution_time_seconds=0.1,
        )
        assert sa.agent_id == "agent1"
        assert sa.score == 1.0

    def test_frozen_immutability(self) -> None:
        sa = SolutionAttempt(
            attempt_id="a1",
            problem_id="p1",
            agent_id="x",
            solution_text="",
            status="PENDING",
            score=0.0,
            tests_passed=0,
            tests_total=0,
            execution_time_seconds=0.0,
        )
        with pytest.raises(Exception):
            sa.score = 1.0  # type: ignore[misc]


class TestAgentRanking:
    def test_create(self) -> None:
        ar = AgentRanking(
            agent_id="agent1",
            suite_id="s1",
            total_score=9.5,
            problems_solved=5,
            problems_attempted=10,
            rank=1,
            percentile=0.95,
        )
        assert ar.agent_id == "agent1"
        assert ar.rank == 1

    def test_frozen_immutability(self) -> None:
        ar = AgentRanking(
            agent_id="a",
            suite_id="s",
            total_score=0.0,
            problems_solved=0,
            problems_attempted=0,
            rank=1,
            percentile=1.0,
        )
        with pytest.raises(Exception):
            ar.rank = 2  # type: ignore[misc]


class TestChallengeConfig:
    def test_defaults(self) -> None:
        cfg = ChallengeConfig()
        assert cfg.grading_strategy == "TEST_CASE_PASS"
        assert cfg.max_execution_time == 60.0
        assert cfg.retry_on_failure is False

    def test_custom(self) -> None:
        cfg = ChallengeConfig(
            grading_strategy="EXACT_MATCH",
            max_execution_time=30.0,
            hidden_test_weight=2.0,
        )
        assert cfg.grading_strategy == "EXACT_MATCH"
        assert cfg.hidden_test_weight == 2.0

    def test_frozen_immutability(self) -> None:
        cfg = ChallengeConfig()
        with pytest.raises(Exception):
            cfg.max_execution_time = 120.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestEngineInit:
    def test_default_initialization(self) -> None:
        e = ChallengeEngine()
        stats = e.get_stats()
        assert stats["suites_registered"] == 0
        assert stats["total_problems"] == 0

    def test_custom_config(self) -> None:
        cfg = ChallengeConfig(grading_strategy="FUZZY_MATCH")
        e = ChallengeEngine(config=cfg)
        assert e._config.grading_strategy == "FUZZY_MATCH"


class TestSuiteManagement:
    def test_register_and_list(self, engine: ChallengeEngine, sample_suite: ChallengeSuite) -> None:
        engine.register_suite(sample_suite)
        suites = engine.list_suites()
        assert len(suites) == 1
        assert suites[0]["name"] == "Test Suite"

    def test_list_empty(self, engine: ChallengeEngine) -> None:
        assert engine.list_suites() == []

    def test_get_problems(self, engine: ChallengeEngine, sample_suite: ChallengeSuite) -> None:
        engine.register_suite(sample_suite)
        problems = engine.get_problems("suite_test")
        assert len(problems) == 1

    def test_get_problems_filtered_by_difficulty(
        self, engine: ChallengeEngine, sample_suite: ChallengeSuite
    ) -> None:
        engine.register_suite(sample_suite)
        problems = engine.get_problems("suite_test", difficulty="MEDIUM")
        assert len(problems) == 0

    def test_get_problems_filtered_by_domain(
        self, engine: ChallengeEngine, sample_suite: ChallengeSuite
    ) -> None:
        engine.register_suite(sample_suite)
        problems = engine.get_problems("suite_test", domain="CODE_GENERATION")
        assert len(problems) == 1

    def test_get_problems_nonexistent_suite(self, engine: ChallengeEngine) -> None:
        assert engine.get_problems("nonexistent") == []


class TestGrading:
    def test_exact_match_pass(
        self, engine: ChallengeEngine, sample_problem: ChallengeProblem
    ) -> None:
        result = engine.grade_solution(sample_problem, "4", strategy="EXACT_MATCH")
        assert result.status == SolutionStatus.PARTIAL.value  # only 1 of 3 matches

    def test_exact_match_perfect(self, engine: ChallengeEngine) -> None:
        tc = (TestCase(test_id="t1", input_data="", expected_output="42"),)
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=tc,
        )
        result = engine.grade_solution(p, "42", strategy="EXACT_MATCH")
        assert result.status == SolutionStatus.PASSED.value
        assert result.score == 1.0

    def test_fuzzy_match_partial(
        self, engine: ChallengeEngine, sample_problem: ChallengeProblem
    ) -> None:
        result = engine.grade_solution(sample_problem, "4 8 30", strategy="FUZZY_MATCH")
        assert result.score > 0.0

    def test_empty_solution(
        self, engine: ChallengeEngine, sample_problem: ChallengeProblem
    ) -> None:
        result = engine.grade_solution(sample_problem, "")
        assert result.status == SolutionStatus.FAILED.value
        assert result.score == 0.0

    def test_partial_credit(self, engine: ChallengeEngine) -> None:
        tc = (TestCase(test_id="t1", input_data="", expected_output="hello world"),)
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=tc,
        )
        result = engine.grade_solution(p, "hello", strategy="PARTIAL_CREDIT")
        assert result.score > 0.0
        assert result.score < 1.0

    def test_semantic_equivalence(self, engine: ChallengeEngine) -> None:
        tc = (TestCase(test_id="t1", input_data="", expected_output="def foo(): pass"),)
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=tc,
        )
        result = engine.grade_solution(p, "def foo(): pass", strategy="SEMANTIC_EQUIVALENCE")
        assert result.score == 1.0

    def test_no_test_cases(self, engine: ChallengeEngine) -> None:
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=(),
        )
        result = engine.grade_solution(p, "anything")
        assert result.status == SolutionStatus.PASSED.value

    def test_no_test_cases_empty_solution(self, engine: ChallengeEngine) -> None:
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=(),
        )
        result = engine.grade_solution(p, "")
        assert result.score == 0.0


class TestAgentEvaluation:
    def test_evaluate_agent_on_suite(
        self, engine: ChallengeEngine, sample_suite: ChallengeSuite
    ) -> None:
        engine.register_suite(sample_suite)
        solutions = {"prob_001": "4"}
        results = engine.evaluate_agent_on_suite("suite_test", "agent1", solutions)
        assert len(results) == 1
        assert results[0].agent_id == "agent1"

    def test_evaluate_nonexistent_suite(self, engine: ChallengeEngine) -> None:
        assert engine.evaluate_agent_on_suite("ghost", "a", {}) == []


class TestRankings:
    def test_compute_rankings(self, engine: ChallengeEngine, sample_suite: ChallengeSuite) -> None:
        engine.register_suite(sample_suite)
        engine.evaluate_agent_on_suite("suite_test", "agent_a", {"prob_001": "4"})
        engine.evaluate_agent_on_suite("suite_test", "agent_b", {"prob_001": "8"})

        rankings = engine.compute_rankings("suite_test")
        assert len(rankings) == 2
        assert rankings[0].rank == 1  # best
        assert rankings[1].rank == 2
        assert rankings[0].total_score <= 1.0

    def test_rankings_empty_suite(self, engine: ChallengeEngine) -> None:
        assert engine.compute_rankings("nonexistent") == []


class TestDifficultyEstimation:
    def test_trivial(self, engine: ChallengeEngine) -> None:
        tc = (TestCase(test_id="t1", input_data="", expected_output=""),)
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="Short",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=tc,
        )
        assert engine.estimate_difficulty(p) == Difficulty.EASY.value

    def test_expert(self, engine: ChallengeEngine) -> None:
        tcs = tuple(
            TestCase(test_id=f"t{i}", input_data="x" * 50, expected_output="y") for i in range(20)
        )
        p = ChallengeProblem(
            problem_id="p1",
            title="Expert Problem",
            description="X" * 3000 + "\nComplex multi-step adversarial reasoning task.",
            domain="ADVERSARIAL",
            difficulty="EASY",
            test_cases=tcs,
            starter_code="def solve():\n    " + "\n".join(f"    # Step {i}" for i in range(40)),
        )
        diff = engine.estimate_difficulty(p)
        assert diff in (Difficulty.HARD.value, Difficulty.EXPERT.value)


class TestGetStats:
    def test_initial_stats(self, engine: ChallengeEngine) -> None:
        stats = engine.get_stats()
        assert stats["suites_registered"] == 0
        assert stats["total_attempts"] == 0

    def test_stats_after_operations(
        self, engine: ChallengeEngine, sample_suite: ChallengeSuite
    ) -> None:
        engine.register_suite(sample_suite)
        engine.evaluate_agent_on_suite("suite_test", "agent1", {"prob_001": "4"})
        stats = engine.get_stats()
        assert stats["suites_registered"] == 1
        assert stats["total_attempts"] == 1
        assert stats["average_score"] >= 0.0


class TestEdgeCases:
    def test_register_multiple_suites(self, engine: ChallengeEngine) -> None:
        for i in range(5):
            s = ChallengeSuite(
                suite_id=f"s{i}",
                name=f"Suite {i}",
                description="",
                problems=(),
            )
            engine.register_suite(s)
        assert len(engine.list_suites()) == 5

    def test_solution_with_unusual_characters(self, engine: ChallengeEngine) -> None:
        tc = (TestCase(test_id="t1", input_data="", expected_output="café"),)
        p = ChallengeProblem(
            problem_id="p1",
            title="T",
            description="D",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=tc,
        )
        result = engine.grade_solution(p, "café", strategy="EXACT_MATCH")
        assert result.status == SolutionStatus.PASSED.value
