# Lyra UI - Claude Code Style Update

Successfully updated Lyra's bottom UI components to match Claude Code's design language.

## Changes Made

### 1. InputArea Component (`packages/ui-terminal/src/components/InputArea.tsx`)

**Before:**
- Input wrapped in bordered box with `borderStyle="single"`
- Prompt symbol: `symbols.userPrompt` with border
- Long placeholder text visible

**After:**
- Clean, borderless input area
- Simple `❯` prompt symbol (Claude Code style)
- No placeholder text (cleaner look)
- Padding: `paddingX={2}` for consistent spacing

```typescript
// New style
<Box paddingX={2}>
  <Text bold color={colors.userPrompt}>❯ </Text>
  <Box flexDirection="column" flexGrow={1}>
    <TextInput
      value={history.current}
      onChange={history.setCurrent}
      onSubmit={handleSubmit}
      placeholder=""
    />
  </Box>
</Box>
```

### 2. StatusBar Component (`packages/ui-terminal/src/components/StatusBar.tsx`)

**Before:**
- Single-line status bar with border
- Static information: session ID, message count, mode, time
- Fixed layout with spacing

**After:**
- Multi-line status area without border
- **Agent/Task indicators** - Shows active state with animated spinner
- **Bottom controls bar** - Permission mode and keyboard shortcuts
- Dynamic visibility (agent indicators only show when active)

**Features:**
- Animated spinner: `⏵`, `⏵⏵`, `⏵⏵⏵`, `⏵⏵` (100ms interval)
- State indicators:
  - `◯` - Ready/Idle
  - `⏺` - Thinking/Running/Composing
  - `⏵⏵⏵` - Streaming (animated)
  - `✳` - Error
- State text: "Ready", "Thinking…", "Running…", "Composing…", "Flowing…", "Error"
- Bottom controls: "⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage"

```typescript
// Agent indicators (conditional)
{(indicatorState === 'streaming' || indicatorState === 'thinking') && (
  <Box paddingX={2} paddingY={0}>
    <Text color={stateColor}>{stateIcon} </Text>
    <Text color={stateColor}>{stateText}</Text>
    <Text color={colors.timestamp} dimColor> ({messageCount} messages)</Text>
  </Box>
)}

// Bottom controls (always visible)
<Box paddingX={2} paddingY={0}>
  <Text color={colors.timestamp} dimColor>
    ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
  </Text>
</Box>
```

### 3. Main Layout (`packages/ui-terminal/src/index.tsx`)

**Before:**
- Separator line only below header
- Input area directly after conversation
- Status bar at bottom

**After:**
- Separator line below header
- **New separator line above input area** (matches Claude Code)
- Input area with clean prompt
- Status bar with agent indicators and controls

```typescript
<Box flexDirection="column" height="100%">
  <Header />
  <Box>
    <Text color={colors.separator}>{symbols.horizontalLine.repeat(terminalWidth)}</Text>
  </Box>
  <ConversationView sessionId={activeSession.id} />
  <Box>
    <Text color={colors.separator}>{symbols.horizontalLine.repeat(terminalWidth)}</Text>
  </Box>
  <InputArea sessionId={activeSession.id} />
  {activeSession.displayConfig.showStatusBar && (
    <StatusBar session={activeSession} />
  )}
</Box>
```

## Visual Comparison

### Before
```
┌─────────────────────────────────────────┐
│ ❯ Type your message... (↑/↓ for hist...│
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ Session: default  ⏺ idle  Messages: 5  │
│ Mode: standard  3:45 PM  Ctrl+\ mode    │
└─────────────────────────────────────────┘
```

### After (Claude Code Style)
```
─────────────────────────────────────────────
  ❯ 

  ⏺ Flowing… (5 messages)

  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

## Key Design Principles

1. **Minimalism** - Remove unnecessary borders and visual clutter
2. **Contextual Information** - Show agent status only when active
3. **Consistent Spacing** - Use `paddingX={2}` for horizontal alignment
4. **Animated Feedback** - Spinner animation for active states
5. **Clear Hierarchy** - Separator lines define input/output boundaries

## State Mapping

| Internal State | Icon | Display Text | Color |
|---------------|------|--------------|-------|
| idle | ◯ | Ready | timestamp |
| thinking | ⏺ | Thinking… | thinking |
| tool_running | ⏺ | Running… | statusActive |
| composing | ⏺ | Composing… | assistant |
| streaming | ⏵⏵⏵ | Flowing… | statusActive |
| error | ✳ | Error | statusError |

## Files Modified

1. `packages/ui-terminal/src/components/InputArea.tsx`
   - Removed border box
   - Changed prompt to `❯`
   - Removed placeholder text
   - Added consistent padding

2. `packages/ui-terminal/src/components/StatusBar.tsx`
   - Removed border box
   - Added animated spinner
   - Conditional agent indicators
   - Bottom controls bar
   - Removed unused imports (symbols)

3. `packages/ui-terminal/src/index.tsx`
   - Added separator line above input area
   - Maintained responsive width for separators

## Testing

Build successful with no TypeScript errors:
```bash
cd packages/ui-terminal && npm run build
# ✓ Build completed successfully
```

## Next Steps

To test the new UI:
```bash
lyra
```

The UI now matches Claude Code's clean, minimal design with:
- ✅ Separator line above input
- ✅ Simple `❯` prompt without border
- ✅ Animated agent status indicators
- ✅ Bottom controls bar
- ✅ Contextual information display
- ✅ Responsive layout
