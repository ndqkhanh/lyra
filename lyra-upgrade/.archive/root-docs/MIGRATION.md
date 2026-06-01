# Migration Guide: v5.x → v6.0.0

## Overview

Lyra v6.0.0 replaces the multi-provider fallback system with **single-provider model routing**. This change makes provider selection predictable, cost-aware, and transparent.

## What Changed

### Before (v5.x): Cross-Provider Fallback

```yaml
# Old config (~/.lyra/settings.json)
fallback_chain:
  - anthropic
  - deepseek
  - openai
  - gemini
```

**Problems:**
- Unpredictable: You never knew which provider would handle your request
- Cost-opaque: Couldn't control which provider to use for cost optimization
- Silent failures: Errors were hidden by automatic fallback

### After (v6.0.0): Single-Provider Routing

```yaml
# New config (~/.lyra/settings.json)
primary_provider: anthropic  # Pick ONE provider
enable_task_routing: true    # Smart routing within provider
```

**Benefits:**
- **Predictable**: Always know which provider you're using
- **Cost-aware**: Choose provider based on pricing (DeepSeek is 10-20× cheaper)
- **Quality-aware**: Choose provider based on model quality
- **Transparent**: Clear errors instead of silent fallbacks

## Migration Steps

### 1. Automatic Migration

Your config is automatically migrated when you upgrade:

```bash
# Upgrade Lyra
pip install --upgrade lyra-cli

# First run migrates your config
lyra
```

The migration uses the **first provider** from your old `fallback_chain` as `primary_provider`.

### 2. Manual Configuration (Optional)

Choose your preferred provider explicitly:

```bash
# Set primary provider
lyra config set primary_provider anthropic  # or deepseek, openai, gemini, etc.

# Enable/disable task routing
lyra config set enable_task_routing true
```

### 3. Verify Migration

Check your config:

```bash
lyra config show
```

Expected output:
```yaml
primary_provider: anthropic
enable_task_routing: true
config_version: 4
```

## Provider Selection Guide

### Cost-Optimized (Recommended)

```bash
lyra config set primary_provider deepseek
```

**Why DeepSeek?**
- 10-20× cheaper than Claude/GPT-5
- Matches Claude/GPT-5 on agentic benchmarks
- Best for tool-heavy workflows (Lyra's sweet spot)

### Quality-Optimized

```bash
lyra config set primary_provider anthropic
```

**Why Anthropic?**
- Best tool-using capabilities
- Most reliable for complex agent workflows
- Reference target for Lyra development

### Balanced

```bash
lyra config set primary_provider openai
```

**Why OpenAI?**
- Good balance of cost and quality
- Wide model selection (GPT-4o, o3, o3-mini)
- Familiar for most users

## Task Routing Within Provider

When `enable_task_routing: true`, Lyra routes tasks to appropriate models **within your chosen provider**:

### Anthropic Example

```python
# Reasoning task → Opus
"Explain quantum computing" → claude-opus-4.7

# Coding task → Sonnet
"Write a function" → claude-sonnet-4.6

# Quick task → Haiku
"What is Python?" → claude-haiku-4.5
```

### DeepSeek Example

```python
# Reasoning task → Pro
"Analyze this code" → deepseek-v4-pro

# Coding task → Flash
"Fix this bug" → deepseek-v4-flash

# Quick task → Chat
"List files" → deepseek-chat
```

## Breaking Changes

### 1. `fallback_chain` Removed

**Old:**
```python
from lyra_cli.config_io import DEFAULT_FALLBACK_CHAIN
```

**New:**
```python
# No longer exists - use primary_provider instead
from lyra_cli.config_io import SettingsConfig

config = SettingsConfig(primary_provider="anthropic")
```

### 2. `FallbackExecutor` Deprecated

**Old:**
```python
from lyra_cli.llm_fallback import FallbackExecutor

executor = FallbackExecutor(chain=["anthropic", "deepseek"])
result = executor.execute(messages)
```

**New:**
```python
from lyra_cli.llm_factory import build_llm

provider = build_llm("anthropic")  # Pick ONE provider
try:
    result = provider.generate(messages)
except ProviderError as e:
    # Handle errors explicitly
    print(f"Provider failed: {e}")
```

### 3. Cross-Provider Task Routing Removed

**Old:**
```python
# Task routing mixed providers unpredictably
"Explain X" → claude-opus-4.7
"Write Y" → deepseek-v4-flash  # Different provider!
```

**New:**
```python
# Task routing stays within provider
"Explain X" → claude-opus-4.7
"Write Y" → claude-sonnet-4.6  # Same provider family
```

## API Changes

### Config Schema

**Old (v3):**
```json
{
  "config_version": 3,
  "fallback_chain": ["anthropic", "deepseek", "openai"]
}
```

**New (v4):**
```json
{
  "config_version": 4,
  "primary_provider": "anthropic",
  "enable_task_routing": true
}
```

### Environment Variables

**New in v6.0.0:**
```bash
# Active provider is tracked in session
export LYRA_ACTIVE_PROVIDER=anthropic
```

This is set automatically by `build_llm()` and used by the session for task routing.

## Troubleshooting

### "Config migration: fallback_chain is deprecated"

**Cause:** Your config still has `fallback_chain` from v5.x.

**Fix:**
```bash
lyra config set primary_provider anthropic
```

### "Provider failed: ANTHROPIC_API_KEY not set"

**Cause:** Your primary provider doesn't have credentials.

**Fix:**
```bash
# Option 1: Set API key
export ANTHROPIC_API_KEY=your-key

# Option 2: Switch provider
lyra config set primary_provider deepseek
export DEEPSEEK_API_KEY=your-key
```

### "Task routing not working"

**Cause:** `enable_task_routing` is disabled.

**Fix:**
```bash
lyra config set enable_task_routing true
```

## FAQ

### Q: Can I still use multiple providers?

**A:** Yes, but explicitly:

```bash
# Use Anthropic for this session
lyra --llm anthropic

# Use DeepSeek for this session
lyra --llm deepseek
```

### Q: What if my primary provider is down?

**A:** Lyra will show a clear error instead of silently falling back. Switch providers explicitly:

```bash
lyra --llm deepseek  # Use DeepSeek instead
```

### Q: How do I optimize for cost?

**A:** Use DeepSeek as primary provider:

```bash
lyra config set primary_provider deepseek
```

DeepSeek is 10-20× cheaper than Claude/GPT-5 with comparable quality.

### Q: Can I disable task routing?

**A:** Yes:

```bash
lyra config set enable_task_routing false
```

This uses the default model for all tasks (usually the coding tier).

### Q: Will my old config still work?

**A:** Yes! Old configs are automatically migrated on first run. The first provider in your `fallback_chain` becomes your `primary_provider`.

## Need Help?

- **Issues:** https://github.com/your-org/lyra/issues
- **Docs:** https://lyra.dev/docs/v6-migration
- **Discord:** https://discord.gg/lyra
