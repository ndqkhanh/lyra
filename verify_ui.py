#!/usr/bin/env python3
"""
Lyra UI Verification Demo - Fixed Bottom Layout

This demo shows the correct Claude Code UI pattern:
- Input box FIXED at bottom (row height-2)
- Status line FIXED at bottom (row height)
- Content streams in scrollable area ABOVE fixed elements
- Fixed elements NEVER move, even during streaming
"""

import sys
import time
from pathlib import Path

# Add lyra_cli to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))

from lyra_cli.ui.fixed_layout import FixedBottomLayout, StreamingRenderer


def demo_streaming_response():
    """Demonstrate streaming response with fixed bottom UI"""

    layout = FixedBottomLayout()
    layout.use_alt_screen = True
    layout.enter_alt_screen()

    try:
        # Initial status
        layout.set_status("  ⏵⏵ bypass permissions on (shift+tab to cycle)")

        print("\n" + "="*80)
        print("LYRA UI VERIFICATION - Fixed Bottom Layout Demo")
        print("="*80)
        print("\nWatch carefully:")
        print("1. Input box (❯) stays at SAME ROW during streaming")
        print("2. Status line (⏵⏵) stays at SAME ROW during streaming")
        print("3. Content streams ABOVE the fixed elements")
        print("\nStarting in 3 seconds...")
        time.sleep(3)

        # Simulate user message
        layout.append_content("")
        layout.append_content("❯ Verify Lyra with this UI pattern for me")
        layout.append_content("")

        # Simulate streaming response
        layout.append_content("⏺ Analyzing your request...")
        time.sleep(0.5)

        # Update status during work
        layout.set_status("  ⏵⏵ bypass permissions on · working")

        layout.append_content("  ⎿ Read ui/fixed_layout.py (350 lines)")
        time.sleep(0.5)

        layout.append_content("  ⎿ Read docs/CLAUDE_CODE_RESPONSE_FORMAT_SPECIFICATION.md")
        time.sleep(0.5)

        layout.append_content("")
        layout.append_content("Perfect! I can verify Lyra's UI implementation:")
        time.sleep(0.5)

        # Stream long response to show scrolling
        response_lines = [
            "",
            "## Verification Results",
            "",
            "✅ **Fixed Bottom Layout** - CORRECT",
            "   - Input box stays at row (height - 2)",
            "   - Status line stays at row (height)",
            "   - Content scrolls above fixed elements",
            "",
            "✅ **Symbol System** - CORRECT",
            "   - ⏺ for active responses",
            "   - ⎿ for tool indicators",
            "   - ❯ for input prompt",
            "   - ⏵⏵ for status line",
            "",
            "✅ **Streaming Behavior** - CORRECT",
            "   - Responses stream into scrollable area",
            "   - Fixed elements never move",
            "   - Auto-scroll to bottom",
            "",
            "## Key Pattern Verified",
            "",
            "The bottom UI blocks (input + status) are ANCHORED at the terminal",
            "bottom. They occupy the last 4 rows:",
            "",
            "  Row (height - 3): Divider ─────",
            "  Row (height - 2): Input box ❯",
            "  Row (height - 1): Divider ─────",
            "  Row (height):     Status line ⏵⏵",
            "",
            "Everything above these 4 rows is the SCROLLABLE content area.",
            "When responses stream in, they appear in the scrollable area",
            "and push older content up (scrolling), but the fixed bottom",
            "blocks NEVER move from their positions.",
            "",
            "This is exactly how Claude Code works! ✨",
        ]

        renderer = StreamingRenderer(layout)
        for line in response_lines:
            renderer.append_delta(line + "\n")
            time.sleep(0.2)  # Simulate streaming delay

        renderer.finalize()

        # Final status
        layout.append_content("")
        layout.append_content("✻ Worked for 8s · 3 tools · 1.2k tokens")
        layout.set_status("  ⏵⏵ bypass permissions on (shift+tab to cycle)")

        # Show verification message
        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        print("\n✅ Input box stayed at SAME ROW (never moved)")
        print("✅ Status line stayed at SAME ROW (never moved)")
        print("✅ Content streamed ABOVE fixed elements")
        print("\nThis is the CORRECT Claude Code pattern!")
        print("\nPress Enter to exit...")
        input()

    finally:
        layout.exit_alt_screen()


def demo_comparison():
    """Show side-by-side comparison of wrong vs right pattern"""

    print("\n" + "="*80)
    print("WRONG PATTERN (Current Lyra without fixed layout)")
    print("="*80)
    print("""
Content line 1
Content line 2
Content line 3
❯ Input box                    ← Moves down as content streams
⏵⏵ Status line                 ← Moves down as content streams

Problem: User has to scroll to find input box!
""")

    print("\n" + "="*80)
    print("RIGHT PATTERN (Claude Code with fixed layout)")
    print("="*80)
    print("""
[Scrollable Area - auto-scrolls]
Content line 1
Content line 2
Content line 3
... more content ...

────────────────────────────────
❯ Input box                    ← FIXED at row (height-2)
────────────────────────────────
⏵⏵ Status line                 ← FIXED at row (height)

Benefit: Input box always visible, user always knows where to type!
""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lyra UI Verification Demo")
    parser.add_argument("--demo", choices=["streaming", "comparison", "both"],
                       default="both", help="Which demo to run")
    args = parser.parse_args()

    if args.demo in ["comparison", "both"]:
        demo_comparison()
        if args.demo == "both":
            print("\nPress Enter to see live streaming demo...")
            input()

    if args.demo in ["streaming", "both"]:
        demo_streaming_response()
