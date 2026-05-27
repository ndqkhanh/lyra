# Manual Fix Guide for Lyra UI Issues

## Fix 1: Duplicated Response Rendering

### File: `packages/ui-core/src/state/store.ts`

**Location**: Line 208-234

**Change**: Add `session.previewMessages = []` after popping the message

**Before**:
```typescript
commitStreamingMessage: (sessionId) => {
  set((state) => {
    const session = state.sessions.get(sessionId)
    if (session && session.previewMessages.length > 0) {
      const msg = session.previewMessages.pop()!
      const committedMsg: AssistantMessage = {
        ...msg as AssistantMessage,
        streaming: false
      }
      session.messages.push(committedMsg)
      session.isStreaming = false

      // Update message count
      const metrics = state.metrics.get(sessionId)
      if (metrics) {
        metrics.messageCount = session.messages.length
      }
    }
  })

  // Emit stream end event
  observability.emit({
    type: 'stream_end',
    timestamp: Date.now(),
    sessionId
  })
},
```

**After**:
```typescript
commitStreamingMessage: (sessionId) => {
  set((state) => {
    const session = state.sessions.get(sessionId)
    if (session && session.previewMessages.length > 0) {
      const msg = session.previewMessages.pop()!

      // CRITICAL FIX: Clear ALL preview messages to prevent duplication
      // This ensures the committed message doesn't appear in both
      // staticItems (committed) and liveItems (preview) arrays
      session.previewMessages = []

      const committedMsg: AssistantMessage = {
        ...msg as AssistantMessage,
        streaming: false
      }
      session.messages.push(committedMsg)
      session.isStreaming = false

      // Update message count
      const metrics = state.metrics.get(sessionId)
      if (metrics) {
        metrics.messageCount = session.messages.length
      }
    }
  })

  // Emit stream end event
  observability.emit({
    type: 'stream_end',
    timestamp: Date.now(),
    sessionId
  })
},
```

**What Changed**: Added one line after `pop()`:
```typescript
session.previewMessages = []
```

---

## Fix 2: Force English Responses

### File: `packages/lyra-cli/src/lyra_cli/interactive/session.py`

**Location**: Line 1870-1892

**Status**: ✅ Already applied in previous edit

**Change**: Added "ALWAYS respond in English" to system prompt

**Before**:
```python
_LYRA_MODE_PREAMBLE = (
    "You are Lyra, a CLI-native coding assistant. You operate in one "
    "of four modes:\n"
    # ... rest of prompt
)
```

**After**:
```python
_LYRA_MODE_PREAMBLE = (
    "You are Lyra, a CLI-native coding assistant. ALWAYS respond in English "
    "unless the user explicitly requests a different language. You operate in one "
    "of four modes:\n"
    # ... rest of prompt
)
```

**What Changed**: Added explicit language instruction at the beginning of the preamble.

---

## Applying the Fixes

### Option 1: Automatic (Already Done)
The fixes have been applied automatically via the Edit tool.

### Option 2: Manual Application

If you need to apply manually:

1. **Fix Duplication**:
   ```bash
   cd packages/ui-core/src/state
   # Edit store.ts line 212, add after the pop() line:
   # session.previewMessages = []
   ```

2. **Fix Language** (already done):
   ```bash
   cd packages/lyra-cli/src/lyra_cli/interactive
   # Edit session.py line 1872, modify the preamble string
   ```

3. **Rebuild UI Core**:
   ```bash
   cd packages/ui-core
   npm run build
   ```

4. **Restart Lyra**:
   ```bash
   pkill -f lyra
   lyra
   ```

---

## Verification Commands

```bash
# 1. Check if store.ts was modified
grep -A5 "previewMessages.pop" packages/ui-core/src/state/store.ts

# 2. Check if session.py was modified
grep "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py

# 3. Rebuild and restart
cd packages/ui-core && npm run build
pkill -f lyra && lyra
```

---

## Rollback Instructions

If you need to revert:

### Rollback Fix 1 (Duplication):
```bash
cd packages/ui-core/src/state
# Remove the line: session.previewMessages = []
# Keep only: const msg = session.previewMessages.pop()!
```

### Rollback Fix 2 (Language):
```bash
cd packages/lyra-cli/src/lyra_cli/interactive
# Remove "ALWAYS respond in English unless the user explicitly requests a different language."
# Restore original: "You are Lyra, a CLI-native coding assistant. You operate in one"
```

---

## Notes

- **Fix 1** requires rebuilding `ui-core` package
- **Fix 2** requires restarting the Lyra server
- Both fixes are backward compatible
- No database migrations needed
- No configuration changes required

