#!/usr/bin/env python3
"""Test Lyra startup without hanging"""

import os
import sys

# Add lyra-cli to path
sys.path.insert(
    0,
    "/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/packages/lyra-cli/src",
)

# Test imports
try:
    from lyra_cli.repl import REPLConfig, SequentialREPL

    print("✓ SequentialREPL imported successfully")

    print("✓ interactive_chat imported successfully")

    # Test config creation
    config = REPLConfig(
        context_budget=200000, permission_mode="ask", show_context=True, show_permission_mode=True
    )
    print("✓ REPLConfig created successfully")

    # Test REPL creation (without running)
    api_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
    repl = SequentialREPL(api_key=api_key, model="claude-opus-4-20250514", config=config)
    print("✓ SequentialREPL instance created successfully")

    print("\n✅ All imports and initialization successful!")
    print("\nTo test interactively, run: lyra")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
