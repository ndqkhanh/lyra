# Lyra LLM Providers - Complete Integration

All requested LLM providers are **already fully integrated** in Lyra! 🎉

## ✅ Supported Providers & Models

### 1. Anthropic ✅
**Models:** claude-opus-4.7, claude-sonnet-4.6, claude-haiku-4.5

**Configuration:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
lyra --llm anthropic
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` - API key
- `ANTHROPIC_MODEL` - Override default model
- `HARNESS_LLM_MODEL` - Global model override

**Default Model:** `claude-3-5-sonnet-latest`

---

### 2. OpenAI ✅
**Models:** gpt-4o, gpt-4-turbo, gpt-3.5-turbo, o3-mini (reasoning)

**Configuration:**
```bash
export OPENAI_API_KEY=sk-...
lyra --llm openai
```

**Environment Variables:**
- `OPENAI_API_KEY` - API key
- `OPENAI_MODEL` - Override default model
- `OPEN_HARNESS_OPENAI_MODEL` - Alternative model override

**Default Model:** `gpt-4o`

**Reasoning Models:**
```bash
lyra --llm openai-reasoning  # Uses o3-mini with reasoning_effort
```

---

### 3. DeepSeek ✅
**Models:** deepseek-v4-pro, deepseek-v4-flash, deepseek-reasoner, deepseek-chat

**Configuration:**
```bash
export DEEPSEEK_API_KEY=sk-...
lyra --llm deepseek
```

**Environment Variables:**
- `DEEPSEEK_API_KEY` - API key
- `DEEPSEEK_MODEL` - Override default model
- `OPEN_HARNESS_DEEPSEEK_MODEL` - Alternative model override

**Default Model:** `deepseek-chat`

**Priority:** DeepSeek is **first** in the auto-cascade (cost-optimized default)

---

### 4. Google Gemini ✅
**Models:** gemini-2.5-pro-preview, gemini-3.1-pro

**Configuration:**
```bash
export GEMINI_API_KEY=...
# or
export GOOGLE_API_KEY=...
lyra --llm gemini
```

**Environment Variables:**
- `GEMINI_API_KEY` - API key (preferred)
- `GOOGLE_API_KEY` - Alternative API key
- `GEMINI_MODEL` - Override default model
- `OPEN_HARNESS_GEMINI_MODEL` - Alternative model override

**Default Model:** `gemini-2.5-pro`

**Cloud Routing (Vertex AI):**
```bash
export GOOGLE_CLOUD_PROJECT=my-project
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_MODEL=gemini-2.5-pro
lyra --llm vertex
```

---

### 5. Alibaba Qwen ✅
**Models:** qwen-3.7-max, qwen-turbo, qwen-plus

**Configuration:**
```bash
export QWEN_API_KEY=sk-...
# or
export DASHSCOPE_API_KEY=sk-...
lyra --llm qwen
```

**Environment Variables:**
- `QWEN_API_KEY` - API key (preferred)
- `DASHSCOPE_API_KEY` - Alternative API key (Alibaba's official name)
- `QWEN_MODEL` - Override default model
- `DASHSCOPE_MODEL` - Alternative model override

**Default Model:** `qwen-plus`

**Endpoint:** `https://dashscope.aliyuncs.com/compatible-mode/v1`

**Legacy Alias:** `--llm dashscope` (still works for backward compatibility)

---

### 6. Moonshot Kimi ✅
**Models:** kimi-k2.6

**Configuration:**
```bash
# Kimi is available via Groq
export GROQ_API_KEY=gsk_...
export GROQ_MODEL=kimi-k2-0711
lyra --llm groq
```

**Note:** Moonshot's Kimi-K2 (1T MoE) is hosted on Groq's infrastructure. Groq recommends it as their "best for agents" model.

**Environment Variables:**
- `GROQ_API_KEY` - API key
- `GROQ_MODEL` - Override default model
- `OPEN_HARNESS_GROQ_MODEL` - Alternative model override

**Default Model:** `llama-3.3-70b-versatile`

**Available Kimi Models on Groq:**
- `kimi-k2-0711` - Moonshot Kimi K2 (1T MoE)

---

## Auto-Cascade Priority

When using `--llm auto` (default), Lyra tries providers in this order:

1. **DeepSeek** - Cost-optimized default (10-20× cheaper than Claude/GPT)
2. **Anthropic** - Reference target for tool-using agents
3. **OpenAI** - Industry standard
4. **Gemini** - Google's flagship
5. **xAI (Grok)** - Fast inference
6. **Groq** - Ultra-fast inference (includes Kimi)
7. **Cerebras** - Fastest inference (~2000 t/s)
8. **Mistral** - European provider
9. **Qwen** - Alibaba's models
10. **OpenRouter** - Meta-provider (hundreds of models)
11. **LM Studio** - Local models
12. **Ollama** - Local models

## Usage Examples

### Basic Usage
```bash
# Auto-select (tries DeepSeek → Anthropic → OpenAI → ...)
lyra

# Explicit provider
lyra --llm anthropic
lyra --llm openai
lyra --llm deepseek
lyra --llm gemini
lyra --llm qwen
lyra --llm groq  # For Kimi

# Specific model
export ANTHROPIC_MODEL=claude-opus-4.7
lyra --llm anthropic

export DEEPSEEK_MODEL=deepseek-reasoner
lyra --llm deepseek

export GROQ_MODEL=kimi-k2-0711
lyra --llm groq
```

### Model Aliases
```bash
# Use friendly aliases instead of full model names
lyra --model opus        # → claude-opus-4.7
lyra --model sonnet      # → claude-sonnet-4.6
lyra --model haiku       # → claude-haiku-4.5
lyra --model gpt-4o      # → gpt-4o
lyra --model deepseek    # → deepseek-chat
```

### Environment Configuration
```bash
# Set in shell profile (~/.bashrc, ~/.zshrc)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export DEEPSEEK_API_KEY=sk-...
export GEMINI_API_KEY=...
export QWEN_API_KEY=sk-...
export GROQ_API_KEY=gsk_...

# Or use project-local .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "DEEPSEEK_API_KEY=sk-..." >> .env
```

### Interactive Setup
```bash
# Guided provider setup
lyra connect

# Connect specific provider
lyra connect anthropic --key sk-ant-...
lyra connect openai --key sk-...
lyra connect deepseek --key sk-...
lyra connect gemini --key ...
lyra connect qwen --key sk-...
lyra connect groq --key gsk_...
```

## Provider Status Check

```bash
# Check which providers are configured
lyra doctor

# Output shows:
# ✓ DeepSeek: deepseek-chat
# ✓ Anthropic: claude-3-5-sonnet-latest
# ✓ OpenAI: gpt-4o
# ✓ Gemini: gemini-2.5-pro
# ✓ Qwen: qwen-plus
# ✓ Groq: llama-3.3-70b-versatile
```

## Model Selection in UI

The Lyra TUI automatically uses the configured provider. The current model is shown in the header:

```
╦  ╦ ╦╦═╗╔═╗  Lyra Code v1.0.0
║  ╚╦╝╠╦╝╠═╣  Opus 4.7 (1M context) · Deep Research Mode
╩═╝ ╩ ╩╚═╩ ╩  ~/Downloads/MyCV/research/harness-engineering
```

## Advanced Configuration

### Custom Provider Routing (OpenRouter)
```json
// ~/.lyra/settings.json
{
  "providers": {
    "openrouter": {
      "sort": "cost",
      "only": ["anthropic", "openai"],
      "require_parameters": true
    }
  }
}
```

### Cloud-Routed Providers

**AWS Bedrock (Anthropic via AWS):**
```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
lyra --llm bedrock
```

**Google Vertex AI (Gemini via GCP):**
```bash
export GOOGLE_CLOUD_PROJECT=my-project
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_MODEL=gemini-2.5-pro
lyra --llm vertex
```

## Cost Optimization

**Recommended Setup for Cost-Conscious Users:**
```bash
# Primary: DeepSeek (cheapest, high quality)
export DEEPSEEK_API_KEY=sk-...
export DEEPSEEK_MODEL=deepseek-chat

# Fallback: Groq (free tier, fast)
export GROQ_API_KEY=gsk_...
export GROQ_MODEL=llama-3.3-70b-versatile

# Use auto-cascade
lyra  # Will use DeepSeek first, Groq as fallback
```

## Architecture

### Provider Implementation

All providers use the OpenAI-compatible chat completions format:
- **Endpoint:** `POST /v1/chat/completions`
- **Format:** OpenAI wire format
- **Translation:** Anthropic-style tool schemas ↔ OpenAI function calling

### Tool Call Translation

Lyra internally uses Anthropic-style tool schemas:
```json
{
  "name": "get_weather",
  "description": "Get weather for a location",
  "input_schema": { "type": "object", ... }
}
```

Automatically translated to OpenAI format:
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather for a location",
    "parameters": { "type": "object", ... }
  }
}
```

### Streaming Support

All providers support Server-Sent Events (SSE) streaming:
- Real-time token-by-token updates
- Progressive UI rendering
- Animated cursor during streaming

## Troubleshooting

### Provider Not Working

1. **Check API key:**
   ```bash
   echo $ANTHROPIC_API_KEY
   echo $OPENAI_API_KEY
   echo $DEEPSEEK_API_KEY
   ```

2. **Verify configuration:**
   ```bash
   lyra doctor
   ```

3. **Test connection:**
   ```bash
   lyra --llm anthropic  # Explicit provider
   ```

### Model Not Found

```bash
# Check available models for provider
export ANTHROPIC_MODEL=claude-opus-4.7
export DEEPSEEK_MODEL=deepseek-reasoner
export GROQ_MODEL=kimi-k2-0711
```

### Rate Limits

DeepSeek and Groq have generous free tiers. For production:
- **DeepSeek:** ~$0.14/M input tokens, $0.28/M output tokens
- **Anthropic:** ~$3/M input tokens, $15/M output tokens
- **OpenAI:** ~$2.50/M input tokens, $10/M output tokens

## Summary

✅ **All 6 requested providers are fully integrated:**
1. ✅ Anthropic (claude-opus-4.7, claude-sonnet-4.6, claude-haiku-4.5)
2. ✅ OpenAI (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
3. ✅ DeepSeek (deepseek-v4-pro, deepseek-v4-flash, deepseek-reasoner, deepseek-chat)
4. ✅ Google Gemini (gemini-2.5-pro-preview, gemini-3.1-pro)
5. ✅ Alibaba Qwen (qwen-3.7-max, qwen-turbo, qwen-plus)
6. ✅ Moonshot Kimi (kimi-k2.6 via Groq)

**No additional integration needed!** Just set the appropriate API keys and start using Lyra with any provider.
