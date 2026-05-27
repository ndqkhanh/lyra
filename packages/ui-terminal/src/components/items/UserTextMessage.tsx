import React from 'react'
import { Box, Text } from 'ink'
import type { UserTextItem } from '@lyra/ui-core'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface Props {
  item: UserTextItem
}

export function UserTextMessage({ item }: Props) {
  const colors = useThemeColors()
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text bold color={colors.userPrompt}>
          {symbols.userPrompt}{' '}
        </Text>
        <Text color={colors.userText}>{item.content}</Text>
      </Box>
    </Box>
  )
}
