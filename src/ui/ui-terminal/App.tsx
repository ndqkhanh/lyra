import React, { useEffect, useState, useCallback } from 'react'
import { Box, useInput, useApp } from 'ink'
import { useUIStore, config, type ProviderInfo, type DisplayMode } from '@lyra/ui-core'
import { LocalTransport } from '@lyra/ui-transport'
import { ConversationView } from './components/ConversationView'
import { InputArea } from './components/InputArea'
import { StatusBar } from './components/StatusBar'
import { CommandPalette } from './components/CommandPalette'
import { AgentTree } from './components/AgentTree'
import { ErrorBoundary } from './components/ErrorBoundary'
import { logger } from './utils/logger'

// Type guard for providers response
interface ProvidersResponse {
  providers: ProviderInfo[]
}

function isProvidersResponse(data: unknown): data is ProvidersResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'providers' in data &&
    Array.isArray((data as Record<string, unknown>).providers)
  )
}

// Type guard for settings response
interface SettingsResponse {
  last_model: string
  last_provider: string
}

function isSettingsResponse(data: unknown): data is SettingsResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'last_model' in data &&
    'last_provider' in data &&
    typeof (data as Record<string, unknown>).last_model === 'string' &&
    typeof (data as Record<string, unknown>).last_provider === 'string'
  )
}

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
  const [ready, setReady] = useState(false)

  // Defer ALL initialisation past the first paint so zustand store
  // mutations don't synchronously re-render StatusBar while App is
  // still rendering (the "Cannot update App while rendering StatusBar"
  // React warning).  The `ready` guard + setTimeout(0) break the
  // synchronous subscriber chain.
  useEffect(() => {
    const id = setTimeout(() => {
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

      transport.onMessage((message) => {
        useUIStore.getState().addMessage(sessionId, message)
      })

      transport.onStreamChunk((chunk) => {
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

      transport.onStreamEvent((event) => {
        if (event.kind === 'thinking_start') {
          useUIStore.getState().startThinking(sessionId)
        } else if (event.kind === 'thinking_end') {
          useUIStore.getState().endThinking(sessionId)
        }
      })

      transport.onError((error) => {
        logger.error('App', 'Transport error:', error.message)
        useUIStore.getState().cancelStreaming(sessionId)
        setTimeout(() => {
          useUIStore.getState().addMessage(sessionId, {
            id: `error-${Date.now()}`,
            role: 'system',
            content: `Error: ${error.message}`,
            timestamp: Date.now()
          })
        }, 0)
      })

      const connectWithRetry = async (maxRetries = config.retryConfig.maxRetries, delay = config.retryConfig.initialDelay) => {
        for (let i = 0; i < maxRetries; i++) {
          try {
            await transport.connect()
            logger.info('App', 'Transport connected successfully')
            return
          } catch (error) {
            logger.error('App', `Connection attempt ${i + 1}/${maxRetries} failed:`, error)
            if (i < maxRetries - 1) {
              await new Promise(resolve => setTimeout(resolve, delay))
            } else {
              useUIStore.getState().addMessage(sessionId, {
                id: `error-${Date.now()}`,
                role: 'system',
                content: `Failed to connect after ${maxRetries} attempts. Please check your connection and ensure the Lyra server is running.`,
                timestamp: Date.now()
              })
            }
          }
        }
      }

      connectWithRetry().catch((error) => {
        logger.error('App', 'Connection failed:', error)
      })

      const fetchProviders = async (retries = 0, maxRetries = 5) => {
        try {
          const resp = await fetch(`${config.apiUrl}/providers`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const data = await resp.json() as unknown
          if (isProvidersResponse(data)) {
            setProviders(data.providers)
            logger.info('App', 'Providers fetched successfully')
          } else {
            throw new Error('Invalid providers response format')
          }
        } catch (error) {
          logger.error('App', `Provider fetch failed (attempt ${retries + 1}/${maxRetries}):`, error)
          if (retries < maxRetries) {
            const delay = Math.min(config.fetchIntervals.providers * Math.pow(config.retryConfig.backoffMultiplier, retries), 30000)
            setTimeout(() => fetchProviders(retries + 1, maxRetries), delay)
          } else {
            logger.error('App', 'Provider fetch failed after max retries')
            useUIStore.getState().addMessage(sessionId, {
              id: `error-${Date.now()}`,
              role: 'system',
              content: `Failed to load providers. Please ensure the Lyra server is running at ${config.apiUrl}.`,
              timestamp: Date.now()
            })
          }
        }
      }

      const fetchSettings = async () => {
        try {
          const resp = await fetch(`${config.apiUrl}/settings`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const data = await resp.json() as unknown
          if (isSettingsResponse(data)) {
            setModelAndProvider(data.last_model, data.last_provider)
            logger.info('App', 'Settings loaded successfully')
          }
        } catch (error) {
          logger.error('App', 'Failed to fetch settings:', error)
        }
      }

      setTimeout(() => {
        fetchProviders()
        fetchSettings()
      }, 1000)

      setReady(true)
    })

    return () => clearTimeout(id)
  }, [createSession, setModelAndProvider, setTransport, setProviders, setDisplayMode])

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
        const modes: DisplayMode[] = ['minimal', 'standard', 'debug']
        const currentIdx = modes.indexOf(session.displayMode)
        const nextMode = modes[(currentIdx + 1) % modes.length]
        if (nextMode) {
          setDisplayMode(session.id, nextMode)
        }
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

  if (!ready || !activeSessionId) {
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
