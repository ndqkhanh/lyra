"""Tests for L311-1 Executor adapters + LifecycleBus integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
from lyra_core.teams import (
    AgentLoopExecutor,
    CallableLLMExecutor,
    LeadSession,
    TeammateSpec,
    make_executor_from_chat,
    make_executor_from_factory,
    register_lifecycle_bus,
    unregister_lifecycle_bus,
)


# ---- AgentLoopExecutor ----------------------------------------------


@dataclass
class _StubResult:
    final_text: str = ""


@dataclass
class _StubLoop:
    canned: str = ""
    seen: list = None  # type: ignore[assignment]

    def run_conversation(self, user_text: str, *, session_id: str) -> _StubResult:
        if self.seen is None:
            self.seen = []
        self.seen.append({"text": user_text, "session_id": session_id})
        return _StubResult(final_text=self.canned or f"reply:{user_text[:20]}")


def test_agent_loop_executor_routes_to_factory():
    factories: list[TeammateSpec] = []
    loops: list[_StubLoop] = []

    def factory(spec: TeammateSpec) -> _StubLoop:
        factories.append(spec)
        loop = _StubLoop(canned=f"<{spec.name}>done</{spec.name}>")
        loops.append(loop)
        return loop

    ex = AgentLoopExecutor(loop_factory=factory)
    out = ex(TeammateSpec(name="alice", persona="be careful"), "review the auth module")
    assert out == "<alice>done</alice>"
    assert factories[0].name == "alice"
    assert "review the auth module" in loops[0].seen[0]["text"]
    assert "be careful" in loops[0].seen[0]["text"]
    assert loops[0].seen[0]["session_id"].startswith("team.alice")


def test_agent_loop_executor_extract_text_override():
    def factory(spec):
        return _StubLoop(canned="ignored")

    ex = AgentLoopExecutor(
        loop_factory=factory,
        extract_text=lambda r: f"wrapped:{getattr(r, 'final_text', '')}",
    )
    out = ex(TeammateSpec(name="x"), "task")
    assert out.startswith("wrapped:")


def test_make_executor_from_factory_helper():
    def factory(spec):
        return _StubLoop(canned="ok")

    ex = make_executor_from_factory(factory)
    assert callable(ex)
    assert ex(TeammateSpec(name="x"), "task") == "ok"


# ---- CallableLLMExecutor --------------------------------------------


def test_callable_llm_executor_routes_to_chat_fn():
    seen: list[str] = []

    def chat(prompt: str) -> str:
        seen.append(prompt)
        return f"reply for {len(prompt)} chars"

    ex = CallableLLMExecutor(chat_fn=chat)
    out = ex(TeammateSpec(name="alice"), "do the thing")
    assert "do the thing" in seen[0]
    assert "alice" in seen[0]
    assert "reply for" in out


def test_make_executor_from_chat_helper():
    ex = make_executor_from_chat(lambda p: f"ack:{p[:5]}")
    out = ex(TeammateSpec(name="x"), "hello")
    assert out.startswith("ack:")


# ---- LeadSession + executor end-to-end ------------------------------


def test_lead_session_with_agent_loop_executor(tmp_path):
    def factory(spec):
        return _StubLoop(canned=f"<{spec.name}>resolved</{spec.name}>")

    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t",
        executor=AgentLoopExecutor(loop_factory=factory),
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("plan the migration", assign="alice")
    n = lead.run_until_idle(timeout_s=2.0)
    assert n == 1
    snap = lead.tasks.summary()
    assert snap.completed == 1


# ---- LifecycleBus fan-out -------------------------------------------


def test_lifecycle_bus_receives_team_events(tmp_path):
    bus = LifecycleBus()
    captured: list = []
    bus.subscribe(LifecycleEvent.TEAM_TASK_COMPLETED, captured.append)
    bus.subscribe(LifecycleEvent.TEAM_SHUTDOWN, captured.append)

    register_lifecycle_bus(bus)
    try:
        lead = LeadSession.create(
            team_name="t", team_dir=tmp_path / "t",
            executor=lambda spec, body: f"ok:{body}",
        )
        lead.spawn(TeammateSpec(name="a"))
        lead.add_task("x", assign="a")
        lead.run_until_idle(timeout_s=2.0)
        lead.shutdown()
    finally:
        unregister_lifecycle_bus(bus)

    # We saw at least one task_completed and one shutdown payload.
    assert any("task_id" in (p or {}) for p in captured)
    assert any("team_name" not in (p or {}) and "report" in (p or {}) for p in captured)


def test_lifecycle_bus_register_idempotent(tmp_path):
    bus = LifecycleBus()
    register_lifecycle_bus(bus)
    register_lifecycle_bus(bus)  # second register is a no-op
    captured: list = []
    bus.subscribe(LifecycleEvent.TEAM_CREATE, captured.append)
    try:
        LeadSession.create(
            team_name="z", team_dir=tmp_path / "z", executor=lambda s, b: ""
        )
    finally:
        unregister_lifecycle_bus(bus)
    # Exactly one team_create payload (would be 2 if double-register failed).
    create_payloads = [p for p in captured if (p or {}).get("team") == "z"]
    assert len(create_payloads) == 1
