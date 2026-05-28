#!/usr/bin/env python3
"""
Extract Anthropic API key from Claude Code settings and configure it for Lyra.
"""

import json
import os
import sys
from pathlib import Path


def find_api_key():
    """Find API key from various sources."""

    # Check environment variable first
    env_key = os.getenv('ANTHROPIC_API_KEY')
    if env_key:
        return env_key, 'environment'

    # Check Claude Code settings
    claude_settings = Path.home() / '.claude' / 'settings.json'
    if claude_settings.exists():
        try:
            with open(claude_settings) as f:
                settings = json.load(f)

            # Check env section
            if 'env' in settings and 'ANTHROPIC_API_KEY' in settings['env']:
                return settings['env']['ANTHROPIC_API_KEY'], 'claude_settings'

            # Check direct apiKey field
            if 'apiKey' in settings:
                return settings['apiKey'], 'claude_settings'

        except Exception as e:
            print(f"Warning: Could not read Claude settings: {e}", file=sys.stderr)

    return None, None


def setup_lyra_config(api_key: str):
    """Set up Lyra configuration with API key."""

    lyra_dir = Path.home() / '.lyra'
    lyra_dir.mkdir(parents=True, exist_ok=True)

    config_file = lyra_dir / 'config.json'

    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {}

    # Update with API key
    config['api_key'] = api_key
    config.setdefault('model', 'opus')
    config.setdefault('verbose', False)

    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Lyra config updated: {config_file}")


def main():
    print("🔍 Searching for Anthropic API key...")

    api_key, source = find_api_key()

    if not api_key:
        print("❌ No API key found!")
        print("\nPlease set your API key using one of these methods:")
        print("1. Environment variable: export ANTHROPIC_API_KEY='sk-ant-...'")
        print("2. Claude settings: Add to ~/.claude/settings.json")
        print("3. Get a key from: https://console.anthropic.com/")
        sys.exit(1)

    # Mask the key for display
    masked_key = f"{api_key[:10]}...{api_key[-4:]}"
    print(f"✅ Found API key from {source}: {masked_key}")

    # Set up Lyra config
    setup_lyra_config(api_key)

    # Also export to environment for current session
    os.environ['ANTHROPIC_API_KEY'] = api_key
    print("✅ API key exported to environment")

    print("\n🚀 Lyra is ready to use!")
    print("\nNext steps:")
    print("  1. Run: cd packages/lyra-cli")
    print("  2. Run: python -m lyra_cli")
    print("  3. Or run E2E tests: pytest tests/e2e/")


if __name__ == '__main__':
    main()
