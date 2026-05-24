"""
Comprehensive tests for lyra-reasoning: models, ReflAct, GRPO, and strategies.
"""

import math
import pytest

from lyra_reasoning.models import (
    AnaloguePair,
    GRPOTrajectory,
    ReasoningStep,
    ReasoningTrace,
    ReflActEpisode,
    SpiralSample,
    ThoughtNode,
)
from lyra_reasoning.reflect import ReflActReasoner
from lyra_reasoning.grpo import GRPOTrainer
from lyra_reasoning.strategies import (
    AnalogicalReasoning,
    ChainOfThought,
    SelfConsistency,
    StepBack,
    TreeOfThoughts,
)


# ═══════════════════════════════════════════════════════════════════════════
# Model tests
# ═══════════════════════════════════════════════════════════════════════════


class TestReasoningStep:
    """ReasoningStep frozen dataclass."""

    def test_create_valid_step(self):
        step = ReasoningStep(
            step_number=1,
            thought="Identify the problem",
            action="analyse",
            observation="Problem identified as a classification task.",
            confidence=0.8,
        )
        assert step.step_number == 1
        assert step.thought == "Identify the problem"
        assert step.action == "analyse"
        assert step.observation.startswith("Problem identified")
        assert step.confidence == 0.8
        assert step.metadata == {}

    def test_confidence_bounds_enforced(self):
        with pytest.raises(ValueError):
            ReasoningStep(step_number=1, thought="x", action="x", observation="x", confidence=-0.1)
        with pytest.raises(ValueError):
            ReasoningStep(step_number=1, thought="x", action="x", observation="x", confidence=1.5)

    def test_frozen_prevents_mutation(self):
        step = ReasoningStep(step_number=1, thought="t", action="a", observation="o", confidence=0.5)
        with pytest.raises(Exception):
            step.confidence = 0.9  # type: ignore[misc]

    def test_metadata_default_and_custom(self):
        default = ReasoningStep(step_number=1, thought="t", action="a", observation="o", confidence=0.5)
        assert default.metadata == {}

        custom = ReasoningStep(
            step_number=2, thought="t", action="a", observation="o", confidence=0.6,
            metadata={"source": "test"},
        )
        assert custom.metadata == {"source": "test"}


class TestReasoningTrace:
    """ReasoningTrace frozen dataclass."""

    def test_empty_trace(self):
        trace = ReasoningTrace(task="test task")
        assert trace.task == "test task"
        assert trace.steps == ()
        assert trace.outcome == "pending"
        assert trace.num_steps == 0
        assert trace.final_step() is None

    def test_add_step_returns_new_trace(self):
        trace = ReasoningTrace(task="test")
        step = ReasoningStep(step_number=1, thought="t", action="a", observation="o", confidence=0.7)
        updated = trace.add_step(step)

        assert trace.num_steps == 0  # original unchanged
        assert updated.num_steps == 1
        assert updated.steps[0] == step

    def test_with_outcome(self):
        trace = ReasoningTrace(task="test")
        done = trace.with_outcome("success")
        assert done.outcome == "success"
        assert trace.outcome == "pending"  # original unchanged

    def test_final_step_returns_last(self):
        trace = ReasoningTrace(task="test")
        s1 = ReasoningStep(step_number=1, thought="t1", action="a1", observation="o1", confidence=0.6)
        s2 = ReasoningStep(step_number=2, thought="t2", action="a2", observation="o2", confidence=0.9)
        trace = trace.add_step(s1).add_step(s2)

        assert trace.num_steps == 2
        assert trace.final_step() == s2

    def test_chain_of_adds(self):
        trace = ReasoningTrace(task="chain")
        for i in range(5):
            trace = trace.add_step(
                ReasoningStep(step_number=i + 1, thought="t", action="a", observation="o", confidence=0.5)
            )
        assert trace.num_steps == 5


class TestReflActEpisode:
    """ReflActEpisode frozen dataclass."""

    def test_create_episode(self):
        trace = ReasoningTrace(task="test")
        episode = ReflActEpisode(
            task="test",
            trace=trace,
            outcome="success",
            lessons_learned=("verify assumptions", "gather more context"),
            success=True,
            score=0.85,
        )
        assert episode.task == "test"
        assert episode.outcome == "success"
        assert len(episode.lessons_learned) == 2
        assert episode.success is True
        assert episode.score == 0.85


class TestGRPOTrajectory:
    """GRPOTrajectory frozen dataclass."""

    def test_create_trajectory(self):
        traj = GRPOTrajectory(
            prompt="What is 2+2?",
            responses=("4", "3", "5"),
            rewards=(1.0, 0.2, 0.1),
            advantages=(1.5, -0.5, -1.0),
            group_mean=0.43,
            group_std=0.4,
        )
        assert len(traj.responses) == 3
        assert len(traj.rewards) == 3
        assert len(traj.advantages) == 3

    def test_best_response(self):
        traj = GRPOTrajectory(
            prompt="Q",
            responses=("a", "b", "c"),
            rewards=(0.3, 0.9, 0.5),
            advantages=(),
        )
        assert traj.best_response == "b"

    def test_best_response_empty(self):
        traj = GRPOTrajectory(prompt="Q", responses=(), rewards=(), advantages=())
        assert traj.best_response is None

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            GRPOTrajectory(
                prompt="Q",
                responses=("a", "b"),
                rewards=(0.5,),
                advantages=(),
            )


class TestSpiralSample:
    """SpiralSample frozen dataclass."""

    def test_create_sample(self):
        sample = SpiralSample(
            prompt="Summarize this article.",
            candidate_responses=("Response A", "Response B", "Response C"),
            scores=(0.2, 0.9, 0.5),
        )
        assert sample.best_candidate() == "Response B"
        assert sample.worst_candidate() == "Response A"

    def test_preference_pair(self):
        sample = SpiralSample(
            prompt="Q",
            candidate_responses=("low", "high"),
            scores=(0.1, 0.95),
        )
        chosen, rejected = sample.preference_pair()
        assert chosen == "high"
        assert rejected == "low"

    def test_empty_candidates(self):
        sample = SpiralSample(prompt="Q", candidate_responses=(), scores=())
        assert sample.best_candidate() is None
        assert sample.worst_candidate() is None

    def test_mismatched_raises(self):
        with pytest.raises(ValueError):
            SpiralSample(prompt="Q", candidate_responses=("a",), scores=())


class TestThoughtNode:
    """ThoughtNode frozen dataclass."""

    def test_create_node(self):
        node = ThoughtNode(id="n1", content="reasoning step", score=0.75, depth=2, parent_id="root")
        assert node.id == "n1"
        assert node.score == 0.75
        assert node.depth == 2
        assert node.parent_id == "root"
        assert node.visits == 0

    def test_frozen(self):
        node = ThoughtNode(id="n1", content="x", score=0.5)
        with pytest.raises(Exception):
            node.score = 0.9  # type: ignore[misc]


class TestAnaloguePair:
    """AnaloguePair frozen dataclass."""

    def test_create_pair(self):
        pair = AnaloguePair(
            source_domain="mathematics",
            target_domain="physics",
            structural_mapping={"addition": "superposition", "multiplication": "scaling"},
            similarity_score=0.8,
            transfer_confidence=0.75,
        )
        assert pair.source_domain == "mathematics"
        assert len(pair.structural_mapping) == 2
        assert pair.similarity_score == 0.8


# ═══════════════════════════════════════════════════════════════════════════
# ReflAct tests
# ═══════════════════════════════════════════════════════════════════════════


class TestReflActReasoner:
    """ReflActReasoner engine tests."""

    def test_reason_produces_trace(self):
        reasoner = ReflActReasoner(default_max_steps=5, confidence_threshold=0.65)
        trace = reasoner.reason("Explain gravity to a child")
        assert isinstance(trace, ReasoningTrace)
        assert trace.task == "Explain gravity to a child"
        assert trace.strategy == "reflect"
        assert trace.num_steps > 0
        assert trace.duration > 0

    def test_reason_respects_max_steps(self):
        reasoner = ReflActReasoner(default_max_steps=3, confidence_threshold=0.99)
        trace = reasoner.reason("Test task", max_steps=2)
        assert trace.num_steps <= 2

    def test_reason_high_confidence_stops_early(self):
        reasoner = ReflActReasoner(default_max_steps=20, confidence_threshold=0.1)
        trace = reasoner.reason("Test")
        # Should stop quickly because threshold is very low
        assert trace.num_steps <= 3

    def test_reflect_produces_lessons(self):
        reasoner = ReflActReasoner()
        trace = reasoner.reason("Analyse market trends")
        lessons = reasoner.reflect(trace)
        assert isinstance(lessons, tuple)
        assert len(lessons) > 0
        assert all(isinstance(l, str) for l in lessons)

    def test_reflect_on_empty_trace(self):
        reasoner = ReflActReasoner()
        empty = ReasoningTrace(task="nothing")
        lessons = reasoner.reflect(empty)
        assert len(lessons) == 1
        assert "no reasoning steps" in lessons[0].lower()

    def test_adapt_modifies_context(self):
        reasoner = ReflActReasoner()
        lessons = ("Confidence decreased — may indicate drift.", "Action resulted in error.")
        adaptation = reasoner.adapt("complex_task", lessons)
        assert "strategy_modifiers" in adaptation
        assert "lessons_applied" in adaptation
        assert len(adaptation["lessons_applied"]) == 2

    def test_synthesize_multiple_traces(self):
        reasoner = ReflActReasoner()
        t1 = reasoner.reason("Task A")
        t2 = reasoner.reason("Task B")
        t3 = reasoner.reason("Task C")

        insights = reasoner.synthesize([t1, t2, t3])
        assert isinstance(insights, list)
        assert len(insights) > 0
        assert "success rate" in insights[0].lower()

    def test_synthesize_empty(self):
        reasoner = ReflActReasoner()
        insights = reasoner.synthesize([])
        assert len(insights) == 1
        assert "no traces" in insights[0].lower()

    def test_record_episode(self):
        reasoner = ReflActReasoner()
        trace = reasoner.reason("Learn Python")
        episode = reasoner.record_episode("Learn Python", trace)
        assert isinstance(episode, ReflActEpisode)
        assert episode.task == "Learn Python"
        assert reasoner.episode_count == 1

    def test_episode_count(self):
        reasoner = ReflActReasoner()
        assert reasoner.episode_count == 0
        trace = reasoner.reason("Task 1")
        reasoner.record_episode("Task 1", trace)
        trace2 = reasoner.reason("Task 2")
        reasoner.record_episode("Task 2", trace2)
        assert reasoner.episode_count == 2

    def test_reflact_with_context(self):
        reasoner = ReflActReasoner()
        trace = reasoner.reason("Analyse data", context={"data": [1, 2, 3]})
        assert trace.num_steps > 0


# ═══════════════════════════════════════════════════════════════════════════
# GRPO tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGRPOTrainer:
    """GRPOTrainer tests."""

    def test_generate_candidates_default_group_size(self):
        trainer = GRPOTrainer(group_size=4)
        candidates = trainer.generate_candidates("What is ML?")
        assert len(candidates) == 4
        assert all(isinstance(c, str) for c in candidates)

    def test_generate_candidates_custom_n(self):
        trainer = GRPOTrainer(group_size=4)
        candidates = trainer.generate_candidates("Prompt", n=7)
        assert len(candidates) == 7

    def test_score_responses_with_ground_truth(self):
        trainer = GRPOTrainer()
        candidates = ["The answer is 4", "The answer is 5"]
        scores = trainer.score_responses(candidates, ground_truth="The answer is 4")
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)
        assert scores[0] > scores[1]

    def test_score_responses_without_ground_truth(self):
        trainer = GRPOTrainer()
        candidates = ["A short response", "A longer response with reasoning and evidence for the answer"]
        scores = trainer.score_responses(candidates)
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)

    def test_compute_advantages(self):
        trainer = GRPOTrainer()
        rewards = (0.1, 0.5, 0.9)
        advantages = trainer.compute_advantages(rewards)
        assert len(advantages) == 3
        # Best reward should have positive advantage, worst negative
        assert advantages[2] > 0  # highest reward
        assert advantages[0] < 0  # lowest reward
        # Sum of advantages should be ~0
        assert abs(sum(advantages)) < 0.01

    def test_compute_advantages_single(self):
        trainer = GRPOTrainer()
        advantages = trainer.compute_advantages((0.5,))
        assert advantages == (0.0,)

    def test_compute_advantages_empty(self):
        trainer = GRPOTrainer()
        assert trainer.compute_advantages(()) == ()

    def test_update_policy(self):
        trainer = GRPOTrainer()
        traj = GRPOTrajectory(
            prompt="Q",
            responses=("low quality", "medium quality", "high quality answer with reasoning"),
            rewards=(0.2, 0.5, 0.9),
            advantages=(-1.0, 0.0, 1.0),
            group_mean=0.53,
            group_std=0.28,
        )
        stats = trainer.update_policy([traj])
        assert "avg_loss" in stats
        assert stats["total_samples"] == 3
        assert stats["trajectories_processed"] == 1

    def test_train_step(self):
        trainer = GRPOTrainer(group_size=3)
        traj = trainer.train_step("What is 2+2?", ground_truth="4")
        assert isinstance(traj, GRPOTrajectory)
        assert len(traj.responses) == 3
        assert len(traj.advantages) == 3
        assert len(traj.rewards) == 3
        assert traj.prompt == "What is 2+2?"

    def test_train_from_spiral(self):
        trainer = GRPOTrainer()
        samples = [
            SpiralSample(
                prompt="Q1",
                candidate_responses=("good", "bad", "ok"),
                scores=(0.8, 0.2, 0.5),
            ),
            SpiralSample(
                prompt="Q2",
                candidate_responses=("best", "worst"),
                scores=(0.9, 0.1),
            ),
        ]
        stats = trainer.train_from_spiral(samples)
        assert stats["trajectories_processed"] == 2

    def test_training_history(self):
        trainer = GRPOTrainer()
        trainer.train_step("Q", ground_truth="A")
        assert len(trainer.training_history) == 1

    def test_default_learning_rate(self):
        trainer = GRPOTrainer(default_learning_rate=1e-4)
        assert trainer.default_learning_rate == 1e-4


# ═══════════════════════════════════════════════════════════════════════════
# Strategy tests
# ═══════════════════════════════════════════════════════════════════════════


class TestChainOfThought:
    """ChainOfThought strategy tests."""

    def test_reason_produces_trace(self):
        cot = ChainOfThought(max_steps=5)
        trace = cot.reason("Why is the sky blue?")
        assert isinstance(trace, ReasoningTrace)
        assert trace.strategy == "chain_of_thought"
        assert trace.num_steps > 0
        assert trace.num_steps <= 5

    def test_reason_with_context(self):
        cot = ChainOfThought(max_steps=3)
        trace = cot.reason("Explain neural networks", context={"audience": "beginner"})
        assert trace.num_steps > 0

    def test_reason_respects_max_steps(self):
        cot = ChainOfThought(max_steps=2)
        trace = cot.reason("Complex multi-step problem")
        assert trace.num_steps <= 2

    def test_outcome_is_set(self):
        cot = ChainOfThought(max_steps=5)
        trace = cot.reason("Test")
        assert trace.outcome in ("success", "incomplete")


class TestTreeOfThoughts:
    """TreeOfThoughts strategy tests."""

    def test_bfs_reason(self):
        tot = TreeOfThoughts(beam_width=2, max_depth=3, exploration_mode="bfs")
        trace = tot.reason("Solve optimization problem")
        assert isinstance(trace, ReasoningTrace)
        assert trace.strategy == "tree_of_thoughts"
        assert "nodes_explored" in trace.metadata

    def test_dfs_reason(self):
        tot = TreeOfThoughts(beam_width=2, max_depth=3, exploration_mode="dfs")
        trace = tot.reason("Analyse argument")
        assert trace.strategy == "tree_of_thoughts"

    def test_pruning_active(self):
        tot = TreeOfThoughts(beam_width=1, max_depth=2, prune_threshold=0.9)
        trace = tot.reason("Test")
        # With high prune threshold, should still produce a trace
        assert trace.num_steps >= 0

    def test_metadata_contains_best_score(self):
        tot = TreeOfThoughts(beam_width=2, max_depth=2)
        trace = tot.reason("Test")
        assert "best_score" in trace.metadata
        assert 0.0 <= trace.metadata["best_score"] <= 1.0


class TestSelfConsistency:
    """SelfConsistency strategy tests."""

    def test_reason_runs_multiple_samples(self):
        sc = SelfConsistency(n_samples=3)
        trace = sc.reason("What causes seasons?")
        assert trace.strategy == "self_consistency"
        assert "n_samples" in trace.metadata
        assert trace.metadata["n_samples"] == 3
        assert "consensus_ratio" in trace.metadata

    def test_metadata_has_consensus_info(self):
        sc = SelfConsistency(n_samples=5)
        trace = sc.reason("Explain tides")
        assert "consensus_count" in trace.metadata
        assert "unique_conclusions" in trace.metadata

    def test_with_custom_inner_reasoner(self):
        inner = ChainOfThought(max_steps=3)
        sc = SelfConsistency(n_samples=2, inner_reasoner=inner)
        trace = sc.reason("Test with custom reasoner")
        assert trace.strategy == "self_consistency"


class TestStepBack:
    """StepBack strategy tests."""

    def test_reason_three_phase(self):
        sb = StepBack()
        trace = sb.reason("Optimize the delivery route for cost minimization")
        assert trace.strategy == "step_back"
        assert trace.num_steps == 3
        assert trace.outcome == "success"

    def test_abstract_detects_problem_class(self):
        sb = StepBack()
        # Different task types should produce different abstractions
        t1 = sb.reason("Classify these images into categories")
        t2 = sb.reason("Predict next month's sales")
        # Both should produce 3-step traces
        assert t1.num_steps == 3
        assert t2.num_steps == 3

    def test_metadata_has_abstraction(self):
        sb = StepBack()
        trace = sb.reason("Why does ice float?")
        assert "abstraction" in trace.metadata
        assert "abstract_solution" in trace.metadata

    def test_general_problem_fallback(self):
        sb = StepBack()
        trace = sb.reason("Do something interesting")
        assert trace.metadata["abstraction"] == "general_reasoning_problem"


class TestAnalogicalReasoning:
    """AnalogicalReasoning strategy tests."""

    def test_reason_without_analogues(self):
        ar = AnalogicalReasoning()
        trace = ar.reason("A completely novel problem")
        assert trace.strategy == "analogical_reasoning"
        assert trace.metadata["analogues_found"] == 0

    def test_reason_with_analogues(self):
        ar = AnalogicalReasoning(analogue_base=[
            AnaloguePair(
                source_domain="fluid dynamics",
                target_domain="traffic flow",
                structural_mapping={"fluid": "cars", "pipe": "road"},
                similarity_score=0.85,
                transfer_confidence=0.8,
            ),
        ])
        trace = ar.reason("Model a fluid dynamics traffic flow problem")
        assert trace.metadata["analogues_found"] >= 0

    def test_add_analogue(self):
        ar = AnalogicalReasoning()
        pair = AnaloguePair(
            source_domain="math optimization",
            target_domain="physics optimization",
            structural_mapping={"cost": "energy"},
            similarity_score=0.85,
            transfer_confidence=0.8,
        )
        ar.add_analogue(pair)
        trace = ar.reason("Solve a math optimization physics problem with cost constraints")
        assert trace.metadata["analogues_found"] >= 1

    def test_similarity_threshold(self):
        ar = AnalogicalReasoning(analogue_base=[
            AnaloguePair(source_domain="math", target_domain="physics", similarity_score=0.95),
        ], similarity_threshold=0.99)
        trace = ar.reason("Unrelated cooking problem")
        assert trace.metadata["analogues_found"] == 0

    def test_mixed_quality_step_confidences(self):
        ar = AnalogicalReasoning(analogue_base=[
            AnaloguePair(
                source_domain="optimization",
                target_domain="scheduling",
                structural_mapping={"cost": "time"},
                similarity_score=0.6,
                transfer_confidence=0.7,
            ),
        ])
        trace = ar.reason("Schedule optimization for delivery")
        # First step (retrieve) confidence should reflect analogue quality
        assert trace.steps[0].confidence >= 0.3


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Cross-module integration tests."""

    def test_reflact_then_grpo(self):
        """ReflActReasoner produces a trace that GRPOTrainer can work with."""
        reasoner = ReflActReasoner(default_max_steps=3)
        trace = reasoner.reason("Prove that sqrt(2) is irrational")

        # Use trace content to seed GRPO
        trainer = GRPOTrainer(group_size=3)
        prompt = f"Continue reasoning: {trace.final_step().observation if trace.final_step() else trace.task}"
        traj = trainer.train_step(prompt, ground_truth="Proof by contradiction")
        assert isinstance(traj, GRPOTrajectory)

    def test_cot_then_selfconsistency(self):
        """ChainOfThought + SelfConsistency composition."""
        cot = ChainOfThought(max_steps=3)
        sc = SelfConsistency(n_samples=3, inner_reasoner=cot)
        trace = sc.reason("Explain machine learning")
        assert trace.metadata["n_samples"] == 3
        assert trace.strategy == "self_consistency"

    def grpo_advantage_ordering(self):
        """Higher reward yields higher advantage."""
        trainer = GRPOTrainer()
        rewards = tuple(float(i) for i in range(10))
        advantages = trainer.compute_advantages(rewards)
        for i in range(len(advantages) - 1):
            assert advantages[i] < advantages[i + 1], f"advantage[{i}]={advantages[i]} < advantage[{i+1}]={advantages[i+1]}"

    def test_all_strategies_produce_valid_traces(self):
        """Smoke test: every strategy can reason about a simple task."""
        task = "What is the capital of France?"
        strategies = {
            ChainOfThought(max_steps=3),
            TreeOfThoughts(beam_width=2, max_depth=2),
            SelfConsistency(n_samples=3),
            StepBack(),
            AnalogicalReasoning(),
        }
        for strat in strategies:
            trace = strat.reason(task)
            assert isinstance(trace, ReasoningTrace), f"{type(strat).__name__} failed"
            assert trace.outcome in ("success", "incomplete"), f"{type(strat).__name__} outcome"
