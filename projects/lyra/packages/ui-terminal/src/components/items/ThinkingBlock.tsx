import React from 'react'
import { Box, Text } from 'ink'
import type { ThinkingItem } from '@lyra/ui-core'

interface Props {
  item: ThinkingItem
}

export function ThinkingBlock({ item }: Props) {
  if (item.collapsed && item.durationSec) {
    // Minimal/Standard mode: show duration badge only
    return (
      <Box marginBottom={1}>
        <Text color="green">⏺ </Text>
        <Text dimColor>💭 Thought for {item.durationSec.toFixed(1)}s</Text>
      </Box>
    )
  }

  if (!item.content) return null

  // Debug mode: show full thinking content
  return (
    <Box flexDirection="column" marginBottom={1} borderStyle="round" borderColor="gray">
      <Box>
        <Text color="green">⏺ </Text>
        <Text color="yellow">💭 Extended Thinking</Text>
        {item.durationSec && (
          <Text dimColor> ({item.durationSec.toFixed(1)}s)</Text>
        )}
      </Box>
      <Box marginLeft={2} marginRight={1}>
        <Text dimColor italic>{item.content}</Text>
      </Box>
    </Box>
  )
}
