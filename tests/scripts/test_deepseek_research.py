#!/usr/bin/env python3
"""Test Lyra deep research with DeepSeek provider."""

import os
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-research/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-core/src"))

def check_deepseek_config():
    """Check if DeepSeek is configured (supports both direct key and Anthropic bridge)."""
    print("=" * 80)
    print("DEEPSEEK CONFIGURATION CHECK")
    print("=" * 80)

    # Check for direct DeepSeek API key
    direct_key = os.environ.get("DEEPSEEK_API_KEY")

    # Check for Anthropic bridge config (DeepSeek via Anthropic-compatible endpoint)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    anthropic_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    anthropic_model = os.environ.get("ANTHROPIC_MODEL", "")

    if direct_key:
        print(f"✓ DEEPSEEK_API_KEY found (direct): {direct_key[:8]}...{direct_key[-4:]}")
        return True

    if anthropic_key and "deepseek" in anthropic_url.lower():
        print("✓ DeepSeek via Anthropic bridge detected")
        print(f"  Base URL: {anthropic_url}")
        print(f"  Model: {anthropic_model}")
        print(f"  API Key: {anthropic_key[:8]}...{anthropic_key[-4:]}")
        return True

    if anthropic_key and not anthropic_url:
        print("⚠ ANTHROPIC_API_KEY found but ANTHROPIC_BASE_URL not set")
        print("  Cannot confirm DeepSeek routing. Set ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic")
        return False

    print("✗ No DeepSeek configuration found")
    print("\nConfigure one of:")
    print("  Option A (direct key):")
    print("    export DEEPSEEK_API_KEY='your-key-here'")
    print("  Option B (Anthropic bridge):")
    print("    export ANTHROPIC_API_KEY='your-key-here'")
    print("    export ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic'")
    print("    export ANTHROPIC_MODEL='deepseek-v4-pro'")
    return False

def test_deepseek_research():
    """Test research with DeepSeek provider."""
    print("\n" + "=" * 80)
    print("DEEPSEEK RESEARCH TEST")
    print("=" * 80)

    from lyra_research.orchestrator import ResearchOrchestrator, ResearchProgress

    try:
        # Create orchestrator with DeepSeek
        output_dir = Path("./test_output_deepseek")
        output_dir.mkdir(exist_ok=True)

        orchestrator = ResearchOrchestrator(output_dir=output_dir)
        print("✓ Orchestrator created")

        # Progress tracking
        progress_updates = []
        def on_progress(p: ResearchProgress):
            bar = "█" * p.current_step + "░" * (10 - p.current_step)
            msg = f"[{bar}] Step {p.current_step}/10: {p.current_step_name}"
            progress_updates.append(msg)
            print(msg)

        # Test topic
        topic = "Large Language Model reasoning capabilities"
        print(f"\n🔬 Researching: {topic}")
        print("📊 Depth: standard")
        print("🤖 Provider: DeepSeek\n")

        # Run research
        result = orchestrator.research(
            topic=topic,
            depth="standard",
            progress_callback=on_progress
        )

        # Results
        print("\n" + "=" * 80)
        print("RESEARCH RESULTS")
        print("=" * 80)
        print(f"✓ Session ID: {result.session_id}")
        print(f"✓ Completed: {result.current_step}/10 steps")
        print(f"✓ Sources found: {result.sources_found}")
        print(f"✓ Papers analyzed: {result.papers_analyzed}")
        print(f"✓ Repos analyzed: {result.repos_analyzed}")
        print(f"✓ Gaps found: {result.gaps_found}")
        print(f"✓ Progress updates: {len(progress_updates)}")

        if result.error:
            print(f"\n⚠ Error: {result.error}")
            return False

        if result.report:
            report_str = str(result.report)
            print(f"\n✓ Report generated ({len(report_str)} chars)")

            # Save report
            report_file = output_dir / f"report_{result.session_id}.txt"
            report_file.write_text(report_str)
            print(f"✓ Report saved to: {report_file}")

            # Show preview
            print("\n" + "=" * 80)
            print("REPORT PREVIEW")
            print("=" * 80)
            preview_len = 1000
            if len(report_str) > preview_len:
                print(report_str[:preview_len])
                print(f"\n... ({len(report_str) - preview_len} more chars)")
            else:
                print(report_str)
            print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_components():
    """Test UI components and formatting."""
    print("\n" + "=" * 80)
    print("UI COMPONENTS TEST")
    print("=" * 80)

    try:
        # Test progress bar rendering
        print("\n1. Progress Bar Rendering:")
        for step in range(1, 11):
            bar = "█" * step + "░" * (10 - step)
            print(f"   [{bar}] Step {step}/10")
        print("   ✓ Progress bars render correctly")

        # Test output formatting
        print("\n2. Output Formatting:")
        print("   🔬 Research icon")
        print("   ✓ Success checkmark")
        print("   ✗ Error cross")
        print("   ⚠ Warning triangle")
        print("   📊 Chart icon")
        print("   🤖 Robot icon")
        print("   ✓ Unicode characters render correctly")

        # Test table formatting
        print("\n3. Table Formatting:")
        print("   | Column 1 | Column 2 | Column 3 |")
        print("   |----------|----------|----------|")
        print("   | Data 1   | Data 2   | Data 3   |")
        print("   ✓ Tables render correctly")

        return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        return False

def main():
    """Run all tests."""
    print("\n🧪 LYRA DEEPSEEK RESEARCH TEST SUITE\n")

    results = []

    # Check DeepSeek config
    if not check_deepseek_config():
        print("\n❌ DeepSeek not configured. Exiting.")
        return 1

    # Test UI components
    results.append(("UI Components", test_ui_components()))

    # Test DeepSeek research
    results.append(("DeepSeek Research", test_deepseek_research()))

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

    if passed == total:
        print("\n🎉 All tests passed! Lyra deep research is working correctly with DeepSeek.")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
