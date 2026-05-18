# Configuration Guide

Complete guide to configuring Lyra for your needs.

---

## Overview

Lyra can be configured through:
1. **Environment variables** - Quick setup
2. **Configuration files** - Persistent settings
3. **Command-line flags** - Session-specific overrides

---

## Environment Variables

### API Keys

```bash
# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI (GPT)
export OPENAI_API_KEY="sk-..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# Google (Gemini)
export GOOGLE_API_KEY="..."
```

### Memory Configuration

```bash
# Memory tier sizes
export LYRA_MEMORY_HOT_SIZE=100
export LYRA_MEMORY_WARM_SIZE=500
export LYRA_MEMORY_COLD_SIZE=10000

# Memory database path
export LYRA_MEMORY_DB=".lyra/memory/memories.db"
```

### Research Configuration

```bash
# Research sources
export LYRA_RESEARCH_SOURCES="arxiv,semantic_scholar,github"

# Quality threshold
export LYRA_RESEARCH_MIN_QUALITY=0.7

# Max results per source
export LYRA_RESEARCH_MAX_RESULTS=50
```

### Evolution Configuration

```bash
# Enable self-evolution
export LYRA_EVOLUTION_ENABLED=true

# Verification required
export LYRA_EVOLUTION_VERIFY=true

# Sandbox enabled
export LYRA_EVOLUTION_SANDBOX=true
```

### Budget Configuration

```bash
# Budget cap in USD
export LYRA_BUDGET_CAP=10.00

# Cost tracking enabled
export LYRA_COST_TRACKING=true
```

---

## Configuration Files

### Main Configuration

Create `.lyra/config.json`:

```json
{
  "model": {
    "default": "claude-opus-4-7",
    "fallback": "claude-sonnet-4-6",
    "budget_cap_usd": 10.0
  },
  "memory": {
    "hot_tier_size": 100,
    "warm_tier_size": 500,
    "cold_tier_size": 10000,
    "db_path": ".lyra/memory/memories.db"
  },
  "research": {
    "sources": ["arxiv", "semantic_scholar", "github"],
    "min_quality": 0.7,
    "max_results": 50,
    "citation_depth": 3
  },
  "evolution": {
    "enabled": true,
    "verification_required": true,
    "sandbox_enabled": true,
    "cost_cap_usd": 5.0
  },
  "context": {
    "max_tokens": 100000,
    "compression_enabled": true,
    "cache_enabled": true
  },
  "process": {
    "transparency_enabled": true,
    "event_logging": true
  }
}
```

### Research Configuration

Create `.lyra/research/config.json`:

```json
{
  "sources": {
    "arxiv": {
      "enabled": true,
      "max_results": 50,
      "categories": ["cs.AI", "cs.CL", "cs.LG"]
    },
    "semantic_scholar": {
      "enabled": true,
      "api_key": "...",
      "max_results": 50
    },
    "github": {
      "enabled": true,
      "token": "...",
      "max_results": 20
    },
    "openreview": {
      "enabled": true
    },
    "huggingface": {
      "enabled": true
    },
    "papers_with_code": {
      "enabled": true
    },
    "acl_anthology": {
      "enabled": true
    }
  },
  "quality": {
    "min_score": 0.5,
    "citation_weight": 0.3,
    "recency_weight": 0.2,
    "github_weight": 0.3,
    "source_weight": 0.2
  },
  "citation": {
    "max_depth": 3,
    "max_papers": 100,
    "traversal_mode": "snowball"
  },
  "memory": {
    "zettelkasten": ".lyra/research/notes/",
    "dci": ".lyra/research/corpus/",
    "reasoning_bank": ".lyra/research/strategies/",
    "memento": ".lyra/research/sessions/"
  }
}
```

### Evolution Configuration

Create `.lyra/evolution/config.json`:

```json
{
  "memory": {
    "db_path": ".lyra/memory/memories.db",
    "hot_tier_size": 100,
    "warm_tier_size": 500,
    "cold_tier_size": 10000
  },
  "skills": {
    "library_path": ".lyra/skills/",
    "verification_enabled": true,
    "quality_threshold": 0.7,
    "auto_extract": true
  },
  "evolution": {
    "sandbox_enabled": true,
    "verification_required": true,
    "rollback_on_failure": true,
    "max_iterations": 10
  },
  "safety": {
    "cost_cap_usd": 10.0,
    "unsafe_actions": ["rm -rf", "DROP TABLE", "DELETE FROM"],
    "halt_on_violation": true
  },
  "learning": {
    "voyager_enabled": true,
    "reflexion_enabled": true,
    "pattern_recognition": true
  }
}
```

---

## Command-Line Flags

### Model Selection

```bash
# Use specific model
lyra --model claude-opus-4-7

# Use fastest model
lyra --model claude-haiku-4-5

# Use reasoning model
lyra --model o1-preview
```

### Budget Control

```bash
# Set budget cap
lyra --budget 10.00

# Disable budget tracking
lyra --no-budget
```

### Session Management

```bash
# Resume session
lyra --resume <session-id>

# Pin session ID
lyra --session <session-id>

# Export session
lyra --export session.json
```

### Feature Flags

```bash
# Enable research
lyra --research

# Enable evolution
lyra --evolution

# Enable process transparency
lyra --transparency

# Disable all features
lyra --minimal
```

---

## Advanced Configuration

### Custom Model Routing

Create `.lyra/routing.json`:

```json
{
  "tiers": {
    "fast": {
      "models": ["claude-haiku-4-5", "gpt-4o-mini"],
      "max_cost": 0.01
    },
    "reasoning": {
      "models": ["claude-opus-4-7", "o1-preview"],
      "max_cost": 0.10
    },
    "advisor": {
      "models": ["claude-opus-4-7", "gemini-2.5-pro"],
      "max_cost": 0.50
    }
  },
  "routing": {
    "simple_queries": "fast",
    "complex_tasks": "reasoning",
    "strategic_decisions": "advisor"
  }
}
```

### Custom Skills

Create `.lyra/skills/custom_skill.json`:

```json
{
  "name": "custom_skill",
  "description": "Custom skill description",
  "trigger": "when to use this skill",
  "implementation": "path/to/implementation.py",
  "verification": {
    "syntax": true,
    "semantics": true,
    "safety": true
  },
  "quality_score": 0.85
}
```

### Custom Hooks

Create `.lyra/hooks/pre_tool.py`:

```python
def pre_tool_hook(tool_name: str, args: dict) -> dict:
    """Hook called before tool execution."""
    # Modify args or add validation
    return args
```

---

## Configuration Precedence

Configuration is loaded in this order (later overrides earlier):

1. **Default values** - Built-in defaults
2. **Global config** - `~/.lyra/config.json`
3. **Project config** - `.lyra/config.json`
4. **Environment variables** - `LYRA_*`
5. **Command-line flags** - `--flag`

---

## Configuration Examples

### Example 1: Research-Focused Setup

```json
{
  "model": {
    "default": "claude-opus-4-7"
  },
  "research": {
    "sources": ["arxiv", "semantic_scholar", "github", "openreview"],
    "min_quality": 0.8,
    "max_results": 100,
    "citation_depth": 5
  },
  "memory": {
    "hot_tier_size": 200,
    "warm_tier_size": 1000
  }
}
```

### Example 2: Cost-Optimized Setup

```json
{
  "model": {
    "default": "claude-haiku-4-5",
    "budget_cap_usd": 1.0
  },
  "research": {
    "sources": ["arxiv"],
    "max_results": 20
  },
  "memory": {
    "hot_tier_size": 50,
    "warm_tier_size": 200
  }
}
```

### Example 3: Evolution-Focused Setup

```json
{
  "model": {
    "default": "claude-opus-4-7"
  },
  "evolution": {
    "enabled": true,
    "verification_required": true,
    "sandbox_enabled": true
  },
  "skills": {
    "auto_extract": true,
    "quality_threshold": 0.9
  },
  "learning": {
    "voyager_enabled": true,
    "reflexion_enabled": true
  }
}
```

---

## Troubleshooting Configuration

### Issue: Configuration not loading

**Solution:**
```bash
# Check config file syntax
cat .lyra/config.json | jq .

# Verify file permissions
ls -la .lyra/config.json

# Check environment variables
env | grep LYRA
```

### Issue: API key not found

**Solution:**
```bash
# Set in environment
export ANTHROPIC_API_KEY="your-key"

# Or add to config
echo '{"api_keys": {"anthropic": "your-key"}}' > .lyra/config.json
```

### Issue: Budget exceeded

**Solution:**
```bash
# Check current spending
lyra --budget-status

# Increase budget
lyra --budget 20.00

# Or disable budget
lyra --no-budget
```

---

## Configuration Validation

Validate your configuration:

```bash
# Check configuration
lyra config validate

# Show current configuration
lyra config show

# Reset to defaults
lyra config reset
```

---

## Next Steps

- **[MCP Integration](mcp-integration.md)** - Connect external tools
- **[Skills Guide](skills.md)** - Create custom skills
- **[Memory System](memory-system.md)** - Configure memory
- **[Hooks Guide](hooks.md)** - Create custom hooks

---

**Last Updated:** 2026-05-18
