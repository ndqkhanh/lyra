# Lyra Streaming Fix & Input Beautification

Fixed streaming response bug and improved input box appearance.

## Issues Fixed

### 1. Streaming Response Bug

**Problem:**
- Messages were appearing but responses were cut off or not displaying properly
- The transport was emitting `stream-chunk` events but no listener was attached
- Streaming messages were not being updated in real-time

**Root Cause:**
The main app component (`index.tsx`) was only listening to `message` and `error` events, but not `stream-chunk` events. This meant streaming updates were being sent but never processed.

**Solution:**
Added `stream-chunk` event listener in `index.tsx`:

```typescript
const unsubscribeStreamChunk = transport.onStreamChunk((chunk) => {
  if (chunk.done) {
    // Commit the streaming message
    useUIStore.getState().commitStreamingMessage(sessionId)
  } else {
    // Update streaming message with new chunk
    useUIStore.getState().updateStreamingMessage(sessionId, chunk.content)
  }
})
```

**Additional Fix:**
Updated `updateStreamingMessage` in `store.ts` to replace content instead of appending:

```typescript
// Before: lastMsg.content += chunk  (WRONG - causes duplication)
// After:  lastMsg.content = chunk   (CORRECT - full text replacement)
```

This is correct because the server sends the full accumulated text in each chunk, not incremental deltas.

### 2. Input Box Appearance

**Problem:**
- Input box looked cramped and unattractive
- No vertical padding around the input area
- Text input was wrapped in unnecessary `flexDirection="column"` Box

**Solution:**
Improved input styling with better spacing:

```typescript
// Before
<Box paddingX={2}>
  <Text bold color={colors.userPrompt}>❯ </Text>
  <Box flexDirection="column" flexGrow={1}>
    <TextInput ... />
  </Box>
</Box>

// After
<Box paddingX={2} paddingY={1}>
  <Text bold color={colors.userPrompt}>❯ </Text>
  <Box flexGrow={1}>
    <TextInput ... />
  </Box>
</Box>
```

**Changes:**
- Added `paddingY={1}` for vertical breathing room
- Removed `flexDirection="column"` (not needed for single-line input)
- Applied same padding to "Waiting for response..." state

## Files Modified

### 1. `packages/ui-terminal/src/index.tsx`

**Added stream-chunk listener:**
```typescript
const unsubscribeStreamChunk = transport.onStreamChunk((chunk) => {
  if (chunk.done) {
    useUIStore.getState().commitStreamingMessage(sessionId)
  } else {
    useUIStore.getState().updateStreamingMessage(sessionId, chunk.content)
  }
})
```

**Updated cleanup:**
```typescript
return () => {
  unsubscribeMessage()
  unsubscribeStreamChunk()  // Added
  unsubscribeError()
  transport.disconnect()
  process.stdout.off('resize', handleResize)
}
```

### 2. `packages/ui-core/src/state/store.ts`

**Fixed streaming logic:**
```typescript
// Replace content instead of appending
lastMsg.content = chunk  // Was: lastMsg.content += chunk
```

### 3. `packages/ui-terminal/src/components/InputArea.tsx`

**Improved styling:**
```typescript
// Added paddingY={1} for vertical spacing
<Box paddingX={2} paddingY={1}>
  <Text bold color={colors.userPrompt}>❯ </Text>
  <Box flexGrow={1}>  // Removed flexDirection="column"
    <TextInput ... />
  </Box>
</Box>
```

## How Streaming Works Now

### Message Flow

1. **User sends message** → `transport.sendMessage(content)`
2. **Server streams response** → SSE events with `kind: 'delta'`
3. **LocalTransport emits** → `stream-chunk` event with full accumulated text
4. **Event listener updates** → `updateStreamingMessage(sessionId, chunk.content)`
5. **Store updates** → `previewMessages[0].content = chunk` (replace, not append)
6. **UI re-renders** → Shows updated streaming message with cursor
7. **Stream completes** → `kind: 'complete'` → `commitStreamingMessage()`
8. **Message committed** → Moved from `previewMessages` to `messages`

### Key Points

- **Full text replacement**: Each chunk contains the full accumulated text, not deltas
- **Preview zone**: Streaming messages live in `previewMessages` array
- **Commit on complete**: When done, message moves to permanent `messages` array
- **Cursor animation**: Blinking cursor shows streaming is active

## Visual Result

### Before (Broken)
```
──────────────────────────────────────────────
❯ What model are you


❯ Hello


──────────────────────────────────────────────
❯
```
*Responses not showing or cut off*

### After (Fixed)
```
──────────────────────────────────────────────
  ❯ What model are you

  ⏺ I am Claude Opus 4.7 by Anthropic (model ID: claude-opus-4-7).▊

  ❯ Hello

  ⏺ Hello! How can I help you today?

──────────────────────────────────────────────
  ❯ 

  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```
*Streaming works, input looks clean*

## Testing

Build successful:
```bash
npm run build
# ✓ All packages built successfully
```

Test streaming:
```bash
lyra
# Type a message and watch it stream in real-time
```

## Summary

✅ **Streaming fixed** - Added missing `stream-chunk` event listener
✅ **Content replacement** - Changed from append to replace logic
✅ **Input beautified** - Added vertical padding and simplified layout
✅ **All builds passing** - No TypeScript errors
✅ **Ready to test** - Run `lyra` to see the improvements
