import React from 'react'
import { Box, Text } from 'ink'
import { useUIStore, useThemeColors, symbols, type Message } from '@lyra/ui-core'

interface QueuedMessagesProps {
  sessionId: string
}

/**
 * QueuedMessages - Display pending messages in queue
 *
 * Shows a compact list of queued messages waiting to be processed.
 * Hermes-style visual indicator for message processing order.
 */
export function QueuedMessages({ sessionId }: QueuedMessagesProps) {
  const colors = useThemeColors()
  const queuedMessages = useUIStore(state => {
    const session = state.sessions.get(sessionId)
    return (session?.queuedMessages ?? []) as Message[]
  })

  if (queuedMessages.length === 0) {
    return null
  }

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={colors.amber}
      paddingX={1}
      marginBottom={1}
    >
      <Box>
        <Text color={colors.amber} bold>
          {symbols.pending} Queued Messages ({queuedMessages.length})
        </Text>
      </Box>

      {queuedMessages.slice(0, 3).map((msg: Message, idx: number) => {
        const preview = msg.content.slice(0, 60)
        const truncated = msg.content.length > 60 ? '...' : ''
        const roleIcon = msg.role === 'user' ? symbols.userPrompt : symbols.assistant

        return (
          <Box key={msg.id} marginTop={idx === 0 ? 1 : 0}>
            <Text color={colors.dim}>
              {idx + 1}. {roleIcon} {preview}{truncated}
            </Text>
          </Box>
        )
      })}

      {queuedMessages.length > 3 && (
        <Box marginTop={1}>
          <Text color={colors.dim}>
            ... and {queuedMessages.length - 3} more
          </Text>
        </Box>
      )}
    </Box>
  )
}
