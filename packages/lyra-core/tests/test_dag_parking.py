"""Red tests for park-on-risk and harness plugin boundary."""
from __future__ import annotations

from lyra_core.harnesses.base import HarnessPlugin, get_harness
from lyra_core.harnesses.dag_teams import (
    DAG,
    Node,
    Scheduler,
)


def test_park_on_risk_between_batches() -> None:
    dag = DAG(
        nodes=[Node(id="a"), Node(id="b", deps=["a"])],
        width_budget=4,
    )

    events: list[str] = []

    def park_hook(completed: list[str], pending: list[str]) -> bool:
        events.append(f"completed={completed} pending={pending}")
        return True  # continue

    Scheduler().run_with_parking(dag, park_hook=park_hook)
    assert events  # hook invoked at least once


def test_park_hook_can_halt() -> None:
    dag = DAG(
        nodes=[Node(id="a"), Node(id="b", deps=["a"])],
        width_budget=4,
    )

    def park_hook(completed: list[str], pending: list[str]) -> bool:
        return False  # stop

    result = Scheduler().run_with_parking(dag, park_hook=park_hook)
    assert result.halted is True
    assert "b" in result.pending


def test_harness_plugin_boundary() -> None:
    dag_plugin = get_harness("dag-teams")
    three_agent = get_harness("three-agent")
    assert isinstance(dag_plugin, HarnessPlugin)
    assert isinstance(three_agent, HarnessPlugin)
    assert dag_plugin.name == "dag-teams"
    assert three_agent.name == "three-agent"
