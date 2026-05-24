# Lyra UI Terminal Echo Fix

## Problem

When typing messages in the Lyra TUI input box and pressing Enter, the messages were appearing **above** the header instead of in the conversation area (middle section). This created a confusing layout:

```
❯ He          ← Terminal echo (wrong place)
❯ hello       ← Terminal echo (wrong place)
❯ hello       ← Terminal echo (wrong place)

██╗  ██╗   ██╗██████╗  █████╗      Lyra v1.0.0
██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗     ← Header
███████║ ╚████╔╝ ██████╔╝███████║

────────────────────────────────────  ← Separator
                                      ← Empty conversation area (should show messages here)
────────────────────────────────────  ← Separator
┌─────────────────────────────────┐
│ ❯ Type your message...          │  ← Input box
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ Session: default  Messages: 4   │  ← Status bar
└─────────────────────────────────┘
```

## Root Cause

The issue was **terminal echo**. When you type in a terminal and press Enter, the terminal itself echoes your input to stdout **before** Ink (the React-for-CLI library) can capture and process it. This is standard terminal behavior.

The original code was:
```typescript
// Entry point
render(<App />)
```

This uses default stdin/stdout handling, which doesn't properly suppress terminal echo.

## Solution

Updated the render call to explicitly configure stdin/stdout and disable console patching:

```typescript
// Entry point
const { waitUntilExit } = render(<App />, {
  stdin: process.stdin,
  stdout: process.stdout,
  stderr: process.stderr,
  patchConsole: false
})

// Wait for exit
waitUntilExit().catch(console.error)
```

### What This Does:

1. **`stdin: process.stdin`** - Explicitly tells Ink to use process.stdin and handle it properly
2. **`stdout: process.stdout`** - Directs all output to stdout (Ink's rendering)
3. **`stderr: process.stderr`** - Keeps error output separate
4. **`patchConsole: false`** - Prevents Ink from patching console.log (avoids interference)
5. **`waitUntilExit()`** - Properly waits for the app to exit before closing

## Expected Result

After this fix, messages should appear in the correct location:

```
██╗  ██╗   ██╗██████╗  █████╗      Lyra v1.0.0
██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗     Opus 4.7 (1M context) · Deep Research Mode
███████║ ╚████╔╝ ██████╔╝███████║  ~/path/to/project

────────────────────────────────────────────────────────────────────

  ❯ Hello                           ← User message (correct place!)
  
  ⏺ Hi! How can I help you?         ← Assistant response (correct place!)

────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────┐
│ ❯ Type your message...                                          │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Session: default  ◻ idle  Messages: 2  Mode: standard  10:06 AM │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

To test the fix:
```bash
lyra
```

Then:
1. Type a message in the input box
2. Press Enter
3. The message should appear in the conversation area (between the two separator lines)
4. No terminal echo should appear above the header

## Technical Details

### Why Terminal Echo Happens

When a terminal is in "cooked mode" (default), it echoes characters as you type them. Ink needs to put the terminal in "raw mode" to capture input without echo. The explicit stdin configuration ensures Ink properly manages terminal modes.

### Ink's Raw Mode

Ink automatically switches the terminal to raw mode when it takes control of stdin. This:
- Disables line buffering
- Disables echo
- Allows character-by-character input
- Enables special key handling (arrows, ctrl+c, etc.)

### Why `patchConsole: false`

Setting `patchConsole: false` prevents Ink from intercepting `console.log` calls. This is important because:
- We want errors to go to stderr naturally
- We don't want console output interfering with the UI
- It keeps the rendering pipeline clean

## Related Files

- **Fixed**: `packages/ui-terminal/src/index.tsx`
- **Related**: `packages/ui-terminal/src/components/InputArea.tsx` (handles input submission)
- **Related**: `packages/ui-terminal/src/components/ConversationView.tsx` (renders messages)

## Additional Improvements Made

Along with fixing the terminal echo issue, we also:
1. ✅ Added vibrant Dracula-inspired colors
2. ✅ Enhanced Header with colorful logo and info
3. ✅ Updated AssistantTextMessage with green marker
4. ✅ Enhanced ToolExecution with pink tool names
5. ✅ Improved StatusBar with color-coded indicators

See `COLOR_ENHANCEMENT.md` for details on the color improvements.
