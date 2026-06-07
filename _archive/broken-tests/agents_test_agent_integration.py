#!/usr/bin/env python3
"""Test agent integration"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

def test_agent_imports():
    """Test agent module imports"""
    print("✓ Testing agent imports...")

    from lyra_cli.agent import AgentLoopFactory, AgentOutputCallback, SimpleAgentLoop
    from lyra_cli.cli.agent_handler import CLIAgentHandler

    print("  - AgentOutputCallback:", AgentOutputCallback)
    print("  - SimpleAgentLoop:", SimpleAgentLoop)
    print("  - AgentLoopFactory:", AgentLoopFactory)
    print("  - CLIAgentHandler:", CLIAgentHandler)
    print("✓ All agent imports successful")

def test_agent_handler():
    """Test CLI agent handler"""
    print("\n✓ Testing CLIAgentHandler...")

    from lyra_cli.cli.agent_handler import CLIAgentHandler
    from rich.console import Console

    console = Console()
    handler = CLIAgentHandler(console)

    # Test callbacks
    handler.on_turn_start("test-turn-1")
    handler.on_tool_use("Read", {"file_path": "test.py"})
    handler.on_stream_chunk("Hello ")
    handler.on_stream_chunk("world!")
    handler.on_turn_end("test-turn-1", {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150
        }
    })

    print("✓ CLIAgentHandler working correctly")

def test_agent_loop_creation():
    """Test agent loop creation (without API key)"""
    print("\n✓ Testing agent loop creation...")

    from lyra_cli.agent import AgentLoopFactory
    from lyra_cli.cli.agent_handler import CLIAgentHandler
    from rich.console import Console

    console = Console()
    handler = CLIAgentHandler(console)

    # This should fail without API key
    try:
        AgentLoopFactory.create_simple_loop(
            callback=handler,
            model="claude-opus-4-20250514"
        )
        print("  - Agent loop created (API key found)")
    except ValueError as e:
        print(f"  - Agent loop creation failed as expected: {e}")
        print("  - This is normal if ANTHROPIC_API_KEY is not set")

    print("✓ Agent loop creation test passed")

if __name__ == "__main__":
    try:
        test_agent_imports()
        test_agent_handler()
        test_agent_loop_creation()
        print("\n✓ All agent integration tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
