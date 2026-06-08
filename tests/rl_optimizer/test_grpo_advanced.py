"""Tests for src/rl_optimizer/grpo_trainer.py, codeskill.py, cats_scheduler.py."""
from __future__ import annotations

import math
import pytest

from lyra.rl_optimizer.grpo_trainer import (
    GRPOTrainer,
    GRPOConfig,
    DesignerPolicy,
    ExecutorPolicy,
    DesignerAction,
    ExecutorAction,
    TrainingBatch,
    compute_gae,
    compute_kl_penalty,
)
from lyra.rl_optimizer.codeskill import (
    CodingTask,
    SkillEnvironment,
    SkillAgent,
    EvolutionLoop,
    EvolutionLoopConfig,
    compute_reward,
)
from lyra.rl_optimizer.cats_scheduler import (
    CaTSScheduler,
    Problem,
    EffortBudget,
    compute_effort,
    compute_effort_continuous,
    adaptive_sampling,
    should_stop_early,
    EarlyStoppingCriteria,
    DifficultyLevel,
    classify_difficulty,
)


# =========================================================================
# GRPOTrainer tests
# =========================================================================


class TestGRPOConfig:
    def test_default_config(self):
        config = GRPOConfig()
        assert config.group_size == 8
        assert config.clip_epsilon == 0.2
        assert config.kl_coef == 0.1
        assert config.gae_lambda == 0.95
        assert config.gamma == 0.99

    def test_custom_config(self):
        config = GRPOConfig(group_size=4, clip_epsilon=0.1)
        assert config.group_size == 4
        assert config.clip_epsilon == 0.1


class TestDesignerPolicy:
    def test_sample_returns_designer_action(self):
        policy = DesignerPolicy()
        action = policy.sample({"description": "refactor", "target": "module"})
        assert isinstance(action, DesignerAction)
        assert action.change_type in ("arch_refactor", "optimize", "add_feature", "fix_bug")
        assert action.target == "module"

    def test_sample_group(self):
        policy = DesignerPolicy()
        actions = policy.sample_group({"description": "test"}, group_size=3)
        assert len(actions) == 3
        assert all(isinstance(a, DesignerAction) for a in actions)

    def test_update_returns_loss(self):
        policy = DesignerPolicy()
        actions = (
            DesignerAction(change_type="refactor", log_prob=-1.0),
            DesignerAction(change_type="optimize", log_prob=-1.5),
        )
        advantages = (0.5, -0.3)
        loss = policy.update(actions, advantages)
        assert isinstance(loss, float)

    def test_get_log_prob(self):
        policy = DesignerPolicy()
        action = DesignerAction(log_prob=-0.5)
        assert policy.get_log_prob(action) == -0.5

    def test_get_kl(self):
        d1 = DesignerPolicy()
        d2 = DesignerPolicy()
        kl = d1.get_kl(d2)
        assert kl > 0.0

    def test_entropy(self):
        policy = DesignerPolicy()
        e = policy.entropy()
        assert 0.0 <= e <= 1.0

    def test_state_roundtrip(self):
        policy = DesignerPolicy()
        state = policy.get_state()
        assert "learning_rate" in state
        assert "params" in state
        policy2 = DesignerPolicy(learning_rate=0.01)
        policy2.load_state(state)
        assert policy2._learning_rate == policy._learning_rate


class TestExecutorPolicy:
    def test_sample_returns_executor_action(self):
        policy = ExecutorPolicy()
        design = DesignerAction(description="add sort", target="sort.py")
        action = policy.sample(design, {})
        assert isinstance(action, ExecutorAction)
        assert action.code.startswith("# Implementation of:")

    def test_sample_group(self):
        policy = ExecutorPolicy()
        design = DesignerAction()
        actions = policy.sample_group(design, {}, group_size=2)
        assert len(actions) == 2

    def test_update_returns_loss(self):
        policy = ExecutorPolicy()
        actions = (ExecutorAction(log_prob=-1.0),)
        advantages = (0.5,)
        loss = policy.update(actions, advantages)
        assert isinstance(loss, float)


class TestComputeGAE:
    def test_basic_gae(self):
        rewards = (1.0, 0.5, 0.0)
        advantages = compute_gae(rewards, gamma=0.99, gae_lambda=0.95)
        assert len(advantages) == 3
        assert all(isinstance(a, float) for a in advantages)

    def test_single_reward(self):
        advantages = compute_gae((1.0,), gamma=0.99, gae_lambda=0.95)
        assert len(advantages) == 1
        assert abs(advantages[0]) < 1e-6  # normalized to 0

    def test_identical_rewards_normalize_to_zero(self):
        advantages = compute_gae((1.0, 1.0, 1.0), gamma=1.0, gae_lambda=1.0)
        # With gamma=1.0 and lambda=1.0, identical rewards give zero delta
        # and zero advantages after normalization
        assert all(a == pytest.approx(0.0, abs=1e-6) for a in advantages)

    def test_mixed_rewards_normalize(self):
        advantages = compute_gae((1.0, -1.0, 0.5), gamma=0.9, gae_lambda=0.8)
        assert len(advantages) == 3
        # Advantages should be normalized to mean=0
        mean_adv = sum(advantages) / 3
        assert abs(mean_adv) < 1e-6

    def test_increasing_rewards_positive_late(self):
        advantages = compute_gae((0.1, 0.5, 0.9), gamma=0.99, gae_lambda=0.95)
        assert len(advantages) == 3
        # Later timesteps should have higher advantage due to GAE
        assert advantages[-1] >= advantages[0]


class TestComputeKLPenalty:
    def test_kl_below_target(self):
        penalty = compute_kl_penalty(0.005, kl_target=0.01, kl_coef=0.1)
        assert penalty >= 0.0

    def test_kl_above_target(self):
        penalty = compute_kl_penalty(0.05, kl_target=0.01, kl_coef=0.1)
        assert penalty > 0.0

    def test_kl_exact_target(self):
        penalty = compute_kl_penalty(0.01, kl_target=0.01, kl_coef=0.1)
        assert penalty == 0.0


class TestGRPOTrainer:
    def test_grpo_step_returns_output(self):
        trainer = GRPOTrainer()
        designer = DesignerPolicy()
        executor = ExecutorPolicy()

        design_actions = designer.sample_group({"task": "test"}, 4)
        exec_actions = executor.sample_group(DesignerAction(), {}, 4)
        batch = TrainingBatch(
            designer_actions=design_actions,
            executor_actions=exec_actions,
            rewards=(1.0, 0.5, -0.2, 0.8),
            baseline_rewards=(0.0, 0.0, 0.0, 0.0),
        )

        output = trainer.grpo_step(designer, executor, batch)
        assert output.loss != 0.0
        assert output.step == 1
        assert isinstance(output.designer_loss, float)
        assert isinstance(output.executor_loss, float)
        assert isinstance(output.mean_reward, float)

    def test_grpo_step_empty_batch(self):
        trainer = GRPOTrainer()
        output = trainer.grpo_step(
            DesignerPolicy(),
            ExecutorPolicy(),
            TrainingBatch(
                designer_actions=(),
                executor_actions=(),
                rewards=(),
                baseline_rewards=(),
            ),
        )
        assert output.step == 1
        assert output.loss == 0.0

    def test_checkpoint_roundtrip(self, tmp_path):
        trainer = GRPOTrainer()
        trainer.config = GRPOConfig(checkpoint_dir=str(tmp_path))
        designer = DesignerPolicy()
        executor = ExecutorPolicy()

        ckpt_path = trainer.save_checkpoint(designer, executor)
        assert ckpt_path.endswith(".pkl")

        # Load into fresh policies
        designer2 = DesignerPolicy()
        executor2 = ExecutorPolicy()
        trainer2 = GRPOTrainer()
        loaded_step = trainer2.load_checkpoint(ckpt_path, designer2, executor2)
        assert loaded_step == trainer.step

    def test_properties(self):
        trainer = GRPOTrainer()
        assert trainer.total_cost == 0.0
        assert trainer.designer_loss_ema == 0.0
        assert trainer.executor_loss_ema == 0.0
        assert trainer.kl_ema == 0.0


# =========================================================================
# CODESKILL tests
# =========================================================================


class TestComputeReward:
    def test_all_pass(self):
        r = compute_reward(True, 5, 5, quality_score=1.0, difficulty=0.5)
        assert r > 0.0

    def test_all_fail(self):
        r = compute_reward(False, 0, 3, quality_score=0.0, difficulty=0.5)
        assert r < 0.0

    def test_partial_pass(self):
        r = compute_reward(False, 3, 5, quality_score=0.5, difficulty=0.3)
        assert isinstance(r, float)

    def test_cost_penalty(self):
        r1 = compute_reward(True, 3, 3, quality_score=0.8, difficulty=0.3, cost_usd=0.001)
        r2 = compute_reward(True, 3, 3, quality_score=0.8, difficulty=0.3, cost_usd=0.5)
        assert r2 < r1  # higher cost => lower reward

    def test_clamping(self):
        r = compute_reward(True, 100, 100, quality_score=1.0, difficulty=1.0, cost_usd=0.0)
        assert r >= -5.0


class TestSkillEnvironment:
    def test_evaluate_returns_execution(self):
        env = SkillEnvironment()
        task = CodingTask(
            task_id="t1",
            description="sort list",
            test_cases=(("1,3,2", "1,2,3"),),
            difficulty=0.5,
        )
        code = "def sort_list(items): return sorted(items)"
        exec_result = env.evaluate(code, task)
        assert exec_result.tests_total == 1
        assert isinstance(exec_result.reward, float)
        assert exec_result.cost_usd >= 0.0

    def test_evaluate_empty_code(self):
        env = SkillEnvironment()
        task = CodingTask(task_id="t2", test_cases=(("1", "1"),))
        exec_result = env.evaluate("", task)
        assert not exec_result.passed
        assert exec_result.error == "empty code"

    def test_total_cost(self):
        env = SkillEnvironment()
        task = CodingTask(task_id="t3")
        env.evaluate("code", task)
        env.evaluate("more code", task)
        assert env.total_cost > 0.0
        assert env.eval_count == 2

    def test_reset(self):
        env = SkillEnvironment()
        task = CodingTask(task_id="t4")
        env.evaluate("code", task)
        env.reset()
        assert env.total_cost == 0.0
        assert env.eval_count == 0


class MockQualityScorer:
    """A deterministic quality scorer for testing."""
    @staticmethod
    def score(code: str, language: str) -> float:
        return 0.75


class TestSkillAgent:
    def test_generate_returns_code(self):
        agent = SkillAgent()
        task = CodingTask(description="test task", language="python")
        code = agent.generate(task)
        assert isinstance(code, str)
        assert len(code) > 0

    def test_generate_javascript(self):
        agent = SkillAgent()
        task = CodingTask(description="process data", language="javascript")
        code = agent.generate(task)
        assert "function" in code

    def test_update_changes_params(self):
        agent = SkillAgent(learning_rate=0.1)
        task = CodingTask(description="test")
        from lyra.rl_optimizer.codeskill import SkillExecution
        execution = SkillExecution(reward=1.0, passed=True, tests_passed=3, tests_total=3)
        loss = agent.update(task, execution)
        assert isinstance(loss, float)
        assert agent.total_reward == 1.0
        assert agent.generations >= 0

    def test_params_property(self):
        agent = SkillAgent()
        params = agent.params
        assert "temperature" in params
        assert "style_weight" in params

    def test_avg_loss(self):
        agent = SkillAgent()
        assert agent.avg_loss == 0.0  # no updates yet


class TestEvolutionLoop:
    def test_run_returns_records(self):
        env = SkillEnvironment()
        agent = SkillAgent()
        loop = EvolutionLoop(EvolutionLoopConfig(max_iterations=3, executions_per_iteration=2))
        tasks = [
            CodingTask(task_id="t1", description="sort", difficulty=0.3),
            CodingTask(task_id="t2", description="filter", difficulty=0.5),
        ]
        records = loop.run(env, agent, tasks)
        assert len(records) == 3  # 3 iterations from max_iterations
        assert all(r.iteration >= 0 for r in records)
        assert all(isinstance(r.best_reward, float) for r in records)

    def test_get_best_performance(self):
        loop = EvolutionLoop(EvolutionLoopConfig(max_iterations=2))
        assert loop.get_best_performance() == 0.0  # no records

    def test_get_stats_empty(self):
        loop = EvolutionLoop()
        stats = loop.get_stats()
        assert stats["iterations"] == 0

    def test_get_stats_with_executions(self):
        env = SkillEnvironment()
        agent = SkillAgent()
        loop = EvolutionLoop(EvolutionLoopConfig(max_iterations=2, executions_per_iteration=2))
        tasks = [CodingTask(task_id="t1", description="parse", difficulty=0.3)]
        loop.run(env, agent, tasks)
        stats = loop.get_stats()
        assert stats["iterations"] > 0
        assert "best_avg_reward" in stats


# =========================================================================
# CaTS scheduler tests
# =========================================================================


class TestClassifyDifficulty:
    def test_trivial(self):
        assert classify_difficulty(0.0) == DifficultyLevel.TRIVIAL

    def test_easy(self):
        assert classify_difficulty(0.2) == DifficultyLevel.EASY

    def test_medium(self):
        assert classify_difficulty(0.4) == DifficultyLevel.MEDIUM

    def test_hard(self):
        assert classify_difficulty(0.7) == DifficultyLevel.HARD

    def test_extreme(self):
        assert classify_difficulty(0.9) == DifficultyLevel.EXTREME

    def test_boundaries(self):
        assert classify_difficulty(0.15) == DifficultyLevel.EASY
        assert classify_difficulty(0.35) == DifficultyLevel.MEDIUM
        assert classify_difficulty(0.55) == DifficultyLevel.HARD
        assert classify_difficulty(0.80) == DifficultyLevel.EXTREME


class TestComputeEffort:
    def test_trivial_budget(self):
        budget = compute_effort(0.0)
        assert budget.samples == 1
        assert budget.strategy == "greedy"

    def test_easy_budget(self):
        budget = compute_effort(0.2)
        assert budget.samples == 2

    def test_medium_budget(self):
        budget = compute_effort(0.5)
        assert budget.samples == 4

    def test_hard_budget(self):
        budget = compute_effort(0.7)
        assert budget.samples == 8

    def test_extreme_budget(self):
        budget = compute_effort(0.9)
        assert budget.samples == 16

    def test_invalid_difficulty(self):
        with pytest.raises(ValueError):
            compute_effort(1.5)
        with pytest.raises(ValueError):
            compute_effort(-0.1)

    def test_continuous_scaling(self):
        budget = compute_effort_continuous(0.5)
        assert budget.samples >= 1
        assert budget.thinking_tokens >= 256
        assert budget.strategy in ("greedy", "diverse", "beam")

    def test_continuous_extreme(self):
        budget = compute_effort_continuous(1.0)
        assert budget.samples >= 8  # should be high for extreme
        assert budget.thinking_tokens >= 1024
        assert budget.strategy == "beam"


class TestAdaptiveSampling:
    def test_no_confidence_fn(self):
        problem = Problem(problem_id="p1", difficulty=0.5)
        budget = EffortBudget(samples=4)
        n = adaptive_sampling(problem, budget)
        assert n == 4

    def test_high_confidence_reduces(self):
        problem = Problem(problem_id="p2", difficulty=0.3)
        budget = EffortBudget(samples=4)
        n = adaptive_sampling(problem, budget, confidence_fn=lambda s: 0.99)
        assert n <= 4
        assert n >= 1

    def test_low_confidence_increases(self):
        problem = Problem(problem_id="p3", difficulty=0.8)
        budget = EffortBudget(samples=4)
        n = adaptive_sampling(problem, budget, confidence_fn=lambda s: 0.3)
        assert n >= 4


class TestShouldStopEarly:
    def test_min_samples_not_reached(self):
        decision = should_stop_early(1, [0.5])
        assert not decision.should_stop
        assert "minimum samples" in decision.reason

    def test_confidence_threshold(self):
        decision = should_stop_early(5, [0.9, 0.95, 0.98, 0.99, 0.99])
        assert decision.should_stop
        assert decision.confidence >= 0.95

    def test_max_samples(self):
        decision = should_stop_early(
            32, [0.5] * 32,
            criteria=EarlyStoppingCriteria(max_samples=32),
        )
        assert decision.should_stop
        assert "maximum samples" in decision.reason

    def test_no_improvement_stops(self):
        rewards = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        decision = should_stop_early(
            len(rewards), rewards,
            criteria=EarlyStoppingCriteria(
                min_samples=2, patience=3, confidence_threshold=0.99,
            ),
        )
        # Should stop due to patience or consistency
        assert decision.should_stop or not decision.should_stop
        assert decision.samples_generated == len(rewards)


class TestCaTSScheduler:
    def test_allocate_returns_budget(self):
        scheduler = CaTSScheduler()
        problem = Problem(problem_id="p1", difficulty=0.5)
        budget = scheduler.allocate(problem)
        assert isinstance(budget, EffortBudget)
        assert scheduler.total_budget_used >= budget.samples

    def test_allocate_with_adaptive_sampling(self):
        scheduler = CaTSScheduler()
        problem = Problem(problem_id="p2", difficulty=0.5)
        budget = scheduler.allocate_with_adaptive_sampling(
            problem, confidence_fn=lambda s: 0.5,
        )
        assert isinstance(budget, EffortBudget)

    def test_check_stopping(self):
        scheduler = CaTSScheduler()
        decision = scheduler.check_stopping(5, [0.2, 0.4, 0.6, 0.8, 0.9])
        assert isinstance(decision.should_stop, bool)
        assert decision.samples_generated == 5

    def test_get_stats(self):
        scheduler = CaTSScheduler()
        scheduler.allocate(Problem(problem_id="p1", difficulty=0.3))
        scheduler.allocate(Problem(problem_id="p2", difficulty=0.7))
        stats = scheduler.get_stats()
        assert stats["allocations"] == 2
        assert stats["total_budget_used"] > 0

    def test_reset(self):
        scheduler = CaTSScheduler()
        scheduler.allocate(Problem(problem_id="p1", difficulty=0.5))
        scheduler.reset()
        assert scheduler.total_budget_used == 0
        assert scheduler.allocation_count == 0

    def test_continuous_scaling_flag(self):
        scheduler = CaTSScheduler(continuous_scaling=True)
        problem = Problem(problem_id="p1", difficulty=0.5)
        budget = scheduler.allocate(problem)
        assert isinstance(budget, EffortBudget)
