"""Tests for CompoundAgent in research analysis — 5-slot multi-perspective."""

from __future__ import annotations

import pytest
from lyra_agent_swarm.compound_agent import (
    CompoundAgent,
    CompoundConfig,
    CompoundResult,
    SlotConfig,
    SlotOutput,
    SlotRole,
)

# ── Helpers ────────────────────────────────────────────────────────────


def _make_agent() -> CompoundAgent:
    config = CompoundConfig(
        slots={
            SlotRole.ANALYST: SlotConfig(role=SlotRole.ANALYST),
            SlotRole.CRITIC: SlotConfig(role=SlotRole.CRITIC),
            SlotRole.SYNTHESIZER: SlotConfig(role=SlotRole.SYNTHESIZER),
            SlotRole.EXECUTOR: SlotConfig(role=SlotRole.EXECUTOR),
            SlotRole.VERIFIER: SlotConfig(role=SlotRole.VERIFIER),
        }
    )
    return CompoundAgent(config=config)


def _slot_fns() -> dict[SlotRole, object]:
    async def analyst(task: str) -> str:
        return f"ANALYSIS: {task} — key components identified"

    async def critic(task: str) -> str:
        return f"CRITIQUE: {task} — edge cases and risks noted"

    async def synthesizer(task: str) -> str:
        return f"SYNTHESIS: {task} — patterns unified"

    async def executor(task: str) -> str:
        return f"EXECUTION: {task} — plan proposed"

    async def verifier(task: str) -> str:
        return f"VERIFICATION: {task} — output validated"

    return {
        SlotRole.ANALYST: analyst,
        SlotRole.CRITIC: critic,
        SlotRole.SYNTHESIZER: synthesizer,
        SlotRole.EXECUTOR: executor,
        SlotRole.VERIFIER: verifier,
    }


# ── SlotRole / CompoundConfig ──────────────────────────────────────────


class TestSlotRole:
    def test_all_five_roles_exist(self):
        roles = list(SlotRole)
        assert SlotRole.ANALYST in roles
        assert SlotRole.CRITIC in roles
        assert SlotRole.SYNTHESIZER in roles
        assert SlotRole.EXECUTOR in roles
        assert SlotRole.VERIFIER in roles

    def test_role_values_distinct(self):
        values = [r.value for r in SlotRole]
        assert len(values) == len(set(values))


class TestCompoundConfig:
    def test_default_config(self):
        cfg = CompoundConfig()
        assert cfg.consensus_threshold == 0.6
        assert cfg.fusion_strategy == "weighted_vote"

    def test_custom_threshold(self):
        cfg = CompoundConfig(consensus_threshold=0.85)
        assert cfg.consensus_threshold == 0.85

    def test_slot_config_defaults(self):
        sc = SlotConfig(role=SlotRole.ANALYST)
        assert sc.role == SlotRole.ANALYST
        assert sc.temperature == 0.7
        assert sc.max_tokens == 2048


# ── CompoundAgent execution ─────────────────────────────────────────────


class TestCompoundAgentExecution:
    @pytest.mark.asyncio
    async def test_execute_returns_compound_result(self):
        agent = _make_agent()
        result = await agent.execute("Analyze transformer attention paper", _slot_fns())
        assert isinstance(result, CompoundResult)
        assert result.task == "Analyze transformer attention paper"

    @pytest.mark.asyncio
    async def test_five_slots_all_executed(self):
        agent = _make_agent()
        result = await agent.execute("Research topic: RLHF safety", _slot_fns())
        assert len(result.slot_outputs) == 5
        roles = {s.role for s in result.slot_outputs}
        assert roles == {
            SlotRole.ANALYST,
            SlotRole.CRITIC,
            SlotRole.SYNTHESIZER,
            SlotRole.EXECUTOR,
            SlotRole.VERIFIER,
        }

    @pytest.mark.asyncio
    async def test_fused_response_non_empty(self):
        agent = _make_agent()
        result = await agent.execute("Research question", _slot_fns())
        assert len(result.fused_response) > 0

    @pytest.mark.asyncio
    async def test_consensus_level_in_range(self):
        agent = _make_agent()
        result = await agent.execute("Test task", _slot_fns())
        assert 0.0 <= result.consensus_level <= 1.0

    @pytest.mark.asyncio
    async def test_parallel_execution_ordering(self):
        """All 5 slots should run; order is not guaranteed due to asyncio.gather."""
        agent = _make_agent()
        result = await agent.execute("Parallel research analysis", _slot_fns())
        # Verify each role produced output
        role_outputs = {s.role: s.content for s in result.slot_outputs}
        assert SlotRole.ANALYST in role_outputs
        assert SlotRole.CRITIC in role_outputs
        assert SlotRole.VERIFIER in role_outputs

    @pytest.mark.asyncio
    async def test_execution_count_increments(self):
        agent = _make_agent()
        assert agent._execution_count == 0
        await agent.execute("First task", _slot_fns())
        assert agent._execution_count == 1
        await agent.execute("Second task", _slot_fns())
        assert agent._execution_count == 2


# ── Research-specific compound patterns ─────────────────────────────────


class TestCompoundResearchAnalysis:
    @pytest.mark.asyncio
    async def test_analyst_breaks_down_research_problem(self):
        agent = _make_agent()
        result = await agent.execute(
            "Analyze the claim: 'larger models always generalize better'",
            _slot_fns(),
        )
        analyst_output = [s for s in result.slot_outputs if s.role == SlotRole.ANALYST][0]
        assert "ANALYSIS" in analyst_output.content

    @pytest.mark.asyncio
    async def test_critic_challenges_research_assumptions(self):
        agent = _make_agent()
        result = await agent.execute(
            "Evaluate methodology: 'small sample size study on attention'",
            _slot_fns(),
        )
        critic_output = [s for s in result.slot_outputs if s.role == SlotRole.CRITIC][0]
        assert "CRITIQUE" in critic_output.content

    @pytest.mark.asyncio
    async def test_synthesizer_unifies_research_perspectives(self):
        agent = _make_agent()
        result = await agent.execute("Synthesize findings across 3 papers", _slot_fns())
        synth_output = [s for s in result.slot_outputs if s.role == SlotRole.SYNTHESIZER][0]
        assert "SYNTHESIS" in synth_output.content

    @pytest.mark.asyncio
    async def test_verifier_validates_research_output(self):
        agent = _make_agent()
        result = await agent.execute("Verify research conclusions", _slot_fns())
        verifier_output = [s for s in result.slot_outputs if s.role == SlotRole.VERIFIER][0]
        assert "VERIFICATION" in verifier_output.content

    @pytest.mark.asyncio
    async def test_dissent_notes_preserve_minority_views(self):
        agent = _make_agent()
        result = await agent.execute("Controversial research topic", _slot_fns())
        assert isinstance(result.dissent_notes, str)


# ── SlotOutput / CompoundResult dataclass contracts ────────────────────


class TestDataclassContracts:
    def test_slot_output_immutable(self):
        so = SlotOutput(role=SlotRole.ANALYST, content="test", confidence=0.9, key_insight="key")
        assert so.confidence == 0.9
        assert so.key_insight == "key"

    def test_compound_result_has_all_required_fields(self):
        slots = tuple(
            SlotOutput(role=r, content=f"output-{r.value}", confidence=0.85, key_insight=f"insight-{r.value}")
            for r in SlotRole
        )
        result = CompoundResult(
            task="test task",
            slot_outputs=slots,  # type: ignore[arg-type]
            fused_response="unified response",
            consensus_level=0.8,
            dissent_notes="minor objection noted",
        )
        assert result.consensus_level == 0.8
        assert "minor objection" in result.dissent_notes
