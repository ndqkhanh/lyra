"""Contract tests for the scripted mock-LLM harness."""
from __future__ import annotations

import pytest

from lyra_core.mock_llm import (
    MockLLMError,
    ScenarioCase,
    ScriptedLLM,
    StreamChunk,
)


def test_generate_returns_scripted_response_in_order() -> None:
    llm = ScriptedLLM(
        scenario=[
            ScenarioCase(
                expected_user_substring="hello",
                response={"role": "assistant", "content": "hi back", "stop_reason": "end_turn"},
            )
        ]
    )
    out = llm.generate(messages=[{"role": "user", "content": "hello world"}])
    assert out["content"] == "hi back"
    llm.assert_exhausted()


def test_generate_raises_when_user_substring_missing() -> None:
    llm = ScriptedLLM(
        scenario=[
            ScenarioCase(
                expected_user_substring="fizzbuzz",
                response={"role": "assistant", "content": "", "stop_reason": "end_turn"},
            )
        ]
    )
    with pytest.raises(MockLLMError, match="expected user substring"):
        llm.generate(messages=[{"role": "user", "content": "not it"}])


def test_generate_raises_when_scenario_exhausted() -> None:
    llm = ScriptedLLM(scenario=[])
    with pytest.raises(MockLLMError, match="exhausted"):
        llm.generate(messages=[{"role": "user", "content": "x"}])


def test_assert_exhausted_detects_unused_cases() -> None:
    llm = ScriptedLLM(
        scenario=[
            ScenarioCase(
                expected_user_substring="unused",
                response={"role": "assistant", "content": "x", "stop_reason": "end_turn"},
            )
        ]
    )
    with pytest.raises(MockLLMError, match="unused cases"):
        llm.assert_exhausted()


def test_stream_generate_yields_scripted_chunks_in_order() -> None:
    llm = ScriptedLLM(
        scenario=[
            ScenarioCase(
                expected_user_substring="stream me",
                response={},
                stream=(
                    StreamChunk(delta="hello "),
                    StreamChunk(delta="world", stop_reason="end_turn"),
                ),
            )
        ]
    )
    chunks = list(
        llm.stream_generate(messages=[{"role": "user", "content": "stream me"}])
    )
    assert [c.delta for c in chunks] == ["hello ", "world"]
    assert chunks[-1].stop_reason == "end_turn"


def test_stream_generate_rejects_cases_without_stream() -> None:
    llm = ScriptedLLM(
        scenario=[ScenarioCase(expected_user_substring="x", response={})]
    )
    with pytest.raises(MockLLMError, match="no stream chunks"):
        list(llm.stream_generate(messages=[{"role": "user", "content": "x"}]))


def test_records_every_call_for_post_mortem() -> None:
    llm = ScriptedLLM(
        scenario=[
            ScenarioCase(
                expected_user_substring="a",
                response={"role": "assistant", "content": "1", "stop_reason": "end_turn"},
            ),
            ScenarioCase(
                expected_user_substring="b",
                response={"role": "assistant", "content": "2", "stop_reason": "end_turn"},
            ),
        ]
    )
    llm.generate(messages=[{"role": "user", "content": "a"}])
    llm.generate(messages=[{"role": "user", "content": "b"}])
    assert len(llm.calls) == 2
