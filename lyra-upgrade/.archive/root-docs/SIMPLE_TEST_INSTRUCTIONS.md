# 🎯 SIMPLE TEST INSTRUCTIONS

## Just Do This:

### Step 1: Open a NEW terminal window

### Step 2: Run these commands:

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
unset OPENAI_API_KEY
pkill -f lyra
lyra
```

### Step 3: In Lyra, type:

```
Hello
```

### Step 4: Exit Lyra (Ctrl+C)

### Step 5: Check the logs:

```bash
cat ~/.lyra/logs/lyra_debug_*.log
```

## What to Look For in the Logs:

### ✅ Good Sign:
```
Full prompt (first 1000 chars): You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
Full response: Hello! How can I help you today?
```

### ❌ Bad Sign (DeepSeek ignoring instruction):
```
Full prompt (first 1000 chars): You are Lyra, a CLI-native coding assistant. ALWAYS respond in English...
Full response: 你好！有什么可以帮你的吗？😊
```

### ❌ Bad Sign (No system prompt):
```
Full prompt (first 1000 chars): Hello
Full response: 你好！
```

---

## That's It!

Just run those commands in a **NEW terminal window** and share the log output.

The logs will tell us **exactly** what's happening! 🎯
