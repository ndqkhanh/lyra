#!/usr/bin/env tsx
/**
 * Lyra UI Demo - E2E Test
 *
 * This demo showcases all the UI features we built:
 * - LYRA ASCII logo header
 * - User messages with cyan prompt
 * - Assistant responses with light gray marker
 * - Tool executions with status colors
 * - Streaming indicators
 * - Thinking blocks
 * - Status bar
 * - All theme colors and symbols
 */

import React, { useEffect, useState } from 'react'
import { Box, Text, render } from 'ink'
import { useUIStore, colors, symbols } from '@lyra/ui-core'
import { Header } from './src/components/Header'
import { ConversationView } from './src/components/ConversationView'
import { StatusBar } from './src/components/StatusBar'

function DemoApp() {
  const [step, setStep] = useState(0)
  const createSession = useUIStore(state => state.createSession)
  const addMessage = useUIStore(state => state.addMessage)
  const activeSession = useUIStore(state => state.getActiveSession())

  useEffect(() => {
    // Initialize session
    const sessionId = 'demo'
    createSession(sessionId)

    // Demo sequence
    const demos = [
      // Step 1: User message
      () => {
        addMessage(sessionId, {
          id: 'msg-1',
          role: 'user',
          content: 'Help me analyze the performance of my React application',
          timestamp: Date.now()
        })
      },

      // Step 2: Assistant response
      () => {
        addMessage(sessionId, {
          id: 'msg-2',
          role: 'assistant',
          content: "I'll help you analyze your React application's performance. Let me start by examining your component structure.",
          timestamp: Date.now()
        })
      },

      // Step 3: Tool execution - Read
      () => {
        addMessage(sessionId, {
          id: 'tool-1',
          role: 'tool',
          toolName: 'Read',
          args: { file_path: 'src/App.tsx' },
          status: 'success',
          result: {
            output: `1  import React from 'react'
2  import { useState, useEffect } from 'react'
3  import { Header } from './components/Header'
4  import { Dashboard } from './components/Dashboard'
5
6  export function App() {
7    const [data, setData] = useState([])
8
9    useEffect(() => {
10      fetchData().then(setData)
11    }, [])
12
13    return (
14      <div>
15        <Header />
16        <Dashboard data={data} />
17      </div>
18    )
19  }`
          },
          timestamp: Date.now()
        })
      },

      // Step 4: Thinking block
      () => {
        addMessage(sessionId, {
          id: 'thinking-1',
          role: 'thinking',
          content: 'Analyzing component structure... I notice several potential performance issues:\n1. Missing dependency array in useEffect\n2. No memoization for expensive computations\n3. Prop drilling could be optimized with context',
          durationSec: 2.5,
          collapsed: false,
          timestamp: Date.now()
        })
      },

      // Step 5: Assistant analysis
      () => {
        addMessage(sessionId, {
          id: 'msg-3',
          role: 'assistant',
          content: "I've identified several performance optimization opportunities:\n\n1. **useEffect dependency**: Missing dependency array could cause infinite re-renders\n2. **Memoization**: Consider using useMemo for expensive computations\n3. **Component splitting**: Break down large components for better code splitting\n\nLet me create an optimized version for you.",
          timestamp: Date.now()
        })
      },

      // Step 6: Tool execution - Write
      () => {
        addMessage(sessionId, {
          id: 'tool-2',
          role: 'tool',
          toolName: 'Write',
          args: { file_path: 'src/App.optimized.tsx' },
          status: 'success',
          result: {
            output: `Wrote 45 lines to src/App.optimized.tsx

Key improvements:
- Added proper dependency arrays
- Implemented useMemo for data processing
- Split Dashboard into smaller components
- Added React.memo for expensive child components`
          },
          timestamp: Date.now()
        })
      },

      // Step 7: Tool execution - Bash (running tests)
      () => {
        addMessage(sessionId, {
          id: 'tool-3',
          role: 'tool',
          toolName: 'Bash',
          args: { command: 'npm run test:performance' },
          status: 'running',
          timestamp: Date.now()
        })
      },

      // Step 8: Complete test execution
      () => {
        addMessage(sessionId, {
          id: 'tool-3',
          role: 'tool',
          toolName: 'Bash',
          args: { command: 'npm run test:performance' },
          status: 'success',
          result: {
            output: `> npm run test:performance

Performance Test Results:
✅ Initial render: 45ms → 12ms (73% faster)
✅ Re-render on data change: 120ms → 35ms (71% faster)
✅ Memory usage: 45MB → 28MB (38% reduction)

All performance benchmarks passed!`
          },
          timestamp: Date.now()
        })
      },

      // Step 9: Final summary
      () => {
        addMessage(sessionId, {
          id: 'msg-4',
          role: 'assistant',
          content: "Perfect! The optimizations are working great:\n\n✅ 73% faster initial render\n✅ 71% faster re-renders\n✅ 38% less memory usage\n\nYour React application is now significantly more performant. The changes are ready to commit!",
          timestamp: Date.now()
        })
      },

      // Step 10: User follow-up
      () => {
        addMessage(sessionId, {
          id: 'msg-5',
          role: 'user',
          content: 'Excellent! Can you also check for any accessibility issues?',
          timestamp: Date.now()
        })
      },

      // Step 11: Assistant response with streaming simulation
      () => {
        addMessage(sessionId, {
          id: 'msg-6',
          role: 'assistant',
          content: "I'll run an accessibility audit for you...",
          streaming: true,
          timestamp: Date.now()
        })
      }
    ]

    // Run demo sequence
    let currentStep = 0
    const interval = setInterval(() => {
      if (currentStep < demos.length) {
        demos[currentStep]()
        currentStep++
        setStep(currentStep)
      } else {
        clearInterval(interval)
      }
    }, 2000) // 2 seconds between each step

    return () => clearInterval(interval)
  }, [])

  if (!activeSession) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text color={colors.userPrompt}>Initializing Lyra Demo...</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column" height="100%">
      {/* Header with LYRA logo */}
      <Header
        version="1.0.0"
        model="Opus 4.7 (1M context)"
        mode="Deep Research Mode"
      />

      {/* Demo info banner */}
      <Box borderStyle="round" borderColor={colors.userPrompt} paddingX={1} marginBottom={1}>
        <Text color={colors.thinking}>
          {symbols.thinking} Lyra UI Demo - Step {step}/11 - Showcasing all UI features
        </Text>
      </Box>

      {/* Conversation area */}
      <Box flexGrow={1}>
        <ConversationView sessionId={activeSession.id} />
      </Box>

      {/* Status bar */}
      <StatusBar session={activeSession} />

      {/* Demo controls */}
      <Box borderStyle="single" borderColor={colors.border} paddingX={1} marginTop={1}>
        <Text color={colors.timestamp}>
          Press Ctrl+C to exit {symbols.separator} Ctrl+\ to cycle display mode
        </Text>
      </Box>
    </Box>
  )
}

// Run the demo
render(<DemoApp />)
