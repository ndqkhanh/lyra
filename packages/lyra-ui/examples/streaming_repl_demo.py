"""
Example: Streaming REPL Demo

Demonstrates the streaming REPL interface with various features.
"""

import asyncio

from lyra_ui.streaming_repl import (
    REPLConfig,
    REPLMode,
    StreamingREPL,
    StatusBar,
    ToolProgressDisplay,
)


async def demo_basic_repl():
    """Demo basic REPL usage."""
    print("=== Basic REPL Demo ===\n")

    config = REPLConfig(
        mode=REPLMode.AGENT,
        model="sonnet",
    )

    repl = StreamingREPL(config)

    # Simulate some interactions
    print("REPL created successfully!")
    print(f"Mode: {repl.config.mode.value}")
    print(f"Model: {repl.config.model}")
    print()


def demo_status_bar():
    """Demo status bar."""
    print("=== Status Bar Demo ===\n")

    status_bar = StatusBar()

    # Update with sample data
    status_bar.update(
        mode="plan",
        model="opus",
        tokens=1500,
        cost=0.75,
        elapsed=45.5,
    )

    status_bar.display()
    print()


def demo_tool_progress():
    """Demo tool progress display."""
    print("=== Tool Progress Demo ===\n")

    progress = ToolProgressDisplay()
    progress.start()

    # Add some tools
    progress.add_tool("read_file", "Reading configuration")
    progress.add_tool("analyze_code", "Analyzing codebase")
    progress.add_tool("generate_plan", "Generating implementation plan")

    # Simulate progress
    import time

    for i in range(0, 101, 20):
        progress.update_tool("read_file", float(i))
        time.sleep(0.1)

    progress.complete_tool("read_file")

    for i in range(0, 101, 10):
        progress.update_tool("analyze_code", float(i))
        time.sleep(0.1)

    progress.complete_tool("analyze_code")

    for i in range(0, 101, 15):
        progress.update_tool("generate_plan", float(i))
        time.sleep(0.1)

    progress.complete_tool("generate_plan")

    progress.stop()
    print()


def demo_commands():
    """Demo command palette."""
    print("=== Command Palette Demo ===\n")

    repl = StreamingREPL()

    # Test commands
    print("Available commands:")
    print("  /help   - Show help")
    print("  /model  - Change model")
    print("  /mode   - Change mode")
    print("  /clear  - Clear screen")
    print("  /exit   - Exit REPL")
    print()

    # Execute some commands
    print("Executing /help:")
    result = repl._cmd_help()
    print(result[:200] + "...")
    print()

    print("Executing /model opus:")
    result = repl._cmd_model("opus")
    print(result)
    print()

    print("Executing /mode plan:")
    result = repl._cmd_mode("plan")
    print(result)
    print()


def demo_completer():
    """Demo autocomplete."""
    print("=== Autocomplete Demo ===\n")

    repl = StreamingREPL()

    # Set up files and skills
    repl.completer.set_files([
        "main.py",
        "config.yaml",
        "test_streaming.py",
        "README.md",
    ])

    repl.completer.set_skills([
        "python-patterns",
        "testing",
        "security",
        "performance",
    ])

    print("Autocomplete configured!")
    print(f"Files: {len(repl.completer.files)}")
    print(f"Skills: {len(repl.completer.skills)}")
    print()

    print("Try typing:")
    print("  /he<TAB>      - Complete to /help")
    print("  @ma<TAB>      - Complete to @main.py")
    print("  #py<TAB>      - Complete to #python-patterns")
    print()


async def demo_streaming():
    """Demo streaming output."""
    print("=== Streaming Output Demo ===\n")

    repl = StreamingREPL()

    print("Streaming mock response:")
    print("-" * 50)

    # Stream a mock response
    async for chunk in repl._mock_agent_stream("demo input"):
        print(chunk, end="", flush=True)

    print()
    print("-" * 50)
    print()


def demo_mode_switching():
    """Demo mode switching."""
    print("=== Mode Switching Demo ===\n")

    repl = StreamingREPL()

    modes = ["agent", "plan", "ask", "auto"]

    for mode in modes:
        repl._cmd_mode(mode)
        badge = repl._get_mode_badge()
        print(f"Mode: {mode:10} -> Badge: {badge}")

    print()


def demo_stats_tracking():
    """Demo statistics tracking."""
    print("=== Statistics Tracking Demo ===\n")

    repl = StreamingREPL()

    # Simulate some activity
    repl.update_stats(
        tokens_used=2500,
        total_cost=1.25,
        elapsed_time=120.5,
        agents_active=3,
    )

    print("Statistics updated:")
    print(f"  Tokens used: {repl.stats.tokens_used:,}")
    print(f"  Total cost: ${repl.stats.total_cost:.2f}")
    print(f"  Elapsed time: {repl.stats.elapsed_time:.1f}s")
    print(f"  Active agents: {repl.stats.agents_active}")
    print()


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Lyra Streaming REPL - Feature Demonstrations")
    print("=" * 60 + "\n")

    # Run demos
    asyncio.run(demo_basic_repl())
    demo_status_bar()
    demo_tool_progress()
    demo_commands()
    demo_completer()
    asyncio.run(demo_streaming())
    demo_mode_switching()
    demo_stats_tracking()

    print("=" * 60)
    print("All demos completed!")
    print("=" * 60 + "\n")

    print("To start the interactive REPL, run:")
    print("  python -m lyra_ui.cli")
    print()


if __name__ == "__main__":
    main()
