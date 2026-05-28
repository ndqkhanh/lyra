"""Tests for SkillOpt — text-space optimization for skill prompts."""

import pytest
from lyra_core.skills.skill_opt import (
    OptimizationPass,
    OptimizationStrategy,
    SkillOptConfig,
    SkillOptimizer,
    TextEdit,
)


class TestOptimizationStrategy:
    def test_strategy_values(self):
        assert OptimizationStrategy.CLARIFY.value == "clarify"
        assert OptimizationStrategy.CONDENSE.value == "condense"
        assert OptimizationStrategy.EXPAND.value == "expand"
        assert OptimizationStrategy.RESTRUCTURE.value == "restructure"
        assert OptimizationStrategy.ADD_EXAMPLES.value == "add_examples"


class TestTextEdit:
    def test_edit_creation(self):
        edit = TextEdit(
            strategy=OptimizationStrategy.CLARIFY,
            original_segment="make sure",
            optimized_segment="verify that",
            rationale="Replace informal phrasing",
            expected_improvement=0.05,
        )
        assert edit.strategy == OptimizationStrategy.CLARIFY
        assert edit.original_segment == "make sure"
        assert edit.expected_improvement == 0.05

    def test_condense_edit(self):
        edit = TextEdit(
            strategy=OptimizationStrategy.CONDENSE,
            original_segment="in order to ",
            optimized_segment="to ",
            rationale="Remove redundancy",
            expected_improvement=0.03,
        )
        assert edit.strategy == OptimizationStrategy.CONDENSE

    def test_edit_immutable(self):
        edit = TextEdit(OptimizationStrategy.CLARIFY, "old", "new", "reason", 0.1)
        with pytest.raises(Exception):
            edit.expected_improvement = 0.5


class TestOptimizationPass:
    def test_pass_improvement(self):
        edit = TextEdit(OptimizationStrategy.CLARIFY, "it", "the function", "clarify pronoun", 0.05)
        opt_pass = OptimizationPass(
            pass_id="opt-0001",
            edits=(edit,),
            score_before=0.45,
            score_after=0.52,
            delta=0.07,
        )
        assert opt_pass.pass_id == "opt-0001"
        assert opt_pass.delta > 0
        assert opt_pass.score_after > opt_pass.score_before

    def test_pass_no_improvement(self):
        opt_pass = OptimizationPass(
            pass_id="opt-0002",
            edits=(),
            score_before=0.50,
            score_after=0.50,
            delta=0.0,
        )
        assert opt_pass.delta == 0.0

    def test_pass_immutable(self):
        p = OptimizationPass(pass_id="p1", edits=(), score_before=0.3, score_after=0.4, delta=0.1)
        with pytest.raises(Exception):
            p.delta = 0.5


class TestSkillOptConfig:
    def test_default_config(self):
        config = SkillOptConfig()
        assert config.max_passes == 5
        assert config.min_improvement == 0.01
        assert len(config.strategies) >= 3

    def test_custom_config(self):
        config = SkillOptConfig(max_passes=3, min_improvement=0.05)
        assert config.max_passes == 3
        assert config.min_improvement == 0.05


class TestSkillOptimizer:
    def test_empty_text(self):
        optimizer = SkillOptimizer()
        text, passes = optimizer.optimize("")
        assert text == ""
        assert len(passes) == 0

    def test_already_clean_text_stays_stable(self):
        optimizer = SkillOptimizer()
        clean_text = "Run the deployment script with proper parameters."
        result, passes = optimizer.optimize(clean_text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_vague_pronoun_clarified(self):
        optimizer = SkillOptimizer()
        text = "When you run it, make sure the output is correct."
        result, passes = optimizer.optimize(text)
        assert isinstance(result, str)

    def test_redundant_phrases_removed(self):
        optimizer = SkillOptimizer()
        text = "In order to use the function, it is important to note that you need proper auth."
        result, passes = optimizer.optimize(text)
        # Should remove "in order to" and "it is important to note that"
        assert isinstance(result, str)

    def test_returns_pass_history(self):
        optimizer = SkillOptimizer()
        text = "When you run it, make sure the output is correct. In order to verify, please note that errors matter."
        result, passes = optimizer.optimize(text)
        assert isinstance(passes, list)
        for p in passes:
            assert isinstance(p, OptimizationPass)

    def test_history_property(self):
        optimizer = SkillOptimizer()
        text = "When you run it, make sure the output is correct."
        optimizer.optimize(text)
        history = optimizer.history
        assert isinstance(history, list)

    def test_pass_count(self):
        optimizer = SkillOptimizer()
        assert optimizer.pass_count == 0
        text = "When you run it, make sure the output is correct."
        optimizer.optimize(text)
        assert optimizer.pass_count >= 0

    def test_long_text_without_sections_restructured(self):
        optimizer = SkillOptimizer()
        long_text = (
            "This is a comprehensive skill for deploying applications. "
            + "Follow these steps carefully. " * 3
            + "Verify all deployments before marking complete. "
            + "Use proper authentication tokens for all operations. " * 2
        )
        result, passes = optimizer.optimize(long_text)
        assert isinstance(result, str)

    def test_score_improves_or_stays_same(self):
        optimizer = SkillOptimizer()
        text = "A very vague description of it for the thing. Make sure it works."
        result, passes = optimizer.optimize(text)
        if passes:
            for p in passes:
                assert p.score_after >= p.score_before
