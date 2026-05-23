import React from 'react'
import { Box, Text } from 'ink'
import type { ThinkingItem } from '@lyra/ui-core'
import { colors, symbols } from '@lyra/ui-core'
import { CollapsibleText } from '../Collapsible'
import { StreamingIndicator } from '../StreamingIndicator'

interface Props {
  item: ThinkingItem
}

export function ThinkingBlock({ item }: Props) {
  if (item.collapsed && item.durationSec) {
    // Minimal/Standard mode: show duration badge only
    return (
      <Box marginBottom={1}>
        <Text color={colors.assistant}>{symbols.assistant} </Text>
        <Text color={colors.timestamp}>💭 Thought for {item.durationSec.toFixed(1)}s</Text>
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
        <Text color={colors.thinking}>💭 Extended Thinking</Text>
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
