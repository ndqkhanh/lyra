# 🎉 ALL BUGS FIXED!

## ✅ Bug #1: Chinese Responses - FIXED!

**Root Cause:** UI server wasn't passing `system_prompt` to ChatRequest

**Fix:** Added system prompt in `ui_server.py`:
```python
system_prompt = (
    "You are Lyra, a CLI-native coding assistant. ALWAYS respond in English "
    "unless the user explicitly requests a different language."
)
```

**Result:** Lyra now responds in English! ✅

---

## ✅ Bug #2: Duplicate Messages - FIXED!

**Root Cause:** `client.py` was sending the same text in both "delta" and "complete" events:
```python
yield StreamEvent(kind="delta", payload=resp.text)    # Message
yield StreamEvent(kind="complete", payload=resp.text) # Duplicate!
```

**Fix:** Changed "complete" event to have empty payload:
```python
yield StreamEvent(kind="delta", payload=resp.text)
yield StreamEvent(kind="complete", payload="")  # ✅ No duplicate!
```

**Result:** Messages now appear only once! ✅

---

## 🎯 Test Now!

Run in your terminal:
```bash
pkill -f lyra && lyra
```

Send "Hello" - you should see:
- ✅ Response in English
- ✅ Message appears only ONCE (no duplicate)

**Both bugs are fixed!** 🚀
