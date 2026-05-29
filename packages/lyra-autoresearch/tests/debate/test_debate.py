"""Tests for lyra-autoresearch debate module."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from lyra_autoresearch.debate import (
    DebateAgent,
    DebateMessage,
    DebatePanel,
    DebateResult,
    DebateRound,
    Perspective,
    run_debate,
)


class TestDebateMessage:
    def test_creation(self):
        msg = DebateMessage(perspective=Perspective.SKEPTIC, content="test message", round_number=1)
        assert msg.perspective == Perspective.SKEPTIC
        assert msg.content == "test message"
        assert msg.round_number == 1

    def test_equality(self):
        m1 = DebateMessage(Perspective.SKEPTIC, "same", 1)
        m2 = DebateMessage(Perspective.SKEPTIC, "same", 1)
        assert m1 == m2

    def test_different_content_not_equal(self):
        m1 = DebateMessage(Perspective.SKEPTIC, "a", 1)
        m2 = DebateMessage(Perspective.SKEPTIC, "b", 1)
        assert m1 != m2


class TestDebateRound:
    def test_creation_empty_messages(self):
        r = DebateRound(round_number=1, messages=[])
        assert r.round_number == 1
        assert r.messages == []
        assert r.synthesis is None

    def test_creation_with_synthesis(self):
        msgs = [DebateMessage(Perspective.SKEPTIC, "msg", 1)]
        r = DebateRound(round_number=2, messages=msgs, synthesis="summary")
        assert r.synthesis == "summary"
        assert len(r.messages) == 1


class TestDebateResult:
    def test_full_result(self):
        result = DebateResult(
            topic="Test topic",
            rounds=[],
            final_synthesis="done",
            consensus_reached=True,
            key_insights=["insight1", "insight2"],
        )
        assert result.topic == "Test topic"
        assert result.consensus_reached is True
        assert len(result.key_insights) == 2

    def test_no_consensus(self):
        result = DebateResult(
            topic="T", rounds=[], final_synthesis="s", consensus_reached=False, key_insights=[]
        )
        assert not result.consensus_reached


class TestDebateAgentCore:
    """Tests that don't require real LLM clients."""

    def test_init_sets_perspective_and_model(self):
        agent = DebateAgent(Perspective.SKEPTIC, None, model="claude-3-opus")
        assert agent.perspective == Perspective.SKEPTIC
        assert agent.model == "claude-3-opus"

    def test_all_perspectives_exist(self):
        perspectives = [
            Perspective.SKEPTIC,
            Perspective.OPTIMIST,
            Perspective.METHODOLOGIST,
            Perspective.DOMAIN_EXPERT,
            Perspective.PRAGMATIST,
        ]
        assert len(perspectives) == 5
        assert len({p.value for p in perspectives}) == 5

    def test_unsupported_client_returns_error(self):
        agent = DebateAgent(Perspective.SKEPTIC, "not_a_client")
        result = agent.generate_response("topic", "context", [])
        assert "Error" in result


class TestDebateAgentWithMockedLLM:
    """Tests using proper mocking to pass isinstance checks."""

    @pytest.fixture
    def fake_anthropic(self):
        class FakeAnthropic:
            class messages:
                @staticmethod
                def create(model=None, max_tokens=None, system=None, messages=None):
                    m = Mock()
                    m.content = [Mock()]
                    m.content[0].text = f"Response via {model or 'default'}"
                    return m

        return FakeAnthropic()

    @pytest.fixture
    def fake_openai(self):
        class FakeOpenAI:
            class chat:
                class completions:
                    @staticmethod
                    def create(model=None, max_tokens=None, messages=None):
                        m = Mock()
                        m.choices = [Mock()]
                        m.choices[0].message.content = f"Response via {model or 'default'}"
                        return m

        return FakeOpenAI()

    def test_anthropic_response(self, fake_anthropic):
        with patch("lyra_autoresearch.debate.Anthropic", new=lambda: fake_anthropic):
            agent = DebateAgent(Perspective.SKEPTIC, fake_anthropic)
            result = agent.generate_response("topic", "context", [])
            assert isinstance(result, str)
            assert len(result) > 0

    def test_openai_response(self, fake_openai):
        with patch("lyra_autoresearch.debate.OpenAI", new=lambda: fake_openai):
            agent = DebateAgent(Perspective.OPTIMIST, fake_openai)
            result = agent.generate_response("topic", "context", [])
            assert isinstance(result, str)
            assert len(result) > 0

    def test_error_handling(self, fake_anthropic):
        fake_anthropic.messages.create = Mock(side_effect=Exception("API Down"))
        with patch("lyra_autoresearch.debate.Anthropic", new=lambda: fake_anthropic):
            agent = DebateAgent(Perspective.SKEPTIC, fake_anthropic)
            result = agent.generate_response("topic", "context", [])
            assert "Error" in result

    def test_prior_messages_context(self, fake_anthropic):
        with patch("lyra_autoresearch.debate.Anthropic", new=lambda: fake_anthropic):
            agent = DebateAgent(Perspective.METHODOLOGIST, fake_anthropic)
            prior = [DebateMessage(Perspective.SKEPTIC, "prior msg", 1)]
            result = agent.generate_response("topic", "context", prior)
            assert isinstance(result, str)


class TestDebatePanelWithMocks:
    @pytest.fixture(autouse=True)
    def _patch_and_client(self):
        """Patch Anthropic and provide a working fake client."""
        import lyra_autoresearch.debate as debate_mod

        orig = getattr(debate_mod, "Anthropic", None)
        FakeAnthropic = type("Anthropic", (), {})
        debate_mod.Anthropic = FakeAnthropic

        class FakeLLM(FakeAnthropic):
            class messages:
                @staticmethod
                def create(model=None, max_tokens=None, system=None, messages=None):
                    m = Mock()
                    m.content = [Mock()]
                    m.content[0].text = "Panel response text"
                    return m

        self.fake_client = FakeLLM()
        yield
        if orig is not None:
            debate_mod.Anthropic = orig

    def test_run_round_produces_messages(self):
        panel = DebatePanel(
            perspectives=[Perspective.SKEPTIC, Perspective.OPTIMIST],
            llm_client=self.fake_client,
        )
        r = panel.run_round("topic", "context", 1, [])
        assert isinstance(r, DebateRound)
        assert r.round_number == 1
        assert len(r.messages) == 2

    def test_run_debate_returns_full_result(self):
        panel = DebatePanel(
            perspectives=[Perspective.SKEPTIC],
            llm_client=self.fake_client,
        )
        result = panel.run_debate("question", "bg", num_rounds=2)
        assert isinstance(result, DebateResult)
        assert result.topic == "question"
        assert len(result.rounds) == 2
        assert len(result.key_insights) <= 5

    def test_consensus_heuristic_works(self):
        m = Mock()
        m.content = [Mock()]
        m.content[0].text = "We have consensus and agreement on this approach."
        self.fake_client.messages.create = Mock(return_value=m)
        panel = DebatePanel(
            perspectives=[Perspective.SKEPTIC],
            llm_client=self.fake_client,
        )
        result = panel.run_debate("t", "c", num_rounds=2)
        assert result.consensus_reached is True

    def test_single_round_no_consensus(self):
        panel = DebatePanel(
            perspectives=[Perspective.SKEPTIC],
            llm_client=self.fake_client,
        )
        result = panel.run_debate("t", "c", num_rounds=1)
        assert result.consensus_reached is False


class TestRunDebateConvenience:
    def test_no_client_raises_error(self):
        with patch("lyra_autoresearch.debate.Anthropic", side_effect=Exception("no key")):
            with patch("lyra_autoresearch.debate.OpenAI", side_effect=Exception("no key")):
                with pytest.raises(ValueError, match="No LLM client"):
                    run_debate("topic", "context")
