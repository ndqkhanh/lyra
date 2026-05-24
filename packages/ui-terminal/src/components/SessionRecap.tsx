import React, { useState, useEffect, useMemo } from 'react'
import { Box, Text } from 'ink'
import { useUIStore, colors } from '@lyra/ui-core'

interface SessionRecapProps {
  sessionId: string
}

export function SessionRecap({ sessionId }: SessionRecapProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const [showRecap, setShowRecap] = useState(false)

  useEffect(() => {
    if (!session) return
    const msgCount = session.messages.length
    if (msgCount > 2) {
      setShowRecap(true)
      const timer = setTimeout(() => setShowRecap(false), 5000)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [session?.messages.length])

  const recap = useMemo(() => {
    if (!session) return null
    const msgs = session.messages
    if (msgs.length < 2) return null

    const lastUser = [...msgs].reverse().find(m => m.role === 'user')
    const lastAssistant = [...msgs].reverse().find(m => m.role === 'assistant')

    return {
      lastPrompt: lastUser ? lastUser.content.slice(0, 60) : null,
      lastResponse: lastAssistant ? lastAssistant.content.slice(0, 80) : null,
      turnCount: msgs.filter(m => m.role === 'user').length,
    }
  }, [session])

  if (!showRecap || !recap) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.info} padding={1} marginBottom={1}>
      <Text bold color={colors.info}>Session Recap (Turn {recap.turnCount})</Text>
      {recap.lastPrompt && (
        <Text dimColor>Last: {recap.lastPrompt}{recap.lastPrompt.length >= 60 ? '...' : ''}</Text>
      )}
      {recap.lastResponse && (
        <Text dimColor>Response: {recap.lastResponse}{recap.lastResponse.length >= 80 ? '...' : ''}</Text>
      )}
    </Box>
  )
}
