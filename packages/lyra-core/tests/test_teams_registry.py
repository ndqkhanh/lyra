"""Contract tests for ``lyra_core.teams`` (Phase J.3).

The five built-in roles must always be present; the executor must
thread step outputs into the next step's input; per-step task
overrides must win over the threaded handoff; unknown roles raise
``KeyError``.
"""
from __future__ import annotations

import pytest
from lyra_core.teams import (
    TeamPlan,
    TeamRegistry,
    TeamRole,
    TeamStep,
    default_registry,
    default_software_plan,
    run_team_plan,
)


def test_registry_ships_five_builtin_roles() -> None:
    reg = default_registry()
    assert {"pm", "architect", "engineer", "reviewer", "qa"} <= set(reg.names())


def test_default_registry_singleton_is_idempotent() -> None:
    a = default_registry()
    b = default_registry()
    assert a is b


def test_each_builtin_role_has_sop_and_toolset() -> None:
    reg = default_registry()
    for name in ("pm", "architect", "engineer", "reviewer", "qa"):
        role = reg.get(name)
        assert role is not None
        assert role.system_prompt.strip()
        assert role.title.strip()
        assert role.toolset
        assert isinstance(role.sop, tuple) and len(role.sop) >= 1


def test_default_software_plan_has_five_steps_in_canonical_order() -> None:
    plan = default_software_plan()
    assert plan.role_names() == ("pm", "architect", "engineer", "reviewer", "qa")


def test_register_then_get_roundtrip() -> None:
    reg = TeamRegistry(builtins=False)
    role = TeamRole(
        name="copy-editor",
        title="Copy Editor",
        description="cleans prose",
        system_prompt="You polish prose.",
        toolset="safe",
        sop=("Read the draft.", "Mark up grammar."),
    )
    reg.register(role)
    assert reg.get("copy-editor") is role


def test_register_duplicate_raises() -> None:
    reg = TeamRegistry()
    with pytest.raises(ValueError):
        reg.register(reg.get("pm"))  # type: ignore[arg-type]


def test_invalid_role_name_rejected() -> None:
    with pytest.raises(ValueError):
        TeamRole(
            name="UPPER",
            title="x",
            description="x",
            system_prompt="x",
        )


def test_run_team_plan_threads_outputs_through_steps() -> None:
    """A stub agent that suffixes its role name reproduces the chain."""

    def stub_agent(role, task_in: str) -> str:
        return f"{task_in} | done-by:{role.name}"

    report = run_team_plan(
        default_software_plan(),
        "build a 2048 game",
        agent=stub_agent,
    )
    chain = report.final_output
    assert chain.startswith("build a 2048 game | done-by:pm")
    assert "done-by:architect" in chain
    assert "done-by:engineer" in chain
    assert "done-by:reviewer" in chain
    assert "done-by:qa" in chain


def test_run_team_plan_records_each_handoff() -> None:
    def stub_agent(role, task_in: str) -> str:
        return f"out:{role.name}"

    report = run_team_plan(
        default_software_plan(),
        "make it work",
        agent=stub_agent,
    )
    assert len(report.steps) == 5
    assert report.steps[0].role == "pm"
    assert report.steps[0].task_in == "make it work"
    assert report.steps[1].role == "architect"
    assert report.steps[1].task_in == "out:pm"
    assert report.steps[2].task_in == "out:architect"


def test_step_task_override_wins_over_handoff() -> None:
    def stub_agent(role, task_in: str) -> str:
        return f"{role.name}:{task_in}"

    plan = TeamPlan(
        steps=(
            TeamStep(role="pm"),
            TeamStep(role="engineer", task="forced-task-for-engineer"),
        )
    )
    report = run_team_plan(plan, "initial-input", agent=stub_agent)
    assert report.steps[0].task_in == "initial-input"
    assert report.steps[1].task_in == "forced-task-for-engineer"


def test_unknown_role_raises_keyerror() -> None:
    plan = TeamPlan(steps=(TeamStep(role="no-such-role"),))
    with pytest.raises(KeyError):
        run_team_plan(plan, "x", agent=lambda role, task: "")


def test_empty_plan_returns_initial_task_as_final_output() -> None:
    report = run_team_plan(
        TeamPlan(steps=()),
        "initial",
        agent=lambda role, task: "should not be called",
    )
    assert report.steps == ()
    assert report.final_output == ""
    assert report.initial_task == "initial"


def test_to_dict_contains_handoff_chain() -> None:
    def stub_agent(role, task_in: str) -> str:
        return f"out:{role.name}"

    report = run_team_plan(
        default_software_plan(),
        "task",
        agent=stub_agent,
    )
    body = report.to_dict()
    assert body["plan"] == "software-company"
    assert body["initial_task"] == "task"
    assert len(body["steps"]) == 5
    assert body["final_output"] == "out:qa"
