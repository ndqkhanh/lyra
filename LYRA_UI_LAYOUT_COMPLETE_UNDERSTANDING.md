# Lyra UI Layout - Complete Understanding

## ✅ Correct Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HEADER (Fixed at Top)                                                           │
│ ██╗  ██╗   ██╗██████╗  █████╗    Lyra v1.0.0                                   │
│ ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   Opus 4.7 (1M context) · Deep Research Mode   │
│ ███████║ ╚████╔╝ ██████╔╝███████║  ~/projects/lyra                             │
│─────────────────────────────────────────────────────────────────────────────────│
│                                                                                  │
│ SCROLLABLE CONVERSATION AREA (Middle - Grows/Scrolls)                           │
│                                                                                  │
│ ❯ Help me implement feature X                                                   │
│                                                                                  │
│ ⏺ I'll help you implement that. Let me start by creating the core files.       │
│                                                                                  │
│ ⏺ Write(src/feature.ts)                                                         │
│   ⎿ Wrote 50 lines to src/feature.ts                                           │
│      1 export function feature() {                                              │
│      2   return "implemented"                                                   │
│      3 }                                                                         │
│      … +47 lines (ctrl+o to expand)                                             │
│                                                                                  │
│ ⏺ Now let me add tests:                                                         │
│                                                                                  │
│ ⏺ Write(src/feature.test.ts)                                                    │
│   ⎿ Wrote 30 lines to src/feature.test.ts                                      │
│      … +30 lines (ctrl+o to expand)                                             │
│                                                                                  │
│ ✳ Flowing… (2m 30s · ↑ 5.2k tokens)  ← STREAMING HAPPENS HERE IN CONVERSATION │
│   ⎿ ◻ Running tests and verifying implementation                               │
│                                                                                  │
│ ◯ researcher  Deep research on best practices                        45s        │
│ ◯ tester     Running integration tests                               30s        │
│                                                                                  │
│─────────────────────────────────────────────────────────────────────────────────│
│ INPUT BOX (Fixed at Bottom)                                                     │
│ ❯ [Type your next message here...]                                             │
│─────────────────────────────────────────────────────────────────────────────────│
│ STATUS BAR (Fixed at Bottom)                                                    │
│ ⏵⏵ bypass permissions on · shift+tab to cycle · esc to interrupt · ↓ to manage│
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Points

### 1. Three-Section Layout

**Top Section (Fixed)**
- Header with logo, version, model info, directory
- Always visible at the top
- Does not scroll

**Middle Section (Scrollable)**
- All conversation history
- User messages (❯)
- Assistant responses (⏺)
- Tool executions with results
- **Streaming content appears here** (✳ Flowing…)
- Background tasks list
- Scrolls when content exceeds viewport

**Bottom Section (Fixed)**
- Input box for typing new messages
- Status bar with shortcuts
- Always visible at the bottom
- Does not scroll

### 2. Streaming Behavior

**Where streaming appears:**
```
│ ✳ Flowing… (2m 30s · ↑ 5.2k tokens)
│   ⎿ ◻ Current task description
│
│ ⏺ [Streaming text appears here as it comes in...]
```

**NOT in the input box!** The input box stays empty and ready for the next user message.

### 3. Component Hierarchy

```
App
├── Header (fixed)
├── ConversationView (scrollable)
│   ├── Message[] (history)
│   ├── StreamingIndicator (when streaming)
│   ├── StreamingContent (when streaming)
│   └── BackgroundTasks (when active)
├── InputArea (fixed)
└── StatusBar (fixed)
```

### 4. Scroll Behavior

- **Auto-scroll**: When new content arrives, scroll to bottom
- **Manual scroll**: User can scroll up to view history
- **Scroll lock**: When user scrolls up, don't auto-scroll
- **Scroll unlock**: When user scrolls to bottom, resume auto-scroll

### 5. Height Management

```typescript
<Box flexDirection="column" height="100%">
  {/* Header: natural height */}
  <Header />
  
  {/* Conversation: grows to fill remaining space */}
  <Box flexGrow={1} overflow="hidden">
    <ConversationView />
  </Box>
  
  {/* Input: natural height */}
  <InputArea />
  
  {/* Status: natural height */}
  <StatusBar />
</Box>
```

## Implementation Notes

### Ink Layout

```typescript
// Main container
<Box flexDirection="column" height="100%">
  
  // Fixed header
  <Box>
    <Header />
  </Box>
  
  // Scrollable middle (flexGrow=1 takes remaining space)
  <Box flexGrow={1} overflow="hidden">
    <ScrollArea>
      <ConversationView />
    </ScrollArea>
  </Box>
  
  // Fixed input
  <Box>
    <InputArea />
  </Box>
  
  // Fixed status
  <Box>
    <StatusBar />
  </Box>
  
</Box>
```

### State Management

```typescript
interface UIState {
  // Conversation
  messages: Message[]
  
  // Streaming
  isStreaming: boolean
  streamingContent: {
    text: string
    duration: number
    tokens: number
    currentTask: string
  }
  
  // Background tasks
  backgroundTasks: Task[]
  
  // Scroll
  scrollPosition: number
  autoScroll: boolean
}
```

## Visual Examples

### Example 1: Normal Conversation
```
❯ Write a hello world function

⏺ I'll create that for you.

⏺ Write(src/hello.ts)
  ⎿ Wrote 3 lines to src/hello.ts
     1 export function hello() {
     2   return "Hello, World!"
     3 }
```

### Example 2: Streaming Response
```
❯ Explain how this works

✳ Flowing… (15s · ↑ 1.2k tokens)
  ⎿ ◻ Analyzing code structure

⏺ This function works by...
   [text streams in here character by character]
```

### Example 3: Background Tasks
```
⏺ I'll research this in parallel.

◯ researcher  Analyzing best practices                    45s
◯ tester     Running test suite                          30s
◯ reviewer   Checking code quality                       20s
```

## Color Reference

| Element | Color | Hex |
|---------|-------|-----|
| User prompt (❯) | Bright cyan | #00D9FF |
| Assistant (⏺) | Light gray | #E0E0E0 |
| Streaming (✳) | Gold | #FFD700 |
| Background (◯) | Gray | #808080 |
| System (⏵⏵) | Cyan | #00CED1 |
| File path | Cyan | #00CED1 |
| Line numbers | Dark gray | #666666 |
| Success | Green | #00FF00 |
| Error | Red | #FF0000 |

## Next Steps

1. ✅ Layout structure understood
2. ✅ Streaming location clarified
3. ⏳ Implement Phase 1 (colors & symbols)
4. ⏳ Implement Phase 2 (header)
5. ⏳ Implement Phase 3 (messages)
6. ⏳ Implement Phase 4 (tool execution)
7. ⏳ Implement Phase 5 (streaming)
8. ⏳ Implement Phase 6 (status bar)

---

**Status**: ✅ Layout fully understood
**Ready for**: Implementation
**Date**: 2026-05-24
