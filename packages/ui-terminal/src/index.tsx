import React, { useEffect } from 'react'
import { Box, Text, useInput, useApp, render } from 'ink'
import { useUIStore } from '@lyra/ui-core'
import { LocalTransport } from '@lyra/ui-transport'
import { Header } from './components/Header'
import { ConversationView } from './components/ConversationView'
import { InputArea } from './components/InputArea'
import { StatusBar } from './components/StatusBar'

function App() {
  const { exit } = useApp()
  const activeSession = useUIStore(state => state.getActiveSession())
  const createSession = useUIStore(state => state.createSession)
  const setTransport = useUIStore(state => state.setTransport)
  const setDisplayMode = useUIStore(state => state.setDisplayMode)

  useEffect(() => {
    // Initialize session and transport
    const sessionId = 'default'
    createSession(sessionId)

    const transport = new LocalTransport()
    setTransport(transport)

    transport.connect().catch(console.error)

    return () => {
      transport.disconnect()
    }
  }, [])

  // Global keyboard shortcuts
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      exit()
      return
    }

    if (key.ctrl && input === '\\') {
      // Cycle display mode: minimal → standard → debug
      if (activeSession) {
        const modes = ['minimal', 'standard', 'debug'] as const
        const currentIdx = modes.indexOf(activeSession.displayMode)
        const nextMode = modes[(currentIdx + 1) % modes.length]
        setDisplayMode(activeSession.id, nextMode)
      }
      return
    }
  })

  if (!activeSession) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text>Initializing Lyra...</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column" height="100%">
      <Header />
      <ConversationView sessionId={activeSession.id} />
      <InputArea sessionId={activeSession.id} />
      {activeSession.displayConfig.showStatusBar && (
        <StatusBar session={activeSession} />
      )}
    </Box>
  )
}

// Entry point
render(<App />)
