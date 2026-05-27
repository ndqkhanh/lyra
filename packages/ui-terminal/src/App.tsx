import React, { useEffect, useState, useMemo } from 'react'
import { Box, Text, useInput, useApp } from 'ink'
import { useUIStore, colors, symbols } from '@lyra/ui-core'
import { LocalTransport } from '@lyra/ui-transport'
import { Header } from './components/Header'
import { ConversationView } from './components/ConversationView'
import { InputArea } from './components/InputArea'
import { StatusBar } from './components/StatusBar'
import { CommandPalette } from './components/CommandPalette'
import { AgentTree } from './components/AgentTree'
import { logger } from './utils/logger'

// Clear screen and hide cursor
process.stdout.write('\x1Bc')
process.stdout.write('\x1B[?25l')

function CleanDivider({ width }: { width: number }) {
  return (
    <Box>
      <Text color={colors.border}>{symbols.horizontalLine.repeat(Math.max(0, width))}</Text>
    </Box>
  )
}

export function App() {
  const { exit } = useApp()
  // Only subscribe to the stable session ID string — never the session object
  // (session is an Immer proxy that changes reference on every mutation,
  // which would re-render the entire App tree including the header)
  const activeSessionId = useUIStore(state => state.activeSessionId)
  const createSession = useUIStore(state => state.createSession)
  const setTransport = useUIStore(state => state.setTransport)
  const setDisplayMode = useUIStore(state => state.setDisplayMode)
  const setProviders = useUIStore(state => state.setProviders)
  const setModelAndProvider = useUIStore(state => state.setModelAndProvider)

  const [terminalWidth, setTerminalWidth] = useState(process.stdout.columns || 120)
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [showAgentTree, setShowAgentTree] = useState(false)

  // Memoized header — only re-creates when terminal width changes
  const headerEl = useMemo(() => <Header width={terminalWidth || 120} />, [terminalWidth])

  useEffect(() => {
    const sessionId = 'default'
    createSession(sessionId)

    const lyraModel = process.env['LYRA_MODEL']
    if (lyraModel) {
      setModelAndProvider(lyraModel, 'anthropic')
    }

    // Allow tests to inject a mock transport before rendering
    const existingTransport = useUIStore.getState().transport
    const transport = existingTransport ?? new LocalTransport()
    if (!existingTransport) {
      setTransport(transport)
    }

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
        // Update the last running tool to success
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

    const handleResize = () => {
      setTerminalWidth(process.stdout.columns || 120)
    }
    process.stdout.on('resize', handleResize)

    return () => {
      unsubscribeMessage()
      unsubscribeStreamChunk()
      unsubscribeStreamEvent()
      unsubscribeError()
      transport.disconnect()
      process.stdout.off('resize', handleResize)
    }
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

    // Ctrl+T — Hide tasks/agent tree
    if (key.ctrl && input === 't') {
      setShowAgentTree(false)
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

  return (
    <Box flexDirection="column">
      {headerEl}
      <ConversationView sessionId={activeSessionId} />
      <CleanDivider width={terminalWidth} />
      <InputArea sessionId={activeSessionId} />
      <CleanDivider width={terminalWidth} />
      <StatusBar sessionId={activeSessionId} width={terminalWidth} />
      <AgentTree sessionId={activeSessionId} visible={showAgentTree} />

      {showCommandPalette && (
        <Box
          position="absolute"
          marginTop={5}
          marginLeft={35}
        >
          <CommandPalette
            visible={showCommandPalette}
            onSelect={(command) => {
              const transport = useUIStore.getState().transport
              if (transport) transport.sendMessage(command)
              setShowCommandPalette(false)
            }}
            onClose={() => setShowCommandPalette(false)}
          />
        </Box>
      )}
    </Box>
  )
}
