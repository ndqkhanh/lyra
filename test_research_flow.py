#!/usr/bin/env python3
"""Test Lyra deep research flow end-to-end."""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-research/src"))

from lyra_cli.commands.research import handle_research_command
from lyra_research.orchestrator import ResearchOrchestrator, ResearchProgress

def test_research_command():
    """Test the research command handler."""
    print("=" * 80)
    print("TEST 1: Research Command Handler")
    print("=" * 80)

    # Capture output
    outputs = []
    def capture_output(msg):
        outputs.append(msg)
        print(msg)

    try:
        # Test with a simple topic
        result = handle_research_command(
            "topic 'Python async patterns' --depth quick",
            output_fn=capture_output
        )
        print(f"\n✓ Command returned: {result}")
        print(f"✓ Captured {len(outputs)} output lines")
        return True
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator_direct():
    """Test the orchestrator directly."""
    print("\n" + "=" * 80)
    print("TEST 2: ResearchOrchestrator Direct")
    print("=" * 80)

    try:
        # Create orchestrator
        orchestrator = ResearchOrchestrator(output_dir=Path("./test_output"))
        print("✓ Orchestrator created")

        # Progress callback
        progress_updates = []
        def on_progress(p: ResearchProgress):
            bar = "█" * p.current_step + "░" * (10 - p.current_step)
            msg = f"[{bar}] Step {p.current_step}/10: {p.current_step_name}"
            progress_updates.append(msg)
            print(msg)

        # Run research
        print("\nStarting research...")
        result = orchestrator.research(
            topic="Python async patterns",
            depth="quick",
            progress_callback=on_progress
        )

        print(f"\n✓ Research completed")
        print(f"✓ Session ID: {result.session_id}")
        print(f"✓ Current step: {result.current_step}/10")
        print(f"✓ Sources found: {result.sources_found}")
        print(f"✓ Progress updates: {len(progress_updates)}")

        if result.error:
            print(f"⚠ Error reported: {result.error}")

        if result.report:
            report_str = str(result.report) if hasattr(result.report, '__str__') else repr(result.report)
            print(f"✓ Report generated ({len(report_str)} chars)")
            print("\nReport preview:")
            print("-" * 80)
            print(report_str[:500] + "..." if len(report_str) > 500 else report_str)
            print("-" * 80)

        return True
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n🔬 LYRA DEEP RESEARCH FLOW TEST\n")

    results = []

    # Test 1: Command handler
    results.append(("Research Command Handler", test_research_command()))

    # Test 2: Direct orchestrator
    results.append(("ResearchOrchestrator Direct", test_orchestrator_direct()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
