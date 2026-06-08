"""Comprehensive tests for GEPAOptimizer — gradient-free reflective prompt evolution."""

import time
from unittest.mock import MagicMock

import pytest

from lyra.rl_optimizer.gepa_optimizer import (
    EditType,
    EvolutionPhase,
    GEPAOptimizer,
    Gene,
    GeneEvaluator,
    SkillOptMutator,
    VariantResult,
)


# =============================================================================
# Tests: Gene
# =============================================================================


class TestGene:
    def test_empty_gene(self):
        g = Gene()
        assert g.matching_signals == ()
        assert g.summary == ""
        assert g.strategy_steps == ()
        assert g.avoid_cues == ()
        assert g.constraints == ()
        assert g.edit_history == ()

    def test_to_prompt_section_full(self):
        g = Gene(
            matching_signals=("signal1", "signal2"),
            summary="A test gene",
            strategy_steps=("step 1", "step 2"),
            avoid_cues=("bad pattern",),
            constraints=("constraint 1",),
        )
        section = g.to_prompt_section()
        assert "WHEN: signal1 | signal2" in section
        assert "SUMMARY: A test gene" in section
        assert "STEPS:" in section
        assert "  - step 1" in section
        assert "AVOID: bad pattern" in section
        assert "CONSTRAINTS: constraint 1" in section

    def test_to_prompt_section_empty(self):
        g = Gene()
        assert g.to_prompt_section() == ""

    def test_to_prompt_section_partial(self):
        g = Gene(summary="only summary", strategy_steps=("do x",))
        section = g.to_prompt_section()
        assert "SUMMARY: only summary" in section
        assert "STEPS:" in section
        assert "  - do x" in section
        assert "WHEN:" not in section
        assert "AVOID:" not in section
        assert "CONSTRAINTS:" not in section

    def test_with_edit_appends_history(self):
        g = Gene(summary="original")
        g2 = g.with_edit("first edit")
        assert len(g2.edit_history) == 1
        assert g2.edit_history[0] == "first edit"
        # Original is unchanged
        assert len(g.edit_history) == 0

    def test_with_edit_preserves_fields(self):
        g = Gene(
            matching_signals=("sig",),
            summary="s",
            strategy_steps=("step",),
            avoid_cues=("avoid",),
            constraints=("cstr",),
        )
        g2 = g.with_edit("edit")
        assert g2.matching_signals == ("sig",)
        assert g2.summary == "s"
        assert g2.strategy_steps == ("step",)
        assert g2.avoid_cues == ("avoid",)
        assert g2.constraints == ("cstr",)

    def test_with_edit_chaining(self):
        g = Gene()
        g1 = g.with_edit("edit 1")
        g2 = g1.with_edit("edit 2")
        assert g2.edit_history == ("edit 1", "edit 2")


# =============================================================================
# Tests: VariantResult
# =============================================================================


class TestVariantResult:
    def test_passes_validation_below_threshold(self):
        result = VariantResult(
            gene=Gene(), variant_id="v1", score=0.8, regression=0.005,
            cost_usd=0.0, latency_ms=0.0,
        )
        assert result.passes_validation is True

    def test_passes_validation_at_threshold(self):
        result = VariantResult(
            gene=Gene(), variant_id="v2", score=0.8, regression=0.01,
            cost_usd=0.0, latency_ms=0.0,
        )
        assert result.passes_validation is True

    def test_passes_validation_above_threshold(self):
        result = VariantResult(
            gene=Gene(), variant_id="v3", score=0.8, regression=0.02,
            cost_usd=0.0, latency_ms=0.0,
        )
        assert result.passes_validation is False

    def test_negative_regression_passes(self):
        result = VariantResult(
            gene=Gene(), variant_id="v4", score=0.8, regression=-0.05,
            cost_usd=0.0, latency_ms=0.0,
        )
        assert result.passes_validation is True

    def test_metadata_defaults_to_empty(self):
        result = VariantResult(
            gene=Gene(), variant_id="v5", score=0.5, regression=0.0,
            cost_usd=0.0, latency_ms=0.0,
        )
        assert result.metadata == {}


# =============================================================================
# Tests: EditType
# =============================================================================


class TestEditType:
    def test_values(self):
        assert EditType.PROMPT_REWRITE.value == "prompt_rewrite"
        assert EditType.STRATEGY_UPDATE.value == "strategy_update"
        assert EditType.CONSTRAINT_ADD.value == "constraint_add"
        assert EditType.CONSTRAINT_REMOVE.value == "constraint_remove"
        assert EditType.PARAMETER_TUNE.value == "parameter_tune"
        assert EditType.TOOL_ROUTINE_CHANGE.value == "tool_routine_change"
        assert EditType.MEMORY_UPDATE.value == "memory_update"

    def test_members(self):
        assert len(EditType) == 7


# =============================================================================
# Tests: EvolutionPhase
# =============================================================================


class TestEvolutionPhase:
    def test_values(self):
        assert EvolutionPhase.INITIALISE.value == "initialise"
        assert EvolutionPhase.COMPLETED.value == "completed"
        assert EvolutionPhase.FAILED.value == "failed"

    def test_members(self):
        assert len(EvolutionPhase) == 9


# =============================================================================
# Tests: SkillOptMutator
# =============================================================================


class TestSkillOptMutator:
    def test_default_budget(self):
        m = SkillOptMutator()
        assert m.initial_budget == 4
        assert m.final_budget == 2
        assert m.total_steps == 8
        assert m.budget == 4

    def test_budget_at_step_start(self):
        m = SkillOptMutator(initial_budget=4, final_budget=2, total_steps=8)
        assert m.budget_at_step(0) == 4  # initial budget

    def test_budget_at_step_middle(self):
        m = SkillOptMutator(initial_budget=4, final_budget=2, total_steps=8)
        budget = m.budget_at_step(4)
        assert 2 <= budget <= 4  # Should have decayed somewhat

    def test_budget_at_step_end(self):
        m = SkillOptMutator(initial_budget=4, final_budget=2, total_steps=8)
        assert m.budget_at_step(7) == 2  # final budget

    def test_budget_at_step_single_step(self):
        m = SkillOptMutator(initial_budget=4, final_budget=2, total_steps=1)
        assert m.budget_at_step(0) == 4
        assert m.budget_at_step(5) == 4  # clamped

    def test_mark_rejected_stores_edit(self):
        m = SkillOptMutator()
        m.mark_rejected("bad edit")
        assert "bad edit" in m._rejected_edits

    def test_is_rejected(self):
        m = SkillOptMutator()
        assert m.is_rejected("new edit") is False
        m.mark_rejected("bad edit")
        assert m.is_rejected("bad edit") is True

    def test_mutate_with_generate_fn(self):
        m = SkillOptMutator()
        gene = Gene(summary="original")
        generate_fn = MagicMock(return_value=Gene(summary="mutated"))
        result = m.mutate(gene, step=1, generate_fn=generate_fn)
        assert result.summary == "mutated"
        generate_fn.assert_called_once_with(gene, m.budget_at_step(1), 1)

    def test_mutate_without_generate_fn_random(self):
        m = SkillOptMutator()
        gene = Gene(matching_signals=("a", "b", "c"), summary="original")
        result = m.mutate(gene, step=1)
        # Without generate_fn, may do nothing if random doesn't hit
        assert isinstance(result, Gene)

    def test_mutate_single_signal_no_random(self):
        m = SkillOptMutator()
        gene = Gene(matching_signals=("only",))
        result = m.mutate(gene, step=1)
        assert result.matching_signals == ("only",)  # unchanged, no rotation possible

    def test_mutate_empty_gene(self):
        m = SkillOptMutator()
        gene = Gene()
        result = m.mutate(gene, step=1)
        assert result is gene  # returns same gene


# =============================================================================
# Tests: GeneEvaluator
# =============================================================================


class TestGeneEvaluator:
    def test_default_init(self):
        e = GeneEvaluator()
        assert e._tasks == []
        assert e.is_frozen is False

    def test_freeze(self):
        e = GeneEvaluator([{"query": "q1", "expected": "e1"}])
        e.freeze()
        assert e.is_frozen is True

    def test_add_task(self):
        e = GeneEvaluator()
        e.add_task({"query": "q1", "expected": "e1"})
        assert len(e._tasks) == 1

    def test_add_task_frozen_raises(self):
        e = GeneEvaluator()
        e.freeze()
        with pytest.raises(RuntimeError, match="Cannot add tasks to a frozen evaluator"):
            e.add_task({"query": "q1", "expected": "e1"})

    def test_evaluate_cold_start(self):
        e = GeneEvaluator()
        result = e.evaluate(Gene())
        assert result.score == 0.5
        assert result.regression == 0.0
        assert result.cost_usd == 0.0
        assert "cold_start" in result.metadata.get("source", "")

    def test_evaluate_with_tasks(self):
        e = GeneEvaluator([
            {"query": "q1", "expected": "e1", "weight": 1.0},
            {"query": "q2", "expected": "e2", "weight": 2.0},
        ])
        result = e.evaluate(Gene(summary="test"))
        assert 0.5 <= result.score <= 0.9
        assert result.cost_usd > 0
        assert result.latency_ms > 0

    def test_evaluate_includes_gene(self):
        gene = Gene(summary="test gene")
        e = GeneEvaluator([{"query": "q1", "expected": "e1"}])
        result = e.evaluate(gene)
        assert result.gene is gene

    def test_score_task_returns_between_05_and_09(self):
        e = GeneEvaluator()
        score = e._score_task(Gene(), {"query": "q", "expected": "e"})
        assert 0.5 <= score <= 0.9


# =============================================================================
# Tests: GEPAOptimizer
# =============================================================================


class TestGEPAOptimizer:
    def test_default_init(self):
        opt = GEPAOptimizer()
        assert opt.phase == EvolutionPhase.INITIALISE
        assert opt.generation == 0
        assert opt.variants_per_generation == 4
        assert opt.max_generations == 10
        assert opt._best_score == 0.0
        assert opt._history == []

    def test_custom_init(self):
        opt = GEPAOptimizer(
            variants_per_generation=2,
            max_generations=5,
            regression_threshold=0.05,
        )
        assert opt.variants_per_generation == 2
        assert opt.max_generations == 5
        assert opt.regression_threshold == 0.05

    def test_set_mutate_fn(self):
        opt = GEPAOptimizer()
        fn = MagicMock()
        opt.set_mutate_fn(fn)
        assert opt._mutate_fn is fn

    def test_set_evaluate_fn(self):
        opt = GEPAOptimizer()
        fn = MagicMock()
        opt.set_evaluate_fn(fn)
        assert opt._evaluate_fn is fn

    def test_run_generation_reaches_max(self):
        opt = GEPAOptimizer(max_generations=0)
        result = opt.run_generation()
        assert result is None
        assert opt.phase == EvolutionPhase.COMPLETED

    def test_run_generation_no_variants_pass(self):
        """When evaluation returns scores all below baseline, no variant passes."""
        opt = GEPAOptimizer(
            variants_per_generation=2,
            max_generations=5,
            incumbent=Gene(summary="incumbent"),
        )
        opt._best_score = 0.9  # high baseline

        # Evaluator returns low scores
        evaluator = MagicMock()
        evaluator.evaluate.return_value = VariantResult(
            gene=Gene(summary="variant"),
            variant_id="test",
            score=0.3,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )
        opt.evaluator = evaluator

        result = opt.run_generation()
        assert result is None  # no variant passes validation
        assert opt.phase == EvolutionPhase.MUTATE

    def test_run_generation_selects_winner(self):
        opt = GEPAOptimizer(
            variants_per_generation=3,
            max_generations=5,
        )

        # Make mutator return a clear variant with high score
        mutator = MagicMock()
        mutator.mutate.return_value = Gene(summary="mutated", strategy_steps=("step",))
        mutator.mark_rejected = MagicMock()
        mutator.budget_at_step = MagicMock(return_value=3)

        evaluator = MagicMock()
        evaluator.evaluate.return_value = VariantResult(
            gene=Gene(summary="mutated", strategy_steps=("step",)),
            variant_id="test",
            score=0.85,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )

        opt.mutator = mutator
        opt.evaluator = evaluator

        result = opt.run_generation()
        assert result is not None
        assert opt.generation == 1
        assert opt.phase == EvolutionPhase.MUTATE

    def test_run_generation_promotes_winner(self):
        opt = GEPAOptimizer(
            variants_per_generation=2,
            max_generations=5,
            incumbent=Gene(summary="incumbent"),
        )
        opt._best_score = 0.5

        mutator = MagicMock()
        mutator.mutate.return_value = Gene(summary="winner")
        mutator.mark_rejected = MagicMock()
        mutator.budget_at_step = MagicMock(return_value=3)

        evaluator = MagicMock()
        evaluator.evaluate.return_value = VariantResult(
            gene=Gene(summary="winner"),
            variant_id="w1",
            score=0.9,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )

        opt.mutator = mutator
        opt.evaluator = evaluator

        result = opt.run_generation()
        assert result is not None
        assert opt.incumbent.summary == "winner"
        assert opt._best_score == 0.9
        assert len(opt._history) == 1

    def test_run_many_generations(self):
        opt = GEPAOptimizer(
            variants_per_generation=2,
            max_generations=3,
        )

        mutator = MagicMock()
        mutator.mutate.return_value = Gene(summary="mutated")
        mutator.mark_rejected = MagicMock()
        mutator.budget_at_step = MagicMock(return_value=3)

        evaluator = MagicMock()
        evaluator.evaluate.return_value = VariantResult(
            gene=Gene(summary="mutated"),
            variant_id="v",
            score=0.75,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )

        opt.mutator = mutator
        opt.evaluator = evaluator

        results = opt.run(steps=3)
        assert len(results) == 3
        assert opt.phase == EvolutionPhase.COMPLETED

    def test_run_default_steps(self):
        opt = GEPAOptimizer(
            max_generations=2,
            variants_per_generation=1,
        )
        opt.evaluator.evaluate = MagicMock(return_value=VariantResult(
            gene=Gene(), variant_id="v", score=0.7, regression=0.0,
            cost_usd=0.0, latency_ms=0.0,
        ))
        opt.mutator.mutate = MagicMock(return_value=Gene(summary="x"))
        results = opt.run()
        assert len(results) == 2

    def test_properties(self):
        opt = GEPAOptimizer()
        assert opt.best_score == 0.0
        assert opt.iteration_cost == 0.0
        assert opt.generation_count == 0
        assert opt.history == []

    def test_to_dict(self):
        opt = GEPAOptimizer()
        d = opt.to_dict()
        assert d["phase"] == "initialise"
        assert d["generation"] == 0
        assert d["best_score"] == 0.0
        assert d["max_generations"] == 10
        assert "incumbent" in d
        assert d["incumbent"]["summary"] == ""

    def test_to_dict_after_run(self):
        opt = GEPAOptimizer(
            max_generations=1,
            variants_per_generation=1,
        )
        mutator = MagicMock()
        mutator.mutate.return_value = Gene(summary="post-run")
        mutator.mark_rejected = MagicMock()
        mutator.budget_at_step = MagicMock(return_value=3)
        opt.mutator = mutator

        evaluator = MagicMock()
        evaluator.evaluate.return_value = VariantResult(
            gene=Gene(summary="post-run"),
            variant_id="pr",
            score=0.8,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )
        opt.evaluator = evaluator

        opt.run()
        d = opt.to_dict()
        assert d["generation"] == 1
        assert d["best_score"] > 0
        assert d["incumbent"]["summary"] == "post-run"
        assert d["history_count"] == 1


# =============================================================================
# Tests: Edge cases
# =============================================================================


class TestEdgeCases:
    def test_optimizer_with_custom_mutate_fn_is_called(self):
        opt = GEPAOptimizer(
            max_generations=1,
            variants_per_generation=2,
        )
        mutate_fn = MagicMock(return_value=Gene(summary="custom"))
        opt.set_mutate_fn(mutate_fn)
        opt.run_generation()
        mutate_fn.assert_called()

    def test_optimizer_with_custom_evaluate_fn(self):
        opt = GEPAOptimizer(
            max_generations=1,
            variants_per_generation=1,
        )
        evaluate_fn = MagicMock(return_value=VariantResult(
            gene=Gene(summary="custom"),
            variant_id="ce",
            score=0.85,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        ))
        opt.set_evaluate_fn(evaluate_fn)
        result = opt.run_generation()
        assert result is not None
        evaluate_fn.assert_called()

    def test_history_tracks_generations(self):
        opt = GEPAOptimizer(
            max_generations=2,
            variants_per_generation=1,
        )
        mutator = MagicMock()
        mutator.mutate.return_value = Gene(summary="h")
        mutator.mark_rejected = MagicMock()
        mutator.budget_at_step = MagicMock(return_value=3)
        opt.mutator = mutator
        opt.evaluator.evaluate = MagicMock(return_value=VariantResult(
            gene=Gene(summary="h"), variant_id="vh", score=0.8, regression=0.0,
            cost_usd=0.0, latency_ms=0.0,
        ))
        opt.run(steps=2)
        assert len(opt.history) == 2
        gen, gene, result = opt.history[0]
        assert gen == 1
        assert isinstance(gene, Gene)
        assert isinstance(result, VariantResult)

    def test_rejected_edit_buffer_used(self):
        opt = GEPAOptimizer(
            max_generations=1,
            variants_per_generation=1,
        )
        # All variants fail validation gate
        opt._best_score = 0.9
        opt.evaluator.evaluate = MagicMock(return_value=VariantResult(
            gene=Gene(summary="fail", edit_history=("bad edit",)),
            variant_id="rej",
            score=0.3,
            regression=0.0,
            cost_usd=0.0,
            latency_ms=0.0,
        ))
        opt.run_generation()
        assert opt.mutator.is_rejected("bad edit")
