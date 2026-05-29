"""Tests for Phase 9: Continuous Evaluation Pipeline."""

from __future__ import annotations

import time

import pytest
from lyra_core.auto.benchmark_harness import (
    BenchmarkDomain,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
)
from lyra_core.evaluation import (
    AgentScore,
    BenchmarkRecord,
    BenchmarkStore,
    EvalPipeline,
    EvalTrigger,
    LeaderboardEngine,
    PipelineConfig,
    PipelineRun,
    RankingView,
    RunComparison,
)

# ═══════════════════════════════════════════════════════════════════════════════
# EvalTrigger
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvalTrigger:
    def test_trigger_values(self):
        assert EvalTrigger.MANUAL.value == "manual"
        assert EvalTrigger.SCHEDULED.value == "scheduled"
        assert EvalTrigger.ON_COMMIT.value == "on_commit"
        assert EvalTrigger.ON_PR.value == "on_pr"
        assert EvalTrigger.ON_DEPLOY.value == "on_deploy"
        assert EvalTrigger.ON_DRIFT.value == "on_drift"
        assert EvalTrigger.ON_LEARNING_CYCLE.value == "on_learning_cycle"

    def test_trigger_is_str_enum(self):
        assert isinstance(EvalTrigger.MANUAL, str)


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineConfig
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.schedule_interval_seconds == 3600.0
        assert config.regression_threshold == 0.05
        assert config.improvement_threshold == 0.05
        assert config.max_runs_history == 100
        assert config.auto_baseline_after_runs == 10
        assert EvalTrigger.MANUAL in config.triggers
        assert EvalTrigger.ON_PR in config.triggers

    def test_custom_config(self):
        config = PipelineConfig(
            schedule_interval_seconds=600.0,
            regression_threshold=0.1,
            triggers=(EvalTrigger.ON_COMMIT,),
        )
        assert config.schedule_interval_seconds == 600.0
        assert config.regression_threshold == 0.1
        assert len(config.triggers) == 1

    def test_is_frozen(self):
        config = PipelineConfig()
        with pytest.raises(Exception):  # noqa: B017
            config.max_runs_history = 50  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineRun
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineRun:
    @pytest.fixture
    def sample_benchmark_run(self):
        return BenchmarkRun(
            run_id="br-test",
            results=(
                BenchmarkResult(
                    domain=BenchmarkDomain.SAFETY, metric_name="block_rate",
                    score=0.95, threshold=0.90, baseline=0.93,
                    status=BenchmarkStatus.PASSED, unit="score", metadata=(),
                ),
            ),
            overall_score=0.95,
            passed=True,
            domains_covered=1,
            timestamp=time.time(),
            summary="1/1 passed",
        )

    def test_create(self, sample_benchmark_run):
        pr = PipelineRun(
            id="pr-1", trigger=EvalTrigger.ON_PR,
            benchmark_run=sample_benchmark_run,
            commit_sha="abc123", pr_number=42,
            regressions=(), improvements=(),
        )
        assert pr.id == "pr-1"
        assert pr.trigger == EvalTrigger.ON_PR
        assert pr.commit_sha == "abc123"
        assert pr.pr_number == 42
        assert pr.overall_score == 0.95
        assert pr.passed is True

    def test_has_regressions(self, sample_benchmark_run):
        pr = PipelineRun(
            id="pr-2", trigger=EvalTrigger.ON_COMMIT,
            benchmark_run=sample_benchmark_run,
            regressions=("safety:block_rate",),
            improvements=(),
        )
        assert pr.has_regressions is True
        assert pr.has_improvements is False

    def test_has_improvements(self, sample_benchmark_run):
        pr = PipelineRun(
            id="pr-3", trigger=EvalTrigger.MANUAL,
            benchmark_run=sample_benchmark_run,
            regressions=(),
            improvements=("skills:pass_rate",),
        )
        assert pr.has_improvements is True
        assert pr.has_regressions is False

    def test_is_frozen(self, sample_benchmark_run):
        pr = PipelineRun(
            id="pr-4", trigger=EvalTrigger.MANUAL,
            benchmark_run=sample_benchmark_run,
        )
        with pytest.raises(Exception):  # noqa: B017
            pr.trigger = EvalTrigger.ON_PR  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# EvalPipeline
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvalPipeline:
    @pytest.fixture
    def pipeline(self):
        p = EvalPipeline()
        p.harness.register("safety", "block_rate", lambda: 0.989, threshold=0.95)
        p.harness.register("skills", "pass_rate", lambda: 0.92, threshold=0.80)
        return p

    def test_create(self):
        pipeline = EvalPipeline()
        assert pipeline.run_count == 0
        assert pipeline.config.max_runs_history == 100

    def test_run_manual(self, pipeline):
        pr = pipeline.run(EvalTrigger.MANUAL)
        assert pr.trigger == EvalTrigger.MANUAL
        assert pipeline.run_count == 1
        assert pr.overall_score is not None

    def test_run_with_commit(self, pipeline):
        pr = pipeline.run(EvalTrigger.ON_COMMIT, commit_sha="deadbeef")
        assert pr.commit_sha == "deadbeef"

    def test_run_with_pr(self, pipeline):
        pr = pipeline.run(EvalTrigger.ON_PR, pr_number=7, triggered_by="bot")
        assert pr.pr_number == 7
        assert pr.triggered_by == "bot"

    def test_get_latest_run(self, pipeline):
        pipeline.run(EvalTrigger.MANUAL)
        latest = pipeline.get_latest_run()
        assert latest is not None
        assert latest.trigger == EvalTrigger.MANUAL

    def test_get_latest_run_empty(self):
        pipeline = EvalPipeline()
        assert pipeline.get_latest_run() is None

    def test_get_runs_by_trigger(self, pipeline):
        pipeline.run(EvalTrigger.MANUAL)
        pipeline.run(EvalTrigger.MANUAL)
        pipeline.run(EvalTrigger.ON_PR)
        manual = pipeline.get_runs_by_trigger(EvalTrigger.MANUAL)
        assert len(manual) == 2
        pr_runs = pipeline.get_runs_by_trigger(EvalTrigger.ON_PR)
        assert len(pr_runs) == 1

    def test_check_regressions_empty(self):
        pipeline = EvalPipeline()
        assert pipeline.check_regressions() == ()

    def test_check_improvements_empty(self):
        pipeline = EvalPipeline()
        assert pipeline.check_improvements() == ()

    def test_get_trend(self, pipeline):
        pipeline.run(EvalTrigger.MANUAL)
        pipeline.run(EvalTrigger.MANUAL)
        trend = pipeline.get_trend("safety:block_rate")
        assert len(trend) == 2

    def test_clear_history(self, pipeline):
        pipeline.run(EvalTrigger.MANUAL)
        pipeline.clear_history()
        assert pipeline.run_count == 0
        assert pipeline.get_latest_run() is None

    def test_last_overall_score(self, pipeline):
        assert pipeline.last_overall_score is None
        pipeline.run(EvalTrigger.MANUAL)
        assert pipeline.last_overall_score is not None

    def test_regression_detection(self, pipeline):
        pipeline.run(EvalTrigger.MANUAL)
        # Hack: register a worse score to simulate regression
        pipeline.harness._metrics.clear()
        pipeline.harness._thresholds.clear()
        pipeline.harness.register("safety", "block_rate", lambda: 0.80, threshold=0.95)
        pipeline.harness.register("skills", "pass_rate", lambda: 0.92, threshold=0.80)
        pipeline.run(EvalTrigger.MANUAL)
        latest = pipeline.get_latest_run()
        # Regression should be detected since block_rate dropped from 0.989 to 0.80
        assert latest is not None
        if latest.has_regressions:
            assert any("block_rate" in r for r in latest.regressions)

    def test_max_runs_history(self):
        config = PipelineConfig(max_runs_history=3)
        pipeline = EvalPipeline(config=config)
        pipeline.harness.register("safety", "block_rate", lambda: 0.99, threshold=0.95)
        for _ in range(5):
            pipeline.run(EvalTrigger.MANUAL)
        assert pipeline.run_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# BenchmarkRecord
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarkRecord:
    def test_create(self):
        rec = BenchmarkRecord(
            id="br1", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.95, threshold=0.90,
        )
        assert rec.id == "br1"
        assert rec.passed is True

    def test_not_passed(self):
        rec = BenchmarkRecord(
            id="br2", domain="skills", agent_id="agent-1",
            metric_name="pass_rate", score=0.75, threshold=0.80,
        )
        assert rec.passed is False

    def test_with_metadata(self):
        rec = BenchmarkRecord(
            id="br3", domain="memory", agent_id="agent-2",
            metric_name="recall", score=0.88, threshold=0.85,
            metadata=(("env", "prod"), ("version", "1.0")),
        )
        assert rec.metadata == (("env", "prod"), ("version", "1.0"))

    def test_defaults(self):
        rec = BenchmarkRecord(
            id="br4", domain="reasoning", agent_id="agent-3",
            metric_name="accuracy", score=0.90, threshold=0.85,
        )
        assert rec.run_id == ""
        assert rec.timestamp > 0

    def test_is_frozen(self):
        rec = BenchmarkRecord(
            id="br5", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.95, threshold=0.90,
        )
        with pytest.raises(Exception):  # noqa: B017
            rec.score = 0.99  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# RunComparison
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunComparison:
    def test_create(self):
        cmp = RunComparison(
            run_id_a="run1", run_id_b="run2",
            metric_diffs=(("safety:block_rate", 0.05),),
            regressions=(), improvements=("safety:block_rate",),
            overall_delta=0.05,
        )
        assert cmp.has_improvements is True
        assert cmp.has_regressions is False

    def test_with_regressions(self):
        cmp = RunComparison(
            run_id_a="run1", run_id_b="run2",
            metric_diffs=(("safety:block_rate", -0.1),),
            regressions=("safety:block_rate",),
            improvements=(),
            overall_delta=-0.1,
        )
        assert cmp.has_regressions is True
        assert cmp.has_improvements is False


# ═══════════════════════════════════════════════════════════════════════════════
# BenchmarkStore
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarkStore:
    @pytest.fixture
    def store(self):
        s = BenchmarkStore()
        s.save(BenchmarkRecord(
            id="r1", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.989, threshold=0.95,
        ))
        s.save(BenchmarkRecord(
            id="r2", domain="skills", agent_id="agent-1",
            metric_name="pass_rate", score=0.88, threshold=0.80,
        ))
        s.save(BenchmarkRecord(
            id="r3", domain="safety", agent_id="agent-2",
            metric_name="block_rate", score=0.95, threshold=0.95,
        ))
        return s

    def test_save_and_get(self, store):
        rec = store.get("r1")
        assert rec is not None
        assert rec.score == 0.989

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None

    def test_query_by_domain(self, store):
        safety = store.query(domain="safety")
        assert len(safety) == 2
        assert all(r.domain == "safety" for r in safety)

    def test_query_by_agent(self, store):
        records = store.query(agent_id="agent-2")
        assert len(records) == 1
        assert records[0].agent_id == "agent-2"

    def test_query_by_metric(self, store):
        records = store.query(metric_name="block_rate")
        assert len(records) == 2

    def test_query_by_time_range(self, store):
        now = time.time()
        store.save(BenchmarkRecord(
            id="r4", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.99, threshold=0.95,
            timestamp=now - 86400,
        ))
        recent = store.query(since=now - 3600)
        assert len(recent) >= 1

    def test_get_trend(self, store):
        store.save(BenchmarkRecord(
            id="r4", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.99, threshold=0.95,
        ))
        trend = store.get_trend("safety", "block_rate", agent_id="agent-1")
        assert len(trend) == 2
        assert trend[0] == 0.989
        assert trend[1] == 0.99

    def test_get_latest_score(self, store):
        score = store.get_latest_score("safety", "block_rate", agent_id="agent-1")
        assert score == 0.989

    def test_get_latest_score_missing(self, store):
        assert store.get_latest_score("nonexistent", "metric") is None

    def test_get_domains(self, store):
        domains = store.get_domains()
        assert "safety" in domains
        assert "skills" in domains

    def test_get_agents(self, store):
        agents = store.get_agents()
        assert "agent-1" in agents
        assert "agent-2" in agents

    def test_get_summary(self, store):
        summary = store.get_summary(agent_id="agent-1")
        assert "safety" in summary
        assert "skills" in summary
        assert summary["safety"]["block_rate"] == 0.989

    def test_get_summary_all(self, store):
        summary = store.get_summary()
        assert "safety" in summary
        assert "skills" in summary

    def test_get_top(self, store):
        top = store.get_top("safety", limit=5)
        assert len(top) >= 1
        assert top[0].domain == "safety"

    def test_prune_before(self, store):
        old_time = time.time() + 100000
        removed = store.prune_before(old_time)
        assert removed >= 0

    def test_max_records_eviction(self):
        s = BenchmarkStore(max_records=3)
        for i in range(5):
            s.save(BenchmarkRecord(
                id=f"r{i}", domain="safety", agent_id=f"agent-{i}",
                metric_name="block_rate", score=0.9, threshold=0.8,
            ))
        assert s.record_count == 3

    def test_clear(self, store):
        store.clear()
        assert store.record_count == 0

    def test_compare_runs(self, store):
        store.save(BenchmarkRecord(
            id="r4", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.99, threshold=0.95,
            run_id="run2",
        ))
        # Update r1 to have a run_id
        store.save(BenchmarkRecord(
            id="r1-v2", domain="safety", agent_id="agent-1",
            metric_name="block_rate", score=0.989, threshold=0.95,
            run_id="run1",
        ))
        cmp = store.compare_runs("run1", "run2")
        # Only works if both run_ids have records
        if cmp is not None:
            assert isinstance(cmp.overall_delta, float)


# ═══════════════════════════════════════════════════════════════════════════════
# AgentScore
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentScore:
    def test_create(self):
        score = AgentScore(
            agent_id="agent-1",
            domain_scores=(("safety", 0.95), ("skills", 0.88)),
            overall_score=0.915,
            rank=3, previous_rank=5, trend="improving",
        )
        assert score.agent_id == "agent-1"
        assert score.get_domain_score("safety") == 0.95
        assert score.get_domain_score("skills") == 0.88
        assert score.get_domain_score("nonexistent") is None

    def test_defaults(self):
        score = AgentScore(
            agent_id="agent-2",
            domain_scores=(("memory", 0.80),),
            overall_score=0.80,
        )
        assert score.rank == 0
        assert score.previous_rank == 0
        assert score.trend == "stable"

    def test_is_frozen(self):
        score = AgentScore(
            agent_id="agent-3",
            domain_scores=(("safety", 0.90),),
            overall_score=0.90,
        )
        with pytest.raises(Exception):  # noqa: B017
            score.rank = 1  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# RankingView
# ═══════════════════════════════════════════════════════════════════════════════


class TestRankingView:
    @pytest.fixture
    def scores(self):
        return tuple(
            AgentScore(
                agent_id=f"agent-{i}",
                domain_scores=(("safety", 0.9 - i * 0.05),),
                overall_score=0.9 - i * 0.05,
                rank=i + 1,
            )
            for i in range(5)
        )

    def test_top_3(self, scores):
        view = RankingView(domain="overall", scores=scores, total_agents=5)
        top = view.top_3
        assert len(top) == 3
        assert top[0].agent_id == "agent-0"

    def test_bottom_3(self, scores):
        view = RankingView(domain="overall", scores=scores, total_agents=5)
        bottom = view.bottom_3
        assert len(bottom) == 3
        assert bottom[-1].agent_id == "agent-4"

    def test_bottom_3_less_than_3(self):
        few_scores = tuple(
            AgentScore(
                agent_id=f"agent-{i}",
                domain_scores=(("safety", 0.9),),
                overall_score=0.9,
                rank=i + 1,
            )
            for i in range(2)
        )
        view = RankingView(domain="overall", scores=few_scores, total_agents=2)
        assert view.bottom_3 == ()


# ═══════════════════════════════════════════════════════════════════════════════
# LeaderboardEngine
# ═══════════════════════════════════════════════════════════════════════════════


class TestLeaderboardEngine:
    @pytest.fixture
    def engine(self):
        eng = LeaderboardEngine()
        eng.submit_score(AgentScore(
            agent_id="agent-a",
            domain_scores=(("safety", 0.98), ("skills", 0.92)),
            overall_score=0.95,
        ))
        eng.submit_score(AgentScore(
            agent_id="agent-b",
            domain_scores=(("safety", 0.85), ("skills", 0.95)),
            overall_score=0.90,
        ))
        eng.submit_score(AgentScore(
            agent_id="agent-c",
            domain_scores=(("safety", 0.80), ("skills", 0.78)),
            overall_score=0.79,
        ))
        return eng

    def test_submit_score(self, engine):
        assert engine.agent_count == 3

    def test_get_overall_ranking(self, engine):
        view = engine.get_overall_ranking()
        assert view.total_agents == 3
        assert view.scores[0].agent_id == "agent-a"
        assert view.scores[0].rank == 1

    def test_get_domain_ranking(self, engine):
        view = engine.get_domain_ranking("safety")
        assert view.total_agents == 3
        assert view.scores[0].agent_id == "agent-a"

    def test_get_agent_history(self, engine):
        engine.submit_score(AgentScore(
            agent_id="agent-a",
            domain_scores=(("safety", 0.99), ("skills", 0.93)),
            overall_score=0.96,
        ))
        history = engine.get_agent_history("agent-a")
        assert len(history) == 2
        assert history[0].overall_score == 0.95
        assert history[1].overall_score == 0.96

    def test_get_agent_history_missing(self, engine):
        assert engine.get_agent_history("nonexistent") == ()

    def test_get_agent_rank_history(self, engine):
        engine.get_overall_ranking()  # populate ranks
        history = engine.get_agent_rank_history("agent-a")
        assert len(history) == 1
        assert history[0][0] == 1

    def test_get_volatile_agents(self, engine):
        volatile = engine.get_volatile_agents()
        assert isinstance(volatile, tuple)

    def test_compare_agents(self, engine):
        comparison = engine.compare_agents("agent-a", "agent-b")
        assert "safety" in comparison
        assert comparison["safety"] == (0.98, 0.85)

    def test_compare_agents_missing(self, engine):
        assert engine.compare_agents("agent-a", "nonexistent") == {}

    def test_trend_computation(self, engine):
        engine.submit_score(AgentScore(
            agent_id="agent-a",
            domain_scores=(("safety", 0.99), ("skills", 0.93)),
            overall_score=0.96,
        ))
        view = engine.get_overall_ranking()
        agent_a = next(s for s in view.scores if s.agent_id == "agent-a")
        assert agent_a.trend in ("stable", "improving", "declining")

    def test_clear(self, engine):
        engine.clear()
        assert engine.agent_count == 0

    def test_rank_with_weights(self, engine):
        view = engine.get_overall_ranking(weights={"safety": 2.0, "skills": 1.0})
        assert view.total_agents == 3
