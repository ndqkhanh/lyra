# Model Selection Guide

## Interactive Model Picker

The easiest way to switch models is using the interactive picker:

```bash
# In Lyra REPL, type:
/model
```

This opens a **full-screen interactive picker** showing:
- All available models with their full names
- Provider information
- Model capabilities
- Current selection highlighted

**Use arrow keys** to navigate and **Enter** to select.

---

## Available Models

### Anthropic (Claude)

```bash
/model claude-opus-4.7      # Most capable, best for complex tasks
/model claude-opus-4.6      # Previous Opus version
/model claude-opus-4.5      # Stable Opus version
/model claude-sonnet-4.6    # Balanced performance/speed
/model claude-sonnet-4.5    # Previous Sonnet version
/model claude-haiku-4.5     # Fastest, most cost-effective
```

### OpenAI

```bash
/model gpt-5                # Latest GPT-5
/model gpt-4o               # GPT-4 Optimized
/model gpt-4o-mini          # Smaller, faster GPT-4o
/model o1                   # Reasoning model
/model o1-mini              # Smaller reasoning model
```

### DeepSeek

```bash
/model deepseek-chat        # DeepSeek V4 (default)
/model deepseek-reasoner    # DeepSeek R1 (reasoning)
```

### Google (Gemini)

```bash
/model gemini-2.5-pro       # Most capable Gemini
/model gemini-2.5-flash     # Fast Gemini
/model gemini-2.0-flash     # Previous Flash version
```

### xAI (Grok)

```bash
/model grok-4               # Latest Grok
/model grok-3               # Previous version
```

### Other Providers

```bash
# Groq
/model llama-3.3-70b        # Llama 3.3 70B on Groq
/model mixtral-8x7b         # Mixtral on Groq

# Cerebras
/model llama-3.3-70b-cerebras

# Mistral
/model mistral-large
/model mistral-medium

# Qwen
/model qwen-max
/model qwen-plus

# Ollama (local)
/model llama3.3
/model qwen2.5
/model deepseek-r1
```

---

## Model Aliases (Shortcuts)

For convenience, Lyra supports short aliases:

| Alias | Full Model Name |
|-------|----------------|
| `opus` | `claude-opus-4.7` |
| `sonnet` | `claude-sonnet-4.6` |
| `haiku` | `claude-haiku-4.5` |
| `gpt5` | `gpt-5` |
| `o1` | `o1` |
| `deepseek` | `deepseek-chat` |
| `gemini` | `gemini-2.5-pro` |
| `grok` | `grok-4` |

**Example:**
```bash
/model opus    # Same as /model claude-opus-4.7
```

**⚠️ Recommendation:** Use full model names for clarity, especially in scripts or documentation.

---

## Listing Models

### List all available models
```bash
/model list
```

**Output shows:**
- ✅ Models with credentials configured
- ❌ Models requiring API keys
- Provider information
- Model capabilities

### Check current model
```bash
# Your current model is shown in the prompt
lyra (claude-opus-4.7) >
```

---

## Model Selection Tips

### For Different Tasks

**Complex reasoning & architecture:**
```bash
/model claude-opus-4.7
/model o1
```

**Balanced performance:**
```bash
/model claude-sonnet-4.6
/model gpt-4o
/model gemini-2.5-pro
```

**Fast iteration & cost-effective:**
```bash
/model claude-haiku-4.5
/model gpt-4o-mini
/model deepseek-chat
```

**Local/offline work:**
```bash
/model llama3.3          # Requires Ollama running
/model qwen2.5
```

---

## Auto-Cascade

Let Lyra automatically select the best available model:

```bash
lyra run --llm auto
```

**Priority order:**
1. Ollama (if local-first enabled)
2. DeepSeek (cost-optimized)
3. Anthropic Claude
4. OpenAI GPT
5. Google Gemini
6. xAI Grok
7. Others (Groq, Cerebras, Mistral, etc.)

---

## Keyboard Shortcuts

- **Alt+P** (Mac) / **Alt+P** (Windows/Linux) - Open model picker
- **Tab** - Autocomplete model names
- **↑/↓** - Navigate model list
- **Enter** - Select model

---

## Configuration

### Set default model in settings

**`~/.lyra/settings.json`:**
```json
{
  "config_version": 2,
  "default_provider": "anthropic",
  "default_model": "claude-opus-4.7"
}
```

### Per-project model

**`<project>/.lyra/settings.json`:**
```json
{
  "default_model": "claude-sonnet-4.6"
}
```

---

## Troubleshooting

**Model not found:**
```bash
# Check available models
/model list

# Verify API key is set
echo $ANTHROPIC_API_KEY
```

**No models available:**
```bash
# Set at least one API key
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="sk-..."
```

**Model switch failed:**
- Verify API key is valid
- Check internet connection
- Try `/model list` to see available models
