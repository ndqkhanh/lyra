import React from 'react'
import { Box, Text } from 'ink'
import type { UserTextItem } from '@lyra/ui-core'
import { colors, symbols } from '@lyra/ui-core'

interface Props {
  item: UserTextItem
}

export function UserTextMessage({ item }: Props) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text bold color={colors.userPrompt}>{symbols.userPrompt} </Text>
        <Text>{item.content}</Text>
      </Box>
    </Box>
  )
}
