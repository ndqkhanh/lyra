# 🚀 Quick Start Guide

## The Problem We Found

Your `~/.zshrc` had an **expired OpenAI API key** that was causing all the issues:
- ❌ OpenAI quota exceeded (HTTP 429 error)
- ❌ Lyra trying to use OpenAI instead of mock/other providers
- ❌ `--llm mock` flag being ignored

## ✅ What We Fixed

1. **Removed OPENAI_API_KEY from ~/.zshrc** (backed up to ~/.zshrc.backup)
2. **Added debug logging** to trace all API calls
3. **Created clean start script**

## 🎯 How to Start Lyra Now

### Option 1: Use the Clean Start Script (Recommended)

```bash
./start_lyra_clean.sh
```

This script:
- Kills old Lyra processes
- Unsets OPENAI_API_KEY
- Shows available API keys
- Starts Lyra in mock mode

### Option 2: Start Fresh Terminal

```bash
# Open a NEW terminal window (to get clean environment)
# Then run:
lyra --llm mock
```

### Option 3: Manual Start

```bash
# In current terminal:
unset OPENAI_API_KEY
pkill -f lyra
lyra --llm mock
```

## 📊 Check Debug Logs

After starting Lyra and sending a message:

```bash
# View logs
tail -f ~/.lyra/logs/lyra_debug_*.log

# Or list all logs
ls -lt ~/.lyra/logs/
```

## 🔍 What to Expect

### With Mock Mode:
```
Provider: mock
Model: mock
Response: [Canned mock response]
```

### With Real API (if you add keys):
```bash
# Add Anthropic key
export ANTHROPIC_API_KEY="your-key-here"

# Or DeepSeek key
export DEEPSEEK_API_KEY="your-key-here"

# Then start
./start_lyra_clean.sh
```

## 🎉 Success Criteria

After starting with the clean script, you should see:
- ✅ Lyra starts without errors
- ✅ Mock responses work (or real API if you added keys)
- ✅ Debug logs show the correct provider
- ✅ No HTTP 429 errors

## 🆘 If Still Having Issues

1. **Check the debug logs:**
   ```bash
   cat ~/.lyra/logs/lyra_debug_*.log
   ```

2. **Verify no OPENAI_API_KEY:**
   ```bash
   env | grep OPENAI_API_KEY
   # Should return nothing
   ```

3. **Try a completely fresh terminal:**
   - Close current terminal
   - Open new terminal
   - Run: `./start_lyra_clean.sh`

## 📝 Summary

**Root cause:** Expired OpenAI API key in ~/.zshrc
**Solution:** Removed the key, use clean start script
**Next step:** Run `./start_lyra_clean.sh` and test!
