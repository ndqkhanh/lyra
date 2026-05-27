import React, { useEffect, useState, useCallback } from 'react'
import { Box, useInput, useApp } from 'ink'
import { useUIStore } from '@lyra/ui-core'
import { LocalTransport } from '@lyra/ui-transport'
import { ConversationView } from './components/ConversationView'
import { InputArea } from './components/InputArea'
import { StatusBar } from './components/StatusBar'
import { CommandPalette } from './components/CommandPalette'
import { AgentTree } from './components/AgentTree'
import { ErrorBoundary } from './components/ErrorBoundary'
import { logger } from './utils/logger'

// Hermes-style layout — matches appLayout.tsx exactly:
//   AlternateScreen → Box column → [
//     TranscriptPane (ConversationView),
//     ComposerPane (InputArea with StatusBar at top inside),
//     StatusRulePane at bottom (StatusBar)
//   ]
export function App() {
  const { exit } = useApp()
  const activeSessionId = useUIStore(state => state.activeSessionId)
  const createSession = useUIStore(state => state.createSession)
  const setTransport = useUIStore(state => state.setTransport)
  const setDisplayMode = useUIStore(state => state.setDisplayMode)
  const setProviders = useUIStore(state => state.setProviders)
  const setModelAndProvider = useUIStore(state => state.setModelAndProvider)

  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [showAgentTree, setShowAgentTree] = useState(false)

  useEffect(() => {
    const sessionId = 'default'
    createSession(sessionId)

    const lyraModel = process.env['LYRA_MODEL']
    if (lyraModel) {
      setModelAndProvider(lyraModel, 'anthropic')
    }

    const existingTransport = useUIStore.getState().transport
    const transport = existingTransport ?? new LocalTransport()
    if (!existingTransport) {
      setTransport(transport)
    }
    transport.setSessionId(sessionId)

    const unsubscribeMessage = transport.onMessage((message) => {
      useUIStore.getState().addMessage(sessionId, message)
    })

    const unsubscribeStreamChunk = transport.onStreamChunk((chunk) => {
      if (chunk.done) {
        useUIStore.getState().commitStreamingMessage(sessionId)
      } else if (chunk.type === 'tool-call') {
        useUIStore.getState().addToolCall(sessionId, {
          id: `tool-${Date.now()}`,
          name: chunk.content,
          args: typeof chunk.metadata?.tool_args === 'string' ? chunk.metadata.tool_args : undefined,
          status: 'running',
          startTime: Date.now(),
        })
      } else if (chunk.type === 'tool-result') {
        const session = useUIStore.getState().sessions.get(sessionId)
        if (session) {
          const runningTool = [...session.activeTools].reverse().find(t => t.status === 'running')
          if (runningTool) {
            useUIStore.getState().updateToolCall(sessionId, runningTool.id, 'success')
          }
        }
      } else {
        useUIStore.getState().updateStreamingMessage(sessionId, chunk.content)
      }
    })

    const unsubscribeStreamEvent = transport.onStreamEvent((event) => {
      if (event.kind === 'thinking_start') {
        useUIStore.getState().startThinking(sessionId)
      } else if (event.kind === 'thinking_end') {
        useUIStore.getState().endThinking(sessionId)
      }
    })

    const unsubscribeError = transport.onError((error) => {
      logger.error('App', 'Transport error:', error.message)
      useUIStore.getState().addMessage(sessionId, {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${error.message}`,
        timestamp: Date.now()
      })
      // CRITICAL: Cancel streaming so the user can send another message
      useUIStore.getState().cancelStreaming(sessionId)
    })

    const connectWithRetry = async (maxRetries = 10, delay = 500) => {
      for (let i = 0; i < maxRetries; i++) {
        try {
          await transport.connect()
          return
        } catch {
          if (i < maxRetries - 1) {
            await new Promise(resolve => setTimeout(resolve, delay))
          }
        }
      }
    }

    connectWithRetry().catch(() => {})

    const fetchProviders = async () => {
      try {
        const resp = await fetch('http://localhost:3737/providers')
        const data = await resp.json() as Record<string, unknown>
        if (data.providers) setProviders(data.providers as any)
      } catch {
        setTimeout(fetchProviders, 2000)
      }
    }

    const fetchSettings = async () => {
      try {
        const resp = await fetch('http://localhost:3737/settings')
        const data = await resp.json() as Record<string, unknown>
        if (data.last_model && data.last_provider) {
          setModelAndProvider(data.last_model as string, data.last_provider as string)
        }
      } catch {}
    }

    setTimeout(() => {
      fetchProviders()
      fetchSettings()
    }, 1000)

    return () => {
      unsubscribeMessage()
      unsubscribeStreamChunk()
      unsubscribeStreamEvent()
      unsubscribeError()
      transport.disconnect()
    }
  }, [])

  const handleCommandPalette = useCallback((command: string) => {
    const transport = useUIStore.getState().transport
    if (transport) transport.sendMessage(command)
    setShowCommandPalette(false)
  }, [])

  useInput((input, key) => {
    if (key.ctrl && input === 'k') {
      setShowCommandPalette(true)
      return
    }

    if (key.ctrl && input === 'd') {
      exit()
      return
    }

    if (key.ctrl && input === '\\') {
      const session = useUIStore.getState().getActiveSession()
      if (session) {
        const modes = ['minimal', 'standard', 'debug'] as const
        const currentIdx = modes.indexOf(session.displayMode as any)
        const nextMode = modes[(currentIdx + 1) % modes.length]
        setDisplayMode(session.id, nextMode)
      }
      return
    }

    if (key.ctrl && input === 'l') {
      process.stdout.write('\x1Bc')
      return
    }

    // Ctrl+O — Toggle agent tree
    if (key.ctrl && input === 'o') {
      setShowAgentTree(prev => !prev)
      return
    }

    if (key.shift && key.tab) {
      const session = useUIStore.getState().getActiveSession()
      if (session) {
        const modes = ['ask', 'allow', 'deny'] as const
        const currentMode = session.permissionMode || 'ask'
        const currentIdx = modes.indexOf(currentMode)
        const nextMode = modes[(currentIdx + 1) % modes.length]
        useUIStore.getState().setPermissionMode(session.id, nextMode)
      }
      return
    }
  })

  if (!activeSessionId) {
    return null
  }

  // Hermes layout: AlternateScreen → Box column → [Transcript, ComposerPane, StatusRule at bottom]
  return (
    <ErrorBoundary>
      <Box flexDirection="column">
        {/* Transcript area — Hermes TranscriptPane (ScrollBox) */}
        <Box flexDirection="column" flexGrow={1}>
          <ErrorBoundary>
            <ConversationView sessionId={activeSessionId} />
          </ErrorBoundary>
        </Box>

        {/* Composer area — StatusBar at top inside + TextInput = Hermes ComposerPane */}
        <ErrorBoundary>
          <InputArea sessionId={activeSessionId} />
        </ErrorBoundary>

        {/* Status bar at bottom — Hermes StatusRulePane at="bottom" */}
        <ErrorBoundary>
          <StatusBar sessionId={activeSessionId} />
        </ErrorBoundary>

        <ErrorBoundary>
          <AgentTree sessionId={activeSessionId} visible={showAgentTree} />
        </ErrorBoundary>

        {showCommandPalette && (
          <Box marginTop={5} marginLeft={35}>
            <ErrorBoundary>
              <CommandPalette
                visible={showCommandPalette}
                onSelect={handleCommandPalette}
                onClose={() => setShowCommandPalette(false)}
              />
            </ErrorBoundary>
          </Box>
        )}
      </Box>
    </ErrorBoundary>
  )
}
