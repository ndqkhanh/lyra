"""State machine transition tests."""

import pytest
from lyra_cli.spec_kit.state import StateManager


def test_state_initialization():
    """Test initial state."""
    manager = StateManager()
    assert manager.state.phase == "idle"
    assert manager.state.spec_draft == ""
    assert manager.state.plan_draft == ""
    assert manager.state.tasks_draft == ""


def test_phase_transitions():
    """Test valid phase transitions."""
    manager = StateManager()

    # idle → constitution_check
    manager.update_phase("constitution_check")
    assert manager.state.phase == "constitution_check"

    # constitution_check → drafting_spec
    manager.update_phase("drafting_spec")
    assert manager.state.phase == "drafting_spec"

    # drafting_spec → drafting_plan
    manager.update_phase("drafting_plan")
    assert manager.state.phase == "drafting_plan"

    # drafting_plan → drafting_tasks
    manager.update_phase("drafting_tasks")
    assert manager.state.phase == "drafting_tasks"

    # drafting_tasks → writing_disk
    manager.update_phase("writing_disk")
    assert manager.state.phase == "writing_disk"

    # writing_disk → executing
    manager.update_phase("executing")
    assert manager.state.phase == "executing"


def test_draft_updates():
    """Test draft content updates."""
    manager = StateManager()

    manager.update_draft("spec", "# Spec content")
    assert manager.state.spec_draft == "# Spec content"

    manager.update_draft("plan", "# Plan content")
    assert manager.state.plan_draft == "# Plan content"

    manager.update_draft("tasks", "# Tasks content")
    assert manager.state.tasks_draft == "# Tasks content"


def test_state_reset():
    """Test state reset to idle."""
    manager = StateManager()

    # Set some state
    manager.update_phase("drafting_spec")
    manager.update_draft("spec", "content")

    # Reset
    manager.reset()

    assert manager.state.phase == "idle"
    assert manager.state.spec_draft == ""


def test_state_listeners():
    """Test state change notifications."""
    manager = StateManager()
    notifications = []

    def listener(state):
        notifications.append(state.phase)

    manager.subscribe(listener)

    manager.update_phase("drafting_spec")
    manager.update_phase("drafting_plan")

    assert len(notifications) == 2
    assert notifications[0] == "drafting_spec"
    assert notifications[1] == "drafting_plan"
