import React from 'react'
import { Box, Text } from 'ink'
import type { AssistantTextItem } from '@lyra/ui-core'
import { colors, symbols } from '@lyra/ui-core'

interface Props {
  item: AssistantTextItem
}

export function AssistantTextMessage({ item }: Props) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={colors.assistant}>{symbols.assistant} </Text>
        <Text>{item.content}</Text>
        {item.streaming && <Text color={colors.userPrompt}>▊</Text>}
      </Box>
    </Box>
  )
}
