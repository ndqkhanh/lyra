import React, { useEffect, useState } from 'react'
import { Box, Text } from 'ink'
import type { AssistantTextItem } from '@lyra/ui-core'
import { useThemeColors, symbols, useUIStore } from '@lyra/ui-core'
import { Markdown } from '../Markdown'

interface Props {
  item: AssistantTextItem
  sessionId?: string
}

export function AssistantTextMessage({ item, sessionId }: Props) {
  const colors = useThemeColors()
  const [cursorVisible, setCursorVisible] = useState(true)

  // Animate cursor when streaming
  useEffect(() => {
    if (!item.streaming) return

    const interval = setInterval(() => {
      setCursorVisible(v => !v)
    }, 500)

    return () => clearInterval(interval)
  }, [item.streaming])

  // Get performance metrics if available
  const metrics = sessionId ? useUIStore(state => state.getMetrics(sessionId)) : null

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Hermes-style bordered response panel */}
      <Box
        borderStyle="round"
        borderColor={colors.bronze}
        paddingX={1}
        paddingY={0}
        flexDirection="column"
      >
        <Box flexDirection="row">
          <Text color={colors.success}>{symbols.assistant} </Text>
          <Box flexDirection="column" flexGrow={1}>
            <Markdown content={item.content} />
          </Box>
          {item.streaming && cursorVisible && (
            <Text color={colors.userPrompt}>▊</Text>
          )}
        </Box>

        {/* Show performance metrics in debug mode */}
        {metrics && metrics.lastRenderTime > 0 && (
          <Box marginTop={1}>
            <Text color={colors.timestamp} dimColor>
              {metrics.lastRenderTime.toFixed(1)}ms
            </Text>
          </Box>
        )}
      </Box>
    </Box>
  )
}
