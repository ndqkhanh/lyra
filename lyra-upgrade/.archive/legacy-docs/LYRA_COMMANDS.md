# ✅ Lyra Slash Commands - Complete Implementation

## All Commands Implemented

### Session & Context Management
- ✅ `/help` - Show all available commands
- ✅ `/status` - Show session status (model, tokens, cost, context)
- ✅ `/clear` - Clear conversation history
- ✅ `/exit` / `/quit` - Exit Lyra

### Model & Configuration
- ✅ `/model` - Show current model and list available models
- ✅ `/model <name>` - Switch to specific model (e.g., `/model claude-opus-4.7`)
- ✅ `/models` - Alias for `/model` (list all models)
- ✅ `/config` - Configure API keys and settings
- ✅ `/credentials` - Set API credentials for providers
- ✅ `/credentials <provider>` - Configure specific provider

### Information & Usage
- ✅ `/usage` - Show token usage and cost statistics
- ✅ `/cost` - View spending (alias for `/usage`)
- ✅ `/history` - Show command history info
- ✅ `/budget` - Show budget cap and remaining

### Development (Coming Soon)
- ⏳ `/diff` - Show git diff
- ⏳ `/commit` - Create git commit
- ⏳ `/pr` - Create pull request

## Usage Examples

### Model Switching

```bash
# Show current model and available models
> /model

Current Model: claude-sonnet-4-6

Available Models:

  Anthropic:
    claude-opus-4.7
    claude-opus-4
    claude-sonnet-4.6
    claude-sonnet-4
    claude-haiku-4.5
    claude-haiku-4

  Openai:
    gpt-5
    gpt-4-turbo
    gpt-4
    o1
    o1-mini

  Deepseek:
    deepseek-v4-pro
    deepseek-v4
    deepseek-coder

Usage: /model <model-name>
Example: /model claude-opus-4.7

# Switch to specific model
> /model claude-opus-4.7

Switching to: claude-opus-4.7 (anthropic)
✓ Model switched to claude-opus-4.7

# Switch to DeepSeek
> /model deepseek-v4-pro

Switching to: deepseek-v4-pro (deepseek)
No credentials found for deepseek.
Run: /credentials deepseek
```

### Credential Configuration

```bash
# Show configured providers
> /credentials

Configured Providers:

  ✓ anthropic (https://api.anthropic.com)
  ✓ openai (https://api.openai.com/v1)

Usage: /credentials <provider>
Example: /credentials anthropic

# Configure new provider
> /credentials anthropic

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

Paste your credentials:
(Input will be saved to ~/.lyra/credentials.json)
```

### JSON Configuration Examples

**Simple API Key:**
```bash
> /credentials anthropic
sk-ant-api03-your-key-here
```

**Gateway/Proxy:**
```json
{
  "api_key": "your-bearer-token",
  "base_url": "https://claude.aishopacc.com"
}
```

**Environment Variables Format:**
```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your-token",
    "ANTHROPIC_BASE_URL": "https://claude.aishopacc.com",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  }
}
```

### Usage Statistics

```bash
> /usage

Usage Statistics:
  Total Tokens: 12,345
  Total Cost: $0.1234
  Budget: $5.00
  Remaining: $4.8766 (2.5% used)
```

### Session Status

```bash
> /status

Session Status:
  Session: demo-session-001
  Model: claude-sonnet-4-6
  Tokens: 12,345
  Cost: $0.1234
  Context: 5,678 / 200,000
```

## Supported Providers

| Provider | Models | Default Base URL |
|----------|--------|------------------|
| **Anthropic** | claude-opus-4.7, claude-sonnet-4.6, claude-haiku-4.5 | https://api.anthropic.com |
| **OpenAI** | gpt-5, gpt-4-turbo, o1, o1-mini | https://api.openai.com/v1 |
| **DeepSeek** | deepseek-v4-pro, deepseek-v4, deepseek-coder | https://api.deepseek.com |
| **Ollama** | llama3, codellama, mistral, qwen | http://localhost:11434 |

## Credential Storage

Credentials are stored securely in:
- **File**: `~/.lyra/credentials.json`
- **Permissions**: `0600` (read/write for owner only)
- **Format**: JSON with provider keys

**Example `~/.lyra/credentials.json`:**
```json
{
  "anthropic": {
    "api_key": "sk-ant-...",
    "base_url": "https://api.anthropic.com"
  },
  "openai": {
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1"
  }
}
```

## Environment Variables (Alternative)

You can also use environment variables instead of `/credentials`:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_BASE_URL="https://api.anthropic.com"

# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
```

## Quick Start

```bash
# 1. Run Lyra
lyra

# 2. Configure credentials
> /credentials anthropic
sk-ant-your-key-here

# 3. Switch model
> /model claude-opus-4.7

# 4. Start chatting!
> Explain @README.md
```

---

**All essential Claude Code commands are now implemented!** 🎉
