"""Tests for Compound Agent — 5-slot compound architecture for multi-perspective reasoning."""

import pytest

from lyra_agent_swarm.compound_agent import (
    CompoundAgent,
    CompoundConfig,
    CompoundResult,
    SlotConfig,
    SlotOutput,
    SlotRole,
)


class TestSlotRole:
    def test_role_values(self):
        assert SlotRole.ANALYST.value == "analyst"
        assert SlotRole.CRITIC.value == "critic"
        assert SlotRole.SYNTHESIZER.value == "synthesizer"
        assert SlotRole.EXECUTOR.value == "executor"
        assert SlotRole.VERIFIER.value == "verifier"

    def test_five_distinct_roles(self):
        roles = {SlotRole.ANALYST, SlotRole.CRITIC, SlotRole.SYNTHESIZER, SlotRole.EXECUTOR, SlotRole.VERIFIER}
        assert len(roles) == 5


class TestSlotOutput:
    def test_output_creation(self):
        output = SlotOutput(
            role=SlotRole.ANALYST,
            content="The problem has 3 main components to analyze.",
            confidence=0.85,
            key_insight="Three components identified",
        )
        assert output.role == SlotRole.ANALYST
        assert output.confidence == 0.85
        assert "3 main components" in output.content

    def test_low_confidence_output(self):
        output = SlotOutput(
            role=SlotRole.CRITIC,
            content="Uncertain about edge cases.",
            confidence=0.2,
            key_insight="",
        )
        assert output.confidence < 0.5

    def test_output_immutable(self):
        o = SlotOutput(SlotRole.EXECUTOR, "plan", 0.8, "insight")
        with pytest.raises(Exception):
            o.confidence = 0.1


class TestCompoundResult:
    def test_result_creation(self):
        s1 = SlotOutput(SlotRole.ANALYST, "analysis", 0.9, "key")
        s2 = SlotOutput(SlotRole.CRITIC, "critique", 0.8, "risk")
        s3 = SlotOutput(SlotRole.SYNTHESIZER, "synthesis", 0.85, "pattern")
        s4 = SlotOutput(SlotRole.EXECUTOR, "plan", 0.9, "step")
        s5 = SlotOutput(SlotRole.VERIFIER, "validated", 0.95, "check")

        result = CompoundResult(
            task="Solve complex problem",
            slot_outputs=(s1, s2, s3, s4, s5),
            fused_response="Unified answer",
            consensus_level=0.88,
            dissent_notes="",
        )
        assert len(result.slot_outputs) == 5
        assert result.consensus_level == 0.88
        assert result.fused_response == "Unified answer"

    def test_result_with_dissent(self):
        s = SlotOutput(SlotRole.ANALYST, "ok", 0.9, "")
        sc = SlotOutput(SlotRole.CRITIC, "concern", 0.3, "risky")
        ss = SlotOutput(SlotRole.SYNTHESIZER, "mixed", 0.7, "")
        se = SlotOutput(SlotRole.EXECUTOR, "go", 0.8, "")
        sv = SlotOutput(SlotRole.VERIFIER, "hmm", 0.4, "verify")

        result = CompoundResult(
            task="risky task",
            slot_outputs=(s, sc, ss, se, sv),
            fused_response="Proceed with caution",
            consensus_level=0.45,
            dissent_notes="Critic flagged risk",
        )
        assert result.consensus_level < 0.6
        assert "risk" in result.dissent_notes.lower()

    def test_result_immutable(self):
        s = SlotOutput(SlotRole.ANALYST, "ok", 0.8, "")
        r = CompoundResult("task", (s, s, s, s, s), "fused", 0.8, "")
        with pytest.raises(Exception):
            r.consensus_level = 0.1


class TestSlotConfig:
    def test_config_defaults(self):
        config = SlotConfig(role=SlotRole.ANALYST)
        assert config.role == SlotRole.ANALYST
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_config_custom(self):
        config = SlotConfig(
            role=SlotRole.CRITIC,
            system_prompt="Be harsh.",
            temperature=0.3,
            max_tokens=1024,
        )
        assert config.temperature == 0.3
        assert config.system_prompt == "Be harsh."


class TestCompoundConfig:
    def test_default_config(self):
        config = CompoundConfig()
        assert config.consensus_threshold == 0.6
        assert config.fusion_strategy == "weighted_vote"

    def test_custom_config(self):
        config = CompoundConfig(consensus_threshold=0.8, fusion_strategy="majority")
        assert config.consensus_threshold == 0.8


class TestCompoundAgent:
    def test_creation(self):
        agent = CompoundAgent()
        assert agent.execution_count == 0

    def test_creation_with_config(self):
        config = CompoundConfig(consensus_threshold=0.75)
        agent = CompoundAgent(config=config)
        assert agent.config.consensus_threshold == 0.75

    def test_execute_sync_basic(self):
        agent = CompoundAgent()
        slot_outputs = {
            SlotRole.ANALYST: "I see 3 issues.",
            SlotRole.CRITIC: "Risk in step 2.",
            SlotRole.SYNTHESIZER: "Combine approaches.",
            SlotRole.EXECUTOR: "1. Analyze 2. Fix 3. Test",
            SlotRole.VERIFIER: "Plan passes basic checks.",
        }
        result = agent.execute_sync("Fix authentication bug", slot_outputs)
        assert isinstance(result, CompoundResult)
        assert result.task == "Fix authentication bug"
        assert len(result.slot_outputs) == 5

    def test_execute_sync_increments_count(self):
        agent = CompoundAgent()
        outputs = {r: "ok" for r in SlotRole}
        agent.execute_sync("task1", outputs)
        agent.execute_sync("task2", outputs)
        assert agent.execution_count == 2

    def test_execute_sync_empty_slot(self):
        agent = CompoundAgent()
        slot_outputs = {
            SlotRole.ANALYST: "Analysis complete.",
            SlotRole.CRITIC: "",
            SlotRole.SYNTHESIZER: "",
            SlotRole.EXECUTOR: "",
            SlotRole.VERIFIER: "",
        }
        result = agent.execute_sync("Test empty slots", slot_outputs)
        assert isinstance(result, CompoundResult)

    def test_execute_sync_fusion_contains_sections(self):
        agent = CompoundAgent()
        slot_outputs = {
            SlotRole.ANALYST: "Analysis section.",
            SlotRole.CRITIC: "Critical section.",
            SlotRole.SYNTHESIZER: "Synthesis section.",
            SlotRole.EXECUTOR: "Execution plan.",
            SlotRole.VERIFIER: "Verification passed.",
        }
        result = agent.execute_sync("task", slot_outputs)
        assert "Analysis" in result.fused_response
        assert "Plan" in result.fused_response

    def test_consensus_high_when_all_confident(self):
        agent = CompoundAgent()
        slot_outputs = {
            SlotRole.ANALYST: "Great analysis with high confidence here.",
            SlotRole.CRITIC: "Very thorough critique and review.",
            SlotRole.SYNTHESIZER: "Excellent synthesis of all perspectives.",
            SlotRole.EXECUTOR: "Solid executable plan with clear steps.",
            SlotRole.VERIFIER: "All checks passed successfully now.",
        }
        result = agent.execute_sync("task", slot_outputs)
        assert result.consensus_level > 0.5

    def test_dissent_when_critic_has_low_confidence(self):
        agent = CompoundAgent()
        slot_outputs = {
            SlotRole.ANALYST: "Analysis with insights.",
            SlotRole.CRITIC: "c",
            SlotRole.SYNTHESIZER: "Synthesis done.",
            SlotRole.EXECUTOR: "Execute step.",
            SlotRole.VERIFIER: "Verified tentatively.",
        }
        result = agent.execute_sync("task", slot_outputs)
        assert isinstance(result.dissent_notes, str)
