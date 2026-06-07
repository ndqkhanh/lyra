import React from 'react'
import { Box } from 'ink'
import { useUIStore } from '@lyra/ui-core'
import { ConversationView } from '../components/ConversationView'
import { StatusBar } from '../components/StatusBar'
import { Header } from '../components/Header'

interface StandardModeProps {
  sessionId: string
}

/**
 * Standard display mode - balanced information
 * - All messages visible
 * - Thinking blocks collapsed by default
 * - Tool summaries shown
 * - Full status bar
 */
export function StandardMode({ sessionId }: StandardModeProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))

  if (!session) return null

  return (
    <Box flexDirection="column" height="100%">
      <Header width={process.stdout.columns || 120} />
      <Box flexGrow={1}>
        <ConversationView sessionId={sessionId} />
      </Box>
      <StatusBar sessionId={sessionId} />
    </Box>
  )
}
