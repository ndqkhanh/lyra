# Lyra UI Fix Plan

## Issues Identified

### Issue 1: Duplicated Response (⏺ appears twice)
**Root Cause**: The streaming message is being committed twice to the store, causing it to appear in both `staticItems` and `liveItems` arrays.

**Location**: 
- `packages/ui-terminal/src/components/ConversationView.tsx` lines 47-58
- `packages/ui-core/src/state/store.ts` lines 208-223 (`commitStreamingMessage`)

**Problem Flow**:
1. Backend streams response → `updateStreamingMessage` adds to `previewMessages`
2. Stream completes → `commitStreamingMessage` moves from `previewMessages` to `messages`
3. **BUG**: The message is being committed twice OR not properly removed from preview
4. `partitionRenderItems` splits into `staticItems` (committed) and `liveItems` (preview)
5. Both arrays contain the same message → renders twice

### Issue 2: Responding in Chinese
**Root Cause**: System prompt change in `session.py` line 1872 requires server restart to take effect.

**Location**: 
- `packages/lyra-cli/src/lyra_cli/interactive/session.py` line 1872
- System prompt is loaded once at server startup and cached

## Fix Strategy

### Fix 1: Prevent Duplicate Rendering

**Option A: Fix at Store Level (Recommended)**
Ensure `commitStreamingMessage` properly clears preview before committing:

```typescript
// packages/ui-core/src/state/store.ts line 208
commitStreamingMessage: (sessionId) => {
  set((state) => {
    const session = state.sessions.get(sessionId)
    if (session && session.previewMessages.length > 0) {
      const msg = session.previewMessages.pop()!
      
      // CRITICAL: Clear ALL preview messages to prevent duplication
      session.previewMessages = []
      
      const committedMsg: AssistantMessage = {
        ...msg as AssistantMessage,
        streaming: false
      }
      session.messages.push(committedMsg)
      session.isStreaming = false
      
      // Update metrics...
    }
  })
}
```

**Option B: Fix at Render Level**
Add deduplication in `ConversationView.tsx`:

```typescript
// Filter out duplicates by message ID
const seenIds = new Set<string>()
const dedupedStatic = staticItems.filter(item => {
  if (seenIds.has(item.sourceMessageId)) return false
  seenIds.add(item.sourceMessageId)
  return true
})
const dedupedLive = liveItems.filter(item => {
  if (seenIds.has(item.sourceMessageId)) return false
  seenIds.add(item.sourceMessageId)
  return true
})
```

### Fix 2: Force English Responses

**Option A: Restart Server (Immediate)**
```bash
pkill -f "lyra.*server"
lyra
```

**Option B: Add Runtime Language Detection**
Add language detection to system prompt builder:

```python
# src/lyra_cli/interactive/session.py
def _get_user_language():
    """Detect user's preferred language from environment."""
    import locale
    lang = os.getenv('LANG', locale.getdefaultlocale()[0] or 'en_US')
    return 'English' if lang.startswith('en') else 'English'  # Force English

_LYRA_MODE_PREAMBLE = (
    f"You are Lyra, a CLI-native coding assistant. ALWAYS respond in {_get_user_language()} "
    "unless the user explicitly requests a different language. You operate in one "
    # ... rest of prompt
)
```

**Option C: Add Model Configuration**
Force Anthropic model in config:

```bash
cat > ~/.lyra/config.json << 'JSON'
{
  "bypassPermissions": false,
  "model": "anthropic",
  "defaultModel": "claude-opus-4.7",
  "language": "en"
}
JSON
```

## Implementation Steps

### Phase 1: Fix Duplication (High Priority)
1. ✅ Identify root cause in store
2. ⬜ Implement Option A (clear preview messages)
3. ⬜ Test with streaming responses
4. ⬜ Verify single render

### Phase 2: Fix Language (Medium Priority)
1. ✅ Verify system prompt change
2. ⬜ Restart Lyra server
3. ⬜ Test English responses
4. ⬜ Add runtime language config (optional)

### Phase 3: Verification
1. ⬜ Test full conversation flow
2. ⬜ Verify no regressions
3. ⬜ Update documentation

## Testing Checklist

- [ ] Single response renders once (not twice)
- [ ] Streaming works correctly
- [ ] Responses are in English
- [ ] Model identifies as Claude
- [ ] No console errors
- [ ] Performance is acceptable

## Files to Modify

1. `packages/ui-core/src/state/store.ts` (line 208-223)
2. `packages/lyra-cli/src/lyra_cli/interactive/session.py` (already modified)
3. `~/.lyra/config.json` (optional)

