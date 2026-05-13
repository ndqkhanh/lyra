"""Tests for observability/context_gauge.py (Phase 8 — saturation, skills, DAG)."""
from __future__ import annotations

import pytest

from lyra_core.observability.context_gauge import (
    AgentDAG,
    ContextGauge,
    SkillPanel,
)
from lyra_core.observability.event_bus import (
    LLMCallFinished,
    LLMCallStarted,
    SubagentFinished,
    SubagentSpawned,
)


# ---------------------------------------------------------------------------
# ContextGauge
# ---------------------------------------------------------------------------


def test_context_gauge_defaults():
    g = ContextGauge()
    assert g.used_tokens() == 0
    assert g.saturation_pct() == 0.0
    assert not g.is_saturated()


def test_context_gauge_update_from_started():
    g = ContextGauge(max_tokens=1000)
    g.update_from_started(prompt_tokens=400)
    assert g.prompt_tokens == 400
    assert g.saturation_pct() == pytest.approx(40.0)


def test_context_gauge_update_from_finished():
    g = ContextGauge(max_tokens=1000)
    g.update_from_finished(input_tokens=600, output_tokens=100, cache_tokens=300)
    assert g.used_tokens() == 700
    assert g.saturation_pct() == pytest.approx(70.0)


def test_context_gauge_cache_hit_pct():
    g = ContextGauge()
    g.update_from_finished(input_tokens=800, output_tokens=100, cache_tokens=400)
    assert g.cache_hit_pct() == pytest.approx(50.0)


def test_context_gauge_is_saturated():
    g = ContextGauge(max_tokens=1000)
    g.update_from_finished(input_tokens=850, output_tokens=0, cache_tokens=0)
    assert g.is_saturated()


def test_context_gauge_not_saturated():
    g = ContextGauge(max_tokens=1000)
    g.update_from_finished(input_tokens=500, output_tokens=0, cache_tokens=0)
    assert not g.is_saturated()


def test_context_gauge_saturation_clamps_at_100():
    g = ContextGauge(max_tokens=100)
    g.update_from_finished(input_tokens=200, output_tokens=0, cache_tokens=0)
    assert g.saturation_pct() == pytest.approx(100.0)


@pytest.mark.parametrize("readings,expected_trend", [
    ([10.0, 20.0, 35.0], "rising"),
    ([35.0, 20.0, 10.0], "falling"),
    ([20.0, 21.0, 20.5], "stable"),
])
def test_context_gauge_trend(readings, expected_trend):
    g = ContextGauge()
    g._history = readings
    assert g.trend() == expected_trend


def test_context_gauge_trend_single_reading():
    g = ContextGauge()
    g._history = [10.0]
    assert g.trend() == "stable"


def test_context_gauge_on_event_llm_started():
    g = ContextGauge(max_tokens=10_000)
    g.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=500, turn=1))
    assert g.prompt_tokens == 500


def test_context_gauge_on_event_llm_finished():
    g = ContextGauge(max_tokens=10_000)
    g.on_event(LLMCallFinished(session_id="s1", input_tokens=800, output_tokens=100,
                                cache_read_tokens=300, duration_ms=500.0))
    assert g.cache_tokens == 300


def test_context_gauge_render_no_error():
    g = ContextGauge(max_tokens=1000)
    g.update_from_finished(600, 100, 200)
    panel = g.render()
    assert panel is not None


# ---------------------------------------------------------------------------
# SkillPanel
# ---------------------------------------------------------------------------


def test_skill_panel_activate_new():
    p = SkillPanel()
    p.activate("python-patterns")
    assert len(p.active_skills()) == 1
    assert p.active_skills()[0].name == "python-patterns"
    assert p.active_skills()[0].use_count == 1


def test_skill_panel_activate_increments_count():
    p = SkillPanel()
    p.activate("tdd")
    p.activate("tdd")
    assert p.active_skills()[0].use_count == 2


def test_skill_panel_total_activations():
    p = SkillPanel()
    p.activate("a")
    p.activate("a")
    p.activate("b")
    assert p.total_activations() == 3


def test_skill_panel_multiple_skills_sorted():
    p = SkillPanel()
    p.activate("z-skill")
    p.activate("a-skill")
    names = [e.name for e in p.active_skills()]
    assert names[0] == "z-skill"  # sorted by activation time, not name
    assert names[1] == "a-skill"


def test_skill_panel_render_empty():
    panel = SkillPanel().render()
    assert panel is not None


def test_skill_panel_render_with_skills():
    p = SkillPanel()
    p.activate("golang-testing")
    panel = p.render()
    assert panel is not None


def test_skill_panel_on_event_no_error():
    p = SkillPanel()
    p.on_event(LLMCallStarted(session_id="s", model="c", prompt_tokens=0, turn=1))


# ---------------------------------------------------------------------------
# AgentDAG
# ---------------------------------------------------------------------------


def test_dag_add_node():
    dag = AgentDAG()
    node = dag.add_node("n1", "root")
    assert node.node_id == "n1"
    assert dag.node_count() == 1


def test_dag_add_node_idempotent():
    dag = AgentDAG()
    dag.add_node("n1", "root")
    dag.add_node("n1", "duplicate")
    assert dag.node_count() == 1


def test_dag_add_edge():
    dag = AgentDAG()
    dag.add_node("p", "root")
    dag.add_node("c", "planner")
    dag.add_edge("p", "c")
    assert dag.edge_count() == 1
    kids = dag.children_of("p")
    assert len(kids) == 1
    assert kids[0].node_id == "c"


def test_dag_roots():
    dag = AgentDAG()
    dag.add_node("p", "root")
    dag.add_node("c1", "worker")
    dag.add_node("c2", "planner")
    dag.add_edge("p", "c1")
    dag.add_edge("p", "c2")
    roots = dag.roots()
    assert len(roots) == 1
    assert roots[0].node_id == "p"


def test_dag_total_cost():
    dag = AgentDAG()
    dag.add_node("n1", "root")
    dag.add_node("n2", "worker")
    dag._nodes["n1"].cost_usd = 0.05
    dag._nodes["n2"].cost_usd = 0.10
    assert dag.total_cost() == pytest.approx(0.15)


def test_dag_on_event_llm_started():
    dag = AgentDAG()
    dag.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    assert "s1" in dag._nodes


def test_dag_on_event_subagent_spawned():
    dag = AgentDAG()
    dag.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    dag.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="planner"))
    assert "a1" in dag._nodes
    kids = dag.children_of("s1")
    assert any(k.node_id == "a1" for k in kids)


def test_dag_on_event_subagent_finished():
    dag = AgentDAG()
    dag.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    dag.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="worker"))
    dag.on_event(SubagentFinished(session_id="s1", agent_id="a1", status="done", cost_usd=0.03))
    assert dag._nodes["a1"].status == "done"
    assert dag._nodes["a1"].cost_usd == pytest.approx(0.03)


def test_dag_to_dict():
    dag = AgentDAG()
    dag.add_node("n1", "root")
    dag.add_node("n2", "planner")
    dag.add_edge("n1", "n2")
    d = dag.to_dict()
    assert "nodes" in d and "edges" in d
    assert len(d["edges"]) == 1
    assert d["edges"][0]["parent"] == "n1"


def test_dag_render_empty():
    dag = AgentDAG()
    tree = dag.render()
    assert tree is not None


def test_dag_render_with_nodes():
    dag = AgentDAG()
    dag.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=0, turn=1))
    dag.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="planner"))
    tree = dag.render()
    assert tree is not None
