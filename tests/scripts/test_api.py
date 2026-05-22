#!/usr/bin/env python3
"""Test Lyra API integration."""

import asyncio
from pathlib import Path
from lyra_cli.cli.agent_integration import TUIAgentIntegration


async def test_api():
    """Test API call."""
    print("Initializing agent...")
    agent = TUIAgentIntegration(
        model="claude-sonnet-4.6",
        repo_root=Path.cwd(),
    )

    await agent.initialize()
    print("Agent initialized successfully!")

    print("\nSending message: 'Hello, how are you?'")
    print("Response: ", end="", flush=True)

    async for event in agent.run_agent("Hello, how are you?"):
        if event["type"] == "text":
            print(event["content"], end="", flush=True)
        elif event["type"] == "usage":
            print("\n\nUsage stats:", event["metadata"])

    print("\n\nFinal stats:", agent.get_usage_stats())


if __name__ == "__main__":
    asyncio.run(test_api())
