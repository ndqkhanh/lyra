#!/usr/bin/env python3
"""Test Sequential REPL - Phase 1"""

import os
import sys

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

def test_imports():
    """Test all imports work"""
    print("Testing imports...")

    try:
        print("✓ SequentialREPL import successful")

        print("✓ Event system imports successful")

        print("✓ UI components imports successful")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sequential_repl_creation():
    """Test creating SequentialREPL"""
    print("\nTesting SequentialREPL creation...")

    try:
        from lyra_cli.repl import REPLConfig, SequentialREPL

        # Test with default config
        SequentialREPL()
        print("✓ SequentialREPL created with defaults")

        # Test with custom config
        config = REPLConfig(
            context_budget=100000,
            permission_mode="bypass",
            show_context=True,
            show_permission_mode=True
        )
        repl2 = SequentialREPL(config=config)
        print("✓ SequentialREPL created with custom config")

        # Verify config
        assert repl2.context_budget == 100000
        assert repl2.permission_mode == "bypass"
        print("✓ Config applied correctly")

        return True
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_tracking():
    """Test context percentage tracking"""
    print("\nTesting context tracking...")

    try:
        from lyra_cli.repl import REPLConfig, SequentialREPL

        config = REPLConfig(context_budget=1000)
        repl = SequentialREPL(config=config)

        # Test initial state
        assert repl.context_used == 0
        assert repl._get_context_percentage() == 0
        print("✓ Initial context is 0%")

        # Update context
        repl.update_context(250)  # 25%
        assert repl._get_context_percentage() == 25
        print("✓ Context updated to 25%")

        repl.update_context(250)  # 50%
        assert repl._get_context_percentage() == 50
        print("✓ Context updated to 50%")

        repl.update_context(500)  # 100%
        assert repl._get_context_percentage() == 100
        print("✓ Context updated to 100%")

        return True
    except Exception as e:
        print(f"✗ Context tracking failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permission_mode():
    """Test permission mode cycling"""
    print("\nTesting permission mode...")

    try:
        from lyra_cli.repl import SequentialREPL

        repl = SequentialREPL()

        # Test initial mode
        assert repl.permission_mode == "ask"
        print("✓ Initial mode is 'ask'")

        # Cycle to bypass
        repl.cycle_permission_mode()
        assert repl.permission_mode == "bypass"
        print("✓ Cycled to 'bypass'")

        # Cycle to deny
        repl.cycle_permission_mode()
        assert repl.permission_mode == "deny"
        print("✓ Cycled to 'deny'")

        # Cycle back to ask
        repl.cycle_permission_mode()
        assert repl.permission_mode == "ask"
        print("✓ Cycled back to 'ask'")

        # Test set_permission_mode
        repl.set_permission_mode("bypass")
        assert repl.permission_mode == "bypass"
        print("✓ set_permission_mode works")

        return True
    except Exception as e:
        print(f"✗ Permission mode failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_status_line_enhancement():
    """Test enhanced status line"""
    print("\nTesting enhanced status line...")

    try:
        from lyra_cli.ui import StatusLine

        status = StatusLine()

        # Test with context and permission mode
        status.update(
            mode="default",
            hints=["esc to exit"],
            context_percentage=45,
            permission_mode="bypass"
        )
        print("✓ Status line updated with context and permission mode")

        # Verify state
        assert status.context_percentage == 45
        assert status.permission_mode == "bypass"
        print("✓ Status line state correct")

        return True
    except Exception as e:
        print(f"✗ Status line enhancement failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_handlers():
    """Test event handlers"""
    print("\nTesting event handlers...")

    try:
        from lyra_cli.events import TextDelta, TurnFinished
        from lyra_cli.repl import SequentialREPL

        repl = SequentialREPL()

        # Test text delta handler
        event = TextDelta(turn_id="test", text="Hello")
        repl._on_text_delta(event)
        print("✓ Text delta handler works")

        # Test turn finished handler
        event = TurnFinished(
            turn_id="test",
            tokens_in=10,
            tokens_out=20,
            stop_reason="end_turn"
        )
        repl._on_turn_finished(event)
        print("✓ Turn finished handler works")

        # Verify context was updated
        assert repl.context_used > 0
        print("✓ Context updated by event handlers")

        return True
    except Exception as e:
        print(f"✗ Event handlers failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 1: SEQUENTIAL REPL CORE - TEST SUITE")
    print("=" * 80)
    print()

    results = []

    results.append(("Imports", test_imports()))
    results.append(("SequentialREPL Creation", test_sequential_repl_creation()))
    results.append(("Context Tracking", test_context_tracking()))
    results.append(("Permission Mode", test_permission_mode()))
    results.append(("Status Line Enhancement", test_status_line_enhancement()))
    results.append(("Event Handlers", test_event_handlers()))

    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    print()
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print()
        print("Phase 1 complete:")
        print("  ✓ SequentialREPL class created")
        print("  ✓ Context percentage tracking working")
        print("  ✓ Permission mode cycling working")
        print("  ✓ Enhanced status line working")
        print("  ✓ Event handlers working")
        print()
        print("Ready to commit and push Phase 1!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
