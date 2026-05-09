"""Tests for L311-1/3 — shell-script hook gates for team events."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from lyra_core.teams import (
    GateResult,
    HOOKABLE_EVENTS,
    HookBlockedError,
    HookDecision,
    HookSpec,
    LeadSession,
    TeamHookRegistry,
    TeammateSpec,
    global_registry,
    load_hooks_yaml,
    reset_global_registry,
)


@pytest.fixture(autouse=True)
def _isolated_registry():
    reset_global_registry()
    yield
    reset_global_registry()


def _stub_executor(spec, body):
    return f"<{spec.name}>{body}</{spec.name}>"


# ---- HookSpec validation -----------------------------------------


def test_hook_spec_rejects_unknown_event():
    with pytest.raises(ValueError, match="not blockable"):
        HookSpec(event="team.create", script="echo")  # type: ignore[arg-type]


def test_hook_spec_rejects_zero_timeout():
    with pytest.raises(ValueError, match="timeout"):
        HookSpec(event="team.task_created", script="echo", timeout_s=0)


def test_hook_spec_accepts_valid_event():
    spec = HookSpec(event="team.task_created", script="echo")
    assert spec.event == "team.task_created"


# ---- registry ----------------------------------------------------


def test_registry_register_and_query():
    reg = TeamHookRegistry()
    spec = HookSpec(event="team.task_created", script="echo")
    reg.register(spec)
    assert reg.hooks_for("team.task_created") == (spec,)
    assert reg.hooks_for("team.task_completed") == ()
    assert len(reg) == 1


def test_registry_unregister_all():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="echo"))
    reg.unregister_all()
    assert len(reg) == 0


# ---- gate dispatch (inline shell) --------------------------------


def test_gate_allows_on_zero_exit():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="exit 0"))
    result = reg.gate("team.task_created", {"team": "t", "title": "x"})
    assert isinstance(result, GateResult)
    assert not result.blocked


def test_gate_blocks_on_exit_2():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="exit 2"))
    result = reg.gate("team.task_created", {"team": "t", "title": "x"})
    assert result.blocked


def test_gate_warning_on_exit_1():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="exit 1"))
    result = reg.gate("team.task_created", {"team": "t", "title": "x"})
    assert not result.blocked
    assert len(result.warnings) == 1


def test_gate_runs_every_hook_even_after_block():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="exit 2"))
    reg.register(HookSpec(event="team.task_created", script="exit 0"))
    result = reg.gate("team.task_created", {"team": "t"})
    assert len(result.decisions) == 2
    assert result.blocked


def test_gate_no_hooks_returns_empty():
    reg = TeamHookRegistry()
    result = reg.gate("team.task_created", {"team": "t"})
    assert result.decisions == ()
    assert not result.blocked


def test_gate_passes_payload_via_env_and_stdin():
    reg = TeamHookRegistry()
    # The shell script reads stdin and asserts payload contents are present.
    script = "read -r line && echo \"$line\" | grep -q '\"team\":' || exit 1"
    reg.register(HookSpec(event="team.task_created", script=script))
    result = reg.gate("team.task_created", {"team": "auth-refactor"})
    assert not result.blocked


def test_gate_env_vars_set():
    reg = TeamHookRegistry()
    reg.register(
        HookSpec(
            event="team.task_completed",
            script='[ "$LYRA_HOOK_EVENT" = "team.task_completed" ] && [ "$LYRA_HOOK_TEAM" = "auth-refactor" ] || exit 1',
        )
    )
    result = reg.gate(
        "team.task_completed",
        {"team": "auth-refactor", "task_id": "001", "teammate": "alice"},
    )
    assert not result.blocked


def test_gate_timeout_treated_as_block():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="sleep 5", timeout_s=0.1))
    result = reg.gate("team.task_created", {"team": "t"})
    assert result.blocked


def test_gate_missing_script_treated_as_warning():
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script="/no/such/path/hook.sh"))
    result = reg.gate("team.task_created", {"team": "t"})
    # Missing scripts → warning, not block.
    assert not result.blocked
    assert any(d.warning for d in result.decisions)


# ---- gate dispatch (path-resolved) -------------------------------


def test_gate_executes_real_path(tmp_path):
    script = tmp_path / "block.sh"
    script.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    reg = TeamHookRegistry()
    reg.register(HookSpec(event="team.task_created", script=str(script)))
    result = reg.gate("team.task_created", {"team": "t"})
    assert result.blocked


# ---- LeadSession integration -------------------------------------


def test_lead_add_task_blocked_by_hook(tmp_path):
    global_registry().register(
        HookSpec(event="team.task_created", script="exit 2")
    )
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    with pytest.raises(HookBlockedError):
        lead.add_task("blocked task", assign="alice")
    # Task list should be empty — block happened before the
    # task was created.
    assert lead.tasks.summary().total == 0


def test_lead_task_completed_hook_block_reverts(tmp_path):
    global_registry().register(
        HookSpec(event="team.task_completed", script="exit 2")
    )
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("x", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    snap = lead.tasks.summary()
    # Completion was blocked → task ended up in the blocked
    # bucket (state=blocked + failure_reason set), not completed.
    assert snap.completed == 0
    assert snap.blocked == 1
    # Verify the failure reason carries the hook block trail.
    blocked_tasks = [t for t in lead.tasks.all() if t.state == "blocked"]
    assert len(blocked_tasks) == 1
    assert "hook-blocked" in (blocked_tasks[0].failure_reason or "")


def test_lead_passes_when_no_hooks(tmp_path):
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("x", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    assert lead.tasks.summary().completed == 1


def test_lead_idle_hook_advisory_only(tmp_path):
    """`team.teammate_idle` hooks fire but cannot block — the task is
    already done."""
    global_registry().register(
        HookSpec(event="team.teammate_idle", script="exit 2")
    )
    lead = LeadSession.create(
        team_name="t", team_dir=tmp_path / "t", executor=_stub_executor
    )
    lead.spawn(TeammateSpec(name="alice"))
    lead.add_task("x", assign="alice")
    lead.run_until_idle(timeout_s=2.0)
    # Completion proceeds even though the idle hook returned 2.
    assert lead.tasks.summary().completed == 1


# ---- YAML loader ------------------------------------------------


def test_load_hooks_yaml_round_trip(tmp_path):
    yaml_path = tmp_path / "hooks.yaml"
    yaml_path.write_text(
        "hooks:\n"
        "  - event: team.task_created\n"
        "    script: exit 0\n"
        "    timeout_s: 5\n"
        "  - event: team.task_completed\n"
        "    script: /usr/bin/true\n"
        "    timeout_s: 30\n",
        encoding="utf-8",
    )
    reg = load_hooks_yaml(yaml_path)
    assert len(reg) == 2
    assert reg.hooks_for("team.task_created")[0].timeout_s == 5
    assert reg.hooks_for("team.task_completed")[0].script == "/usr/bin/true"


def test_load_hooks_yaml_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_hooks_yaml(tmp_path / "nope.yaml")


def test_load_hooks_yaml_skips_invalid_entries(tmp_path):
    yaml_path = tmp_path / "hooks.yaml"
    yaml_path.write_text(
        "hooks:\n"
        "  - event: team.task_created\n"
        "    script: exit 0\n"
        "  - event: \n"  # empty event → skipped
        "    script: exit 0\n"
        "  - script: exit 0\n",  # no event → skipped
        encoding="utf-8",
    )
    reg = load_hooks_yaml(yaml_path)
    assert len(reg) == 1


# ---- HOOKABLE_EVENTS sanity --------------------------------------


def test_hookable_events_set():
    assert HOOKABLE_EVENTS == frozenset({
        "team.task_created", "team.task_completed", "team.teammate_idle"
    })
