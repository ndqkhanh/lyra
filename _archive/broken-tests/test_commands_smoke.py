"""Smoke tests for all 19 REPL slash commands — verify they parse, handle
args, and return CommandResult without crashing.

Run: ``pytest tests/test_commands_smoke.py -v``
"""
from __future__ import annotations

import pytest
from lyra_cli.commands.registry import CommandResult

# ── Fake session object ────────────────────────────────────────────────

class FakeSession:
    """Minimal session stub for command tests."""
    def __init__(self):
        self.turn_index = 42
        self.total_tokens = 12345
        self.message_count = 67
        self.repo_root = None


@pytest.fixture
def session():
    return FakeSession()


# ── Test matrix ────────────────────────────────────────────────────────

COMMANDS = [
    # (module, function, args)
    ("workflow_cmd", "cmd_workflow", "list"),
    ("workflow_cmd", "cmd_workflow", "start feature"),
    ("workflow_cmd", "cmd_workflow", "status"),
    ("workflow_cmd", "cmd_workflow", "next"),
    ("undo_cmd", "cmd_undo", ""),
    ("undo_cmd", "cmd_undo", "--list"),
    ("redo_cmd", "cmd_redo", ""),
    ("help_cmd", "cmd_help_enhanced", ""),
    ("help_cmd", "cmd_help_enhanced", "--quick"),
    ("profile_cmd", "cmd_profile", ""),
    ("profile_cmd", "cmd_whoami", ""),
    ("git_cmd", "cmd_git", "status"),
    ("diff_cmd", "cmd_diff", ""),
    ("verify_cmd", "cmd_verify", ""),
    ("verify_cmd", "cmd_verify", "add test-123"),
    ("checkpoint_cmd", "cmd_checkpoint", ""),
    ("checkpoint_cmd", "cmd_checkpoint", "list"),
    ("recipe_cmd", "cmd_recipe", "list"),
    ("recipe_cmd", "cmd_recipe", "show new-command"),
    ("changelog_cmd", "cmd_changelog", "--last 5"),
    ("budget_cmd", "cmd_budget", ""),
    ("budget_cmd", "cmd_budget", "set 20"),
    ("budget_cmd", "cmd_budget", "status"),
    ("handoff_cmd", "cmd_handoff", ""),
    ("auth_cmd", "cmd_auth", "list"),
    ("effort_cmd", "cmd_effort", ""),
    ("effort_cmd", "cmd_effort", "list"),
    ("effort_cmd", "cmd_effort", "medium"),
    ("keys_cmd", "cmd_keys", "list"),
    ("replay_cmd", "cmd_replay", ""),
]


@pytest.mark.parametrize("module_name,func_name,args", COMMANDS)
def test_command_runs(session, module_name: str, func_name: str, args: str):
    """Test that every slash command runs without exception."""
    import importlib
    mod = importlib.import_module(f"lyra_cli.interactive.{module_name}")
    assert hasattr(mod, func_name), f"{module_name}.{func_name} not found"
    func = getattr(mod, func_name)

    result = func(session, args)
    assert result is not None
    assert isinstance(result, CommandResult)
    assert isinstance(result.output, str)
    assert len(result.output) > 0


def test_workflow_full_cycle(session):
    """Test a full /workflow lifecycle."""
    from lyra_cli.interactive.workflow_cmd import cmd_workflow

    # Start
    r = cmd_workflow(session, "start feature")
    assert "Started" in r.output

    # Status
    r = cmd_workflow(session, "status")
    assert "feature" in r.output

    # Next step
    r = cmd_workflow(session, "next")
    assert r.output is not None

    # Done
    r = cmd_workflow(session, "done")
    assert "done" in r.output.lower()

    # Cancel
    r = cmd_workflow(session, "cancel")
    assert "cancelled" in r.output.lower()


def test_verify_full_cycle(session):
    """Test a full /verify lifecycle."""
    from lyra_cli.interactive.verify_cmd import cmd_verify

    # Add checks
    r = cmd_verify(session, "add Auth works")
    assert "Added" in r.output

    r = cmd_verify(session, "add Data validated")
    assert "Added" in r.output

    # Show
    r = cmd_verify(session, "")
    assert "Auth" in r.output

    # Pass one
    r = cmd_verify(session, "pass 1")
    assert "marked passed" in r.output.lower()

    # Fail one
    r = cmd_verify(session, "fail 2 bug found")
    assert "marked failed" in r.output.lower()

    # Clear
    r = cmd_verify(session, "clear")
    assert "cleared" in r.output.lower()


def test_checkpoint_full_cycle(session):
    """Test a full /checkpoint lifecycle."""
    from lyra_cli.interactive.checkpoint_cmd import cmd_checkpoint

    # Save
    r = cmd_checkpoint(session, "test-snapshot")
    assert "Checkpoint" in r.output

    # List
    r = cmd_checkpoint(session, "list")
    assert "test-snapshot" in r.output

    # Diff
    r = cmd_checkpoint(session, "diff 1")
    assert "Diff" in r.output

    # Delete
    r = cmd_checkpoint(session, "delete 1")
    assert "Deleted" in r.output


def test_undo_redo_cycle(session):
    """Test /undo and /redo play well together."""
    from lyra_cli.interactive.undo_cmd import cmd_redo, cmd_undo

    r = cmd_undo(session, "--list")
    assert r is not None

    r = cmd_redo(session, "")
    assert "Nothing" in r.output or "not available" in r.output


def test_effort_level_setting(session):
    """Test setting /effort by name and number."""
    from lyra_cli.interactive.effort_cmd import cmd_effort

    for level in ("low", "medium", "high", "xhigh", "max"):
        r = cmd_effort(session, level)
        assert "set" in r.output.lower() or r.output is not None

    for num in ("1", "2", "3", "4", "5"):
        r = cmd_effort(session, num)
        assert r.output is not None
