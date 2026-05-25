"""Multi-provider fallback executor (DEPRECATED in v6.0.0).

⚠️  DEPRECATION NOTICE ⚠️

This module is deprecated as of Lyra v6.0.0 and will be removed in v7.0.0.

The multi-provider fallback system has been replaced with single-provider
model routing. When you select a provider (e.g., Anthropic, DeepSeek),
Lyra now routes tasks within that provider's model family instead of
silently switching between providers.

**Old behavior (v5.x):**
```python
# Auto mode cascaded through providers
claude → deepseek → gemini → openai → ...
# Task routing mixed providers unpredictably
```

**New behavior (v6.0.0+):**
```python
# Auto mode picks ONE provider and sticks with it
provider = "anthropic"  # or "deepseek", "openai", etc.

# Task routing stays within provider family
reasoning → claude-opus-4.7
coding → claude-sonnet-4.6
quick → claude-haiku-4.5
```

**Migration Guide:**

If you were using `FallbackExecutor` directly:

```python
# OLD (v5.x)
from lyra_cli.llm_fallback import FallbackExecutor
executor = FallbackExecutor(chain=["anthropic", "deepseek", "openai"])
result = executor.execute(messages)

# NEW (v6.0.0+)
from lyra_cli.llm_factory import build_llm
provider = build_llm("anthropic")  # Pick ONE provider explicitly
try:
    result = provider.generate(messages)
except ProviderError as e:
    # Handle errors explicitly instead of silent fallback
    print(f"Provider failed: {e}")
    # Optionally try another provider explicitly
    provider = build_llm("deepseek")
    result = provider.generate(messages)
```

If you had `fallback_chain` in your config:

```python
# OLD config (~/.lyra/config.yaml)
fallback_chain:
  - anthropic
  - deepseek
  - openai

# NEW config (v6.0.0+)
primary_provider: anthropic  # Uses first from old chain
```

**Why this change?**

1. **Predictable**: Always know which provider you're using
2. **Cost-aware**: Choose provider based on pricing
3. **Quality-aware**: Choose provider based on model quality
4. **Transparent**: Clear errors instead of silent fallbacks

**Need help?**

See MIGRATION.md for detailed migration instructions.
"""

from __future__ import annotations

import warnings
from typing import Any


class AllProvidersExhausted(Exception):
    """Raised when every provider in the fallback chain has failed.

    DEPRECATED: This exception is no longer raised in v6.0.0+.
    Use provider-specific exceptions instead.
    """


class FallbackExecutor:
    """Execute a prompt across a fallback chain of providers.

    DEPRECATED: This class is deprecated in v6.0.0 and will be removed in v7.0.0.

    Use `build_llm()` to select a single provider explicitly instead.
    """

    def __init__(self, chain: list[str] | None = None, provider_factory: Any = None):
        warnings.warn(
            "FallbackExecutor is deprecated in v6.0.0 and will be removed in v7.0.0. "
            "Use build_llm() to select a single provider explicitly. "
            "See llm_fallback.py module docstring for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.chain = chain or []
        self._provider_factory = provider_factory

    def execute(self, messages: list[Any], model_override: str | None = None) -> tuple[str, str, Any]:
        """Execute messages (DEPRECATED).

        Raises:
            DeprecationWarning: Always raises to prevent usage.
        """
        raise DeprecationWarning(
            "FallbackExecutor.execute() is deprecated. "
            "Use build_llm() to get a provider and call generate() directly. "
            "See llm_fallback.py module docstring for migration guide."
        )

    def stream(self, messages: list[Any], model_override: str | None = None) -> Any:
        """Stream messages (DEPRECATED).

        Raises:
            DeprecationWarning: Always raises to prevent usage.
        """
        raise DeprecationWarning(
            "FallbackExecutor.stream() is deprecated. "
            "Use build_llm() to get a provider and call stream() directly. "
            "See llm_fallback.py module docstring for migration guide."
        )


# Keep these for backward compatibility (will be removed in v7.0.0)
DEFAULT_FALLBACK_CHAIN: list[str] = []


def execute_with_fallback(
    messages: list[Any],
    chain: list[str] | None = None,
    model_override: str | None = None,
) -> tuple[str, str, Any]:
    """Execute with fallback (DEPRECATED).

    Raises:
        DeprecationWarning: Always raises to prevent usage.
    """
    raise DeprecationWarning(
        "execute_with_fallback() is deprecated. "
        "Use build_llm() to get a provider and call generate() directly. "
        "See llm_fallback.py module docstring for migration guide."
    )


__all__ = [
    "AllProvidersExhausted",
    "FallbackExecutor",
    "DEFAULT_FALLBACK_CHAIN",
    "execute_with_fallback",
]
