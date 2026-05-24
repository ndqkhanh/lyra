import pytest

from harness_core.messages import Message, StopReason
from harness_core.models import MockLLM, get_default_llm


def test_mock_llm_returns_scripted_strings():
    llm = MockLLM(scripted_outputs=["hello", "world"])
    m1 = llm.generate([Message.user("hi")])
    m2 = llm.generate([Message.user("again")])
    assert m1.content == "hello"
    assert m2.content == "world"
    assert m1.stop_reason == StopReason.END_TURN


def test_mock_llm_tool_calls_from_dict():
    llm = MockLLM(
        scripted_outputs=[
            {"text": "using calc", "tool_calls": [{"name": "calculator", "args": {"expression": "1+1"}}]}
        ]
    )
    m = llm.generate([Message.user("q")])
    assert m.has_tool_calls()
    assert m.tool_calls[0].name == "calculator"
    assert m.stop_reason == StopReason.TOOL_USE


def test_mock_llm_overflow_returns_done():
    llm = MockLLM(scripted_outputs=[])
    m = llm.generate([Message.user("x")])
    assert m.content == "done"
    assert m.stop_reason == StopReason.END_TURN


def test_mock_llm_records_calls():
    llm = MockLLM(scripted_outputs=["a"])
    _ = llm.generate([Message.user("q")])
    assert len(llm.calls) == 1


def test_mock_llm_rejects_bad_script_entry():
    llm = MockLLM(scripted_outputs=[123])
    with pytest.raises(TypeError):
        llm.generate([Message.user("q")])


def test_get_default_llm_returns_mock_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm = get_default_llm()
    assert isinstance(llm, MockLLM)
