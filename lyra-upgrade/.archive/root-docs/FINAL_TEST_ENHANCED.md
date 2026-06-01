# 🎯 FINAL TEST - Enhanced Logging Active

## ✅ What's New

**Enhanced logging now shows:**
- Total number of messages
- Each message with role (system/user/assistant)
- First 500 chars of each message
- This will reveal if "ALWAYS respond in English" is in the system message!

## 🚀 Run This Test

### In a NEW terminal:

```bash
pkill -f lyra && lyra
```

### Send:
```
Hello
```

### Exit and check logs:
```bash
cat ~/.lyra/logs/lyra_debug_*.log
```

## 📊 What You'll See

### Expected Log Output:

```
🔵 OpenAI-compatible API call | Provider: deepseek | Model: deepseek-chat
Total messages: 2
Message 1 [system]: You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
Message 2 [user]: Hello
```

## 🔍 Key Things to Check:

### ✅ If you see this:
```
Message 1 [system]: You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
```
→ **System prompt IS being sent with English instruction**
→ **DeepSeek is ignoring it!**

### ❌ If you see this:
```
Total messages: 1
Message 1 [user]: Hello
```
→ **No system prompt being sent**
→ **Bug in message construction**

## 💡 What This Means

### Scenario A: System prompt sent, DeepSeek ignores
**Solution:** Switch to Anthropic
```bash
export DEEPSEEK_API_KEY=""
pkill -f lyra && lyra
```

### Scenario B: No system prompt sent
**Solution:** Bug in session.py message construction

---

**Run the test and share the full log output!** 🎯
