# 🔍 Enhanced Debug Logging - What's New

## ✅ Added More Debug Information

### 1. **Full Prompt Logging** (First 1000 chars)
```
Full prompt (first 1000 chars): You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
```

### 2. **Full Response Logging**
```
Full response: Hello! How can I help you today?
```

### 3. **Extended Previews**
- Prompt preview: 200 → 500 chars
- Response preview: 200 → 500 chars

## 🎯 What to Look For

After running `./enhanced_debug_test.sh` and sending "Hello", check the logs:

```bash
cat ~/.lyra/logs/lyra_debug_*.log
```

### Expected Log Output:

```
=== API CALL START ===
Provider: deepseek (or anthropic)
Model: deepseek-chat (or claude-opus-4.7)
Prompt length: XXX chars
Prompt preview: You are Lyra...
Full prompt (first 1000 chars): You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
=== API CALL END ===

=== API RESPONSE START ===
Provider: deepseek
Model: deepseek-chat
Response length: XXX chars
Response preview: Hello! How can I help you today?
Full response: Hello! How can I help you today?
=== API RESPONSE END ===
```

## 🔍 Key Things to Check:

1. **Does the prompt include "ALWAYS respond in English"?**
   - ✅ YES → English fix is working
   - ❌ NO → Fix not installed

2. **What's the full response?**
   - ✅ English → Working correctly
   - ❌ Chinese → Provider ignoring instruction

3. **Which provider is being used?**
   - DeepSeek → Using DEEPSEEK_API_KEY
   - Anthropic → Using ANTHROPIC_API_KEY

## 🚀 Run the Test

```bash
./enhanced_debug_test.sh
```

Then:
1. Send: "Hello"
2. Wait for response
3. Check logs: `cat ~/.lyra/logs/lyra_debug_*.log`

## 📊 What This Will Tell Us

The enhanced logs will reveal:
- ✅ If the English instruction is in the prompt
- ✅ The exact response from the API
- ✅ Which provider/model is being used
- ✅ If the response is duplicated at API level or UI level

This will **definitively** show us where the problem is!
