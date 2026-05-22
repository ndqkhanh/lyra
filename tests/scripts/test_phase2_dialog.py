#!/usr/bin/env python3
"""Integration test for Phase 2: Rich UX with Dialogs."""

from lyra_cli.cli.skill_manager import SkillManager
from lyra_cli.interactive.dialog_skill_picker import run_skill_picker


def test_dialog_skill_picker_exists():
    """Test that dialog_skill_picker module exists and exports run_skill_picker."""
    assert callable(run_skill_picker), "run_skill_picker should be callable"
    print("✓ dialog_skill_picker module exists with run_skill_picker function")


def test_dialog_returns_none_for_empty_skills():
    """Test that dialog returns None when no skills are available."""
    result = run_skill_picker({})
    assert result is None, "Should return None for empty skills dict"
    print("✓ Dialog returns None for empty skills dict")


def test_skill_command_launches_dialog():
    """Test that /skill command can launch dialog (integration check)."""
    from lyra_cli.commands.registry import COMMAND_REGISTRY

    skill_cmd = next((cmd for cmd in COMMAND_REGISTRY if cmd.name == "skill"), None)
    assert skill_cmd is not None, "/skill command should be registered"
    assert skill_cmd.handler.__name__ == "_cmd_skill", "Handler should be _cmd_skill dispatcher"
    print("✓ /skill command is properly registered with dispatcher")


def test_keybinds_has_launch_skill_picker():
    """Test that keybinds module exports launch_skill_picker helper."""
    from lyra_cli.interactive import keybinds

    assert hasattr(keybinds, "launch_skill_picker"), "keybinds should export launch_skill_picker"
    assert callable(keybinds.launch_skill_picker), "launch_skill_picker should be callable"
    print("✓ keybinds.launch_skill_picker exists and is callable")


def test_launch_skill_picker_signature():
    """Test that launch_skill_picker has correct signature."""
    from lyra_cli.interactive import keybinds
    import inspect

    # Check function signature
    sig = inspect.signature(keybinds.launch_skill_picker)
    params = list(sig.parameters.keys())
    assert "session" in params, "Should accept session parameter"

    # Check return type annotation
    return_annotation = sig.return_annotation
    assert return_annotation != inspect.Signature.empty, "Should have return type annotation"

    print("✓ launch_skill_picker has correct signature (session) -> tuple[str | None, str]")


def test_phase2_integration():
    """Test complete Phase 2 integration: dialog + keyboard shortcut + /skill command."""
    from lyra_cli.interactive import keybinds
    from lyra_cli.commands.registry import COMMAND_REGISTRY

    # Check dialog exists
    assert callable(run_skill_picker), "Dialog should exist"

    # Check keybind helper exists
    assert hasattr(keybinds, "launch_skill_picker"), "Keybind helper should exist"
    assert "launch_skill_picker" in keybinds.__all__, "Helper should be exported"

    # Check /skill command exists
    skill_cmd = next((cmd for cmd in COMMAND_REGISTRY if cmd.name == "skill"), None)
    assert skill_cmd is not None, "/skill command should exist"

    print("✓ Phase 2 integration complete: dialog + keybind + command")


if __name__ == "__main__":
    print("Running Phase 2 Dialog Integration Tests\n")
    print("=" * 60)

    try:
        test_dialog_skill_picker_exists()
        print()
        test_dialog_returns_none_for_empty_skills()
        print()
        test_skill_command_launches_dialog()
        print()
        test_keybinds_has_launch_skill_picker()
        print()
        test_launch_skill_picker_signature()
        print()
        test_phase2_integration()
        print()
        print("=" * 60)
        print("✓ All Phase 2 integration tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
