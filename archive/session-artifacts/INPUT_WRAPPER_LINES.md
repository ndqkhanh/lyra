# Lyra Input Box Wrapper Lines

Added separator lines above and below the input box to match Claude Code's design.

## Layout Structure

### Before
```
Header
─────────────────────────────────────────────
Conversation Area
─────────────────────────────────────────────
Input Box
Status Bar
```

### After (Claude Code Style)
```
Header
─────────────────────────────────────────────
Conversation Area
─────────────────────────────────────────────
❯ Input Box
─────────────────────────────────────────────
Status Bar
```

## Changes Made

### 1. `packages/ui-terminal/src/index.tsx`

Added third separator line below input box:

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
  <Box>
    <Text color={colors.separator}>{symbols.horizontalLine.repeat(terminalWidth)}</Text>
  </Box>
  {activeSession.displayConfig.showStatusBar && (
    <StatusBar session={activeSession} />
  )}
</Box>
```

### 2. `packages/ui-terminal/src/components/InputArea.tsx`

Removed vertical padding to align with separator lines:

```typescript
// Before: <Box paddingX={2} paddingY={1}>
// After:  <Box paddingX={2}>
```

### 3. `packages/ui-terminal/src/components/StatusBar.tsx`

Removed explicit `paddingY={0}` (unnecessary):

```typescript
// Before: <Box paddingX={2} paddingY={0}>
// After:  <Box paddingX={2}>
```

## Visual Result

```
╦  ╦ ╦╦═╗╔═╗  Lyra Code v1.0.0
║  ╚╦╝╠╦╝╠═╣  Opus 4.7 (1M context) · Deep Research Mode
╩═╝ ╩ ╩╚═╩ ╩  ~/Downloads/MyCV/research/harness-engineering

──────────────────────────────────────────────────────────────────────────────

  No messages yet. Type a message below to start.

──────────────────────────────────────────────────────────────────────────────
  ❯ 
──────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

## Key Features

✅ **Three separator lines:**
1. Below header (separates header from conversation)
2. Above input box (separates conversation from input)
3. Below input box (separates input from status bar)

✅ **Clean alignment:**
- Input box sits between two separator lines
- No extra vertical padding
- Matches Claude Code's visual hierarchy

✅ **Responsive width:**
- All separator lines adjust to terminal width
- Consistent appearance across different terminal sizes

## Build Status

✅ TypeScript build successful
✅ No errors or warnings
✅ Ready to test with `lyra`
