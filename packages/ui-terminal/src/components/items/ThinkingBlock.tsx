import React, { useEffect } from 'react'
import { Box, Text } from 'ink'
import type { ThinkingItem } from '@lyra/ui-core'
import { colors, symbols, observability } from '@lyra/ui-core'
import { CollapsibleText } from '../Collapsible'
import { StreamingIndicator } from '../StreamingIndicator'

interface Props {
  item: ThinkingItem
  sessionId?: string
}

export function ThinkingBlock({ item, sessionId }: Props) {
  // Emit observability events for thinking
  useEffect(() => {
    if (!sessionId) return

    if (!item.content && !item.durationSec) {
      // Thinking started
      observability.emit({
        type: 'thinking_start',
        timestamp: Date.now(),
        sessionId
      })
    } else if (item.durationSec) {
      // Thinking ended
      observability.emit({
        type: 'thinking_end',
        timestamp: Date.now(),
        sessionId,
        data: {
          metadata: { duration: item.durationSec }
        }
      })
    }
  }, [item.content, item.durationSec, sessionId])

  if (item.collapsed && item.durationSec) {
    // Minimal/Standard mode: show duration badge only
    return (
      <Box marginBottom={1}>
        <Text color={colors.assistant}>{symbols.assistant} </Text>
        <Text color={colors.timestamp}>
          {symbols.thinking || '💭'} Thought for {item.durationSec.toFixed(1)}s
        </Text>
      </Box>
    )
  }

  if (!item.content) {
    // Still thinking (no duration yet)
    return (
      <Box marginBottom={1}>
        <StreamingIndicator type="thinking" label="Thinking..." />
      </Box>
    )
  }

  // Debug mode: show full thinking content
  return (
    <Box flexDirection="column" marginBottom={1} borderStyle="round" borderColor={colors.border}>
      <Box>
        <Text color={colors.assistant}>{symbols.assistant} </Text>
        <Text color={colors.thinking}>
          {symbols.thinking || '💭'} Extended Thinking
        </Text>
        {item.durationSec && (
          <Text color={colors.timestamp}> ({item.durationSec.toFixed(1)}s)</Text>
        )}
      </Box>
      <Box marginLeft={2} marginRight={1}>
        <CollapsibleText content={item.content} maxLines={20} />
      </Box>
    </Box>
  )
}
