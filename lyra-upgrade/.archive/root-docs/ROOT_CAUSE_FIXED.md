# 🎉 ROOT CAUSE FOUND AND FIXED!

## 🔴 The Bug

**Location:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/packages/lyra-cli/src/lyra_cli/ui_server.py` line 165

**Problem:** The UI server was creating `ChatRequest` WITHOUT a `system_prompt`:

```python
request = ChatRequest(
    prompt=prompt,
    session_id=session_id,
    model=model,
    # ❌ Missing: system_prompt
)
```

This caused the client code to skip adding the system message (line 294 in `client.py`):

```python
if req.system_prompt:  # ❌ This was False!
    msgs.append(Message.system(req.system_prompt))
```

## ✅ The Fix

Added system prompt to the ChatRequest:

```python
# CRITICAL FIX: Add system prompt with English instruction
system_prompt = (
    "You are Lyra, a CLI-native coding assistant. ALWAYS respond in English "
    "unless the user explicitly requests a different language."
)

request = ChatRequest(
    prompt=prompt,
    session_id=session_id,
    model=model,
    system_prompt=system_prompt,  # ✅ Now included!
)
```

## 🎯 Test Now!

Run in your terminal:
```bash
pkill -f lyra && lyra
```

Send "Hello" - it should now respond in **ENGLISH**! 🎉

## 📊 What Changed

Before:
- Messages sent to API: `[{role: "user", content: "Hello"}]`
- DeepSeek responded in Chinese (no instruction)

After:
- Messages sent to API: `[{role: "system", content: "...ALWAYS respond in English..."}, {role: "user", content: "Hello"}]`
- DeepSeek will respond in English! ✅

## 🔍 Why This Happened

The interactive session code (session.py) had the system prompt, but the UI server path (ui_server.py → client.py) was a separate code path that bypassed it!

**We found it!** 🎯
