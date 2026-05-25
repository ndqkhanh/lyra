"""Comprehensive tests for lyra-context-optimizer package."""

from __future__ import annotations

import asyncio
import time

import pytest

from lyra_context_optimizer import (
    # Agent-driven compaction
    CompactionDecider,
    CompactionStrategy,
    CompactionPlanner,
    CompactionAction,
    # Verbatim pruner
    VerbatimPruner,
    PruneStrategy,
    PruneResult,
    # Async compactor
    AsyncCompactor,
    CompactionJudge,
    JudgeVerdict,
    # Knowledge blocks
    KnowledgeBlock,
    PriorityLevel,
    KnowledgeBlockRegistry,
    # Input compressor
    InputCompressor,
    CompressionStrategy,
    CompressionResult,
    # Output compressor
    OutputCompressor,
    CompressionConfig,
    # DACS switcher
    DACSManager,
    DACSMode,
    DACSConfig,
    # Compression metrics
    CompressionMetrics,
    MetricsSnapshot,
    StrategyStats,
    MetricsReport,
    # Exceptions
    ContextOptimizerError,
    CompactionError,
    CompressionError,
    KnowledgeBlockNotFoundError,
    DACSConfigError,
    FidelityLossError,
)


# ═══════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_error_can_be_raised(self):
        with pytest.raises(ContextOptimizerError):
            raise ContextOptimizerError("test")

    def test_compaction_error(self):
        with pytest.raises(CompactionError):
            raise CompactionError("test reason")

    def test_compaction_error_with_window(self):
        err = CompactionError("reason", 1024)
        assert "1024" in str(err)
        assert err.context_window_size == 1024

    def test_compression_error(self):
        err = CompressionError("input", 500, "empty output")
        assert err.target == "input"
        assert err.original_size == 500
        assert "empty output" in str(err)

    def test_knowledge_block_not_found(self):
        err = KnowledgeBlockNotFoundError("block_1")
        assert "block_1" in str(err)

    def test_knowledge_block_not_found_with_registry(self):
        err = KnowledgeBlockNotFoundError("b2", "primary")
        assert "primary" in str(err)

    def test_dacs_config_error(self):
        err = DACSConfigError("agent_1", "bad config")
        assert "agent_1" in str(err)
        assert "bad config" in str(err)

    def test_fidelity_loss_error(self):
        err = FidelityLossError(0.5, 0.8)
        assert "0.500" in str(err)
        assert "0.800" in str(err)

    def test_fidelity_loss_error_with_detail(self):
        err = FidelityLossError(0.5, 0.8, "too much pruning")
        assert "too much pruning" in str(err)


# ═══════════════════════════════════════════════════════════════════════════
# Knowledge Blocks
# ═══════════════════════════════════════════════════════════════════════════


class TestKnowledgeBlock:
    def test_create_block(self):
        block = KnowledgeBlock(block_id="b1", name="test", content="hello world")
        assert block.block_id == "b1"
        assert block.content == "hello world"
        assert block.priority == PriorityLevel.NORMAL

    def test_touch_updates_last_accessed(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="c")
        time.sleep(0.01)
        touched = block.touch()
        assert touched.last_accessed >= block.last_accessed
        assert touched.block_id == block.block_id
        assert touched.content == block.content

    def test_mark_survived(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="c")
        survived = block.mark_survived()
        assert survived.compaction_survival_count == 1
        assert block.compaction_survival_count == 0  # original unchanged

    def test_token_estimate(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="a" * 40)
        assert block.token_estimate == 10  # 40 / 4

    def test_min_token_estimate(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="ab")
        assert block.token_estimate == 1  # max(1, 2/4)

    def test_age_seconds(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="c")
        assert block.age_seconds >= 0

    def test_critical_priority_block(self):
        block = KnowledgeBlock(
            block_id="b1", name="critical", content="data",
            priority=PriorityLevel.CRITICAL,
        )
        assert block.priority == PriorityLevel.CRITICAL

    def test_frozen_dataclass(self):
        block = KnowledgeBlock(block_id="b1", name="t", content="c")
        with pytest.raises(Exception):
            block.content = "changed"  # type: ignore[misc]


class TestKnowledgeBlockRegistry:
    def test_register_and_get(self):
        reg = KnowledgeBlockRegistry()
        block = KnowledgeBlock(block_id="b1", name="test", content="data")
        reg.register(block)
        assert reg.get("b1").block_id == "b1"

    def test_get_not_found_raises(self):
        reg = KnowledgeBlockRegistry()
        with pytest.raises(KnowledgeBlockNotFoundError):
            reg.get("nonexistent")

    def test_get_or_none(self):
        reg = KnowledgeBlockRegistry()
        block = KnowledgeBlock(block_id="b1", name="t", content="c")
        reg.register(block)
        assert reg.get_or_none("b1") is not None
        assert reg.get_or_none("b2") is None

    def test_unregister(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(block_id="b1", name="t", content="c"))
        assert reg.unregister("b1")
        assert not reg.unregister("b1")

    def test_list_all(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(block_id="b1", name="a", content="x"))
        reg.register(KnowledgeBlock(block_id="b2", name="b", content="y"))
        assert reg.get_count() == 2
        assert len(reg.list()) == 2

    def test_list_by_priority(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(
            block_id="b1", name="low", content="x", priority=PriorityLevel.LOW,
        ))
        reg.register(KnowledgeBlock(
            block_id="b2", name="crit", content="y", priority=PriorityLevel.CRITICAL,
        ))
        blocks = reg.list(priority=PriorityLevel.CRITICAL)
        assert len(blocks) == 1
        assert blocks[0].block_id == "b2"

    def test_find_by_tag(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(
            block_id="b1", name="t", content="x", tags=("important", "code"),
        ))
        reg.register(KnowledgeBlock(
            block_id="b2", name="u", content="y", tags=("docs",),
        ))
        assert len(reg.find_by_tag("important")) == 1
        assert len(reg.find_by_tag("docs")) == 1
        assert len(reg.find_by_tag("code")) == 1

    def test_total_tokens(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(block_id="b1", name="t", content="a" * 40))
        reg.register(KnowledgeBlock(block_id="b2", name="u", content="a" * 80))
        assert reg.get_total_tokens() == 30  # 10 + 20

    def test_record_compaction_cycle(self):
        reg = KnowledgeBlockRegistry()
        reg.record_compaction_cycle(
            blocks_before=10, tokens_before=1000,
            blocks_after=5, tokens_after=300,
        )
        hist = reg.compaction_history
        assert len(hist) == 1
        assert hist[0]["tokens_saved"] == 700

    def test_summary(self):
        reg = KnowledgeBlockRegistry()
        reg.register(KnowledgeBlock(
            block_id="b1", name="t", content="x", priority=PriorityLevel.CRITICAL,
        ))
        s = reg.summary
        assert s["total_blocks"] == 1
        assert s["by_priority"]["CRITICAL"] == 1
        assert s["compaction_cycles"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Verbatim Pruner
# ═══════════════════════════════════════════════════════════════════════════


class TestVerbatimPruner:
    def test_prune_empty_raises(self):
        pruner = VerbatimPruner()
        with pytest.raises(CompressionError):
            pruner.prune("", 0.5)

    def test_prune_basic(self):
        pruner = VerbatimPruner()
        content = "line one\nline two\nline three\n"
        result = pruner.prune(content, 0.0)
        assert isinstance(result, PruneResult)
        assert result.original_length == len(content)

    def test_remove_boilerplate(self):
        pruner = VerbatimPruner()
        content = "Some text\nDISCLAIMER: This is confidential\nMore text"
        result = pruner.prune(content, 0.3)
        assert "DISCLAIMER" not in result.content

    def test_collapse_whitespace(self):
        pruner = VerbatimPruner()
        content = "a\n\n\n\nb\n\n\nc"
        result = pruner.prune(content, 0.2)
        assert "\n\n\n\n" not in result.content

    def test_remove_duplicates(self):
        pruner = VerbatimPruner()
        content = "a\na\na\na\nb\nb\nb\nc\n"
        result = pruner.prune(content, 0.2,
                              strategies=[PruneStrategy.REMOVE_DUPLICATES])
        assert result.pruned_length < result.original_length

    def test_code_blocks_preserved(self):
        pruner = VerbatimPruner()
        content = "Some text\n```\ncode block\n```\nmore text"
        # Boilerplate removal should not touch code blocks
        result = pruner.prune(content, 0.1)
        assert "```" in result.content
        assert "code block" in result.content

    def test_min_fidelity_threshold_respected(self):
        pruner = VerbatimPruner(min_fidelity_threshold=0.9)
        content = "\n".join([f"0123456789" for _ in range(500)])
        with pytest.raises(FidelityLossError):
            pruner.prune(content, 0.9)

    def test_compute_fidelity(self):
        pruner = VerbatimPruner()
        score = pruner.compute_fidelity("hello world", "hello")
        assert 0 < score < 1.0
        assert pruner.compute_fidelity("hello", "hello") == 1.0
        assert pruner.compute_fidelity("hello", "") == 0.0

    def test_prune_strategies_listed(self):
        pruner = VerbatimPruner()
        # Content with boilerplate and extra whitespace to trigger strategies
        content = "Some text here\n\n\n\n\ndisclaimer: this is confidential\nmore text"
        result = pruner.prune(content, 0.3)
        assert len(result.strategies_applied) > 0

    def test_truncate_long_outputs(self):
        pruner = VerbatimPruner()
        content = "\n".join([f"line {i}" for i in range(200)])
        result = pruner.prune(content, 0.5)
        # Should have truncated
        assert result.pruned_length < result.original_length


# ═══════════════════════════════════════════════════════════════════════════
# CompactionDecider
# ═══════════════════════════════════════════════════════════════════════════


class TestCompactionDecider:
    def test_should_compact_high_fill(self):
        decider = CompactionDecider(max_context_tokens=1000)
        assert decider.should_compact(950)  # 95% full

    def test_should_not_compact_low_fill(self):
        decider = CompactionDecider(
            max_context_tokens=1000, exploration_rate=0.0,
        )
        assert not decider.should_compact(100)  # 10% full

    def test_should_not_compact_immediately_after(self):
        decider = CompactionDecider(
            max_context_tokens=1000, min_time_between_compactions=9999,
        )
        decider.record_compaction("agent_1")
        assert not decider.should_compact(900, agent_id="agent_1")

    def test_always_compact_at_100_percent(self):
        decider = CompactionDecider(max_context_tokens=1000)
        assert decider.should_compact(1000)

    def test_decision_history(self):
        decider = CompactionDecider(max_context_tokens=1000)
        decider.should_compact(500)
        assert len(decider.decision_history) >= 1

    def test_reset_agent(self):
        decider = CompactionDecider(max_context_tokens=1000)
        decider.record_compaction("agent_1")
        decider.reset("agent_1")
        # After reset, should compact if fill is high
        assert decider.should_compact(900, agent_id="agent_1")

    def test_reset_all(self):
        decider = CompactionDecider(max_context_tokens=1000)
        decider.record_compaction("agent_1")
        decider.record_compaction("agent_2")
        decider.reset()
        assert len(decider.decision_history) == 0  # history is separate; only timestamps reset

    def test_task_phase_influence(self):
        decider = CompactionDecider(
            max_context_tokens=1000, exploration_rate=0.0,
        )
        # Same fill, different phases
        research_score = decider.should_compact(600, task_phase="research")
        debug_score = decider.should_compact(600, task_phase="debugging")
        assert debug_score >= research_score or not research_score

    def test_message_recency(self):
        decider = CompactionDecider(
            max_context_tokens=1000, exploration_rate=0.0,
        )
        recent = decider.should_compact(700, time_since_last_msg=1.0)
        idle = decider.should_compact(700, time_since_last_msg=120.0)
        # Idle should be at least as likely to compact
        assert idle >= recent or not recent


# ═══════════════════════════════════════════════════════════════════════════
# CompactionPlanner
# ═══════════════════════════════════════════════════════════════════════════


class TestCompactionPlanner:
    def test_plan_prunes_low_priority_first(self):
        planner = CompactionPlanner()
        blocks = [
            KnowledgeBlock(block_id="b1", name="low1", content="x" * 100,
                           priority=PriorityLevel.LOW),
            KnowledgeBlock(block_id="b2", name="norm", content="x" * 100,
                           priority=PriorityLevel.NORMAL),
            KnowledgeBlock(block_id="b3", name="crit", content="x" * 100,
                           priority=PriorityLevel.CRITICAL),
        ]
        actions = planner.plan(current_tokens=1000, target_tokens=500, blocks=blocks)
        assert len(actions) >= 1
        # First action should prune low priority
        assert actions[0].strategy in (CompactionStrategy.PRUNE, CompactionStrategy.SUMMARIZE)

    def test_plan_raises_on_invalid_target(self):
        planner = CompactionPlanner()
        with pytest.raises(CompactionError):
            planner.plan(100, 200, [])

    def test_plan_returns_defer_when_insufficient(self):
        planner = CompactionPlanner()
        blocks = [KnowledgeBlock(block_id="b1", name="crit", content="x",
                                 priority=PriorityLevel.CRITICAL)]
        actions = planner.plan(current_tokens=1000, target_tokens=100, blocks=blocks)
        assert any(a.strategy == CompactionStrategy.DEFER for a in actions)

    def test_plan_history(self):
        planner = CompactionPlanner()
        planner.plan(current_tokens=100, target_tokens=50, blocks=[])
        assert len(planner.plan_history) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# CompactionAction
# ═══════════════════════════════════════════════════════════════════════════


class TestCompactionAction:
    def test_create_action(self):
        action = CompactionAction(
            strategy=CompactionStrategy.PRUNE,
            tokens_before=1000,
            tokens_after=700,
            tokens_saved=300,
        )
        assert action.tokens_saved == 300

    def test_frozen_dataclass(self):
        action = CompactionAction(
            strategy=CompactionStrategy.PRUNE,
            tokens_before=1000,
            tokens_after=700,
        )
        with pytest.raises(Exception):
            action.tokens_saved = 999  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
# AsyncCompactor & CompactionJudge
# ═══════════════════════════════════════════════════════════════════════════


class TestCompactionJudge:
    @pytest.mark.asyncio
    async def test_evaluate_identical(self):
        judge = CompactionJudge()
        verdict, criteria = await judge.evaluate("hello world", "hello world")
        assert verdict == JudgeVerdict.PASS
        assert criteria.overall_score >= 0.8

    @pytest.mark.asyncio
    async def test_evaluate_empty_compacted(self):
        judge = CompactionJudge()
        verdict, criteria = await judge.evaluate("hello", "")
        assert verdict == JudgeVerdict.FAIL

    @pytest.mark.asyncio
    async def test_evaluate_reasonable_scores(self):
        judge = CompactionJudge()
        original = "The quick brown fox jumps over the lazy dog. " * 10
        compacted = "The quick fox jumps over the lazy dog. " * 3
        verdict, criteria = await judge.evaluate(original, compacted)
        assert 0 <= criteria.overall_score <= 1.0
        assert verdict in (JudgeVerdict.PASS, JudgeVerdict.FAIL, JudgeVerdict.NEEDS_REVIEW)

    def test_pass_rate(self):
        judge = CompactionJudge()
        assert judge.pass_rate == 1.0  # no evaluations yet


class TestAsyncCompactor:
    @pytest.mark.asyncio
    async def test_compact_async_basic(self):
        compactor = AsyncCompactor()
        context = "line " + "\n".join([f"content line {i}" for i in range(100)])
        result, action = await compactor.compact_async(context, target_ratio=0.5)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_compact_async_empty_raises(self):
        compactor = AsyncCompactor()
        with pytest.raises(CompactionError):
            await compactor.compact_async("")

    @pytest.mark.asyncio
    async def test_compact_async_small_context(self):
        compactor = AsyncCompactor()
        context = "small context"
        result, action = await compactor.compact_async(context, target_ratio=0.5)
        # Small content likely returns as-is
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_compactor_summary(self):
        compactor = AsyncCompactor()
        s = compactor.summary
        assert "total_operations" in s
        assert s["judge_pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_judge_history(self):
        judge = CompactionJudge()
        await judge.evaluate("a b c d e f g h i j", "a b c")
        assert len(judge.history) == 1

    @pytest.mark.asyncio
    async def test_compactor_with_metadata(self):
        compactor = AsyncCompactor()
        context = "\n".join([f"line {i}" for i in range(50)])
        result, action = await compactor.compact_async(
            context, target_ratio=0.3, metadata={"task": "test"}
        )
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_partial_rollback(self):
        compactor = AsyncCompactor()
        result, action = await compactor.compact_async(
            "a\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk\nl\nm\nn\no\np",
            target_ratio=0.8,
        )
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# Input Compressor
# ═══════════════════════════════════════════════════════════════════════════


class TestInputCompressor:
    def test_compress_empty_raises(self):
        compressor = InputCompressor()
        with pytest.raises(CompressionError):
            compressor.compress_command_output("ls", "")

    def test_compress_smart_filtering(self):
        compressor = InputCompressor()
        output = "\n".join([f"-rw-r--r--  1 user  staff  {i*100} May 1 12:00 file{i}.txt"
                           for i in range(50)])
        result = compressor.compress_command_output("ls", output,
                                                     CompressionStrategy.SMART_FILTERING)
        assert isinstance(result, CompressionResult)
        assert result.original_tokens > 0
        assert result.compression_ratio >= 0

    def test_compress_deduplication(self):
        compressor = InputCompressor()
        output = "a\nb\nb\nb\nb\nc\n"
        result = compressor.compress_command_output("cat", output,
                                                     CompressionStrategy.DEDUPLICATION)
        assert result.compressed_tokens < result.original_tokens

    def test_compress_truncation(self):
        compressor = InputCompressor()
        output = "\n".join([f"line {i}" for i in range(500)])
        result = compressor.compress_command_output("find", output,
                                                     CompressionStrategy.TRUNCATION)
        assert result.compressed_tokens < result.original_tokens

    def test_compress_grouping(self):
        compressor = InputCompressor()
        output = "\n".join([f"file{i}.txt" for i in range(200)])
        result = compressor.compress_command_output("ls", output,
                                                     CompressionStrategy.GROUPING)
        assert result.compression_ratio >= 0

    def test_command_pattern_detection(self):
        compressor = InputCompressor()
        output = "file1.txt\nfile2.txt\n"
        result = compressor.compress_command_output("git diff HEAD", output)
        assert result.original_tokens > 0

    def test_summary(self):
        compressor = InputCompressor()
        compressor.compress_command_output("ls", "file1\nfile2\n")
        s = compressor.summary
        assert s["total_compressions"] >= 1
        assert s["overall_compression_ratio"] >= 0

    def test_get_history(self):
        compressor = InputCompressor()
        compressor.compress_command_output("ls", "file1\n")
        history = compressor.get_history()
        assert len(history) == 1

    def test_compress_git_status(self):
        compressor = InputCompressor()
        output = " M file1.py\n M file2.py\n?? new.txt\n"
        result = compressor.compress_command_output("git status", output)
        assert isinstance(result, CompressionResult)

    def test_invalid_target_ratio(self):
        compressor = InputCompressor()
        with pytest.raises(CompressionError):
            compressor.compress_command_output("ls", "foo", target_ratio=1.5)

    def test_generic_fallback(self):
        compressor = InputCompressor()
        output = "\n".join([f"output {i}" for i in range(300)])
        result = compressor.compress_command_output("some_unknown_cmd", output)
        assert result.compressed_tokens > 0


# ═══════════════════════════════════════════════════════════════════════════
# Output Compressor
# ═══════════════════════════════════════════════════════════════════════════


class TestOutputCompressor:
    def test_compress_empty_raises(self):
        compressor = OutputCompressor()
        with pytest.raises(CompressionError):
            compressor.compress_response("")

    def test_compress_basic(self):
        compressor = OutputCompressor()
        text = "The implementation basically just works really well."
        result = compressor.compress_response(text)
        assert len(result) > 0

    def test_compress_reduces_length(self):
        compressor = OutputCompressor(
            config=CompressionConfig(aggression_level=0.9)
        )
        text = "It is important to note that the application configuration " \
               "should basically just work for the majority of users."
        result = compressor.compress_response(text)
        assert len(result) < len(text)

    def test_code_blocks_preserved(self):
        compressor = OutputCompressor()
        text = 'Use the `os.environ` module to access environment variables.'
        result = compressor.compress_response(text)
        assert "`os.environ`" in result

    def test_file_paths_preserved(self):
        compressor = OutputCompressor()
        text = "The config is at /etc/app/config.yaml"
        result = compressor.compress_response(text)
        assert "/etc/app/config.yaml" in result

    def test_abbreviations_applied(self):
        compressor = OutputCompressor(
            config=CompressionConfig(aggression_level=0.8)
        )
        text = "The configuration directory has the application implementation."
        result = compressor.compress_response(text)
        # Should have some abbreviations
        assert len(result) < len(text)

    def test_summary(self):
        compressor = OutputCompressor()
        compressor.compress_response("Hello world.")
        s = compressor.summary
        assert s["total_compressions"] == 1

    def test_technical_terms_preserved(self):
        compressor = OutputCompressor()
        text = "Run python3 --version to check implementation details."
        result = compressor.compress_response(text)
        assert "python3 --version" in result


# ═══════════════════════════════════════════════════════════════════════════
# DACS Manager
# ═══════════════════════════════════════════════════════════════════════════


class TestDACSManager:
    def test_register_agent(self):
        dacs = DACSManager()
        config = dacs.register_agent("agent_1", DACSMode.REGISTRY)
        assert config.agent_id == "agent_1"
        assert config.mode == DACSMode.REGISTRY

    def test_register_empty_id_raises(self):
        dacs = DACSManager()
        with pytest.raises(DACSConfigError):
            dacs.register_agent("")

    def test_register_invalid_budget_raises(self):
        dacs = DACSManager()
        with pytest.raises(DACSConfigError):
            dacs.register_agent("a1", token_budget=10)

    def test_register_invalid_summary_length_raises(self):
        dacs = DACSManager()
        with pytest.raises(DACSConfigError):
            dacs.register_agent("a1", summary_length=1)

    def test_unregister_agent(self):
        dacs = DACSManager()
        dacs.register_agent("agent_1")
        assert dacs.unregister_agent("agent_1")
        assert not dacs.unregister_agent("agent_1")

    def test_switch_mode(self):
        dacs = DACSManager()
        dacs.register_agent("agent_1", DACSMode.REGISTRY)
        config = dacs.switch_mode("agent_1", DACSMode.FOCUS)
        assert config.mode == DACSMode.FOCUS

    def test_switch_mode_unregistered_raises(self):
        dacs = DACSManager()
        with pytest.raises(DACSConfigError):
            dacs.switch_mode("unknown", DACSMode.FOCUS)

    def test_set_focus(self):
        dacs = DACSManager()
        dacs.register_agent("a1")
        dacs.register_agent("a2")
        focus = dacs.set_focus("a1")
        assert focus.mode == DACSMode.FOCUS
        assert dacs.get_focus_agent() == "a1"
        # Other agents should be in REGISTRY mode
        a2 = dacs.get_config("a2")
        assert a2.mode == DACSMode.REGISTRY

    def test_get_agents_in_mode(self):
        dacs = DACSManager()
        dacs.register_agent("a1", DACSMode.FOCUS)
        dacs.register_agent("a2")
        assert len(dacs.get_agents_in_mode(DACSMode.FOCUS)) == 1
        assert len(dacs.get_agents_in_mode(DACSMode.REGISTRY)) == 1

    def test_get_config_unregistered_raises(self):
        dacs = DACSManager()
        with pytest.raises(DACSConfigError):
            dacs.get_config("unknown")

    def test_get_agent_ids(self):
        dacs = DACSManager()
        dacs.register_agent("a1")
        dacs.register_agent("a2")
        assert sorted(dacs.get_agent_ids()) == ["a1", "a2"]

    def test_update_config(self):
        dacs = DACSManager()
        dacs.register_agent("a1")
        updated = dacs.update_config("a1", token_budget=5000)
        assert updated.token_budget == 5000

    def test_estimate_context_allocation(self):
        dacs = DACSManager()
        dacs.register_agent("a1", DACSMode.REGISTRY)
        est = dacs.estimate_context_allocation("a1")
        assert est["mode"] == "REGISTRY"
        assert est["summary_tokens"] > 0

    def test_summary(self):
        dacs = DACSManager()
        dacs.register_agent("a1")
        s = dacs.summary
        assert s["agents_registered"] == 1
        assert "mode_counts" in s
        assert "focus_agent" in s


# ═══════════════════════════════════════════════════════════════════════════
# Compression Metrics
# ═══════════════════════════════════════════════════════════════════════════


class TestCompressionMetrics:
    def test_record(self):
        cm = CompressionMetrics()
        snapshot = cm.record(
            strategy="prune", task_type="code",
            tokens_before=1000, tokens_after=300, time_taken_ms=50.0,
        )
        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.compression_ratio == pytest.approx(0.7, abs=0.01)

    def test_get_snapshots(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        snapshots = cm.get_snapshots()
        assert len(snapshots) == 1

    def test_get_snapshots_filtered(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        cm.record("summary", "docs", 500, 100, 30.0)
        assert len(cm.get_snapshots(strategy="prune")) == 1
        assert len(cm.get_snapshots(task_type="docs")) == 1

    def test_get_strategy_stats(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        cm.record("prune", "code", 2000, 600, 100.0)
        stats = cm.get_strategy_stats("prune")
        assert stats is not None
        assert stats.count == 2
        assert stats.strategy == "prune"

    def test_get_strategy_stats_nonexistent(self):
        cm = CompressionMetrics()
        assert cm.get_strategy_stats("nonexistent") is None

    def test_get_task_type_summary(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        summary = cm.get_task_type_summary("code")
        assert summary is not None
        assert summary["event_count"] == 1

    def test_get_task_type_summary_nonexistent(self):
        cm = CompressionMetrics()
        assert cm.get_task_type_summary("nonexistent") is None

    def test_get_optimization_suggestions(self):
        cm = CompressionMetrics()
        # Add enough data to generate suggestions
        cm.record("prune", "code", 1000, 950, 50.0, fidelity_score=0.5)
        cm.record("prune", "code", 2000, 1900, 100.0, fidelity_score=0.4)
        suggestions = cm.get_optimization_suggestions()
        # At least one suggestion should mention fidelity
        fidelity_suggestions = [s for s in suggestions if "fidelity" in s]
        assert len(fidelity_suggestions) >= 1

    def test_get_optimization_suggestions_empty(self):
        cm = CompressionMetrics()
        assert len(cm.get_optimization_suggestions()) == 0

    def test_generate_report(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        cm.record("summary", "docs", 500, 100, 30.0)
        report = cm.generate_report()
        assert isinstance(report, MetricsReport)
        assert report.total_events == 2
        assert report.total_tokens_saved == 1100
        assert len(report.strategy_stats) == 2
        assert "code" in report.task_type_stats

    def test_export_json(self):
        cm = CompressionMetrics()
        cm.record("prune", "code", 1000, 300, 50.0)
        data = cm.export_json()
        assert data["total_events"] == 1
        assert len(data["recent_snapshots"]) == 1

    def test_fidelity_clamping(self):
        cm = CompressionMetrics()
        snapshot = cm.record(
            "prune", "code", 1000, 300, 50.0, fidelity_score=2.0,
        )
        assert snapshot.fidelity_score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════
# Package-level imports
# ═══════════════════════════════════════════════════════════════════════════


class TestPackage:
    def test_all_exports_available(self):
        """Verify all expected symbols are importable from the package."""
        expected = [
            "CompactionDecider", "CompactionStrategy", "CompactionPlanner",
            "CompactionAction", "VerbatimPruner", "PruneStrategy",
            "PruneResult", "AsyncCompactor", "CompactionJudge",
            "JudgeVerdict", "KnowledgeBlock", "PriorityLevel",
            "KnowledgeBlockRegistry", "InputCompressor",
            "CompressionStrategy", "CompressionResult",
            "OutputCompressor", "CompressionConfig",
            "DACSManager", "DACSMode", "DACSConfig",
            "CompressionMetrics", "MetricsSnapshot", "StrategyStats",
            "MetricsReport", "ContextOptimizerError", "CompactionError",
            "CompressionError", "KnowledgeBlockNotFoundError",
            "DACSConfigError", "FidelityLossError",
        ]
        for name in expected:
            assert hasattr(__import__("lyra_context_optimizer"), name), \
                f"Missing export: {name}"
