"""Model and credential management for Lyra CLI.

Handles:
- Model switching (/model command)
- Credential configuration (/credentials, /config)
- Provider management
- API key validation
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class CredentialManager:
    """Manage API credentials for multiple providers."""

    def __init__(self):
        self.config_dir = Path.home() / ".lyra"
        self.config_file = self.config_dir / "credentials.json"
        self.claude_settings = Path.home() / ".claude" / "settings.json"
        self.config_dir.mkdir(exist_ok=True)

    def load_credentials(self) -> dict[str, Any]:
        """Load saved credentials.

        Priority:
        1. ~/.lyra/credentials.json (Lyra-specific)
        2. ~/.claude/settings.json (Claude Code format)
        3. Environment variables
        """
        credentials = {}

        # Try Claude Code settings first
        if self.claude_settings.exists():
            try:
                claude_config = json.loads(self.claude_settings.read_text())
                if "env" in claude_config:
                    env_vars = claude_config["env"]

                    # Map Claude Code env vars to providers
                    key_mapping = {
                        "ANTHROPIC_API_KEY": "anthropic",
                        "OPENAI_API_KEY": "openai",
                        "GEMINI_API_KEY": "gemini",
                        "DEEPSEEK_API_KEY": "deepseek",
                        "GROQ_API_KEY": "groq",
                        "XAI_API_KEY": "xai",
                        "MISTRAL_API_KEY": "mistral",
                        "CEREBRAS_API_KEY": "cerebras",
                        "QWEN_API_KEY": "qwen",
                    }

                    for env_key, provider in key_mapping.items():
                        if env_key in env_vars:
                            credentials[provider] = {
                                "api_key": env_vars[env_key],
                                "source": "claude_settings"
                            }
            except Exception:
                pass  # Ignore errors, fall back to other sources

        # Override with Lyra-specific credentials
        if self.config_file.exists():
            try:
                lyra_creds = json.loads(self.config_file.read_text())
                for provider, cred in lyra_creds.items():
                    if isinstance(cred, dict):
                        credentials[provider] = cred
                    else:
                        credentials[provider] = {"api_key": cred}
            except Exception:
                pass

        # Check environment variables as final fallback
        env_keys = {
            "ANTHROPIC_API_KEY": "anthropic",
            "OPENAI_API_KEY": "openai",
            "GEMINI_API_KEY": "gemini",
            "DEEPSEEK_API_KEY": "deepseek",
        }

        for env_var, provider in env_keys.items():
            if env_var in os.environ and provider not in credentials:
                credentials[provider] = {
                    "api_key": os.environ[env_var],
                    "source": "environment"
                }

        return credentials

    def save_credentials(self, credentials: dict[str, Any]) -> None:
        """Save credentials to file."""
        self.config_file.write_text(json.dumps(credentials, indent=2))
        self.config_file.chmod(0o600)  # Secure permissions

    def set_provider(
        self, provider: str, api_key: str, base_url: str | None = None
    ) -> None:
        """Set credentials for a provider."""
        creds = self.load_credentials()
        creds[provider] = {"api_key": api_key}
        if base_url:
            creds[provider]["base_url"] = base_url
        self.save_credentials(creds)

    def get_provider(self, provider: str) -> dict[str, Any] | None:
        """Get credentials for a provider."""
        creds = self.load_credentials()
        cred = creds.get(provider)
        if isinstance(cred, dict):
            return cred
        elif cred:
            return {"api_key": cred}
        return None

    def list_providers(self) -> list[str]:
        """List configured providers."""
        creds = self.load_credentials()
        return list(creds.keys())


# Available models by provider
AVAILABLE_MODELS = {
    "anthropic": [
        "claude-opus-4.7",
        "claude-opus-4",
        "claude-sonnet-4.6",
        "claude-sonnet-4",
        "claude-haiku-4.5",
        "claude-haiku-4",
    ],
    "openai": [
        "gpt-5",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1",
        "o1-mini",
    ],
    "deepseek": [
        "deepseek-v4-pro",
        "deepseek-v4",
        "deepseek-coder",
    ],
    "ollama": [
        "llama3",
        "codellama",
        "mistral",
        "qwen",
    ],
}

# Default base URLs
DEFAULT_BASE_URLS = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "ollama": "http://localhost:11434",
}


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse model string like 'claude-opus-4.7' or 'deepseek-v4-pro'.

    Returns:
        (provider, model_name)
    """
    model_lower = model_str.lower()

    # Detect provider from model name
    if "claude" in model_lower or "anthropic" in model_lower:
        return ("anthropic", model_str)
    elif "gpt" in model_lower or "o1" in model_lower:
        return ("openai", model_str)
    elif "deepseek" in model_lower:
        return ("deepseek", model_str)
    elif model_lower in ["llama", "codellama", "mistral", "qwen"]:
        return ("ollama", model_str)
    else:
        # Default to anthropic
        return ("anthropic", model_str)


def format_credentials_prompt(provider: str) -> str:
    """Format prompt for credential input."""
    prompts = {
        "anthropic": """
Configure Anthropic (Claude) credentials:

Option 1 - Simple (API Key only):
  API Key: sk-ant-...

Option 2 - Gateway/Proxy (JSON):
  {
    "api_key": "your-key-or-token",
    "base_url": "https://your-gateway.com"
  }

Option 3 - Environment variables (paste JSON):
  {
    "env": {
      "ANTHROPIC_API_KEY": "sk-ant-...",
      "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
    }
  }
""",
        "openai": """
Configure OpenAI credentials:

Option 1 - Simple (API Key only):
  API Key: sk-...

Option 2 - Gateway/Proxy (JSON):
  {
    "api_key": "your-key",
    "base_url": "https://your-gateway.com/v1"
  }
""",
        "deepseek": """
Configure DeepSeek credentials:

Option 1 - Simple (API Key only):
  API Key: sk-...

Option 2 - Custom endpoint (JSON):
  {
    "api_key": "your-key",
    "base_url": "https://api.deepseek.com"
  }
""",
    }
    return prompts.get(provider, f"Enter API key for {provider}:")


def parse_credential_input(input_str: str) -> dict[str, Any]:
    """Parse credential input (simple key or JSON).

    Returns:
        Dict with 'api_key' and optional 'base_url', 'env'
    """
    input_str = input_str.strip()

    # Try parsing as JSON
    if input_str.startswith("{"):
        try:
            data = json.loads(input_str)

            # Handle env format
            if "env" in data:
                env_vars = data["env"]
                result = {}

                # Extract API key from various env var names
                for key_var in [
                    "ANTHROPIC_API_KEY",
                    "ANTHROPIC_AUTH_TOKEN",
                    "OPENAI_API_KEY",
                    "DEEPSEEK_API_KEY",
                ]:
                    if key_var in env_vars:
                        result["api_key"] = env_vars[key_var]
                        break

                # Extract base URL
                for url_var in [
                    "ANTHROPIC_BASE_URL",
                    "OPENAI_BASE_URL",
                    "DEEPSEEK_BASE_URL",
                ]:
                    if url_var in env_vars:
                        result["base_url"] = env_vars[url_var]
                        break

                return result

            # Handle direct format
            return data

        except json.JSONDecodeError:
            pass

    # Simple API key
    return {"api_key": input_str}
