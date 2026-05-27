# Lyra API Key Configuration Guide

## Overview

Lyra CLI requires an Anthropic API key to function. This guide shows how to configure it.

## Option 1: Environment Variable (Recommended)

Set the `ANTHROPIC_API_KEY` environment variable:

```bash
# For current session
export ANTHROPIC_API_KEY="sk-ant-..."

# For permanent setup (add to ~/.zshrc or ~/.bashrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

## Option 2: .env File

Create a `.env` file in the project root:

```bash
# packages/lyra-cli/.env
ANTHROPIC_API_KEY=sk-ant-...
```

Then load it in your Python code:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Option 3: Lyra Config File

Create `~/.lyra/config.json`:

```json
{
  "api_key": "sk-ant-...",
  "model": "opus",
  "verbose": false
}
```

## Verification

Test that the API key is configured:

```bash
cd packages/lyra-cli
python3 -c "import os; print('API Key:', 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET')"
```

## Security Best Practices

1. **Never commit API keys to git**
   - Add `.env` to `.gitignore`
   - Use environment variables for CI/CD

2. **Rotate keys regularly**
   - Generate new keys periodically
   - Revoke old keys

3. **Use separate keys for dev/prod**
   - Development key for testing
   - Production key for live usage

## Getting an API Key

1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys section
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

## Troubleshooting

### "API key not found" error
- Check that `ANTHROPIC_API_KEY` is set: `echo $ANTHROPIC_API_KEY`
- Verify the key format (should start with `sk-ant-`)
- Restart your terminal after setting environment variables

### "Invalid API key" error
- Verify the key is correct (no extra spaces)
- Check that the key hasn't been revoked
- Generate a new key if needed

### Permission denied
- Check file permissions on config files
- Ensure `.env` file is readable

## Next Steps

After configuring the API key:

1. Run Lyra CLI: `lyra`
2. Test with a simple prompt: "Hello, can you help me?"
3. Verify UI rendering and responses
4. Run E2E tests: `pytest tests/e2e/`

---

**Note**: For the E2E tests in this project, you can extract the API key from `~/.claude/settings.json` if you're already using Claude Code.
