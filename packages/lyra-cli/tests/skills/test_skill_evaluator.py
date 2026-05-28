"""Tests for skill evaluator."""

import pytest
from lyra_cli.skills.skill_evaluator import (
    MetricType,
    SkillEvaluator,
    SkillExecution,
)


@pytest.fixture
def evaluator():
    """Create a fresh evaluator instance."""
    return SkillEvaluator()


@pytest.fixture
def sample_executions():
    """Create sample execution data."""
    return [
        SkillExecution(
            execution_id="exec_001",
            skill_name="test-skill",
            timestamp="2026-05-28T10:00:00",
            success=True,
            latency_ms=250.0,
            tokens_used=500,
            user_rating=0.9,
        ),
        SkillExecution(
            execution_id="exec_002",
            skill_name="test-skill",
            timestamp="2026-05-28T10:05:00",
            success=True,
            latency_ms=300.0,
            tokens_used=600,
            user_rating=0.85,
        ),
        SkillExecution(
            execution_id="exec_003",
            skill_name="test-skill",
            timestamp="2026-05-28T10:10:00",
            success=False,
            latency_ms=450.0,
            tokens_used=800,
            error_message="Timeout",
        ),
        SkillExecution(
            execution_id="exec_004",
            skill_name="test-skill",
            timestamp="2026-05-28T10:15:00",
            success=True,
            latency_ms=280.0,
            tokens_used=550,
            user_rating=0.88,
        ),
        SkillExecution(
            execution_id="exec_005",
            skill_name="test-skill",
            timestamp="2026-05-28T10:20:00",
            success=True,
            latency_ms=320.0,
            tokens_used=620,
            user_rating=0.92,
        ),
    ]


class TestSkillEvaluator:
    """Test suite for SkillEvaluator."""

    def test_record_execution(self, evaluator):
        """Test recording a skill execution."""
        execution = SkillExecution(
            execution_id="exec_001",
            skill_name="test-skill",
            timestamp="2026-05-28T10:00:00",
            success=True,
            latency_ms=250.0,
            tokens_used=500,
        )

        evaluator.record_execution(execution)

        metrics = evaluator.get_performance_metrics("test-skill")
        assert metrics is not None
        assert metrics.total_executions == 1

    def test_performance_metrics_calculation(self, evaluator, sample_executions):
        """Test performance metrics calculation."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        metrics = evaluator.get_performance_metrics("test-skill")

        assert metrics is not None
        assert metrics.total_executions == 5
        assert metrics.successful_executions == 4
        assert metrics.failed_executions == 1
        assert metrics.success_rate == 0.8
        assert metrics.avg_latency_ms > 0
        assert metrics.p95_latency_ms >= metrics.p50_latency_ms

    def test_latency_percentiles(self, evaluator, sample_executions):
        """Test latency percentile calculations."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        metrics = evaluator.get_performance_metrics("test-skill")

        # Verify percentile ordering
        assert metrics.p50_latency_ms <= metrics.p95_latency_ms
        assert metrics.p95_latency_ms <= metrics.p99_latency_ms

    def test_token_efficiency(self, evaluator, sample_executions):
        """Test token efficiency calculation."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        metrics = evaluator.get_performance_metrics("test-skill")

        # Token efficiency = successes per 1k tokens
        # 4 successes / (3100 total tokens / 1000) = ~1.29
        assert metrics.token_efficiency > 0

    def test_user_rating_average(self, evaluator, sample_executions):
        """Test user rating averaging."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        metrics = evaluator.get_performance_metrics("test-skill")

        # Average of 0.9, 0.85, 0.88, 0.92 = 0.8875
        assert 0.85 <= metrics.avg_user_rating <= 0.95

    def test_quality_score_calculation(self, evaluator, sample_executions):
        """Test multi-dimensional quality score."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        quality = evaluator.calculate_quality_score("test-skill")

        assert quality is not None
        assert 0.0 <= quality.correctness <= 1.0
        assert 0.0 <= quality.efficiency <= 1.0
        assert 0.0 <= quality.robustness <= 1.0
        assert 0.0 <= quality.generality <= 1.0
        assert 0.0 <= quality.composite_score <= 1.0
        assert quality.sample_size == 5

    def test_quality_score_requires_minimum_executions(self, evaluator):
        """Test that quality score requires at least 5 executions."""
        # Add only 3 executions
        for i in range(3):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_{i}",
                    skill_name="test-skill",
                    timestamp="2026-05-28T10:00:00",
                    success=True,
                    latency_ms=250.0,
                    tokens_used=500,
                )
            )

        quality = evaluator.calculate_quality_score("test-skill")
        assert quality is None  # Not enough data

    def test_quality_score_caching(self, evaluator, sample_executions):
        """Test that quality scores are cached."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        # First call calculates
        quality1 = evaluator.calculate_quality_score("test-skill")

        # Second call should return cached value
        quality2 = evaluator.calculate_quality_score("test-skill")

        assert quality1 == quality2

    def test_quality_score_cache_invalidation(self, evaluator, sample_executions):
        """Test that cache is invalidated on new execution."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        quality1 = evaluator.calculate_quality_score("test-skill")

        # Add new execution
        evaluator.record_execution(
            SkillExecution(
                execution_id="exec_006",
                skill_name="test-skill",
                timestamp="2026-05-28T10:25:00",
                success=True,
                latency_ms=200.0,
                tokens_used=400,
            )
        )

        quality2 = evaluator.calculate_quality_score("test-skill")

        # Should be recalculated
        assert quality1.sample_size != quality2.sample_size

    def test_compare_skills(self, evaluator):
        """Test A/B comparison between two skills."""
        # Add executions for skill A
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_a_{i}",
                    skill_name="skill-a",
                    timestamp="2026-05-28T10:00:00",
                    success=True,
                    latency_ms=250.0,
                    tokens_used=500,
                )
            )

        # Add executions for skill B (worse performance)
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_b_{i}",
                    skill_name="skill-b",
                    timestamp="2026-05-28T10:00:00",
                    success=i < 7,  # 70% success rate
                    latency_ms=350.0,
                    tokens_used=700,
                )
            )

        result = evaluator.compare_skills("skill-a", "skill-b", MetricType.SUCCESS_RATE)

        assert result is not None
        assert result.skill_a == "skill-a"
        assert result.skill_b == "skill-b"
        assert result.skill_a_value > result.skill_b_value
        assert result.winner == "skill-a"

    def test_compare_skills_latency(self, evaluator):
        """Test comparison by latency (lower is better)."""
        # Skill A: fast
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_a_{i}",
                    skill_name="skill-a",
                    timestamp="2026-05-28T10:00:00",
                    success=True,
                    latency_ms=200.0,
                    tokens_used=500,
                )
            )

        # Skill B: slow
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_b_{i}",
                    skill_name="skill-b",
                    timestamp="2026-05-28T10:00:00",
                    success=True,
                    latency_ms=500.0,
                    tokens_used=500,
                )
            )

        result = evaluator.compare_skills("skill-a", "skill-b", MetricType.AVG_LATENCY_MS)

        assert result is not None
        assert result.winner == "skill-a"  # Lower latency wins

    def test_get_top_skills(self, evaluator):
        """Test getting top-performing skills."""
        # Add executions for multiple skills
        skills = {
            "skill-a": 0.9,  # 90% success
            "skill-b": 0.7,  # 70% success
            "skill-c": 0.95,  # 95% success
        }

        for skill_name, success_rate in skills.items():
            for i in range(10):
                evaluator.record_execution(
                    SkillExecution(
                        execution_id=f"exec_{skill_name}_{i}",
                        skill_name=skill_name,
                        timestamp="2026-05-28T10:00:00",
                        success=(i < success_rate * 10),
                        latency_ms=250.0,
                        tokens_used=500,
                    )
                )

        top_skills = evaluator.get_top_skills(MetricType.SUCCESS_RATE, limit=3)

        assert len(top_skills) == 3
        # Should be ordered by success rate
        assert top_skills[0][0] == "skill-c"
        assert top_skills[1][0] == "skill-a"
        assert top_skills[2][0] == "skill-b"

    def test_get_skills_needing_improvement(self, evaluator):
        """Test identifying skills that need improvement."""
        # Good skill
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_good_{i}",
                    skill_name="good-skill",
                    timestamp="2026-05-28T10:00:00",
                    success=True,
                    latency_ms=200.0,
                    tokens_used=400,
                )
            )

        # Poor skill
        for i in range(10):
            evaluator.record_execution(
                SkillExecution(
                    execution_id=f"exec_poor_{i}",
                    skill_name="poor-skill",
                    timestamp="2026-05-28T10:00:00",
                    success=(i < 5),  # 50% success
                    latency_ms=600.0,
                    tokens_used=1000,
                )
            )

        needs_improvement = evaluator.get_skills_needing_improvement(threshold=0.7)

        # Only poor-skill should be flagged
        assert len(needs_improvement) == 1
        assert needs_improvement[0][0] == "poor-skill"

    def test_generate_report(self, evaluator, sample_executions):
        """Test comprehensive report generation."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        report = evaluator.generate_report("test-skill")

        assert "skill_name" in report
        assert "performance" in report
        assert "quality" in report
        assert report["performance"]["total_executions"] == 5

    def test_clear_history_specific_skill(self, evaluator, sample_executions):
        """Test clearing history for specific skill."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        # Add another skill
        evaluator.record_execution(
            SkillExecution(
                execution_id="exec_other",
                skill_name="other-skill",
                timestamp="2026-05-28T10:00:00",
                success=True,
                latency_ms=250.0,
                tokens_used=500,
            )
        )

        evaluator.clear_history("test-skill")

        # test-skill should be cleared
        assert evaluator.get_performance_metrics("test-skill") is None

        # other-skill should remain
        assert evaluator.get_performance_metrics("other-skill") is not None

    def test_clear_history_all(self, evaluator, sample_executions):
        """Test clearing all history."""
        for execution in sample_executions:
            evaluator.record_execution(execution)

        evaluator.clear_history()

        assert evaluator.get_performance_metrics("test-skill") is None

    def test_no_data_returns_none(self, evaluator):
        """Test that methods return None when no data available."""
        assert evaluator.get_performance_metrics("nonexistent") is None
        assert evaluator.calculate_quality_score("nonexistent") is None
        assert evaluator.compare_skills("a", "b") is None
