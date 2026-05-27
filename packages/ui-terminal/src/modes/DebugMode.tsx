import React from 'react'
import { Box, Text } from 'ink'
import { useUIStore, colors } from '@lyra/ui-core'
import { ConversationView } from '../components/ConversationView'
import { StatusBar } from '../components/StatusBar'
import { Header } from '../components/Header'

interface DebugModeProps {
  sessionId: string
}

/**
 * Debug display mode - maximum information
 * - All messages with full details
 * - Thinking blocks expanded
 * - Full tool input/output
 * - Performance metrics
 * - State machine status
 */
export function DebugMode({ sessionId }: DebugModeProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const metrics = useUIStore(state => state.getMetrics(sessionId))
  const stateMachine = useUIStore(state => state.getStateMachine(sessionId))

  if (!session) return null

  return (
    <Box flexDirection="column" height="100%">
      <Header width={process.stdout.columns || 120} />

      {/* Debug info panel */}
      <Box borderStyle="single" borderColor={colors.border} paddingX={1} marginBottom={1}>
        <Box flexDirection="column">
          <Text color={colors.thinking} bold>
            DEBUG MODE
          </Text>
          {metrics && (
            <Box>
              <Text color={colors.timestamp}>
                Renders: {metrics.renderCount} | Avg: {metrics.averageRenderTime.toFixed(2)}ms
              </Text>
            </Box>
          )}
          {stateMachine && (
            <Box>
              <Text color={colors.timestamp}>State: {(stateMachine as any).state || 'unknown'}</Text>
            </Box>
          )}
        </Box>
      </Box>

      <Box flexGrow={1}>
        <ConversationView sessionId={sessionId} />
      </Box>

      <StatusBar sessionId={sessionId} />
    </Box>
  )
}
