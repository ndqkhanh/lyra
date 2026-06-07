import React from 'react'
import { Box } from 'ink'
import { useUIStore } from '@lyra/ui-core'
import { ConversationView } from '../components/ConversationView'
import { StatusBar } from '../components/StatusBar'

interface MinimalModeProps {
  sessionId: string
}

/**
 * Minimal display mode - only essential information
 * - Latest message only
 * - No thinking blocks
 * - No tool details
 * - Compact status bar
 */
export function MinimalMode({ sessionId }: MinimalModeProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))

  if (!session) return null

  return (
    <Box flexDirection="column" height="100%">
      <Box flexGrow={1}>
        <ConversationView sessionId={sessionId} />
      </Box>
      <StatusBar sessionId={sessionId} />
    </Box>
  )
}
