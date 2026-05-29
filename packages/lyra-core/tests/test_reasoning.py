"""
Tests for Multi-Hop Reasoning System
"""

import pytest
from lyra_core.reasoning import (
    ReasoningType,
    ReasoningStep,
    ReasoningChain,
    MultiHopReasoner
)


class TestReasoningStep:
    """Test ReasoningStep"""

    def test_initialization(self):
        """Test step initialization"""
        step = ReasoningStep(
            id="step1",
            type=ReasoningType.INFERENCE,
            content="Test inference"
        )
        assert step.id == "step1"
        assert step.type == ReasoningType.INFERENCE
        assert step.confidence == 1.0

    def test_add_evidence(self):
        """Test adding evidence"""
        step = ReasoningStep(
            id="step1",
            type=ReasoningType.INFERENCE,
            content="Test"
        )
        step.add_evidence("evidence1")
        step.add_evidence("evidence2")

        assert len(step.evidence) == 2
        assert "evidence1" in step.evidence


class TestReasoningChain:
    """Test ReasoningChain"""

    def test_initialization(self):
        """Test chain initialization"""
        chain = ReasoningChain(id="chain1")
        assert chain.id == "chain1"
        assert len(chain.steps) == 0

    def test_add_step(self):
        """Test adding steps"""
        chain = ReasoningChain(id="chain1")
        step = ReasoningStep(
            id="step1",
            type=ReasoningType.RETRIEVAL,
            content="Retrieve data"
        )
        chain.add_step(step)

        assert len(chain.steps) == 1
        assert chain.steps[0].id == "step1"

    def test_confidence_update(self):
        """Test confidence updates"""
        chain = ReasoningChain(id="chain1")

        step1 = ReasoningStep(
            id="step1",
            type=ReasoningType.INFERENCE,
            content="High confidence",
            confidence=0.9
        )
        step2 = ReasoningStep(
            id="step2",
            type=ReasoningType.INFERENCE,
            content="Low confidence",
            confidence=0.5
        )

        chain.add_step(step1)
        chain.add_step(step2)

        # Chain confidence should be minimum
        assert chain.confidence == 0.5


class TestMultiHopReasoner:
    """Test MultiHopReasoner"""

    def test_initialization(self):
        """Test reasoner initialization"""
        reasoner = MultiHopReasoner()
        assert len(reasoner.chains) == 0
        assert len(reasoner.steps) == 0

    def test_create_chain(self):
        """Test chain creation"""
        reasoner = MultiHopReasoner()
        chain = reasoner.create_chain()

        assert chain.id in reasoner.chains
        assert len(chain.steps) == 0

    def test_add_step(self):
        """Test adding steps to chain"""
        reasoner = MultiHopReasoner()
        chain = reasoner.create_chain()

        step = reasoner.add_step(
            chain.id,
            ReasoningType.RETRIEVAL,
            "Retrieve information"
        )

        assert step.id in reasoner.steps
        assert len(chain.steps) == 1

    def test_link_evidence(self):
        """Test linking evidence"""
        reasoner = MultiHopReasoner()
        chain = reasoner.create_chain()
        step = reasoner.add_step(
            chain.id,
            ReasoningType.INFERENCE,
            "Make inference"
        )

        reasoner.link_evidence(step.id, "evidence1")

        assert "evidence1" in step.evidence

    def test_conclude_chain(self):
        """Test concluding a chain"""
        reasoner = MultiHopReasoner()
        chain = reasoner.create_chain()

        reasoner.add_step(chain.id, ReasoningType.RETRIEVAL, "Step 1")
        reasoner.add_step(chain.id, ReasoningType.INFERENCE, "Step 2")
        reasoner.conclude_chain(chain.id, "Final conclusion")

        assert chain.conclusion == "Final conclusion"

    def test_find_chains_with_evidence(self):
        """Test finding chains by evidence"""
        reasoner = MultiHopReasoner()

        chain1 = reasoner.create_chain()
        step1 = reasoner.add_step(chain1.id, ReasoningType.RETRIEVAL, "Step 1")
        reasoner.link_evidence(step1.id, "evidence_A")

        chain2 = reasoner.create_chain()
        step2 = reasoner.add_step(chain2.id, ReasoningType.INFERENCE, "Step 2")
        reasoner.link_evidence(step2.id, "evidence_B")

        chains = reasoner.find_chains_with_evidence("evidence_A")
        assert len(chains) == 1
        assert chains[0].id == chain1.id

    def test_get_reasoning_path(self):
        """Test getting reasoning path"""
        reasoner = MultiHopReasoner()
        chain = reasoner.create_chain()

        reasoner.add_step(chain.id, ReasoningType.RETRIEVAL, "Retrieve data")
        reasoner.add_step(chain.id, ReasoningType.INFERENCE, "Make inference")
        reasoner.conclude_chain(chain.id, "Final answer")

        path = reasoner.get_reasoning_path(chain.id)
        assert len(path) == 3
        assert "Retrieve data" in path[0]
        assert "Final answer" in path[2]

    def test_get_stats(self):
        """Test statistics collection"""
        reasoner = MultiHopReasoner()

        chain1 = reasoner.create_chain()
        reasoner.add_step(chain1.id, ReasoningType.RETRIEVAL, "Step 1")
        reasoner.add_step(chain1.id, ReasoningType.INFERENCE, "Step 2")

        chain2 = reasoner.create_chain()
        reasoner.add_step(chain2.id, ReasoningType.SYNTHESIS, "Step 3")

        stats = reasoner.get_stats()
        assert stats['total_chains'] == 2
        assert stats['total_steps'] == 3
        assert stats['avg_chain_length'] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
