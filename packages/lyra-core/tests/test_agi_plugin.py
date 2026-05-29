"""Dedicated tests for agent/agi_plugin.py."""

from __future__ import annotations

import pytest
from lyra_core.agent.agi_plugin import AGILoopPlugin, SessionCtx
from lyra_core.agent.event_sourced_loop import EventType


class TestSessionCtx:
    def test_create(self):
        ctx = SessionCtx(session_id="sess-1", user_text="hello")
        assert ctx.session_id == "sess-1"
        assert ctx.user_text == "hello"

    def test_default_user_text(self):
        ctx = SessionCtx(session_id="sess-2")
        assert ctx.user_text == ""

    def test_mutable(self):
        ctx = SessionCtx(session_id="s1")
        ctx.user_text = "updated"
        assert ctx.user_text == "updated"


class TestAGILoopPlugin:
    @pytest.fixture
    def plugin(self):
        return AGILoopPlugin(agent_id="test-agent")

    def test_init_creates_event_log(self, plugin):
        assert plugin._es_loop is not None
        assert plugin._active is True

    def test_event_log_property(self, plugin):
        log = plugin.event_log
        assert log is not None

    def test_default_agent_id(self):
        plugin = AGILoopPlugin()
        assert plugin.agent_id == "lyra"

    def test_on_session_start_emits_event(self, plugin):
        ctx = SessionCtx(session_id="sess-1", user_text="hello world")
        assert plugin.event_log.size == 0
        plugin.on_session_start(ctx)
        assert plugin.event_log.size > 0

    def test_on_session_start_event_type(self, plugin):
        ctx = SessionCtx(session_id="sess-1")
        plugin.on_session_start(ctx)
        events = plugin.event_log.replay()
        assert events[-1].event_type == EventType.AGENT_STARTED

    def test_on_session_start_when_inactive(self, plugin):
        plugin._active = False
        ctx = SessionCtx(session_id="sess-1")
        size_before = plugin.event_log.size
        plugin.on_session_start(ctx)
        assert plugin.event_log.size == size_before

    def test_pre_llm_call_emits_event(self, plugin):
        class FakeCtx:
            def __str__(self):
                return "x" * 100

        plugin.pre_llm_call(FakeCtx())
        events = plugin.event_log.replay()
        assert events[-1].event_type == EventType.THOUGHT_GENERATED

    def test_pre_llm_call_when_inactive(self, plugin):
        plugin._active = False
        size_before = plugin.event_log.size
        plugin.pre_llm_call("prompt")
        assert plugin.event_log.size == size_before

    def test_pre_tool_call_emits_event_with_tool_name(self, plugin):
        class FakeCtx:
            tool_name = "search"

        plugin.pre_tool_call(FakeCtx())
        events = plugin.event_log.replay()
        last = events[-1]
        assert last.event_type == EventType.TOOL_CALLED
        assert last.data["tool"] == "search"

    def test_pre_tool_call_unknown_tool(self, plugin):
        class FakeCtx:
            pass

        plugin.pre_tool_call(FakeCtx())
        events = plugin.event_log.replay()
        assert events[-1].data["tool"] == "unknown"

    def test_post_tool_call_emits_event(self, plugin):
        plugin.post_tool_call(None)
        events = plugin.event_log.replay()
        assert events[-1].event_type == EventType.TOOL_RESULT

    def test_on_session_end_emits_event(self, plugin):
        ctx = SessionCtx(session_id="sess-1")
        plugin.on_session_start(ctx)
        size_before = plugin.event_log.size
        plugin.on_session_end(ctx)
        assert plugin.event_log.size > size_before
        events = plugin.event_log.replay()
        assert events[-1].event_type == EventType.AGENT_FINISHED

    def test_on_session_end_when_inactive(self, plugin):
        plugin._active = False
        ctx = SessionCtx(session_id="sess-1")
        size_before = plugin.event_log.size
        plugin.on_session_end(ctx)
        assert plugin.event_log.size == size_before

    def test_get_event_log_summary(self, plugin):
        ctx = SessionCtx(session_id="sess-1", user_text="test")
        plugin.on_session_start(ctx)
        plugin.pre_tool_call(type("FakeCtx", (), {"tool_name": "write"})())
        plugin.post_tool_call(None)
        plugin.on_session_end(ctx)
        summary = plugin.get_event_log_summary()
        assert summary["agent_id"] == "test-agent"
        assert summary["total_events"] > 0
        assert "state" in summary

    def test_full_session_workflow(self, plugin):
        ctx = SessionCtx(session_id="full-session", user_text="build feature X")

        plugin.on_session_start(ctx)
        plugin.pre_llm_call("thinking...")
        plugin.pre_tool_call(type("FakeCtx", (), {"tool_name": "bash"})())
        plugin.post_tool_call(None)
        plugin.on_session_end(ctx)

        log = plugin.event_log
        events = log.replay()
        types = [e.event_type for e in events]
        assert EventType.AGENT_STARTED in types
        assert EventType.THOUGHT_GENERATED in types
        assert EventType.TOOL_CALLED in types
        assert EventType.TOOL_RESULT in types
        assert EventType.AGENT_FINISHED in types
