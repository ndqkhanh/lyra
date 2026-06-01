# 🎯 CRITICAL FINDING

## The System Message is Missing!

The debug logs show:
```
Total messages: 1
Message 1 [user]: Hello...
```

But the code at line 2325 creates:
```python
messages = [Message.system(effective_system), *history, Message.user(line)]
```

This SHOULD create 2 messages (system + user), but only 1 message reaches the API!

## Possible Causes:

1. **`effective_system` is empty** - The system prompt is being cleared somewhere
2. **Message filtering** - Empty system messages are being filtered out
3. **Provider filtering** - The provider is removing system messages

## Next Steps:

I've added logging to show:
- Total messages constructed
- System prompt length
- System prompt preview

This will reveal if the system prompt is empty or being filtered.

## To Test:

Run in your **actual Mac Terminal** (not through Claude Code):
```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
pkill -f lyra
lyra
```

Send "Hello", then check:
```bash
cat ~/.lyra/logs/lyra_debug_*.log
```

Look for:
```
📝 Message construction | Total: X
System prompt length: X chars
System prompt preview: You are Lyra...
```

This will tell us if the system prompt is empty or being filtered!
