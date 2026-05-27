# 🔑 Lyra API Keys Setup

## How to Set API Keys

Lyra supports **multiple LLM providers** and automatically picks the best one available!

### Quick Setup

```bash
# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI (GPT)
export OPENAI_API_KEY="sk-..."

# Or add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

### Supported Providers (Auto-Detection Order)

Lyra checks these in order and uses the first one configured:

1. **DeepSeek** - `DEEPSEEK_API_KEY` (cheapest, great for coding)
2. **Anthropic** - `ANTHROPIC_API_KEY` (Claude Sonnet/Opus)
3. **OpenAI** - `OPENAI_API_KEY` (GPT-4/GPT-5)
4. **Gemini** - `GEMINI_API_KEY` or `GOOGLE_API_KEY`
5. **xAI (Grok)** - `XAI_API_KEY` or `GROK_API_KEY`
6. **Groq** - `GROQ_API_KEY`
7. **Cerebras** - `CEREBRAS_API_KEY`
8. **Mistral** - `MISTRAL_API_KEY`
9. **Qwen** - `DASHSCOPE_API_KEY` or `QWEN_API_KEY`
10. **OpenRouter** - `OPENROUTER_API_KEY`
11. **LM Studio** (local) - Auto-detects `:1234/v1/models`
12. **Ollama** (local) - Auto-detects `:11434/api/tags`

### Usage

```bash
# Auto mode (uses first available key)
lyra

# Force specific provider
lyra --llm anthropic
lyra --llm openai
lyra --llm deepseek
lyra --llm ollama
```

### Example: Anthropic Setup

```bash
# 1. Get your API key from https://console.anthropic.com/
# 2. Set the environment variable
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# 3. Run Lyra
lyra

# You'll see:
# Model: claude-sonnet-4-6  (or whatever model is configured)
```

### Example: OpenAI Setup

```bash
# 1. Get your API key from https://platform.openai.com/
# 2. Set the environment variable
export OPENAI_API_KEY="sk-your-key-here"

# 3. Run Lyra
lyra --llm openai
```

### Example: Local Ollama

```bash
# 1. Install Ollama: https://ollama.ai/
# 2. Pull a model
ollama pull llama3

# 3. Run Lyra (auto-detects Ollama)
lyra --llm ollama
```

### Permanent Setup

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Anthropic (recommended for best quality)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI (alternative)
export OPENAI_API_KEY="sk-..."

# DeepSeek (cheapest, great for coding)
export DEEPSEEK_API_KEY="sk-..."
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### Check Configuration

```bash
# Run Lyra and check which model it picked
lyra

# Or use the doctor command
lyra doctor
```

### Troubleshooting

**"No provider configured" error?**
- Make sure you've set at least one API key
- Check the key is exported: `echo $ANTHROPIC_API_KEY`
- Restart your terminal after setting the key

**Want to use a specific model?**
```bash
lyra --llm anthropic --model claude-opus-4
lyra --llm openai --model gpt-4
```

---

## Multi-Agent Features (Coming Soon)

The features you mentioned from OpenAgentd will be integrated:

1. ✅ **Multi-agent orchestration** - Lead agent + Executor/Researcher/Writer
2. ✅ **Local-first & Tool-use** - File system, shell, web fetch
3. ⏳ **Coding Mode** - Diff review, split view (Phase 2)
4. ✅ **Extensible** - MCP, plugins, multiple providers
5. ⏳ **Split View** - Multiple agents in parallel (Phase 3)

**Current Status**: Phase 1 Complete (UI + Infrastructure)  
**Next**: Phase 2 (Agent Loop Integration)

---

**Just set your API key and run `lyra`!** 🚀
