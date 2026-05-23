# Lyra UI - Claude Code Format Implementation Plan

## Overview

Transform Lyra UI to match Claude Code's visual format with rich colors, symbols, and interactive elements.

## Phase 1: Core Formatting & Colors

### 1.1 Color System
**File**: `packages/ui-core/src/theme/colors.ts`

```typescript
export const colors = {
  // Primary message colors
  userPrompt: '#00D9FF',      // Bright cyan
  assistant: '#E0E0E0',       // Light gray
  thinking: '#FFD700',        // Gold
  backgroundTask: '#808080',  // Gray
  system: '#00CED1',          // Cyan
  
  // Status colors
  success: '#00FF00',         // Green
  error: '#FF0000',           // Red
  warning: '#FFA500',         // Orange
  
  // UI element colors
  filePath: '#00CED1',        // Cyan
  lineNumber: '#666666',      // Dark gray
  code: '#FFFFFF',            // White
  timestamp: '#999999',       // Medium gray
  
  // Background
  background: '#000000',      // Black
  backgroundAlt: '#1A1A1A',   // Dark gray
}
```

### 1.2 Symbol System
**File**: `packages/ui-core/src/theme/symbols.ts`

```typescript
export const symbols = {
  // Message markers
  userPrompt: '❯',
  assistant: '⏺',
  thinking: '✳',
  backgroundTask: '◯',
  system: '⏵⏵',
  
  // Tree/indent
  branch: '⎿',
  checkbox: '◻',
  
  // Navigation
  upArrow: '↑',
  downArrow: '↓',
  separator: '·',
  ellipsis: '…',
  
  // Logo (3 lines)
  logo: [
    ' ▐▛███▜▌',
    '▝▜█████▛▘',
    '  ▘▘ ▝▝'
  ]
}
```

## Phase 2: Header Component

### 2.1 Header Layout
**File**: `packages/ui-terminal/src/components/Header.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'

export function Header() {
  return (
    <Box flexDirection="column">
      {/* Logo + Version */}
      <Box>
        <Box flexDirection="column" marginRight={2}>
          {symbols.logo.map((line, i) => (
            <Text key={i} color={colors.userPrompt}>{line}</Text>
          ))}
        </Box>
        <Box flexDirection="column">
          <Text bold>Lyra v1.0.0</Text>
          <Text color={colors.timestamp}>
            Opus 4.7 (1M context) · Deep Research Mode
          </Text>
          <Text color={colors.timestamp}>
            ~/projects/lyra
          </Text>
        </Box>
      </Box>
      
      {/* Separator */}
      <Text color={colors.lineNumber}>
        {'─'.repeat(80)}
      </Text>
    </Box>
  )
}
```

## Phase 3: Message Components

### 3.1 User Message
**File**: `packages/ui-terminal/src/components/UserMessage.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'

export function UserMessage({ content }: { content: string }) {
  return (
    <Box flexDirection="column" marginY={1}>
      <Box>
        <Text color={colors.userPrompt} bold>
          {symbols.userPrompt}{' '}
        </Text>
        <Text>{content}</Text>
      </Box>
    </Box>
  )
}
```

### 3.2 Assistant Message
**File**: `packages/ui-terminal/src/components/AssistantMessage.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'

export function AssistantMessage({ content }: { content: string }) {
  return (
    <Box flexDirection="column">
      <Box>
        <Text color={colors.assistant}>
          {symbols.assistant}{' '}
        </Text>
        <Text>{content}</Text>
      </Box>
    </Box>
  )
}
```

## Phase 4: Tool Execution Display

### 4.1 Tool Call Component
**File**: `packages/ui-terminal/src/components/ToolCall.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'
import { useState } from 'react'

interface ToolCallProps {
  toolName: string
  args: string
  result: string
  codePreview?: { line: number; content: string }[]
  collapsed?: boolean
}

export function ToolCall({ 
  toolName, 
  args, 
  result, 
  codePreview,
  collapsed = true 
}: ToolCallProps) {
  const [isExpanded, setIsExpanded] = useState(!collapsed)
  
  return (
    <Box flexDirection="column">
      {/* Tool call line */}
      <Box>
        <Text color={colors.assistant}>
          {symbols.assistant}{' '}
        </Text>
        <Text bold>{toolName}</Text>
        <Text color={colors.filePath}>({args})</Text>
      </Box>
      
      {/* Result */}
      <Box marginLeft={2}>
        <Text color={colors.lineNumber}>
          {symbols.branch}  
        </Text>
        <Text>{result}</Text>
      </Box>
      
      {/* Code preview */}
      {codePreview && (
        <Box flexDirection="column" marginLeft={4}>
          {isExpanded ? (
            codePreview.map(({ line, content }) => (
              <Box key={line}>
                <Text color={colors.lineNumber}>
                  {line.toString().padStart(4, ' ')} 
                </Text>
                <Text> {content}</Text>
              </Box>
            ))
          ) : (
            <Text color={colors.timestamp}>
              {symbols.ellipsis} +{codePreview.length} lines (ctrl+o to expand)
            </Text>
          )}
        </Box>
      )}
    </Box>
  )
}
```

## Phase 5: Progress Indicators

### 5.1 Thinking Indicator
**File**: `packages/ui-terminal/src/components/ThinkingIndicator.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'
import { useEffect, useState } from 'react'

export function ThinkingIndicator({ 
  duration, 
  tokens 
}: { 
  duration: number
  tokens: number 
}) {
  const [frame, setFrame] = useState(0)
  const frames = ['✳', '✴', '✵', '✶']
  
  useEffect(() => {
    const interval = setInterval(() => {
      setFrame(f => (f + 1) % frames.length)
    }, 200)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <Box flexDirection="column">
      <Box>
        <Text color={colors.thinking}>
          {frames[frame]} Flowing{symbols.ellipsis}
        </Text>
        <Text color={colors.timestamp}>
          {' '}({formatDuration(duration)} {symbols.separator} {symbols.upArrow} {formatTokens(tokens)})
        </Text>
      </Box>
    </Box>
  )
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}

function formatTokens(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k tokens`
  }
  return `${count} tokens`
}
```

### 5.2 Background Task List
**File**: `packages/ui-terminal/src/components/BackgroundTasks.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'

interface Task {
  id: string
  agent: string
  description: string
  duration: number
  active: boolean
}

export function BackgroundTasks({ tasks }: { tasks: Task[] }) {
  return (
    <Box flexDirection="column">
      {tasks.map(task => (
        <Box key={task.id}>
          <Text color={task.active ? colors.assistant : colors.backgroundTask}>
            {task.active ? symbols.assistant : symbols.backgroundTask}{' '}
          </Text>
          <Text color={colors.timestamp}>{task.agent}</Text>
          <Text>  {task.description}</Text>
          <Text color={colors.timestamp}>
            {' '.repeat(Math.max(0, 60 - task.description.length))}
            {formatDuration(task.duration)}
          </Text>
        </Box>
      ))}
    </Box>
  )
}
```

## Phase 6: Status Bar

### 6.1 Interactive Status Bar
**File**: `packages/ui-terminal/src/components/StatusBar.tsx`

```typescript
import { Box, Text } from 'ink'
import { symbols, colors } from '@lyra/ui-core'

export function StatusBar({ 
  mode, 
  shortcuts 
}: { 
  mode: string
  shortcuts: string[] 
}) {
  return (
    <Box borderStyle="single" borderColor={colors.lineNumber}>
      <Text color={colors.system}>
        {symbols.system} {mode}
      </Text>
      {shortcuts.map((shortcut, i) => (
        <Text key={i} color={colors.timestamp}>
          {' '}{symbols.separator} {shortcut}
        </Text>
      ))}
    </Box>
  )
}
```

## Phase 7: Streaming Animation

### 7.1 Streaming Text Component
**File**: `packages/ui-terminal/src/components/StreamingText.tsx`

```typescript
import { Text } from 'ink'
import { colors } from '@lyra/ui-core'
import { useEffect, useState } from 'react'

export function StreamingText({ content }: { content: string }) {
  const [opacity, setOpacity] = useState(1)
  
  useEffect(() => {
    const interval = setInterval(() => {
      setOpacity(o => o === 1 ? 0.7 : 1)
    }, 500)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <Text color={colors.assistant} dimColor={opacity < 1}>
      {content}
    </Text>
  )
}
```

## Phase 8: Main Layout Integration

### 8.1 Layout Structure

**IMPORTANT**: The layout has three fixed sections:
1. **Header** (top) - Logo, version, model info
2. **Scrollable conversation area** (middle) - All messages, streaming, tool calls
3. **Input + Status bar** (bottom) - Fixed input box and status

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HEADER (fixed at top)                                                           │
│  ▐▛███▜▌   Lyra v1.0.0                                                          │
│ ▝▜█████▛▘  Opus 4.7 (1M context) · Deep Research Mode                          │
│   ▘▘ ▝▝    ~/projects/lyra                                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│ SCROLLABLE CONVERSATION AREA (grows/scrolls)                                    │
│                                                                                  │
│ ❯ User message 1                                                                │
│                                                                                  │
│ ⏺ Assistant response 1                                                          │
│                                                                                  │
│ ⏺ Write(src/feature.ts)                                                         │
│   ⎿ Wrote 50 lines to src/feature.ts                                           │
│      1 export function feature() {                                              │
│      2   return "implemented"                                                   │
│      … +48 lines (ctrl+o to expand)                                             │
│                                                                                  │
│ ✳ Flowing… (2m 30s · ↑ 5.2k tokens)  ← STREAMING HAPPENS HERE                 │
│   ⎿ ◻ Analyzing codebase structure                                             │
│                                                                                  │
│ ◯ researcher  Deep research on token optimization                    45s        │
│ ◯ tester     Running integration tests                               30s        │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ INPUT BOX (fixed at bottom)                                                     │
│ ❯ [Type your message here...]                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ STATUS BAR (fixed at bottom)                                                    │
│ ⏵⏵ bypass permissions on · shift+tab to cycle · esc to interrupt · ↓ to manage│
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Updated Main App
**File**: `packages/ui-terminal/src/index.tsx`

```typescript
import React from 'react'
import { Box, render } from 'ink'
import { Header } from './components/Header'
import { ConversationView } from './components/ConversationView'
import { InputArea } from './components/InputArea'
import { StatusBar } from './components/StatusBar'

function App() {
  return (
    <Box flexDirection="column" height="100%">
      {/* Fixed header at top */}
      <Header />
      
      {/* Scrollable conversation area (grows to fill space) */}
      <Box flexDirection="column" flexGrow={1} overflow="hidden">
        <ConversationView />
      </Box>
      
      {/* Fixed input box at bottom */}
      <InputArea />
      
      {/* Fixed status bar at bottom */}
      <StatusBar 
        mode="bypass permissions on (shift+tab to cycle)"
        shortcuts={['esc to interrupt', '↓ to manage']}
      />
    </Box>
  )
}

render(<App />)
```

### 8.3 Conversation View Component
**File**: `packages/ui-terminal/src/components/ConversationView.tsx`

```typescript
import React from 'react'
import { Box } from 'ink'
import { UserMessage } from './UserMessage'
import { AssistantMessage } from './AssistantMessage'
import { ToolCall } from './ToolCall'
import { ThinkingIndicator } from './ThinkingIndicator'
import { BackgroundTasks } from './BackgroundTasks'
import { useUIStore } from '@lyra/ui-core'

export function ConversationView() {
  const messages = useUIStore(state => state.messages)
  const isStreaming = useUIStore(state => state.isStreaming)
  const streamingContent = useUIStore(state => state.streamingContent)
  const backgroundTasks = useUIStore(state => state.backgroundTasks)
  
  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Render all messages */}
      {messages.map((msg, i) => {
        if (msg.role === 'user') {
          return <UserMessage key={i} content={msg.content} />
        }
        if (msg.role === 'assistant') {
          return <AssistantMessage key={i} content={msg.content} />
        }
        if (msg.role === 'tool') {
          return (
            <ToolCall 
              key={i}
              toolName={msg.toolName}
              args={msg.args}
              result={msg.result}
              codePreview={msg.codePreview}
            />
          )
        }
        return null
      })}
      
      {/* Streaming indicator (appears in conversation area) */}
      {isStreaming && (
        <>
          <ThinkingIndicator 
            duration={streamingContent.duration} 
            tokens={streamingContent.tokens} 
          />
          <AssistantMessage content={streamingContent.text} streaming />
        </>
      )}
      
      {/* Background tasks (appear in conversation area) */}
      {backgroundTasks.length > 0 && (
        <BackgroundTasks tasks={backgroundTasks} />
      )}
    </Box>
  )
}
```

## Implementation Checklist

### Phase 1: Core (Week 1)
- [ ] Create color system
- [ ] Create symbol system
- [ ] Set up theme infrastructure

### Phase 2: Components (Week 2)
- [ ] Implement Header
- [ ] Implement UserMessage
- [ ] Implement AssistantMessage
- [ ] Implement ToolCall

### Phase 3: Advanced (Week 3)
- [ ] Implement ThinkingIndicator
- [ ] Implement BackgroundTasks
- [ ] Implement StatusBar
- [ ] Implement StreamingText

### Phase 4: Integration (Week 4)
- [ ] Integrate all components
- [ ] Add keyboard shortcuts
- [ ] Add animations
- [ ] Test on different terminals

### Phase 5: Polish (Week 5)
- [ ] Fine-tune colors
- [ ] Optimize performance
- [ ] Add accessibility features
- [ ] Write documentation

## Testing Strategy

1. **Visual Testing**: Compare side-by-side with Claude Code
2. **Terminal Compatibility**: Test on iTerm2, Terminal.app, Windows Terminal
3. **Color Accuracy**: Verify hex colors render correctly
4. **Animation Smoothness**: Check frame rates and timing
5. **Responsive Layout**: Test at different terminal widths

## Success Criteria

✅ Visual match: 95%+ similarity to Claude Code
✅ Color accuracy: Exact hex color matches
✅ Symbol rendering: All Unicode symbols display correctly
✅ Animation smoothness: 60fps for all animations
✅ Performance: <50ms render time per frame

---

**Target**: Complete Claude Code UI replication
**Timeline**: 5 weeks
**Priority**: High
