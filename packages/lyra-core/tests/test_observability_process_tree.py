"""Tests for observability/process_tree.py (Phase 4 — Process Tree)."""
from __future__ import annotations

import json

import pytest

from lyra_core.observability.event_bus import (
    LLMCallFinished,
    LLMCallStarted,
    StopHookFired,
    SubagentFinished,
    SubagentSpawned,
    ToolCallStarted,
)
from lyra_core.observability.process_tree import (
    AgentLifecycleState,
    AgentNode,
    ProcessTree,
)


# ---------------------------------------------------------------------------
# AgentNode
# ---------------------------------------------------------------------------


def test_agent_node_defaults():
    node = AgentNode(node_id="n1", parent_id=None, role="root")
    assert node.state == AgentLifecycleState.RUNNING
    assert node.children == []
    assert node.is_active()


def test_agent_node_done_not_active():
    node = AgentNode(node_id="n1", parent_id=None, role="root",
                     state=AgentLifecycleState.DONE)
    assert not node.is_active()


def test_agent_node_elapsed_s():
    node = AgentNode(node_id="n1", parent_id=None, role="root")
    assert node.elapsed_s() >= 0.0


def test_agent_node_round_trip():
    node = AgentNode(node_id="n1", parent_id="p", role="planner",
                     state=AgentLifecycleState.VERIFYING, token_in=500)
    restored = AgentNode.from_dict(node.to_dict())
    assert restored.node_id == "n1"
    assert restored.role == "planner"
    assert restored.state == AgentLifecycleState.VERIFYING
    assert restored.token_in == 500


# ---------------------------------------------------------------------------
# ProcessTree — basic structure
# ---------------------------------------------------------------------------


def test_ensure_root_creates_node():
    tree = ProcessTree()
    root = tree.ensure_root("sess-1")
    assert "sess-1" in tree._nodes
    assert root.role == "root"


def test_ensure_root_idempotent():
    tree = ProcessTree()
    tree.ensure_root("sess-1")
    tree.ensure_root("sess-1")
    assert len(tree._nodes) == 1


def test_spawn_adds_child():
    tree = ProcessTree()
    tree.ensure_root("sess-1")
    child = tree.spawn("a1", parent_id="sess-1", role="planner")
    assert "a1" in tree._nodes
    assert "a1" in tree._nodes["sess-1"].children
    assert child.role == "planner"


def test_spawn_without_parent():
    tree = ProcessTree()
    child = tree.spawn("orphan", parent_id=None, role="worker")
    assert child.parent_id is None


def test_transition_updates_state():
    tree = ProcessTree()
    tree.ensure_root("sess-1")
    tree.transition("sess-1", AgentLifecycleState.DONE)
    assert tree._nodes["sess-1"].state == AgentLifecycleState.DONE
    assert tree._nodes["sess-1"].finished_at is not None


def test_transition_unknown_node_no_error():
    tree = ProcessTree()
    tree.transition("nonexistent", AgentLifecycleState.FAILED)  # must not raise


# ---------------------------------------------------------------------------
# ProcessTree — event handlers
# ---------------------------------------------------------------------------


def test_on_llm_started_creates_root():
    tree = ProcessTree()
    tree.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=100, turn=3))
    assert "s1" in tree._nodes
    assert tree._nodes["s1"].current_step == 3


def test_on_llm_finished_accumulates_tokens():
    tree = ProcessTree()
    tree.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    tree.on_event(LLMCallFinished(session_id="s1", input_tokens=400, output_tokens=100,
                                   cache_read_tokens=200, duration_ms=500.0))
    tree.on_event(LLMCallFinished(session_id="s1", input_tokens=300, output_tokens=50,
                                   cache_read_tokens=100, duration_ms=400.0))
    assert tree._nodes["s1"].token_in == 700
    assert tree._nodes["s1"].token_out == 150


def test_on_tool_started_sets_last_tool():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.on_event(ToolCallStarted(session_id="s1", tool_name="bash", args_preview="ls"))
    assert tree._nodes["s1"].last_tool == "bash"


def test_on_subagent_spawned_adds_child():
    tree = ProcessTree()
    tree.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    tree.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="evaluator"))
    assert "a1" in tree._nodes
    assert tree._nodes["a1"].role == "evaluator"
    assert "a1" in tree._nodes["s1"].children


def test_on_subagent_finished_transitions():
    tree = ProcessTree()
    tree.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    tree.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="worker"))
    tree.on_event(SubagentFinished(session_id="s1", agent_id="a1", status="done", cost_usd=0.02))
    assert tree._nodes["a1"].state == AgentLifecycleState.DONE
    assert tree._nodes["a1"].cost_usd == pytest.approx(0.02)


def test_on_stop_hook_stops_session():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.on_event(StopHookFired(session_id="s1", reason="budget"))
    assert tree._nodes["s1"].state == AgentLifecycleState.STOPPED


# ---------------------------------------------------------------------------
# ProcessTree — queries
# ---------------------------------------------------------------------------


def test_roots_returns_parentless_nodes():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="worker")
    roots = tree.roots()
    assert len(roots) == 1
    assert roots[0].node_id == "s1"


def test_children_of():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="worker")
    tree.spawn("a2", parent_id="s1", role="planner")
    kids = tree.children_of("s1")
    assert {k.node_id for k in kids} == {"a1", "a2"}


def test_active_count():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="worker")
    tree.transition("a1", AgentLifecycleState.DONE)
    assert tree.active_count() == 1  # only root is still active


def test_total_cost():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="w")
    tree._nodes["a1"].cost_usd = 0.05
    tree._nodes["s1"].cost_usd = 0.10
    assert tree.total_cost() == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def test_to_dict_round_trip():
    tree = ProcessTree(session_id="s1")
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="planner")
    d = tree.to_dict()
    restored = ProcessTree.from_dict(d)
    assert "s1" in restored._nodes
    assert "a1" in restored._nodes
    assert "a1" in restored._nodes["s1"].children


def test_from_state_file(tmp_path):
    data = {
        "session_id": "sess-42",
        "agent_role": "planner",
        "status": "running",
        "token_in": 1200,
        "current_step": 4,
        "last_tool": {"name": "bash", "status": "done"},
    }
    p = tmp_path / "process_state.json"
    p.write_text(json.dumps(data))
    tree = ProcessTree.from_state_file(p)
    assert tree.session_id == "sess-42"
    node = tree._nodes["sess-42"]
    assert node.role == "planner"
    assert node.token_in == 1200
    assert node.last_tool == "bash"


def test_from_state_file_unknown_status(tmp_path):
    data = {"session_id": "s", "status": "weird", "agent_role": "root"}
    p = tmp_path / "process_state.json"
    p.write_text(json.dumps(data))
    tree = ProcessTree.from_state_file(p)
    assert tree._nodes["s"].state == AgentLifecycleState.RUNNING


# ---------------------------------------------------------------------------
# Rich rendering (smoke tests)
# ---------------------------------------------------------------------------


def test_render_empty_tree():
    tree = ProcessTree(session_id="s1")
    r = tree.render()
    assert r is not None


def test_render_with_nodes():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="planner")
    r = tree.render()
    assert r is not None


def test_render_nested():
    tree = ProcessTree()
    tree.ensure_root("s1")
    tree.spawn("a1", parent_id="s1", role="planner")
    tree.spawn("a1a", parent_id="a1", role="worker")
    # a1 → a1a: manually wire grandchild (spawn doesn't know about a1a)
    tree._nodes["a1"].children.append("a1a")
    r = tree.render()
    assert r is not None
