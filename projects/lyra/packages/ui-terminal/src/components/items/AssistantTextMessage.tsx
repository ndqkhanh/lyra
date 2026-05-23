import React from 'react'
import { Box, Text } from 'ink'
import type { AssistantTextItem } from '@lyra/ui-core'

interface Props {
  item: AssistantTextItem
}

export function AssistantTextMessage({ item }: Props) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color="green">⏺ </Text>
        <Text>{item.content}</Text>
        {item.streaming && <Text color="cyan">▊</Text>}
      </Box>
    </Box>
  )
}
