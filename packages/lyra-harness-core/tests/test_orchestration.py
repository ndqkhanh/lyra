"""Tests for harness_core.orchestration — pure-function agents + replay."""
from __future__ import annotations

import pytest

from harness_core.orchestration import (
    AgentDecision,
    PureFunctionAgent,
    SideEffectLog,
    SideEffectRecord,
    TrajectoryReplay,
    decision_fingerprint,
)


class TestDecisionFingerprint:
    def test_deterministic(self):
        a = decision_fingerprint(prompt="p", context={"k": "v"}, history=[])
        b = decision_fingerprint(prompt="p", context={"k": "v"}, history=[])
        assert a == b

    def test_changes_with_prompt(self):
        a = decision_fingerprint(prompt="p1", context={}, history=[])
        b = decision_fingerprint(prompt="p2", context={}, history=[])
        assert a != b

    def test_changes_with_context(self):
        a = decision_fingerprint(prompt="p", context={"k": "v1"}, history=[])
        b = decision_fingerprint(prompt="p", context={"k": "v2"}, history=[])
        assert a != b

    def test_changes_with_history(self):
        a = decision_fingerprint(prompt="p", context={}, history=[{"x": 1}])
        b = decision_fingerprint(prompt="p", context={}, history=[{"x": 2}])
        assert a != b

    def test_unicode_safe(self):
        # Non-ASCII must hash without errors
        fp = decision_fingerprint(prompt="café", context={"café": "ναι"}, history=[])
        assert isinstance(fp, str) and len(fp) == 64


class TestPureFunctionAgent:
    def test_policy_via_init(self):
        def policy(*, prompt, context, history):
            return AgentDecision(action="answer", payload={"text": f"echo: {prompt}"})

        agent = PureFunctionAgent(policy=policy)
        d = agent.decide(prompt="hi", context={}, history=[])
        assert d.action == "answer"
        assert d.payload == {"text": "echo: hi"}
        assert d.fingerprint != ""

    def test_no_policy_raises(self):
        agent = PureFunctionAgent()
        with pytest.raises(NotImplementedError):
            agent.decide(prompt="x", context={}, history=[])

    def test_decide_is_deterministic(self):
        def policy(*, prompt, context, history):
            return AgentDecision(action="tool_call", payload={"name": "search", "q": prompt})

        agent = PureFunctionAgent(policy=policy)
        d1 = agent.decide(prompt="q", context={}, history=[])
        d2 = agent.decide(prompt="q", context={}, history=[])
        assert d1.fingerprint == d2.fingerprint
        assert d1.action == d2.action
        assert d1.payload == d2.payload

    def test_subclass(self):
        class StubAgent(PureFunctionAgent):
            def policy(self, *, prompt, context, history):
                return AgentDecision(action="stop", payload={})

        agent = StubAgent()
        d = agent.decide(prompt="q", context={}, history=[])
        assert d.action == "stop"


class TestSideEffectLog:
    def test_append_and_find(self):
        log = SideEffectLog()
        log.append(
            SideEffectRecord(call_id="c1", tool_name="write", args={"path": "/tmp/x"}, result="ok")
        )
        rec = log.find("c1")
        assert rec is not None
        assert rec.tool_name == "write"

    def test_find_missing(self):
        log = SideEffectLog()
        assert log.find("nope") is None

    def test_jsonl(self):
        log = SideEffectLog()
        log.append(SideEffectRecord(call_id="a", tool_name="t", args={}, result=1))
        log.append(SideEffectRecord(call_id="b", tool_name="t", args={}, result=2))
        out = log.to_jsonl()
        assert "\"call_id\": \"a\"" in out
        assert "\"call_id\": \"b\"" in out
        assert out.count("\n") == 1  # 2 lines = 1 newline


class TestExecuteSideEffect:
    def test_runs_and_logs(self):
        agent = PureFunctionAgent(policy=lambda **kw: AgentDecision(action="tool_call"))
        result = agent.execute_side_effect(
            call_id="c1",
            tool_name="echo",
            args={"x": 1},
            runner=lambda args: args["x"] * 2,
        )
        assert result == 2
        rec = agent.log.find("c1")
        assert rec is not None
        assert rec.result == 2

    def test_non_replayable_flag(self):
        agent = PureFunctionAgent(policy=lambda **kw: AgentDecision(action="tool_call"))
        agent.execute_side_effect(
            call_id="c1",
            tool_name="net_read",
            args={},
            runner=lambda a: "fresh",
            is_replayable=False,
        )
        rec = agent.log.find("c1")
        assert rec is not None
        assert rec.is_replayable is False


class TestTrajectoryReplay:
    def _agent_with_log(self):
        agent = PureFunctionAgent(policy=lambda **kw: AgentDecision(action="tool_call"))
        agent.execute_side_effect(
            call_id="c1", tool_name="t", args={"a": 1}, runner=lambda a: "v1"
        )
        agent.execute_side_effect(
            call_id="c2", tool_name="t", args={"a": 2}, runner=lambda a: "v2", is_replayable=False
        )
        return agent

    def test_replay_replayable_uses_recorded(self):
        agent = self._agent_with_log()
        replay = TrajectoryReplay(log=agent.log)
        out = replay.replay_call(call_id="c1")
        assert out == "v1"

    def test_replay_non_replayable_runs_runner(self):
        agent = self._agent_with_log()
        replay = TrajectoryReplay(log=agent.log)
        out = replay.replay_call(call_id="c2", runner=lambda a: f"re-{a['a']}")
        assert out == "re-2"

    def test_replay_non_replayable_no_runner_raises(self):
        agent = self._agent_with_log()
        replay = TrajectoryReplay(log=agent.log)
        with pytest.raises(ValueError):
            replay.replay_call(call_id="c2")

    def test_replay_unknown_call_id_raises(self):
        replay = TrajectoryReplay(log=SideEffectLog())
        with pytest.raises(KeyError):
            replay.replay_call(call_id="nope")

    def test_verify_decision_match(self):
        def policy(*, prompt, context, history):
            return AgentDecision(action="answer")

        agent = PureFunctionAgent(policy=policy)
        d = agent.decide(prompt="q", context={}, history=[])
        replay = TrajectoryReplay(log=agent.log)
        assert replay.verify_decision(
            agent=agent,
            prompt="q",
            context={},
            history=[],
            expected_fingerprint=d.fingerprint,
        )

    def test_verify_decision_mismatch(self):
        def policy(*, prompt, context, history):
            return AgentDecision(action="answer")

        agent = PureFunctionAgent(policy=policy)
        replay = TrajectoryReplay(log=agent.log)
        assert not replay.verify_decision(
            agent=agent,
            prompt="q",
            context={},
            history=[],
            expected_fingerprint="bogus",
        )
