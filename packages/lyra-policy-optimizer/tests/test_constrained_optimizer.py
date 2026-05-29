"""Tests for the constrained_optimizer module."""

from __future__ import annotations

import pytest
from lyra_policy_optimizer.constrained_optimizer import (
    ConstrainedOptimizer,
    ConstrainedResult,
    ConstraintConfig,
    ConstraintViolation,
)
from lyra_policy_optimizer.exceptions import ConstraintOptimizationError
from lyra_policy_optimizer.policy_search import (
    PolicyCandidate,
    SearchConfig,
    SearchResult,
)


class TestConstraintConfig:
    """Test ConstraintConfig dataclass."""

    def test_create_config(self) -> None:
        """ConstraintConfig should store constraints correctly."""
        config = ConstraintConfig(
            constraints=("learning_rate", "batch_size"),
            constraint_bounds=((0.0001, 0.1), (16, 256)),
            penalty_coef=2.0,
            feasibility_tolerance=0.001,
        )
        assert config.penalty_coef == 2.0
        assert config.feasibility_tolerance == 0.001

    def test_frozen(self) -> None:
        """ConstraintConfig should be frozen."""
        config = ConstraintConfig(
            constraints=("lr",), constraint_bounds=((0.0, 1.0),)
        )
        with pytest.raises(AttributeError):
            config.penalty_coef = 3.0  # type: ignore[misc]


class TestConstraintViolation:
    """Test ConstraintViolation dataclass."""

    def test_create_violation(self) -> None:
        """ConstraintViolation should store violation details."""
        violation = ConstraintViolation(
            constraint="learning_rate",
            required_range=(0.0, 0.1),
            actual_value=0.5,
            violation_magnitude=0.4,
        )
        assert violation.constraint == "learning_rate"
        assert violation.required_range == (0.0, 0.1)
        assert violation.actual_value == 0.5
        assert violation.violation_magnitude == 0.4


class TestConstrainedResult:
    """Test ConstrainedResult dataclass."""

    def test_feasible_result(self) -> None:
        """ConstrainedResult should reflect feasibility."""
        policy = PolicyCandidate("test", (("lr", 0.01),), 0.9, 0.1, 0)
        result = ConstrainedResult(
            policy=policy,
            violations=(),
            feasible=True,
            penalty=0.0,
        )
        assert result.feasible is True
        assert result.penalty == 0.0


class TestConstrainedOptimizer:
    """Test ConstrainedOptimizer class."""

    @pytest.fixture
    def optimizer(self) -> ConstrainedOptimizer:
        return ConstrainedOptimizer()

    @pytest.mark.asyncio
    async def test_add_constraint(self, optimizer: ConstrainedOptimizer) -> None:
        """Add constraint should register a new constraint."""
        await optimizer.add_constraint("learning_rate", 0.0, 0.1)
        assert "learning_rate" in optimizer._constraints

    @pytest.mark.asyncio
    async def test_add_constraint_invalid_bounds(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Add constraint should reject invalid bounds."""
        with pytest.raises(
            ConstraintOptimizationError, match="invalid constraint"
        ):
            await optimizer.add_constraint("test", 1.0, 0.0)

    @pytest.mark.asyncio
    async def test_check_constraints_satisfied(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Check constraints with valid policy should pass."""
        await optimizer.add_constraint("learning_rate", 0.0, 0.1)
        policy = PolicyCandidate(
            "test", (("learning_rate", 0.05),), 0.9, 0.1, 0
        )
        result = await optimizer.check_constraints(policy)
        assert result.feasible is True
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_check_constraints_violated(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Check constraints with violating policy should fail."""
        await optimizer.add_constraint("learning_rate", 0.0, 0.1)
        policy = PolicyCandidate(
            "test", (("learning_rate", 0.5),), 0.9, 0.1, 0
        )
        result = await optimizer.check_constraints(policy)
        assert result.feasible is False
        assert len(result.violations) > 0
        assert result.violations[0].violation_magnitude > 0

    @pytest.mark.asyncio
    async def test_check_constraints_no_constraints(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Check constraints with no constraints should raise."""
        policy = PolicyCandidate(
            "test", (("learning_rate", 0.05),), 0.9, 0.1, 0
        )
        with pytest.raises(
            ConstraintOptimizationError, match="no constraints"
        ):
            await optimizer.check_constraints(policy)

    @pytest.mark.asyncio
    async def test_check_constraints_missing_param(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Check constraints with missing parameter should raise."""
        await optimizer.add_constraint("missing_param", 0.0, 1.0)
        policy = PolicyCandidate(
            "test", (("other_param", 0.5),), 0.9, 0.1, 0
        )
        with pytest.raises(
            ConstraintOptimizationError, match="not found"
        ):
            await optimizer.check_constraints(policy)

    @pytest.mark.asyncio
    async def test_project_feasible(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Project feasible should clamp parameters to valid range."""
        await optimizer.add_constraint("learning_rate", 0.0, 0.1)
        policy = PolicyCandidate(
            "test", (("learning_rate", 0.5), ("other", 1.0)), 0.9, 0.1, 0
        )
        projected = await optimizer.project_feasible(policy)
        param_dict = dict(projected.parameters)
        assert param_dict["learning_rate"] == 0.1
        assert param_dict["other"] == 1.0  # unchanged

    @pytest.mark.asyncio
    async def test_project_feasible_already_valid(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Project feasible should not alter valid parameters."""
        await optimizer.add_constraint("lr", 0.0, 1.0)
        policy = PolicyCandidate(
            "test", (("lr", 0.5),), 0.9, 0.1, 0
        )
        projected = await optimizer.project_feasible(policy)
        param_dict = dict(projected.parameters)
        assert param_dict["lr"] == 0.5

    @pytest.mark.asyncio
    async def test_project_feasible_no_constraints(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Project feasible with no constraints should raise."""
        policy = PolicyCandidate(
            "test", (("lr", 0.5),), 0.9, 0.1, 0
        )
        with pytest.raises(
            ConstraintOptimizationError, match="no constraints"
        ):
            await optimizer.project_feasible(policy)

    @pytest.mark.asyncio
    async def test_constrained_search(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Constrained search should return a valid search result."""
        search_config = SearchConfig(
            max_iterations=5, exploration_rate=0.0
        )
        constraint_config = ConstraintConfig(
            constraints=("learning_rate",),
            constraint_bounds=((0.0, 0.1),),
        )
        result = await optimizer.constrained_search(
            search_config, constraint_config
        )
        assert isinstance(result, SearchResult)
        assert len(result.candidates) > 0
        # All params should be projected to feasible
        for candidate in result.candidates:
            param_dict = dict(candidate.parameters)
            if "learning_rate" in param_dict:
                assert param_dict["learning_rate"] <= 0.1
                assert param_dict["learning_rate"] >= 0.0

    @pytest.mark.asyncio
    async def test_constrained_search_mismatched_lengths(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Constrained search should reject mismatched lengths."""
        search_config = SearchConfig(max_iterations=3)
        constraint_config = ConstraintConfig(
            constraints=("lr", "bs"),
            constraint_bounds=((0.0, 0.1),),
        )
        with pytest.raises(
            ConstraintOptimizationError, match="same length"
        ):
            await optimizer.constrained_search(
                search_config, constraint_config
            )

    @pytest.mark.asyncio
    async def test_multiple_constraints(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Multiple constraints should all be enforced."""
        await optimizer.add_constraint("lr", 0.0, 0.1)
        await optimizer.add_constraint("bs", 16, 256)
        policy = PolicyCandidate(
            "test",
            (("lr", 0.5), ("bs", 512)),
            0.9, 0.1, 0,
        )
        result = await optimizer.check_constraints(policy)
        assert len(result.violations) == 2

    @pytest.mark.asyncio
    async def test_violation_magnitude_lower_bound(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Violation magnitude should be correct for lower bound."""
        await optimizer.add_constraint("x", 0.0, 1.0)
        policy = PolicyCandidate(
            "test", (("x", -0.5),), 0.9, 0.1, 0
        )
        result = await optimizer.check_constraints(policy)
        assert len(result.violations) == 1
        assert result.violations[0].violation_magnitude == 0.5

    @pytest.mark.asyncio
    async def test_violation_magnitude_upper_bound(
        self, optimizer: ConstrainedOptimizer
    ) -> None:
        """Violation magnitude should be correct for upper bound."""
        await optimizer.add_constraint("x", 0.0, 1.0)
        policy = PolicyCandidate(
            "test", (("x", 2.0),), 0.9, 0.1, 0
        )
        result = await optimizer.check_constraints(policy)
        assert len(result.violations) == 1
        assert result.violations[0].violation_magnitude == 1.0

    @pytest.mark.asyncio
    async def test_boundary_acceptable(self, optimizer: ConstrainedOptimizer) -> None:
        """Values exactly at boundary should be acceptable."""
        await optimizer.add_constraint("x", 0.0, 1.0)
        policy = PolicyCandidate(
            "test", (("x", 0.0),), 0.9, 0.1, 0
        )
        result = await optimizer.check_constraints(policy)
        assert result.feasible is True
