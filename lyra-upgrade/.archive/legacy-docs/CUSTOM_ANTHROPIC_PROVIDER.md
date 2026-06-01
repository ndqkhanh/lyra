# Custom Anthropic Provider Configuration Guide

## Problem
Lyra does NOT natively support `ANTHROPIC_BASE_URL` override for custom Anthropic-compatible endpoints.

## Solution: Custom Provider

### Step 1: Create Custom Provider

Create `~/.lyra/custom_anthropic.py`:

```python
"""Custom Anthropic provider with base_url override support."""

import os
from typing import Any, Optional
from anthropic import Anthropic
from lyra_cli.providers.anthropic import AnthropicProvider


class CustomAnthropicProvider(AnthropicProvider):
    """Anthropic provider with custom base_url support."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize with custom base_url support.
        
        Args:
            api_key: API key (defaults to ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY)
            model: Model name (defaults to ANTHROPIC_MODEL or claude-opus-4.5)
            base_url: Custom base URL (defaults to ANTHROPIC_BASE_URL)
        """
        # Get credentials from environment
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        
        self.base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com"
        )
        
        self.model = (
            model
            or os.environ.get("ANTHROPIC_MODEL")
            or "claude-opus-4.5"
        )
        
        # Initialize Anthropic client with custom base_url
        self._client = Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
        )
```

### Step 2: Register in Settings

Edit `~/.lyra/settings.json`:

```json
{
  "config_version": 2,
  "providers": {
    "custom-anthropic": "custom_anthropic:CustomAnthropicProvider"
  },
  "default_provider": "custom-anthropic",
  "default_model": "claude-opus-4.5"
}
```

### Step 3: Set Environment Variables

```bash
export ANTHROPIC_AUTH_TOKEN="your-custom-token"
export ANTHROPIC_BASE_URL="https://custom-anthropic-endpoint.com"
export ANTHROPIC_MODEL="claude-opus-4.5"
```

Or create `~/.lyra/.env`:

```bash
ANTHROPIC_AUTH_TOKEN=your-custom-token
ANTHROPIC_BASE_URL=https://custom-anthropic-endpoint.com
ANTHROPIC_MODEL=claude-opus-4.5
```

### Step 4: Use Custom Provider

```bash
# Start Lyra with custom provider
lyra

# Or explicitly specify
lyra run --llm custom-anthropic

# Switch models in REPL
/model custom-anthropic
```

## Alternative: Settings-Only Configuration

You can also configure everything in `~/.lyra/settings.json`:

```json
{
  "config_version": 2,
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your-token-here",
    "ANTHROPIC_BASE_URL": "https://custom-anthropic-endpoint.com",
    "ANTHROPIC_MODEL": "claude-opus-4.5"
  },
  "providers": {
    "custom-anthropic": "custom_anthropic:CustomAnthropicProvider"
  },
  "default_provider": "custom-anthropic",
  "permissions": {
    "allow": [],
    "deny": []
  }
}
```

## Verification

Test your custom provider:

```bash
# Check if provider is registered
lyra run --llm custom-anthropic --help

# Test with a simple query
echo "Hello, test custom endpoint" | lyra run --llm custom-anthropic
```

## Troubleshooting

**Provider not found:**
- Ensure `custom_anthropic.py` is in `~/.lyra/` or in your PYTHONPATH
- Check import string format: `"module:ClassName"`

**Authentication errors:**
- Verify `ANTHROPIC_AUTH_TOKEN` is set correctly
- Check base URL is accessible: `curl https://custom-anthropic-endpoint.com`

**Model not available:**
- Verify model name matches your custom endpoint's models
- Check endpoint documentation for available models

## Notes

- This workaround is necessary because Lyra's built-in Anthropic provider doesn't support `base_url` override
- The custom provider inherits all functionality from the base `AnthropicProvider`
- Environment variables take precedence over settings.json values
- Credentials are stored securely in `~/.lyra/auth.json` (mode 0600)
