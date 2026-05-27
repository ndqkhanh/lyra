# 🔍 Lyra Debug Guide

## What We Added

**Debug logging system** to trace every LLM API call in real-time.

### Files Modified:

1. **`debug_logger.py`** (NEW) - Core logging infrastructure
2. **`providers/openai_compatible.py`** - Logs DeepSeek/OpenAI/etc calls
3. **`providers/anthropic.py`** - Logs Anthropic/Claude calls
4. **`cli/research_pipeline.py`** - Logs research pipeline calls

### Log Location:

```
~/.lyra/logs/lyra_debug_YYYYMMDD_HHMMSS.log
```

## How to Use

### Step 1: Kill Old Processes

```bash
pkill -f lyra
```

### Step 2: Start Lyra

```bash
# With mock (no API key needed)
lyra --llm mock

# With real API
lyra --llm anthropic  # or deepseek, openai, etc
```

### Step 3: Send a Message

In Lyra:
```
❯ Hello, test message
```

### Step 4: Check the Logs

```bash
# Find the latest log
ls -lt ~/.lyra/logs/ | head -5

# View the log
tail -f ~/.lyra/logs/lyra_debug_*.log

# Or open in editor
code ~/.lyra/logs/lyra_debug_*.log
```

## What You'll See in Logs

### Example Log Output:

```
2026-05-25 09:15:23 | INFO     | lyra_debug | 🔵 OpenAI-compatible API call | Provider: deepseek | Model: deepseek-chat | Prompt: Hello, test message...
2026-05-25 09:15:24 | INFO     | lyra_debug | === API CALL START ===
2026-05-25 09:15:24 | INFO     | lyra_debug | Provider: deepseek
2026-05-25 09:15:24 | INFO     | lyra_debug | Model: deepseek-chat
2026-05-25 09:15:24 | INFO     | lyra_debug | Prompt length: 18 chars
2026-05-25 09:15:24 | INFO     | lyra_debug | Prompt preview: Hello, test message...
2026-05-25 09:15:25 | INFO     | lyra_debug | === API RESPONSE START ===
2026-05-25 09:15:25 | INFO     | lyra_debug | Response length: 156 chars
2026-05-25 09:15:25 | INFO     | lyra_debug | Response preview: Hello! How can I help you today?...
```

## Troubleshooting with Logs

### Issue: Duplicated Responses

**Check logs for:**
- How many API calls are made for one message
- If the same response appears twice

**Expected:** 1 API call per message
**If you see:** 2+ API calls → Bug in message handling

### Issue: Chinese Responses

**Check logs for:**
- The system prompt sent to the API
- Look for "ALWAYS respond in English"

**Expected:** System prompt contains "ALWAYS respond in English"
**If missing:** Python fix not loaded

### Issue: Wrong Model (DeepSeek instead of Claude)

**Check logs for:**
- Which provider is being called
- The model name in the API call

**Expected:** `Provider: anthropic | Model: claude-opus-4.7`
**If you see:** `Provider: deepseek` → API key configuration issue

### Issue: Not Responding

**Check logs for:**
- Any error messages
- If API calls are being made at all

**Expected:** API call logged for every message
**If missing:** Connection or configuration issue

## Quick Debug Commands

```bash
# Watch logs in real-time
tail -f ~/.lyra/logs/lyra_debug_*.log

# Search for errors
grep -i error ~/.lyra/logs/lyra_debug_*.log

# Count API calls
grep "API CALL START" ~/.lyra/logs/lyra_debug_*.log | wc -l

# See which providers were used
grep "Provider:" ~/.lyra/logs/lyra_debug_*.log | sort | uniq -c

# Check for English instruction
grep "ALWAYS respond in English" ~/.lyra/logs/lyra_debug_*.log
```

## Understanding the Logs

### Log Levels:

- **INFO** - Normal operation (API calls, responses)
- **WARNING** - Potential issues (fallbacks, retries)
- **ERROR** - Actual errors (failed API calls, exceptions)

### Key Markers:

- 🔵 **OpenAI-compatible** - DeepSeek, OpenAI, Groq, etc.
- 🟣 **Anthropic** - Claude models
- === **API CALL START** === - Beginning of API request
- === **API RESPONSE START** === - Beginning of API response

## Next Steps

1. **Start Lyra with logging enabled** ✅ (already done)
2. **Send a test message**
3. **Check the logs** to see what's actually happening
4. **Share the log file** if you need help debugging

The logs will tell us:
- ✅ Which API is being called
- ✅ What prompt is being sent
- ✅ What response is received
- ✅ Any errors that occur

This is **much better** than guessing! 🎯
